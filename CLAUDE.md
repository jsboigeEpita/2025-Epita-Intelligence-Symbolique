# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-agent argumentation analysis system for EPITA (student project platform). Python 3.10+ with Java/JPype integration. The system analyzes rhetorical strategies, detects fallacies (8 families), performs fact-checking, and orchestrates collaborative reasoning agents (Sherlock/Watson paradigm).

**History**: The core ("tronc commun") was built by the professor inside `argumentation_analysis/`. Student PRs were merged at root level as numbered directories. Root-level overflow has been cleaned up (#34). 12 student projects have been integrated into the BaseAgent/SK architecture (#35): agents inherit from `BaseAgent`, logic is exposed via `@kernel_function` plugins, and everything is wired into `CapabilityRegistry` + `AgentFactory`.

## Build & Environment Setup

**IMPORTANT**: You must activate a Conda environment before running anything. Without it, imports will fail.

```bash
# List available environments
conda env list

# Activate dev environment (preferred — most recent deps)
conda activate projet-is-roo-new    # SK 1.40, Pydantic 2.11, JPype 1.6

# Alternative (CI environment)
conda activate projet-is            # SK 1.35, Pydantic 2.11

# From Claude Code / non-interactive shells (conda activate won't work):
conda run -n projet-is-roo-new --no-capture-output <command>

# Full environment setup from scratch (Windows PowerShell)
./setup_project_env.ps1
```

### API Keys

Copy `.env.example` to `.env`. Primary LLM access is through OpenAI:
```
OPENAI_API_KEY=sk-...
OPENAI_CHAT_MODEL_ID=gpt-5-mini
```

OpenRouter is also supported as an alternative:
```
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

Tests auto-skip when API keys are unavailable (no failures).

### GitHub CLI

The repo is owned by `jsboigeEpita`. A `GH_TOKEN` in `.env` grants `gh` CLI access with the correct account. **Always prefix `gh` commands** with the token export:
```bash
export GH_TOKEN=$(grep "^GH_TOKEN=" .env | cut -d= -f2) && gh issue list
```
Without this, `gh` uses the global default account (`jsboige`) which lacks write permissions on this repo.

## Testing

```bash
# Run all tests (always prefix with conda run in non-interactive shells)
conda run -n projet-is-roo-new --no-capture-output pytest tests/ -v

# Unit tests only
pytest tests/unit/ -v

# Skip slow tests
pytest tests/ -m "not slow" -v

# Single test file
pytest tests/unit/argumentation_analysis/test_synthesis_agent.py -v

# Single test function
pytest tests/unit/argumentation_analysis/test_synthesis_agent.py::TestSynthesisAgent::test_method -v

# By marker (see pytest.ini for full list)
pytest tests/ -m "llm_light" -v          # Light LLM tests (<30s, ~$0.01-0.05)
pytest tests/ -m "requires_api" -v       # Tests needing API keys
pytest tests/ -m "not jpype" -v          # Skip Java/JPype tests
pytest tests/ -m "belief_set" -v         # Logic belief set tests
```

**Async mode**: `asyncio_mode = auto` — no need for `@pytest.mark.asyncio`.

**Python path**: pytest resolves from `.`, `argumentation_analysis`, and `project_core` (configured in `pyproject.toml`).

**DLL load order on Windows**: `conftest.py` imports torch/transformers BEFORE jpype to avoid `WinError 182` crashes. Do not reorder these imports.

## Linting (CI)

```bash
black --check --diff .
flake8 .
```

## Repository Structure

### Intended Layout

```
Root/
├── argumentation_analysis/   ← CANONICAL source for all core code (professor's trunk)
├── tests/                    ← Test suite (unit, integration, e2e)
├── docs/                     ← Documentation
├── examples/                 ← Demo scripts and showcases
├── scripts/                  ← Utility/maintenance scripts
├── config/                   ← Configuration files
├── 1.4.1-JTMS/              ← Student project directories (numbered)
├── 2.3.2-detection-sophismes/
├── ...other student projects...
└── config files (pyproject.toml, pytest.ini, etc.)
```

### Known Overflow (completed — Epic #317)

Root-level directories that were cleaned up during Epic #317 consolidation:

| Root directory | Overlaps with | Status |
|---|---|---|
| `api/` | `argumentation_analysis/api/` | **KEPT** — root has general FastAPI endpoints, inside has JTMS-specific |
| ~~`core/`~~ | ~~`argumentation_analysis/core/`~~ | **DELETED** (PR #154) |
| ~~`demos/`~~ | ~~`argumentation_analysis/demos/`~~ | **MOVED** → `examples/03_demos_overflow/` |
| ~~`services/`~~ | ~~`argumentation_analysis/services/`~~ | **CONSOLIDATED** (#322) — React frontend kept (load-bearing `STATIC_FILES_DIR`); `interface-simple/` archived; management scripts kept |
| ~~`plugins/`~~ | ~~`argumentation_analysis/plugins/`~~ | **CONSOLIDATED** (#321) — orphan SK prompts archived to `docs/archives/plugins_overflow/` |
| ~~`src/`~~ | ~~`argumentation_analysis/agents/`~~ | **CONSOLIDATED** (#321) — `fallacy_families.yaml` moved to consuming plugin; empty dir removed |
| ~~`reports/`~~ | — | **ARCHIVED** (#323) → `docs/archives/reports_legacy_317/` (28 files, June 2025) |
| ~~`validation/`~~ | — | **ARCHIVED** (#323) → `docs/archives/validation_legacy_317/` (3 files) |
| ~~`data/`~~ | — | **RELOCATED** (#323) → `argumentation_analysis/data/datasets/legacy_fixtures/` (4 JSON files) |
| `project_core/` | `argumentation_analysis/core/` | **KEPT** — infrastructure utilities (NOT business logic) |

**Rule**: When adding new code, put it inside `argumentation_analysis/`. Do not add new modules at root level.

### Student Project Directories (root level, correct)

`1.4.1-JTMS`, `1_2_7_argumentation_dialogique`, `2.1.6_multiagent_governance_prototype`, `2.3.2-detection-sophismes`, `2.3.3-generation-contre-argument`, `2.3.5_argument_quality`, `2.3.6_local_llm`, `3.1.5_Interface_Mobile`

### Other Root Directories

- `interface_web/` — Starlette web app serving React frontend + analysis API
- `Arg_Semantic_Index/` — Knowledge indexing system (Streamlit)
- `abs_arg_dung/` — Abstract argumentation (Dung semantics) library
- `CaseAI/` — Slack bot frontend
- `speech-to-text/` — Speech service
- `libs/` — External libraries/JARs
- `portable_jdk/` — Cached JDK for JPype

## Architecture

### Three-Tier Agent Hierarchy

```
Strategic  → Orchestrators (complex multi-step workflows)
Tactical   → Coordinators (manage agent interactions)
Operational → Base agents (Sherlock, Watson, JTMS, FOL, Modal logic)
```

### Agent System (`argumentation_analysis/agents/core/`)

- **`abc/agent_bases.py`** — `BaseAgent(ChatCompletionAgent, ABC)` and `BaseLogicAgent`. All agents inherit from `BaseAgent` which extends Semantic Kernel's `ChatCompletionAgent` (required for `AgentGroupChat` compatibility). Uses Pydantic V2 — private attributes use `PrivateAttr`, logger is `agent_logger` (not `_logger`).
- **`logic/`** — FOL, Modal, Propositional logic agents + `TweetyBridge` (Java/JPype bridge to Tweety reasoner)
- **`extract/`** — `FactExtractionAgent` for extracting verifiable claims
- **`informal/`** — Informal logic + `TaxonomySophismDetector` (8-family fallacy classification)
- **`synthesis/`** — `SynthesisAgent` for aggregating analysis results
- **`oracle/`** — Cluedo dataset + `MoriartyInterrogatorAgent`
- **`pm/`** — `SherlockEnqueteAgent` (investigation orchestration)
- **`pl/`** — Propositional logic agent
- **`debate/`** — `DebateAgent(BaseAgent)` — multi-personality adversarial debate with Walton-Krabbe protocols, argument scoring, knowledge bases. Alias: `EnhancedArgumentationAgent`.
- **`counter_argument/`** — `CounterArgumentAgent(BaseAgent)` — generates counter-arguments using 5 rhetorical strategies (reductio ad absurdum, counter-example, distinction, reformulation, concession). 5-criteria weighted evaluator.
- **`governance/`** — Governance simulation: 7 voting methods (majority, Borda, Condorcet, approval, etc.), conflict resolution, consensus metrics. NOT a BaseAgent — logic exposed via plugin.
- **`quality/`** — Argument quality evaluation: 9 virtue detectors (clarity, coherence, relevance, etc.). Exposed via plugin.

### Semantic Kernel Plugins (`argumentation_analysis/plugins/`)

- **`quality_scoring_plugin.py`** — `QualityScoringPlugin`: 3 `@kernel_function` methods wrapping `ArgumentQualityEvaluator`
- **`french_fallacy_plugin.py`** — `FrenchFallacyPlugin`: 3 `@kernel_function` methods for 3-tier hybrid fallacy detection (French NLP)
- **`governance_plugin.py`** — `GovernancePlugin`: 4 `@kernel_function` methods for voting, conflict detection, consensus metrics

### Lego Architecture (`argumentation_analysis/core/capability_registry.py`)

- **`CapabilityRegistry`** — Central registry for agents, plugins, and services. `register_agent()`, `register_plugin()`, `register_service()`, `find_*_for_capability()`.
- **`ServiceDiscovery`** — Provider registry with quality scoring. `register_provider()`, `get_best_provider()`.
- **`WorkflowDSL`** (`orchestration/workflow_dsl.py`) — Declarative workflow builder: `add_phase(capability=...)`, `depends_on()`, `optional()`.
- **`AgentFactory`** (`agents/factory.py`) — Creates agents with proper kernel wiring: `create_counter_argument_agent()`, `create_debate_agent()`.
- **`UnifiedPipeline`** (`orchestration/unified_pipeline.py`) — `setup_registry()` auto-registers all components, 3 pre-built workflows (light/standard/full), `run_unified_analysis()` convenience function.

### Core Services (`argumentation_analysis/core/`)

- **`communication/`** — Multi-channel messaging: hierarchical, collaboration, pub/sub, request/response, with operational/tactical/strategic adapters
- **`llm_service.py`** — LLM integration layer
- **`jvm_setup.py`** — JVM initialization for JPype/Tweety
- **`bootstrap.py`** — System initialization
- **`config.py`** / **`environment.py`** — Configuration management
- **`capability_registry.py`** — CapabilityRegistry + ServiceDiscovery (Lego architecture)
- **`shared_state.py`** — `UnifiedAnalysisState` extending `RhetoricalAnalysisState` with 10 new dimensions

### Integrated Services (`argumentation_analysis/services/`)

- **`jtms/jtms_core.py`** — JTMS (Justification-based Truth Maintenance System): Belief, Justification, JTMS classes
- **`local_llm_service.py`** — OpenAI-compatible adapter for local LLM endpoints
- **`speech_transcription.py`** — Speech-to-text adapter (HTTP service)
- **`semantic_index_service.py`** — Kernel Memory semantic indexing adapter

### Key Integration Points

- **Java/JPype**: Tweety logic library accessed via `jpype1`. JVM must be initialized before use (`jvm_setup.py`). Tests marked `@pytest.mark.jpype` or `@pytest.mark.tweety`.
- **Semantic Kernel**: All agents use SK's kernel for LLM orchestration. Agent plugins loaded via `core/plugin_loader.py`.
- **Pydantic V2**: Data validation throughout. Recent migration from V1 — watch for `_logger` vs `agent_logger` attribute naming.

### Entry Points

**Modern (fully integrated with Lego Architecture):**
- `api/main.py` — **FastAPI REST API** (RECOMMENDED). 7 routers, 25+ routes. Agent capabilities, proposals, mobile, WebSocket streaming. Uses CapabilityRegistry + UnifiedPipeline + WorkflowDSL. Launch: `uvicorn api.main:app --reload --port 8000`

**Web UI:**
- `interface_web/app.py` — **Starlette web app** (formerly Flask). Serves React frontend + analysis API. Uses ServiceManager (not UnifiedPipeline). **Note**: React build at `services/web_api/interface-web-argumentative/build/` is required (not in git — run `npm run build` in that dir first). Launch: `uvicorn interface_web.app:app --port 5003`

**CLI (multi-mode orchestration):**
- `argumentation_analysis/run_orchestration.py` — CLI runner with `--mode pipeline|conversational|legacy` and `--workflow light|standard|full|collaborative`
- `argumentation_analysis/main_orchestrator.py` — Interactive orchestrator with Tkinter UI

**Pedagogical:**
- `examples/02_core_system_demos/scripts_demonstration/demonstration_epita.py` — Interactive demo for courses/soutenances

### Orchestration Modes

The system supports 4 orchestration modes. See `docs/architecture/ORCHESTRATION_MODES.md` for full details.

| Mode | Status | Entry Point | Description |
|------|--------|-------------|-------------|
| Sequential (Pipeline) | ACTIVE | `--mode pipeline` (default) | Phases run in DAG order via WorkflowExecutor |
| Conversational | ACTIVE | `--mode conversational` | Multi-agent dialogue via SK AgentGroupChat |
| Hierarchical | DORMANT | — | Strategic → Tactical → Operational delegation |
| Cluedo | ACTIVE | Dedicated scripts | Sherlock-Watson investigation game |

## CI/CD

GitHub Actions (`.github/workflows/ci.yml`):
1. **lint-and-format**: Black + Flake8 on Windows/Conda
2. **automated-tests**: Pytest on Windows with Java 11 (Temurin) + Conda. Tests skip gracefully without API keys.

## Key Conventions

- **Pydantic V2 agents**: Use `agent_logger` (public attribute via `PrivateAttr`), not `_logger`. The `ChatCompletionAgent` inheritance is mandatory for `AgentGroupChat`.
- **Import order in conftest.py**: torch/transformers must load before jpype on Windows. This prevents DLL crashes.
- **Test markers**: Use appropriate markers from `pytest.ini` (50+ markers). Tests requiring API keys should use `@pytest.mark.requires_api` and will auto-skip.
- **Async**: All async code uses `asyncio`. Tests use `asyncio_mode = auto`.
- **New code goes in `argumentation_analysis/`**: Do not create new modules at root level.

## Dataset Privacy Discipline

The canonical dataset is `argumentation_analysis/data/extract_sources.json.gz.enc` (encrypted, tracked). Passphrase is in `.env` (`TEXT_CONFIG_PASSPHRASE`). It contains politically sensitive speeches (historical dictators, current heads of state, domestic politics). **Never let plaintext or downstream analysis leave the machine via git.**

### Rules

1. **Never commit plaintext dataset content.** No `full_text`, `raw_text`, `full_text_segment`, `raw_text_snippet`, or similar fields. If a script produces such output, write it under a gitignored path.
2. **Never commit decrypted snapshots.** Any `*_unencrypted*`, `*_decrypted*`, or bare `extract_sources.json` is blocked by `.gitignore`.
3. **Downstream analysis is gitignored by default.** `argumentation_analysis/evaluation/results/` is fully ignored — benchmark outputs, LLM judge scores, baselines, state snapshots live there. If you need to share a summary, hand-curate an aggregate-only report with opaque IDs.
4. **Use opaque IDs in commits/PRs/dashboards/chat.** Prefer `src0_ext0`, `doc_A`, `corpus_001`, `Source_3`. Avoid source names (author, title, date of the underlying speech) even in Git commit messages or dashboard posts — the repo is indexed by GitHub search.
5. **Downstream writers must consume the encrypted dataset in-memory.** Load via `argumentation_analysis.core.io_manager.load_extract_definitions` with the derived key; never persist the decrypted definitions to disk.
6. **When in doubt, gitignore.** Better to over-ignore and have to un-ignore an aggregate report than to push raw content.

A verification script lives at `scripts/security/verify_encrypted_dataset_completeness.py` — run it before deleting any plaintext file to confirm the encrypted dataset is a superset.

## Related Resources

- `D:\CoursIA` — Professor's course repository with Tweety notebooks (`MyIA.AI.Notebooks/SymbolicAI/Tweety/`) — reference for Tweety/JPype best practices
- `docs/architecture/` — System architecture docs, design documents, diagrams
- `docs/guides/` — Installation, deployment, testing guides, troubleshooting, tutorials
- `docs/projets/` — 17 student project subjects with detailed specs
- `docs/technical/` — API docs, agent components, entry points, tools reference
- `docs/reports/` — Audit reports, mission reports, analysis results
- `docs/architecture/INTEGRATION_STRATEGY.md` — Overall integration strategy and Lego architecture
- `KNOWN_ISSUES.md` — Tracked problems and active issues
- Issue #21 — Planned Tweety environment update from CoursIA

## RooSync Cluster Topology

Ce repo est cloné sur plusieurs machines qui collaborent via le dashboard RooSync workspace.
**Identifie toujours TA machine** via `hostname` avant de signer un message dashboard. Le fichier CLAUDE.md est partagé — il ne peut pas encoder l'identité d'une machine donnée.

### Machines du cluster (workspace `2025-Epita-Intelligence-Symbolique`)

| Machine ID | Rôle | Hostname | Notes |
|------------|------|----------|-------|
| `myia-ai-01` | **Coordinateur** | MyIA-AI-01 | Arbitre dispatch, merge PRs, tient le compte des rounds |
| `myia-po-2025` | Worker | MyIA-PO-2025 | Exécute tâches assignées |
| `myia-po-2023` | Worker | MyIA-PO-2023 | Exécute tâches assignées |
| `NanoClaw` (ai-01:3101) | ClusterManager | — | Monitoring passif, artefacts (ex : archéologie git #327) |

### Adressage

- **Format** : `machine-id:workspace-id` (ex : `myia-ai-01:2025-Epita-Intelligence-Symbolique`)
- **Jamais** : "po-2025" seul (ambigu — machine ou rôle ?) ou "po-2025 sur toutes machines" (contradictoire)
- **Signature dashboard** : `Claude Code @ <machine-id>:<workspace-id>` en en-tête de message

### Dashboard workspace

```
roosync_dashboard(action: "read", type: "workspace")    # début de session
roosync_dashboard(action: "append", type: "workspace",
                  tags: ["..."], content: "...")        # pendant/fin
```

### Communication cross-workspace

```python
roosync_send(
  action: "send",
  to: "myia-ai-01:2025-Epita-Intelligence-Symbolique",   # adresse du destinataire
  subject: "[EPITA] Titre",
  body: "Message..."
)
```

### MCPs disponibles

- **roo-state-manager** — RooSync (dashboards, config, sync), grounding conversationnel, codebase_search
- MCPs globaux hérités de la config machine (varient selon la machine)
