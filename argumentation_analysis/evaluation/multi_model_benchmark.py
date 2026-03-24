"""
Multi-model × multi-workflow benchmark runner.

Executes the full benchmark matrix: models × workflows × documents,
produces comparison reports, and identifies optimal model/workflow
combinations per use case.

Usage:
    python -m argumentation_analysis.evaluation.multi_model_benchmark \
        --corpus argumentation_analysis/evaluation/corpus/baseline_corpus_v1.json \
        --output results/multi_model \
        --workflows light standard formal_debate \
        --models default openrouter \
        --max-docs 5 \
        --timeout 180
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from argumentation_analysis.evaluation.model_registry import ModelRegistry, ModelConfig
from argumentation_analysis.evaluation.benchmark_runner import (
    BenchmarkRunner,
    BenchmarkResult,
)
from argumentation_analysis.evaluation.result_collector import ResultCollector

logger = logging.getLogger("evaluation.multi_model_benchmark")


@dataclass
class ModelWorkflowScore:
    """Aggregated score for a (model, workflow) pair."""

    model_name: str
    workflow_name: str
    total_runs: int = 0
    successes: int = 0
    failures: int = 0
    avg_duration: float = 0.0
    avg_phases_completed: float = 0.0
    avg_completion_ratio: float = 0.0
    total_cost_estimate: float = 0.0

    @property
    def success_rate(self) -> float:
        return self.successes / self.total_runs if self.total_runs > 0 else 0.0


@dataclass
class ComparisonReport:
    """Full comparison report across models and workflows."""

    timestamp: str = ""
    models: List[str] = field(default_factory=list)
    workflows: List[str] = field(default_factory=list)
    num_documents: int = 0
    total_cells: int = 0
    total_duration_seconds: float = 0.0
    scores: List[ModelWorkflowScore] = field(default_factory=list)
    best_by_success: Optional[Dict[str, str]] = None
    best_by_speed: Optional[Dict[str, str]] = None
    best_overall: Optional[Dict[str, str]] = None
    model_rankings: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    workflow_rankings: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


def compute_scores(
    results: List[BenchmarkResult],
) -> List[ModelWorkflowScore]:
    """Aggregate BenchmarkResults into per-(model, workflow) scores."""
    buckets: Dict[Tuple[str, str], List[BenchmarkResult]] = {}
    for r in results:
        key = (r.model_name, r.workflow_name)
        buckets.setdefault(key, []).append(r)

    scores = []
    for (model, workflow), group in buckets.items():
        total = len(group)
        successes = sum(1 for r in group if r.success)
        durations = [r.duration_seconds for r in group if r.success]
        phases = [r.phases_completed for r in group if r.success]
        ratios = [
            r.phases_completed / r.phases_total
            for r in group
            if r.success and r.phases_total > 0
        ]

        scores.append(
            ModelWorkflowScore(
                model_name=model,
                workflow_name=workflow,
                total_runs=total,
                successes=successes,
                failures=total - successes,
                avg_duration=sum(durations) / len(durations) if durations else 0.0,
                avg_phases_completed=(sum(phases) / len(phases) if phases else 0.0),
                avg_completion_ratio=(sum(ratios) / len(ratios) if ratios else 0.0),
            )
        )
    return scores


def rank_models(scores: List[ModelWorkflowScore]) -> Dict[str, List[Dict[str, Any]]]:
    """Rank models for each workflow by composite score."""
    by_workflow: Dict[str, List[ModelWorkflowScore]] = {}
    for s in scores:
        by_workflow.setdefault(s.workflow_name, []).append(s)

    rankings = {}
    for wf, wf_scores in by_workflow.items():
        ranked = sorted(
            wf_scores,
            key=lambda s: (s.success_rate, s.avg_completion_ratio, -s.avg_duration),
            reverse=True,
        )
        rankings[wf] = [
            {
                "rank": i + 1,
                "model": s.model_name,
                "success_rate": round(s.success_rate, 3),
                "avg_duration": round(s.avg_duration, 2),
                "completion_ratio": round(s.avg_completion_ratio, 3),
            }
            for i, s in enumerate(ranked)
        ]
    return rankings


def rank_workflows(
    scores: List[ModelWorkflowScore],
) -> Dict[str, List[Dict[str, Any]]]:
    """Rank workflows for each model by composite score."""
    by_model: Dict[str, List[ModelWorkflowScore]] = {}
    for s in scores:
        by_model.setdefault(s.model_name, []).append(s)

    rankings = {}
    for model, model_scores in by_model.items():
        ranked = sorted(
            model_scores,
            key=lambda s: (s.success_rate, s.avg_completion_ratio, -s.avg_duration),
            reverse=True,
        )
        rankings[model] = [
            {
                "rank": i + 1,
                "workflow": s.workflow_name,
                "success_rate": round(s.success_rate, 3),
                "avg_duration": round(s.avg_duration, 2),
                "completion_ratio": round(s.avg_completion_ratio, 3),
            }
            for i, s in enumerate(ranked)
        ]
    return rankings


def find_best(scores: List[ModelWorkflowScore]) -> Dict[str, Dict[str, str]]:
    """Find best model+workflow combo by different criteria."""
    if not scores:
        return {}
    successful = [s for s in scores if s.successes > 0]
    if not successful:
        return {"note": "No successful runs"}

    best_success = max(successful, key=lambda s: s.success_rate)
    best_speed = min(successful, key=lambda s: s.avg_duration)
    # Composite: 0.5 * success_rate + 0.3 * completion_ratio + 0.2 * (1 / (1 + avg_duration))
    best_overall = max(
        successful,
        key=lambda s: (
            0.5 * s.success_rate
            + 0.3 * s.avg_completion_ratio
            + 0.2 * (1.0 / (1.0 + s.avg_duration))
        ),
    )

    return {
        "best_by_success": {
            "model": best_success.model_name,
            "workflow": best_success.workflow_name,
            "success_rate": round(best_success.success_rate, 3),
        },
        "best_by_speed": {
            "model": best_speed.model_name,
            "workflow": best_speed.workflow_name,
            "avg_duration": round(best_speed.avg_duration, 2),
        },
        "best_overall": {
            "model": best_overall.model_name,
            "workflow": best_overall.workflow_name,
            "composite_score": round(
                0.5 * best_overall.success_rate
                + 0.3 * best_overall.avg_completion_ratio
                + 0.2 * (1.0 / (1.0 + best_overall.avg_duration)),
                3,
            ),
        },
    }


def generate_markdown_report(report: ComparisonReport) -> str:
    """Generate a human-readable markdown comparison report."""
    lines = [
        "# Multi-Model Benchmark Report",
        "",
        f"**Generated**: {report.timestamp}",
        f"**Models**: {', '.join(report.models)}",
        f"**Workflows**: {', '.join(report.workflows)}",
        f"**Documents**: {report.num_documents}",
        f"**Total cells**: {report.total_cells}",
        f"**Total duration**: {report.total_duration_seconds:.1f}s",
        "",
        "## Results Matrix",
        "",
    ]

    # Build comparison table
    if report.scores:
        lines.append("| Model | Workflow | Success Rate | Avg Duration | Completion |")
        lines.append("|-------|---------|:---:|:---:|:---:|")
        for s in sorted(report.scores, key=lambda x: (x.model_name, x.workflow_name)):
            lines.append(
                f"| {s.model_name} | {s.workflow_name} | "
                f"{s.success_rate:.0%} ({s.successes}/{s.total_runs}) | "
                f"{s.avg_duration:.1f}s | "
                f"{s.avg_completion_ratio:.0%} |"
            )
        lines.append("")

    # Best combos
    if report.best_overall:
        lines.append("## Best Combinations")
        lines.append("")
        for criterion, info in report.best_overall.items():
            if isinstance(info, dict):
                model = info.get("model", "?")
                workflow = info.get("workflow", "?")
                metric_key = [k for k in info.keys() if k not in ("model", "workflow")]
                metric_val = info.get(metric_key[0], "?") if metric_key else "?"
                lines.append(
                    f"- **{criterion}**: {model} + {workflow} ({metric_key[0] if metric_key else '?'}: {metric_val})"
                )
        lines.append("")

    # Model rankings per workflow
    if report.model_rankings:
        lines.append("## Model Rankings (per workflow)")
        lines.append("")
        for wf, ranking in report.model_rankings.items():
            lines.append(f"### {wf}")
            lines.append("| Rank | Model | Success | Duration | Completion |")
            lines.append("|:---:|-------|:---:|:---:|:---:|")
            for r in ranking:
                lines.append(
                    f"| {r['rank']} | {r['model']} | {r['success_rate']:.0%} | "
                    f"{r['avg_duration']:.1f}s | {r['completion_ratio']:.0%} |"
                )
            lines.append("")

    # Workflow rankings per model
    if report.workflow_rankings:
        lines.append("## Workflow Rankings (per model)")
        lines.append("")
        for model, ranking in report.workflow_rankings.items():
            lines.append(f"### {model}")
            lines.append("| Rank | Workflow | Success | Duration | Completion |")
            lines.append("|:---:|---------|:---:|:---:|:---:|")
            for r in ranking:
                lines.append(
                    f"| {r['rank']} | {r['workflow']} | {r['success_rate']:.0%} | "
                    f"{r['avg_duration']:.1f}s | {r['completion_ratio']:.0%} |"
                )
            lines.append("")

    return "\n".join(lines)


async def run_multi_model_benchmark(
    corpus_path: str,
    output_dir: str,
    workflows: Optional[List[str]] = None,
    models: Optional[List[str]] = None,
    max_docs: int = 0,
    timeout: float = 180.0,
    max_text_chars: int = 5000,
) -> ComparisonReport:
    """
    Run the full multi-model × multi-workflow benchmark.

    Args:
        corpus_path: Path to corpus JSON file.
        output_dir: Directory for results output.
        workflows: Workflow names to test (default: light, standard).
        models: Model names from registry (default: all registered).
        max_docs: Max documents to process (0 = all).
        timeout: Timeout per cell in seconds.
        max_text_chars: Max input text length.

    Returns:
        ComparisonReport with aggregated scores and rankings.
    """
    from dotenv import load_dotenv

    load_dotenv()

    workflows = workflows or ["light", "standard"]
    registry = ModelRegistry.from_env()
    available_models = list(registry.list_models().keys())
    models = models or available_models

    # Filter to actually registered models
    models = [m for m in models if m in available_models]
    if not models:
        raise ValueError(f"No registered models found. Available: {available_models}")

    runner = BenchmarkRunner(registry)
    if corpus_path.endswith(".enc"):
        import os

        passphrase = os.environ.get("TEXT_CONFIG_PASSPHRASE", "")
        if not passphrase:
            raise ValueError(
                "TEXT_CONFIG_PASSPHRASE env var required for encrypted dataset"
            )
        runner.load_dataset_encrypted(corpus_path, passphrase)
    else:
        runner.load_dataset_unencrypted(corpus_path)

    num_docs = len(runner.dataset)
    if max_docs > 0:
        num_docs = min(num_docs, max_docs)

    total_cells = len(models) * len(workflows) * num_docs
    logger.info(
        f"Benchmark matrix: {len(models)} models × {len(workflows)} workflows × "
        f"{num_docs} docs = {total_cells} cells"
    )

    # Setup output
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    collector = ResultCollector(out_path)

    all_results: List[BenchmarkResult] = []
    start_time = time.monotonic()
    cell_num = 0

    for model_name in models:
        for wf_name in workflows:
            for doc_idx in range(num_docs):
                cell_num += 1
                logger.info(
                    f"[{cell_num}/{total_cells}] {model_name} × {wf_name} × doc_{doc_idx}"
                )

                result = await runner.run_cell(
                    workflow_name=wf_name,
                    model_name=model_name,
                    document_index=doc_idx,
                    max_text_chars=max_text_chars,
                    timeout=timeout,
                )
                all_results.append(result)
                collector.save(result)

                status = "OK" if result.success else f"FAIL: {result.error}"
                logger.info(
                    f"  → {status} ({result.duration_seconds:.1f}s, "
                    f"{result.phases_completed}/{result.phases_total} phases)"
                )

    total_duration = time.monotonic() - start_time

    # Compute scores and rankings
    scores = compute_scores(all_results)
    best = find_best(scores)
    model_rank = rank_models(scores)
    workflow_rank = rank_workflows(scores)

    report = ComparisonReport(
        models=models,
        workflows=workflows,
        num_documents=num_docs,
        total_cells=total_cells,
        total_duration_seconds=total_duration,
        scores=scores,
        best_overall=best,
        model_rankings=model_rank,
        workflow_rankings=workflow_rank,
    )

    # Save reports
    report_json = out_path / "comparison_report.json"
    report_md = out_path / "comparison_report.md"

    with open(report_json, "w", encoding="utf-8") as f:
        json.dump(asdict(report), f, indent=2, ensure_ascii=False, default=str)

    with open(report_md, "w", encoding="utf-8") as f:
        f.write(generate_markdown_report(report))

    logger.info(f"Reports saved to {out_path}/")
    logger.info(f"Total benchmark duration: {total_duration:.1f}s")

    return report


def list_available_workflows() -> List[str]:
    """List all registered workflow names from the catalog.

    Includes 'conversational' as a special mode (uses ConversationalOrchestrator
    instead of UnifiedPipeline). (#208-L)
    """
    try:
        from argumentation_analysis.orchestration.unified_pipeline import (
            get_workflow_catalog,
        )

        workflows = list(get_workflow_catalog().keys())
        if "conversational" not in workflows:
            workflows.append("conversational")
        return workflows
    except Exception:
        return ["light", "standard", "full", "conversational"]


def main():
    parser = argparse.ArgumentParser(
        description="Multi-model benchmark: compare LLM models across workflows"
    )
    parser.add_argument(
        "--corpus",
        default="argumentation_analysis/evaluation/corpus/baseline_corpus_v1.json",
        help="Path to corpus JSON",
    )
    parser.add_argument(
        "--output",
        default="argumentation_analysis/evaluation/results/multi_model",
        help="Output directory",
    )
    parser.add_argument(
        "--workflows",
        nargs="+",
        default=["light", "standard"],
        help="Workflow names to benchmark",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=None,
        help="Model names (default: all from .env)",
    )
    parser.add_argument("--max-docs", type=int, default=0, help="Max documents (0=all)")
    parser.add_argument(
        "--timeout", type=float, default=180.0, help="Timeout per cell (seconds)"
    )
    parser.add_argument(
        "--max-text", type=int, default=5000, help="Max input text chars"
    )
    parser.add_argument(
        "--list-workflows",
        action="store_true",
        help="List available workflows and exit",
    )
    parser.add_argument(
        "--list-models", action="store_true", help="List available models and exit"
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(message)s",
    )

    if args.list_workflows:
        print("Available workflows:")
        for wf in list_available_workflows():
            print(f"  - {wf}")
        return

    if args.list_models:
        from dotenv import load_dotenv

        load_dotenv()
        registry = ModelRegistry.from_env()
        print("Available models:")
        for name, config in registry.list_models().items():
            print(f"  - {name}: {config.display_name} ({config.base_url})")
        return

    report = asyncio.run(
        run_multi_model_benchmark(
            corpus_path=args.corpus,
            output_dir=args.output,
            workflows=args.workflows,
            models=args.models,
            max_docs=args.max_docs,
            timeout=args.timeout,
            max_text_chars=args.max_text,
        )
    )

    print(
        f"\nBenchmark complete: {report.total_cells} cells in {report.total_duration_seconds:.1f}s"
    )
    if report.best_overall:
        for criterion, info in report.best_overall.items():
            if isinstance(info, dict):
                print(
                    f"  {criterion}: {info.get('model', '?')} + {info.get('workflow', '?')}"
                )


if __name__ == "__main__":
    main()
