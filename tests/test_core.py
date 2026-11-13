import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dm_save_update import core  # noqa: E402


def general(name, **gameplay):
    gp = {'globalPerformance': 300, 'pointsSystem': [10, 5], 'raceRules': {'fuelCapacity': 100, 'drs': {'enabled': False}}}
    gp.update(gameplay)
    return {'_comment': 'x', 'categoryName': name, 'startYear': 2025,
            'regulations': {'firstMajorRegulationYear': 2030}, 'gameplay': gp}


def circuit(cid, **kw):
    c = {'id': cid, 'name': 'Track %d' % cid, 'week': 5, 'laps': 100, 'tyreWear': 1.0, 'hasSprintWeekend': False}
    c.update(kw)
    return c


def make_mod():
    return {
        'modName': 'Test mod',
        'generalData': general('Cup', globalPerformance=320, pointsSystem=[20, 10]),
        'circuits': [circuit(1, laps=120, week=9, tyreWear=1.4), circuit(3)],
        'sponsors': [{'id': 7, 'name': 'Acme', 'baseAmount': 2.0}],
        'namingSponsors': [],
        'additionalCategories': [{'id': 'cat_b', 'name': 'Truck', 'data': {
            'general': general('Truck', raceRules={'fuelCapacity': 80, 'drs': {'enabled': False}}),
            'circuits': [circuit(11, tyreWear=2.0)], 'sponsors': [], 'namingSponsors': []}}],
    }


def write_save(folder, current_season=2025, era=None):
    """Save in which the Truck category is being played and Cup is parked in the backup."""
    os.makedirs(folder, exist_ok=True)
    config = {'generalData': general('Truck'), 'currentRegulation': {'lapTimeCoefficients': {}}}
    season = {
        'currentSeason': current_season,
        'circuits': [circuit(11, lapRecords=[1])], 'reserveCircuits': [],
        'sponsorsDatabase': [], 'namingSponsorsDatabase': [],
        '_activeCategoryId': 'cat_b', '_activeCategoryOriginalName': 'Truck',
        '_mainCategoryBackup': {'name': 'Cup', 'data': {
            'general': general('Cup'), 'circuits': [circuit(1, lapRecords=[1]), circuit(2)],
            'sponsorsDatabase': [{'id': 7, 'name': 'Acme', 'baseAmount': 1.0, 'contracts': 3}]}},
        'additionalCategories': [],
        'eraSchedule': era, 'categoryEraSchedules': {},
    }
    for name, data in (('config.json', config), ('season.json', season), ('meta.json', {'currentSeason': current_season})):
        with open(os.path.join(folder, name), 'w', encoding='utf-8') as fh:
            json.dump(data, fh, indent=2)
    return core.Save(folder)


def by(changes, **kw):
    return [c for c in changes if all(getattr(c, k) == v for k, v in kw.items())]


class CompareTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = os.path.join(self.tmp.name, 'solo', 'slot_1')

    def tearDown(self):
        self.tmp.cleanup()

    def test_categories_found_through_the_swap(self):
        save = write_save(self.dir)
        cats = {c['key']: c for c in save.categories()}
        self.assertEqual(cats['cat_b']['name'], 'Truck')
        self.assertIn('_mainCategoryBackup', cats['main']['where'])
        self.assertEqual(core.match_score(make_mod(), save), (2, 2))

    def test_settings_and_meta(self):
        changes, _ = core.compare(make_mod(), write_save(self.dir))
        self.assertTrue(by(changes, category='Cup', path='gameplay.globalPerformance', action=core.UPDATE))
        self.assertTrue(by(changes, category='Truck', path='gameplay.raceRules.fuelCapacity', old=100, new=80))
        self.assertFalse([c for c in changes if c.path == '_comment'])

    def test_circuits_keep_calendar_and_records(self):
        changes, _ = core.compare(make_mod(), write_save(self.dir))
        cup = by(changes, category='Cup', section='circuits')
        fields = {c.path for c in cup if c.action == core.UPDATE}
        self.assertEqual(fields, {'laps', 'tyreWear'})  # week stays, lapRecords stays
        self.assertTrue(by(cup, item='Track 3 (3)', action=core.NOT_ADDED))
        self.assertTrue(by(cup, item='Track 2 (2)', action=core.NOT_IN_MOD))

    def test_list_of_dicts_shows_the_field(self):
        mod = make_mod()
        mod['additionalCategories'][0]['data']['general']['gameplay']['raceRules']['dryTyres'] = [
            {'name': 'General', 'durability': 25, 'speed': 50}]
        save = write_save(self.dir)
        save.config['generalData']['gameplay']['raceRules']['dryTyres'] = [{'name': 'General', 'durability': 38, 'speed': 50}]
        changes, _ = core.compare(mod, save)
        self.assertTrue(by(changes, category='Truck', path='gameplay.raceRules.dryTyres[General].durability',
                           old=38, new=25))

    def test_game_managed_fields(self):
        mod = make_mod()
        mod['generalData']['regulations']['baseLimits'] = {'speed': {'max': 25}}
        mod['circuits'][0]['name'] = '6 Hours of Track 1'
        save = write_save(self.dir)
        save.categories()  # Cup sits in the backup
        cup = save.season['_mainCategoryBackup']['data']
        cup['general']['regulations']['baseLimits'] = {'speed': {'max': 100}}
        cup['circuits'][0]['officialName'] = '6 Hours of Track 1'
        changes, _ = core.compare(mod, save)
        self.assertTrue(by(changes, path='regulations.baseLimits.speed.max', action=core.KEEP_GAME))
        self.assertFalse(by(changes, section='circuits', path='name'))
        self.assertFalse(by(changes, section='circuits', path='officialName'))
        cup['circuits'][0]['officialName'] = 'old name'
        changes, _ = core.compare(mod, save)
        self.assertTrue(by(changes, section='circuits', path='officialName', old='old name', new='6 Hours of Track 1'))

    def test_image_paths_made_absolute_by_the_game(self):
        self.assertTrue(core.same_value('./sponsors/a b.png', 'D:/Steam/steamapps/common/Delta Manager/resources/sponsors/a b.png'))
        self.assertTrue(core.same_value('./teams/x.png', 'D:\\Steam\\steamapps\\common\\Delta Manager\\resources\\teams/x.png'))
        self.assertFalse(core.same_value('./sponsors/a.png', 'D:/Steam/.../resources/sponsors/b.png'))
        self.assertFalse(core.same_value('Red Bull', 'red bull'))
        mod = make_mod()
        mod['sponsors'][0]['logo'] = './sponsors/acme.png'
        save = write_save(self.dir)
        save.season['_mainCategoryBackup']['data']['sponsorsDatabase'][0]['logo'] = \
            'E:/SteamLibrary/steamapps/common/Delta Manager/resources/sponsors/acme.png'
        changes, _ = core.compare(mod, save)
        self.assertFalse(by(changes, section='sponsors', path='logo'))

    def test_sponsor_values(self):
        changes, _ = core.compare(make_mod(), write_save(self.dir))
        self.assertTrue(by(changes, section='sponsors', path='baseAmount', old=1.0, new=2.0))

    def test_era_vote_keeps_save_value(self):
        era = {'categoryKey': 'main', 'proposals': [
            {'ruleType': 'points', 'status': 'passed', 'payload': {'pointsSystem': [30, 1]}},
            {'ruleType': 'drs', 'status': 'rejected', 'payload': {'presetId': 'x'}}]}
        save = write_save(self.dir, era=era)
        changes, notes = core.compare(make_mod(), save)
        self.assertTrue(by(changes, category='Cup', path='gameplay.pointsSystem', action=core.KEEP_ERA))
        self.assertTrue(any('era votes' in n for n in notes))
        changes, _ = core.compare(make_mod(), save, core.Options(overwrite_era=True))
        self.assertTrue(by(changes, category='Cup', path='gameplay.pointsSystem', action=core.UPDATE))

    def test_eras_only_with_option(self):
        mod = make_mod()
        mod['generalData']['eras'] = [{'id': 'era_1', 'name': 'Proving Ground', 'fromYear': 2025}]
        save = write_save(self.dir)
        changes, _ = core.compare(mod, save)
        era = by(changes, category='Cup', path='eras')
        self.assertTrue(era and era[0].action == core.KEEP_ERAS and 'add eras' in era[0].note)
        changes, _ = core.compare(mod, save, core.Options(add_eras=True), apply=True)
        self.assertTrue(by(changes, category='Cup', path='eras', action=core.UPDATE))
        cup = [c for c in save.categories() if c['name'] == 'Cup'][0]
        self.assertEqual(cup['general']['eras'][0]['name'], 'Proving Ground')

    def test_report_groups_entities_not_added(self):
        mod = make_mod()
        mod['sponsors'] += [{'id': i, 'name': 'New %d' % i, 'baseAmount': 1.0} for i in range(100, 140)]
        changes, notes = core.compare(mod, write_save(self.dir))
        text = core.report_text(changes, notes, 'm', 's')
        self.assertIn('- [not added] 40 items  (New in the mod.', text)
        self.assertIn('New 100 (100), New 101 (101)', text)
        self.assertEqual(text.count('[not added]'), 2)  # the 40 sponsors on one line, the single circuit as before
        self.assertTrue(all(len(line) <= 120 for line in text.splitlines() if line.startswith('    New')))

    def test_major_regulation_keeps_drawn_values(self):
        changes, _ = core.compare(make_mod(), write_save(self.dir, current_season=2031))
        self.assertTrue(by(changes, category='Cup', path='gameplay.globalPerformance', action=core.KEEP_MAJOR))
        changes, _ = core.compare(make_mod(), write_save(self.dir, current_season=2026))
        self.assertTrue(by(changes, category='Cup', path='gameplay.globalPerformance', action=core.UPDATE))

    def test_save_is_not_written(self):
        save = write_save(self.dir)
        before = {f: os.path.getmtime(os.path.join(self.dir, f)) for f in os.listdir(self.dir)}
        core.compare(make_mod(), save)
        core.report_text(*core.compare(make_mod(), save), mod_label='m', save_label='s')
        self.assertEqual(before, {f: os.path.getmtime(os.path.join(self.dir, f)) for f in os.listdir(self.dir)})

    def test_other_mod_matches_nothing(self):
        mod = make_mod()
        mod['generalData']['categoryName'] = 'Formula X'
        mod['additionalCategories'] = []
        save = write_save(self.dir)
        self.assertEqual(core.match_score(mod, save), (0, 1))
        _, notes = core.compare(mod, save)
        self.assertTrue(any('not in this save' in n for n in notes))


if __name__ == '__main__':
    unittest.main()
