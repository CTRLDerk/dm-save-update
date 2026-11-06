import json
import os
import shutil
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dm_save_update import apply, core, jsonfmt  # noqa: E402
from tests.test_core import by, make_mod, write_save  # noqa: E402


def read(path):
    with open(path, encoding='utf-8', newline='') as fh:
        return fh.read()


class ApplyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = os.path.join(self.tmp.name, 'solo', 'slot_1')
        write_save(self.dir)
        # the game writes JSON like JSON.stringify: rewrite the fixture that way
        for name in ('config.json', 'season.json'):
            p = os.path.join(self.dir, name)
            data = json.loads(read(p))
            with open(p, 'w', encoding='utf-8', newline='') as fh:
                fh.write(jsonfmt.dumps(data))
        with open(os.path.join(self.dir, 'teams.json'), 'w') as fh:
            fh.write('{"untouched": true}')

    def tearDown(self):
        self.tmp.cleanup()

    def test_apply_then_nothing_left(self):
        before = {n: read(os.path.join(self.dir, n)) for n in ('config.json', 'season.json', 'teams.json')}
        applied, _, backup = apply.apply_update(make_mod(), self.dir, mod_label='Test mod')
        self.assertTrue(applied)
        changes, _ = core.compare(make_mod(), core.Save(self.dir))
        self.assertFalse(by(changes, action=core.UPDATE))
        # backup holds the old files, teams.json is not touched
        for n in ('config.json', 'season.json'):
            self.assertEqual(read(os.path.join(backup, n)), before[n])
        self.assertEqual(read(os.path.join(self.dir, 'teams.json')), before['teams.json'])
        self.assertEqual(json.loads(read(os.path.join(backup, apply.MANIFEST)))['mod'], 'Test mod')

    def test_kept_values_and_save_only_fields_stay(self):
        apply.apply_update(make_mod(), self.dir)
        season = json.loads(read(os.path.join(self.dir, 'season.json')))
        cup = season['_mainCategoryBackup']['data']
        track1 = [c for c in cup['circuits'] if c['id'] == 1][0]
        self.assertEqual(track1['week'], 5)            # calendar kept
        self.assertEqual(track1['laps'], 120)          # mod value
        self.assertEqual(track1['lapRecords'], [1])    # career data kept
        self.assertEqual([c['id'] for c in cup['circuits']], [1, 2])  # circuit 3 not added, 2 not removed
        self.assertEqual(cup['sponsorsDatabase'][0]['contracts'], 3)
        config = json.loads(read(os.path.join(self.dir, 'config.json')))
        self.assertEqual(config['generalData']['gameplay']['raceRules']['fuelCapacity'], 80)  # Truck, being played

    def test_era_value_not_written(self):
        p = os.path.join(self.dir, 'season.json')
        season = json.loads(read(p))
        season['eraSchedule'] = {'proposals': [{'ruleType': 'points', 'status': 'passed', 'payload': {}}]}
        with open(p, 'w', encoding='utf-8') as fh:
            fh.write(jsonfmt.dumps(season))
        apply.apply_update(make_mod(), self.dir)
        cup = json.loads(read(p))['_mainCategoryBackup']['data']['general']['gameplay']
        self.assertEqual(cup['pointsSystem'], [10, 5])
        self.assertEqual(cup['globalPerformance'], 320)

    def test_refuses_when_save_changed_after_preview(self):
        preview = core.Save(self.dir)
        time.sleep(0.05)
        p = os.path.join(self.dir, 'config.json')
        os.utime(p, (time.time() + 5, time.time() + 5))
        with self.assertRaises(apply.SaveChanged):
            apply.apply_update(make_mod(), self.dir, expect_mtime=preview.mtime)
        self.assertEqual(apply.list_backups(self.dir), [])

    def test_restore(self):
        original = read(os.path.join(self.dir, 'config.json'))
        _, _, backup = apply.apply_update(make_mod(), self.dir)
        self.assertNotEqual(read(os.path.join(self.dir, 'config.json')), original)
        restored, undo = apply.restore_backup(self.dir, backup)
        self.assertIn('config.json', restored)
        self.assertEqual(read(os.path.join(self.dir, 'config.json')), original)
        self.assertTrue(os.path.isdir(undo))
        self.assertEqual(len(apply.list_backups(self.dir)), 2)

    def test_nothing_to_do_writes_nothing(self):
        apply.apply_update(make_mod(), self.dir)
        n = len(apply.list_backups(self.dir))
        applied, _, backup = apply.apply_update(make_mod(), self.dir)
        self.assertEqual((applied, backup), ([], None))
        self.assertEqual(len(apply.list_backups(self.dir)), n)


if __name__ == '__main__':
    unittest.main()
