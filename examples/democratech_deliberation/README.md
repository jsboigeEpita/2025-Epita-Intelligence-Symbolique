# Democratech Deliberation Demo (BO-2 #1472)

A bundle-able demo of the `democratech` workflow: runs a multi-agent citizen
deliberation E2E over a set of **synthetic, domain-public** propositions and
prints a readable per-proposition verdict (winner, voting methods, consensus).

## What it demonstrates

The `democratech` workflow decides **firsthand with real LLM agents** (no mock) —
the 3rd north-star axis of Epic #1470. Each proposition is subjected to the full
10-phase deliberation (extract → quality → counter-arguments → adversarial
debate → democratic vote), and the governance phase renders a genuine collective
choice via 12 voting methods (majority, Borda, Condorcet, approval, STV, …).

## "Lancer en 3 commandes" — DT-3 #1499 run-story

The non-specialist runs **one command** and gets a readable verdict. The
entrypoint `run_democratech_demo_one_command.py` selects the mode automatically:

1. **Backend health-check** (optional, but recommended):

    ```bash
    conda run -n projet-is-roo-new --no-capture-output \
      uvicorn api.main:app --port 8000 &
    curl -s http://localhost:8000/health
    # → {"status":"healthy",...}
    ```

2. **Run the demo (LIVE if LLM key, else SNAPSHOT replay)**:

    ```bash
    conda run -n projet-is-roo-new --no-capture-output \
      python examples/democratech_deliberation/run_democratech_demo_one_command.py
    ```

3. **Inspect the verdict** (table on stdout, or `--json` for machine-readable):

    ```bash
    python examples/democratech_deliberation/run_democratech_demo_one_command.py --json
    ```

### Two modes, picked automatically

| Mode | Trigger | Verdict marker | Speed |
|------|---------|----------------|-------|
| **LIVE** | `OPENAI_API_KEY` (or `OPENROUTER_API_KEY` + `OPENROUTER_BASE_URL`) set | `decided_firsthand=True` | ~150-200 s/proposition |
| **SNAPSHOT** | snapshot JSON found (`--snapshot <path>` > `./prerecorded_snapshot.json` > `~/.cache/democratech/prerecorded_snapshot.json`) | `decided_firsthand="PRE-RECORDED"` | <1 s |
| **Exit 2** | neither | (no verdict) | n/a |

To generate a snapshot from a successful LIVE run for later replay:

```bash
python examples/democratech_deliberation/run_democratech_demo.py --json \
  > prerecorded_snapshot.json
```

### Dashboard React (BO-2b #1493)

The web dashboard at `services/web_api/interface-web-argumentative/` consumes a
real `democratech` run via 8 wired FastAPI endpoints. To reproduce the E2E
proof offline (no LLM/JVM/browser):

```bash
python scripts/proof_bo2b_dashboard_e2e.py
python scripts/render_bo2b_dashboard_static.py
# → evaluation/results/bo2b_dashboard_proof/dashboard_snapshot.html
```

See `services/web_api/interface-web-argumentative/README.md` (section
"Dashboard de Gouvernance (BO-2b #1493)") for full endpoint map.

## Run (legacy driver)

The original BO-2 #1486 driver is still available for users who want explicit
command-line flags:

```bash
conda run -n projet-is-roo-new --no-capture-output \
  python examples/democratech_deliberation/run_democratech_demo.py

# Limit to 3 propositions, or emit compact JSON
python run_democratech_demo.py --limit 3
python run_democratech_demo.py --json
```

Requires an LLM key (`OPENAI_API_KEY` or `OPENROUTER_API_KEY` + `OPENROUTER_BASE_URL`).

## Output

A table: per proposition — `Firsthand` (decided LIVE / PRE-RECORDED / no),
`Winner` (Condorcet), `#Methods` (how many voting methods agreed), `Consensus`.
A per-phase honesty row shows which phases ran or were honestly degraded.

## Privacy HARD

Every proposition is **synthetic and domain-public** (chess club, library,
sports association, park, music school — generic participatory-budget models).
**No corpus, no real names, no `raw_text`.** Opaque IDs (`prop_A`..`prop_E`) on
all output. See `synthetic_proposals.py`.

## Anti-théâtre

The `Firsthand` column is the truth flag: a proposition that fails to decide is
reported as `no`, never fabricated. The demo reports honest-partial results
(N/5 decide) as-is. SNAPSHOT mode replays a previously-recorded verdict marked
`PRE-RECORDED` (never `True`, never silently confused with LIVE). The entrypoint
exits with code 2 if neither an LLM key nor a snapshot is available — never
fabricates a verdict.
