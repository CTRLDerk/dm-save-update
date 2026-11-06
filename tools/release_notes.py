"""Release text for a tag: the version's CHANGELOG section plus the install notes.

    python tools/release_notes.py v0.2.0 [sha256 of the exe] > body.md

Fails when the tag does not match dm_save_update.__version__ or the CHANGELOG has no section for it.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from dm_save_update import __version__  # noqa: E402


def section(version):
    with open(os.path.join(ROOT, 'CHANGELOG.md'), encoding='utf-8') as fh:
        text = fh.read()
    m = re.search(r'^## %s\b[^\n]*\n(.*?)(?=^## |\Z)' % re.escape(version), text, re.S | re.M)
    return m.group(1).strip() if m else None


def main(argv):
    tag = argv[1]
    version = tag.lstrip('v')
    if version != __version__:
        sys.exit('Tag %s does not match __version__ %s' % (tag, __version__))
    changes = section(version)
    if not changes:
        sys.exit('CHANGELOG.md has no section "## %s"' % version)
    with open(os.path.join(ROOT, '.github', 'release-install.md'), encoding='utf-8') as fh:
        install = fh.read().strip()
    parts = [install, '## What is new in %s' % version, changes]
    if len(argv) > 2:
        parts.append('SHA-256 of `DM-Save-Update.exe`: `%s`' % argv[2].strip().lower())
    sys.stdout.write('\n\n'.join(parts) + '\n')


if __name__ == '__main__':
    main(sys.argv)
