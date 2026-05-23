# Soutenance Demo — Spectacular Analysis

Runnable artefact backing the soutenance deck (UU #673). Produces a
privacy-clean recap of the full 22-phase spectacular pipeline.

## Quick Start

```bash
# Dry-run (mock data, no API key needed — CI-safe)
python examples/02_core_system_demos/run_soutenance_demo.py --dry-run

# Live pipeline (requires OPENAI_API_KEY or OPENROUTER_API_KEY in .env)
python examples/02_core_system_demos/run_soutenance_demo.py --live

# JSON output
python examples/02_core_system_demos/run_soutenance_demo.py --dry-run --json

# Single section
python examples/02_core_system_demos/run_soutenance_demo.py --dry-run --step 9
```

## Environment

| Variable | Required | Purpose |
|----------|----------|---------|
| `OPENAI_API_KEY` | live mode | OpenAI GPT-5-mini |
| `OPENROUTER_API_KEY` | live mode (fallback) | OpenRouter proxy |
| `OPENROUTER_BASE_URL` | live mode (fallback) | `https://openrouter.ai/api/v1` |

Dry-run mode requires **no** environment variables.

## Section → Slide Mapping

| Section | Slide in deck |
|---------|---------------|
| 1 — Extraction & Quality | Phase 1-2 : Extraction & Qualite |
| 2 — Fallacy Detection | Phase 3-4 : Detection de Sophismes |
| 3 — Formal Logic | Phase 5-7 : Logique Formelle |
| 4 — Dung Framework | Phase 8 : Cadre de Dung |
| 5 — JTMS Cascades | Phase 10 : JTMS — Cascades de Retraction |
| 6 — Counter-Arguments | Phase 11 : Contre-Argumentation |
| 7 — Debate | Phase 12 : Debat |
| 8 — Governance | Phase 13 : Gouvernance Democratique |
| 9 — Convergence | Convergence Cross-Methode — 5 Signaux |
| 10 — Adjudication | Adjudication Grounded vs Claimed |
| 11 — Insight | Insight Convergent — Emergence vs 0-Shot |

## Output

Privacy-clean JSON written to `outputs/soutenance_demo_<timestamp>.json`
(gitignored). Contains opaque IDs (`arg_N`, `f_N`, `corpus_dense_A`)
only — never source text.

## Programmatic Use

```python
from run_soutenance_demo import run_demo

result = run_demo(["--dry-run"])          # dict with 11 sections
result = run_demo(["--dry-run", "--json"]) # also prints JSON
```
