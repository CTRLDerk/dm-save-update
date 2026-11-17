"""Finding saves and Workshop mods (steam.py) on a fake Steam folder."""
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dm_save_update import steam  # noqa: E402


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(data if isinstance(data, str) else json.dumps(data))


class SteamTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='dmsu-steam-')
        self.lib = os.path.join(self.tmp, '.steam', 'steam')  # ~/.steam/steam on Linux
        self.other = os.path.join(self.tmp, 'Other Library')
        os.makedirs(os.path.join(self.other, 'steamapps'))
        write(os.path.join(self.lib, 'steamapps', 'libraryfolders.vdf'),
              '"libraryfolders"\n{\n "0" { "path" "%s" }\n "1" { "path" "%s" }\n "2" { "path" "%s" }\n}\n'
              % (self.lib.replace('\\', '\\\\'), self.other.replace('\\', '\\\\'),
                 os.path.join(self.tmp, 'gone').replace('\\', '\\\\')))
        self.saves = os.path.join(self.other, 'steamapps', 'common', 'Delta Manager', 'sauvegardes')
        self.workshop = os.path.join(self.lib, 'steamapps', 'workshop', 'content', steam.APP_ID)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_libraries_from_libraryfolders_vdf(self):
        with mock.patch.object(steam.sys, 'platform', 'linux'), \
                mock.patch.object(steam.os.path, 'expanduser', return_value=self.tmp):
            libs = steam.steam_libraries()
        self.assertIn(os.path.normpath(self.other), libs)
        self.assertNotIn(os.path.normpath(os.path.join(self.tmp, 'gone')), libs)

    def test_find_folders_in_any_library(self):
        os.makedirs(self.saves)
        os.makedirs(self.workshop)
        with mock.patch.object(steam, 'steam_libraries', return_value=[self.lib, self.other]):
            self.assertEqual(steam.find_saves_dir(), self.saves)
            self.assertEqual(steam.find_workshop_dir(), self.workshop)
        with mock.patch.object(steam, 'steam_libraries', return_value=[]):
            self.assertEqual((steam.find_saves_dir(), steam.find_workshop_dir()), ('', ''))

    def test_list_saves_newest_first(self):
        write(os.path.join(self.saves, 'solo', 'slot_1', 'config.json'), {})
        write(os.path.join(self.saves, 'solo', 'slot_1', 'meta.json'),
              {'displayName': 'Penske', 'currentSeason': 2026, 'currentWeek': 4, 'savedAt': '2026-01-01'})
        write(os.path.join(self.saves, 'spectator', 'slot_2', 'config.json'), {})
        write(os.path.join(self.saves, 'spectator', 'slot_2', 'meta.json'), {'teamName': 'Ganassi', 'savedAt': '2026-05-01'})
        write(os.path.join(self.saves, 'solo', 'slot_3', 'config.json'), {})
        write(os.path.join(self.saves, 'solo', 'slot_3', 'meta.json'), '{broken')
        os.makedirs(os.path.join(self.saves, 'solo', 'slot_4'))  # no config.json: not a save
        os.makedirs(os.path.join(self.saves, 'solo', 'other'))
        saves = steam.list_saves(self.saves)
        self.assertEqual([(s['mode'], s['slot']) for s in saves],
                         [('spectator', 'slot_2'), ('solo', 'slot_1'), ('solo', 'slot_3')])
        self.assertEqual(saves[1]['label'], 'solo slot_1 - Penske, 2026 week 4')
        self.assertEqual(saves[2]['team'], '?')
        self.assertEqual(steam.list_saves(os.path.join(self.tmp, 'nothing')), [])

    def test_workshop_mods_by_name(self):
        write(os.path.join(self.workshop, '111', 'mod.json'), '{"modName": "Oval \\"Series\\"", "x": "%s"}' % ('a' * 500))
        write(os.path.join(self.workshop, '111', 'small.json'), {'modName': 'wrong file'})
        write(os.path.join(self.workshop, '222', 'slot.json'), {'name': 'no modName'})
        os.makedirs(os.path.join(self.workshop, '333'))  # no json
        write(os.path.join(self.workshop, 'readme.txt'), 'x')
        mods = steam.list_workshop_mods(self.workshop)
        self.assertEqual([m['item'] for m in mods], ['111', '222'])
        self.assertEqual(mods[0]['label'], 'Oval "Series"  (Workshop 111)')
        self.assertTrue(mods[0]['path'].endswith('mod.json'))
        self.assertEqual(mods[1]['label'], 'slot.json  (Workshop 222)')
        self.assertEqual(steam.peek_mod_name(os.path.join(self.tmp, 'missing.json')), '')
        self.assertEqual(steam.list_workshop_mods(''), [])


if __name__ == '__main__':
    unittest.main()
