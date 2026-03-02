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
conda activate projet-is-roo-new    # SK 1.37, Pydantic 2.11, JPype 1.6

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

### Known Overflow (to be cleaned up)

Several root-level directories contain code that should live under `argumentation_analysis/`:

| Root directory | Overlaps with | Status |
|---|---|---|
| `api/` | `argumentation_analysis/api/` | **KEPT** — root has general FastAPI endpoints, inside has JTMS-specific |
| ~~`core/`~~ | ~~`argumentation_analysis/core/`~~ | **ARCHIVED** → `docs/archives/core_overflow/` |
| ~~`demos/`~~ | ~~`argumentation_analysis/demos/`~~ | **MOVED** → `examples/03_demos_overflow/` |
| ~~`services/`~~ | ~~`argumentation_analysis/services/`~~ | **MIGRATED** — `mcp_server/` → `argumentation_analysis/services/mcp_server/`; legacy archived |
| ~~`plugins/`~~ | ~~`argumentation_analysis/plugins/`~~ | **MIGRATED** — `AnalysisToolsPlugin` → `argumentation_analysis/plugins/analysis_tools/`; minor plugins archived |
| ~~`src/`~~ | ~~`argumentation_analysis/agents/`~~ | **MIGRATED** → `argumentation_analysis/plugin_framework/` (duplicate orchestration_service deleted) |
| `project_core/` | `argumentation_analysis/core/` | **KEPT** — infrastructure utilities (NOT business logic) |

**Rule**: When adding new code, put it inside `argumentation_analysis/`. Do not add new modules at root level.

### Student Project Directories (root level, correct)

`1.4.1-JTMS`, `1_2_7_argumentation_dialogique`, `2.1.6_multiagent_governance_prototype`, `2.3.2-detection-sophismes`, `2.3.3-generation-contre-argument`, `2.3.5_argument_quality`, `2.3.6_local_llm`, `3.1.5_Interface_Mobile`

### Other Root Directories

- `interface_web/` — Flask/Jinja web UI with its own routes and services
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

- `argumentation_analysis/main_orchestrator.py` — Web orchestrator
- `argumentation_analysis/run_orchestration.py` — CLI orchestration runner
- `examples/02_core_system_demos/scripts_demonstration/demonstration_epita.py` — Interactive pedagogical demo

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

## Related Resources

- `D:\CoursIA` — Professor's course repository with Tweety notebooks (`MyIA.AI.Notebooks/SymbolicAI/Tweety/`) — reference for Tweety/JPype best practices
- `docs/architecture/` — System architecture docs, design documents, diagrams
- `docs/guides/` — Installation, deployment, testing guides, troubleshooting, tutorials
- `docs/projets/` — 17 student project subjects with detailed specs
- `docs/technical/` — API docs, agent components, entry points, tools reference
- `docs/reports/` — Audit reports, mission reports, analysis results
- `docs/validation/` — Test verification reports
- `docs/integration/plans/` — 12 per-project integration plans (one per student project)
- `docs/architecture/INTEGRATION_STRATEGY.md` — Overall integration strategy and Lego architecture
- `KNOWN_ISSUES.md` — Tracked problems and active issues
- Issue #21 — Planned Tweety environment update from CoursIA
