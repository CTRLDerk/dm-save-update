"""Prepare a release: version number, changelog heading and every check in one step.

    python tools/release.py patch|minor|major|X.Y.Z [--dry-run] [--no-verify]

1. The "## Unreleased" section of CHANGELOG.md becomes "## X.Y.Z" (a new empty "## Unreleased" goes above it).
2. __version__ in dm_save_update/__init__.py becomes X.Y.Z.
3. python tools/verify.py --quick runs (the release text for X.Y.Z is part of it).
4. The git commands to commit, merge and tag are printed. Nothing is committed, pushed or tagged.

Refused when "## Unreleased" is missing or empty, or when X.Y.Z is not higher than the current version.
"""
import argparse
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHANGELOG = os.path.join(ROOT, 'CHANGELOG.md')
INIT = os.path.join(ROOT, 'dm_save_update', '__init__.py')
UNRELEASED = '## Unreleased'


def read(path):
    with open(path, encoding='utf-8', newline='') as fh:
        return fh.read()


def write(path, text):
    with open(path, 'w', encoding='utf-8', newline='') as fh:
        fh.write(text)


def parse(version):
    m = re.fullmatch(r'(\d+)\.(\d+)\.(\d+)', version)
    if not m:
        raise ValueError('not a version X.Y.Z: %s' % version)
    return tuple(int(x) for x in m.groups())


def next_version(current, bump):
    major, minor, patch = parse(current)
    if bump == 'major':
        return '%d.0.0' % (major + 1)
    if bump == 'minor':
        return '%d.%d.0' % (major, minor + 1)
    if bump == 'patch':
        return '%d.%d.%d' % (major, minor, patch + 1)
    if parse(bump) <= parse(current):
        raise ValueError('%s is not higher than the current version %s' % (bump, current))
    return bump


def current_version():
    m = re.search(r'__version__ = "([^"]+)"', read(INIT))
    return m.group(1)


def release_changelog(text, version):
    """CHANGELOG text with "## Unreleased" renamed to "## version" and a new empty Unreleased on top."""
    m = re.search(r'^## Unreleased[ \t]*\r?\n(.*?)(?=^## |\Z)', text, re.S | re.M)
    if not m:
        raise ValueError('CHANGELOG.md has no "%s" section: write the changes there first' % UNRELEASED)
    if not m.group(1).strip():
        raise ValueError('"%s" in CHANGELOG.md is empty: nothing to release' % UNRELEASED)
    if re.search(r'^## %s\b' % re.escape(version), text, re.M):
        raise ValueError('CHANGELOG.md already has a section "## %s"' % version)
    nl = '\r\n' if '\r\n' in text else '\n'
    heading = UNRELEASED + nl + nl + '## ' + version + nl
    return text[:m.start()] + heading + text[m.start(1):]


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('version', help='patch, minor, major or X.Y.Z')
    ap.add_argument('--dry-run', action='store_true', help='only show what would change')
    ap.add_argument('--no-verify', action='store_true', help='do not run tools/verify.py')
    args = ap.parse_args(argv)
    current = current_version()
    try:
        version = next_version(current, args.version)
        changelog = release_changelog(read(CHANGELOG), version)
    except ValueError as exc:
        sys.exit('release: %s' % exc)
    print('Release %s -> %s' % (current, version))
    if args.dry_run:
        print('(dry run: nothing written)')
        return 0
    write(CHANGELOG, changelog)
    write(INIT, re.sub(r'__version__ = "[^"]+"', '__version__ = "%s"' % version, read(INIT)))
    print('Updated CHANGELOG.md and dm_save_update/__init__.py')
    if not args.no_verify:
        res = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'verify.py'), '--quick'], cwd=ROOT)
        if res.returncode:
            print('\nverify.py failed: fix it before releasing (the version and changelog stay changed).')
            return res.returncode
    print('\nNext:\n'
          '  git commit -am "Release %(v)s"\n'
          '  (pull request, merge to main)\n'
          '  git checkout main && git pull\n'
          '  git tag v%(v)s && git push origin v%(v)s    # builds the exe and publishes the Release' % {'v': version})
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
