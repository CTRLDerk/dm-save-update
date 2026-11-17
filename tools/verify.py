"""Every quality check of DM Save Update in one step, with only a summary on screen.

    python tools/verify.py            all checks
    python tools/verify.py --quick    skip the window check (no Tk needed)
    python tools/verify.py --strict   a check that cannot run (no ruff, coverage, Node.js or real mods) fails

Full output: build/verify.log. Exit code 0 = everything that ran is in order.

Optional extras, each makes the check stronger:
  pip install ruff coverage         lint + coverage threshold (pyproject.toml)
  Node.js on PATH                   jsonfmt is compared with JSON.stringify, what the game writes with
  ../dm-mods clone                  real mods: fresh career = 0 updates, apply restores byte for byte
                                    (or DMSU_REAL_MODS=<folder with slot_N.json files>)
"""
import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
LOG = os.path.join(ROOT, 'build', 'verify.log')


class Run:
    def __init__(self, strict):
        self.strict, self.failed = strict, []
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        self.log = open(LOG, 'w', encoding='utf-8')

    def step(self, name, cmd, env=None):
        self.log.write('\n== %s\n$ %s\n' % (name, ' '.join(cmd)))
        self.log.flush()
        t0 = time.time()
        res = subprocess.run(cmd, cwd=ROOT, stdout=self.log, stderr=subprocess.STDOUT,
                             env=dict(os.environ, **(env or {})))
        took = ' (%.1fs)' % (time.time() - t0)
        if res.returncode == 0:
            print('OK    %s%s' % (name, took))
        else:
            print('FAIL  %s%s  -> build/verify.log' % (name, took))
            self.failed.append(name)

    def skip(self, name, why):
        if self.strict:
            print('FAIL  %s: %s (--strict)' % (name, why))
            self.failed.append(name)
        else:
            print('SKIP  %s: %s' % (name, why))
        self.log.write('\n== %s\nskipped: %s\n' % (name, why))


def has(module):
    return importlib.util.find_spec(module) is not None


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--quick', action='store_true', help='skip the window check')
    ap.add_argument('--strict', action='store_true', help='fail when a check cannot run')
    args = ap.parse_args(argv)
    run = Run(args.strict)
    py = sys.executable

    from dm_save_update import __version__
    from tests import realdata
    print('DM Save Update %s - Python %s' % (__version__, sys.version.split()[0]))

    ruff = shutil.which('ruff')
    if ruff:
        run.step('lint (ruff)', [ruff, 'check', '.'])
    elif has('ruff'):
        run.step('lint (ruff)', [py, '-m', 'ruff', 'check', '.'])
    else:
        run.skip('lint', 'ruff not installed (pip install ruff)')

    mods = realdata.real_mods()
    print('      real mods: %s' % (', '.join(n for n, _ in mods) if mods else
                                   'none (clone dm-mods next to this repository for the real-mod tests)'))
    print('      Node.js:   %s' % (realdata.node() or 'not found (jsonfmt is not compared with JSON.stringify)'))
    if not mods:
        run.skip('real-mod tests', 'no real mods found')
    if not realdata.node():
        run.skip('JSON.stringify reference', 'Node.js not found')

    unittest_cmd = ['-m', 'unittest', 'discover', '-s', 'tests']
    if has('coverage'):
        run.step('unit tests + coverage', [py, '-m', 'coverage', 'run'] + unittest_cmd)
        run.step('coverage threshold (pyproject.toml)', [py, '-m', 'coverage', 'report'])
    else:
        run.step('unit tests', [py] + unittest_cmd)
        run.skip('coverage threshold', 'coverage not installed (pip install coverage)')

    run.step('release text for %s' % __version__,
             [py, os.path.join('tools', 'release_notes.py'), 'v' + __version__,
              '--out', os.path.join('build', 'release-check.md')])
    run.step('CLI --version', [py, 'update.py', '--save', '.', '--version'])

    if args.quick:
        print('SKIP  window check: --quick')
    elif not has('tkinter'):
        run.skip('window check', 'tkinter not available')
    else:
        run.step('window check', [py, '-m', 'tests.gui_check'])

    run.log.close()
    print('\n%s' % ('All checks passed.' if not run.failed else 'Failed: ' + ', '.join(run.failed)))
    return 1 if run.failed else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
