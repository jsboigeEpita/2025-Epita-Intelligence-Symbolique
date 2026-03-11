# Known Issues — Projet Intelligence Symbolique

Last updated: 2026-02-24

---

## Resolved Issues

### PyTorch WinError 182 on Windows
- **Identified**: 2025-10-16 | **Resolved**: 2025-10-22
- **Cause**: Incompatible PyTorch CUDA build on CPU-only machine
- **Fix**: Install PyTorch CPU-only: `pip install torch --index-url https://download.pytorch.org/whl/cpu`
- **Status**: RESOLVED — conftest.py now imports torch before jpype to prevent DLL load order crashes

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

### 67 Skipped Tests in CI Mode
- **Breakdown**:
  - ~44 JVM/jpype-dependent (expected with `--disable-jvm-session`) → #28
  - ~7 phantom modules (deleted scripts, never-implemented modules)
  - ~8 e2e/Playwright (require running backend on :8095 + `RUN_E2E_TESTS=1`)
  - ~3 LLM flakiness (dynamic skip on API variability)
  - ~3 misc (MCP SDK API change, conditional skips)
- **Status**: At theoretical minimum — all remaining skips are by-design or need infrastructure
- **Related**: #28, #30

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

## Test Commands

```bash
# CI mode (fast, JVM mocked)
pytest tests/ --allow-dotenv --disable-jvm-session --ignore=tests/e2e --ignore=tests/performance -q

# Full JVM mode (slower, tests Java integration)
pytest tests/ --allow-dotenv --ignore=tests/e2e --ignore=tests/performance -q
```

---

**Maintainer**: Project team
