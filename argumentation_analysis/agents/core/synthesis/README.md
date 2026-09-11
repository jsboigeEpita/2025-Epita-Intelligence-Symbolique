# `agents/core/synthesis/` — deux agents de synthèse distincts, un seul vivant

## Rôle et frontière

5 fichiers, 2 806 lignes. Le module porte **deux agents qui ne sont pas la même chose** et qu'il ne faut pas confondre :

- `SynthesisAgent` (`synthesis_agent.py`) — l'ancien : orchestre des analyses logiques/informelles et les agrège dans un `UnifiedReport`. **Il est importable, instanciable, et fonctionnellement inerte** (voir *Statut d'intégration*) ;
- `DeepSynthesisAgent` (`deep_synthesis_agent.py`) — le vivant : consomme un `UnifiedAnalysisState` déjà peuplé et rend un rapport markdown grounded en 9 sections. C'est **le livrable narratif canonique du workflow spectacular**.

Les deux sont exportés par `__init__.py` :11-14 (6 noms). Frontière : le module ne fait **aucune analyse primaire** — il agrège un état produit ailleurs (voir *Amont / aval*).

## Composants publics

- `synthesis_agent.py` — `SynthesisAgent` :26 (hérite `BaseAgent`) ; point d'entrée `synthesize_analysis` :154, `invoke_single` :691, `get_response` :699 ; auto-description `get_agent_capabilities` :130 ;
- `data_models.py` — `LogicAnalysisResult` :16, `InformalAnalysisResult` :69, `UnifiedReport` :123 (+ `to_dict` :169, `to_json` :188, `get_summary_statistics` :200) ;
- `deep_synthesis_agent.py` — `DeepSynthesisAgent` :41 ; `synthesize` :252, `invoke_single` :234, `get_response` :244, `render_markdown` :732 (statique), `validate_value_gates` :1387, `count_populated_artifact_fields` :1113, `build_artifact_briefing` :1205, `grounded_transversal_synthesis` :1339 ; 10 constructeurs statiques `_build_*` :369-1151 ;
- `deep_synthesis_models.py` — 11 dataclasses ; agrégat `DeepSynthesisReport` :126, à ne pas confondre avec `UnifiedReport`.

`__init__.py` exporte 6 noms, tous réels — zéro fantôme.

## Points d'entrée valides

1. **Phase workflow (le chemin vivant)** : `capability="deep_synthesis"` — `orchestration/workflows.py:1012-1013`, `optional=False`, `depends_on=["belief_revision", "stakes"]` (:1014-1017), `timeout_seconds=180` → résolu par `registry_setup.py:699-711` (`name="deep_synthesis_service"`, `capabilities=["deep_synthesis"]`, `invoke=_invoke_deep_synthesis`) → `orchestration/invoke_callables.py:10094` ;
2. **Post-phase conversationnelle** : `orchestration/conversational_orchestrator.py:1612` (`_invoke_deep_synthesis` importé puis appelé :1628, sous garde `if spectacular and _budget_allows("deep_synthesis")` :1609) ;
3. **API agent directe** — signatures réelles (lues, non inventées) :
   `DeepSynthesisAgent(kernel, agent_name="DeepSynthesisAgent", service_id=None, deanonymized=True)` :201 → `await agent.synthesize(state, transcript=None, source_metadata=None) -> DeepSynthesisReport` :252 → `DeepSynthesisAgent.render_markdown(report) -> str` :732 ;
4. **Pipeline « original » (chemin dégradé)** : `pipelines/unified_pipeline.py:333` → `run_unified_text_analysis_pipeline` → `pipelines/unified_text_analysis.py:516` `await synthesis_agent.synthesize_analysis(text=text)` (`SynthesisAgent`) ;
5. `SynthesisAgent(kernel, agent_name="SynthesisAgent", enable_advanced_features=False, service_id=None)` :56 → `await agent.synthesize_analysis(text) -> UnifiedReport` :154.

Aucun de ces appels n'est reconstruit : chacun est lu à la ligne citée.

## Amont / aval

- **Amont** (deep) : `core/shared_state.py` `UnifiedAnalysisState` — lu via `getattr(state, …)` (`identified_arguments`, `identified_fallacies`, `dung_frameworks`, `jtms_retraction_chain`, `stakes_and_stakeholders`, `analysis_trace`) ; phases `belief_revision` et `stakes` (déclarées `depends_on`, `workflows.py:1014-1017`) ;
- **Aval** (deep) : `state.narrative_synthesis` (écrit par `_write_deep_synthesis_to_state`, `state_writers.py:1911`, enregistré dans `CAPABILITY_STATE_WRITERS["deep_synthesis"]` :2323) — lu ensuite par **Acte II** (`workflows.py:1036-1044`, `depends_on=["deep_synthesis"]`) et **Acte III**, plus le rendu markdown sur disque ;
- **Amont** (SynthesisAgent) : ses propres `_run_formal_analysis` :408 / `_run_informal_analysis` :450 — qui échouent par construction ;
- **Aval** (SynthesisAgent) : `unified_results["synthesis_report"] = synthesis_result.executive_summary` (`unified_text_analysis.py:518-527`).

## Statut d'intégration

Deux familles, deux statuts mesurés.

**`DeepSynthesisAgent` + `deep_synthesis_models` — `actif-critique`.** Preuve : 1 entrée registry (`registry_setup.py:704`), 1 littéral de phase production non-optionnel (`workflows.py:1013`), 1 invoker (`invoke_callables.py:10094`), 1 writer (`state_writers.py:1911`/`:2323`), 2 appelants (workflow + post-phase conversationnelle). C'est la phase terminale du workflow spectacular et la source de `narrative_synthesis`, dont dépendent Actes II et III.

**`SynthesisAgent` + `data_models` — `compatibilité`.** Importable et instancié par 3 modules de production (`conversation_orchestrator.py:569`, `unified_text_analysis.py:258`, `operational/direct_executor.py:40`), mais **inerte** : ses deux délégations lèvent inconditionnellement.
- `_get_logic_agent` :490-492 `raise NotImplementedError("MockLogicAgent éliminé…")` — le cache testé :488 est initialisé `{}` :78 et **jamais écrit hors tests** (toutes les occurrences de `_logic_agents_cache` :47/:78/:488/:494 sont dans ce fichier ; la seule écriture externe est `tests/…/test_synthesis_agent.py:292`) ;
- `_get_informal_agent` :501-503 `raise NotImplementedError("MockInformalAgent éliminé…")`, `_informal_agent` valant `None` :79 sans jamais être assigné.

Ces exceptions sont **avalées** par les `try/except` :444 et :478, qui écrivent une *chaîne d'erreur* dans `result.propositional_result` / `result.arguments_structure`. `synthesize_analysis` **retourne donc un `UnifiedReport` dégénéré, sans lever** : appelant et tests voient un objet valide. Le commentaire d'en-tête :489/:499 (`MOCKS ÉLIMINÉS PHASE 3`) documente le retrait — rien d'authentique n'a pris la place.

## Artefacts et lecteurs

- Rapport markdown 9 sections, écrit sur disque si `context["deep_synthesis_output_path"]` est posé (`invoke_callables.py:10202-10207`) ;
- Dictionnaire de retour (`invoke_callables.py:10210-10226`) : `report`, `markdown`, `sections_populated`, `total_state_fields`, `grounded_synthesis`, `grounded_synthesis_status`, `value_gates`, `populated_artifact_fields` ;
- Persistance d'état : `state.narrative_synthesis` (le `grounded_synthesis`), et `state.workflow_results["deep_synthesis_value_gates"]` (l'état n'a pas d'attribut dédié, `state_writers.py:1950-1955`).

Lecteurs aval : Actes II/III (restitution), les tests de wiring, `scripts/run_real_analysis.py:303` (voir *Limites connues*).

## Tests représentatifs

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/test_deep_synthesis_agent.py -v
```

**277 `def test_` sur 15 fichiers** qui importent le paquet (comptage : `for f in $(grep -rl "agents\.core\.synthesis\|deep_synthesis_agent\|DeepSynthesisAgent" tests/ --include=*.py); do grep -c "def test_" $f; done`, total 277). Principaux : `test_deep_synthesis_agent.py` (61), `test_fb18_grounded_synthesis.py` (21), `test_deep_synthesis_wiring.py` (11), `test_track_nn_adjudication.py` (12), `test_stakes_extractor.py` (12), `test_synthesis_agent.py` (31), `agents/core/synthesis/test_synthesis_agent.py` (28).

Garde dédiée : `orchestration/test_one_capability_surface_1842.py` (4 tests) — voir *Limites connues*.

## Frères et parent

Parent : [`../README.md`](../README.md) (agents/core, sans README de lot). Frères du même niveau : [`../counter_argument/README.md`](../counter_argument/README.md), [`../quality/`](../quality/) (sans README), [`../debate/`](../debate/), [`../governance/`](../governance/) — les quatre autres « spécialistes » de la découpe #1842.

## Limites connues

Tout ce qui suit est **constaté, non corrigé** (mission read-only).

1. **Deux champs déclarés et sérialisés mais jamais produits.** `UnifiedReport.logic_informal_alignment` (`data_models.py:156`) et `UnifiedReport.analysis_completeness` (`:158`) sont exportés par `to_dict()` (`:181-182`) et lus par des tests (`test_synthesis_data_models.py:275-276` assertent `is None`), mais **aucune affectation en production** : `unify_results` (`synthesis_agent.py:258-288`) ne pose que `executive_summary`, `overall_validity`, `confidence_level`, `contradictions_identified`, `recommendations`. Un consommateur du JSON reçoit deux clés toujours nulles.
2. **`ArgumentMapEntry.attacks` déclaré, vide par construction, jamais lu.** `deep_synthesis_models.py:35` ; `_build_argument_map` passe `attacks=[]` avec le raisonnement explicite (`deep_synthesis_agent.py:447`, commentaire :444-446 : toute clé d'`attack_map` est un nœud synthétique, jamais un argument) ; `render_markdown` ne lit que `a.attacked_by` (`:764`). Le champ est du contrat mort assumé et documenté (#1647) — mais mort.
3. **Attributs dynamiques non déclarés sur `DeepSynthesisReport`.** `report._raw_stakes` (`deep_synthesis_agent.py:308`/`:310`) et `report._raw_analysis_trace` (`:314`) sont posés sur une dataclass **qui n'a pas de `__slots__`** (vérifié : `grep __slots__ deep_synthesis_models.py` → aucun). Fonctionne à l'exécution (relus par `getattr(…, {})` :1514, `getattr(…, [])` :1592) — **pas un défaut d'exécution**, mais un **défaut de typage statique** (attribut absent du modèle) et une asymétrie : le chemin de repli de `_invoke_deep_synthesis` (`invoke_callables.py:10169-10193`) construit le rapport sans passer par `synthesize`, donc sans jamais poser ces attributs.
4. **Surface de production trompeuse pour `SynthesisAgent`.** `get_agent_capabilities` :130-152 annonce `synthesis_coordination`, `formal_analysis_orchestration`, `informal_analysis_orchestration`, `unified_reporting` — **aucune n'existe comme entrée `CapabilityRegistry`** (aucun `register_agent`/`register_service` pour cet agent). C'est un dictionnaire d'auto-description, pas un câblage. `AgentType.SYNTHESIS → "SynthesisAgent"` (`config/unified_config.py:237`) reste déclaré dans plusieurs listes d'agents.
5. **Lecteur d'une phase retirée.** `scripts/run_real_analysis.py:303` liste encore `("analysis_synthesis", "7b. Synthèse d'analyse (phase \`synthesis\`)")`. La phase `analysis_synthesis` a été retirée en #1625/R759 (`workflows.py:1007` le consigne ; les tests verrouillent son absence : `test_synthesis_spectacular.py:17`, `:115`, `:117`). La clé étant un `snap.get(...)`, le script dégrade en section vide — mais le libellé désigne une phase qui n'existe plus.
6. **Inerte ≠ mort : ne pas lire un `import` comme une activité.** Les appels de `conversation_orchestrator.py:569` et `unified_text_analysis.py:258` atteignent du code qui lève puis avale (limite 4 ci-dessus). `operational/direct_executor.py:40` n'a **aucun importeur de production** (seul `operational/test_conversation_history.py:4`, un test colocalisé dans le paquet).
7. **Collision de nom.** `synthesis/data_models.UnifiedReport` n'a rien à voir avec `reporting/document_assembler.UnifiedReportTemplate` : un `grep UnifiedReport` sur-dénombre (les occurrences `reporting/` concernent l'autre type).
8. **La ligne #1842 est bien fermée ici.** Aucune seconde surface : `deep_synthesis_agent.py:1661-1664` porte le commentaire de retrait, et `grep register_with_capability_registry` ne trouve **aucun** définisseur dans ce paquet. Le seul survivant légitime est `counter_argument/__init__.py:43`, importé et appelé par `registry_setup.py:100`. Aucune trace de la capacité retirée `analysis_synthesis`.
