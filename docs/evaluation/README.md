# Evaluation Framework

The evaluation framework provides a comprehensive system for benchmarking, analyzing, and comparing the performance of argumentation analysis workflows across different LLM models and document types.

## Overview

The framework supports:

- **Multi-model benchmarking**: Compare workflows across different LLM providers and models
- **Workflow analysis**: Evaluate light, standard, and full analysis workflows
- **Result collection**: Append-only JSONL storage with query capabilities
- **LLM Judge evaluation**: Quality assessment using structured rubrics
- **Synergy analysis**: Identify optimal workflow configurations for specific use cases
- **Fallacy detection benchmarks**: Comparative analysis of detection modes

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Evaluation Framework                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────┐ │
│  │ ModelRegistry    │───▶│ BenchmarkRunner  │───▶│ ResultCollector│ │
│  │ - ModelConfig    │    │ - run_cell()     │    │ - save()      │ │
│  │ - activate()     │    │ - load_dataset() │    │ - query()     │ │
│  └──────────────────┘    └──────────────────┘    └──────────────┘ │
│           │                       │                     │           │
│           │                       ▼                     ▼           │
│           │              ┌──────────────────┐  ┌──────────────┐    │
│           └─────────────▶│   LLMJudge       │  │ SynergyAnalyzer│ │
│                          │ - evaluate()     │  │ - compare()  │    │
│                          │ - score results  │  │ - recommend()│    │
│                          └──────────────────┘  └──────────────┘    │
│                                                                       │
├─────────────────────────────────────────────────────────────────────┤
│  Benchmark Runners                                                   │
├─────────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────┐  ┌─────────────────────────────────┐  │
│  │ run_baseline_benchmark  │  │ FallacyBenchmarkRunner          │  │
│  │ - Multi-model tests     │  │ - Mode comparison (free/oneshot)│  │
│  │ - Workflow comparison   │  │ - Taxonomy-based evaluation     │  │
│  └────────────────────────┘  └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## Key Components

### Model Registry

Manages LLM model configurations and provides model switching capabilities:

- **ModelConfig**: Configuration dataclass for model settings
- **ModelRegistry**: Central registry for model management
- Supports multiple providers (OpenAI, OpenRouter, local endpoints)
- Environment variable switching for cost-effective testing

### Benchmark Runner

Executes individual benchmark cells (workflow × model × document):

- **BenchmarkRunner**: Main execution engine
- **BenchmarkResult**: Result dataclass with metrics
- Supports encrypted/unencrypted datasets
- Timeout handling and error recovery
- Phase completion tracking

### Result Collector

Persistent storage and query system for benchmark results:

- **ResultCollector**: Append-only JSONL storage
- Query by workflow, model, document
- Summary statistics generation
- CSV export for external analysis

### LLM Judge

Quality evaluation using structured rubrics:

- **LLMJudge**: Evaluates analysis results
- **JudgeScore**: Structured scoring across 5 dimensions
- Smart result summarization for context budget
- JSON parsing with markdown fallback

### Synergy Analyzer

Analyzes workflow performance to generate recommendations:

- **SynergyAnalyzer**: Comparative analysis engine
- **WorkflowMetrics**: Performance aggregation
- **SynergyRecommendation**: Use case-based recommendations
- Document difficulty categorization
- Report generation (JSON/Markdown)

### Fallacy Benchmark

Comparative fallacy detection evaluation:

- **FallacyBenchmarkRunner**: Three-mode comparison
  - Mode A: Free detection (no taxonomy)
  - Mode B: One-shot (full taxonomy)
  - Mode C: Constrained (hierarchical navigation)
- **DetectionResult**: Detailed scoring per attempt
- Precision metrics (PK match, family match, depth)

## Quick Start

### Basic Benchmark

```python
from argumentation_analysis.evaluation.model_registry import ModelRegistry
from argumentation_analysis.evaluation.benchmark_runner import BenchmarkRunner
from argumentation_analysis.evaluation.result_collector import ResultCollector

# Initialize
registry = ModelRegistry.from_env()
runner = BenchmarkRunner(registry)
runner.load_dataset_unencrypted("path/to/corpus.json")

# Run benchmark
result = await runner.run_cell(
    workflow_name="light",
    model_name="default",
    document_index=0,
    timeout=120.0,
)

# Save results
collector = ResultCollector()
collector.save(result)
```

### Synergy Analysis

```python
from argumentation_analysis.evaluation.synergy_analyzer import SynergyAnalyzer

analyzer = SynergyAnalyzer()

# Generate comparison report
comparison = analyzer.compare_workflows()

# Get recommendations
recommendations = analyzer.generate_recommendations()
for rec in recommendations:
    print(f"{rec.use_case}: {rec.recommended_workflow}")

# Export reports
analyzer.generate_report("output.json")
analyzer.export_markdown_report("output.md")
```

### LLM Judge Evaluation

```python
from argumentation_analysis.evaluation.judge import LLMJudge

judge = LLMJudge(model_name="default")
score = await judge.evaluate(
    input_text="Argument text to analyze",
    workflow_name="standard",
    analysis_results=state_snapshot,
    model_registry=registry,
)

print(f"Overall quality: {score.overall}/5")
print(f"Reasoning: {score.reasoning}")
```

## CLI Tools

### Baseline Benchmark

```bash
python -m argumentation_analysis.evaluation.run_baseline_benchmark \
    --corpus argumentation_analysis/evaluation/corpus/baseline_corpus_v1.json \
    --output argumentation_analysis/evaluation/results/baseline \
    --workflows light standard \
    --max-docs 10 \
    --verbose
```

### Synergy Analysis

```bash
python -m argumentation_analysis.evaluation.run_synergy_analysis \
    --results-dir argumentation_analysis/evaluation/results \
    --format both \
    --output argumentation_analysis/evaluation/reports
```

## Workflow Definitions

| Workflow | Phases | Use Case |
|----------|--------|----------|
| **light** | extract, quality, counter | Quick assessment |
| **standard** | extract, quality, counter, jtms, governance, debate | Standard analysis |
| **full** | transcribe, extract, quality, neural_fallacy, counter, jtms, governance, debate, index | Complete analysis |

## Documentation

- [API Reference](api_reference.md) - Detailed API documentation
- [Usage Guide](usage_guide.md) - Comprehensive usage examples
- [Configuration Guide](configuration.md) - Model and environment setup

## Output Structure

```
argumentation_analysis/evaluation/results/
├── benchmark_results.jsonl      # Raw benchmark results
├── benchmark_results.csv        # CSV export for analysis
├── benchmark_summary.json       # Aggregated statistics
├── judge_evaluation.json        # LLM judge scores
├── synergy_analysis_report.json # Workflow comparison
└── synergy_analysis_report.md   # Human-readable report
```

## Version

**Current Version**: 1.0.0

## License

EPITA Argumentation Analysis Project - Internal Use
