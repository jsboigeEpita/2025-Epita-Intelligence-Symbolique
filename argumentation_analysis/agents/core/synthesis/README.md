# `agents/core/synthesis/` — l'agent de synthèse grounded

## Rôle et frontière

3 fichiers, ~2 400 lignes. Le module porte **un** agent de synthèse :

- `DeepSynthesisAgent` (`deep_synthesis_agent.py`) — consomme un `UnifiedAnalysisState` déjà peuplé et rend un rapport markdown grounded en 9 sections. C'est **le livrable narratif canonique du workflow spectacular**.

L'ancien `SynthesisAgent` (`synthesis_agent.py`) et ses `data_models` (`UnifiedReport`, `LogicAnalysisResult`, `InformalAnalysisResult`) ont été **retirés (#2140)** : la classe était fonctionnellement inerte (ses deux fabriques d'agents internes levaient inconditionnellement — aucun code de production ne peuplait leurs caches — et les `except` environnants écrivaient le texte de l'exception dans des champs de résultat, une panne voyageant comme une donnée, forme #1019). Le câbler aurait dupliqué les analyses informelle et formelle que le pipeline appelant exécutait déjà ; la surface de synthèse réelle est `DeepSynthesisAgent`.

Frontière : le module ne fait **aucune analyse primaire** — il agrège un état produit ailleurs (voir *Amont / aval*).

## Composants publics

- `deep_synthesis_agent.py` — `DeepSynthesisAgent` :41 ; `synthesize` :252, `invoke_single` :234, `get_response` :244, `render_markdown` :732 (statique), `validate_value_gates` :1387, `count_populated_artifact_fields` :1113, `build_artifact_briefing` :1205, `grounded_transversal_synthesis` :1339 ; 10 constructeurs statiques `_build_*` :369-1151 ;
- `deep_synthesis_models.py` — 11 dataclasses ; agrégat `DeepSynthesisReport` :126.

`__init__.py` exporte 2 noms (`DeepSynthesisAgent`, `DeepSynthesisReport`), tous réels — zéro fantôme. Une garde dédiée verrouille l'absence de la surface retirée : `tests/unit/argumentation_analysis/agents/core/synthesis/test_no_inert_synthesis_surface.py`.

## Points d'entrée valides

1. **Phase workflow (le chemin vivant)** : `capability="deep_synthesis"` — `orchestration/workflows.py:1012-1013`, `optional=False`, `depends_on=["belief_revision", "stakes"]` (:1014-1017), `timeout_seconds=180` → résolu par `registry_setup.py:699-711` (`name="deep_synthesis_service"`, `capabilities=["deep_synthesis"]`, `invoke=_invoke_deep_synthesis`) → `orchestration/invoke_callables.py:10094` ;
2. **Post-phase conversationnelle** : `orchestration/conversational_orchestrator.py:1612` (`_invoke_deep_synthesis` importé puis appelé :1628, sous garde `if spectacular and _budget_allows("deep_synthesis")` :1609) ;
3. **API agent directe** — signatures réelles (lues, non inventées) :
   `DeepSynthesisAgent(kernel, agent_name="DeepSynthesisAgent", service_id=None, deanonymized=True)` :201 → `await agent.synthesize(state, transcript=None, source_metadata=None) -> DeepSynthesisReport` :252 → `DeepSynthesisAgent.render_markdown(report) -> str` :732.

Aucun de ces appels n'est reconstruit : chacun est lu à la ligne citée.

## Amont / aval

- **Amont** (deep) : `core/shared_state.py` `UnifiedAnalysisState` — lu via `getattr(state, …)` (`identified_arguments`, `identified_fallacies`, `dung_frameworks`, `jtms_retraction_chain`, `stakes_and_stakeholders`, `analysis_trace`) ; phases `belief_revision` et `stakes` (déclarées `depends_on`, `workflows.py:1014-1017`) ;
- **Aval** (deep) : `state.narrative_synthesis` (écrit par `_write_deep_synthesis_to_state`, `state_writers.py:1911`, enregistré dans `CAPABILITY_STATE_WRITERS["deep_synthesis"]` :2323) — lu ensuite par **Acte II** (`workflows.py:1036-1044`, `depends_on=["deep_synthesis"]`) et **Acte III**, plus le rendu markdown sur disque.

## Statut d'intégration

**`DeepSynthesisAgent` + `deep_synthesis_models` — `actif-critique`.** Preuve : 1 entrée registry (`registry_setup.py:704`), 1 littéral de phase production non-optionnel (`workflows.py:1013`), 1 invoker (`invoke_callables.py:10094`), 1 writer (`state_writers.py:1911`/`:2323`), 2 appelants (workflow + post-phase conversationnelle). C'est la phase terminale du workflow spectacular et la source de `narrative_synthesis`, dont dépendent Actes II et III.

**`SynthesisAgent` + `data_models` — retirés (#2140).** Aucune classe éponyme inerte n'est plus exportée du paquet ; les portes d'instanciation (`pipelines/unified_text_analysis.py`, `orchestration/conversation_orchestrator.py`, `orchestration/operational/direct_executor.py` — ce dernier supprimé, zéro importeur de production) ont été nettoyées dans le même lot.

## Artefacts et lecteurs

- Rapport markdown 9 sections, écrit sur disque si `context["deep_synthesis_output_path"]` est posé (`invoke_callables.py:10202-10207`) ;
- Dictionnaire de retour (`invoke_callables.py:10210-10226`) : `report`, `markdown`, `sections_populated`, `total_state_fields`, `grounded_synthesis`, `grounded_synthesis_status`, `value_gates`, `populated_artifact_fields` ;
- Persistance d'état : `state.narrative_synthesis` (le `grounded_synthesis`), et `state.workflow_results["deep_synthesis_value_gates"]` (l'état n'a pas d'attribut dédié, `state_writers.py:1950-1955`).

Lecteurs aval : Actes II/III (restitution), les tests de wiring, `scripts/run_real_analysis.py:303` (voir *Limites connues*).

## Tests représentatifs

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/test_deep_synthesis_agent.py -v
```

Les tests du paquet vivent dans `test_deep_synthesis_agent.py` (61), `test_fb18_grounded_synthesis.py` (21), `test_deep_synthesis_wiring.py` (11), `test_track_nn_adjudication.py` (12), plus la garde de surface `agents/core/synthesis/test_no_inert_synthesis_surface.py` (2).

Garde dédiée : `orchestration/test_one_capability_surface_1842.py` (4 tests) — voir *Limites connues*.

## Frères et parent

Parent : [`../README.md`](../README.md) (agents/core, sans README de lot). Frères du même niveau : [`../counter_argument/README.md`](../counter_argument/README.md), [`../quality/`](../quality/) (sans README), [`../debate/`](../debate/), [`../governance/`](../governance/) — les quatre autres « spécialistes » de la découpe #1842.

## Limites connues

1. **`ArgumentMapEntry.attacks` déclaré, vide par construction, jamais lu.** `deep_synthesis_models.py` ; `_build_argument_map` passe `attacks=[]` avec le raisonnement explicite (toute clé d'`attack_map` est un nœud synthétique, jamais un argument) ; `render_markdown` ne lit que `a.attacked_by`. Le champ est du contrat mort assumé et documenté (#1647) — mais mort.
2. **Attributs dynamiques non déclarés sur `DeepSynthesisReport`.** `report._raw_stakes` et `report._raw_analysis_trace` (`deep_synthesis_agent.py:308`/`:310`/`:314`) sont posés sur une dataclass **qui n'a pas de `__slots__`**. Fonctionne à l'exécution (relus par `getattr(…, {})` :1514, `getattr(…, [])` :1592) — **pas un défaut d'exécution**, mais un **défaut de typage statique** (attribut absent du modèle) et une asymétrie : le chemin de repli de `_invoke_deep_synthesis` (`invoke_callables.py:10169-10193`) construit le rapport sans passer par `synthesize`, donc sans jamais poser ces attributs.
3. **Lecteur d'une phase retirée.** `scripts/run_real_analysis.py:303` liste encore `("analysis_synthesis", "7b. Synthèse d'analyse (phase \`synthesis\`)")`. La phase `analysis_synthesis` a été retirée en #1625/R759 (`workflows.py:1007` le consigne ; les tests verrouillent son absence : `test_synthesis_spectacular.py:17`, `:115`, `:117`). La clé étant un `snap.get(...)`, le script dégrade en section vide — mais le libellé désigne une phase qui n'existe plus.
4. **La ligne #1842 est bien fermée ici.** Aucune seconde surface : `deep_synthesis_agent.py:1661-1664` porte le commentaire de retrait, et `grep register_with_capability_registry` ne trouve **aucun** définisseur dans ce paquet. Le seul survivant légitime est `counter_argument/__init__.py:43`, importé et appelé par `registry_setup.py:100`. Aucune trace de la capacité retirée `analysis_synthesis`.
