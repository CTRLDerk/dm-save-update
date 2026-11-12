# DM Save Update

Bring a running Delta Manager career up to date with the newest version of a mod, without losing your progress.

When a mod author updates a mod on the Steam Workshop, careers that were already started keep the old settings: the game copies the mod into the save when the career starts. This tool compares the new mod with your save, shows exactly which settings would change, and writes them into the save when you press **Apply update**. A backup is made first.

## Download and start

1. Download `DM-Save-Update.exe` from the [Releases](../../releases) page.
2. **Chrome or Edge blocks the download?** Open the downloads list (`Ctrl+J`) and choose **Keep**. Double-click the exe; if **Windows protected your PC** appears, click **More info → Run anyway**. The program is new and not signed, so browsers and Windows do not know it yet. The SHA-256 of the exe is listed with every release.
3. The tool looks for your Steam libraries and fills in both folders by itself:
   - **Save folder:** `...\steamapps\common\Delta Manager\sauvegardes`
   - **Workshop folder:** `...\steamapps\workshop\content\4247780` (Workshop mods are stored here, not in the game's `resources\mods` folder)

   Both are shown under **Folders** at the bottom left. If a folder is not found, press **…** next to it and point to it.
4. Pick the **save** in the list on the left, choose the **mod** (new version) and press **Show changes**. Nothing is written yet.
5. Close Delta Manager, or go back to its main menu, so the game does not overwrite the save afterwards.
6. Press **Apply update** and confirm. The list is refreshed and should show no updates left.
7. Start the game and load the save.

## Backup and restore

Before writing, the tool copies `config.json`, `season.json` and `meta.json` to a folder inside the save:
`...\sauvegardes\solo\slot_N\_dmsu_backup_<date>_<time>\`. Only `config.json` and `season.json` are written; every other file of the save (drivers, teams, career, history) is never opened for writing.

**Restore backup…** lists these backups and puts one back. The files from before the restore are backed up as well, so a restore can be undone too.

The update is refused when the save was written after the preview (for example because the game saved it): press **Show changes** again.

Running from source instead: Python 3.8 or newer, then `python update.py`.

## What is compared

| Part of the mod | Compared | How |
|---|---|---|
| Category settings (`generalData`: rules, economy, development, regulations, …) | yes | field by field, for every category (also the ones you are not playing) |
| Circuits and reserve circuits | yes | by circuit id; week, event type, sprint weekend and testing circuit stay as in the save |
| Sponsor pool (sponsors, naming sponsors) | yes | by sponsor id |
| New circuits or sponsors | listed, not added | adding them would change the calendar or sponsor market of a running career |
| Drivers, teams, staff, contracts, results, standings, history | **never** | that is your career |
| The active regulation of the current season | **never** | the game keeps it separately; changed regulation values count from the next regulation change |
| Fields the game sets itself at career start (`regulations.baseLimits`, a circuit's `name`) | **never** | the mod's circuit name is compared with the save's `officialName` |

### Settings the career itself changed

Some settings change during a career. By default the tool keeps the save value for them:

- **Era votes.** Rules adopted by a team vote (points, tyres, fuel, DRS, …) keep the voted value. Tick *Also overwrite rules changed by era votes* to replace them anyway.
- **Major regulations.** Values the game draws again at a major regulation (global performance, development bonuses, regulation aggressiveness) keep the save value once a major regulation has happened. Tick *Also overwrite values drawn at a major regulation* to replace them anyway.

A save from another mod is recognised: if none of the mod's categories are in the save, nothing is compared.

## Command line

```
DM-Save-Update.exe --mod <mod.json> --save <...\sauvegardes\solo\slot_1> --report report.txt
python update.py   --mod <mod.json> --save <...\sauvegardes\solo\slot_1> [--overwrite-era] [--overwrite-major] [--apply]
python update.py   --save <...\slot_1> --list-backups
python update.py   --save <...\slot_1> --restore <...\slot_1\_dmsu_backup_...>
```

Without `--apply` nothing is written.

The exe has no console window, so use `--report` with it.

## For mod authors

Ask players to run **Show changes** after an update and to send the report (*Save report…*) if something looks wrong. A local slot file (`resources\mods\slot_N.json`) can be compared too: *Other mod file…*.

## Development

```
python -m unittest discover -s tests -v
```

Every push builds the Windows exe on GitHub Actions (artifact `DM-Save-Update-exe`).

**Release:** set `__version__` in `dm_save_update/__init__.py`, add a `## X.Y.Z` section to `CHANGELOG.md`, merge to `main`, then push a tag `vX.Y.Z`. The workflow builds the exe, writes the release text (`tools/release_notes.py`: install notes from `.github/release-install.md` + the changelog section + SHA-256) and publishes the Release with the exe and its `.sha256` file. It refuses a tag that does not match `__version__`.

Fonts: Barlow and Barlow Condensed (SIL Open Font License 1.1, `dm_save_update/fonts/OFL-Barlow.txt`), bundled in the exe.

License: MIT.
