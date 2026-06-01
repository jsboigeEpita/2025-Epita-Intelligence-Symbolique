# B-11: Audit — `tests/unit/` infra web (services + webapp + interface_web + libs)

**Track**: B-11 #767 (Epic B #743)
**Date**: 2026-06-01
**Author**: Claude Code @ myia-po-2025:2025-Epita-Intelligence-Symbolique
**Scope**: 15 fichiers, 143 tests collectés (dont 1 archivé)

---

## Méthodologie

Même classification a/b/c que B-01 à B-10. Ces 4 répertoires couvrent l'infrastructure web périphérique du CapabilityRegistry :

- `services/` : MCP Server v1 (archivé) + MCP Server v2 (6 fichiers)
- `interface_web/` : Dashboard web (Starlette/FastAPI)
- `libs/` : Client MCP (modèles, session, transport stdio)
- `webapp/` : Orchestrateur webapp (backend/frontend managers)

Ces composants ne sont PAS enregistrés dans `registry_setup.py` — ils sont des **services périphériques** (MCP, web, API) qui consomment le CapabilityRegistry indirectement. La catégorie naturelle pour l'infrastructure critique est **(c) JUSTIFIÉ**.

---

## Scoreboard

| Catégorie | Fichiers | Tests | % |
|-----------|----------|-------|---|
| **(a) Mort** | 1 | 5 | 7% |
| **(b) Non-wiré** | 0 | 0 | 0% |
| **(c) Justifié** | 14 | ~138 | 93% |

---

## Tableau de classification

### (a) DEAD — MCP Server v1 archivé

| # | Fichier | Composant testé | Pourquoi DEAD |
|---|---------|-----------------|---------------|
| 1 | `services/_archived/test_mcp_server.py` | MCP Server v1 | **Archivé** — contient un stub TODO (0 test réel). Le fichier est dans `_archived/`. MCP Server v1 supplanté par v2. |

### (c) JUSTIFIÉ — Infrastructure critique

#### services/test_mcp_server_v2/ (6 fichiers, ~56 tests) — MCP Server v2

| # | Fichier | Composant testé | Rôle | Tests |
|---|---------|-----------------|------|-------|
| 1 | `test_capability_tools.py` | `capability_tools` | Outils MCP pour lister/invoquer capabilities du registry. **Consomme CapabilityRegistry**. | 7 |
| 2 | `test_conversation_tools.py` | `conversation_tools` + `session_manager` | Gestion conversations MCP (start, continue, status). | 7 |
| 3 | `test_main_v2.py` | `mcp_server.main` | Point d'entrée MCP Server v2 (outils, backward compat, sérialisation). | 13 |
| 4 | `test_session_manager.py` | `session_manager` | Lifecycle sessions MCP (CRUD, expiration, eviction, cleanup). | 15 |
| 5 | `test_specialized_tools.py` | `specialized_tools` | Outils spécialisés MCP (quality, counter-arg, debate, governance). **Invoque capabilities via registry**. | 8 |
| 6 | `test_workflow_tools.py` | `workflow_tools` | Outils workflow MCP (catalog, exécution, détails). **Consomme WorkflowDSL**. | 6 |

#### interface_web/ (1 fichier, 17 tests) — Dashboard

| # | Fichier | Composant testé | Rôle | Tests |
|---|---------|-----------------|------|-------|
| 1 | `test_dashboard.py` | `interface_web` dashboard | Templates HTML, routes Starlette/FastAPI, navigation, endpoints API. **Interface de monitoring du pipeline**. | 17 |

#### libs/mcp/client/ (3 fichiers, ~55 tests) — Client MCP

| # | Fichier | Composant testé | Rôle | Tests |
|---|---------|-----------------|------|-------|
| 1 | `test_models.py` | `libs.mcp.client.models` | Data models JSONRPC (Request, Response, Tool, Resource, Prompt). **Protocole MCP**. | 20 |
| 2 | `test_session.py` | `libs.mcp.client.session` | Session client MCP (initialize, list_tools, call_tool, close). | 16 |
| 3 | `test_stdio.py` | `libs.mcp.client.stdio` | Transport stdio MCP (StdioTransport, ProcessStdioTransport). | 19 |

#### webapp/ (4 fichiers, 26 tests) — Orchestrateur webapp

| # | Fichier | Composant testé | Rôle | Tests |
|---|---------|-----------------|------|-------|
| 1 | `test_backend_manager.py` | `BackendManager` | Lifecycle processus backend FastAPI (start, health check, stop). | 9 |
| 2 | `test_frontend_manager.py` | frontend manager | Lifecycle processus frontend React (start, health check, stop). | 7 |
| 3 | `test_unified_web_orchestrator.py` | `UnifiedWebOrchestrator` | Orchestrateur backend + frontend. **Point d'entrée déploiement web**. | 6 |
| 4 | `test_webapp_config.py` | config webapp | Chargement config YAML, defaults, port management. | 4 |

---

## Récit du framework — 3 épisodes

### Épisode 1 : Le MCP Server v1 et sa migration (~2025-Q3-Q4)

Le MCP Server v1 (`_archived/test_mcp_server.py`) était un stub de test TODO qui n'a jamais été implémenté. Le MCP Server v2 a été conçu comme un remplacement complet avec 6 modules fonctionnels (capability tools, conversation tools, main, session manager, specialized tools, workflow tools). Les 56 tests v2 couvrent le lifecycle complet : sérialisation JSONRPC, session CRUD avec eviction, invocation de capabilities via le registry, et orchestration de workflows.

**Trace** : Le test `test_main_v2.py` a 8 tests de sérialisation Safe — signe que la robustesse JSONRPC a été un focus de conception. `test_session_manager.py` teste explicitement l'expiration et l'éviction — problème de production résolu.

### Épisode 2 : Le client MCP et la librairie partagée (~2026-Q1)

Les 3 fichiers dans `libs/mcp/client/` (55 tests) cristallisent la **librairie client MCP**. Le client implémente le protocole JSONRPC complet (models), la gestion de session avec lifecycle (session), et le transport stdio avec subprocess management (stdio). Cette librairie est **indépendante du serveur** — elle pourrait servir à n'importe quel client MCP.

**Trace** : `test_stdio.py` teste `ProcessStdioTransport` avec mock de subprocess — signe que la gestion de processus fils a été un point d'attention (Windows compatibility).

### Épisode 3 : Le dashboard et le déploiement webapp (~2025-Q4 → 2026)

Les 2 modules `interface_web/` et `webapp/` (43 tests) cristallisent la **couche de déploiement web**. Le dashboard (17 tests) teste les templates HTML, les routes Starlette, et la navigation. Le webapp orchestrator (26 tests) gère le lifecycle des processus backend/frontend avec health checks et port management.

**Trace** : `test_backend_manager.py` teste explicitement `test_stop_process_forces_kill_on_timeout` — signe que la gestion des processus zombies a été un problème de production.

---

## Actions recommandées

### Priorité BASSE — MCP Server v1 archivé

| Action | Fichier | Impact |
|--------|---------|--------|
| Supprimer | `services/_archived/test_mcp_server.py` | 1 fichier archivé, stub TODO |

Le fichier est déjà dans `_archived/`. La suppression est cosmétique — pas d'urgence.

---

## Fix-intents ouverts

**Aucun fix-intent ouvert.** Les 14 fichiers actifs sont du code infrastructure critique justifié. L'unique fichier DEAD est déjà archivé.

---

*Généré par Claude Code @ myia-po-2025:2025-Epita-Intelligence-Symbolique*
*Track B-11 #767 — Epic B #743*
