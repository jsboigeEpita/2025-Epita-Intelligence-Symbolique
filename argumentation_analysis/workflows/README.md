# `workflows/` — 8 macro-workflows déclaratifs

## Rôle et frontière

Bibliothèque de **définitions** : chaque fichier expose `build_X_workflow() -> WorkflowDefinition` (DSL `WorkflowBuilder` de [`orchestration/workflow_dsl.py`](../orchestration/workflow_dsl.py)) + un wrapper `run_X()` async déléguant à `run_unified_analysis`. **Aucune exécution propre, aucun effet de bord** — pure construction de DAG de phases par capability.

**Disambiguïsation des 3 « workflows »** : ce répertoire = 8 macro-workflows (« Track D macro » + « Track A formal ») ; `orchestration/workflows.py` = le **catalogue** (~20 workflows dont light/standard/full/spectacular, qui importe lazy les 8 d'ici, :1222-1267) ; `plugin_framework/core/plugins/workflows/` = coquille vide (`__init__.py` 0 octet).

## Composants publics (8 paires build/run)

| Module | build | run | Phases réelles (mesurées) |
|---|---|---|---|
| `democratech.py` | :51 | `run_deliberation` :144 | 10 (extract ajouté #1472/#1477 :75-78) |
| `debate_tournament.py` | :52 | `run_tournament` :112 | 6 (LoopConfig convergence 5 % :27-49) |
| `fact_check_pipeline.py` | :24 | `run_fact_check` :75 | 6 |
| `formal_debate.py` | :23 | `run_formal_debate` :97 | 9 |
| `belief_dynamics.py` | :36 | `run_belief_dynamics` :91 | 6 |
| `argument_strength.py` | :22 | `run_argument_strength` :84 | 7 |
| `formal_verification.py` | :55 | `run_formal_verification` :196 | **17** |
| `comprehensive_analysis.py` | :55 | `run_comprehensive_analysis` :131 | 8 (LLM-only, `jvm_required: False` :126) |

`__init__.py:12-56` ré-exporte les 16 symboles (`__all__` :47-56).

## Points d'entrée valides

- [`orchestration/workflows.py:1222-1267`](../orchestration/workflows.py) — enregistre 8 clés catalogue (`democratech`, `debate_tournament`, `fact_check`, `formal_debate`, `belief_dynamics`, `argument_strength`, `formal_verification`, `comprehensive`), chaque bloc sous `try/except` (warning si échec :1230-1231) ; via `get_workflow_catalog()`, atteignables depuis le CLI `run_orchestration.py --workflow <clé>` (résolution `unified_pipeline.py:259-265`) ;
- [`examples/democratech_deliberation/run_democratech_demo.py:91`](../../examples/democratech_deliberation/run_democratech_demo.py) — `run_deliberation` ;
- [`scripts/extract_belief_trajectories.py:730`](../../scripts/extract_belief_trajectories.py) — `build_democratech_workflow`.

## Amont / aval

- Amont : `orchestration/workflow_dsl.py` (`WorkflowBuilder`/`WorkflowDefinition`/`LoopConfig`).
- Aval : `orchestration/unified_pipeline.py::run_unified_analysis` (exécution DAG + CapabilityRegistry) ; rendu [`cli/output_formatter.py`](../cli/README.md).

## Statut d'intégration

**actif** — enregistré dans le catalogue production, consommé par le CLI (`--list-workflows`), un example, un script de mesure, un benchmark documenté (`docs/reports/benchmark_comparative_analysis.md:53-71`), 152 tests unitaires dédiés (5 fichiers sous `tests/unit/argumentation_analysis/workflows/`).

## Artefacts et lecteurs

Aucun — définitions pures (les runs écrivent via unified_pipeline, en aval).

## Tests représentatifs

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/workflows/ -v
```

152 tests (17+28+13+53+41 par fichier) + croisés `orchestration/test_dung_aspic_wiring.py:794,804,814`, `test_workflow_dsl.py:373,386,398`.

## Frères et parent

Parent : [`../README.md`](../README.md) — ne mentionne pas `workflows/`. Frère : [`orchestration/`](../orchestration/README.md) (DSL + catalogue + exécution).

## Limites connues

- docstrings « N-phase » périmées dans 4 fichiers (phases optionnelles ajoutées sans mise à jour) : `formal_verification.py:4` « 14-phase » et `:56` « 10-phase » pour **17** réelles ; `belief_dynamics.py:4` « 5 » vs 6 ; `argument_strength.py:4` « 4 » vs 7 ; `formal_debate.py:4` « 5 » vs 9 ;
- mapping de noms non documenté : clé catalogue `comprehensive` vs `workflow_name="comprehensive_analysis"` (:157) — fonctionne uniquement parce que `custom_workflow` court-circuite le lookup (`unified_pipeline.py:230-231`) ; idem `fact_check` vs module `fact_check_pipeline` ;
- benchmark doc périmé : `docs/reports/benchmark_comparative_analysis.md:55` compte democratech à 9 phases (10 depuis #1477), `:70` formal_verification à 17 ;
- enregistrement catalogue sous `try/except` silencieux (warning log seulement) : un workflow qui échoue à builder disparaît du catalogue sans erreur.
