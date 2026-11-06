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
