# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-agent argumentation analysis system for EPITA (student project platform). Python 3.10+ with Java/JPype integration. The system analyzes rhetorical strategies, detects fallacies (8 families), performs fact-checking, and orchestrates collaborative reasoning agents (Sherlock/Watson paradigm).

**History**: The core ("tronc commun") was built by the professor inside `argumentation_analysis/`. Student PRs were merged at root level as numbered directories. Root-level overflow has been cleaned up (#34). 12 student projects have been integrated into the BaseAgent/SK architecture (#35): agents inherit from `BaseAgent`, logic is exposed via `@kernel_function` plugins, and everything is wired into `CapabilityRegistry` + `AgentFactory`. "Integrated" here means **registered and callable** — whether each project's singular contribution **reaches the reader** is a separate, measured question: the per-project audit (`docs/reports/AUDIT_DISTILLATION_3379.md`, #3379) counts 7 of 12 reaching the render (two in degraded form: JTMS as a derived signal, local LLM as a phase status), 2 channels where the render bar does not apply (mobile app, speech-to-text), 2 kept-but-inert (governance learning/coalitions, #3386; semantic index, #3387) and 1 not ported without analytical contribution (CaseAI).

## Build & Environment Setup

**IMPORTANT**: The repo is cloned across machines whose conda envs differ. Run everything inside the **most recent environment available locally** — check what your machine actually has (`conda env list`) rather than assuming a name.

Per-seat envs, and what was measured on each seat (versions, user-site, lock env) → [`docs/guides/DEV_ENV_SEATS.md`](docs/guides/DEV_ENV_SEATS.md). The rules that decide:

- **Gate versions.** CI runs pytest 9.1.1, pytest-asyncio 1.4.0, pytest-timeout 2.4.0, pytest-xdist 3.8.0, pytest-playwright 0.9.0 and JPype 1.7.1 (#2566, #2538). A dev env on other versions does not measure what the gate runs: check `python -m pytest --version` and `python -c "import jpype; print(jpype.__version__)"` before comparing with the gate.
- **CI installs `conda-lock.yml`, not `environment.yml`** (#1803). After changing a dependency in `environment.yml`, regenerate the lock in the same PR with conda-lock **4.0.4**, and declare the transitive-build census in the PR body. `libclang13` stays on the build pinned in `environment.yml` (#2856). `tests/unit/test_conda_lock_matches_environment_1803.py` guards the pair. Command and history → the same page.
- **pytest 9.1.1 conftest shim** (#3080): `tests/conftest.py` ports the upstream fix and self-disables at ≥ 9.1.2. Delete it at the next pytest bump.

```bash
# List available environments
conda env list

# Activate dev environment where it exists (preferred — most recent deps)
conda activate projet-is-roo-new

# Fallback (present on every machine)
conda activate projet-is

# From Claude Code / non-interactive shells (conda activate won't work):
conda run -n projet-is-roo-new --no-capture-output <command>   # or -n projet-is where roo-new is absent

# Full environment setup from scratch (Windows PowerShell)
./setup_project_env.ps1
```

> ⚠ **User-site shadowing**: on some seats a user-site package shadows the env's spec (#2282 A0). After provisioning, verify the resolved version, not just that the import succeeds. Detail → [`docs/guides/DEV_ENV_SEATS.md`](docs/guides/DEV_ENV_SEATS.md).

### API Keys

Copy `.env.example` to `.env`. Primary LLM access is through OpenAI:
```
OPENAI_API_KEY=sk-...
OPENAI_CHAT_MODEL_ID=gpt-5.6-luna
```

OpenRouter is also supported as an alternative:
```
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

Tests auto-skip when API keys are unavailable (no failures).

### GitHub CLI

The repo is owned by `jsboigeEpita`. The keyring has multiple accounts (`jsboige`, `jsboigeEpita`, etc.). The default active account is `jsboige` which lacks write permissions on this repo. **Always switch before write operations**:
```bash
gh auth switch --user jsboigeEpita
gh pr create ...   # now works
```
Verify with `gh auth status` — the active account should show `jsboigeEpita`. Do NOT rely on `GH_TOKEN` env var from `.env` — it does not override the keyring default.

## Testing

```bash
# Run all tests (always prefix with conda run in non-interactive shells)
conda run -n projet-is-roo-new --no-capture-output pytest tests/ -v

# Unit tests only
pytest tests/unit/ -v

# Skip slow tests
pytest tests/ -m "not slow" -v

# Single test file
pytest tests/unit/argumentation_analysis/test_deep_synthesis_agent.py -v

# Single test function
pytest tests/unit/argumentation_analysis/test_deep_synthesis_agent.py::TestHelpers::test_fallacy_family -v

# By marker (see pytest.ini for full list)
pytest tests/ -m "llm_light" -v          # Light LLM tests (<30s, ~$0.01-0.05)
pytest tests/ -m "requires_api" -v       # Tests needing API keys
pytest tests/ -m "not jpype" -v          # Skip Java/JPype tests
pytest tests/ -m "belief_set" -v         # Logic belief set tests
```

**Async mode**: `asyncio_mode = auto` — no need for `@pytest.mark.asyncio`.

**Python path**: pytest config lives in **`pytest.ini`** (the single source of truth — `pythonpath = . src`; `argumentation_analysis` and `project_core` are reachable as subdirs of `.`). Do not assume `pyproject.toml`'s `[tool.pytest.ini_options]` applies: pytest discovers exactly one config file and `pytest.ini` wins, so any `[tool.pytest.ini_options]` section is dead/overridden (removed in #1293 to kill the drift).

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

Epic #317 cleaned up the root-level overflow. `api/` and `project_core/` were kept; the other overlapping directories were deleted, moved, consolidated or archived. Table → [`docs/architecture/ROOT_OVERFLOW_317.md`](docs/architecture/ROOT_OVERFLOW_317.md).

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

- **`abc/agent_bases.py`** — `BaseAgent(ChatCompletionAgent, ABC)` and `BaseLogicAgent`. All agents inherit from `BaseAgent` which extends Semantic Kernel's `ChatCompletionAgent` (required for `AgentGroupChat` compatibility). Uses Pydantic V2 — private attributes use `PrivateAttr`; the logger is `_agent_logger` (private, `PrivateAttr`), read through the public `logger` property.
- **`logic/`** — FOL, Modal, Propositional logic agents + `TweetyBridge` (Java/JPype bridge to Tweety reasoner)
- **`extract/`** — `ExtractAgent` for extracting verifiable claims
- **`informal/`** — Informal logic + `TaxonomySophismDetector` (8-family fallacy classification)
- **`synthesis/`** — `DeepSynthesisAgent`: 9-section state-grounded synthesis report (the former inert `SynthesisAgent` was removed, #2140)
- **`oracle/`** — Cluedo dataset + `MoriartyInterrogatorAgent`
- **`pm/`** — `SherlockEnqueteAgent` (investigation orchestration)
- **`pl/`** — Propositional logic agent
- **`debate/`** — `DebateAgent(BaseAgent)` — 8-personality adversarial debate: argument generation, scoring, winner + honest-quality evaluation. Walton-Krabbe survives only as dialogical vocabulary in `protocols.py` (#2137, #1649). Alias: `EnhancedArgumentationAgent`.
- **`counter_argument/`** — `CounterArgumentAgent(BaseAgent)`. `definitions.py` carries **two distinct enums, do not conflate them**: `CounterArgumentType` (5 — direct refutation, counter-example, alternative explanation, premise challenge, reductio ad absurdum) and `RhetoricalStrategy` (5 — socratic questioning, reductio ad absurdum, analogical counter, authority appeal, statistical evidence). 5-criteria weighted evaluator.
- **`governance/`** — Governance simulation. `governance_methods.py` exposes **7 governance methods**, of which **5 are voting rules** (majority, plurality, Borda, Condorcet, quadratic) and **2 are distributed-consensus protocols** (Byzantine, Raft) — the latter are not scrutins, do not count them as voting methods. `social_choice.py` adds **8 more social-choice functions**: approval voting, STV, Copeland, Kemeny-Young (+ a `_safe` variant), Schulze, Condorcet winner, pairwise matrix. Plus conflict resolution and consensus metrics. NOT a BaseAgent — logic exposed via plugin.
- **`quality/`** — Argument quality evaluation: **9 virtue detectors** in `quality_evaluator.py`, named in French — `clarte`, `pertinence`, `presence_sources`, `refutation_constructive`, `structure_logique`, `analogie_pertinente`, `fiabilite_sources`, `exhaustivite`, `redondance_faible`. `agentic_virtue_detectors.py` adds LLM-backed variants through an **injectable** `LLMCallable` (so a grep for `kernel.invoke`/`ChatCompletion` will wrongly report this module as LLM-free). Exposed via plugin.

### Semantic Kernel Plugins (`argumentation_analysis/plugins/`)

- **`quality_scoring_plugin.py`** — `QualityScoringPlugin`: **4** `@kernel_function` methods wrapping `ArgumentQualityEvaluator` (`evaluate_argument_quality`, `get_quality_score`, `evaluate_with_cross_kb_context`, `list_virtues`)
- **`french_fallacy_plugin.py`** — `FrenchFallacyPlugin`: 3 `@kernel_function` methods for 3-tier hybrid fallacy detection (French NLP)
- **`governance_plugin.py`** — `GovernancePlugin`: **6** `@kernel_function` methods (`detect_conflicts_fn`, `resolve_conflict_fn`, `compute_consensus_metrics`, `list_governance_methods`, `social_choice_vote`, `find_condorcet_winner`)

> ⚠ **Capability census guards.** Full rules and measured figures → [`docs/architecture/CAPABILITY_CENSUS_GUARDS.md`](docs/architecture/CAPABILITY_CENSUS_GUARDS.md).
> - Count the decorated `def`s, never the `@kernel_function` lines: two class docstrings open a line with it.
> - **One capability surface per module** (#1842). A new capability goes on the surface `setup_registry()` populates, **and gets a consumer**: a phase asking for it, or a table a resolver reads. `test_one_capability_surface_1842.py` reddens on an unwired definer or a new zero-demand capability, and its `PENDING_TRIAGE` map (#1604) only shrinks.
> - **"Requested" means `add_phase(capability=…)`**, or a table a resolver reads, never a `find_*` grep. Production calls only the untyped `find_for_capability`, and `test_capability_resolver_surface_1980.py` re-derives that partition.

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
- **`config.py`** / **`environment.py`** — Configuration management. The canonical checkout-root `.env` loader is `argumentation_analysis/config/env_loader.py`; `project_core/managers/environment_manager.py` only re-exports it. Keep imports from the installable `argumentation_analysis` package independent of checkout-only `project_core` (#2708, #2346).
- **`capability_registry.py`** — CapabilityRegistry + ServiceDiscovery (Lego architecture)
- **`shared_state.py`** — `UnifiedAnalysisState` extending `RhetoricalAnalysisState` with 10 new dimensions

### Integrated Services (`argumentation_analysis/services/`)

- **`jtms/jtms_core.py`** — JTMS (Justification-based Truth Maintenance System): Belief, Justification, JTMS classes
- **`local_llm_service.py`** — OpenAI-compatible adapter for local LLM endpoints
- **`speech_transcription.py`** — Speech-to-text adapter (HTTP service)
- **`semantic_index_service.py`** — Kernel Memory semantic indexing adapter

### Key Integration Points

- **Java/JPype**: Tweety logic library accessed via `jpype1`. JVM must be initialized before use (`jvm_setup.py`). Tests marked `@pytest.mark.jpype` or `@pytest.mark.tweety`.
- **Semantic Kernel**: All agents use SK's kernel for LLM orchestration. Agent plugins are loaded via `agents/factory.py` (`AGENT_SPECIALITY_MAP` / `_PLUGIN_REGISTRY`).
- **Pydantic V2**: Data validation throughout. Recent migration from V1.

### Entry Points

**Modern (fully integrated with Lego Architecture):**
- `api/main.py` — **FastAPI REST API** (RECOMMENDED). 7 routers, 25+ routes. Agent capabilities, proposals, mobile, WebSocket streaming. Uses CapabilityRegistry + UnifiedPipeline + WorkflowDSL. Launch: `uvicorn api.main:app --reload --port 8000`

**Web UI:**
- `interface_web/app.py` — **Starlette web app** (formerly Flask). Serves React frontend + analysis API. Uses ServiceManager (not UnifiedPipeline). **Note**: React build at `services/web_api/interface-web-argumentative/build/` is required (not in git — run `npm run build` in that dir first). Launch: `uvicorn interface_web.app:app --port 5003`

**CLI (multi-mode orchestration):**
- `argumentation_analysis/run_orchestration.py` — CLI runner with `--mode pipeline|conversational|hierarchical|cluedo|sherlock_modern` and `--workflow light|standard|full|collaborative`
- `argumentation_analysis/main_orchestrator.py` — Interactive orchestrator with Tkinter UI

**Pedagogical:**
- `examples/02_core_system_demos/scripts_demonstration/demonstration_epita.py` — Interactive demo for courses/soutenances

### Orchestration Modes

The system supports 4 orchestration modes. See `docs/architecture/ORCHESTRATION_MODES.md` for full details.

| Mode | Status | Entry Point | Description |
|------|--------|-------------|-------------|
| Sequential (Pipeline) | ACTIVE | `--mode pipeline` (default) | Phases run in DAG order via WorkflowExecutor |
| Conversational | ACTIVE | `--mode conversational` | Multi-agent dialogue via SK AgentGroupChat |
| Hierarchical | ACTIVE | `--mode hierarchical --hierarchical-mode bridge\|delegation` | `bridge` (M2, RA-10 #1069): StrategicManager → Lego WorkflowExecutor. `delegation` (M3): Strategic → Tactical → Operational, dispatching through `CapabilityRegistry` via `RegistryBackedOperationalRegistry` (BO-1 #1471, fail-loud `DelegationError` without a registry). ~10.3k LOC, `strategic_bridge.py` (RA-4 #1049) syncs NL objectives/decisions into `UnifiedAnalysisState` with privacy scrubbing. |
| Cluedo | ACTIVE | Dedicated scripts | Sherlock-Watson investigation game |

**Cross-mode comparison**: `scripts/compare_orchestration_modes.py` runs the engines on the same corpus and emits markdown + JSON with trade-off metrics. It is the instrument of #1735 and #3378. Calibrate `--max-wall-seconds` before comparing: at the 180s default every mode dies mid-DAG. Mode keys, aliases and budget figures → [`docs/architecture/ORCHESTRATION_MODES.md`](docs/architecture/ORCHESTRATION_MODES.md) §Cross-mode comparison.

## CI/CD

GitHub Actions (`.github/workflows/ci.yml`):
1. **lint-and-format**: Black + Flake8 on Windows/Conda
2. **automated-tests**: Pytest on Windows + Conda. The JVM runs on the portable JDK 17 that `jvm_setup.py` provisions into `portable_jdk/` (cached, #1874); there is no setup-java step (#1959), and the floor is Java 15 (`settings.jvm.min_java_version`). Tests skip gracefully without API keys.

## Key Conventions

- **Pydantic V2 agents**: the logger is `_agent_logger`, a private `PrivateAttr`; access it through the public `logger` property (`self._agent_logger` directly only inside the base class). The `ChatCompletionAgent` inheritance is mandatory for `AgentGroupChat`.
- **Import order in conftest.py**: torch/transformers must load before jpype on Windows. This prevents DLL crashes.
- **Test markers**: Use appropriate markers from `pytest.ini` (50+ markers). Tests requiring API keys should use `@pytest.mark.requires_api` and will auto-skip.
- **Async**: All async code uses `asyncio`. Tests use `asyncio_mode = auto`.
- **New code goes in `argumentation_analysis/`**: Do not create new modules at root level.
- **Metric mandate renders are reproducible** (#2353): a PR that shows a real render cites the command that reproduces it; the producer is tracked under `scripts/`, its output stays gitignored, and the render opens with a provenance header. Convention and producer table: `docs/guides/RENDER_REPRODUCIBILITY.md`.

## STOP&REPAIR — Never Workaround

User mandate 2026-09-17 (verbatim): « Il faut réparer tout ce qui est défectueux, pas de workaround » · « STOP&REPAIR, never workaround » · « vous oubliez régulièrement en enterrant la moitié de notre code utile ».

- **A workaround discovered is a defect to open and repair, never a documentation item.** Carried env pins (`JVM_TWEETY_VERSION` per-process), mandatory secret flags, manual steps that "everyone knows", tolerated "baselined" failures — each masks a repairable root. Measured instance: the fleet-wide `JVM_TWEETY_VERSION=1.28` pin masked "`initialize_jvm()` returns False despite a complete local classpath" — repaired in #2278 as the common root of #2277's ×40 WARN motif and #2276's 11 failed phases.
- **Burial requires proof of non-utility.** The Cleanup Gate bar applies equally to `pytest.ini` ignores, `PENDING_TRIAGE` entries and `_archives/`/`docs/archives/` moves: burying useful code is the same failure as deleting it, and a workaround must not outlive its repair. Instance: `test_analysis_service_mock.py` stayed ignored in `addopts` for months after the root conflict was fixed in conftest (un-buried in #2279).

## The Cap

User, 2026-11-03 (Epic #3374). The project's outcome is **the final differential with the same-model zero-shot**, in a report a non-specialist can read. The report gives a *neutralising* light on the manipulations a debate carries: the same map for every side, never a partisan verdict. In its ultimate form, it synthesises the next debate.

The formal and informal instruments are what zero-shot cannot easily reach once complexity is not trivial:

- the calibrated Argumentum taxonomy descent;
- Dung, ASPIC+ and bipolar argumentation;
- JTMS;
- FOL entailment queries;
- Tweety's argumentative extensions.

They are **lenses**: each is worth only what the agentic harness points it at, meaning the KB it is given and the question it is asked. Orchestration counts as much as individual capability, so the 5 engines of `scripts/compare_orchestration_modes.py` are compared on the same bar (#3378). Restitution is part of the outcome, not decoration: clear metaphors, aphorisms, and analogies that are not abusive.

## When v1 Is Done — the Panel Bar

User decision 2026-11-03, superseding the 19/10 one-document tunnel. Measured: 21 paid passes on one document, the counter still 0/2. That criterion measured the reader's resolution, not the analysis, so it could not converge.

- **Bar.** On a 10-document panel taken from #2841 (#3375), the pipeline is compared with the same-model zero-shot. The judging is blind, done by a model of another family and by the coordinator.
- **Exhaustion**, declared by the coordinator. On the panel, all three must hold:
  1. no severe defect remains;
  2. two consecutive cycles pass without the pipeline-vs-zero-shot verdict progressing;
  3. every remaining gap is named and classed, either as fixable (so v1 is not done) or as out of the architecture's reach, with the reason.
- **The user reads last.** The user's reading is the final validation, not a tuning instrument. A dossier is submitted only with an exhaustion declaration that holds.
- **Batches.** Each paid run covers the whole panel. Defects are sorted by class and severity, with one issue per class. Workers take several fixes per cycle. Paid spends and merges stay with the coordinator.

Native failures and revival epics continue as ordinary improvement work. The coordinator's DONE entries report the panel verdict table and the cycle count for condition 2.

## Dataset Privacy Discipline

The canonical dataset is `argumentation_analysis/data/extract_sources.json.gz.enc` (encrypted, tracked). Passphrase is in `.env` (`TEXT_CONFIG_PASSPHRASE`). It contains politically sensitive speeches (historical dictators, current heads of state, domestic politics). **Never let plaintext or downstream analysis leave the machine via git.**

### Rules

1. **Never commit plaintext dataset content.** No `full_text`, `raw_text`, `full_text_segment`, `raw_text_snippet`, or similar fields. If a script produces such output, write it under a gitignored path.
2. **Never commit decrypted snapshots.** Any `*_unencrypted*`, `*_decrypted*`, or bare `extract_sources.json` is blocked by `.gitignore`.
3. **Downstream analysis is gitignored by default.** `argumentation_analysis/evaluation/results/` is fully ignored — benchmark outputs, LLM judge scores, baselines, state snapshots live there. If you need to share a summary, hand-curate an aggregate-only report with opaque IDs.
4. **Use opaque IDs on GitHub-indexed surfaces** — commit messages, PR descriptions, PR comments, issue titles/bodies. Prefer `src0_ext0`, `doc_A`, `corpus_001`, `Source_3` there, and avoid source names (author, title, date of the underlying speech) on them — the repo is indexed by GitHub search. **The frontier is GitHub indexation, not "any cluster channel": private roosync channels (`roosync_dashboard` dashboards, `roosync_messages` messaging incl. attachments — stored on the shared GDrive `$ROOSYNC_SHARED_PATH`, not GitHub-indexed), user↔coordinator chat, and gitignored local artifacts (`evaluation/results/`) all accept real names.** The test before naming a source: *is this surface indexed by GitHub?* If yes → opaque; if no → real names are fine.
5. **Downstream writers must consume the encrypted dataset in-memory.** Load via `argumentation_analysis.core.io_manager.load_extract_definitions` with the derived key; never persist the decrypted definitions to disk.
6. **When in doubt, gitignore.** Better to over-ignore and have to un-ignore an aggregate report than to push raw content.
7. **A document identifier never enters a tracked file — not even in a leak detector (#2168).** Any label that maps 1:1 to one encrypted document (a `source_name` from the census) stays out of every tracked file: fixtures, comments, and detector pattern lists alike. "The detector needs the real names to catch them" is not a license — a detector that enumerates corpus identifiers publishes the census the encryption protects. Detect by **class** (generic public vocabulary — `argumentation_analysis/evaluation/leak_patterns.py`), or derive instance tokens at runtime from the in-memory decrypted definitions.

A verification script lives at `scripts/security/verify_encrypted_dataset_completeness.py` — run it before deleting any plaintext file to confirm the encrypted dataset is a superset.

## Cleanup Gate — PR Deletion Policy

Established 2026-05-16 after the audit at `docs/reports/AUDIT_ROGUE_CLEANUP_2026-05-16.md` (issues #580 #581). The "Consolider != Archiver" rule (global CLAUDE.md) was not enough on its own — design docs kept being silently deleted as "cleanup" (e.g. `DESIGN_PARALLEL_WORKFLOW.md` via PR #130, `architecture_fallacy_workflows.md` via PR #442). Rules below apply prospectively to all PRs opened after their adoption.

### Rules

1. **Per-file justification.** Any cleanup PR deleting `.py`, `.md`, `.json`, `.yaml`, or `.toml` files MUST include a `## Files removed and why` section in the PR body. Each entry lists the file with its **role** (design / archive / draft / test / config / other) and a **1-sentence reason**. Reviewers MUST request changes if missing.
2. **Origin check.** Before deleting any file not referenced in the last 3 months, run `git log --all -- <path>` to verify origin. If the most recent commit touching it is a `feat(` commit, treat as HIGH suspicion — design docs are `feat(` artifacts and have been mistaken for drafts. Require explicit justification.
3. **Bulk deletion table.** Cleanup PRs with more than 5 file deletions MUST include a markdown table in the PR body: `| File | Type | Last useful date | Reason for deletion |`. Bulk deletions without this table are NOT to be merged.

Full proposal text + reviewer checklist + commit-template are in `docs/proposals/CLAUDE_MD_CLEANUP_GATE_ADDENDUM.md`. A pre-commit hook sketch enforcing Rule A is in `docs/proposals/PRE_COMMIT_HOOK_CLEANUP_GATE.md`.

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
