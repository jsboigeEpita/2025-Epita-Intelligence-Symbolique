# `agents/utils/` — navigation taxonomique et traçage d'agents

## Rôle et frontière

Trois fichiers suivis + un fossile disque. Ce ne sont **pas** les utils généraux du dépôt ([`argumentation_analysis/utils/`](../../utils/README.md)) : ce répertoire ne sert que les agents.

- `__init__.py` (3 l.) — docstring seule, aucun export ;
- `taxonomy_navigator.py` (193 l.) — `TaxonomyNavigator` (:8) : navigation d'une taxonomie **déjà chargée** (rows PK/path/depth) — `get_node` :40, `get_node_by_path` :46, `get_root_nodes` :52, `get_children` :65, `get_parent` :96, `is_leaf` :114, `get_branch_as_str` :120, `get_taxonomy_preview` :144, `get_taxonomy_as_json` :187 ;
- `tracer.py` (138 l.) — `TracedAgent` (:21) : proxy async qui journalise la ChatHistory avant/après `invoke` (:103).

## Composants publics

`TaxonomyNavigator`, `TracedAgent`. (L'`__init__` n'exporte rien.)

## Points d'entrée valides

- `TaxonomyNavigator` : `plugins/fallacy_workflow_plugin.py:40` et `plugins/exploration_plugin.py:16` (plugins du tronc commun), `evaluation/plugin_benchmark.py:538` (lazy), `scripts/analyze_taxonomy.py:27` (lazy). Chaîne workflow : `fallacy_workflow_plugin` ← `orchestration/registry_setup.py:249,274` ← `invoke_callables.py:2853,5309,5751`.
- `TracedAgent` : `agents/factory.py:19`, instancié :336, :383, :465 quand `trace_log_path` est fourni — usine utilisée par `analysis_runner_v2.py:221,234`, `cluedo_orchestrator.py:142`, `cluedo_extended_orchestrator.py:253`, `informal_agent_adapter.py:76-77`.

## Amont / aval

- Amont : `argumentation_analysis/utils/taxonomy_local_overrides.render_alias` (taxonomy_navigator.py:5), stdlib logging.
- Aval taxonomie : prompts des plugins fallacy/exploration (prévisualisations/JSON). Aval tracer : fichier de log de traçage.

## Statut d'intégration

**actif** — `TaxonomyNavigator` : 4 importeurs production mesurés ; `TracedAgent` : 3 sites d'instanciation dans l'usine production.

## Artefacts et lecteurs

Aucun artefact du dépôt. Le tracer écrit un log de traçage (chemin passé par l'appelant).

## Tests représentatifs

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/agents/utils/test_taxonomy_navigator.py tests/agents/factories/test_agent_factory.py -v
```

44 `def test_` pour le navigateur ; tracer couvert via les tests factory (~4 liés à l'enveloppe).

## Frères et parent

Parent : [`../README.md`](../README.md). Consommateurs : plugins du tronc commun ([`../../README.md`](../../README.md)), [`../factory.py`](../README.md).

## Limites connues

- docstring fossile : `taxonomy_navigator.py:10` prétend charger « from a CSV or JSON file » — la classe ne charge rien et **lève** sur un chemin (TypeError :19-22, fix #2041) ;
- imports inutilisés : `csv` (taxonomy_navigator.py:1) ; `json`/`List`/`Optional`/`Kernel`/`Agent`/`StreamingChatMessageContent` (tracer.py:3-11) ;
- `informal_optimization/` : 0 fichier suivi (uniquement `__pycache__` local + sous-répertoire vide `taxonomy_analysis/`) — fossile disque invisible à `git ls-files`, présent sur les clones ayant exécuté l'ancien code.
