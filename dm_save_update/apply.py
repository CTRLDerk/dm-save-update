"""Write an update into a save, with a backup first, and put a backup back.

Only config.json and season.json are written. Before that, both are copied (with meta.json)
to a backup folder inside the slot: <slot>/_dmsu_backup_<date>_<time>/.
"""
import datetime
import json
import os
import shutil

from . import __version__, core, jsonfmt

BACKUP_PREFIX = '_dmsu_backup_'
MANIFEST = 'dm-save-update.json'


class SaveChanged(Exception):
    """The save was written by someone else (the game?) after it was read."""


def changed_files(save):
    out = []
    for name in save.FILES:
        path = os.path.join(save.folder, name)
        if not os.path.exists(path) or os.path.getmtime(path) != save.mtime[name]:
            out.append(name)
    return out


def make_backup(save, mod_label=''):
    stamp = datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S')
    folder = os.path.join(save.folder, BACKUP_PREFIX + stamp)
    n = 1
    while os.path.exists(folder):
        n += 1
        folder = os.path.join(save.folder, '%s%s_%d' % (BACKUP_PREFIX, stamp, n))
    os.makedirs(folder)
    copied = []
    for name in save.FILES + ('meta.json',):
        src = os.path.join(save.folder, name)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(folder, name))
            copied.append(name)
    with open(os.path.join(folder, MANIFEST), 'w', encoding='utf-8') as fh:
        json.dump({'tool': 'DM Save Update', 'version': __version__,
                   'created': datetime.datetime.now().isoformat(timespec='seconds'),
                   'mod': mod_label, 'files': copied}, fh, indent=2)
    return folder


def _write_atomic(path, text):
    tmp = path + '.dmsu-tmp'
    with open(tmp, 'w', encoding='utf-8', newline='') as fh:
        fh.write(text)
    with open(tmp, encoding='utf-8') as fh:
        json.load(fh)  # never put a file the game cannot read in place of the save
    os.replace(tmp, path)


def apply_update(mod, save_folder, options=None, mod_label='', expect_mtime=None):
    """Update the save on disk. Returns (changes applied, notes, backup folder).

    The save is read again here. expect_mtime (Save.mtime of the preview) makes sure the
    files are still the ones the player saw in the preview.
    """
    save = core.Save(save_folder)
    if expect_mtime is not None and save.mtime != expect_mtime:
        raise SaveChanged('The save has changed since the preview (the game saved it?). Show the changes again.')
    changes, notes = core.compare(mod, save, options, apply=True)
    applied = [c for c in changes if c.action == core.UPDATE]
    if not applied:
        return applied, notes, None
    new_text = {
        'config.json': jsonfmt.dumps_like(save.config, save.raw['config.json']),
        'season.json': jsonfmt.dumps_like(save.season, save.raw['season.json']),
    }
    if changed_files(save):
        raise SaveChanged('The save was written while the update was prepared. Close Delta Manager and try again.')
    backup = make_backup(save, mod_label)
    for name, text in new_text.items():
        if text != save.raw[name]:
            _write_atomic(os.path.join(save.folder, name), text)
    return applied, notes, backup


def list_backups(save_folder):
    """Backups made by this tool in a slot, newest first: [(folder, manifest dict)]."""
    out = []
    if not os.path.isdir(save_folder):
        return out
    for name in os.listdir(save_folder):
        folder = os.path.join(save_folder, name)
        if name.startswith(BACKUP_PREFIX) and os.path.isdir(folder):
            info = {}
            try:
                with open(os.path.join(folder, MANIFEST), encoding='utf-8') as fh:
                    info = json.load(fh)
            except (OSError, ValueError):
                pass
            out.append((folder, info))
    out.sort(key=lambda b: os.path.basename(b[0]), reverse=True)
    return out


def restore_backup(save_folder, backup_folder):
    """Put a backup back. The current files are backed up first, so a restore can be undone."""
    current = core.Save(save_folder)
    undo = make_backup(current, 'before restoring %s' % os.path.basename(backup_folder))
    restored = []
    for name in core.Save.FILES + ('meta.json',):
        src = os.path.join(backup_folder, name)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(save_folder, name))
            restored.append(name)
    return restored, undo
