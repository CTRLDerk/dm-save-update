# dm-save-update

Windows-tool (exe) die een mod-update op een carrière-save toepast.

## Controles

- `python -m unittest discover -s tests -v`
- `python -m tests.gui_check` (venstercontrole; heeft een display nodig)
- Bij een nieuwe versie: `__version__` in `dm_save_update/__init__.py` én een `## X.Y.Z`-sectie in `CHANGELOG.md`.

## Publiceren

Tag `vX.Y.Z` → `build.yml` bouwt en test de exe; de job `release` wacht op goedkeuring in environment `publish`.

## Werkwijze (geldt voor alle Delta Manager-repo's)

Doel: kwaliteit bewaken, en **niets wordt gepubliceerd zonder dat de eigenaar zelf ingrijpt**.

### Stap 1: Voorstel in Markdown, en wachten op akkoord

Vóór elke actie op een repo (commit, push, pull request) toon je eerst een voorstel in Markdown, in deze vorm:

```markdown
# Voorstel: <korte titel>

## Samenvatting
<2–5 zinnen: wat verandert er, waarom, in welke repo('s), en wat de controles zeggen.>

## Uitgewerkt resultaat
### Repo en branch
<repo> → `<branch>`

### Wijzigingen per bestand
| Bestand | Wat verandert |
|---|---|

### Details
<per onderdeel de concrete waarden: oud → nieuw, met bron of reden>

### Controles
| Controle | Resultaat |
|---|---|
| JSON-poort: DM Validator | … fouten / … waarschuwingen |
| JSON-poort: DM Toolkit (check-mod.js) | … |
| Repo-controles (zie hieronder) | … |

### Actie na akkoord
<precies wat er gebeurt: commit "<bericht>", push naar `<branch>`, pull request "<titel>">
```

Pas na een expliciet **akkoord** van de eigenaar voer je precies die actie uit. Verandert er daarna nog iets, dan eerst een nieuw voorstel. Commit, push en het openen van een PR vragen in Claude Code bovendien om bevestiging (`ask` in `.claude/settings.json`).

### Stap 2: JSON-poort

Voordat iets naar de repo gaat, wordt alle gewijzigde JSON gecontroleerd in **DM Validator** (strikte parser + schema) en **DM Toolkit** (`tools/check-mod.js`). In dm-mods draait per gewijzigde mod `tools/verify.sh`. Dit gebeurt automatisch bij `git commit` en `git push` via `.claude/hooks/guard.js` → `.claude/hooks/json-gate.js`; bij fouten wordt de actie geblokkeerd. Draai hem ook zelf vóór het voorstel, zodat de uitkomst in het voorstel staat:

```
node .claude/hooks/json-gate.js          # alles wat afwijkt van origin/main
node .claude/hooks/json-gate.js --all    # alle JSON in de repo
```

`dm-validator` en `dm-toolkit` moeten naast deze repo staan (`../dm-validator`, `../dm-toolkit`). Ontbreken ze, dan wordt de actie geblokkeerd.

### Regels

1. **Altijd op een eigen branch.** Nooit committen of pushen op `main`. Eén onderwerp per branch.
2. **Rood = niet doorgaan.** Een falende controle meld je eerlijk in het voorstel; eerst oplossen.
3. **Changelog bijwerken** waar de repo er een heeft (zie hierboven), in dezelfde commit als de wijziging.
4. **Na akkoord:** committen, pushen naar de eigen branch en een pull request openen, zoals in het voorstel stond.
5. **Nooit zelf:** een PR mergen of auto-merge aanzetten, een tag maken of pushen, een GitHub Release maken, een workflow handmatig starten, force-pushen, of via de GitHub-API bestanden direct op een branch zetten. Dit is technisch geblokkeerd (`.claude/settings.json`, `.claude/hooks/`). Pas die bestanden niet aan zonder dat de eigenaar erom vraagt.
6. **Publiceren doet de eigenaar:** PR mergen → tag/release maken → in GitHub Actions de job in environment `publish` goedkeuren.
7. Geen privébestanden in Git: mod-slots van spelers, saves, webhook-URL's, e-mailadressen, tokens.

### CI

Elke push en PR draait de workflow `check`. Die publiceert niets. Een PR mag pas gemerged worden als `check` groen is.
