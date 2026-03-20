# Evaluation Framework API Reference

Complete API documentation for all evaluation framework components.

## Table of Contents

- [Model Registry](#model-registry)
- [Benchmark Runner](#benchmark-runner)
- [Result Collector](#result-collector)
- [LLM Judge](#llm-judge)
- [Synergy Analyzer](#synergy-analyzer)
- [Fallacy Benchmark](#fallacy-benchmark)

---

## Model Registry

### `ModelConfig`

```python
@dataclass
class ModelConfig:
    """Configuration for an LLM model."""

    model_id: str                    # Model identifier (e.g., "gpt-5-mini")
    base_url: str                    # API endpoint URL
    api_key_env_var: str             # Environment variable name for API key
    display_name: str                # Human-readable name
    cost_per_1k_tokens: float        # Cost per 1000 tokens (USD)
    is_thinking_model: bool = False  # Whether model supports thinking
    max_tokens: int = 128000         # Maximum context window
```

**Example:**
```python
config = ModelConfig(
    model_id="gpt-5-mini",
    base_url="https://api.openai.com/v1",
    api_key_env_var="OPENAI_API_KEY",
    display_name="GPT-5 Mini",
    cost_per_1k_tokens=0.0001,
    is_thinking_model=False,
    max_tokens=128000,
)
```

### `ModelRegistry`

```python
class ModelRegistry:
    """Registry for managing LLM model configurations."""

    def __init__(self, default_config: ModelConfig, models: Dict[str, ModelConfig])
    @classmethod
    def from_env(cls) -> "ModelRegistry"
    def register(self, name: str, config: ModelConfig) -> None
    def get(self, name: str) -> ModelConfig
    def list_models(self) -> List[str]
    def activate(self, name: str) -> None
    def save_env(self) -> Dict[str, str]
    def restore_env(self, saved: Dict[str, str]) -> None
```

**Methods:**

- **`from_env()`**: Creates registry from environment variables
- **`register(name, config)`**: Add a model configuration
- **`get(name)`**: Retrieve model configuration
- **`activate(name)`**: Switch active model via environment variables
- **`save_env()`**: Save current environment state
- **`restore_env(saved)`**: Restore previous environment state

**Example:**
```python
registry = ModelRegistry.from_env()

# Register custom model
registry.register("local", ModelConfig(
    model_id="llama-3-70b",
    base_url="http://localhost:8000/v1",
    api_key_env_var="LOCAL_API_KEY",
    display_name="Llama 3 70B (Local)",
    cost_per_1k_tokens=0.0,
))

# Switch to local model
registry.activate("local")

# Run inference...

# Restore previous model
saved = registry.save_env()
registry.activate("default")
# ... do work ...
registry.restore_env(saved)
```

---

## Benchmark Runner

### `BenchmarkResult`

```python
@dataclass
class BenchmarkResult:
    """Result of a single benchmark cell execution."""

    workflow_name: str
    model_name: str
    document_index: int
    document_name: str
    success: bool
    duration_seconds: float
    phases_completed: int
    phases_total: int
    phases_failed: int
    phases_skipped: int
    error: Optional[str] = None
    state_snapshot: Optional[Dict[str, Any]] = None
    phase_results: Optional[Dict[str, Any]] = None
    timestamp: str = ""  # Auto-generated
```

### `BenchmarkRunner`

```python
class BenchmarkRunner:
    """Execute benchmark cells (workflow × model × document)."""

    def __init__(self, model_registry: ModelRegistry, dataset_path: Optional[str] = None)

    # Dataset loading
    def load_dataset_unencrypted(self, path: str) -> List[Dict[str, Any]]
    def load_dataset_encrypted(self, path: str, passphrase: str) -> List[Dict[str, Any]]

    # Dataset access
    @property
    def dataset(self) -> List[Dict[str, Any]]
    def get_document_text(self, index: int) -> str
    def get_document_name(self, index: int) -> str

    # Benchmark execution
    async def run_cell(
        self,
        workflow_name: str,
        model_name: str,
        document_index: int,
        max_text_chars: int = 5000,
        timeout: float = 120.0,
    ) -> BenchmarkResult
```

**Dataset Format:**
```json
{
  "documents": [
    {
      "id": "doc_001",
      "name": "Sample Document",
      "difficulty": "medium",
      "expected_fallacies": ["ad_hominem"],
      "full_text": "Complete document text...",
      "extracts": [
        {"extract_text": "Extract 1..."},
        {"extract_text": "Extract 2..."}
      ]
    }
  ]
}
```

**Example:**
```python
runner = BenchmarkRunner(model_registry)

# Load unencrypted dataset
runner.load_dataset_unencrypted("corpus.json")

# Or load encrypted dataset
runner.load_dataset_encrypted("corpus.enc", "passphrase")

# Run benchmark cell
result = await runner.run_cell(
    workflow_name="light",
    model_name="default",
    document_index=0,
    max_text_chars=5000,  # Truncate for cost control
    timeout=120.0,        # Max execution time
)

print(f"Success: {result.success}")
print(f"Duration: {result.duration_seconds:.1f}s")
print(f"Phases: {result.phases_completed}/{result.phases_total}")
```

---

## Result Collector

### `ResultCollector`

```python
class ResultCollector:
    """Append-only benchmark result store with query capabilities."""

    DEFAULT_RESULTS_DIR = Path("argumentation_analysis/evaluation/results")

    def __init__(self, results_dir: Optional[Path] = None)

    # Storage
    def save(self, result: BenchmarkResult) -> None
    def save_batch(self, results: List[BenchmarkResult]) -> None

    # Retrieval
    def load_all(self) -> List[Dict[str, Any]]

    # Querying
    def query(
        self,
        workflow_name: Optional[str] = None,
        model_name: Optional[str] = None,
        document_index: Optional[int] = None,
        success_only: bool = False,
    ) -> List[Dict[str, Any]]

    # Analysis
    def generate_summary(self) -> Dict[str, Any]
    def export_csv(self, output_path: Optional[Path] = None) -> Path
```

**Summary Format:**
```python
{
    "total": 100,                    # Total results
    "successes": 95,                 # Successful runs
    "failures": 5,                   # Failed runs
    "by_model": {                    # Per-model stats
        "gpt-5-mini": {
            "total": 50,
            "success": 48,
            "avg_duration": 15.3,
            "avg_phases_completed": 4.2
        }
    },
    "by_workflow": {                 # Per-workflow stats
        "light": {
            "total": 33,
            "success": 32,
            "avg_duration": 8.5
        }
    },
    "generated_at": "2025-01-15T10:30:00"
}
```

**Example:**
```python
collector = ResultCollector(Path("results"))

# Save single result
collector.save(result)

# Save batch
collector.save_batch(results)

# Query results
light_results = collector.query(workflow_name="light")
successful = collector.query(success_only=True)

# Generate summary
summary = collector.generate_summary()
print(f"Success rate: {summary['successes']}/{summary['total']}")

# Export for analysis
csv_path = collector.export_csv("analysis.csv")
```

---

## LLM Judge

### `JudgeScore`

```python
@dataclass
class JudgeScore:
    """Score from LLM judge evaluation."""

    completeness: float    # 1-5: Coverage of key arguments
    accuracy: float        # 1-5: Correctness of analysis
    depth: float           # 1-5: Depth beyond surface-level
    coherence: float       # 1-5: Internal consistency
    actionability: float   # 1-5: Usability of results
    overall: float         # 1-5: Overall quality
    reasoning: str         # Explanation of scores
    judge_model: str       # Model used for evaluation
    raw_response: str = "" # Raw LLM response
```

### `LLMJudge`

```python
class LLMJudge:
    """Evaluate analysis quality using an LLM judge."""

    JUDGE_SYSTEM_PROMPT = "..."  # Structured rubric
    JUDGE_USER_TEMPLATE = "..."  # Input template

    def __init__(self, model_name: str = "default")

    async def evaluate(
        self,
        input_text: str,
        workflow_name: str,
        analysis_results: Dict[str, Any],
        model_registry: Optional[Any] = None,
    ) -> JudgeScore

    @staticmethod
    def _prepare_results_for_judge(results: Dict[str, Any]) -> Dict[str, Any]
    def _parse_json_response(self, raw: str) -> Dict[str, Any]
```

**Evaluation Criteria:**

| Criterion | Description |
|-----------|-------------|
| **Completeness** | Does the analysis cover all key arguments and claims? |
| **Accuracy** | Are the identified arguments, fallacies, and relationships correct? |
| **Depth** | Does the analysis go beyond surface-level observations? |
| **Coherence** | Are the results internally consistent and well-structured? |
| **Actionability** | Could someone use these results to understand the argumentation? |

**Example:**
```python
judge = LLMJudge(model_name="default")

score = await judge.evaluate(
    input_text="The original text that was analyzed",
    workflow_name="standard",
    analysis_results=state_snapshot,
    model_registry=registry,
)

print(f"Overall: {score.overall}/5")
print(f"Completeness: {score.completeness}/5")
print(f"Accuracy: {score.accuracy}/5")
print(f"Depth: {score.depth}/5")
print(f"Coherence: {score.coherence}/5")
print(f"Actionability: {score.actionability}/5")
print(f"\nReasoning: {score.reasoning}")
```

---

## Synergy Analyzer

### `WorkflowMetrics`

```python
@dataclass
class WorkflowMetrics:
    """Performance metrics for a workflow."""

    workflow_name: str
    total_runs: int = 0
    success_rate: float = 0.0
    avg_duration: float = 0.0
    avg_phases_completed: float = 0.0
    avg_phases_total: float = 0.0
    completion_ratio: float = 0.0  # phases_completed / phases_total
    by_difficulty: Dict[str, Dict[str, float]] = field(default_factory=dict)
    by_fallacy_category: Dict[str, Dict[str, float]] = field(default_factory=dict)
```

### `SynergyRecommendation`

```python
@dataclass
class SynergyRecommendation:
    """Recommendation for optimal workflow configuration."""

    use_case: str                          # Use case identifier
    recommended_workflow: str              # Recommended workflow
    confidence: float                      # 0.0 - 1.0
    reasoning: str                         # Explanation
    alternative_workflows: List[str] = field(default_factory=list)
    expected_metrics: Dict[str, float] = field(default_factory=dict)
```

### `SynergyAnalyzer`

```python
class SynergyAnalyzer:
    """Analyze workflow and agent combination performance from benchmark results."""

    WORKFLOW_PHASES = {
        "light": ["extract", "quality", "counter"],
        "standard": ["extract", "quality", "counter", "jtms", "governance", "debate"],
        "full": ["transcribe", "extract", "quality", "neural_fallacy", "counter",
                 "jtms", "governance", "debate", "index"],
    }

    DIFFICULTY_LEVELS = ["easy", "medium", "hard"]

    def __init__(self, results_dir: Optional[Path] = None)

    # Corpus metadata
    def load_corpus(self, corpus_path: Optional[Path] = None) -> Dict
    def get_document_metadata(self, document_index: int) -> Dict[str, Any]

    # Analysis
    def analyze_workflow_performance(self) -> Dict[str, WorkflowMetrics]
    def compare_workflows(self) -> Dict[str, Any]
    def generate_recommendations(self) -> List[SynergyRecommendation]

    # Reports
    def generate_report(self, output_path: Optional[Path] = None) -> Path
    def export_markdown_report(self, output_path: Optional[Path] = None) -> Path
```

**Comparison Report Format:**
```python
{
    "workflows": {
        "light": {
            "total_runs": 33,
            "success_rate": 0.97,
            "avg_duration": 8.5,
            "completion_ratio": 0.95,
            "by_difficulty": {
                "easy": {"count": 10, "success_rate": 1.0, "avg_duration": 5.2},
                "medium": {"count": 15, "success_rate": 0.95, "avg_duration": 8.1},
                "hard": {"count": 8, "success_rate": 0.90, "avg_duration": 12.3}
            }
        }
    },
    "best_by_success_rate": {"workflow": "standard", "rate": 0.95},
    "best_by_speed": {"workflow": "light", "avg_duration": 8.5},
    "best_by_completion": {"workflow": "full", "ratio": 0.92},
    "summary": {
        "avg_success_rate": 0.93,
        "avg_duration": 15.2,
        "total_workflows_analyzed": 3
    }
}
```

**Example:**
```python
analyzer = SynergyAnalyzer(Path("results"))

# Load corpus for metadata
analyzer.load_corpus("corpus/baseline_corpus_v1.json")

# Analyze performance
metrics = analyzer.analyze_workflow_performance()
for workflow, metric in metrics.items():
    print(f"{workflow}: {metric.success_rate:.1%} success, {metric.avg_duration:.1f}s avg")

# Compare workflows
comparison = analyzer.compare_workflows()
print(f"Best success rate: {comparison['best_by_success_rate']['workflow']}")

# Get recommendations
recommendations = analyzer.generate_recommendations()
for rec in recommendations:
    print(f"\n{rec.use_case}: {rec.recommended_workflow} ({rec.confidence:.0%})")
    print(f"  {rec.reasoning}")

# Generate reports
analyzer.generate_report("synergy.json")
analyzer.export_markdown_report("synergy.md")
```

---

## Fallacy Benchmark

### `DetectionResult`

```python
@dataclass
class DetectionResult:
    """Result from a single fallacy detection attempt."""

    case_id: str
    mode: str                     # "free", "one_shot", "constrained"
    detected_name: str = ""
    detected_pk: str = ""
    detected_family: str = ""
    confidence: float = 0.0
    justification: str = ""
    exact_pk_match: bool = False
    family_match: bool = False
    name_similarity: float = 0.0   # Jaccard similarity on name tokens
    depth_reached: int = 0
    duration_seconds: float = 0.0
    error: str = ""
    raw_response: str = ""
```

### `BenchmarkReport`

```python
@dataclass
class BenchmarkReport:
    """Aggregate fallacy benchmark results."""

    results: List[DetectionResult] = field(default_factory=list)
    mode_scores: Dict[str, Dict[str, float]] = field(default_factory=dict)
    summary: str = ""

    def compute_scores(self)
```

### `FallacyBenchmarkRunner`

```python
class FallacyBenchmarkRunner:
    """Run comparative fallacy detection benchmark."""

    BENCHMARK_CASES = [...]  # 10 predefined test cases

    def __init__(self, taxonomy_path: Optional[str] = None)

    # Detection modes
    async def run_mode_a_free(self, text: str) -> Dict[str, Any]
    async def run_mode_b_one_shot(self, text: str) -> Dict[str, Any]
    async def run_mode_c_constrained(self, text: str) -> Dict[str, Any]

    # Benchmark execution
    async def run_benchmark(
        self,
        cases: Optional[List[dict]] = None,
        modes: Optional[List[str]] = None,
        concurrency: int = 1,
    ) -> BenchmarkReport

    # Utilities
    def save_report(self, report: BenchmarkReport, path: str)
```

**Detection Modes:**

| Mode | Description | Context |
|------|-------------|---------|
| **Free** | Zero taxonomy context | Pure LLM detection |
| **One-shot** | Full taxonomy available | LLM chooses from complete list |
| **Constrained** | Hierarchical navigation | Iterative deepening via plugin |

**Scoring Metrics:**

- **Exact PK accuracy**: Exact taxonomy node match
- **Family accuracy**: Correct family-level match
- **Name similarity**: Jaccard similarity on name tokens
- **Depth reached**: Taxonomy depth of detected node
- **Confidence**: LLM confidence score

**Example:**
```python
runner = FallacyBenchmarkRunner()

# Run full benchmark
report = await runner.run_benchmark(
    cases=BENCHMARK_CASES,
    modes=["free", "one_shot", "constrained"],
    concurrency=3,  # Parallel execution
)

# View scores
for mode, scores in report.mode_scores.items():
    print(f"\n{mode}:")
    print(f"  Exact PK accuracy: {scores['exact_pk_accuracy']:.1%}")
    print(f"  Family accuracy: {scores['family_accuracy']:.1%}")
    print(f"  Avg depth: {scores['avg_depth_reached']:.1f}")

# Save report
runner.save_report(report, "fallacy_benchmark.json")
```

---

## Type Hints

All components use standard Python type hints:

```python
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
```

## Error Handling

All async methods handle exceptions gracefully:

```python
try:
    result = await runner.run_cell(...)
except Exception as e:
    # Returns BenchmarkResult with success=False and error message
    logger.error(f"Benchmark failed: {e}")
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | API key for OpenAI-compatible endpoints | - |
| `OPENAI_BASE_URL` | Base URL for API requests | `https://api.openai.com/v1` |
| `OPENAI_CHAT_MODEL_ID` | Model identifier | `gpt-5-mini` |
