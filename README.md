# Projet d'Intelligence Symbolique EPITA

[![CI Pipeline](https://github.com/jsboigeEpita/2025-Epita-Intelligence-Symbolique/actions/workflows/ci.yml/badge.svg)](https://github.com/jsboigeEpita/2025-Epita-Intelligence-Symbolique/actions/workflows/ci.yml)

Multi-agent argumentation analysis system. Python agents (Sherlock, Watson, logic, fallacy detection) orchestrated via Semantic Kernel, with Java/Tweety formal reasoning through JPype. Built as an EPITA pedagogical platform for symbolic AI.

## Quick Start

```bash
# 1. Setup (Windows PowerShell)
./setup_project_env.ps1

# 2. Configure API key
cp .env.example .env
# Edit .env: set OPENAI_API_KEY or OPENROUTER_API_KEY

# 3. Activate and test
conda activate projet-is-roo-new
python examples/scripts_demonstration/demonstration_epita.py --quick-start
```

Linux/macOS: use `setup_project_env.sh` instead.

## Repository Map

```text
argumentation_analysis/    Core source code (agents, orchestration, services)
  agents/                  Agent implementations (BaseAgent hierarchy)
  core/                    Infrastructure (capability registry, LLM, JVM)
  orchestration/           Workflow engine (DSL, unified pipeline)
  plugins/                 Semantic Kernel @kernel_function plugins
  services/                JTMS, speech, semantic indexing
  evaluation/              Benchmarks, corpus analysis, metrics
tests/                     Test suite (unit, integration, e2e, property)
  unit/                    Unit tests
  integration/             Integration tests
  e2e/                     End-to-end tests (Playwright)
docs/                      Documentation
  architecture/            System design and diagrams
  guides/                  Installation and usage guides
  projets/                 17 student project subjects
  security/                Dataset privacy discipline
examples/                  Demo scripts and scenarios
scripts/                   Utility and maintenance scripts
interface_web/             Starlette + React web interface
api/                       FastAPI REST API (25+ routes)
```

Student project directories (sanctuarized): `1.4.1-JTMS/`, `1_2_7_argumentation_dialogique/`, `2.1.6_multiagent_governance_prototype/`, etc.

## Running Tests

```bash
# All tests (from repo root, conda activated)
pytest tests/ -v

# Fast feedback — unit tests only, no API keys needed
pytest tests/unit/ -v --ignore=tests/unit/api

# Specific marker
pytest tests/ -m "not slow" -v
```

Tests auto-skip when API keys are unavailable. See `pytest.ini` for 50+ markers.

## Architecture

Three-tier agent hierarchy:

| Tier        | Role                                | Examples                                      |
|-------------|-------------------------------------|-----------------------------------------------|
| Strategic   | Orchestration of complex workflows  | UnifiedPipeline, WorkflowDSL                  |
| Tactical    | Agent interaction coordination      | TacticalCoordinator, ProgressMonitor          |
| Operational | Specialized analysis agents         | Sherlock, Watson, FOL, PL, Extract            |

Key components:
- **CapabilityRegistry** (`core/capability_registry.py`) — agent/plugin discovery
- **WorkflowDSL** (`orchestration/workflow_dsl.py`) — declarative workflow builder
- **UnifiedPipeline** (`orchestration/unified_pipeline.py`) — 3 pre-built workflows (light/standard/full)
- **TweetyBridge** (`agents/core/logic/tweety_bridge.py`) — Java/JPype bridge for formal reasoning

Entry points: `api/main.py` (FastAPI), `argumentation_analysis/run_orchestration.py` (CLI), `interface_web/app.py` (Starlette+React).

## Student Projects

17 project subjects covering formal logic, multi-agent systems, fallacy detection, web/mobile interfaces, and more. Each has detailed specs, difficulty rating, and deliverables.

- [Project catalog](docs/projets/README.md)
- [Integration guide](docs/projets/sujets/aide/GUIDE_INTEGRATION_PROJETS.md)

## Dataset Privacy

The corpus is encrypted (`argumentation_analysis/data/extract_sources.json.gz.enc`). Passphrase in `.env` (`TEXT_CONFIG_PASSPHRASE`). It contains politically sensitive content.

- Never commit plaintext or analysis outputs
- Use opaque IDs in all commits, PRs, and discussions
- Downstream analysis goes under gitignored paths (`.analysis_kb/`)

See [security documentation](docs/security/) for full discipline rules.

## Documentation

| Directory             | Content                                       |
|-----------------------|-----------------------------------------------|
| `docs/architecture/`  | System design, diagrams, ADR                  |
| `docs/guides/`        | Installation, testing, deployment guides      |
| `docs/projets/`       | Student project subjects (17)                 |
| `docs/security/`      | Dataset privacy and security policies         |
| `docs/technical/`     | Agent components, API reference               |
| `CLAUDE.md`           | Project instructions for AI-assisted dev      |

## Environment

- **Python**: 3.10+ (Conda env `projet-is-roo-new`)
- **Java**: JDK 11+ (for Tweety/JPype formal reasoning)
- **Linting**: Black + Flake8 (CI enforced)
- **CI**: GitHub Actions (lint + test on every PR)
