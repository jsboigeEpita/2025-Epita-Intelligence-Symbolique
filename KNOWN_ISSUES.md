# Known Issues — Projet Intelligence Symbolique

Last updated: 2026-06-30

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

## Resolved — Epic #317: Professor-Side Consolidation & Cleanup

- **#318**: 510 `*.log` files + untracked clutter deleted, `.gitignore` tightened
- **#319**: `FileHandler(None)` bug fixed — stray `None` file no longer created
- **#320**: 6 orphan root scripts removed (broken paths, obsolete env names, exact duplicates)
- **#321**: `src/` and `plugins/` root residues cleaned — `fallacy_families.yaml` moved to consuming plugin, orphan SK prompts archived
- **#322**: `services/web_api/` investigated and consolidated — NOT a duplicate (frontend vs backend), `interface-simple/` archived, tests moved, PNGs deleted
- **#323**: `reports/` (28 files), `validation/` (3 files) archived; `data/` fixtures relocated
- **#311**: Absorbed into Epic #317 (original repo cleanup issue)
- **Result**: Root-level tracked entries reduced from ~953 to ~50. `*.log` at root: 0.

---

## Resolved — Formal Robustness, Restitution Honesty & Infra (May–June 2026)

Architectural hardening landed across several epics. Entries below are verified against `main` (`b6dcf927`) and the merged PRs; statuses asserted are firsthand-checked, not assumed.

### Test-Infra: `scripts` Namespace Collision Aborted Full-Suite Collection
- **Identified**: 2026-06-29 | **Resolved**: 2026-06-29
- **Symptom**: `pytest tests/ --collect-only` aborted (exit 2, `Interrupted: errors during collection`) on 5 modules `ModuleNotFoundError: No module named 'scripts.*'`. Passed in isolation, failed full-suite (first-import-wins poisoning).
- **Root cause**: a phantom vestigial `tests/scripts/__init__.py` (0 importers, mass-commit `865140b7`) rebound the bare top-level `scripts` package during prepend-mode collection.
- **Fix**: PR #1294 (`fafd0bc1`) removed the phantom, added the missing `scripts/analysis/__init__.py`, deleted the dead `[tool.pytest.ini_options]` block from `pyproject.toml` (overridden by `pytest.ini` — see below), and reconciled CLAUDE.md to name `pytest.ini` the single source of truth. `pythonpath` unchanged (CI-safe).
- **Verified**: `pytest tests/ --collect-only` → exit 0, 14212 collected (firsthand 2026-06-29).
- **Status**: RESOLVED

### Determinism: 3 `.env` Files With Divergent OpenAI Keys
- **Identified**: 2026-06-29 | **Resolved**: 2026-06-29
- **Symptom**: 401 on all LLM call-sites — `find_dotenv()` + `override=False` pinned a dead key from a sub-directory `.env` (first-import-wins) over the valid root key.
- **Fix**: PR #1296 (`cf7eda6f`) — `environment_manager.py` detects the repo root via a `pyproject.toml` sentinel, loads the root `.env` with `override=True` (root always wins), and emits a masked WARNING when a secondary `.env` diverges (no secret in logs). Sub-`.env` files preserved (may serve other services — anti-pendule, no deletion).
- **Status**: RESOLVED

### Pytest Markers `debuglog` / `use_mock_numpy` Not Registered
- **Symptom**: `PytestUnknownMarkWarning` (cosmetic).
- **Fix**: both markers now declared in `pytest.ini` (`markers` section).
- **Verified**: `grep` of `pytest.ini` shows `use_mock_numpy` + `debuglog` registered (firsthand 2026-06-29).
- **Status**: RESOLVED

### Starlette Tests: Event Loop Contamination in Full Suite
- **Symptom**: 18 ERRORs in `test_interface_web_starlette.py` running the full suite; all 18 pass in isolation.
- **Root cause**: tests reused the module-level `routes` list with a shared `StaticFiles` ASGI sub-app accumulating lifecycle state across long sessions.
- **Fix**: tests build fresh API-only routes per fixture (verified: `Build fresh API routes for testing` helper present), importing only endpoint functions, excluding the StaticFiles mount. Same fix applied to `test_dashboard.py`.
- **Related**: Issue #276
- **Status**: RESOLVED *(was previously mislabeled under Active Issues)*

### Formal Robustness — Reasoners Decide-or-Fail-Loud (Epic #1191)
- **What changed**: the logic axes no longer fabricate verdicts. PL routes to PySAT and persists state; FOL is decided on Windows (EProver E2.0, with Mace4/Prover9 selectable + cross-validated) and honest-degraded on Linux; Modal parses end-to-end and decides via vendored SPASS (EML→eml adapter) instead of OOM-ing `SimpleMlReasoner`; DL/DeLP/CF2 decide or fail-loud. The invariant throughout (#1019): a formal verdict is `True`/`False` (decided) or `None` (degraded) — **never** collapsed `None`→`False`.
- **Refs**: #1191 (closed, DoD satisfied by #1291/#1292), #1234/#1239 (modal SPASS), #1243/#1245 (FOL multi-prover), #1278/#1286 (FOL fail-loud), #1279/#1288 (modal fail-loud).
- **Status**: RESOLVED (epic closed)

### Restitution Honesty & Reliability (Epic #1276 / #1290)
- **What changed**: the spectacular 3-act restitution no longer primes or fabricates. Acte II/III prompt builders carry honesty guardrails — no claim that "Tweety confirms inconsistance" unless the FOL axis actually reports it (the appendix `axe_fol` is tri-state: decided / degraded / unavailable, degraded surfaced not silently dropped); internal identifiers (`gv.winner`/`gv.method`) are described by role, never echoed raw into reader-facing prose (parity guardrail across **both** Acte II and Acte III builders — #1297 + #1298). LLM fact-extraction is strict-JSON + bounded-retry + fail-loud with explicit `max_tokens` (no silent `[]`).
- **Refs**: #1290/#1291 (extraction reliability), #1292 (FOL prose/annex coherence), #1297 (3 findings), #1298 (Acte III jargon parity). Epic #1276 at user-gate (4/4 worker readings PASSE).
- **Status**: components RESOLVED; epic closure pending user gate.

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

### Flaky Test: `test_invoke_fact_extraction_short_text` (ATT-1 residual, latent)

- **Symptom**: `tests/unit/argumentation_analysis/workflows/test_formal_verification.py::TestInvokeCallables::test_invoke_fact_extraction_short_text` asserts `claim_count == 0` on the trivial input `"Hi."`; can intermittently fail when the suite runs with an OpenAI key present.
- **Root cause**: `_invoke_fact_extraction` (`invoke_callables.py`) issues a **real LLM call** even on a 3-character input. On `"Hi."` the model can occasionally hallucinate a claim, yielding `claim_count >= 1` and failing the assertion. This is **intrinsic LLM non-determinism**, not a code bug. The no-key path (heuristic fallback) is deterministic — `"Hi."` is below the per-sentence `len > 20` threshold, so `claims == []` and the test passes cleanly.
- **Proof**: **PASSED** in the recent green run #1420 (run `28893501286`, `test_invoke_fact_extraction_short_text PASSED`). It is a *latent* floater, not a persistent CI-RED.
- **Why not fixed (anti-théâtre #1019)**: a length short-circuit in `_invoke_fact_extraction` would regress `test_track_a_extraction_reliability_1290.py` (Track A #1290), which feeds `"some text"` (9 chars) with the LLM mocked and explicitly asserts the call is made (`mock_call.call_count == 2`, `response_format` threaded) — the extraction contract is that length does **not** gate the LLM. Mocking this test would be theatre (asserting the mock returns 0 is trivial and tests nothing). Coordinated characterization: documented, non-fixable without mock.
- **Impact**: Low — green at the most recent run; part of the ATT-1 baseline (~1–2 ambient F+E floaters, count stable, non-regression).
- **Workaround**: If it flakes on a run, re-run (a fresh LLM call typically returns 0 claims on `"Hi."`). Do NOT treat it as a regression signal without confirming its isolation pass first.
- **Related**: #1355 (ATT-1), #1290 (Track A extraction reliability)

### Skipped Tests in Unit Suite
- **Breakdown** (as of 2026-05-04): 4 skips observed in CI mode. Tests requiring API keys or JVM auto-skip gracefully.
- **Status**: Stable — skip count remains low and consistent across runs
- **Related**: #28, #30, #94, #112

### gpt-5-mini Constraints
- No `temperature` parameter (hardcoded to 1.0)
- No `max_tokens` (use `max_completion_tokens`, but omit entirely via SK 1.37 to avoid empty responses)
- **Related**: #22 (closed)

### CI test suite silently skipped — green badge misleading
- **Symptom**: The `automated-tests` job is `success` (green) on every run, but runs **zero tests**. The README CI badge advertises a pipeline that does not, in fact, test.
- **Root cause**: `.github/workflows/ci.yml` gates the pytest step on `if: env.API_KEYS_CONFIGURED == 'true'`. `secrets.OPENAI_API_KEY` is not configured on this repo → the step is `[skipped]` (confirmed on runs 2026-06-21 → 2026-06-29). The conditional design is intentional since `241e3395` (2025-07-24, don't burn LLM budget on every push); the defect is the **signaling** — a green badge reads as "tests passed", not "tests skipped".
- **Impact**: Every merged PR (May–June 2026) was validated only by `mypy strict` (black/flake8 are `continue-on-error`). Latent test regressions are invisible to the gate. A local full run does report failures, but the raw count is **inflated by environment gaps** (e.g. `pyfakefs` declared in `requirements.txt` but not installed in `projet-is-roo-new`) — the true bug count is lower and must be re-measured after a full `pip install -r requirements.txt`.
- **Workaround**: Run tests locally before trusting any PR (`conda run -n projet-is-roo-new pytest <path> -q`). Only `mypy strict` is a real CI gate today.
- **Lint gate scope**: `mypy strict` — the only enforcing step (`black`/`flake8` are `continue-on-error: true`) — runs **unconditionally** (no secret gate, confirmed green on main), but is scoped to **8 core orchestration files only** (`.github/workflows/ci.yml:40-43`: `capability_registry`, `shared_state`, `workflow_dsl`, `registry_setup`, `workflows`, `invoke_callables`, `state_writers`, `factory`). The rest of `argumentation_analysis/` is **not type-checked by CI** — type regressions outside those 8 files are invisible to the gate, same as test regressions.
- **Related**: #1303

### 4 Overlapping Web Applications → 3 (partially resolved)
- `api/main.py` (FastAPI + JVM bootstrap)
- `argumentation_analysis/api/main.py` (FastAPI + JTMS plugins)
- `interface_web/app.py` (Starlette + ServiceManager + React frontend)
- ~~`services/web_api_from_libs/app.py`~~ — **ARCHIVED** (#322) — only stale .pyc files remained, no source
- **Impact**: Reduced from 4 to 3. Still confusing for new developers.
- **Related**: #33, #34

---

## Test Statistics (as of 2026-06-30)

- **Full suite**: 14212 tests collected, exit 0 (collection verified firsthand 2026-06-29, post-#1294). Earlier May-2026 baseline reported 2845+ passed / 4 skipped in CI mode (`--disable-jvm-session`); the pass count has not been re-measured at the new collection size.
- **Spectacular pipeline**: 75+ golden tests (17 phases, 0 failures on golden fixture)
- **Epic B pedagogy**: 53+ tests (HTML report, Jupyter notebook, scenario fixtures, slide deck, README quickstart)
- **Epic A hardening**: 11 property tests (ATMS/JTMS invariants, requires `hypothesis` dep), profiling tests
- **Epic C discourse mining**: 71+ tests (privacy plumbing, batch runner, pattern aggregator, report generator, enrichment workflow)
- **CI**: GREEN on main (`eb0bd4c3`) — ⚠️ but the `automated-tests` job is **silently skipped** (`OPENAI_API_KEY` secret not configured); only `mypy strict` actually runs. See *Active Issues* / #1303.
- **Conda env**: `projet-is` (primary) or `projet-is-roo-new` (latest deps)
- **Known flaky**: robustness adversarial tests (~87 tests, resource exhaustion after 1.5h runs). Starlette tests resolved.
- **Property tests**: Require `hypothesis` package (not installed by default — `pip install hypothesis`)

## Test Commands

```bash
# CI mode (fast, JVM mocked) — requires conda env activation
conda run -n projet-is --no-capture-output pytest tests/ --allow-dotenv --disable-jvm-session --ignore=tests/e2e --ignore=tests/performance --ignore=tests/property -q

# Unit only
conda run -n projet-is --no-capture-output pytest tests/unit/ --allow-dotenv --disable-jvm-session -q

# Property tests (requires hypothesis: pip install hypothesis)
conda run -n projet-is --no-capture-output pytest tests/property/ --allow-dotenv --disable-jvm-session -q

# Full JVM mode (slower, tests Java integration)
conda run -n projet-is --no-capture-output pytest tests/ --allow-dotenv --ignore=tests/e2e --ignore=tests/performance --ignore=tests/property -q
```

---

**Maintainer**: Project team | Coordinator: myia-ai-01
