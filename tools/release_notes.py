"""Release text for a tag: the version's CHANGELOG section plus the install notes.

    python tools/release_notes.py v0.2.0 [--sha256 HASH] [--out body.md]

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
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('tag')
    ap.add_argument('--sha256')
    ap.add_argument('--out', help='write UTF-8 to this file (the Windows console cannot show every character)')
    args = ap.parse_args(argv[1:])
    tag = args.tag
    version = tag.lstrip('vV')  # V1.0.0 is accepted too
    if version != __version__:
        sys.exit('Tag %s does not match __version__ %s' % (tag, __version__))
    changes = section(version)
    if not changes:
        sys.exit('CHANGELOG.md has no section "## %s"' % version)
    with open(os.path.join(ROOT, '.github', 'release-install.md'), encoding='utf-8') as fh:
        install = fh.read().strip()
    parts = [install, '## What is new in %s' % version, changes]
    if args.sha256:
        parts.append('SHA-256 of `DM-Save-Update.exe`: `%s`' % args.sha256.strip().lower())
    text = '\n\n'.join(parts) + '\n'
    if args.out:
        with open(args.out, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
    else:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stdout.write(text)


if __name__ == '__main__':
    main(sys.argv)
