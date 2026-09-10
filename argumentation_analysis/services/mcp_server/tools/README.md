# mcp_server/tools/ — outils MCP v2 (workflows, capacités, conversations, spécialisés)

## Rôle et frontière

Modules d'enregistrement des **outils MCP v2** : 13 outils exposant
l'infrastructure d'orchestration (catalogue de workflows, exécution,
capacités du registry, conversations multi-tours, agents spécialisés) sur le
protocole MCP. Créés par #79 (« modularize MCP server and add 13 new tools »),
dernier toucher #1981.

La frontière exclut : les 10 outils v1 (méthodes de `MCPService` dans
`../main.py:153-660`), le bootstrap/serveur (`../main.py`), les sessions
(`../session_manager.py`), la config (`../server_config.py`), le Dockerfile et
le README (parent).

## Composants publics

Chaque module expose une unique fonction `register_*(mcp, get_registry[, get_session_manager])`
qui définit les outils en closures sous `@mcp.tool()` :

| Module | Outils définis |
|---|---|
| `workflow_tools.py:13` | `list_workflows` (:17, catalogue), `run_workflow` (:50, délègue à `run_unified_analysis`), `get_workflow_details` (:92, DAG + `validate()`) |
| `conversation_tools.py:13` | `start_conversation` (:19), `continue_conversation` (:63, respecte `max_rounds` :87), `get_conversation_status` (:113) ; privé `_execute_round` (:149) via `WorkflowTurnStrategy` (:168-180) |
| `capability_tools.py:13` | `list_capabilities` (:17), `invoke_capability` (:38 — `find_for_capability` :54 puis `provider.invoke` :67), `get_registry_summary` (:80) |
| `specialized_tools.py:13` | `evaluate_quality` (:49, capacité `argument_quality`), `generate_counter_argument` (:61), `run_debate_analysis` (:75), `run_governance_analysis` (:89) — tous via `_invoke_by_capability` (:16-46) |
| `_serialization.py:7` | `safe_serialize` — dataclass/enum/set → JSON ; seul helper partagé (importé par les 4 modules) |

## Points d'entrée valides

Unique importateur production : `../main.py:693-711` (`_register_v2_tools`,
main.py:686), appelé depuis `MCPService.__init__` (main.py:130).
L'enregistrement est **fail-silent par design** : main.py:714-715 avale toute
exception (« V2 tools not registered ») pour préserver les 10 outils v1.
Lancement du serveur : script direct `../main.py:734-738` (affiche
« 23 outils ») ou Docker (`../Dockerfile:33` — chemin périmé, cf. limites).
Aucun importateur production de `MCPService` dans le repo (seuls
`__init__.py:3` et les tests).

## Amont / aval

- **Amont (consommé)** : `orchestration/unified_pipeline`
  (`get_workflow_catalog` workflow_tools.py:24,99 ; `run_unified_analysis`
  :66 ; `setup_registry` main.py:667 ; `CAPABILITY_STATE_WRITERS`
  conversation_tools.py:157), `orchestration/conversational_executor.WorkflowTurnStrategy`
  (conversation_tools.py:160-162), `CapabilityRegistry` via getter injecté,
  SDK pip `mcp` 2.x (`main.py:23`, #1559).
- **Aval (consommateurs)** : `mcp_server/main.py` seul en production. Tests :
  `tests/unit/services/test_mcp_server_v2/` (7 fichiers, 60 tests),
  `tests/unit/argumentation_analysis/services/test_mcp_server.py` (70 tests,
  sections v2 :920-975), `tests/integration/services/test_mcp_server_integration.py`
  (5). Les lanes cassettes LLM excluent explicitement `test_mcp_server_v2`
  (`replay-llm-lane.yml:80`, `record-llm-cassettes.yml:106`).

## Statut d'intégration

| Famille | Statut | Preuve |
|---|---|---|
| Outils workflow | **actif** | câblés `main.py:706` ; chemin production `run_unified_analysis` (workflow_tools.py:71) ; contrat réel sur vrai `MCPServer` (`test_real_server_tool_registration.py`, #1576) |
| Outils capacité | **actif** | `main.py:710` ; `find_for_capability` est l'unique spelling production du resolver (capability_tools.py:54) |
| Outils conversation | **actif** à l'enregistrement | `main.py:707-709`, 7 tests — mais continuité d'état inopérante (cf. limites) |
| Outils spécialisés | **actif** | `main.py:711`, 8 tests ; docstring gouvernance alignée #1981 (specialized_tools.py:92-98) |

## Artefacts et lecteurs

Dicts JSON sérialisés (`safe_serialize`) renvoyés sur transport
`streamable-http` port 8000 (`main.py:719-730`, `server_config.py:13`).
Lecteurs : clients MCP externes (Claude Desktop, Cursor… documentés dans le
[README parent](../README.md)).

## Tests représentatifs

```bash
conda run -n projet-is-roo-new --no-capture-output pytest \
  tests/unit/services/test_mcp_server_v2/ -v

conda run -n projet-is-roo-new --no-capture-output pytest \
  "tests/unit/argumentation_analysis/services/test_mcp_server.py" \
  tests/integration/services/test_mcp_server_integration.py -v
```

## Frères et parent

- Parent : [mcp_server/](../) — README parent : [../README.md](../README.md)
  (orienté utilisateur : build Docker + config client ; ne documente pas
  `tools/`).
- Fichiers frères : `../main.py` (bootstrap + outils v1),
  `../session_manager.py`, `../server_config.py`.

## Limites connues

- Fail-silent v2 (`main.py:714`) : une régression d'import dans `tools/`
  dégrade silencieusement le serveur à 10 outils.
- `session.state` n'est jamais assigné dans le repo (défaut `None`,
  `session_manager.py:22`) : les `state_writers`
  (conversation_tools.py:171) et `state=session.state` (:180) sont toujours
  `None` — aucune continuité d'état inter-rounds, `CAPABILITY_STATE_WRITERS`
  mort sur ce chemin.
- `../Dockerfile:33` lance `python services/mcp_server/main.py` (chemin
  racine inexistant depuis la migration #34) sous l'env conda `projet-is-v2`
  périmée — l'image Docker ne peut pas démarrer le serveur.
- La docstring de `generate_counter_argument` (specialized_tools.py:64-65)
  liste des types de contre-argument qui ne correspondent à aucune des deux
  énumérations réelles (`agents/core/counter_argument/definitions.py:15-22,34-41`).
- `run_mcp_tests.ps1:4` cible `tests/unit/services/test_mcp_server.py`,
  inexistant (le chemin vivant est
  `tests/unit/argumentation_analysis/services/test_mcp_server.py`).
