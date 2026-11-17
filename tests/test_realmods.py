"""QA on real mods (dm-mods or DMSU_REAL_MODS): see tests/realdata.py. Skipped when none are found.

For every real mod:
  * a fresh career from the mod shows 0 updates, whichever category is played;
  * a career with changed values gets exactly those values back from Apply update, and the
    written files are then byte-identical to the fresh career (every other line untouched);
  * comparing stays fast enough for the window.
"""
import json
import os
import random
import shutil
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dm_save_update import apply, core  # noqa: E402
from tests import realdata  # noqa: E402

MODS = realdata.real_mods()
PROTECTED = (set().union(*core.ERA_RULE_KEYS.values()) | core.MAJOR_KEYS | core.GAME_KEYS
             | core.ERA_LIST_KEYS | core.META_KEYS)


def read(path):
    with open(path, encoding='utf-8', newline='') as fh:
        return fh.read()


def numeric_leaves(obj, path=(), skip=frozenset()):
    """(dict, key, path) for every number that sits directly in a dict, outside protected keys."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in skip:
                continue
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                yield obj, k, path + (k,)
            else:
                yield from numeric_leaves(v, path + (k,), skip)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            if isinstance(v, (dict, list)):
                yield from numeric_leaves(v, path + (i,), skip)


def entity_leaves(entities, keep):
    for ent in entities:
        for k, v in ent.items():
            if k not in keep and k not in core.META_KEYS and isinstance(v, (int, float)) and not isinstance(v, bool):
                yield ent, k


@unittest.skipUnless(MODS, 'no real mods: clone dm-mods next to this repository or set DMSU_REAL_MODS')
class RealModTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='dmsu-qa-')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _career(self, mod, name, play=None):
        return realdata.fresh_career(mod, os.path.join(self.tmp, name, 'solo', 'slot_1'), play)

    def test_fresh_career_has_no_updates(self):
        for name, path in MODS:
            mod = realdata.load(path)
            plays = [None] + [a.get('id') for a in (mod.get('additionalCategories') or [])][:1]
            for play in plays:
                with self.subTest(mod=name, playing=play or 'main'):
                    save = core.Save(self._career(mod, '%s-%s' % (name, play), play))
                    found, total = core.match_score(mod, save)
                    self.assertEqual(found, total, 'not every category of the mod is found in its own career')
                    changes, _ = core.compare(mod, save)
                    updates = [c for c in changes if c.action == core.UPDATE]
                    self.assertEqual([], [(c.category, c.section, c.item, c.path) for c in updates][:10])

    def test_apply_restores_changed_values_byte_for_byte(self):
        for name, path in MODS:
            with self.subTest(mod=name):
                mod = realdata.load(path)
                folder = self._career(mod, name)
                fresh = {f: read(os.path.join(folder, f)) for f in core.Save.FILES}
                expected = self._age_career(folder, seed=name)
                self.assertGreater(expected, 0)
                applied, _, backup = apply.apply_update(mod, folder, mod_label=name)
                self.assertEqual(len(applied), expected)
                self.assertTrue(backup and os.path.isdir(backup))
                for f in core.Save.FILES:
                    self.assertTrue(read(os.path.join(folder, f)) == fresh[f], '%s differs from the fresh career' % f)
                changes, _ = core.compare(mod, core.Save(folder))
                self.assertFalse([c for c in changes if c.action == core.UPDATE])

    def test_compare_is_fast(self):
        for name, path in MODS:
            with self.subTest(mod=name):
                mod = realdata.load(path)
                save = core.Save(self._career(mod, name))
                t0 = time.perf_counter()
                core.compare(mod, save)
                self.assertLess(time.perf_counter() - t0, 3.0)

    def _age_career(self, folder, seed):
        """Change numbers in the save as an older mod version would have had them. Returns how many."""
        cfg_path, sea_path = os.path.join(folder, 'config.json'), os.path.join(folder, 'season.json')
        with open(cfg_path, encoding='utf-8') as fh:
            config = json.load(fh)
        with open(sea_path, encoding='utf-8') as fh:
            season = json.load(fh)
        rnd = random.Random(seed)
        picks = list(numeric_leaves(config['generalData'], skip=PROTECTED))
        picks = rnd.sample(picks, min(15, len(picks)))
        entities = []
        for section, keep in (('circuits', core.CIRCUIT_KEEP), ('sponsorsDatabase', {'id'})):
            entities += list(entity_leaves(season.get(section) or [], keep))
        for add in season.get('additionalCategories') or []:
            entities += list(entity_leaves((add.get('data') or {}).get('circuits') or [], core.CIRCUIT_KEEP))
        picks += [(d, k, None) for d, k in rnd.sample(entities, min(15, len(entities)))]
        for d, k, _ in picks:
            v = d[k]
            d[k] = v + 1 if isinstance(v, int) else round(v * 1.5 + 0.25, 6)
        from dm_save_update import jsonfmt
        for p, data in ((cfg_path, config), (sea_path, season)):
            with open(p, 'w', encoding='utf-8', newline='') as fh:
                fh.write(jsonfmt.dumps(data))
        return len(picks)


if __name__ == '__main__':
    unittest.main()
