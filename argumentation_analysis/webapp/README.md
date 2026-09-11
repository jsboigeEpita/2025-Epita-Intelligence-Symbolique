# `webapp/` — orchestrateur de lancement et de test de la webapp

## Rôle et frontière

`orchestrator.py` (1850 lignes, exécutable) : démarre backend + frontend React, exécute les tests Playwright, trace, nettoie les processus. **Ne sert aucun contenu lui-même** — c'est un harness d'intégration. `__init__.py` vide.

**Disambiguïsation web (qui sert quoi)** :

| Surface | Rôle | Preuve |
|---|---|---|
| `argumentation_analysis/webapp/` (ici) | **Lanceur/harness** d'intégration | `orchestrator.py` entier |
| `api/main.py` (racine) | Le **vrai backend FastAPI** (7 routers) — cible du lancement | `config/webapp_config.yml` `module: api.main:app` ; défaut code `orchestrator.py:225` |
| `interface_web/app.py` (racine) | Proxy **Starlette frontend-only** (modèle 2-serveurs séparé) — **pas** lancé par cet orchestrateur | docstring :4-25 (issue #844) |
| [`services/web_api/`](../services/web_api/README.md) | Module service web + source du build React lancé | config :24 |

## Composants publics

- `UnifiedWebOrchestrator` (`orchestrator.py:610`) — classe principale : config YAML fusionnée (`_load_config` :720, fallback création défaut :726-732), signal handlers :665, shutdown :684 ;
- `MinimalProcessCleaner` :82 (nettoyage par port ; par nom désactivé :93-97), `MinimalBackendManager` :171 (lance `uvicorn api.main:app` :225-233, attend « Application startup complete » :207-210), `MinimalFrontendManager` :409 (`npm start`) ;
- dataclasses d'état : `WebAppStatus` :574, `TraceEntry` :585, `WebAppInfo` :597 ;
- `main()` :1706 — CLI : `--config` (défaut `config/webapp_config.yml` local :1720), `--start/--stop/--test/--integration` (défaut), `--frontend`, `--no-playwright`, `--exit-after-start`, `--timeout` ;
- `config/webapp_config.yml` (46 l.) — backend `api.main:app` port 5003 + fallbacks 5004-5006, `health_endpoint` :8, playwright `tests/functional/` :38, cleanup kill `python*`/`node*` :15-17.

## Points d'entrée valides

- Production : [`scripts/orchestration/pipelines/run_web_e2e_pipeline.py:29`](../../scripts/orchestration/pipelines/run_web_e2e_pipeline.py) — importe `UnifiedWebOrchestrator` ;
- Tests : `tests/fixtures/integration_fixtures.py:667`, `tests/integration/webapp/test_full_webapp_lifecycle.py:9`, `tests/unit/webapp/` (4 fichiers).

## Amont / aval

- Amont : `project_core/config/port_manager` (:51-54), `project_core/utils/shell` (:57-61).
- Aval : `api.main:app` en subprocess, `npm start`, tests Playwright `tests/functional/`.

## Statut d'intégration

**actif** — testé unitairement (33 tests, 7 fichiers sous `tests/unit/webapp/`, dont des gardes récentes #1853/#1857/#1861 ; dernier commit fonctionnel #1857/#1858). **Nuance CI** : `ci.yml` inclut `tests/unit/` mais **pas** `tests/integration/webapp/` — le cycle d'intégration complet est local.

## Artefacts et lecteurs

`logs/webapp_orchestrator.log` (config :29), `logs/screenshots/` + `logs/traces/` (:851-852), `logs/webapp_integration_trace.md` (:1621), `_temp/service_urls.json` (:1687-1689).

## Tests représentatifs

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/webapp/ -v
```

33 tests, 7 fichiers (`test_uvicorn_targets_live_1853.py`, `test_health_endpoint_decider_1857.py`, `test_wait_for_backend_key_decides_1861.py`, `test_frontend_manager.py`…). Intégration (locale) : `tests/integration/webapp/test_full_webapp_lifecycle.py`.

## Frères et parent

Parent : [`../README.md`](../README.md) — ne mentionne pas `webapp/`. Docs dédiées : `docs/architecture/unified_web_orchestrator.md`, `docs/architecture/web_app_orchestration.md`, `docs/integration/MIGRATION_WEBAPP.md`.

## Limites connues

- chemin de config mort : `run_web_e2e_pipeline.py:192` vise `scripts/webapp/config/webapp_config.yml` — **inexistant** → fallback silencieux `_load_config` (config par défaut créée sans avertissement) ;
- **double orchestrateur homonyme** : `scripts/apps/webapp/unified_web_orchestrator.py` (970 l.) définit aussi `UnifiedWebOrchestrator` — consommé par `scripts/verification/run_api_validation.py:27` et 3 fichiers `tests/e2e/` ;
- 3 copies divergentes de `webapp_config.yml` : `argumentation_analysis/webapp/config/` (défaut CLI), `config/` racine (commentaires #1853/#1857), `scripts/apps/webapp/config/` ;
- docstring périmée : `orchestrator.py:615` « backend **Flask** » alors que la cible est FastAPI depuis #1853 ;
- 3 fichiers de test **vides** (0 octet) dans `tests/integration/webapp/` (`test_playwright_integration.py`, `test_port_failover_integration.py`, `test_signal_handling.py` — jamais remplis depuis le commit initial) ;
- `:1841-1842` : `asyncio.get_event_loop()` + `run_until_complete` — API dépréciée (Python 3.10+/3.12).
