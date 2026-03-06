# Skill: Benchmark — Run Orchestration Evaluation

**Version:** 1.0.0
**Usage:** `/benchmark`

---

## Objective

Execute a benchmark evaluation cell (workflow × model × document) and return structured results. Supports single-cell runs, batch sweeps, and result comparison.

---

## Workflow

### Step 1: Parse User Intent

Determine what the user wants to benchmark:
- **Single cell**: `/benchmark light 0` → run "light" workflow on document 0
- **Model comparison**: `/benchmark light 0 --compare-models` → run across all registered models
- **Workflow comparison**: `/benchmark --all-workflows 0` → run all workflows on document 0
- **Full sweep**: `/benchmark --sweep` → run entire matrix (expensive!)
- **Show results**: `/benchmark --results` → display collected results summary

### Step 2: Load Dataset

```python
from argumentation_analysis.evaluation import BenchmarkRunner, ModelRegistry, ResultCollector

# Load from .env
from dotenv import load_dotenv
load_dotenv()

registry = ModelRegistry.from_env()

# Also register known models explicitly
from argumentation_analysis.evaluation.model_registry import ModelConfig
registry.register("qwen-local", ModelConfig(
    model_id="qwen3.5-35b-a3b",
    base_url=os.environ.get("OPENAI_BASE_URL_4", ""),
    api_key=os.environ.get("OPENAI_API_KEY_4", ""),
    display_name="Qwen 3.5 35B MoE (local)",
    is_thinking_model=True,
))

runner = BenchmarkRunner(registry)

# Load encrypted dataset
runner.load_dataset_encrypted(
    "argumentation_analysis/data/extract_sources.json.gz.enc",
    passphrase="Propaganda"
)
```

### Step 3: Execute

Use the `benchmark-worker` agent for actual execution to avoid polluting the main context:

```
Agent(subagent_type="benchmark-worker", prompt="Run workflow={wf} model={model} document={idx}")
```

### Step 4: Collect and Report

```python
collector = ResultCollector()
summary = collector.generate_summary()
```

Display results as a markdown table.

---

## Available Workflows

| Name | Phases | Description |
|------|--------|-------------|
| light | 2 | Quality only |
| standard | 4 | Quality + fallacy + counter-arg |
| full | 6 | All core capabilities |
| quality_gated | 3 | Quality check before counter-arg |
| democratech | 9 | Democratic deliberation |
| debate_tournament | 6 | Adversarial debate |
| fact_check | 6 | JTMS-based verification |
| formal_debate | 5 | ASPIC+ structured debate |
| belief_dynamics | 5 | AGM belief revision |
| argument_strength | 4 | Formal ranking |
| formal_verification | 10 | Full formal logic pipeline |

## Available Documents (encrypted dataset)

| # | Name | Chars | Language |
|---|------|-------|----------|
| 0 | Lincoln-Douglas Debate 1 | 99K | EN |
| 1 | Lincoln-Douglas Debate 2 | 102K | EN |
| 2 | Kremlin Discours 2022 | 46K | FR |
| 3 | Anthology (PDF) | 3M | DE/EN |
| 4 | Gouvernement.fr | 0 | FR |
| 5 | Assemblée Nationale | 140K | FR |
| 6 | Vie Publique | 0 | FR |
| 7 | Le Monde | 66K | FR |

Note: Documents 4 and 6 have no text and will be skipped.

## Available Models

| Name | Model | Cost | Role |
|------|-------|------|------|
| default | gpt-5-mini | ~$0.01/call | Production |
| qwen-local | qwen3.5-35b-a3b | Free | Calibration |
| openrouter | Claude Sonnet | Variable | SOTA |

---

## Tools Used

- **Agent**: benchmark-worker subagent for execution
- **Bash**: conda run for Python execution
- **Read**: Results files
- **TodoWrite**: Track sweep progress

---

## Notes

- Always start with `qwen-local` for calibration (free)
- Truncate documents to 5000 chars by default for cost control
- Use `--judge` flag to add LLM judge evaluation (costs extra tokens)
