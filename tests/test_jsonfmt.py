"""jsonfmt writes JSON exactly as Delta Manager does (JSON.stringify). Checked against Node.js when it is installed."""
import json
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dm_save_update import jsonfmt  # noqa: E402
from tests import realdata  # noqa: E402


class NumberTest(unittest.TestCase):
    def test_numbers_like_javascript(self):
        cases = [  # a list: in a dict True/1 and 0/-0.0 would be the same key
            (0, '0'), (-0.0, '0'), (1.0, '1'), (-2.5, '-2.5'), (7.5e-05, '0.000075'), (1e-07, '1e-7'),
            (1.5e-07, '1.5e-7'), (1e20, '100000000000000000000'), (1e21, '1e+21'), (1.2345e+22, '1.2345e+22'),
            (5e-324, '5e-324'), (float('nan'), 'null'), (float('inf'), 'null'), (True, 'true'), (False, 'false'),
            (12345678901234567890, '12345678901234567890'),
        ]
        for value, text in cases:
            with self.subTest(value=value):
                self.assertEqual(jsonfmt.js_number(value), text)

    def test_layout(self):
        obj = {'a': [], 'b': {}, 'c': [1, {'d': None}], 'é': 'ü"'}
        self.assertEqual(jsonfmt.dumps(obj), '{\n  "a": [],\n  "b": {},\n  "c": [\n    1,\n    {\n      "d": null\n'
                                             '    }\n  ],\n  "é": "ü\\""\n}')
        with self.assertRaises(TypeError):
            jsonfmt.dumps({1, 2})

    def test_dumps_like_keeps_the_file_style(self):
        obj = {'a': [1, 2]}
        self.assertEqual(jsonfmt.detect_indent('{\n    "a": 1\n}'), 4)
        self.assertEqual(jsonfmt.dumps_like(obj, '{"x":1}'), '{"a":[1,2]}')
        self.assertEqual(jsonfmt.dumps_like(obj, '{\n  "x": 1\n}'), jsonfmt.dumps(obj))


@unittest.skipUnless(realdata.node(), 'Node.js not found (set DMSU_NODE or put node on PATH)')
class NodeReferenceTest(unittest.TestCase):
    def assertLikeNode(self, text, label):
        ours = jsonfmt.dumps(json.loads(text))
        ref = realdata.js_stringify(text)
        if ours != ref:
            a, b = ours.splitlines(), ref.splitlines()
            first = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
            self.fail('%s: line %d differs from JSON.stringify\n  ours: %r\n  node: %r'
                      % (label, first + 1, a[first] if first < len(a) else '<end>', b[first] if first < len(b) else '<end>'))

    def test_random_numbers(self):
        rnd = random.Random(7)
        values = []
        for _ in range(5000):
            values += [rnd.random() * 10 ** rnd.randint(-30, 30), -rnd.random() / 10 ** rnd.randint(0, 12),
                       round(rnd.random() * 1e6) / 1e3, rnd.randint(-10 ** 15, 10 ** 15), -0.0]
        self.assertLikeNode(json.dumps(values), 'random numbers')

    def test_text(self):
        self.assertLikeNode(json.dumps(['é ü ß 中文 🏁', '   ', 'tab\t"quote"\\', '\x00\x1f\x7f'],
                                       ensure_ascii=False), 'text')

    def test_real_mods(self):
        if not realdata.real_mods():
            self.skipTest('no real mods: clone dm-mods next to this repository or set DMSU_REAL_MODS')
        for name, path in realdata.real_mods():
            with self.subTest(mod=name):
                with open(path, encoding='utf-8') as fh:
                    self.assertLikeNode(fh.read(), name)


if __name__ == '__main__':
    unittest.main()
