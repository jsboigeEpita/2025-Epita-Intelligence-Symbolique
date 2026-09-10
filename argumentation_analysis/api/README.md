# `api/` — endpoints JTMS montés par l'API racine

## Rôle et frontière

Le package **JTMS-spécifique** de l'API : un `APIRouter` FastAPI + ses modèles Pydantic, plus une mini-app démo. 3 fichiers, ~1390 lignes.

**Disambiguïsation (homonyme `api/` racine)** : l'app FastAPI générale du dépôt est `api/` **racine** (`factory.py`, `endpoints/`, `main.py` — `uvicorn api.main:app`, CLAUDE.md). Ce package-ci n'est pas une app autonome : son router est **monté par** l'app racine, routes finales sous `/api/v1/jtms/*`.

## Composants publics

- `jtms_router` (`jtms_endpoints.py:59`, `APIRouter(prefix="/jtms")`) — **18 routes** (comptées sur les décorateurs :116-885) : 6 beliefs (create :116, justification :203, validité :283, explain :336, query :396, state :456), 4 sessions (create :540, list :571, checkpoint :612, restore :641), export :682 / import :716, plugin status :755, et 5 routes miroir `sk_*` :787-886 passant par le plugin SK plutôt que le service direct ;
- DI lazy : `get_jtms_service` :67, `get_session_manager` :75, `get_sk_plugin` :85 ; erreur centralisée `handle_jtms_error` :97 ;
- `initialize_jtms_services()` :911 — init au démarrage + tâche asyncio horaire de purge des sessions expirées (:923-932) ;
- `jtms_models.py` — 30 modèles Pydantic (:13-381) : requêtes (`CreateBeliefRequest` :39…), réponses (`JTMSResponse` :154…), data (`BeliefInfo` :13, `SessionInfo` :220, `JTMSStatistics` :209), `JTMSError` :316 ;
- `main.py` (61 l.) — mini-app FastAPI **démo** : `TestPlugin(BasePlugin)` mock (:11), route unique `POST /api/v2/analyze` :43 sur `OrchestrationService`. N'est **pas** l'app racine.

## Points d'entrée valides

- [`api/main.py:31-33`](../../api/main.py) (racine) importe `jtms_router` + `initialize_jtms_services`, monte à `:106` `app.include_router(jtms_router, prefix="/api/v1")`, appelle au startup `:73-75` — dégradation gracieuse si JVM absente (guard #857, `:43-44`) ;
- `interface_web/routes/jtms_routes.py:26` importe `jtms_models.BeliefInfo/JustificationInfo` — **mais** ce fichier est un Blueprint Flask orphelin : `interface_web/app.py` est Starlette (:39-51, aucun Flask) et `jtms_bp` (:34) n'est enregistré nulle part ;
- `main.py` local : 0 importeur production (seul `tests/integration/argumentation_analysis/api/test_main_api.py:5`).

## Amont / aval

- Amont : [`services/jtms_service`](../services/README.md), `services/jtms_session_manager`, `plugins/semantic_kernel/jtms_plugin` (:51-56) ; cœur : `services/jtms/jtms_core.py`.
- Aval : l'app racine `api/main.py` (subprocess uvicorn lancé par `scripts/apps/webapp/backend_manager.py:55` et l'orchestrateur webapp).

## Statut d'intégration

| Composant | Statut | Preuve |
|---|---|---|
| `jtms_endpoints.py` | **actif** (monté, dégradation gracieuse JVM) | api/main.py:31, :106 |
| `jtms_models.py` | **actif** | consommé par jtms_endpoints :13-48 + la racine via le router |
| `main.py` | **expérimental (démo)** | mock :11, 0 importeur production |

## Artefacts et lecteurs

Aucune écriture disque directe (checkpoints/sessions gérés par `JTMSSessionManager`). Effet de bord : tâche asyncio de fond horaire (:932) si le startup racine appelle `initialize_jtms_services`.

## Tests représentatifs

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/api/test_jtms_fastapi_mount.py tests/unit/api/test_jtms_import_guard.py tests/unit/argumentation_analysis/api/ -v
```

Montage + cardinalité (« 18 routes », `test_jtms_fastapi_mount.py:41`), guard #857 par analyse statique (`test_jtms_import_guard.py:20-24`), modèles, import triage.

## Frères et parent

Parent : [`../README.md`](../README.md) — ne mentionne pas `api/`. À distinguer de `api/` racine (l'app) et de [`services/web_api/`](../services/web_api/README.md) (service web + build React).

## Limites connues

- `jtms_endpoints.py:932` : `asyncio.create_task(cleanup_expired_sessions())` **sans référence gardée** — la tâche peut être ramassée par le GC (gotcha asyncio officiel), silencieux de toute façon (`except Exception: pass` :928-929) ;
- globals lazy :62-64 : si le startup échoue, les getters DI recréent des instances divergentes de l'état global ;
- double surface beliefs (6 endpoints service vs 5 `sk_*` plugin) — duplication fonctionnelle non documentée dans le code ;
- `interface_web/routes/jtms_routes.py` mort importe `jtms_models` pour rien (charge Pydantic à l'import d'interface_web).
