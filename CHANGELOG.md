# Changelog

## 0.2.0
- **Apply update**: writes the previewed updates into `config.json` and `season.json`. Only after a preview, with a confirmation, and refused when the save changed after the preview.
- Backup first in `<slot>\_dmsu_backup_<date>_<time>\` (config, season, meta + manifest); **Restore backup…** puts one back and backs up the current files first.
- Files are written the way the game writes them (JSON.stringify, 2 spaces): every line that is not updated stays byte-identical. Written to a temporary file and checked before it replaces the save.
- After applying, the preview runs again and should show no updates left.
- Command line: `--apply`, `--list-backups`, `--restore`.
- Checked on a copy of a GTWC career (solo slot_1): 65 updates applied, all in circuits; afterwards 0 updates; restore gives the original files byte for byte.

## 0.1.0 (preview)
- Window: finds the save folder and the Workshop folder of Delta Manager (app 4247780) on every Steam library; Browse buttons to change them.
- Lists Workshop mods (name read from the mod file) and career saves (team, season, week), newest save first.
- Compares category settings, circuits and the sponsor pool of every category, also when another category than the main one is being played.
- Keeps the save value for rules adopted by era votes and for values drawn at a major regulation; both can be overwritten with a tick box.
- New circuits and sponsors are listed but not added.
- Fields the game sets itself at career start are kept: `regulations.baseLimits`; a circuit's mod name is compared with the save's `officialName` (the game puts the track name in `name`).
- Saves of another mod are recognised (no category in common).
- Lists such as tyres and concepts show the field that differs (`dryTyres[General].durability`).
- Report as text file; command line with `--report`.
- Fix: the chosen mod or save was sometimes not found ("Choose a mod and a save first"); labels no longer contain backslashes and the selection is tracked by the tool itself. A mod file picked by hand stays in the list after Reload.
- Reads only. Nothing is written to the save.
- Windows exe built by GitHub Actions (PyInstaller), with a smoke test of the exe.
