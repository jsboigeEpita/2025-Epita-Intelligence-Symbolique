# Soutenance Reproduction Guide

End-to-end guide for reproducing the SCDA (Spectacular Conversational Deep Analysis)
pipeline results on the 3 reference corpora. Follow these steps to run the demo
during soutenance.

## Prerequisites

### 1. Environment

```bash
# Clone and enter the repository
git clone https://github.com/jsboigeEpita/2025-Epita-Intelligence-Symbolique.git
cd 2025-Epita-Intelligence-Symbolique

# Activate Conda environment
conda activate projet-is    # or projet-is-roo-new
```

### 2. API Keys

Copy `.env.example` to `.env` and fill in:

```ini
OPENAI_API_KEY=sk-...           # Required: OpenAI API access
OPENAI_CHAT_MODEL_ID=gpt-5-mini # Required: pipeline standard model
TEXT_CONFIG_PASSPHRASE=...      # Required: dataset decryption
GH_TOKEN=...                    # Optional: GitHub CLI access
```

### 3. Verify Setup

```bash
python -c "from argumentation_analysis.core.io_manager import load_extract_definitions; print('Imports OK')"
```

## Running the Demos

Each corpus demo is a one-shot script that runs the full SCDA pipeline
(~20 min wall-clock) and produces a state JSON + summary.

### Corpus A (EN dense ~58K)

```bash
python examples/soutenance/run_corpus_a.py
```

### Corpus B (DE dense ~50K)

```bash
python examples/soutenance/run_corpus_b.py
```

### Corpus C (EN dense ~46K)

```bash
python examples/soutenance/run_corpus_c.py
```

## Expected Outputs

### Tolerance Bands

Metrics are validated against these bands (derived from Sprint 6 baseline):

| Metric | Corpus A | Corpus B | Corpus C |
|--------|----------|----------|----------|
| Arguments found | 20 ± 2 | 17 ± 2 | 10 ± 2 |
| Fallacies found | 13 ± 3 | 17 ± 3 | 14 ± 3 |
| Formal categories | ≥ 3 | ≥ 3 | ≥ 3 |

### Output Files

Each run produces files under `outputs/soutenance_demo/<corpus_label>/`:

| File | Description |
|------|-------------|
| `state.json` | Full pipeline state snapshot |
| `summary.json` | Headline metrics (JSON) |
| `deep_synthesis_report.md` | Markdown analysis report |

### Console Output

Each script prints a formatted summary:

```
============================================================
 SCDA Soutenance Demo — corpus_dense_A (EN dense (~58K))
============================================================
  Duration         : 1234.5s (20.6 min)
  Arguments found  : 20
  Fallacies found  : 13
  Formal categories: 7
    - dung_frameworks
    - aspic_analyses
    - ...
  JTMS beliefs     : 94
  Counter-args     : 8
============================================================

  All metrics within tolerance bands.
```

## Demo Flow (Soutenance)

Recommended order for presentation:

1. **Corpus A** — Start the script, explain pipeline phases while it runs
2. **Show results** — While waiting, show a previous run's outputs in `outputs/`
3. **Cross-corpus comparison** — Reference `docs/reports/SCDA_CROSS_CORPUS_PARALLELS_2026-05.md`
4. **Corpus B or C** — If time permits, show the tolerance bands differ per corpus

## Architecture

The demo scripts invoke the SCDA pipeline via:

```
run_corpus_X.py
  └── run_conversational_analysis(text, spectacular=True)
        ├── Extraction phase (ExtractAgent)
        ├── Detection phase (InformalAgent + FallacyWorkflowPlugin)
        │     ├── Per-family 7-family systematic traversal
        │     ├── German keyword bridge (DE→EN→taxonomy PK)
        │     └── Parent harness auto-fire (>5000 chars)
        ├── Formal Analysis phase (FOLAgent, PLAgent, ModalAgent)
        ├── Counter-Argument phase (CounterArgumentAgent)
        ├── Re-Analysis phase (with Dung/ASPIC/BR)
        └── Deep Synthesis phase (SynthesisAgent)
```

## Troubleshooting

### "TEXT_CONFIG_PASSPHRASE not set"

The `.env` file is missing or the passphrase variable is not set. Copy from
`.env.example` and fill in the value.

### "OPENAI_API_KEY not set"

The OpenAI API key is required for LLM calls. Ensure it's in `.env`.

### Import errors

```bash
# Verify conda environment is active
conda info --envs

# Verify project is on sys.path
python -c "import argumentation_analysis; print(argumentation_analysis.__file__)"
```

### JVM / JPype errors

The JVM initializes automatically on first logic agent call. If it fails,
formal agents use Python fallbacks. The pipeline still completes.

### Tolerance warnings

Tolerance warnings are informational — they indicate the run deviated from
the baseline but do not mean the pipeline failed. LLM outputs are
non-deterministic; small variations are expected.

## Privacy

- Scripts load the encrypted dataset in-memory via `load_extract_definitions`
- No plaintext content is written to disk (state JSON uses opaque IDs)
- `outputs/` directory is gitignored
- Corpus labels (`corpus_dense_A/B/C`) are opaque identifiers
