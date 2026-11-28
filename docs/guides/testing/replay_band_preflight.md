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

Since #3679 the band is on another route: the named Anthropic route
(`ANTHROPIC_CHAT_MODEL_ID=claude-haiku-5-5`), where the model id hashed is that one, verbatim.
The OpenRouter case above still holds for a seat that declares it — and the `ANTHROPIC_*`
variables below are now the ones that select the band's route.

A second gap adds calls instead of re-keying them. A `.env` that sets
`SELF_HOSTED_LLM_ENDPOINT` (the first of the two phases below also needs
`SELF_HOSTED_LLM_MODEL`) switches on the self-hosted phases, `_invoke_camembert_fallacy` and
`_invoke_local_llm` (`orchestration/invoke_callables.py`), which report "not configured"
without it. Those phases make SK calls CI never makes, so no cassette holds their keys.
Measured (#3690) on `main` `df82a458e`: six lookups in two tests, and `miss_replay=6` with
`hit=1702` — the CI count — so the `hit` check alone cannot see this gap.

## The recipe (measured)

```bash
# 1. Import the committed cassettes into a replay store (once per store).
python scripts/cassettes/import.py tests/fixtures/llm_cassettes .cache/llm_replay_band --purge --verify-run

# 2. Replay the band's population with the CI route — the four empty vars are the point:
OPENROUTER_API_KEY="" OPENROUTER_BASE_URL="" SELF_HOSTED_LLM_ENDPOINT="" ANTHROPIC_BASE_URL="" \
OPENAI_API_KEY=replay-band-no-live-anti-1019 \
ANTHROPIC_API_KEY=replay-band-no-live-anti-1019 ANTHROPIC_CHAT_MODEL_ID=claude-haiku-5-5 \
LLM_CACHE_MODE=replay LLM_CACHE_DIR=.cache/llm_replay_band \
REPLAY_GATE=1 REPLAY_STATS_OUT=replay_stats.json \
  python -m pytest <the band's argv, marker -m "requires_api and not llm_light"> \
    -p scripts.cassettes.replay_stats_plugin -q
```

**Write the dummy `ANTHROPIC_API_KEY` explicitly.** A seat's `.env` may hold a real
`ANTHROPIC_API_KEY`; a variable set in the shell wins over it, because the `.env` load only
fills what is absent (#3116). With the real key and the model id, the route the process
resolves is a billable one. Replay mode still never calls on a miss (`LLMCacheMiss`), but
nothing else should run under that pair. Never print the key to check which one is in play:
`tests/unit/test_record_lane_route_parity_3679.py` reads the route from the two workflow
files and holds the recorder and the replayer to one route.

**Empty `ANTHROPIC_BASE_URL` too.** A Claude Code seat exports it (the harness proxy).
`llm_service` reads it as the named route's base URL, and `endpoint_compat` classifies the
provider from that URL: a non-Anthropic base sends `response_format {"type": "json_object"}`,
and those calls then enter the raw key. It is in the process environment, not in `.env`, so
emptying the file does not drop it. Measured on `3ff8640e0` (the population CI's band run
45517998474 replays), one line apart:

| the run | counters | pytest |
| --- | --- | --- |
| without `ANTHROPIC_BASE_URL=""` | `hit=43`, `miss_replay=20` on 8 distinct keys | 19 failed, 33 passed |
| with it | `hit=1745`, `miss_replay=0`, `miss_record=0`, `live=0` | 52 passed, 2 skipped, 1 xfailed |

The second row is CI's row. A seat that inherits the variable reads those misses as a family
(20 lookups on 8 distinct keys), not as one drifted prompt.

Read the same way on a second seat, `myia-ai-01` (27/11, the coordinator's reading), dropping
the variable from the environment instead of emptying it (`env -u ANTHROPIC_BASE_URL`): 19
failed and 20 entries missing with it inherited, 52 passed and none missing with it dropped.
Two seats, two ways of removing one variable, one family.

Measured on `fix/penalty-register-order-3394`, before #3679 moved the band to the Anthropic
route: 52 passed, `hit=1856` — the same count as the CI job — and `miss_replay=7`. Without
the two empty OpenRouter vars the same run is 23 failed / 28 passed, `hit=30`, `miss_replay=32`,
which is not a measurement of the cassettes. The counts of the current cassettes are those of
the CI job on the same commit.

Measured again on `main` `df82a458e` with `SELF_HOSTED_LLM_ENDPOINT=""` among the empties and a
store holding every committed key (#3690): 51 passed, `hit=1702`, `miss_replay=0`. The same seat
without that empty reads `miss_replay=6`.

**Step 1's `--verify-run` reads the record run from the GitHub API.** CI has `GITHUB_TOKEN` and
`GITHUB_REPOSITORY`; a bare seat has neither, and the provenance gate refuses there — the plain
import does not need them. On a seat, export both before step 1:

```bash
export GH_TOKEN="$(gh auth token)"
export GITHUB_REPOSITORY=jsboigeEpita/2025-Epita-Intelligence-Symbolique
```

Measured on `myia-po-2023`: without them the gate stops at `requires GITHUB_TOKEN/GH_TOKEN and
GITHUB_REPOSITORY`; with them, `run 45513278355 exported 587 cassettes; declared non-job delta 0
(sk_patches: 0); disk carries 587`.

The token is not the whole story. A Windows seat whose **user intermediate store** has cached the
Let's Encrypt intermediates `YR1`/`YR2` used to refuse here — `ssl.create_default_context()`
loads that store as trust anchors, the chain then needed `ISRG Root YR`, and neither the conda
bundle nor any Windows store carries it. The gate no longer reads that store: the run's log is
fetched through a context anchored on the certifi bundle (`scripts/cassettes/import.py`,
`_run_log_ssl_context`, #3716), verification on, no fallback. A refusal there is still a
provenance verdict like any other (`RunLogError`, rc 3), never a silent skip: a seat that drops
`--verify-run` has not taken step 1. The plain import still runs `verify_manifest` — the manifest
to the directory (count and digest) and to the recording environment — and cannot do what the
flag adds, resolving the record run id against the run's own log.

The recipe as it stands above, followed as written on `myia-po-2023` against `main` `b612ab24e`
(27/11): step 1 in its literal form, with whichever account `gh` holds active, exits 0 and writes
587; step 2 reads `52 passed, 2 skipped, 1 xfailed`; the workflow's own gate
(`scripts.cassettes.replay_gate_check`) reads `live=0 hit=1745 miss_record=0 miss_replay=0`. That
is CI's row on the same commit.

## Reading the counters

- `hit` should match the CI job's count for the same branch. A large gap means the route is
  wrong (see above), not that the cassettes are stale.
- `miss_replay: 0` — nothing drifted.
- **One or two keys** — a prompt changed. The PR that changes a prompt is the one that
  invalidates a cassette; the re-record (`record-llm-cassettes.yml`, manual, paid) rides the
  same PR. The miss message now names the model it hashed (#3411).
- **A fixed family of keys, identical run after run** — a seat gap: a `.env` entry the recipe
  does not drop (e.g. the SELF_HOSTED keys missing on some seats, R1288;
  `SELF_HOSTED_LLM_ENDPOINT` set, #3690) or a process variable it does not empty
  (`ANTHROPIC_BASE_URL`, above — its family is the raw-path calls, whose settings carry
  `response_format`). It is not the branch; the CI job is the instrument that decides. A family
  that survives the recipe above names a gap this page does not carry yet.
