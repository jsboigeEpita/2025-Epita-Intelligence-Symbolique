# LLM Cassettes — tracktes fixtures for offline replay (#1603)

This directory holds a **deterministic, audited subset** of LLM responses
used by `tests/unit/.../test_cassette_round_trip.py` to prove the
record/export/import/replay loop end-to-end.

## Why

- `argumentation_analysis.services.llm_cache` supports `off` / `record` /
  `replay` modes. `record` writes to a runtime diskcache DB under
  `LLM_CACHE_DIR` (default `.cache/llm_responses`, gitignored). `replay`
  reads from this DB and raises `LLMCacheMiss` on a miss — never falls back
  silently to a live call.
- The runtime DB is opaque (SQLite, binary). This directory holds a
  diff-friendly export: one `<sha256>.json` per cassette, each containing
  `{"key": sha256, "value": <serialized LLM response>}`.
- Each cassette was recorded against a **synthetic test fixture** (no
  plaintext dataset content). Privacy audit at export time is blocking —
  see `scripts/cassettes/privacy.py` for the forbidden-key list.

## Layout

Each file: `<sha256>.json`. The sha256 is the cache key computed by
`llm_cache.compute_cache_key` over (model_id, messages, temperature, tools)
— deterministic across runs.

## Usage

Recording a new cassette (manual workflow, NOT part of the default tests).

**The procedure differs by path, and picking the wrong one silently records
nothing** — see "What a record run actually captures" below for why. Until
#1950 this section named a single command that could not work for the SK path.

### SK path (`narrate_convergence` and friends)

Use the dedicated script. It is the only supported way: an SK-path test run
under pytest is mocked and records nothing, so no `pytest` invocation can
refresh these cassettes.

```bash
conda run -n projet-is-roo-new --no-capture-output \
  python scripts/cassettes/record_sk_cassette.py
```

It records with `force_authentic=True` into a scratch DB, then exports through
`export.py` (blocking privacy audit) and prints the new `<sha256>.json`. Then
delete the file it supersedes and commit.

⚠ Makes a real LLM call (order of $0.0005). Run it only when
`TestCommittedCassettesStillReplay::test_replay_path_uses_cache` reddens with
the DRIFT message — that red means the prompt moved, not that the code broke.

### Raw path (pipeline consumers: extract / governance / quality / fallacy /
counter-arg)

These are never mocked, so a plain record run over the pipeline lane does
capture them:

```bash
# 1. Run the pipeline tests with `record` mode into a clean DB:
LLM_CACHE_MODE=record LLM_CACHE_DIR=.cache/llm_record \
  conda run -n projet-is-roo-new pytest <pipeline test path>

# 2. Export the DB to JSON, audits privacy:
python scripts/cassettes/export.py .cache/llm_record tests/fixtures/llm_cassettes

# 3. Commit the new <sha256>.json files (a PR diff shows them).
```

⚠ #1603: the broad record pass is **not** hermetic yet (it produced 5 leaks and
3 false positives). Do not re-record the raw-path bands before that is fixed.

Replaying (the default — CI lane and reproducibility):

```bash
# 1. Import JSON fixtures into a fresh DB:
python scripts/cassettes/import.py tests/fixtures/llm_cassettes .cache/llm_replay --purge

# 2. Run the test in `replay` mode. A miss raises `LLMCacheMiss`:
LLM_CACHE_MODE=replay LLM_CACHE_DIR=.cache/llm_replay \
  conda run -n projet-is-roo-new pytest \
    tests/unit/argumentation_analysis/plugins/test_narrate_convergence.py::TestNarrateConvergenceIntegration
```

`tests/unit/.../test_cassette_round_trip.py` holds **two properties with
opposite failure regimes** (#1950). It records nothing — no test does.

| Class | Property | On red |
|---|---|---|
| `TestExportImportScriptsRoundTrip` | the export/import scripts are lossless | **fix the scripts.** Built on synthetic `(key, value)` pairs, so a contract change cannot redden it |
| `TestCommittedCassettesStillReplay` | committed cassettes still match the production prompt | **re-record** (see SK path above). Not a code defect |

The anti-#1019 metric (`live == 0` in replay) lives in the second. Note that
`narrate_convergence` swallows a replay miss and falls back to its template
narrative, so drift is visible **only** in the `hit` counter — never in the
returned string, and never in `live` alone.

## What a record run actually captures (measured #1603 R826)

`create_llm_service` mocks on `PYTEST_CURRENT_TEST in os.environ`
(`core/llm_service.py:115`) — every SK-service call in a pytest run is
mocked (fast, deterministic) and records NOTHING, unless the call site
passes `force_authentic=True`. The direct path
(`_guarded_chat_completion` → `cached_raw_chat_completion`,
`orchestration/invoke_callables.py:439`) is NEVER mocked: with a key
present it calls the real API through the raw cache layer and records
cassettes. So a record run over the unit lane captures the raw-path
consumers (extract / governance / quality / fallacy / counter-arg phases,
i.e. the pipeline tests) — the SK-path tests (e.g. the narrate integration
test) stay mocked and record nothing, which is correct: they run mocked in
pytest anyway and need no cassette to pass in replay.

Raw-path cassette values are the OpenAI `ChatCompletion.model_dump()` dict
and carry a `usage` block (prompt/completion tokens) — the record job's
cost artifact (`scripts/cassettes/cost_report.py`) sums it. SK-path values
are role/content lists without usage.

## Privacy contract

Cassettes committed here MUST be:

- Synthetic (test fixture inputs only — no real corpus).
- Free of the forbidden keys listed in `scripts/cassettes/privacy.py`
  (`raw_text`, `full_text`, `full_text_segment`, `raw_text_snippet`,
  `passphrase`).
- Free of source-name hints (politically sensitive authors / historical
  figures) and politically sensitive date stamps (1933–2026).
- Audited by `scripts/cassettes/privacy.py` at export. The audit is
  blocking — a violation raises `PrivacyViolation` and the cassette is
  refused.
- The audit exempts response-metadata keys (`model`, `id`, `created`,
  `object`, `service_tier`, `system_fingerprint`, `finish_reason`,
  `index`, `role`) from the year/name heuristics: the versioned model id
  (`gpt-5-mini-2025-08-07`) would otherwise trip the historical-date rule
  on every raw-path cassette. Forbidden-key checks still apply to dict
  keys everywhere.

If a legitimate-cassette use case conflicts with the privacy contract,
do NOT bypass with `--allow-unsafe` — open an issue and discuss
documented-bounded leakage first.
