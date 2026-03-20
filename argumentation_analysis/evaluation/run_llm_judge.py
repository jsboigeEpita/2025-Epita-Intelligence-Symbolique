"""
LLM Judge runner: score benchmark results on quality dimensions.

Reads a benchmark_results.jsonl file and evaluates each successful result
using LLMJudge, producing a quality report beyond the simple completion metric.

Usage:
    python -m argumentation_analysis.evaluation.run_llm_judge \
        --results argumentation_analysis/evaluation/results/corpus_v1.1_benchmark/benchmark_results.jsonl \
        --output argumentation_analysis/evaluation/results/corpus_v1.1_benchmark/llm_judge_scores.jsonl \
        --max-docs 10 \
        --judge-model default
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
from typing import Any, Dict, List, Optional

from argumentation_analysis.evaluation.judge import LLMJudge, JudgeScore

logger = logging.getLogger("evaluation.run_llm_judge")


@dataclass
class JudgeResult:
    """Judge evaluation for a single benchmark cell."""

    workflow_name: str
    model_name: str
    document_name: str
    document_index: int
    judge_model: str
    completeness: float
    accuracy: float
    depth: float
    coherence: float
    actionability: float
    overall: float
    reasoning: str
    error: Optional[str] = None
    duration_seconds: float = 0.0
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    @property
    def composite_score(self) -> float:
        """Weighted composite: overall 40%, depth 20%, completeness 20%, accuracy 10%, coherence 5%, actionability 5%."""
        return (
            self.overall * 0.40
            + self.depth * 0.20
            + self.completeness * 0.20
            + self.accuracy * 0.10
            + self.coherence * 0.05
            + self.actionability * 0.05
        )


@dataclass
class JudgeReport:
    """Aggregated quality report across workflows and models."""

    timestamp: str = ""
    total_cells_evaluated: int = 0
    total_errors: int = 0
    # Per (model, workflow) pair stats
    aggregates: List[Dict[str, Any]] = field(default_factory=list)
    best_by_quality: Optional[Dict[str, str]] = None
    best_by_depth: Optional[Dict[str, str]] = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


def load_benchmark_results(path: Path) -> List[Dict[str, Any]]:
    """Load benchmark results from a JSONL file."""
    results = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                results.append(json.loads(line))
    return results


def _load_dotenv() -> None:
    """Load .env file if present."""
    env_path = Path(".env")
    if not env_path.exists():
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip()
            # Strip surrounding quotes if present
            if len(val) >= 2 and val[0] in ('"', "'") and val[-1] == val[0]:
                val = val[1:-1]
            if key not in os.environ:
                os.environ[key] = val


async def run_judge_on_results(
    benchmark_results: List[Dict[str, Any]],
    judge: LLMJudge,
    max_docs: Optional[int] = None,
    workflows_filter: Optional[List[str]] = None,
    models_filter: Optional[List[str]] = None,
) -> List[JudgeResult]:
    """
    Evaluate benchmark results with the LLM judge.

    Args:
        benchmark_results: List of benchmark result dicts from JSONL.
        judge: LLMJudge instance to use.
        max_docs: Limit number of unique documents to evaluate.
        workflows_filter: Only evaluate these workflows (None = all).
        models_filter: Only evaluate these models (None = all).

    Returns:
        List of JudgeResult objects.
    """
    judge_results: List[JudgeResult] = []
    seen_docs: set = set()

    for entry in benchmark_results:
        workflow = entry.get("workflow_name", "")
        model = entry.get("model_name", "")
        doc_name = entry.get("document_name", "")
        doc_idx = entry.get("document_index", 0)
        success = entry.get("success", False)

        # Apply filters
        if workflows_filter and workflow not in workflows_filter:
            continue
        if models_filter and model not in models_filter:
            continue
        if not success:
            logger.info(f"Skipping failed cell: {workflow}/{model}/{doc_name}")
            continue

        # Apply max_docs limit (across all workflows/models, per doc name)
        if max_docs is not None:
            if doc_name not in seen_docs:
                if len(seen_docs) >= max_docs:
                    continue
                seen_docs.add(doc_name)

        state_snapshot = entry.get("state_snapshot", {})
        raw_text = state_snapshot.get("raw_text", "")
        if not raw_text:
            logger.warning(f"No raw_text for {workflow}/{model}/{doc_name}, skipping")
            continue

        logger.info(f"Evaluating: {workflow} / {model} / {doc_name}")
        start = time.time()

        try:
            score: JudgeScore = await judge.evaluate(
                input_text=raw_text,
                workflow_name=workflow,
                analysis_results=state_snapshot,
            )
            duration = time.time() - start

            jr = JudgeResult(
                workflow_name=workflow,
                model_name=model,
                document_name=doc_name,
                document_index=doc_idx,
                judge_model=score.judge_model,
                completeness=score.completeness,
                accuracy=score.accuracy,
                depth=score.depth,
                coherence=score.coherence,
                actionability=score.actionability,
                overall=score.overall,
                reasoning=score.reasoning,
                duration_seconds=duration,
            )
            judge_results.append(jr)
            logger.info(
                f"  → overall={score.overall:.1f} composite={jr.composite_score:.2f} ({duration:.1f}s)"
            )

        except Exception as e:
            duration = time.time() - start
            logger.error(f"Judge failed for {workflow}/{model}/{doc_name}: {e}")
            jr = JudgeResult(
                workflow_name=workflow,
                model_name=model,
                document_name=doc_name,
                document_index=doc_idx,
                judge_model=judge.model_name,
                completeness=0,
                accuracy=0,
                depth=0,
                coherence=0,
                actionability=0,
                overall=0,
                reasoning="",
                error=str(e),
                duration_seconds=duration,
            )
            judge_results.append(jr)

    return judge_results


def build_report(judge_results: List[JudgeResult]) -> JudgeReport:
    """Aggregate judge results into a summary report."""
    from collections import defaultdict

    report = JudgeReport(
        total_cells_evaluated=len(judge_results),
        total_errors=sum(1 for r in judge_results if r.error),
    )

    # Group by (model, workflow)
    groups: Dict[tuple, List[JudgeResult]] = defaultdict(list)
    for r in judge_results:
        if not r.error:
            groups[(r.model_name, r.workflow_name)].append(r)

    aggregates = []
    for (model, workflow), results in groups.items():
        n = len(results)
        agg = {
            "model_name": model,
            "workflow_name": workflow,
            "n_docs": n,
            "avg_overall": sum(r.overall for r in results) / n,
            "avg_completeness": sum(r.completeness for r in results) / n,
            "avg_accuracy": sum(r.accuracy for r in results) / n,
            "avg_depth": sum(r.depth for r in results) / n,
            "avg_coherence": sum(r.coherence for r in results) / n,
            "avg_actionability": sum(r.actionability for r in results) / n,
            "avg_composite": sum(r.composite_score for r in results) / n,
        }
        aggregates.append(agg)

    # Sort by composite descending
    aggregates.sort(key=lambda x: x["avg_composite"], reverse=True)
    report.aggregates = aggregates

    if aggregates:
        best_quality = aggregates[0]
        report.best_by_quality = {
            "model": best_quality["model_name"],
            "workflow": best_quality["workflow_name"],
            "avg_composite": round(best_quality["avg_composite"], 3),
            "avg_overall": round(best_quality["avg_overall"], 3),
        }

        best_depth = max(aggregates, key=lambda x: x["avg_depth"])
        report.best_by_depth = {
            "model": best_depth["model_name"],
            "workflow": best_depth["workflow_name"],
            "avg_depth": round(best_depth["avg_depth"], 3),
        }

    return report


def write_scores_jsonl(results: List[JudgeResult], output_path: Path) -> None:
    """Write per-cell scores to JSONL."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")
    logger.info(f"Wrote {len(results)} scores to {output_path}")


def write_report(report: JudgeReport, output_path: Path) -> None:
    """Write summary report as JSON and Markdown."""
    report_dict = asdict(report)

    # JSON
    json_path = output_path.with_suffix(".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=2, ensure_ascii=False)
    logger.info(f"Report JSON: {json_path}")

    # Markdown
    md_path = output_path.with_suffix(".md")
    lines = [
        "# LLM Judge Quality Report",
        f"\n**Generated:** {report.timestamp}",
        f"**Cells evaluated:** {report.total_cells_evaluated} ({report.total_errors} errors)",
        "",
        "## Best Combinations",
        "",
    ]

    if report.best_by_quality:
        bq = report.best_by_quality
        lines.append(
            f"**Best overall quality**: `{bq['model']}` × `{bq['workflow']}` "
            f"(composite={bq['avg_composite']}, overall={bq['avg_overall']})"
        )
    if report.best_by_depth:
        bd = report.best_by_depth
        lines.append(
            f"**Best depth**: `{bd['model']}` × `{bd['workflow']}` "
            f"(avg_depth={bd['avg_depth']})"
        )

    lines += [
        "",
        "## Scores by (Model × Workflow)",
        "",
        "| Model | Workflow | N | Composite | Overall | Completeness | Accuracy | Depth | Coherence | Actionability |",
        "|-------|----------|---|-----------|---------|--------------|----------|-------|-----------|---------------|",
    ]

    for agg in report.aggregates:
        lines.append(
            f"| {agg['model_name']} | {agg['workflow_name']} | {agg['n_docs']} "
            f"| {agg['avg_composite']:.2f} | {agg['avg_overall']:.2f} "
            f"| {agg['avg_completeness']:.2f} | {agg['avg_accuracy']:.2f} "
            f"| {agg['avg_depth']:.2f} | {agg['avg_coherence']:.2f} "
            f"| {agg['avg_actionability']:.2f} |"
        )

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    logger.info(f"Report Markdown: {md_path}")


async def main_async(args: argparse.Namespace) -> int:
    """Main async entry point."""
    _load_dotenv()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    results_path = Path(args.results)
    if not results_path.exists():
        logger.error(f"Results file not found: {results_path}")
        return 1

    output_path = Path(args.output)
    report_path = output_path.parent / "llm_judge_report"

    logger.info(f"Loading benchmark results from {results_path}")
    benchmark_results = load_benchmark_results(results_path)
    logger.info(f"Loaded {len(benchmark_results)} benchmark cells")

    judge = LLMJudge(model_name=args.judge_model)

    workflows_filter = args.workflows.split(",") if args.workflows else None
    models_filter = args.models.split(",") if args.models else None

    judge_results = await run_judge_on_results(
        benchmark_results,
        judge,
        max_docs=args.max_docs,
        workflows_filter=workflows_filter,
        models_filter=models_filter,
    )

    logger.info(
        f"Evaluated {len(judge_results)} cells "
        f"({sum(1 for r in judge_results if r.error)} errors)"
    )

    write_scores_jsonl(judge_results, output_path)

    report = build_report(judge_results)
    write_report(report, report_path)

    # Print summary table
    print("\n=== LLM Judge Quality Summary ===\n")
    print(
        f"{'Model':<15} {'Workflow':<22} {'N':>3}  {'Composite':>9}  {'Overall':>7}  {'Depth':>5}"
    )
    print("-" * 75)
    for agg in report.aggregates:
        print(
            f"{agg['model_name']:<15} {agg['workflow_name']:<22} {agg['n_docs']:>3}  "
            f"{agg['avg_composite']:>9.2f}  {agg['avg_overall']:>7.2f}  {agg['avg_depth']:>5.2f}"
        )
    if report.best_by_quality:
        bq = report.best_by_quality
        print(
            f"\nBest overall: {bq['model']} × {bq['workflow']} (composite={bq['avg_composite']})"
        )

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run LLM judge on benchmark results to score analysis quality."
    )
    parser.add_argument(
        "--results",
        required=True,
        help="Path to benchmark_results.jsonl",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to write scored JSONL output",
    )
    parser.add_argument(
        "--judge-model",
        default="default",
        help="Model name for the judge (default: use OPENAI_CHAT_MODEL_ID env var)",
    )
    parser.add_argument(
        "--max-docs",
        type=int,
        default=None,
        help="Max unique documents to evaluate (default: all)",
    )
    parser.add_argument(
        "--workflows",
        default=None,
        help="Comma-separated list of workflows to evaluate (default: all)",
    )
    parser.add_argument(
        "--models",
        default=None,
        help="Comma-separated list of model names to evaluate (default: all)",
    )
    args = parser.parse_args()

    sys.exit(asyncio.run(main_async(args)))


if __name__ == "__main__":
    main()
