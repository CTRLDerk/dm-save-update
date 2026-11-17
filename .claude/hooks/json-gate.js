#!/usr/bin/env node
/* JSON-poort: controleert JSON vóórdat iets naar GitHub gaat.
   Als hook: aangeroepen door guard.js bij `git commit` (gestagede bestanden) en `git push`
   (alles wat afwijkt van origin/main). Handmatig: node .claude/hooks/json-gate.js [--all]
   Per gewijzigd .json-bestand:
     - DM Validator (../dm-validator): strikte JSON-parser (syntaxis, dubbele sleutels);
       is het een mod-bestand, dan ook schema-controle. Fouten blokkeren.
     - DM Toolkit (../dm-toolkit): tools/check-mod.js op elk mod-bestand. Fouten blokkeren.
   dm-mods: elke mod met gewijzigde bronnen wordt gebouwd en met tools/verify.sh gecontroleerd
   (modsplit, check.py, round-trip, validator + toolkit).
   Exitcode 0 = in orde, 2 = geblokkeerd (de uitleg staat op stderr). */
'use strict';
const fs = require('fs'), path = require('path'), { execFileSync, spawnSync } = require('child_process');

function run(mode, cwd) {
  const git = (...a) => { try { return execFileSync('git', a, { cwd, stdio: ['ignore', 'pipe', 'ignore'] }).toString(); } catch { return ''; } };
  const top = git('rev-parse', '--show-toplevel').trim();
  if (!top) return { ok: true, report: '' };
  const repo = path.basename(top);
  const sib = (name) => repo === name ? top : path.resolve(top, '..', name);
  const valDir = sib('dm-validator'), kitDir = sib('dm-toolkit');
  const lines = [], fail = [];
  const out = (s) => lines.push(s);

  let files;
  if (mode === 'all') files = git('ls-files', '*.json').split('\n');
  else if (mode === 'commit') files = git('diff', '--cached', '--name-only', '--diff-filter=ACMR').split('\n');
  else {
    git('fetch', '-q', 'origin', 'main');
    const base = git('merge-base', 'origin/main', 'HEAD').trim();
    files = (base ? git('diff', '--name-only', '--diff-filter=ACMR', base, 'HEAD') : git('ls-files')).split('\n');
  }
  files = [...new Set(files.filter(Boolean))];
  const json = files.filter(f => f.endsWith('.json') && fs.existsSync(path.join(top, f)));

  const missing = [['dm-validator', valDir, 'engine.js'], ['dm-toolkit', kitDir, 'tools/check-mod.js']]
    .filter(([, d, f]) => !fs.existsSync(path.join(d, f))).map(([n]) => n);
  if (missing.length && (json.length || repo === 'dm-mods')) {
    return { ok: false, report: `JSON-poort: ${missing.join(' en ')} ontbreekt naast ${repo} (verwacht in ${path.dirname(top)}). ` +
      'Zonder validator en toolkit kan de JSON niet gecontroleerd worden; voeg de repo(s) toe aan de sessie.' };
  }

  // dm-mods: per mod met gewijzigde bestanden de volledige verify.sh
  if (repo === 'dm-mods') {
    const mods = [...new Set(files.map(f => (f.match(/^mods\/([^/]+)\//) || [])[1]).filter(Boolean))]
      .filter(m => fs.existsSync(path.join(top, 'mods', m, 'src', '_root.json')));
    for (const m of mods) {
      const r = spawnSync('bash', ['tools/verify.sh', m], { cwd: top, encoding: 'utf8' });
      out(`mod ${m}: verify.sh ${r.status === 0 ? 'OK' : 'FOUT'}`);
      out((r.stdout || '').trim().split('\n').map(l => '    ' + l).join('\n'));
      if (r.status !== 0) fail.push(`verify.sh ${m}`);
    }
  }

  const DMV = require(path.join(valDir, 'engine.js'));
  const S = JSON.parse(fs.readFileSync(path.join(valDir, 'schema', 'dm-0.7.json'), 'utf8'));
  for (const f of json) {
    const abs = path.join(top, f), text = fs.readFileSync(abs, 'utf8');
    let doc;
    try { doc = DMV.parse(text); }
    catch (e) { out(`FOUT  ${f}: ongeldige JSON (${e.code || ''} regel ${e.line}, kolom ${e.col})`); fail.push(f); continue; }
    const isMod = doc && typeof doc === 'object' && !Array.isArray(doc) && ['generalData', 'teams', 'titularDrivers', 'circuits', 'additionalCategories', 'modName'].some(k => k in doc)
      && !/(^|\/)(schema|i18n|testdata)\//.test(f) && !/(^|\/)src\//.test(f);
    if (!isMod) { out(`OK    ${f}: geldige JSON`); continue; }
    const res = DMV.resolve(DMV.validate(doc, S), DMV.lineIndex(text));
    const err = res.msgs.filter(m => m.sev === 'error'), warn = res.msgs.filter(m => m.sev === 'warning');
    out(`${err.length ? 'FOUT' : 'OK  '}  ${f}: validator ${err.length} fouten, ${warn.length} waarschuwingen`);
    for (const m of err.slice(0, 8)) out(`        regel ${m.line}: ${m.code} ${m.field || ''} ${m.value || ''}`);
    if (err.length) fail.push(f + ' (validator)');
    const r = spawnSync(process.execPath, [path.join(kitDir, 'tools', 'check-mod.js'), abs, '--validator', valDir], { encoding: 'utf8' });
    out(`${r.status === 0 ? 'OK  ' : 'FOUT'}  ${f}: toolkit check-mod.js (exit ${r.status})`);
    const sum = (r.stdout || '').split('\n').filter(l => /^#{1,3} |fout|error|warning|waarschuwing|Open/i.test(l)).slice(0, 10);
    for (const l of sum) out('        ' + l.trim());
    if (r.status !== 0) fail.push(f + ' (toolkit)');
  }
  if (!json.length && repo !== 'dm-mods') out('Geen gewijzigde JSON-bestanden.');
  const head = fail.length ? `JSON-poort: GEBLOKKEERD (${fail.join(', ')})` : 'JSON-poort: in orde';
  return { ok: !fail.length, report: head + '\n' + lines.join('\n') };
}

module.exports = { run };
if (require.main === module) {
  const r = run(process.argv.includes('--all') ? 'all' : process.argv.includes('--commit') ? 'commit' : 'push', process.cwd());
  console.log(r.report);
  process.exit(r.ok ? 0 : 2);
}
