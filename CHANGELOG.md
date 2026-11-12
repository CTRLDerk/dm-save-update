# Changelog

## 0.3.0
New look, same workings.

- The window now has the DM Save Card style: dark top bar, red/green slash, chequered strip, panels with `//` headings, Barlow fonts (bundled in the exe).
- Saves are a list on the left, grouped by solo, co-op and spectator, with team, slot, season and week. The chosen save stays chosen after **Reload**.
- A red bar at the top shows the chosen save and the mod, with tiles for updates, kept and skipped after **Show changes**.
- The folders are under **Folders** at the bottom left; **…** replaces **Browse…**.
- **Show kept and skipped** moved to the **Changes** panel, next to a colour legend (update, kept in gold, skipped in grey).
- Dark title bar on Windows 10 and 11.

## 0.2.0
First public release.

**Show changes (preview, writes nothing)**
- Finds the Delta Manager save folder and the Steam Workshop folder by itself, on every Steam library; **Browse…** to point elsewhere. **Other mod file…** compares a local mod file (`resources\mods\slot_N.json`).
- Lists Workshop mods by name and saves by team, season and week (solo, co-op and spectator), newest save first.
- Compares the settings, circuits and sponsor pool of every category of the mod with the save, also the categories you are not playing.
- Lists such as tyres and concepts show the exact field that differs, e.g. `dryTyres[General].durability`.
- Kept by default: rules changed by era votes in your career and values drawn again at a major regulation (tick boxes to overwrite them anyway).
- Always kept: what the game sets itself at career start (`regulations.baseLimits`, the circuit name in `name`; the mod's circuit name is compared with `officialName`), the calendar (week, event type, sprint weekend), and everything that is your career (drivers, teams, staff, contracts, results, history).
- New circuits and sponsors are listed but not added.
- Image paths (logos, flags) count as equal when they point to the same file: the game turns `./sponsors/x.png` into an absolute path when it loads a save.
- A save of another mod is recognised: nothing is compared.
- **Save report…** writes the list to a text file.

**Apply update**
- Writes the updates from the preview into `config.json` and `season.json`, after a confirmation. Refused when the save changed after the preview (for example because the game saved it).
- Backup first in `<slot>\_dmsu_backup_<date>_<time>\`; **Restore backup…** puts one back and backs up the current files first.
- Files are written the way the game writes them: every line that is not updated stays byte-identical.
- Afterwards the preview runs again and should show no updates left.

**Command line:** `--report`, `--apply`, `--list-backups`, `--restore`.

Checked on real saves: a new GTWC career shows 0 updates; older GTWC careers show 65–70 circuit updates that match the mod's changelog; an AOS save backup shows the changes in all three series; applying and restoring a copy of a GTWC career gives 0 updates afterwards and the original files back byte for byte. A GTWC spectator career was updated (70 circuit updates), loaded and saved again in the game: the new values stayed, week, results and teams unchanged.
