# DM Save Update

Bring a running Delta Manager career up to date with the newest version of a mod, without losing your progress.

When a mod author updates a mod on the Steam Workshop, careers that were already started keep the old settings: the game copies the mod into the save when the career starts. This tool compares the new mod with your save and shows exactly which settings would change.

> **Version 0.1 is a preview.** It only reads. Nothing is written to your save yet. Applying the update (with an automatic backup) comes in the next version, after the preview has been checked on real saves.

## Download and start

1. Download `DM-Save-Update.exe` from the [Releases](../../releases) page.
2. Double-click it. Windows SmartScreen may warn because the program is not signed: choose *More info → Run anyway*.
3. The tool looks for your Steam libraries and fills in both folders by itself:
   - **Save folder:** `...\steamapps\common\Delta Manager\sauvegardes`
   - **Workshop folder:** `...\steamapps\workshop\content\4247780` (Workshop mods are stored here, not in the game's `resources\mods` folder)

   If a folder is not found, press **Browse…** and point to it.
4. Choose the **mod** (new version) and the **save**, and press **Show changes**.

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

### Settings the career itself changed

Some settings change during a career. By default the tool keeps the save value for them:

- **Era votes.** Rules adopted by a team vote (points, tyres, fuel, DRS, …) keep the voted value. Tick *Also overwrite rules changed by era votes* to replace them anyway.
- **Major regulations.** Values the game draws again at a major regulation (global performance, development bonuses, regulation aggressiveness) keep the save value once a major regulation has happened. Tick *Also overwrite values drawn at a major regulation* to replace them anyway.

A save from another mod is recognised: if none of the mod's categories are in the save, nothing is compared.

## Command line

```
DM-Save-Update.exe --mod <mod.json> --save <...\sauvegardes\solo\slot_1> --report report.txt
python update.py   --mod <mod.json> --save <...\sauvegardes\solo\slot_1> [--overwrite-era] [--overwrite-major]
```

The exe has no console window, so use `--report` with it.

## For mod authors

Ask players to run the preview after an update and to send the report (*Save report…*) if something looks wrong. A local slot file (`resources\mods\slot_N.json`) can be compared too: *Other mod file…*.

## Development

```
python -m unittest discover -s tests -v
```

Every push builds the Windows exe on GitHub Actions (artifact `DM-Save-Update-exe`). A tag `vX.Y.Z` publishes it as a Release.

License: MIT.
