# Audit Report: 4 Core Features

**Issue**: #32
**Date**: 2026-02-23
**Baseline**: commit `b270a6f2` (main branch, clean)
**Test Health**: 0 failed, 2264+ passed, ~67 skipped (CI mode)

---

## Executive Summary

| Feature | Working State | Severity | Test Coverage |
|---------|--------------|----------|---------------|
| 1. Demo EPITA | Functional (menu/quick-start) | Low | Minimal (2 tests) |
| 2. Rhetorical Analysis | **BROKEN** (import error) | **Critical** | Moderate (13 tests) |
| 3. Sherlock-Watson Games | Functional (scripted) | Medium | Excellent (54+ tests) |
| 4. Web Applications | Functional (4 apps, overlapping) | Medium | Adequate (8 tests) |

**Critical finding**: The two main CLI entry points for rhetorical analysis (`main_orchestrator.py` and `run_orchestration.py`) are broken due to a deleted module. The replacement (`analysis_runner_v2.py`) exists but imports were never updated.

---

## Feature 1: Demo EPITA

### Entry Point
- `examples/02_core_system_demos/scripts_demonstration/demonstration_epita.py`

### What It Does
Interactive pedagogical demonstration with 7 execution modes:
- `--interactive` — Menu-driven with pauses
- `--quick-start` — Runs all 6 categories sequentially
- `--metrics` — Displays project statistics only
- `--all-tests` — Non-interactive full execution with report
- `--validate-custom` — Mock vs real processing detection
- `--custom-data "text"` — Tests with user-provided text
- `--legacy` — Falls back to original script

### Architecture
```
demonstration_epita.py
  |-- modules/demo_utils.py (Colors, Symbols, DemoLogger, config loader)
  |-- configs/demo_categories.yaml (6 categories)
  |-- modules/demo_*.py (6 category modules, dynamically loaded)
```

6 demo categories configured in YAML:
1. Tests & Validation (`demo_tests_validation`)
2. Agents Logiques & Argumentation (`demo_analyse_argumentation`)
3. Services Core & Extraction (`demo_services_core`)
4. Integrations & Interfaces (`demo_integrations`)
5. Cas d'Usage Complets (`demo_cas_usage`)
6. Outils & Utilitaires (`demo_outils_utils`)

### Working State
- **Menu display**: Works
- **Module loading**: Works (dynamic `importlib` loading)
- **Category execution**: Depends on individual modules
- **Config loading**: Works via `demo_categories.yaml`

### Issues Found
1. **`valider_environnement()` checks for `project_core/`** (line in `demo_utils.py`). This is a legacy root-level directory that will be removed in #34. When removed, the validation will always fail, blocking the demo.
2. **No real LLM integration** in demo modules — they mostly run pytest via subprocess or display pre-computed results.
3. **`ensure_yaml_dependency()`** auto-installs PyYAML at runtime (line 44-50). This should be a declared dependency, not auto-installed.

### Test Coverage
- `tests/integration/test_run_demo_epita.py` — Integration test
- `tests/integration/_test_consolidation_demo_epita.py` — Consolidation validation
- **Gap**: No unit tests for individual demo modules

### Dependencies
- `project_core.utils.shell` (for `run_sync`, `run_in_activated_env`, `ShellCommandError`)
- `PyYAML` (auto-installed)
- `argumentation_analysis.core.environment` (auto-activation)

### Recommendations
- [ ] Replace `project_core/` check in `valider_environnement()` with current directory structure
- [ ] Add PyYAML to declared dependencies (remove auto-install)
- [ ] Add unit tests for at least 2-3 demo modules

---

## Feature 2: Agentic Rhetorical Analysis

### Entry Points
- `argumentation_analysis/main_orchestrator.py` — Primary CLI (Tkinter UI or `--skip-ui`)
- `argumentation_analysis/run_orchestration.py` — Secondary CLI (`--file`, `--text`, or `--ui`)

### What It Should Do
Multi-phase analysis pipeline using 6 agents:
1. **Phase 1 — Informal Analysis** (5 turns): PM + InformalAnalysisAgent detect fallacies
2. **Phase 2 — Formal Analysis** (5 turns): PM + PropositionalLogicAgent + Watson formalize arguments
3. **Phase 3 — Synthesis** (5 turns): All agents produce consolidated report

Agents (from `AgentFactory`):
- `ProjectManagerAgent` — Orchestrator/coordinator
- `InformalAnalysisAgent` — Fallacy detection, rhetoric
- `PropositionalLogicAgent` — Formal logic (requires JVM)
- `ExtractAgent` — Fact/claim extraction
- `SherlockEnqueteAgent` — Investigation orchestration
- `WatsonLogicAssistant` — Logic assistant

### Working State: **BROKEN**

**Critical**: `analysis_runner.py` was deleted and replaced by `analysis_runner_v2.py`, but two entry points still import the old module:

| File | Line | Broken Import | Required Fix |
|------|------|---------------|-------------|
| `main_orchestrator.py` | 214 | `from ...analysis_runner import AnalysisRunner` | Change to `analysis_runner_v2 import AnalysisRunnerV2` |
| `run_orchestration.py` | 133 | `from ...analysis_runner import run_analysis` | Change to `analysis_runner_v2 import run_analysis_v2` |

The `main_orchestrator.py` import is inside a try/except (line 226), so it degrades to an error message rather than a crash. But the analysis **cannot complete**.

Additionally, 3 legacy test scripts also reference the deleted module:
- `agents/test_scripts/orchestration/test_orchestration_scale.py`
- `agents/runners/test/orchestration/test_orchestration_scale.py`
- `agents/runners/test/orchestration/test_orchestration_complete.py`

### `analysis_runner_v2.py` Assessment
The replacement file is functional:
- `AnalysisRunnerV2` class with `run_analysis(text_content, llm_service)` async method
- Uses `AgentGroupChat` with `CyclicSelectionStrategy` and custom termination
- Produces structured trace output via `enhanced_real_time_trace_analyzer`
- **Issue**: `__main__` block hardcodes `gpt-4-turbo-2024-04-09` model (should be configurable)

### Test Coverage
13 test files cover the orchestration pipeline:
- Unit: `test_analysis_runner.py`, `test_run_analysis_conversation.py`, `test_integration.py`, `test_integration_balanced_strategy.py`, `test_integration_end_to_end.py`, `test_agent_interaction.py`, `test_text_analyzer.py`, `test_unified_orchestrations.py`
- Integration: `test_orchestration_finale_integration.py`, `test_unified_system_integration.py`
- Environment: `test_project_module_imports.py`

### Dependencies
- Semantic Kernel (`AgentGroupChat`, `ChatCompletionAgent`, `CyclicSelectionStrategy`)
- `AgentFactory` (creates all 6 agents)
- `RhetoricalAnalysisState` (shared analysis state)
- JVM/Tweety (for `PropositionalLogicAgent`)
- LLM service (OpenAI-compatible)

### Recommendations
- [ ] **CRITICAL**: Fix `main_orchestrator.py` import to use `analysis_runner_v2`
- [ ] **CRITICAL**: Fix `run_orchestration.py` import to use `analysis_runner_v2`
- [ ] Create `analysis_runner.py` shim module for backward compatibility (or delete old references)
- [ ] Fix hardcoded model in `analysis_runner_v2.__main__`
- [ ] Clean up 3 legacy test scripts with stale imports

---

## Feature 3: Sherlock-Watson Investigation Games

### Entry Points
- `scripts/sherlock_watson/run_cluedo_oracle_enhanced.py` — Cluedo game
- `scripts/sherlock_watson/run_einstein_oracle_demo.py` — Einstein puzzle

### What They Do

**Cluedo Oracle Enhanced**: Multi-agent investigation game where Sherlock, Watson, and Moriarty (Oracle) collaborate to solve a Cluedo mystery.
- Uses `CluedoExtendedOrchestrator` with configurable strategies
- Supports `--test-mode`, `--max-turns`, `--oracle-strategy`
- Real LLM integration via Semantic Kernel
- Agent interactions through `run_cluedo_oracle_game()` from `cluedo_runner.py`

**Einstein Oracle Demo**: Logic puzzle where Moriarty gives progressive clues and Sherlock/Watson deduce the solution.
- Uses `EinsteinOracleOrchestrator` with scripted responses
- Solution is hardcoded (German owns the fish)
- Agents give pre-written responses (NOT real LLM calls)
- Supports `--integration-test` mode

### Working State

**Cluedo**: Functional when called with a properly configured Kernel and AppSettings.
- Bootstrap handles JVM init, LLM service creation, kernel configuration
- `--test-mode` forces mock LLM (no API key needed)
- Full pipeline: bootstrap → kernel setup → orchestrator → agent group chat → report

**Einstein**: Functional but **scripted** (no real AI reasoning).
- Sherlock's "analysis" is a predetermined sequence of strings (lines 323-334)
- Solution always "found" at round 9+ regardless of clue content
- Watson's assistance is also scripted (lines 358-365)
- The demo demonstrates the orchestration framework, not real AI deduction

### Issues Found
1. **Einstein demo is scripted**: Sherlock/Watson responses are hardcoded strings, not LLM-generated. This means the demo doesn't actually test AI reasoning capability.
2. **`cluedo_runner.py` standalone mode broken**: `main()` at line 59 calls `run_cluedo_oracle_game(kernel=kernel)` without required `settings` argument → `TypeError`.
3. **Einstein hardcodes `gpt-4` model** (line 464), not `gpt-5-mini`.
4. **Einstein writes trace to `results/sherlock_watson/`** (auto-created) — contributes to root-level directory clutter.

### Test Coverage
Excellent — 54+ test files:
- 11 integration tests (Cluedo workflow, Einstein, oracle behavior)
- 9 unit tests (oracle agents, JTMS, dataset management)
- 17+ validation tests (`tests/validation_sherlock_watson/`)
- 3 worker/performance tests
- Many require `OPENAI_API_KEY` and auto-skip without it

### Dependencies
- Semantic Kernel (Kernel, ChatCompletionAgent)
- `CluedoExtendedOrchestrator`, `CluedoOracleState`, `CluedoDataset`
- `SherlockEnqueteAgent`, `WatsonLogicAssistant`, `MoriartyInterrogatorAgent`
- JVM/Tweety (for Cluedo; optional for Einstein)
- LLM service (real for Cluedo, simulated for Einstein)

### Recommendations
- [ ] Make Einstein demo use real LLM calls (at least optionally)
- [ ] Fix `cluedo_runner.py` standalone `main()` — add `settings` parameter
- [ ] Update hardcoded `gpt-4` model in Einstein to use config/env
- [ ] Move Einstein trace output directory to `logs/` (already in .gitignore)

---

## Feature 4: Web Applications

### Overview

The project has **4 separate web applications** with overlapping functionality:

| App | Framework | Port | Entry Point | Purpose |
|-----|-----------|------|-------------|---------|
| Root FastAPI | FastAPI | 8000 | `api/main.py` | General analysis + Tweety/Dung |
| Inner FastAPI | FastAPI | — | `argumentation_analysis/api/main.py` | JTMS/Plugin orchestration |
| Flask API | Flask | 5004 | `services/web_api_from_libs/app.py` | Analysis with React frontend |
| Starlette | Starlette | 5003 | `interface_web/app.py` | Full UI + ServiceManager |

### App-by-App Assessment

#### Root FastAPI (`api/main.py`)
- **Endpoints**: `/` (status), `/health`, `/api/*` (analysis, examples, Dung framework)
- **Startup**: Calls `initialize_project_environment()` → JVM init + LLM service
- **Issue**: Root endpoint and health check import `jpype` directly in route handler (line 62, 78) — will crash if jpype unavailable
- **API format**: `{status: "healthy", details: {api, jvm}}`

#### Inner FastAPI (`argumentation_analysis/api/main.py`)
- **Endpoints**: `/api/v2/analyze` (POST with plugin_name)
- **Architecture**: Uses `OrchestrationService` singleton with plugin system
- **Minimal**: Only 1 endpoint + 1 test plugin, 62 lines total
- **Purpose**: JTMS-specific analysis via plugins

#### Flask API (`services/web_api_from_libs/app.py`)
- **Endpoints**: `/api/*` (analysis, validation, fallacy, framework, logic)
- **Services**: AnalysisService, ValidationService, FallacyService, FrameworkService, LogicService
- **Frontend**: Serves React build from `services/web_api/interface-web-argumentative/build/`
- **ASGI adapter**: Has `WsgiToAsgi` wrapper for Uvicorn compatibility
- **Issue**: Imports `environment_loader` from `scripts.utils` — may fail if scripts/ is reorganized
- **Issue**: Uses `MockFallacyDetector` always (line 116) — real detection not wired
- **API format**: `{success: true, fallacies: [...]}`

#### Starlette (`interface_web/app.py`)
- **Endpoints**: `/api/status`, `/api/health`, `/api/analyze`, `/api/examples`, `/api/v1/framework/analyze`
- **Architecture**: Async lifespan with `ServiceManager` + `NLPModelManager`
- **Frontend**: Same React build directory as Flask app
- **Depends on**: `ServiceManager` from `orchestration.service_manager`
- **API format**: `{analysis_id, status, results, metadata: {duration}}`

### Issues Found

1. **4 overlapping web apps** with different frameworks, API formats, and endpoint structures. This creates confusion about which app to run and which format to expect.

2. **Root FastAPI imports jpype in route handlers**: Lines 62 and 78 — will crash if jpype is not available (e.g., in Docker without Java).

3. **Flask app always uses MockFallacyDetector**: Line 116 creates `MockFallacyDetector()` unconditionally. Real fallacy detection is never used in the Flask API.

4. **Starlette and Flask serve the same React frontend**: Both point to `services/web_api/interface-web-argumentative/build/`. Running both would create port conflicts.

5. **No shared API contract**: Each app has a different response format for the same operations.

### Test Coverage
8 test files:
- Root FastAPI: `test_fastapi_simple.py` (10 tests), `test_fastapi_gpt4o_authentique.py` (10 tests), `test_api_direct.py`, `test_api_direct_simple.py`, `test_analysis_service_mock.py`
- Inner FastAPI: `test_main_api.py`
- Flask: `test_argument_analyzer_client.py` (3 tests)
- Starlette: **No dedicated tests**

### Dependencies

| App | LLM | JVM | Frontend | External |
|-----|-----|-----|----------|----------|
| Root FastAPI | via bootstrap | Required | None | jpype |
| Inner FastAPI | None | None | None | None |
| Flask | create_llm_service | Optional | React build | flask-cors, asgiref |
| Starlette | via ServiceManager | via ServiceManager | React build | starlette, uvicorn |

### Recommendations
- [ ] Document which web app to use for which purpose (or consolidate)
- [ ] Add jpype availability guard in Root FastAPI route handlers
- [ ] Wire real FallacyDetector in Flask app (replace MockFallacyDetector)
- [ ] Add tests for Starlette app (`interface_web/app.py`)
- [ ] Standardize API response format across all apps (or document differences)

---

## Cross-Cutting Issues

### 1. Deleted `analysis_runner.py` — Broken Import Chain
The most critical finding. `analysis_runner.py` was replaced by `analysis_runner_v2.py` but 5+ files still reference the old name. This breaks the two main CLI entry points for rhetorical analysis.

**Affected files**:
- `argumentation_analysis/main_orchestrator.py:214`
- `argumentation_analysis/run_orchestration.py:133`
- `argumentation_analysis/agents/test_scripts/orchestration/test_orchestration_scale.py:99`
- `argumentation_analysis/agents/runners/test/orchestration/test_orchestration_scale.py:101`
- `argumentation_analysis/agents/runners/test/orchestration/test_orchestration_complete.py:200`
- `argumentation_analysis/notebooks/main_orchestrator.ipynb:402`

### 2. Hardcoded Model IDs
Several scripts hardcode LLM model IDs instead of reading from config/environment:
- `analysis_runner_v2.py` → `gpt-4-turbo-2024-04-09`
- `run_einstein_oracle_demo.py` → `gpt-4`
- Current project uses `gpt-5-mini` via `.env`

### 3. Root-Level Directory Overflow
Consistent with issue #34's assessment:
- `api/` overlaps with `argumentation_analysis/api/`
- `services/` overlaps with `argumentation_analysis/services/`
- `interface_web/` is standalone but should be documented
- `project_core/` is legacy but still referenced by demo code

### 4. Documentation Gaps
- No single document explains which web app to use
- `run_orchestration.py` and `main_orchestrator.py` are not compared/contrasted
- Einstein demo's scripted nature is not documented (could mislead students)

---

## Priority Fix List

### Critical (blocks core functionality)
1. Fix `main_orchestrator.py` import: `analysis_runner` → `analysis_runner_v2`
2. Fix `run_orchestration.py` import: `analysis_runner` → `analysis_runner_v2`

### High (affects user experience)
3. Fix `cluedo_runner.py` standalone `main()` — add missing `settings` argument
4. Guard jpype imports in Root FastAPI route handlers
5. Update hardcoded model IDs to use configuration

### Medium (technical debt)
6. Document web app landscape (which app for what)
7. Replace `project_core/` check in demo validation
8. Add Starlette app tests
9. Wire real FallacyDetector in Flask app

### Low (nice to have)
10. Make Einstein demo optionally use real LLM calls
11. Clean up legacy test scripts with stale imports
12. Standardize API response formats
13. Move trace output directories to `logs/`

---

## Appendix: Test Coverage Matrix

| Feature | Unit Tests | Integration | Validation | Total |
|---------|-----------|-------------|------------|-------|
| Demo EPITA | 0 | 2 | 0 | **2** |
| Rhetorical Analysis | 8 | 2 | 0 | **13** |
| Sherlock-Watson | 9 | 11 | 17+ | **54+** |
| Web Applications | 5 | 2 | 0 | **8** |
| **Total** | **22** | **17** | **17+** | **~77** |
