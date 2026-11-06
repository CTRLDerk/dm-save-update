"""Find the Delta Manager save folder and the Steam Workshop mods on this PC."""
import json
import os
import re
import sys

from .core import APP_ID

GAME_DIR = 'Delta Manager'
SAVES_DIR = 'sauvegardes'
SAVE_MODES = ('solo', 'coop', 'spectator')


def steam_libraries():
    roots = []
    if sys.platform.startswith('win'):
        try:
            import winreg
            for hive, sub in ((winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam'),
                              (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Valve\Steam')):
                try:
                    with winreg.OpenKey(hive, sub) as key:
                        for name in ('SteamPath', 'InstallPath'):
                            try:
                                roots.append(os.path.normpath(winreg.QueryValueEx(key, name)[0]))
                            except OSError:
                                pass
                except OSError:
                    pass
        except ImportError:
            pass
        for env in ('ProgramFiles(x86)', 'ProgramFiles'):
            if os.environ.get(env):
                roots.append(os.path.join(os.environ[env], 'Steam'))
    else:
        home = os.path.expanduser('~')
        roots += [os.path.join(home, '.steam', 'steam'), os.path.join(home, '.local', 'share', 'Steam'),
                  os.path.join(home, 'Library', 'Application Support', 'Steam')]
    libs = []
    for root in roots:
        if root not in libs:
            libs.append(root)
        vdf = os.path.join(root, 'steamapps', 'libraryfolders.vdf')
        try:
            with open(vdf, encoding='utf-8', errors='replace') as fh:
                for m in re.finditer(r'"path"\s+"([^"]+)"', fh.read()):
                    path = os.path.normpath(m.group(1).replace('\\\\', '\\'))
                    if path not in libs:
                        libs.append(path)
        except OSError:
            pass
    return [lib for lib in libs if os.path.isdir(os.path.join(lib, 'steamapps'))]


def find_saves_dir():
    for lib in steam_libraries():
        cand = os.path.join(lib, 'steamapps', 'common', GAME_DIR, SAVES_DIR)
        if os.path.isdir(cand):
            return cand
    return ''


def find_workshop_dir():
    for lib in steam_libraries():
        cand = os.path.join(lib, 'steamapps', 'workshop', 'content', APP_ID)
        if os.path.isdir(cand):
            return cand
    return ''


def list_saves(saves_dir):
    """Career slots: [{path, mode, slot, label}] sorted newest first."""
    out = []
    if not saves_dir or not os.path.isdir(saves_dir):
        return out
    modes = [m for m in SAVE_MODES if os.path.isdir(os.path.join(saves_dir, m))] or ['']
    for mode in modes:
        base = os.path.join(saves_dir, mode)
        for name in sorted(os.listdir(base)):
            path = os.path.join(base, name)
            if not (name.startswith('slot_') and os.path.isfile(os.path.join(path, 'config.json'))):
                continue
            meta = {}
            try:
                with open(os.path.join(path, 'meta.json'), encoding='utf-8') as fh:
                    meta = json.load(fh)
            except (OSError, ValueError):
                pass
            label = '%s %s - %s, %s week %s' % (mode, name, meta.get('displayName') or meta.get('teamName') or '?',
                                                meta.get('currentSeason', '?'), meta.get('currentWeek', '?'))
            out.append({'path': path, 'mode': mode, 'slot': name, 'label': label,
                        'savedAt': meta.get('savedAt') or ''})
    out.sort(key=lambda s: s['savedAt'], reverse=True)
    return out


_NAME_RE = re.compile(r'"modName"\s*:\s*"((?:[^"\\]|\\.)*)"')


def peek_mod_name(path):
    """modName from the start of a mod file, without parsing the whole (possibly huge) file."""
    try:
        with open(path, encoding='utf-8', errors='replace') as fh:
            head = fh.read(65536)
    except OSError:
        return ''
    m = _NAME_RE.search(head)
    if not m:
        return ''
    try:
        return json.loads('"%s"' % m.group(1))
    except ValueError:
        return m.group(1)


def list_workshop_mods(workshop_dir):
    """Workshop items: [{path, item, label}]. The mod file is the largest .json in the item folder."""
    out = []
    if not workshop_dir or not os.path.isdir(workshop_dir):
        return out
    for item in sorted(os.listdir(workshop_dir)):
        folder = os.path.join(workshop_dir, item)
        if not os.path.isdir(folder):
            continue
        jsons = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith('.json')]
        if not jsons:
            continue
        path = max(jsons, key=os.path.getsize)
        name = peek_mod_name(path) or os.path.basename(path)
        out.append({'path': path, 'item': item, 'label': '%s  (Workshop %s)' % (name, item)})
    return out
