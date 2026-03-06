# Agent: Benchmark Worker

Execute a single benchmark cell (workflow × model × document) and return structured results.

## Instructions

You are a benchmark execution agent. Your job is to:
1. Parse the requested workflow, model, and document index from the prompt
2. Execute the benchmark using the evaluation module
3. Return a structured result

## Execution

Write a temporary Python script and run it with conda:

```python
import asyncio, json, os, sys
from dotenv import load_dotenv
load_dotenv()

from argumentation_analysis.evaluation.model_registry import ModelRegistry, ModelConfig
from argumentation_analysis.evaluation.benchmark_runner import BenchmarkRunner
from argumentation_analysis.evaluation.result_collector import ResultCollector

# Build registry from .env
registry = ModelRegistry.from_env()

# Register qwen-local explicitly
api_key_4 = os.environ.get("OPENAI_API_KEY_4", "")
base_url_4 = os.environ.get("OPENAI_BASE_URL_4", "")
if api_key_4 and base_url_4:
    registry.register("qwen-local", ModelConfig(
        model_id="qwen3.5-35b-a3b",
        base_url=base_url_4,
        api_key=api_key_4,
        display_name="Qwen 3.5 35B MoE (local)",
        is_thinking_model=True,
    ))

runner = BenchmarkRunner(registry)
runner.load_dataset_encrypted(
    "argumentation_analysis/data/extract_sources.json.gz.enc",
    passphrase="Propaganda"
)

async def main():
    result = await runner.run_cell(
        workflow_name=WORKFLOW,
        model_name=MODEL,
        document_index=DOC_INDEX,
        max_text_chars=MAX_CHARS,
        timeout=TIMEOUT,
    )
    collector = ResultCollector()
    collector.save(result)
    print(json.dumps({
        "success": result.success,
        "workflow": result.workflow_name,
        "model": result.model_name,
        "document": result.document_name,
        "duration": round(result.duration_seconds, 2),
        "phases_completed": result.phases_completed,
        "phases_total": result.phases_total,
        "error": result.error,
    }, indent=2))

asyncio.run(main())
```

Replace WORKFLOW, MODEL, DOC_INDEX, MAX_CHARS, TIMEOUT with the requested values.

## Default Parameters
- max_text_chars: 5000
- timeout: 120 seconds

## Output Format

Return a JSON summary with success/failure, timing, and phase completion counts.
Always save results via ResultCollector before returning.
