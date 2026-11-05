# Replay band — pre-flight on a seat

The replay band (`.github/workflows/requires_api_band.yml`, job `replay-band`) replays the
non-light `requires_api` tests against committed cassettes (`tests/fixtures/llm_cassettes/`)
with `live=0`. Until #3411, a worker could not reproduce it locally: a seat's `.env` silently
made every cache key differ from the recorder's, and the resulting misses looked exactly like
cassette drift.

## Why a seat sees misses that CI does not

The cache keys hash the model id verbatim (`compute_raw_cache_key`, `compute_cache_key`).
A `.env` that sets `OPENROUTER_API_KEY` + `OPENROUTER_BASE_URL` takes the `use_openrouter`
branch (`llm_service.py`), which rewrites the model to its provider slug:
`gpt-5-mini` → `openai/gpt-5.6-luna`. CI has no `.env`, resolves the bare `gpt-5.6-luna`,
and therefore hashes a different key for the same request. Measured (#3411): one request
hashes to `b7a81cc8…` on the seat (absent from the store) and `91192b98…` with the prefix
stripped (present).

## The recipe (measured)

```bash
# 1. Import the committed cassettes into a replay store (once per store).
python scripts/cassettes/import.py tests/fixtures/llm_cassettes .cache/llm_replay_band --purge --verify-run

# 2. Replay the band's population with the CI route — the two empty vars are the point:
OPENROUTER_API_KEY="" OPENROUTER_BASE_URL="" \
OPENAI_API_KEY=replay-band-no-live-anti-1019 \
LLM_CACHE_MODE=replay LLM_CACHE_DIR=.cache/llm_replay_band \
REPLAY_GATE=1 REPLAY_STATS_OUT=replay_stats.json \
  python -m pytest <the band's argv, marker -m "requires_api and not llm_light"> \
    -p scripts.cassettes.replay_stats_plugin -q
```

Measured on `fix/penalty-register-order-3394`: 52 passed, `hit=1856` — the same count as the
CI job — and `miss_replay=7`. Without the two empty vars the same run is 23 failed / 28
passed, `hit=30`, `miss_replay=32`, which is not a measurement of the cassettes.

## Reading the counters

- `hit` should match the CI job's count for the same branch. A large gap means the route is
  wrong (see above), not that the cassettes are stale.
- `miss_replay: 0` — nothing drifted.
- **One or two keys** — a prompt changed. The PR that changes a prompt is the one that
  invalidates a cassette; the re-record (`record-llm-cassettes.yml`, manual, paid) rides the
  same PR. The miss message now names the model it hashed (#3411).
- **A fixed family of keys, identical run after run** — a seat `.env` gap (e.g. the
  SELF_HOSTED keys missing on some seats, R1288). It is not the branch; the CI job is the
  instrument that decides.
