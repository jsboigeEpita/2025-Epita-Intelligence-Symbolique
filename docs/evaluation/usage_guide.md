# Evaluation Framework Usage Guide

Comprehensive examples and workflows for using the evaluation framework.

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Benchmarking Workflows](#benchmarking-workflows)
- [Model Comparison](#model-comparison)
- [Synergy Analysis](#synergy-analysis)
- [Custom Benchmarks](#custom-benchmarks)
- [Advanced Patterns](#advanced-patterns)

---

## Installation

The evaluation framework is part of the argumentation analysis package.

```bash
# Activate conda environment
conda activate projet-is-roo-new

# Install dependencies (if needed)
pip install openai scipy numpy

# Set up API keys
cp .env.example .env
# Edit .env with your API keys
```

---

## Quick Start

### Run a Simple Benchmark

```python
import asyncio
from argumentation_analysis.evaluation.model_registry import ModelRegistry
from argumentation_analysis.evaluation.benchmark_runner import BenchmarkRunner
from argumentation_analysis.evaluation.result_collector import ResultCollector

async def main():
    # Initialize components
    registry = ModelRegistry.from_env()
    runner = BenchmarkRunner(registry)

    # Load dataset
    runner.load_dataset_unencrypted("corpus.json")

    # Run a single benchmark cell
    result = await runner.run_cell(
        workflow_name="light",
        model_name="default",
        document_index=0,
    )

    # Save result
    collector = ResultCollector()
    collector.save(result)

    print(f"Success: {result.success}")
    print(f"Duration: {result.duration_seconds:.1f}s")

asyncio.run(main())
```

### Using the CLI

```bash
# Run baseline benchmark
python -m argumentation_analysis.evaluation.run_baseline_benchmark \
    --corpus argumentation_analysis/evaluation/corpus/baseline_corpus_v1.json \
    --output results/baseline \
    --workflows light standard \
    --max-docs 5

# Generate synergy analysis
python -m argumentation_analysis.evaluation.run_synergy_analysis \
    --results-dir results/baseline \
    --format both
```

---

## Benchmarking Workflows

### Full Workflow Comparison

```python
async def compare_workflows():
    """Compare light, standard, and full workflows."""

    registry = ModelRegistry.from_env()
    runner = BenchmarkRunner(registry)
    collector = ResultCollector()

    # Load corpus
    runner.load_dataset_unencrypted("corpus.json")

    workflows = ["light", "standard", "full"]
    num_docs = len(runner.dataset)

    # Benchmark all combinations
    for workflow in workflows:
        for doc_idx in range(num_docs):
            result = await runner.run_cell(
                workflow_name=workflow,
                model_name="default",
                document_index=doc_idx,
                timeout=180.0,
            )
            collector.save(result)
            print(f"{workflow}/doc_{doc_idx}: {result.success}")

    # Generate summary
    summary = collector.generate_summary()
    print(f"\nResults:")
    for workflow in workflows:
        wf_results = collector.query(workflow_name=workflow)
        success_rate = sum(1 for r in wf_results if r["success"]) / len(wf_results)
        print(f"  {workflow}: {success_rate:.1%} success")
```

### Parallel Execution

```python
async def parallel_benchmark():
    """Run benchmarks in parallel for faster execution."""

    async def run_cell(runner, workflow, doc_idx):
        return await runner.run_cell(
            workflow_name=workflow,
            model_name="default",
            document_index=doc_idx,
            timeout=120.0,
        )

    registry = ModelRegistry.from_env()
    runner = BenchmarkRunner(registry)
    runner.load_dataset_unencrypted("corpus.json")

    # Create all tasks
    tasks = []
    workflows = ["light", "standard"]
    for workflow in workflows:
        for doc_idx in range(len(runner.dataset)):
            tasks.append(run_cell(runner, workflow, doc_idx))

    # Run in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter successful results
    successful = [r for r in results if isinstance(r, BenchmarkResult) and r.success]
    print(f"Completed {len(successful)}/{len(results)} benchmarks")
```

---

## Model Comparison

### Compare Multiple Models

```python
async def compare_models():
    """Compare the same workflow across different models."""

    registry = ModelRegistry.from_env()

    # Register additional models
    registry.register("gpt4", ModelConfig(
        model_id="gpt-4-turbo",
        base_url="https://api.openai.com/v1",
        api_key_env_var="OPENAI_API_KEY",
        display_name="GPT-4 Turbo",
        cost_per_1k_tokens=0.01,
    ))

    registry.register("claude", ModelConfig(
        model_id="claude-3-opus-20240229",
        base_url="https://api.anthropic.com/v1",
        api_key_env_var="ANTHROPIC_API_KEY",
        display_name="Claude 3 Opus",
        cost_per_1k_tokens=0.015,
    ))

    runner = BenchmarkRunner(registry)
    runner.load_dataset_unencrypted("corpus.json")

    models = ["default", "gpt4", "claude"]
    results_by_model = {model: [] for model in models}

    # Test each model on the same document
    for model in models:
        for doc_idx in range(5):  # Test on 5 documents
            result = await runner.run_cell(
                workflow_name="standard",
                model_name=model,
                document_index=doc_idx,
            )
            results_by_model[model].append(result)

    # Compare results
    for model, results in results_by_model.items():
        success_rate = sum(1 for r in results if r.success) / len(results)
        avg_duration = sum(r.duration_seconds for r in results if r.success) / sum(1 for r in results if r.success)
        print(f"{model}: {success_rate:.1%} success, {avg_duration:.1f}s avg")
```

### Cost-Aware Benchmarking

```python
async def cost_aware_benchmark():
    """Run benchmarks with cost tracking."""

    registry = ModelRegistry.from_env()
    runner = BenchmarkRunner(registry)
    runner.load_dataset_unencrypted("corpus.json")

    # Track costs
    total_cost = 0.0
    model = registry.get("default")

    # Run with cost truncation
    for doc_idx in range(len(runner.dataset)):
        result = await runner.run_cell(
            workflow_name="light",
            model_name="default",
            document_index=doc_idx,
            max_text_chars=3000,  # Limit input size
        )

        # Estimate cost (rough approximation)
        # Cost = (input_tokens + output_tokens) / 1000 * cost_per_1k
        # This is simplified - actual token counts vary
        estimated_cost = 0.001  # Placeholder
        total_cost += estimated_cost

        print(f"doc_{doc_idx}: ${estimated_cost:.4f} (total: ${total_cost:.4f})")
```

---

## Synergy Analysis

### Generate Recommendations

```python
from argumentation_analysis.evaluation.synergy_analyzer import SynergyAnalyzer

def generate_recommendations():
    """Generate workflow recommendations based on benchmark results."""

    analyzer = SynergyAnalyzer(Path("results/baseline"))

    # Load corpus metadata for difficulty categorization
    analyzer.load_corpus("corpus/baseline_corpus_v1.json")

    # Get recommendations
    recommendations = analyzer.generate_recommendations()

    print("Workflow Recommendations:\n")
    for rec in recommendations:
        print(f"Use Case: {rec.use_case}")
        print(f"  Recommended: {rec.recommended_workflow}")
        print(f"  Confidence: {rec.confidence:.0%}")
        print(f"  Reasoning: {rec.reasoning}")
        if rec.alternative_workflows:
            print(f"  Alternatives: {', '.join(rec.alternative_workflows)}")
        print()
```

### Performance Analysis

```python
def analyze_performance():
    """Detailed performance analysis by document difficulty."""

    analyzer = SynergyAnalyzer(Path("results/baseline"))
    analyzer.load_corpus()

    metrics = analyzer.analyze_workflow_performance()

    print("Performance by Document Difficulty:\n")

    for workflow, metric in metrics.items():
        print(f"\n{workflow.upper()} Workflow:")
        print(f"  Overall: {metric.success_rate:.1%} success, {metric.avg_duration:.1f}s avg")

        for difficulty in ["easy", "medium", "hard"]:
            if difficulty in metric.by_difficulty:
                stats = metric.by_difficulty[difficulty]
                print(f"  {difficulty.capitalize()}: {stats['success_rate']:.1%} success, "
                      f"{stats['avg_duration']:.1f}s avg ({stats['count']} docs)")
```

### Generate Reports

```python
def generate_all_reports(results_dir: Path):
    """Generate all available report formats."""

    analyzer = SynergyAnalyzer(results_dir)

    # JSON report (machine-readable)
    json_path = analyzer.generate_report("synergy_analysis.json")
    print(f"JSON report: {json_path}")

    # Markdown report (human-readable)
    md_path = analyzer.export_markdown_report("synergy_analysis.md")
    print(f"Markdown report: {md_path}")

    # Summary statistics
    summary = analyzer.compare_workflows()
    print(f"\nBest success rate: {summary['best_by_success_rate']['workflow']}")
    print(f"Fastest workflow: {summary['best_by_speed']['workflow']}")
```

---

## Custom Benchmarks

### Custom Dataset

```python
async def custom_dataset_benchmark():
    """Run benchmark on a custom dataset."""

    # Create custom dataset
    custom_corpus = {
        "documents": [
            {
                "id": "custom_001",
                "name": "Political Speech",
                "difficulty": "medium",
                "expected_fallacies": ["appeal_to_emotion", "straw_man"],
                "full_text": """
                My opponent wants to destroy our economy! They've proposed
                policies that will lead to chaos and ruin. We cannot let
                this happen. Vote for stability, vote for progress!
                """,
            },
            {
                "id": "custom_002",
                "name": "Product Review",
                "difficulty": "easy",
                "expected_fallacies": ["false_cause"],
                "full_text": """
                I bought this product yesterday and today I got a promotion!
                This product is clearly good luck and you should buy it too.
                """,
            },
        ]
    }

    # Save corpus
    import json
    with open("custom_corpus.json", "w") as f:
        json.dump(custom_corpus, f)

    # Run benchmark
    registry = ModelRegistry.from_env()
    runner = BenchmarkRunner(registry)
    runner.load_dataset_unencrypted("custom_corpus.json")

    for doc_idx in range(len(custom_corpus["documents"])):
        result = await runner.run_cell(
            workflow_name="standard",
            model_name="default",
            document_index=doc_idx,
        )
        print(f"{custom_corpus['documents'][doc_idx]['name']}: {result.success}")
```

### LLM Judge Evaluation

```python
async def judge_evaluation():
    """Use LLM judge to evaluate analysis quality."""

    from argumentation_analysis.evaluation.judge import LLMJudge

    registry = ModelRegistry.from_env()
    runner = BenchmarkRunner(registry)
    runner.load_dataset_unencrypted("corpus.json")

    judge = LLMJudge(model_name="default")

    # Run analysis
    result = await runner.run_cell(
        workflow_name="standard",
        model_name="default",
        document_index=0,
    )

    if result.success:
        # Get document text
        doc_text = runner.get_document_text(0)

        # Evaluate quality
        score = await judge.evaluate(
            input_text=doc_text,
            workflow_name="standard",
            analysis_results=result.state_snapshot,
            model_registry=registry,
        )

        print(f"Quality Assessment:")
        print(f"  Overall: {score.overall}/5")
        print(f"  Completeness: {score.completeness}/5")
        print(f"  Accuracy: {score.accuracy}/5")
        print(f"  Depth: {score.depth}/5")
        print(f"  Coherence: {score.coherence}/5")
        print(f"  Actionability: {score.actionability}/5")
        print(f"\nReasoning: {score.reasoning}")
```

### Fallacy Detection Benchmark

```python
async def fallacy_benchmark():
    """Run comparative fallacy detection benchmark."""

    from argumentation_analysis.evaluation.fallacy_benchmark import (
        FallacyBenchmarkRunner,
        BENCHMARK_CASES,
    )

    runner = FallacyBenchmarkRunner()

    # Run benchmark with all three modes
    report = await runner.run_benchmark(
        cases=BENCHMARK_CASES,
        modes=["free", "one_shot", "constrained"],
        concurrency=1,  # Sequential for debugging
    )

    # Print results
    print(report.summary)

    # Compare modes
    print("\nMode Comparison:")
    for mode, scores in report.mode_scores.items():
        print(f"\n{mode.upper()}:")
        print(f"  Exact PK accuracy: {scores['exact_pk_accuracy']:.1%}")
        print(f"  Family accuracy: {scores['family_accuracy']:.1%}")
        print(f"  Avg depth reached: {scores['avg_depth_reached']:.1f}")
        print(f"  Avg duration: {scores['avg_duration']:.1f}s")

    # Save report
    runner.save_report(report, "fallacy_results.json")
```

---

## Advanced Patterns

### Batch Processing with Progress Tracking

```python
import asyncio
from tqdm import tqdm

async def batch_with_progress():
    """Run benchmarks with progress tracking."""

    registry = ModelRegistry.from_env()
    runner = BenchmarkRunner(registry)
    runner.load_dataset_unencrypted("corpus.json")

    collector = ResultCollector()

    workflows = ["light", "standard", "full"]
    total = len(workflows) * len(runner.dataset)

    with tqdm(total=total, desc="Benchmarking") as pbar:
        for workflow in workflows:
            for doc_idx in range(len(runner.dataset)):
                result = await runner.run_cell(
                    workflow_name=workflow,
                    model_name="default",
                    document_index=doc_idx,
                )
                collector.save(result)
                pbar.update(1)
                pbar.set_postfix({
                    "workflow": workflow,
                    "success": result.success,
                })
```

### Result Filtering and Analysis

```python
def analyze_results():
    """Query and analyze benchmark results."""

    collector = ResultCollector(Path("results/baseline"))

    # Query specific results
    light_results = collector.query(workflow_name="light")
    standard_results = collector.query(workflow_name="standard")

    # Filter successful runs
    successful = collector.query(success_only=True)

    # Filter by document
    doc_0_results = collector.query(document_index=0)

    # Calculate statistics
    def calc_stats(results):
        durations = [r["duration_seconds"] for r in results if r["success"]]
        phases = [r["phases_completed"] for r in results if r["success"]]
        return {
            "count": len(results),
            "success_rate": sum(1 for r in results if r["success"]) / len(results),
            "avg_duration": sum(durations) / len(durations) if durations else 0,
            "avg_phases": sum(phases) / len(phases) if phases else 0,
        }

    print("Light Workflow:", calc_stats(light_results))
    print("Standard Workflow:", calc_stats(standard_results))
```

### Export for External Analysis

```python
def export_for_analysis():
    """Export results for external analysis tools."""

    collector = ResultCollector(Path("results/baseline"))

    # Export to CSV
    csv_path = collector.export_csv("benchmark_results.csv")
    print(f"CSV export: {csv_path}")

    # Export to JSON
    import json
    all_results = collector.load_all()
    with open("benchmark_results.json", "w") as f:
        json.dump(all_results, f, indent=2)

    # Export filtered results
    light_results = collector.query(workflow_name="light")
    with open("light_results.json", "w") as f:
        json.dump(light_results, f, indent=2)
```

### Error Recovery and Retry

```python
async def benchmark_with_retry(max_retries=3):
    """Run benchmarks with automatic retry on failure."""

    registry = ModelRegistry.from_env()
    runner = BenchmarkRunner(registry)
    runner.load_dataset_unencrypted("corpus.json")

    collector = ResultCollector()

    for doc_idx in range(len(runner.dataset)):
        for attempt in range(max_retries):
            result = await runner.run_cell(
                workflow_name="standard",
                model_name="default",
                document_index=doc_idx,
            )

            if result.success:
                collector.save(result)
                break
            else:
                if attempt == max_retries - 1:
                    # Final attempt failed, save the error result
                    collector.save(result)
                print(f"doc_{doc_idx} attempt {attempt + 1} failed: {result.error}")
                await asyncio.sleep(1)  # Wait before retry
```

### Custom Metrics Collection

```python
@dataclass
class CustomBenchmarkResult(BenchmarkResult):
    """Extended result with custom metrics."""

    token_count: int = 0
    estimated_cost: float = 0.0
    memory_usage_mb: float = 0.0

async def custom_metrics_benchmark():
    """Run benchmark with custom metrics collection."""

    import psutil
    import os

    registry = ModelRegistry.from_env()
    runner = BenchmarkRunner(registry)
    runner.load_dataset_unencrypted("corpus.json")

    process = psutil.Process(os.getpid())

    result = await runner.run_cell(
        workflow_name="standard",
        model_name="default",
        document_index=0,
    )

    # Add custom metrics
    custom_result = CustomBenchmarkResult(
        **asdict(result),
        token_count=len(runner.get_document_text(0)) // 4,  # Rough estimate
        estimated_cost=result.duration_seconds * 0.0001,  # Rough estimate
        memory_usage_mb=process.memory_info().rss / 1024 / 1024,
    )

    print(f"Memory usage: {custom_result.memory_usage_mb:.1f} MB")
    print(f"Estimated tokens: {custom_result.token_count}")
```

---

## Troubleshooting

### Common Issues

**Issue**: `Dataset not loaded` error
```python
# Solution: Always load dataset before running cells
runner.load_dataset_unencrypted("path/to/corpus.json")
```

**Issue**: Timeout errors
```python
# Solution: Increase timeout or reduce max_text_chars
result = await runner.run_cell(
    workflow_name="full",
    model_name="default",
    document_index=0,
    timeout=300.0,  # 5 minutes
    max_text_chars=3000,  # Reduce input size
)
```

**Issue**: API key errors
```python
# Solution: Verify environment variables
import os
print(os.environ.get("OPENAI_API_KEY"))  # Should not be None
```

**Issue**: JSON parsing errors in judge
```python
# Solution: The judge includes fallback parsing
# Check raw_response for debugging
score = await judge.evaluate(...)
print(f"Raw response: {score.raw_response}")
```
