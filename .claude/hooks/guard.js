#!/usr/bin/env node
/* Publicatiepoort voor Claude Code (PreToolUse-hook).
   Blokkeert alles waarmee code zonder jouw tussenkomst gepubliceerd kan worden:
   pushen naar main/master, tags, force-push, branches verwijderen, releases,
   PR's mergen. Werken op een eigen branch en die pushen blijft gewoon mogelijk.
   Exitcode 2 = geblokkeerd; de reden gaat terug naar Claude. */
'use strict';
let raw = '';
process.stdin.on('data', d => raw += d).on('end', () => {
  let input = {};
  try { input = JSON.parse(raw); } catch { process.exit(0); }
  const cmd = String((input.tool_input || {}).command || '');
  const rules = [
    [/\bgit\b[^;&|]*\bpush\b[^;&|]*(\s|:|\/)(main|master)(\s|$|;|&|\|)/, 'pushen naar main/master'],
    [/\bgit\b[^;&|]*\bpush\b[^;&|]*(--tags|--follow-tags|refs\/tags\/)/, 'tags pushen'],
    [/\bgit\b[^;&|]*\bpush\b[^;&|]*(\s--force\b|\s-f\b|\s--force-with-lease\b|\s\+\S)/, 'force-push'],
    [/\bgit\b[^;&|]*\bpush\b[^;&|]*(\s--delete\b|\s-d\b|\s:\S)/, 'remote branch verwijderen'],
    [/\bgit\b[^;&|]*\btag\b/, 'tags maken (een tag start een release-workflow)'],
    [/\bgh\s+(release|pr\s+merge|workflow\s+run|repo\s+edit|api\b[^;&|]*-X\s*(POST|PUT|PATCH|DELETE))/i, 'publiceren of mergen via gh'],
  ];
  const push = cmd.match(/\bgit\b[^;&|]*\bpush\b([^;&|]*)/);
  if (push) {  // ook `git push` zonder doel vanaf main, en tags op naam
    const { execSync } = require('child_process');
    const git = (a) => { try { return execSync('git ' + a, { cwd: input.cwd || process.cwd(), stdio: ['ignore', 'pipe', 'ignore'] }).toString(); } catch { return ''; } };
    if (/^(main|master)$/.test(git('branch --show-current').trim())) rules.unshift([/./, 'pushen vanaf main/master']);
    const tags = new Set(git('tag -l').split('\n').filter(Boolean));
    if (push[1].split(/\s+/).some(w => tags.has(w))) rules.unshift([/./, 'een tag pushen']);
  }
  for (const [re, why] of rules) {
    if (re.test(cmd)) {
      process.stderr.write(`Geblokkeerd door de publicatiepoort (.claude/hooks/guard.js): ${why}. ` +
        'Werk op je eigen branch en laat mergen, taggen en releasen aan de eigenaar over.');
      process.exit(2);
    }
  }
  process.exit(0);
});
