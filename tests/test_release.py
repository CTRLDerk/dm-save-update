"""tools/release.py: version bump and changelog heading."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools'))
import release  # noqa: E402


class ReleaseTest(unittest.TestCase):
    def test_next_version(self):
        self.assertEqual(release.next_version('0.3.0', 'patch'), '0.3.1')
        self.assertEqual(release.next_version('0.3.4', 'minor'), '0.4.0')
        self.assertEqual(release.next_version('0.3.4', 'major'), '1.0.0')
        self.assertEqual(release.next_version('0.3.4', '0.10.0'), '0.10.0')
        for bad in ('0.3.4', '0.3.3', '1.0', 'v1.0.0'):
            with self.assertRaises(ValueError):
                release.next_version('0.3.4', bad)

    def test_changelog(self):
        text = '# Changelog\n\n## Unreleased\n- fix\n\n## 0.3.0\nold\n'
        self.assertEqual(release.release_changelog(text, '0.3.1'),
                         '# Changelog\n\n## Unreleased\n\n## 0.3.1\n- fix\n\n## 0.3.0\nold\n')
        crlf = text.replace('\n', '\r\n')
        self.assertIn('## 0.3.1\r\n- fix', release.release_changelog(crlf, '0.3.1'))
        for bad in ('# Changelog\n\n## 0.3.0\nold\n', '# Changelog\n\n## Unreleased\n\n## 0.3.0\nold\n',
                    '## Unreleased\n- x\n## 0.3.1\n'):
            with self.assertRaises(ValueError):
                release.release_changelog(bad, '0.3.1')

    def test_release_notes_ignore_unreleased(self):
        import release_notes
        self.assertIsNone(release_notes.section('Unreleased-does-not-exist'))


if __name__ == '__main__':
    unittest.main()
