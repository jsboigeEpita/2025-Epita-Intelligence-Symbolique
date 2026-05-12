# Reproducibility Verification Protocol

Step-by-step guide for examiners to verify the analysis system end-to-end using only public sample texts (no encrypted dataset required).

## Prerequisites

- Docker + Docker Compose
- An OpenAI API key (for LLM-backed analysis phases)
- ~10 GB disk space (Docker image with Conda + PyTorch + Java)

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/jsboigeEpita/2025-Epita-Intelligence-Symbolique.git
cd 2025-Epita-Intelligence-Symbolique

# 2. Set your API key
export OPENAI_API_KEY=sk-...

# 3. Build the Docker image (~15 min first time)
docker compose build

# 4. Run the verification protocol
docker compose run verify
```

Expected output: `=== VERIFICATION PASSED ===` with argument count >= 3 and fallacy count >= 1.

## Verification Steps

### Step 1: Build succeeds

```bash
docker compose build
```

This creates a self-contained image with:
- Ubuntu + JDK 17 (Temurin) for Tweety/JPype formal reasoning
- Miniconda with Python 3.10 and all dependencies (PyTorch, Semantic Kernel, JPype, etc.)
- The full project codebase

### Step 2: Demo scenario runs

```bash
docker compose up demo
```

Runs the **politics** scenario (`examples/scenarios/politics.txt`) through the **light** workflow (5 phases: extraction, quality, fallacy detection, NL-to-logic, synthesis).

Expected wall-clock: ~15-30 seconds (LLM API latency dependent).

### Step 3: Full verification with assertions

```bash
docker compose run verify
```

This executes `scripts/repro/run_demo.sh` which:
1. Runs the pipeline on `politics.txt`
2. Validates the output JSON structure
3. Asserts: arguments >= 3, fallacies >= 1, state snapshot non-empty

### Step 4 (Optional): Web API

```bash
docker compose up api
# Open http://localhost:8000/docs for Swagger UI
```

The FastAPI server exposes 25+ routes for agent capabilities, proposals, and analysis.

## Available Scenarios

All in `examples/scenarios/` — original pedagogical texts, not from the encrypted corpus:

| Scenario | File | Theme | Key Capabilities |
|----------|------|-------|-----------------|
| Politics | `politics.txt` | Public policy | Extraction, fallacies, governance |
| Science | `science.txt` | Climate | FOL, Dung, formal reasoning |
| Media | `media.txt` | Free speech | Quality, taxonomy, detection |
| Fact-check | `factcheck.txt` | Pensions | ATMS, JTMS, Modal logic |
| Philosophy | `philosophy.txt` | Trolley problem | Counter-args, debate, governance |

Run any scenario:
```bash
docker compose run verify bash scripts/repro/run_demo.sh examples/scenarios/science.txt light
```

## Without Docker (Local)

```bash
# Conda environment required
conda env create -f environment.yml
conda activate projet-is

# Set API key
export OPENAI_API_KEY=sk-...

# Run pipeline
python argumentation_analysis/run_orchestration.py \
    --file examples/scenarios/politics.txt \
    --workflow light

# Run verification
bash scripts/repro/run_demo.sh examples/scenarios/politics.txt light
```

## What the Verification Checks

| Check | Criterion | Why |
|-------|-----------|-----|
| Pipeline completes | `status` in output JSON | System doesn't crash on valid input |
| Arguments extracted | >= 3 | Extraction phase works |
| Fallacies detected | >= 1 | Detection phase works |
| JSON valid | `json.load()` succeeds | Output structure is correct |
| State non-empty | > 0 keys | Pipeline populated the state |

## Cost

Each demo run costs approximately **$0.01-0.05** in OpenAI API calls (light workflow, single short text).

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `OPENAI_API_KEY not set` | Export the key before `docker compose` |
| `docker build` fails on Temurin | Check internet access for Adoptium repository |
| `jpype` import error | JDK 17 must be available — check `JAVA_HOME` |
| Timeout | LLM API latency — retry or increase timeout |
| Empty results | Check API key validity and OpenAI account balance |
