# API Web - Reference

## Introduction

Le projet expose ses fonctionnalites d'analyse argumentative via **deux serveurs web** :

| Serveur | Framework | Fichier | Port | Integration |
|---------|-----------|---------|------|-------------|
| **API REST** | FastAPI | `api/main.py` | 8000 | Complete (CapabilityRegistry + UnifiedPipeline) |
| **Interface Web** | Starlette | `interface_web/app.py` | 5003 | ServiceManager |

## Principes Generaux

- **Format des Donnees** : JSON (request/response)
- **Encodage** : UTF-8
- **Validation** : Modeles Pydantic pour tous les endpoints FastAPI
- **Documentation** : OpenAPI/Swagger auto-genere a `http://localhost:8000/docs`
- **CORS** : Active pour tous domaines sur les deux serveurs

## Lancement

```bash
# API REST (recommande pour l'integration)
conda run -n projet-is-roo-new --no-capture-output uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Interface Web (recommande pour les demos)
conda run -n projet-is-roo-new --no-capture-output uvicorn interface_web.app:app --reload --host 127.0.0.1 --port 5003
```

---

## API REST FastAPI (`api/main.py`)

### Startup

Au demarrage, `startup_event()` appelle `initialize_project_environment()` qui :
- Initialise la JVM (JPype/Tweety)
- Charge la configuration depuis `.env`
- Attache le contexte a `app.state.project_context`

### Routers (7)

#### 1. Core Analysis (`/api`)

Source : `api/endpoints.py`

| Methode | URL | Description |
|---------|-----|-------------|
| POST | `/api/analyze` | Analyse argumentative complete d'un texte |
| POST | `/api/validate` | Validation logique d'un argument |
| POST | `/api/fallacies` | Detection de sophismes |
| POST | `/api/framework` | Construction framework de Dung |
| GET | `/api/endpoints` | Liste auto-documentee des endpoints |

#### 2. Agent Capabilities (`/api/v1/agents`)

Source : `api/agent_routes.py` (PR #197, round 71)

| Methode | URL | Description |
|---------|-----|-------------|
| POST | `/api/v1/agents/quality` | Evaluation qualite (9 vertus d'argumentation) |
| POST | `/api/v1/agents/counter-arguments` | Generation de contre-arguments (5 strategies) |
| POST | `/api/v1/agents/debate` | Debat adversarial (protocoles Walton-Krabbe) |
| POST | `/api/v1/agents/governance` | Simulation de gouvernance (7 methodes de vote) |
| POST | `/api/v1/agents/full-analysis` | Pipeline unifie complet |

**Modeles Request/Response** : 9 modeles Pydantic (TextRequest, QualityScore, CounterArgument, DebateResponse, GovernanceResult, etc.)

**Implementation** : Chaque endpoint utilise `_run_pipeline_phase()` qui :
1. Cree un workflow minimal via WorkflowDSL
2. Appelle `setup_registry()` pour initialiser le CapabilityRegistry
3. Execute via `WorkflowExecutor`
4. Retourne les resultats structures

#### 3. Framework Analysis (`/api/v1/framework`)

Source : `api/endpoints.py`

| Methode | URL | Description |
|---------|-----|-------------|
| POST | `/api/v1/framework/analyze` | Analyse semantiques d'argumentation (Dung) |

#### 4. Informal Analysis (`/api/v1/informal`)

Source : `api/endpoints.py`

| Methode | URL | Description |
|---------|-----|-------------|
| POST | `/api/v1/informal/toulmin` | Extraction modele de Toulmin |

#### 5. Proposals & Deliberation (`/api`)

Source : `api/proposal_endpoints.py`

| Methode | URL | Description |
|---------|-----|-------------|
| POST | `/api/propose` | Soumettre une proposition citoyenne |
| GET | `/api/proposals` | Lister les propositions (filtre par status) |
| GET | `/api/proposals/{id}` | Detail + resultats d'analyse |
| POST | `/api/proposals/{id}/vote` | Voter sur une proposition |
| POST | `/api/deliberate` | Lancer un workflow de deliberation |
| GET | `/api/deliberate/{id}/status` | Statut de deliberation |
| GET | `/api/capabilities` | Lister les capabilities du registre |
| POST | `/api/workflow/custom` | Executer un workflow custom sur texte |

#### 6. Mobile (`/api/mobile`)

Source : `api/mobile_endpoints.py`

| Methode | URL | Description |
|---------|-----|-------------|
| POST | `/api/mobile/analyze` | Analyse argumentative complete |
| POST | `/api/mobile/fallacies` | Detection de sophismes |
| POST | `/api/mobile/validate` | Validation logique (Toulmin) |
| POST | `/api/mobile/chat` | Assistant IA conversationnel |

Les endpoints mobile utilisent `run_unified_analysis(workflow_name="light"|"standard")` directement.

#### 7. WebSocket (`/ws`)

Source : `api/websocket_routes.py`

| URL | Description |
|-----|-------------|
| `ws://host/ws/analysis/{session_id}` | Streaming analyse par phases |
| `ws://host/ws/debate/{session_id}` | Streaming tours de debat |
| `ws://host/ws/deliberation/{session_id}` | Streaming progression deliberation |

### Health & Monitoring

| Methode | URL | Description |
|---------|-----|-------------|
| GET | `/` | Root + statut JVM |
| GET | `/health` | Health check API + JVM |

---

## Interface Web Starlette (`interface_web/app.py`)

### Routes

| Methode | URL | Description |
|---------|-----|-------------|
| GET | `/api/status` | Statut des services (ServiceManager + NLP) |
| GET | `/api/health` | Alias de `/api/status` |
| POST | `/api/analyze` | Analyse de texte (timeout 25s) |
| GET | `/api/examples` | Exemples de textes pour analyse |
| POST | `/api/v1/framework/analyze` | Analyse Dung AF |
| GET | `/` | Application React (fichiers statiques) |

### Architecture

- **Starlette** ASGI (anciennement Flask) avec lifespan pattern
- **ServiceManager** pour l'orchestration des services backend
- **NLPModelManager** pour les modeles NLP (CamemBERT, etc.)
- Frontend React servi depuis `services/web_api/interface-web-argumentative/build/`

---

## Workflows Disponibles

Le point `/api/v1/agents/full-analysis` et `/api/workflow/custom` donnent acces a **17 workflows** :

`light`, `standard` (recommande), `full`, `quality_gated`, `collaborative`, `debate_governance`, `jtms_dung`, `neural_symbolic`, `hierarchical_fallacy`, `democratech`, `debate_tournament`, `fact_check`, `formal_debate`, `belief_dynamics`, `argument_strength`, `formal_verification`, `comprehensive`

Voir `docs/reports/CARTOGRAPHIE_5_POINTS_ENTREE_PRINCIPAUX.md` pour la description de chaque workflow.

---

## Authentification/Autorisation

L'API est ouverte (pas d'authentification). La protection est geree par des mecanismes externes si necessaire (reverse proxy, firewall, API gateway).

## Gestion des Erreurs

- **Codes HTTP** : 200 (succes), 400 (requete invalide), 404 (non trouve), 500 (erreur interne), 503 (service indisponible), 504 (timeout)
- **Reponse JSON** : `{"detail": "Description de l'erreur"}` (FastAPI) ou `{"error": "...", "message": "..."}` (Starlette)

## Exemple d'Utilisation

```bash
# Health check
curl http://localhost:8000/health

# Analyse de qualite d'argument
curl -X POST http://localhost:8000/api/v1/agents/quality \
  -H "Content-Type: application/json" \
  -d '{"text": "Les chats sont meilleurs que les chiens car ils sont plus independants."}'

# Analyse complete via pipeline
curl -X POST http://localhost:8000/api/v1/agents/full-analysis \
  -H "Content-Type: application/json" \
  -d '{"text": "Si il pleut, la route est mouillee. Il pleut. Donc la route est mouillee."}'

# Lister les capabilities
curl http://localhost:8000/api/capabilities

# Workflow custom
curl -X POST http://localhost:8000/api/workflow/custom \
  -H "Content-Type: application/json" \
  -d '{"text": "...", "workflow_name": "quality_gated"}'
```

---

**Derniere mise a jour** : 22 mars 2026 (round 71, post-PR #197/#198/#199)
