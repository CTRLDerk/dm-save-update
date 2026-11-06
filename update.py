"""DM Save Update - bring a Delta Manager career save up to date with a new mod version.

Without arguments the window opens. On the command line:

    python update.py --mod <mod.json> --save <sauvegardes/solo/slot_N> [--report report.txt]
                     [--overwrite-era] [--overwrite-major] [--apply]
    python update.py --save <sauvegardes/solo/slot_N> --list-backups
    python update.py --save <sauvegardes/solo/slot_N> --restore <backup folder>

Without --apply nothing is written. With --apply a backup is made in the save folder first.
"""
import argparse
import sys

from dm_save_update import __version__, apply, core


def cli(argv):
    ap = argparse.ArgumentParser(prog='DM-Save-Update', description=__doc__.split('\n')[0])
    ap.add_argument('--mod', help='mod file (Workshop mod.json or a slot_N.json)')
    ap.add_argument('--save', required=True, help='save folder, e.g. ...\\sauvegardes\\solo\\slot_1')
    ap.add_argument('--report', help='write the preview to this file instead of the screen')
    ap.add_argument('--overwrite-era', action='store_true', help='also overwrite rules changed by era votes')
    ap.add_argument('--overwrite-major', action='store_true', help='also overwrite values drawn at a major regulation')
    ap.add_argument('--apply', action='store_true', help='write the update (a backup is made first)')
    ap.add_argument('--list-backups', action='store_true', help='list the backups in the save folder')
    ap.add_argument('--restore', metavar='BACKUP', help='put a backup folder back')
    ap.add_argument('--version', action='version', version=__version__)
    args = ap.parse_args(argv)
    out = []
    if args.list_backups:
        for folder, info in apply.list_backups(args.save):
            out.append('%s  %s' % (folder, info.get('mod', '')))
        return _emit('\n'.join(out) + '\n', args.report)
    if args.restore:
        restored, undo = apply.restore_backup(args.save, args.restore)
        return _emit('Restored %s. Files from before the restore: %s\n' % (', '.join(restored), undo), args.report)
    if not args.mod:
        ap.error('--mod is needed')
    mod = core.load_json(args.mod)
    opts = core.Options(args.overwrite_era, args.overwrite_major)
    if args.apply:
        applied, _, backup = apply.apply_update(mod, args.save, opts, args.mod)
        out.append('Applied %d updates. Backup: %s\n\n' % (len(applied), backup or '- (nothing to do)'))
    changes, notes = core.compare(mod, core.Save(args.save), opts)
    text = ''.join(out) + core.report_text(changes, notes, args.mod, args.save)
    return _emit(text, args.report)


def _emit(text, report):
    if report:
        with open(report, 'w', encoding='utf-8') as fh:
            fh.write(text)
    elif sys.stdout:  # None in the windowed exe
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # Windows console: cp1252
        except (AttributeError, ValueError):
            pass
        sys.stdout.write(text)
    return 0


def main():
    if len(sys.argv) > 1:
        return cli(sys.argv[1:])
    from dm_save_update import gui
    gui.main()
    return 0


if __name__ == '__main__':
    sys.exit(main())
