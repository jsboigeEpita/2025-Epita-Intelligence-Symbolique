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

## Run

```bash
conda run -n projet-is-roo-new --no-capture-output \
  python examples/democratech_deliberation/run_democratech_demo.py

# Limit to 3 propositions, or emit compact JSON
python run_democratech_demo.py --limit 3
python run_democratech_demo.py --json
```

Requires an LLM key (`OPENAI_API_KEY` or `OPENROUTER_API_KEY` + `OPENROUTER_BASE_URL`).

## Output

A table: per proposition — `Firsthand` (decided with real agents), `Winner`
(Condorcet), `#Methods` (how many voting methods agreed), `Consensus`. A
per-phase honesty row shows which phases ran or were honestly degraded.

## Privacy HARD

Every proposition is **synthetic and domain-public** (chess club, library,
sports association, park, music school — generic participatory-budget models).
**No corpus, no real names, no `raw_text`.** Opaque IDs (`prop_A`..`prop_E`) on
all output. See `synthetic_proposals.py`.

## Anti-théâtre

The `Firsthand` column is the truth flag: a proposition that fails to decide is
reported as `no`, never fabricated. The demo reports honest-partial results
(N/5 decide) as-is.
