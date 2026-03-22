# CARTOGRAPHIE DES POINTS D'ENTREE PRINCIPAUX
# Systeme d'Intelligence Symbolique EPITA 2025

> **Date de cartographie** : 22 mars 2026
> **Status** : CARTOGRAPHIE COMPLETE VALIDEE
> **Revision** : v3.0 - Post-integration Lego Architecture (round 71)
> **Historique** : v2.1 (10/06/2025, 5 points pre-integration) -> v3.0 (refonte complete)

---

## SYNTHESE EXECUTIVE

Le systeme a evolue depuis la v2.1 vers une **architecture Lego** (CapabilityRegistry + WorkflowDSL + UnifiedPipeline) avec **17 workflows pre-construits** et **46 capabilities enregistrees**. Les points d'entree se repartissent desormais en **3 couches** :

| Couche | Point d'entree | Integration moderne | Usage |
|--------|---------------|---------------------|-------|
| **API (moderne)** | `api/main.py` (FastAPI) | COMPLETE | Production, mobile, integrations |
| **Web UI** | `interface_web/app.py` (Starlette) | ServiceManager | Etudiants, demos interactives |
| **CLI (legacy)** | `argumentation_analysis/main_orchestrator.py` | Legacy (AnalysisRunner) | Analyse avancee avec UI |
| **CLI (legacy)** | `argumentation_analysis/run_orchestration.py` | Legacy (AnalysisRunner) | Analyse en ligne de commande |
| **Demo** | `examples/.../demonstration_epita.py` | Pedagogique | Soutenances, cours |

### Architecture Globale (post-integration)

```
                    CapabilityRegistry (46 capabilities)
                            |
                     WorkflowDSL (17 workflows)
                            |
                    UnifiedPipeline (32 state writers, 14 invoke callables)
                   /        |        \
          api/main.py   interface_web/   CLI scripts
          (FastAPI)     (Starlette)      (legacy)
          7 routers     ServiceManager   AnalysisRunner
          25+ routes    5 routes
```

- **Agents specialises** : Quality, Debate, CounterArgument, Governance, FOL, Modal, PL, JTMS, Informal, Extract, Synthesis, Oracle, Sherlock
- **Orchestrateurs** : Cluedo, Conversation, RealLLM, LogiqueComplexe, CollaborativeDebate
- **Pipeline unifie** : 17 workflows (light, standard, full, quality_gated, collaborative, formal_debate, etc.)
- **Interface multi-mode** : FastAPI REST, Starlette Web, CLI, WebSocket streaming
- **Integration Java** : TweetyProject via JPype avec fallbacks Python

---

## POINT D'ENTREE #1 : API REST (FastAPI) — RECOMMANDE

### Fichier Principal
```
api/main.py
```

### Description
**Point d'entree principal** pour toute utilisation programmatique. FastAPI v2.0 avec **7 routers** couvrant l'integralite des capabilities du systeme. **Seul point d'entree entierement integre** avec la Lego Architecture (CapabilityRegistry + UnifiedPipeline + WorkflowDSL).

### Lancement
```bash
# Standard
conda run -n projet-is-roo-new --no-capture-output uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Avec la doc OpenAPI
# -> http://localhost:8000/docs
```

### Routers enregistres (7)

| Router | Prefix | Routes | Description |
|--------|--------|--------|-------------|
| `api_router` | `/api` | Core text analysis | Analyse argumentative generale |
| `framework_router` | `/api/v1/framework` | Dung AF analysis | Semantiques d'argumentation abstraite |
| `informal_router` | `/api/v1/informal` | Toulmin extraction | Modele de Toulmin |
| `agent_router` | `/api/v1/agents` | 5 endpoints | Capabilities agents (PR #197) |
| `proposal_router` | `/api` | 8 endpoints | Propositions, vote, deliberation |
| `mobile_router` | `/api/mobile` | 4 endpoints | API simplifiee mobile (3.1.5) |
| `ws_router` | `/ws` | 3 WebSockets | Streaming temps reel |

### Routes detaillees

**Agent Capabilities** (`api/agent_routes.py`, PR #197) :
```
POST /api/v1/agents/quality          — Evaluation qualite (9 vertus)
POST /api/v1/agents/counter-arguments — Generation de contre-arguments (5 strategies)
POST /api/v1/agents/debate           — Debat adversarial (Walton-Krabbe)
POST /api/v1/agents/governance       — Simulation de gouvernance (7 methodes de vote)
POST /api/v1/agents/full-analysis    — Pipeline unifie complet
```

**Propositions & Deliberation** (`api/proposal_endpoints.py`) :
```
POST /api/propose                    — Soumettre une proposition citoyenne
GET  /api/proposals                  — Lister les propositions
GET  /api/proposals/{id}             — Detail + resultats d'analyse
POST /api/proposals/{id}/vote        — Voter sur une proposition
POST /api/deliberate                 — Lancer un workflow de deliberation
GET  /api/deliberate/{id}/status     — Statut de deliberation
GET  /api/capabilities               — Lister les capabilities du registre
POST /api/workflow/custom            — Executer un workflow custom
```

**Mobile** (`api/mobile_endpoints.py`) :
```
POST /api/mobile/analyze             — Analyse argumentative complete
POST /api/mobile/fallacies           — Detection de sophismes
POST /api/mobile/validate            — Validation logique (Toulmin)
POST /api/mobile/chat                — Assistant IA conversationnel
```

**WebSocket** (`api/websocket_routes.py`) :
```
ws://host/ws/analysis/{session_id}     — Streaming analyse par phases
ws://host/ws/debate/{session_id}       — Streaming tours de debat
ws://host/ws/deliberation/{session_id} — Streaming progression deliberation
```

**Health & Monitoring** :
```
GET /        — Root + statut JVM
GET /health  — Health check API + JVM
```

### Integration Architecture
- `startup_event()` appelle `initialize_project_environment()` (bootstrap JVM + config)
- `agent_routes` utilise `_run_pipeline_phase()` → `setup_registry()` + `WorkflowExecutor`
- `mobile_endpoints` appelle `run_unified_analysis(workflow_name="light"|"standard")`
- `proposal_endpoints` query `CapabilityRegistry` + `WorkflowBuilder` custom
- Modeles Pydantic pour validation request/response (9 modeles dans agent_routes)

### Status Technique
- ENTIEREMENT INTEGRE avec CapabilityRegistry, UnifiedPipeline, WorkflowDSL
- 13 tests unitaires pour agent_routes (`tests/unit/api/test_agent_routes.py`)
- CORS active, error handling structure
- OpenAPI/Swagger auto-genere a `/docs`

---

## POINT D'ENTREE #2 : INTERFACE WEB (Starlette)

### Fichier Principal
```
interface_web/app.py
```

### Description
**Interface web Starlette** (ASGI, anciennement Flask) pour l'analyse argumentative interactive. Point d'entree **grand public** et **etudiants**. Sert une application React pre-buildee avec API backend integree.

### Lancement
```bash
# Depuis la racine du projet
conda run -n projet-is-roo-new --no-capture-output python interface_web/app.py

# Ou directement via uvicorn
uvicorn interface_web.app:app --reload --host 127.0.0.1 --port 5003

# -> http://localhost:5003
```

### Routes (5)

| Route | Methode | Description |
|-------|---------|-------------|
| `/api/status` | GET | Statut des services (ServiceManager + NLP) |
| `/api/health` | GET | Alias de `/api/status` |
| `/api/analyze` | POST | Analyse de texte (timeout 25s) |
| `/api/examples` | GET | Exemples de textes pour analyse |
| `/api/v1/framework/analyze` | POST | Analyse Dung AF (arguments + attaques) |
| `/` | GET | Application React (fichiers statiques) |

### Architecture
- **Starlette** ASGI avec lifespan pattern (init/cleanup async)
- **ServiceManager** (`orchestration.service_manager`) : gestion des services backend
- **NLPModelManager** : chargement modeles NLP (CamemBERT, etc.)
- **React Frontend** : build statique servi depuis `services/web_api/interface-web-argumentative/build/`
- **CORS** : active pour tous domaines

### Differences avec l'API FastAPI
- N'utilise **PAS** CapabilityRegistry/UnifiedPipeline/WorkflowDSL
- Orchestration via **ServiceManager** (couche d'abstraction separee)
- Interface web HTML/React servie directement
- Moins d'endpoints mais experience utilisateur complete (UI + API)

### Status Technique
- FONCTIONNEL (Starlette v2.0.0)
- Mode degrade si ServiceManager ou NLP indisponibles
- Middleware CORS configure
- Port par defaut: 5003

---

## POINT D'ENTREE #3 : ORCHESTRATEUR PRINCIPAL (CLI)

### Fichier Principal
```
argumentation_analysis/main_orchestrator.py
```

### Description
**Orchestrateur CLI interactif** avec interface utilisateur Tkinter optionnelle. Point d'entree **technique avance** pour analyse approfondie avec controle fin.

### Lancement
```bash
# Mode interactif avec UI Tkinter
conda run -n projet-is-roo-new --no-capture-output python argumentation_analysis/main_orchestrator.py

# Mode headless avec fichier
conda run -n projet-is-roo-new --no-capture-output python argumentation_analysis/main_orchestrator.py --skip-ui --text-file=path/to/text.txt
```

### Flux d'Execution
1. Chargement environnement (`.env` via auto_env)
2. Configuration logging multi-niveaux
3. Initialisation JVM (JPype/Tweety)
4. Creation service LLM (`create_llm_service()`)
5. UI Tkinter pour selection texte (sauf `--skip-ui`)
6. Analyse via `AnalysisRunner().run_analysis_async()`

### Architecture
- **LEGACY** : utilise `orchestration.analysis_runner.AnalysisRunner`
- N'utilise PAS CapabilityRegistry, UnifiedPipeline, ou WorkflowDSL
- Pipeline d'agents original : PM, Informal, PL, Extract, Oracle

### Status Technique
- FONCTIONNEL mais non modernise
- Requiert Tkinter pour mode interactif (pas de mode headless sans `--text-file`)
- Pas de tests dedies

---

## POINT D'ENTREE #4 : RUNNER CLI FLEXIBLE

### Fichier Principal
```
argumentation_analysis/run_orchestration.py
```

### Description
**CLI runner flexible** avec 3 modes d'entree (fichier, texte inline, UI). Version simplifiee du main_orchestrator pour usage en scripts et CI.

### Lancement
```bash
# Depuis un fichier texte
conda run -n projet-is-roo-new --no-capture-output python argumentation_analysis/run_orchestration.py --file path/to/text.txt -v

# Texte inline
conda run -n projet-is-roo-new --no-capture-output python argumentation_analysis/run_orchestration.py --text "Votre argument ici"

# Mode UI interactif
conda run -n projet-is-roo-new --no-capture-output python argumentation_analysis/run_orchestration.py --ui
```

### Arguments
```
--file, -f   : Chemin vers un fichier texte
--text, -t   : Texte a analyser (inline)
--ui, -u     : Interface utilisateur Tkinter
--verbose, -v : Logs detailles (DEBUG)
```

### Architecture
- **LEGACY** : utilise `orchestration.analysis_runner.run_analysis()`
- Memes limitations que le main_orchestrator (pas d'integration Lego)
- Source mutuellement exclusive obligatoire (--file | --text | --ui)

### Status Technique
- FONCTIONNEL
- Plus adapte au scripting que le main_orchestrator (args flexibles)
- Pas de tests dedies

---

## POINT D'ENTREE #5 : DEMO PEDAGOGIQUE EPITA

### Fichier Principal
```
examples/02_core_system_demos/scripts_demonstration/demonstration_epita.py
```

### Description
**Demonstration pedagogique interactive** concue pour les cours et soutenances EPITA. Systeme de menus avec validation de datasets custom et detection de processing reel vs mocks.

### Lancement
```bash
# Menu interactif
conda run -n projet-is-roo-new --no-capture-output python examples/02_core_system_demos/scripts_demonstration/demonstration_epita.py

# Demarrage rapide etudiant
conda run -n projet-is-roo-new --no-capture-output python examples/02_core_system_demos/scripts_demonstration/demonstration_epita.py --quick-start

# Validation avec donnees custom
conda run -n projet-is-roo-new --no-capture-output python examples/02_core_system_demos/scripts_demonstration/demonstration_epita.py --validate-custom
```

### Fonctionnalites
- Systeme de menus categorise
- Validation de datasets custom avec marqueurs uniques
- Detection processing reel vs mocks (analyse des sorties)
- Mode `--quick-start` pour demos rapides en cours

### Status Technique
- PEDAGOGIQUE : pas d'integration avec l'architecture moderne
- Autonome, pas de dependance a CapabilityRegistry ou UnifiedPipeline

---

## POINTS D'ENTREE ADDITIONNELS

### Web App Orchestrator (DevOps)
```
scripts/apps/webapp/unified_web_orchestrator.py
```
Orchestre le demarrage backend + frontend + tests Playwright. Outil DevOps/CI, pas un point d'entree utilisateur.

### Sherlock-Watson Scripts
```
scripts/sherlock_watson/run_cluedo_oracle_enhanced.py   — Jeu Cluedo avec Oracle
scripts/sherlock_watson/run_einstein_oracle_demo.py     — Demo Einstein
scripts/sherlock_watson/test_oracle_behavior_demo.py    — Tests comportement Oracle
```
Demos specialisees pour le systeme d'agents Sherlock/Watson/Moriarty.

### Engine-Level Orchestrator
```
argumentation_analysis/orchestration/engine/main_orchestrator.py
```
Classe `MainOrchestrator` utilisee en interne par les strategies d'orchestration. Pas un point d'entree direct.

### Validation Scripts
```
scripts/validation/sprint3_final_validation.py          — Validation sprint 3
scripts/validation/validators/integration_validator.py  — Validateur integration
scripts/validation/validators/orchestration_validator.py — Validateur orchestration
```
Suite de validation distribuee (pas de script unique comme dans v2.1).

---

## MATRICE DE CHOIX

| Utilisateur | Objectif | Point d'Entree | Complexite |
|-------------|----------|----------------|------------|
| **Developpeur** | Integration, API calls | #1 FastAPI (`api/main.py`) | Avance |
| **Etudiant** | Decouverte interactive | #2 Interface Web (`interface_web/app.py`) | Facile |
| **Chercheur** | Analyse CLI approfondie | #3 Orchestrateur (`main_orchestrator.py`) | Avance |
| **Scripteur** | Automation, batch | #4 CLI Runner (`run_orchestration.py`) | Moyen |
| **Enseignant** | Demo en cours | #5 Demo EPITA (`demonstration_epita.py`) | Facile |
| **App Mobile** | API mobile | #1 FastAPI routes `/api/mobile/*` | Moyen |
| **Frontend** | Temps reel | #1 FastAPI WebSocket `/ws/*` | Avance |
| **Gouvernance** | Vote, deliberation | #1 FastAPI routes `/api/propose`, `/api/deliberate` | Moyen |

---

## WORKFLOWS DISPONIBLES (via UnifiedPipeline)

Le point d'entree #1 (FastAPI) donne acces a **17 workflows pre-construits** :

| Workflow | Description | Phases |
|----------|-------------|--------|
| `light` | Analyse minimale | Extract -> Quality -> Counter |
| `standard` | **Recommande** | Extract -> Quality -> Counter -> JTMS -> Governance -> Debate |
| `full` | Complet (tous composants) | Tous + speech + neural fallacy |
| `quality_gated` | Raffinement iteratif qualite | Boucle qualite avec seuil |
| `collaborative` | Debat multi-agents (PR #199) | Critic -> Validator -> Devil's Advocate -> Synthesizer |
| `debate_governance` | Vote-contestation-debat-revote | Governance + Debate en boucle |
| `jtms_dung` | Maintenance croyances + extensions | JTMS + Dung semantics |
| `neural_symbolic` | CamemBERT + hierarchie | Detection sophismes hybride |
| `hierarchical_fallacy` | Taxonomie guidee | 8 familles de sophismes |
| `democratech` | Gouvernance democratique | Track D |
| `debate_tournament` | Tournoi de debats | Track D |
| `fact_check` | Pipeline fact-checking | Track D |
| `formal_debate` | Debat en logique formelle | Track A |
| `belief_dynamics` | Operateurs de revision | Track A |
| `argument_strength` | Ranking semantiques | Track A |
| `formal_verification` | Verification formelle | Track A |
| `comprehensive` | LLM-only, benchmark-optimise | Toutes capabilities LLM |

---

## DEPENDANCES ET PREREQUIS

### Environnement
```bash
# Conda (recommande)
conda activate projet-is-roo-new   # Python 3.10, SK 1.40, Pydantic 2.11

# Variables d'environnement (.env)
OPENAI_API_KEY=sk-...
OPENAI_CHAT_MODEL_ID=gpt-5-mini
TEXT_CONFIG_PASSPHRASE=...          # Pour main_orchestrator UI uniquement
```

### Java (Optionnel)
```bash
# JDK 11+ pour TweetyProject (agents logiques)
# Fallbacks Python disponibles si JVM indisponible
JAVA_HOME=/path/to/jdk
```

### Ports par defaut
| Service | Port |
|---------|------|
| FastAPI (`api/main.py`) | 8000 |
| Starlette (`interface_web/app.py`) | 5003 |

---

**Version** : 3.0 - Cartographie post-integration Lego Architecture
**Derniere mise a jour** : 22 mars 2026 (round 71)
**Status** : 4927+ tests passent, CI GREEN, 17 workflows, 46 capabilities
