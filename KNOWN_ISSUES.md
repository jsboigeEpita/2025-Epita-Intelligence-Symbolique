# Known Issues — Projet Intelligence Symbolique

Last updated: 2026-03-19

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

### 7 Skipped Tests in Unit Suite
- **Breakdown** (as of 2026-03-19, 9265 passed / 7 skipped):
  - 7 phantom module tests (`test_configuration_cli.py` — `unified_production_analyzer` never existed)
- **Status**: At theoretical minimum — phantom module skips documented in #112
- **Related**: #28, #30, #94, #112

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

## Test Statistics (as of 2026-03-19)

- **Unit suite**: 9265 passed, 0 failed, 7 skipped
- **Sherlock Watson validation**: 43/43 passed
- **Black formatting**: 0 files to reformat (fully compliant)

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
