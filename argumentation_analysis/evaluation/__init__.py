"""
Evaluation module for benchmarking orchestration workflows across models and documents.

Provides:
- ModelRegistry: multi-model endpoint abstraction
- BenchmarkRunner: execute workflow × model × document cells
- ResultCollector: persist and query benchmark results
- LLMJudge: evaluate analysis quality via LLM judge
- SynergyAnalyzer: workflow comparison and recommendations
- Multi-model benchmark: compare models × workflows × documents

The exports are resolved on first access (#2477). Importing a submodule runs
this ``__init__`` first, and ``model_registry`` pulls in the LLM stack (2 945
modules, measured): an eager import here made ``leak_patterns`` — which must
stay import-effect-free — cost the whole stack to every consumer reaching it
by its package path.
"""

import importlib

# export name -> submodule that defines it
_EXPORTS = {
    "ModelRegistry": "model_registry",
    "ModelConfig": "model_registry",
    "BenchmarkRunner": "benchmark_runner",
    "BenchmarkResult": "benchmark_runner",
    "ResultCollector": "result_collector",
    "LLMJudge": "judge",
}

__all__ = list(_EXPORTS)


def __getattr__(name):
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(f"{__name__}.{_EXPORTS[name]}")
    value = getattr(module, name)
    globals()[name] = value
    return value
