# Known Issues — Projet Intelligence Symbolique

Last updated: 2026-03-29

---

## Resolved Issues

### PyTorch WinError 182 on Windows
- **Identified**: 2025-10-16 | **Resolved**: 2025-10-22
- **Cause**: Incompatible PyTorch CUDA build on CPU-only machine
- **Fix**: Install PyTorch CPU-only: `pip install torch --index-url https://download.pytorch.org/whl/cpu`
- **Status**: RESOLVED — conftest.py now imports torch before jpype to prevent DLL load order crashes

### Test Ordering Contamination (test_auto_env)
- **Identified**: 2026-03-13 | **Resolved**: 2026-03-14
- **Cause**: conftest.py sets `E2E_TESTING_MODE=1` globally, causing `ensure_env()` bypass in full suite
- **Fix**: Context manager pattern with explicit `os.environ.pop()` (commit 84d65f35)
- **Status**: RESOLVED

### Git Status Clutter (libs/ directories)
- **Identified**: 2026-03-14 | **Resolved**: 2026-03-14
- **Cause**: libs/portable_octave/, libs/tweety/, node directories not in .gitignore
- **Fix**: Updated .gitignore (PR #104)
- **Status**: RESOLVED

### Stale JTMS Imports
- **Identified**: 2026-03-28 | **Resolved**: 2026-03-28
- **Cause**: `state_manager_plugin.py` imported JTMS symbols from stale paths that diverged from canonical `services/jtms/` location
- **Fix**: PR #262 updated imports in `argumentation_analysis/core/state_manager_plugin.py` to canonical `argumentation_analysis/services/jtms/` paths
- **Related**: Issue #263
- **Status**: RESOLVED

### ConflictResolver Import Path
- **Identified**: 2026-03-28 | **Resolved**: 2026-03-28
- **Cause**: `ConflictResolver` was only accessible via `agents/jtms_communication_hub.py`, an indirect and fragile import path
- **Fix**: PR #262 extracted `ConflictResolver` to `argumentation_analysis/services/jtms/conflict_resolution.py` as the canonical location; all callers updated
- **Status**: RESOLVED

### Async Mock Failures in test_fallacy_workflow_calibration.py
- **Identified**: 2026-03-28 | **Resolved**: 2026-03-28
- **Cause**: `MagicMock` used for `get_chat_message_content` (singular) which is awaited — raises `TypeError: object MagicMock can't be used in 'await' expression`
- **Fix**: PR #270 (#269) replaced with context-aware async mocks simulating the full 2-phase hierarchical workflow
- **Status**: RESOLVED

### Bootstrap Tests: _pre_init_safety_checks on Windows (7 tests)
- **Identified**: 2026-03-29 | **Resolved**: 2026-03-29
- **Cause**: `TestInitializeProjectEnvironment` tests passed fake paths (`/tmp/test`, `/my/project`) to `initialize_project_environment()`, but `_pre_init_safety_checks()` validates real filesystem paths — all fail on Windows
- **Fix**: Commit `88af060f` added autouse fixture to mock `_pre_init_safety_checks` → 24/24 bootstrap tests pass
- **Status**: RESOLVED

### MCP Stdio Tests: stdin/stdout Swap + pytest Capture (8 tests)
- **Identified**: 2026-03-29 | **Resolved**: 2026-03-29
- **Cause**: (1) Test mocks passed to wrong parameter (`stdout=` for send tests, `stdin=` for receive tests), (2) `StdioTransport()` without args accesses `sys.stdin.buffer` which pytest captures, (3) `MagicMock()` has spurious `drain` attribute triggering wrong async path
- **Fix**: Commit `88af060f` — corrected param names, patched `sys` module, used `MagicMock(spec=["write", "flush"])` → 17/17 stdio tests pass
- **Status**: RESOLVED

### Dead E2E Tests: Logic Graph Component (5 tests removed/updated)
- **Identified**: 2026-03-28 | **Resolved**: 2026-03-28
- **Cause**: Logic Graph frontend component removed during Flask→FastAPI refactor (Oct 2025). No `/api/logic/*` endpoints in FastAPI, no `[data-testid="logic-graph-*"]` in dashboard.
- **Fix**: PR #271 deleted `test_logic_graph.py` (3 dead tests), removed `test_logic_graph_fallacy_integration` from integration workflows, updated skip reasons on 2 remaining API tests
- **Related**: Issue #264
- **Status**: RESOLVED

---

## Active Issues

### JVM "Access Violation" Warning Under pytest (cosmetic)
- **Symptom**: `Windows fatal exception: access violation` printed to stderr during `jpype.startJVM()`
- **Impact**: None — JVM starts successfully despite the warning (SEH exception is caught by Windows)
- **Workaround**: None needed. Use `--disable-jvm-session` in CI to skip JVM entirely.
- **Related**: #28

### Flaky Test: `test_backend_lifecycle`
- **Symptom**: Fails intermittently in full suite due to test ordering/state pollution
- **Impact**: Low — passes in isolation, only fails when run after certain other tests
- **Workaround**: Run in isolation if investigating: `pytest tests/integration/web/test_fastapi_gpt4o_authentique.py::test_backend_lifecycle -v`

### Flaky Tests: `test_workflow_robustness.py` adversarial tests (~80-90 tests)

- **Symptom**: ~87 tests fail when running the full `tests/unit/argumentation_analysis/orchestration/` suite (1h30-1h40m run). Affected tests: `debate_tournament-*`, `test_format_string_attack`, `test_state_not_corrupted_by_massive_input`, `test_concurrent_different_workflows`.
- **Root cause**: Resource exhaustion after prolonged test execution. Each adversarial test is heavy (~40-60s individually). After 1.5h of continuous runs, async event loops or OS handles degrade.
- **Proof**: Every failing test passes cleanly in isolation (1 passed, ~38s).
- **Impact**: Low — individual tests are correct; only the marathon bulk run degrades.
- **Workaround**: Run orchestration tests in smaller batches (e.g., by class), not as a full suite. Do NOT use this failure count as a regression signal — always verify individual test pass before investigating.

### Skipped Tests in Unit Suite
- **Breakdown** (as of 2026-03-28, 10085 collected):
  - Phantom module skips from `test_configuration_cli.py` (`unified_production_analyzer`) appear resolved — 0 skips observed in that file
  - Remaining skips are test-body skips (conditional on platform/env), not module-level skips
- **Status**: Monitoring — exact runtime skip count pending full suite run
- **Related**: #28, #30, #94, #112

### Starlette Tests: Event Loop Contamination in Full Suite
- **Symptom**: 18 ERRORs in `test_interface_web_starlette.py` when running full suite, but all 18 pass in isolation
- **Impact**: Low — cosmetic failures only in marathon suite runs
- **Root cause**: Suspected async event loop pollution from prior tests
- **Workaround**: Run in isolation: `pytest tests/unit/test_interface_web_starlette.py -v`
- **Related**: Issue #276

### Pytest Markers Not Registered (cosmetic warnings)
- **Symptom**: `PytestUnknownMarkWarning` for `debuglog`, `use_mock_numpy` markers
- **Impact**: None — tests run correctly despite warnings
- **Fix Needed**: Add custom markers to `pytest.ini`

### gpt-5-mini Constraints
- No `temperature` parameter (hardcoded to 1.0)
- No `max_tokens` (use `max_completion_tokens`, but omit entirely via SK 1.37 to avoid empty responses)
- **Related**: #22 (closed)

### 4 Overlapping Web Applications
- `api/main.py` (FastAPI + JVM bootstrap)
- `argumentation_analysis/api/main.py` (FastAPI + JTMS plugins)
- `services/web_api_from_libs/app.py` (Flask + React)
- `interface_web/app.py` (Starlette + ServiceManager)
- **Impact**: Confusing for new developers. Different API formats and ports.
- **Related**: #33, #34

---

## Test Statistics (as of 2026-03-29)

- **Unit suite**: 10085+ collected; 0 known regressions (15 fixes in commit `88af060f`)
- **Epic #208 tests**: 158+ passed (conv_orch, groupchat, plugin, trace, quality, NL-logic, JTMS, benchmark, CamemBERT, integration)
- **Orchestration modes**: 2 active — pipeline (default), conversational (legacy removed round 79)
- **Sherlock Watson validation**: 43/43 passed
- **CI**: GREEN on main (`88af060f`)
- **Known flaky in full suite**: Starlette (18 ERRORs, pass in isolation — #276), robustness adversarial (~87 tests, resource exhaustion)

## Test Commands

```bash
# CI mode (fast, JVM mocked)
pytest tests/ --allow-dotenv --disable-jvm-session --ignore=tests/e2e --ignore=tests/performance -q

# Unit only
pytest tests/unit/ --allow-dotenv --disable-jvm-session -q

# Full JVM mode (slower, tests Java integration)
pytest tests/ --allow-dotenv --ignore=tests/e2e --ignore=tests/performance -q
```

---

**Maintainer**: Project team
