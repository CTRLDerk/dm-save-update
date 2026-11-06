"""DM Save Update - preview what a new mod version would change in a Delta Manager career save.

Without arguments the window opens. On the command line:

    python update.py --mod <mod.json> --save <sauvegardes/solo/slot_N> [--report report.txt]
                     [--overwrite-era] [--overwrite-major]

Version 0.1 only reads: the save is never written.
"""
import argparse
import sys

from dm_save_update import __version__, core


def cli(argv):
    ap = argparse.ArgumentParser(prog='DM-Save-Update', description=__doc__.split('\n')[0])
    ap.add_argument('--mod', required=True, help='mod file (Workshop mod.json or a slot_N.json)')
    ap.add_argument('--save', required=True, help='save folder, e.g. ...\\sauvegardes\\solo\\slot_1')
    ap.add_argument('--report', help='write the preview to this file instead of the screen')
    ap.add_argument('--overwrite-era', action='store_true', help='also overwrite rules changed by era votes')
    ap.add_argument('--overwrite-major', action='store_true', help='also overwrite values drawn at a major regulation')
    ap.add_argument('--version', action='version', version=__version__)
    args = ap.parse_args(argv)
    mod = core.load_json(args.mod)
    save = core.Save(args.save)
    changes, notes = core.compare(mod, save, core.Options(args.overwrite_era, args.overwrite_major))
    text = core.report_text(changes, notes, args.mod, args.save)
    if args.report:
        with open(args.report, 'w', encoding='utf-8') as fh:
            fh.write(text)
    else:
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
