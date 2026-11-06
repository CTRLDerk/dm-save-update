"""Compare a Delta Manager mod with a career save and list what an update would change.

Version 0.1 only reads. Nothing is written to the save.

What counts as a mod setting and is compared:
  * generalData of every category (rules, economy, development, regulations, ...)
  * circuits and reserve circuits, matched by id (calendar fields stay as in the save)
  * sponsors and naming sponsors in the sponsor pool, matched by id

What is never touched: drivers, teams, staff, contracts, results, standings, history,
the active regulation (config.currentRegulation) and everything else that is career progress.
"""
import json
import os
import re

APP_ID = '4247780'

# Keys that are documentation, not settings.
META_KEYS = {'_comment', '_documentation'}

# Circuit fields that belong to the running calendar, not to the mod's track settings.
CIRCUIT_KEEP = {'id', 'week', 'eventType', 'hasSprintWeekend', 'testingCircuitId'}

# Settings that eras can change by a team vote (modding guide, chapter 16).
# Key names are matched anywhere in generalData; a protected key protects its whole subtree.
ERA_RULE_KEYS = {
    'points': {'pointsSystem', 'sprintPointsSystem', 'qualifyingPointsSystem', 'constructorRewards', 'fastestLapPoint'},
    'qualifying': {'qualifyingFormat', 'q1AdvanceCount', 'q2AdvanceCount', 'groupsAndDuels',
                   'eliminationQualifying107', 'eliminationThreshold', 'preQualifying', 'preQualifyingMode',
                   'preQualifyingExcludedCount', 'preQualifyingAdaptive', 'sprintWeekendsEnabled',
                   'singleSprintQualifying', 'sharedSprintQualifying', 'raceGridFromSprint', 'sprintReverseGrid',
                   'sprintReverseGridCount', 'raceReverseGrid', 'raceReverseGridCount', 'singleQualifying', 'skipRace'},
    'drs': {'drs'},
    'ers': {'ers'},
    'dirtyAir': {'dirtyAir'},
    'tyres': {'dryTyres', 'wetTyres', 'tyreAllocationEnabled', 'tyreAllocationPerCar', 'dryTyreSetsPerDriver',
              'wetTyreSetsPerDriver', 'dryTyreWearImpact', 'wetTyreWearImpact'},
    'fuel': {'fuelEnabled', 'fuelAsElectricity', 'fuelCapacity', 'fuelConsumptionPerLap', 'fuelWeightEffect',
             'refuelTimePerKg', 'refuelRigTime', 'fuelVariance', 'fuelConserveMultiplier', 'fuelPushMultiplier',
             'fuelUltraPushMultiplier'},
    'pitRules': {'mandatoryPitStop', 'mandatoryTwoCompounds'},
    'raceStart': {'startCrashMultiplier', 'startIncidentMultiplier'},
    'reliability': {'reliabilityMultiplier', '_reliabilityMultiplierV2'},
    'incidents': {'incidentMultiplier'},
    'regFreeze': {'minFrozenAttributes', 'maxFrozenAttributes'},
    'energy': {'energyStartAdvantage', 'energyStartAdvantageChance', 'energyStartImpact'},
    'catchUp': {'catchUp'},
    'engineCatchUp': {'engineCatchUp'},
    'powerUnit': {'powerUnit'},
    'safety': {'injurySafetyLevel', 'deathSafetyLevel'},
    'teams': {'minTeams', 'maxTeams'},
    'driverAids': {'driverAids'},
}

# Settings the game draws again at every major regulation (modding guide, chapters 13, 15, 16).
MAJOR_KEYS = {'globalPerformance', 'perfBonus', 'regulationAggressiveness'}

# Set by the game itself when a career starts (checked on a new GTWC career, 2026-11-06):
# the mod's regulations.baseLimits are replaced by the absolute caps (100 / 200).
GAME_KEYS = {'baseLimits'}

# The running career uses these from config.currentRegulation; the generalData value is used
# again when the next regulation is generated.
ACTIVE_REGULATION_KEYS = {'lapTimeCoefficients', 'qualifyingLapTimeCoefficients', 'freePracticeLapTimeCoefficients',
                          'startingRegulation', 'minimumCarWeight', 'baseLimits'}

# Actions in a change list.
UPDATE = 'update'
KEEP_ERA = 'keep (era vote)'
KEEP_MAJOR = 'keep (major regulation)'
KEEP_GAME = 'keep (set by the game)'
NOT_ADDED = 'not added'
NOT_IN_MOD = 'not in mod'


def load_json(path):
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


# ----------------------------------------------------------------- mod

def mod_categories(mod):
    """Categories of a mod file (slot format) as a list of dicts with the parts we compare."""
    cats = [{
        'key': 'main',
        'name': (mod.get('generalData') or {}).get('categoryName') or 'Main category',
        'general': mod.get('generalData') or {},
        'circuits': mod.get('circuits') or [],
        'reserveCircuits': mod.get('reserveCircuits') or [],
        'sponsors': mod.get('sponsors') or [],
        'namingSponsors': mod.get('namingSponsors') or [],
    }]
    for add in mod.get('additionalCategories') or []:
        data = add.get('data') or {}
        gen = data.get('general') or {}
        cats.append({
            'key': add.get('id'),
            'name': gen.get('categoryName') or add.get('name') or add.get('id'),
            'general': gen,
            'circuits': data.get('circuits') or [],
            'reserveCircuits': data.get('reserveCircuits') or [],
            'sponsors': data.get('sponsors') or [],
            'namingSponsors': data.get('namingSponsors') or [],
        })
    return cats


def mod_name(mod, fallback=''):
    return mod.get('modName') or mod.get('name') or fallback


# ----------------------------------------------------------------- save

class Save:
    """A career save folder (sauvegardes/<mode>/slot_N)."""

    def __init__(self, folder):
        self.folder = folder
        self.config = load_json(os.path.join(folder, 'config.json'))
        self.season = load_json(os.path.join(folder, 'season.json'))
        meta_path = os.path.join(folder, 'meta.json')
        self.meta = load_json(meta_path) if os.path.exists(meta_path) else {}

    @property
    def current_season(self):
        return self.season.get('currentSeason') or self.meta.get('currentSeason')

    def categories(self):
        """Settings of every category in the save, wherever the game keeps them.

        The category being played sits in config.json / season.json. When that is not the main
        category, the main category is parked in season._mainCategoryBackup and the others stay
        in season.additionalCategories.
        """
        cfg, sea = self.config, self.season
        active = sea.get('_activeCategoryId')
        top = {
            'general': cfg.get('generalData') or {},
            'circuits': sea.get('circuits') or [],
            'reserveCircuits': sea.get('reserveCircuits') or [],
            'sponsors': sea.get('sponsorsDatabase') or [],
            'namingSponsors': sea.get('namingSponsorsDatabase') or [],
        }
        cats = []
        if active:
            cats.append(dict(top, key=active, name=sea.get('_activeCategoryOriginalName') or top['general'].get('categoryName'),
                             where='config.json + season.json (category being played)'))
            backup = sea.get('_mainCategoryBackup') or {}
            bdata = backup.get('data') or {}
            if bdata:
                cats.append(self._from_data('main', backup.get('name'), bdata, 'season.json > _mainCategoryBackup'))
        else:
            cats.append(dict(top, key='main', name=top['general'].get('categoryName'),
                             where='config.json + season.json'))
        for i, add in enumerate(sea.get('additionalCategories') or []):
            cats.append(self._from_data(add.get('id'), add.get('name'), add.get('data') or {},
                                        'season.json > additionalCategories[%d]' % i))
        return cats

    @staticmethod
    def _from_data(key, name, data, where):
        gen = data.get('general') or {}
        return {
            'key': key, 'name': gen.get('categoryName') or name or key, 'where': where,
            'general': gen,
            'circuits': data.get('circuits') or [],
            'reserveCircuits': data.get('reserveCircuits') or [],
            'sponsors': data.get('sponsorsDatabase') or [],
            'namingSponsors': data.get('namingSponsorsDatabase') or [],
        }

    def era_rules(self, category_key):
        """Era rules passed in this career for a category: (set of rule types, set of payload keys)."""
        sea = self.season
        if category_key == 'main':
            sources = [sea.get('eraSchedule'), sea.get('eraRuleHistory')]
        else:
            sources = [(sea.get('categoryEraSchedules') or {}).get(category_key),
                       (sea.get('categoryEraRuleHistory') or {}).get(category_key)]
        types, keys = set(), set()
        for proposal in _proposals(sources):
            status = proposal.get('status')
            # History entries may carry no status: count them as passed, to be safe.
            if status not in (None, 'passed', 'adopted', 'accepted', 'applied'):
                continue
            if proposal.get('ruleType'):
                types.add(proposal['ruleType'])
            payload = proposal.get('payload')
            if isinstance(payload, dict):
                keys.update(k for k in payload if k not in ('presetId', 'enabled'))
        return types, keys

    def major_regulation_passed(self, general):
        regs = general.get('regulations') or {}
        first = regs.get('firstMajorRegulationYear', general.get('firstMajorRegulationYear'))
        try:
            return int(self.current_season) >= int(first)
        except (TypeError, ValueError):
            return True  # unknown: protect


def _proposals(sources):
    """Every dict with a ruleType found in era schedules / histories, whatever their exact shape."""
    stack = [s for s in sources if s]
    while stack:
        obj = stack.pop()
        if isinstance(obj, dict):
            if 'ruleType' in obj:
                yield obj
            else:
                stack.extend(obj.values())
        elif isinstance(obj, list):
            stack.extend(obj)


# ----------------------------------------------------------------- matching

def match_categories(mod_cats, save_cats):
    """Pairs (mod category, save category or None).

    Additional categories match by id, then by name. Every mod and save has a "main" category,
    so the main category only matches when the names are the same: a save of another mod
    must never be compared with this mod.
    """
    by_key = {c['key']: c for c in save_cats if c['key'] != 'main'}
    by_name = {(c['name'] or '').strip().lower(): c for c in save_cats}
    used, pairs = set(), []
    for mc in mod_cats:
        sc = by_key.get(mc['key'])
        if sc is None or id(sc) in used:
            sc = by_name.get((mc['name'] or '').strip().lower())
        if sc is not None and id(sc) in used:
            sc = None
        if sc is not None:
            used.add(id(sc))
        pairs.append((mc, sc))
    unmatched_save = [c for c in save_cats if id(c) not in used]
    return pairs, unmatched_save


def match_score(mod, save):
    """How many of the mod's categories are found in the save (by id or name)."""
    pairs, _ = match_categories(mod_categories(mod), save.categories())
    return sum(1 for _, sc in pairs if sc is not None), len(pairs)


# ----------------------------------------------------------------- diff

class Change:
    __slots__ = ('category', 'section', 'item', 'path', 'old', 'new', 'action', 'note')

    def __init__(self, category, section, item, path, old, new, action, note=''):
        self.category, self.section, self.item, self.path = category, section, item, path
        self.old, self.new, self.action, self.note = old, new, action, note

    def as_dict(self):
        return {k: getattr(self, k) for k in self.__slots__}


class Options:
    def __init__(self, overwrite_era=False, overwrite_major=False):
        self.overwrite_era = overwrite_era
        self.overwrite_major = overwrite_major


def compare(mod, save, options=None):
    """All differences between the mod and the save, with the action an update would take."""
    options = options or Options()
    changes, notes = [], []
    pairs, unmatched_save = match_categories(mod_categories(mod), save.categories())
    for mc, sc in pairs:
        if sc is None:
            notes.append('Category "%s" from the mod is not in this save. It is skipped.' % mc['name'])
            continue
        cname = sc['name']
        rule_types, payload_keys = save.era_rules(sc['key'])
        era_keys = set(payload_keys)
        for rt in rule_types:
            era_keys |= ERA_RULE_KEYS.get(rt, set())
        major = save.major_regulation_passed(sc['general'])
        if rule_types:
            notes.append('%s: era votes passed in this career (%s). Those settings keep the save value%s.'
                         % (cname, ', '.join(sorted(rule_types)), '' if not options.overwrite_era else ' unless overwritten'))
        if major:
            notes.append('%s: a major regulation has already happened. Values the game draws again at a major '
                         '(%s) keep the save value.' % (cname, ', '.join(sorted(MAJOR_KEYS))))
        protect = {k: KEEP_GAME for k in GAME_KEYS}
        if not options.overwrite_era:
            protect.update({k: KEEP_ERA for k in era_keys})
        if major and not options.overwrite_major:
            protect.update({k: KEEP_MAJOR for k in MAJOR_KEYS})
        _diff_dict(sc['general'], mc['general'], [], cname, protect, changes)
        for section in ('circuits', 'reserveCircuits'):
            _diff_list_by_id(sc[section], mc[section], cname, section, CIRCUIT_KEEP, changes)
        _diff_list_by_id(sc['sponsors'], mc['sponsors'], cname, 'sponsors', {'id'}, changes)
        _diff_list_by_id(sc['namingSponsors'], mc['namingSponsors'], cname, 'namingSponsors', {'id'}, changes)
    for c in unmatched_save:
        notes.append('Category "%s" in the save is not in the mod. It is left as it is.' % c['name'])
    return changes, notes


def _diff_dict(old, new, path, category, protect, out, protected_by=None):
    for key, nval in new.items():
        if key in META_KEYS:
            continue
        sub = path + [key]
        action = protected_by or protect.get(key)
        if key not in old:
            out.append(Change(category, 'settings', '', '.'.join(sub), None, nval, action or UPDATE,
                              _note_for(sub, action)))
            continue
        oval = old[key]
        if isinstance(oval, dict) and isinstance(nval, dict):
            _diff_dict(oval, nval, sub, category, protect, out, action)
        elif _same_shape_dict_lists(oval, nval):
            # Lists like dryTyres or concepts: show the field that differs, e.g. dryTyres[General].durability
            for i, (o, n) in enumerate(zip(oval, nval)):
                tag = n.get('displayName') or n.get('name') or n.get('id') or i
                elem = sub[:-1] + ['%s[%s]' % (key, tag)]
                _diff_dict(o, n, elem, category, protect, out, action or protect.get(key))
        elif oval != nval:
            out.append(Change(category, 'settings', '', '.'.join(sub), oval, nval, action or UPDATE,
                              _note_for(sub, action)))


def _same_shape_dict_lists(a, b):
    return (isinstance(a, list) and isinstance(b, list) and len(a) == len(b) and a
            and all(isinstance(x, dict) for x in a) and all(isinstance(x, dict) for x in b))


def _note_for(path, action):
    if action:
        return ''
    if any(p in ACTIVE_REGULATION_KEYS for p in path):
        return 'The running season uses the active regulation; this value counts from the next regulation change.'
    return ''


def _label(entity):
    return '%s (%s)' % (entity.get('name') or entity.get('officialName') or '?', entity.get('id'))


def _diff_list_by_id(old_list, new_list, category, section, keep, out):
    old_by_id = {e.get('id'): e for e in old_list if isinstance(e, dict)}
    new_ids = set()
    for ent in new_list:
        if not isinstance(ent, dict):
            continue
        eid = ent.get('id')
        new_ids.add(eid)
        cur = old_by_id.get(eid)
        if cur is None:
            out.append(Change(category, section, _label(ent), '', None, None, NOT_ADDED,
                              'New in the mod. Adding it changes the calendar or sponsor pool of a running career.'))
            continue
        for key, nval in ent.items():
            if key in keep or key in META_KEYS:
                continue
            target = key
            # The game moves a circuit's mod name to officialName and puts the track name in name.
            if key == 'name' and section in ('circuits', 'reserveCircuits') and 'officialName' in cur:
                target = 'officialName'
            if cur.get(target) != nval:
                out.append(Change(category, section, _label(cur), target, cur.get(target), nval, UPDATE))
    for eid, cur in old_by_id.items():
        if eid not in new_ids:
            out.append(Change(category, section, _label(cur), '', None, None, NOT_IN_MOD,
                              'No longer in the mod. It stays in the save.'))


# ----------------------------------------------------------------- report

def short(value, limit=80):
    if value is None:
        return '-'
    text = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    text = re.sub(r'\s+', ' ', text)
    return text if len(text) <= limit else text[:limit - 1] + '…'


def summary(changes):
    counts = {}
    for c in changes:
        counts[c.action] = counts.get(c.action, 0) + 1
    return counts


def report_text(changes, notes, mod_label, save_label):
    lines = ['DM Save Update - preview (nothing has been written)',
             'Mod:  %s' % mod_label, 'Save: %s' % save_label, '']
    counts = summary(changes)
    lines.append('Summary: ' + (', '.join('%s %d' % (k, v) for k, v in sorted(counts.items())) or 'no differences'))
    for n in notes:
        lines.append('* ' + n)
    current = None
    for c in changes:
        head = '%s / %s' % (c.category, c.section)
        if head != current:
            lines += ['', '## ' + head]
            current = head
        what = ' > '.join(x for x in (c.item, c.path) if x)
        lines.append('- [%s] %s: %s -> %s%s' % (c.action, what, short(c.old), short(c.new),
                                                ('  (' + c.note + ')') if c.note else ''))
    return '\n'.join(lines) + '\n'
