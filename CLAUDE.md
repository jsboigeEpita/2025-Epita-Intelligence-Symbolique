# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-agent argumentation analysis system for EPITA (student project platform). Python 3.10+ with Java/JPype integration. The system analyzes rhetorical strategies, detects fallacies (8 families), performs fact-checking, and orchestrates collaborative reasoning agents (Sherlock/Watson paradigm).

**History**: The core ("tronc commun") was built by the professor inside `argumentation_analysis/`. Student PRs were merged at root level as numbered directories. Over time, AI-assisted development caused code to "overflow" from `argumentation_analysis/` to root-level directories. The structure is being progressively cleaned up.

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

Copy `.env.example` to `.env`. Primary LLM access is through OpenRouter:
```
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=gpt-4o-mini
```

Tests auto-skip when API keys are unavailable (no failures).

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
| `services/` | `argumentation_analysis/services/` | **PARTIAL** — legacy `web_api_from_libs/` archived; MCP server + UI wrappers kept |
| ~~`plugins/`~~ | ~~`argumentation_analysis/plugins/`~~ | **MIGRATED** — `AnalysisToolsPlugin` → `argumentation_analysis/plugins/analysis_tools/`; minor plugins archived |
| `src/` | `argumentation_analysis/agents/` | **DEFERRED** to #35 — legacy plugin/benchmark framework, 13 active imports |
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

### Core Services (`argumentation_analysis/core/`)

- **`communication/`** — Multi-channel messaging: hierarchical, collaboration, pub/sub, request/response, with operational/tactical/strategic adapters
- **`llm_service.py`** — LLM integration layer
- **`jvm_setup.py`** — JVM initialization for JPype/Tweety
- **`bootstrap.py`** — System initialization
- **`config.py`** / **`environment.py`** — Configuration management

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
- `KNOWN_ISSUES.md` — Tracked problems and active issues
- Issue #21 — Planned Tweety environment update from CoursIA
