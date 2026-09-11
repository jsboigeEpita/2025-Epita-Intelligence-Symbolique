# `reporting/restitution/` — moteur de restitution structurée (actes + annexes + gate)

## Rôle et frontière

19 modules + `__init__` (9 335 lignes) — le moteur qui transforme l'état d'analyse en **restitution lisible** : 3 actes narratifs (cadrage, narratif, conclusion), annexes techniques, gate de lisibilité, identification vertueuse. C'est la couche « rendre compte », pas la couche analyser : elle consomme `UnifiedAnalysisState` et produit la prose.

## Composants publics

- Squelette : `acts.py` (`ACT_TITLES` :22, `RestitutionActs` :30), `renderer.py` (`RenderedReport` :72, `RestitutionReportRenderer` :79, `render_restitution_report` :244), `appendix.py` (`render_appendix` :539) ;
- Qualité : `readability_gate.py` (`GateVerdict` :193, `ReadabilityGate` :369, `ReaderCheckResult` :567), `conclusion_salience.py` (`assess_conclusion_salience` :263) ;
- Identification : `virtuous_identification.py` (`ExtractProfile` :118, `VirtuousCandidate` :152, `VirtuousInventory` :170, `identify` :225, `render_inventory_report` :300, `detect_virtuous_mode` :505) ;
- Actes : `act1_framing` (667 l.), `act2_narrative` (1 558 l.), `act3_conclusion` (2 646 l.) ;
- Prose partagée : `fr_accord.py` (`accord` :17), `formal_derivation.py` (`extract_tested_content` :87), `specialist_roles.py` (`classify_specialist_roles` :145), `dung_reader.py` (`appendix_ref` :95, `appendix_refs_in` :105, `backend_provenance` :114), `global_projection.py` (`GlobalFinding` :45, `project_global_findings` :61), `factual_consistency_check.py` (`check_factual_consistency` :150), `native_dung.py` (210 l.) ;
- Adaptateurs : `pipeline_adapter.py` (279 l.), `conversational_adapter.py` (248 l.), `state_adapter.py` (`state_to_appendix_mapping` :97).

`__init__.py` (49 l.) exporte 15 noms — tous vérifiés réels, zéro fantôme.

## Points d'entrée valides

1. **Pipeline** : `run_orchestration.py --mode pipeline` → `orchestration/unified_pipeline.py:418-422` — `render_spectacular_restitution(state)` → clé de résultat `restitution_report` (:422) ;
2. **Phases workflow** : `capability=act1_framing` / `act2_narrative` / `act3_conclusion` → `orchestration/invoke_callables.py` `_invoke_act1_framing` :9235, `_invoke_act2_narrative` :9115, `_invoke_act3_conclusion` :9338 (appels :9130/9250/9354) → `state_writers.py:1890` ;
3. **Conversationnel** : `orchestration/conversational_orchestrator.py:1795-1800` ;
4. **CLI dédiées** : `scripts/run_virtuous_restitution.py:171,284` (`__main__`), `scripts/scan_virtuous_corpus.py:181,210` (argparse).

## Amont / aval

- Amont : `core/shared_state.py` (`UnifiedAnalysisState`), taxonomie qualité.
- Aval : résultat pipeline `restitution_report`, scripts d'analyse de corpus vertueux, bundle spectacular.

## Statut d'intégration

**actif-critique** — 4 familles de points d'entrée production mesurées (pipeline, phases workflow, conversationnel, CLI), 616 `def test_` sur 33 fichiers. C'est la sortie finale du système : tout ce que les autres axes calculent atterrit ici.

## Artefacts et lecteurs

Rapports rendus (prose + annexes). Lecteurs : l'utilisateur final (restitution), le bundle spectacular (`scripts/analysis/generate_spectacular_bundle.py`), le notebook `docs/coursia_contrib/restitution_evidential_roles.ipynb` (rôles/actualisation).

## Tests représentatifs

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/reporting/restitution/ -v
```

**616 `def test_`** sur 33 fichiers + tests croisés orchestration/plugins (track B/C, structured_arg, belief_revision, conclusion_strategy #1668, narrative dung decoder #1912).

## Frères et parent

Parent : `reporting/` (sans README). Amont : [`../../orchestration/`](../../orchestration/README.md) (les `_invoke_act*`), [`../../core/`](../../core/README.md) (état partagé).

## Limites connues

- `conclusion_salience` et `specialist_roles` n'ont pas d'importeur production **externe** direct — consommés en interne (act2 :56-60, act3 :67) et par le notebook : c'est du découplage, pas de la mort ;
- le gate de lisibilité (`readability_gate.py`, 585 l.) n'est câblé que côté vérification — son verdict ne bloque aucune écriture (à confirmer par le coordinateur si un blocage est attendu).
