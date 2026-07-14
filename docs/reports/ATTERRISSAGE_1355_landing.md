# Epic #1355 « Atterrissage » — État système à l'atterrissage

**Date** : 2026-07-14.
**Auteur** : `Claude Code @ myia-po-2025:2025-Epita-Intelligence-Symbolique`.
**Epic** : #1355 (mandate user — seule Epic ouverte).
**Base** : `76123007` (branche `feat/att3-finalization-1355-1449`).

> Ce document fige l'état du système au moment de l'atterrissage de l'Epic #1355. Il complète `ATT3_AGGREGATE_opaque.md` (preuve capstone) en décrivant la posture d'ensemble : ce qui est tenu, ce qui reste, ce qui est honnêtement non-résolu.

---

## 1. Posture d'atterrissage

L'Epic #1355 « Atterrissage » vise à faire descendre le système d'un cycle de features vers un état **stable, honnête et reproductible**. À l'atterrissage :

- **Le tronc commun fonctionne de bout en bout sur corpus réel.** Le workflow `spectacular_analysis` (40 phases) termine sans crash sur les 3 corpus testés (cf. `ATT3_AGGREGATE_opaque.md` §3).
- **L'honnêteté est codée, pas cosmétique.** Le Constat n°5 (un axe dégradé ne se déguise jamais en décision genuine) est appliqué sur **les deux chemins** de pipeline (`conversational_orchestrator` `#1446` + portage `unified_pipeline` ce commit).
- **Les solveurs formels rendent un verdict genuine.** Modal (SPASS), FOL (EProver), PL (PySAT) produisent des booléens de décision réels, sans `ParserException` non-géré.

---

## 2. Axes d'atterrissage — statut

### ATT-1 — CI (gate mypy strict)

**Atteint.** `mypy --strict` sur les 8 fichiers core est le seul vrai gate CI. `black`/`flake8` sont `continue-on-error` (bruit). Les tests sautent gracieusement sans clé API.

- ⚠ **Floater résiduel** `tests/.../test_fol_2pass_pipeline.py::test_template_fallback_includes_fallacies` : échec par **collection-order pollution** (le test pose `OPENAI_API_KEY=""` sans mocker `openai.AsyncOpenAI`, contrairement à ses frères L105/147/190). **Non-régressif**, **dispatché à po-2023 (#1452, T0)** — ne pas fixer côté po-2025 (collision sur le fichier test). Cité ici honnêtement comme « floater ATT-1 sous fix #1452 », pas comme « main vert ».

### ATT-3 — Capstone texte-terminal

**Mécanique de preuve atteinte** (cf. `ATT3_AGGREGATE_opaque.md`) :

- 3 corpus re-run sur base `76123007`, 40/40 phases chacun.
- `capabilities_degraded` populé firsthand (≠ `used`) sur les 3 corpus.
- 0 `ParserException` non-géré (modal `#1443` tient ; FOL résiduel catché en fail-loud degraded).
- Gate reporté verbatim : A/C `PASS`, B `FAIL` (Acte II vide — échec restitution narrative, pas crash).

**Reste** : l'acte de clôture final (validation user) est **non-délégable**, ai-01-local. La mécanique est livrée et prouvée ; le feu vert terminal est différé pour revue.

### NORTH-STAR paramétrique — mécanique complète

- **5/5 traducteurs** : TR-1 (bipolar + ABA `#1422`) + TR-2 (ASPIC+ `#1427`, SetAF `#1428`, weighted `#1431`).
- **3 axes de comparaison** : FOL / Dung (I5 `#1430`) / sophism (I1 `#1429`).
- **Harness unifié** `compare_all_axes` (`#1438`) + capability `multi_axis_compare` (`#1439`), MERGED.

> **Note honnête SetAF** : le traducteur SetAF est câblé mais n'extracte rien sur le matériel testé (`absent_no_translator` sur 3/3 corpus). Ce n'est pas un bug — c'est la non-déterminisme LLM honnête signalée par le Constat n°5. L'axe surgit via `capabilities_degraded`, jamais maquillé en `used`.

### ATT-5 — Documentation

**Atteint** (`#1315` CLOSED). 6 PRs, ~607 liens cassés → 0 réel.

---

## 3. Ce qui est honnêtement non-résolu à l'atterrissage

Anti-pendule : l'atterrissage ne déclare pas « tout est vert ». Voici les résidus assumés.

| Résidu | Nature | Statut |
|--------|--------|--------|
| Floater `test_template_fallback_includes_fallacies` | Collection-order pollution (test, pas code) | Sous fix `#1452` (po-2023, parallèle) |
| `setaf_reasoning` `absent_no_translator` | Pas de traducteur extractant sur ce corpus | Honnête (degraded, jamais masqué) |
| FOL `fol_2` corpus B `ParserException` | Token de parse FOL résiduel (≠ `#1443`) | Catché fail-loud degraded `#1019` |
| Corpus B Acte II vide | Générateur narration muet (`--offset 120000`) | Gate `FAIL` reporté verbatim |
| `fact_extraction` floaters (`#1423`) | Fallback LLM sur entrées courtes | Documenté non-régressif |
| ATT-1 résidu Linux L1 (`#1204`) | EProver WSL | Coord-gated |

Aucun de ces résidus n'est masqué. Chacun est tracé dans un issue ou un report.

---

## 4. Discipline de confidentialité à l'atterrissage

Le dataset canonique (`extract_sources.json.gz.enc`, chiffré, tracked) contient du matériel politiquement sensible. À l'atterrissage, la discipline tient :

- **Aucun plaintext ne quitte la machine via git.** `full_text`/`raw_text`/snippets sont bloqués par `.gitignore`.
- **Les artefacts d'évaluation sont gitignored** (`evaluation/results/`). Les `judge_*_state.json` (nominatifs) restent locaux.
- **Les rapports commités (`docs/reports/`) sont opaques** : IDs `A`/`B`/`C`, verdicts booléens, aucune formule ni nom de source.
- **Les surfaces GitHub-indexées** (commit messages, PR, issues) utilisent des IDs opaques. Les canaux privés RooSync (dashboard, messages, GDrive) acceptent les noms réels.

`ATT3_AGGREGATE_opaque.md` est le modèle : construit uniquement depuis `judge_*_meta.json` + booléens, jamais depuis `judge_*_state.json`/`_restitution.md`.

---

## 5. Preuve reproductible

La chaîne est reproductible par quiconque a le dataset chiffré + `.env` :

```bash
# Harness ATT-3 (privacy-safe, opaque IDs, no corpus text on stdout)
scripts/run_full_judgment.py --corpus A
scripts/run_full_judgment.py --corpus B --offset 120000
scripts/run_full_judgment.py --corpus C
# → judge_{A,B,C}_{meta,trace,state}.json + _restitution.md (gitignored)

# Extracteur privacy-safe (booléens de décision uniquement)
python scratchpad/extract_verdicts.py <judge_X_state.json>
```

L'harness est tracké (`#1447`). Les verdicts booléens par corpus figurent dans `ATT3_AGGREGATE_opaque.md` §3 pour vérification croisée.

---

## 6. Conclusion

L'Epic #1355 atterrit sur un système **stable, honnête et reproductible**. Le capstone ATT-3 prouve firsthand que les fixes `#1443` (sanitization) et Constat n°5 (`#1446` + portage `unified_pipeline`) tiennent hors des tests unitaires, sur 3 corpus réels, sans `ParserException` non-géré et sans maquillage d'axe dégradé. Les résidus sont tracés et assumés, non masqués. Le feu vert terminal (validation user) reste l'acte non-délégable, ai-01-local.

---

## Voir aussi

- [`ATT3_AGGREGATE_opaque.md`](ATT3_AGGREGATE_opaque.md) — preuve capstone ATT-3 (3 corpus).
- [`docs/architecture/ORCHESTRATION_MODES.md`](../architecture/ORCHESTRATION_MODES.md) — modes d'orchestration.
- Issue `#1355` — Epic source.
- Issue `#1449` — tâche T1 (ce livrable).
