"""Real mod files and Node.js for the QA tests. Both are optional: tests that need them are skipped.

Real mods, first found wins:
  * DMSU_REAL_MODS=<folder>: every *.json in it (recursively) is a mod file in slot format;
  * a dm-mods clone next to this repository (../dm-mods): every mod with src/ is built once
    with its tools/modsplit.py into a temporary folder.

Node.js (DMSU_NODE or `node` on PATH) gives the reference output of JSON.stringify, which is
what Delta Manager uses to write saves.
"""
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_cache = {}


def node():
    return os.environ.get('DMSU_NODE') or shutil.which('node')


def js_stringify(text, indent=2):
    """JSON.stringify(JSON.parse(text), null, indent) as Node writes it."""
    script = ('let s="";process.stdin.setEncoding("utf8");process.stdin.on("data",d=>s+=d);'
              'process.stdin.on("end",()=>process.stdout.write(JSON.stringify(JSON.parse(s),null,%d)));' % indent)
    res = subprocess.run([node(), '-e', script], input=text.encode('utf-8'), stdout=subprocess.PIPE, check=True)
    return res.stdout.decode('utf-8')


def dm_mods_dir():
    return os.environ.get('DMSU_DM_MODS') or os.path.join(os.path.dirname(ROOT), 'dm-mods')


def real_mods():
    """[(name, path to slot json)]; empty when no real mods are available."""
    if 'mods' in _cache:
        return _cache['mods']
    found = []
    folder = os.environ.get('DMSU_REAL_MODS')
    if folder:
        for path in sorted(glob.glob(os.path.join(folder, '**', '*.json'), recursive=True)):
            found.append((os.path.relpath(path, folder), path))
    else:
        repo = dm_mods_dir()
        tool = os.path.join(repo, 'tools', 'modsplit.py')
        if os.path.isfile(tool):
            out = tempfile.mkdtemp(prefix='dmsu-realmods-')
            for meta in sorted(glob.glob(os.path.join(repo, 'mods', '*', 'mod.json'))):
                mod_dir = os.path.dirname(meta)
                src = os.path.join(mod_dir, 'src')
                if not os.path.isfile(os.path.join(src, '_root.json')):
                    continue
                slug = os.path.basename(mod_dir)
                target = os.path.join(out, slug + '.json')
                subprocess.run([sys.executable, tool, 'build', src, target], check=True,
                               stdout=subprocess.DEVNULL)
                found.append((slug, target))
    _cache['mods'] = found
    return found


def load(path):
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


# ----------------------------------------------------------------- a fresh career save from a mod

def _circuit_in_save(c):
    """The game moves a circuit's mod name to officialName at career start."""
    c = dict(c)
    if 'name' in c:
        c['officialName'] = c['name']
        c['name'] = 'Track %s' % c.get('id')
    return c


def _general_in_save(g):
    g = json.loads(json.dumps(g))
    regs = g.get('regulations')
    if isinstance(regs, dict) and 'baseLimits' in regs:
        regs['baseLimits'] = {'note': 'set by the game at career start'}
    return g


def _data_in_save(general, src):
    return {
        'general': _general_in_save(general),
        'circuits': [_circuit_in_save(c) for c in src.get('circuits') or []],
        'reserveCircuits': [_circuit_in_save(c) for c in src.get('reserveCircuits') or []],
        'sponsorsDatabase': json.loads(json.dumps(src.get('sponsors') or [])),
        'namingSponsorsDatabase': json.loads(json.dumps(src.get('namingSponsors') or [])),
    }


def fresh_career(mod, folder, play=None):
    """Write a save as the game makes it when a career starts from this mod.

    play=None plays the main category; play=<id> plays that additional category, so the main
    category is parked in season._mainCategoryBackup (the swap the game does).
    """
    from dm_save_update import jsonfmt
    os.makedirs(folder, exist_ok=True)
    main = _data_in_save(mod.get('generalData') or {}, mod)
    adds = []
    for add in mod.get('additionalCategories') or []:
        data = add.get('data') or {}
        adds.append({'id': add.get('id'), 'name': add.get('name'), 'data': _data_in_save(data.get('general') or {}, data)})
    start = (mod.get('generalData') or {}).get('startYear') or 2025
    season = {'currentSeason': start, 'eraSchedule': None, 'categoryEraSchedules': {}}
    if play is None:
        top, rest = main, adds
    else:
        top = next(a['data'] for a in adds if a['id'] == play)
        rest = [a for a in adds if a['id'] != play]
        season['_activeCategoryId'] = play
        season['_activeCategoryOriginalName'] = top['general'].get('categoryName')
        season['_mainCategoryBackup'] = {'name': main['general'].get('categoryName'), 'data': main}
    config = {'generalData': top['general'], 'currentRegulation': {'lapTimeCoefficients': {}}}
    season.update({'circuits': top['circuits'], 'reserveCircuits': top['reserveCircuits'],
                   'sponsorsDatabase': top['sponsorsDatabase'], 'namingSponsorsDatabase': top['namingSponsorsDatabase'],
                   'additionalCategories': rest})
    for name, data in (('config.json', config), ('season.json', season),
                       ('meta.json', {'currentSeason': start, 'currentWeek': 1})):
        with open(os.path.join(folder, name), 'w', encoding='utf-8', newline='') as fh:
            fh.write(jsonfmt.dumps(data))
    return folder
