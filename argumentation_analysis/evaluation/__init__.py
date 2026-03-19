"""
Evaluation module for benchmarking orchestration workflows across models and documents.

Provides:
- ModelRegistry: multi-model endpoint abstraction
- BenchmarkRunner: execute workflow × model × document cells
- ResultCollector: persist and query benchmark results
- LLMJudge: evaluate analysis quality via LLM judge
- SynergyAnalyzer: workflow comparison and recommendations
- Multi-model benchmark: compare models × workflows × documents
"""

from argumentation_analysis.evaluation.model_registry import ModelRegistry, ModelConfig
from argumentation_analysis.evaluation.benchmark_runner import (
    BenchmarkRunner,
    BenchmarkResult,
)
from argumentation_analysis.evaluation.result_collector import ResultCollector
from argumentation_analysis.evaluation.judge import LLMJudge

__all__ = [
    "ModelRegistry",
    "ModelConfig",
    "BenchmarkRunner",
    "BenchmarkResult",
    "ResultCollector",
    "LLMJudge",
]
