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

Recording a new cassette (manual workflow, NOT part of the default tests):

```bash
# 1. Run the test with `record` mode into a clean DB:
LLM_CACHE_MODE=record LLM_CACHE_DIR=.cache/llm_record \
  conda run -n projet-is-roo-new pytest \
    tests/unit/argumentation_analysis/plugins/test_narrate_convergence.py::TestNarrateConvergenceIntegration

# 2. Export the DB to JSON, audits privacy:
python scripts/cassettes/export.py .cache/llm_record tests/fixtures/llm_cassettes

# 3. Commit the new <sha256>.json files (a PR diff shows them).
```

Replaying (the default — CI lane and reproducibility):

```bash
# 1. Import JSON fixtures into a fresh DB:
python scripts/cassettes/import.py tests/fixtures/llm_cassettes .cache/llm_replay --purge

# 2. Run the test in `replay` mode. A miss raises `LLMCacheMiss`:
LLM_CACHE_MODE=replay LLM_CACHE_DIR=.cache/llm_replay \
  conda run -n projet-is-roo-new pytest \
    tests/unit/argumentation_analysis/plugins/test_narrate_convergence.py::TestNarrateConvergenceIntegration
```

The pytest test `tests/unit/.../test_cassette_round_trip.py` runs the
full record → export → import → replay loop and asserts `live == 0` in
replay (the anti-#1019 metric).

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

If a legitimate-cassette use case conflicts with the privacy contract,
do NOT bypass with `--allow-unsafe` — open an issue and discuss
documented-bounded leakage first.
