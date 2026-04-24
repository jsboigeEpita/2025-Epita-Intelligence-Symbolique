#!/usr/bin/env python3
"""
Multi-model benchmark with LLM judge evaluation (Issue #82, Phase 3).

Runs benchmarks across multiple models and evaluates output quality using an LLM judge.
Produces a comparison report.

Usage:
    # Run comparison on 2 workflows × 2 docs for all available models
    python scripts/run_benchmark_multimodel.py

    # With LLM judge scoring
    python scripts/run_benchmark_multimodel.py --judge

    # Generate report from existing results
    python scripts/run_benchmark_multimodel.py --report
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from argumentation_analysis.evaluation import (
    ModelRegistry,
    BenchmarkRunner,
    ResultCollector,
    BenchmarkResult,
    LLMJudge,
)
from argumentation_analysis.evaluation.judge import JudgeScore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("benchmark.multimodel")

DATASET_PATH = str(
    project_root / "argumentation_analysis" / "data" / "extract_sources.json.gz.enc"
)

# Workflows to compare (representative subset)
COMPARE_WORKFLOWS = ["light", "standard", "full"]
COMPARE_DOCS = [0, 1]


def build_registry() -> ModelRegistry:
    """Build registry and log available models."""
    registry = ModelRegistry.from_env()
    models = registry.list_models()
    logger.info(f"Available models: {list(models.keys())}")
    for name, cfg in models.items():
        logger.info(f"  {name}: {cfg.display_name} @ {cfg.base_url}")
    return registry


async def run_multimodel_comparison(
    workflows: list,
    doc_indices: list,
    timeout: float = 600.0,
    max_text_chars: int = 3000,
    run_judge: bool = False,
) -> dict:
    """Run benchmarks across all registered models and compare."""
    registry = build_registry()
    runner = BenchmarkRunner(registry)
    collector = ResultCollector()

    # Load dataset
    if not os.path.exists(DATASET_PATH):
        logger.error(f"Dataset not found: {DATASET_PATH}")
        return {}

    passphrase = os.getenv("TEXT_CONFIG_PASSPHRASE")
    if not passphrase:
        logger.error("TEXT_CONFIG_PASSPHRASE not set in environment (.env)")
        return {}
    runner.load_dataset_encrypted(DATASET_PATH, passphrase)
    total_docs = len(runner.dataset)
    valid_docs = [i for i in doc_indices if i < total_docs]

    models = list(registry.list_models().keys())
    total_cells = len(models) * len(workflows) * len(valid_docs)
    logger.info(f"Multi-model comparison: {len(models)} models × {len(workflows)} workflows × {len(valid_docs)} docs = {total_cells} cells")

    all_results = {}
    cell_num = 0

    for model_name in models:
        model_results = []
        for wf in workflows:
            for doc_idx in valid_docs:
                cell_num += 1
                doc_name = runner.get_document_name(doc_idx)
                logger.info(f"[{cell_num}/{total_cells}] {model_name} × {wf} × doc[{doc_idx}] ({doc_name})")

                result = await runner.run_cell(
                    workflow_name=wf,
                    model_name=model_name,
                    document_index=doc_idx,
                    max_text_chars=max_text_chars,
                    timeout=timeout,
                )

                status = "OK" if result.success else f"FAIL: {result.error}"
                logger.info(f"  → {status} ({result.duration_seconds:.1f}s, "
                            f"{result.phases_completed}/{result.phases_total} phases)")

                collector.save(result)
                model_results.append(result)

        all_results[model_name] = model_results

    # LLM Judge evaluation
    judge_scores = {}
    if run_judge:
        logger.info("=== LLM Judge Evaluation ===")
        judge = LLMJudge(model_name="default")
        judge_results = []

        for model_name, results in all_results.items():
            for result in results:
                if not result.success or not result.state_snapshot:
                    continue

                doc_text = runner.get_document_text(result.document_index)[:2000]
                logger.info(f"Judging: {model_name} × {result.workflow_name} × doc[{result.document_index}]")

                score = await judge.evaluate(
                    input_text=doc_text,
                    workflow_name=result.workflow_name,
                    analysis_results=result.state_snapshot or {},
                    model_registry=registry,
                )

                judge_entry = {
                    "model": model_name,
                    "workflow": result.workflow_name,
                    "document_index": result.document_index,
                    "completeness": score.completeness,
                    "accuracy": score.accuracy,
                    "depth": score.depth,
                    "coherence": score.coherence,
                    "actionability": score.actionability,
                    "overall": score.overall,
                    "reasoning": score.reasoning,
                    "judge_model": score.judge_model,
                }
                judge_results.append(judge_entry)
                logger.info(f"  → Overall: {score.overall}/5 ({score.reasoning[:80]}...)")

        # Save judge results
        judge_path = collector.results_dir / "judge_scores.jsonl"
        with open(judge_path, "a", encoding="utf-8") as f:
            for entry in judge_results:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        logger.info(f"Saved {len(judge_results)} judge scores to {judge_path}")
        judge_scores = _aggregate_judge_scores(judge_results)

    # Print comparison
    print_comparison(all_results, judge_scores)
    return all_results


def _aggregate_judge_scores(judge_results: list) -> dict:
    """Aggregate judge scores by model."""
    from collections import defaultdict
    by_model = defaultdict(list)
    for entry in judge_results:
        by_model[entry["model"]].append(entry)

    agg = {}
    for model, entries in by_model.items():
        n = len(entries)
        agg[model] = {
            "count": n,
            "avg_overall": sum(e["overall"] for e in entries) / n if n else 0,
            "avg_completeness": sum(e["completeness"] for e in entries) / n if n else 0,
            "avg_accuracy": sum(e["accuracy"] for e in entries) / n if n else 0,
            "avg_depth": sum(e["depth"] for e in entries) / n if n else 0,
            "avg_coherence": sum(e["coherence"] for e in entries) / n if n else 0,
            "avg_actionability": sum(e["actionability"] for e in entries) / n if n else 0,
        }
    return agg


def print_comparison(all_results: dict, judge_scores: dict = None):
    """Print formatted multi-model comparison."""
    print("\n" + "=" * 90)
    print("MULTI-MODEL BENCHMARK COMPARISON")
    print("=" * 90)

    # Performance table
    print(f"\n{'Model':<25} {'Cells':>6} {'OK':>4} {'Rate':>6} {'Avg Duration':>14} {'Avg Phases':>12}")
    print("-" * 75)

    for model_name, results in all_results.items():
        total = len(results)
        ok = sum(1 for r in results if r.success)
        ok_results = [r for r in results if r.success]
        avg_dur = sum(r.duration_seconds for r in ok_results) / len(ok_results) if ok_results else 0
        avg_phases = sum(r.phases_completed for r in ok_results) / len(ok_results) if ok_results else 0
        rate = f"{ok/total*100:.0f}%" if total else "N/A"
        print(f"{model_name:<25} {total:>6} {ok:>4} {rate:>6} {avg_dur:>12.1f}s {avg_phases:>10.1f}")

    # Per-workflow breakdown
    print(f"\n{'Model':<20} {'Workflow':<20} {'OK':>4} {'Avg Dur':>10} {'Phases':>8}")
    print("-" * 65)
    for model_name, results in all_results.items():
        by_wf = {}
        for r in results:
            by_wf.setdefault(r.workflow_name, []).append(r)
        for wf, wf_results in by_wf.items():
            ok = [r for r in wf_results if r.success]
            avg_dur = sum(r.duration_seconds for r in ok) / len(ok) if ok else 0
            avg_ph = sum(r.phases_completed for r in ok) / len(ok) if ok else 0
            print(f"{model_name:<20} {wf:<20} {len(ok):>4} {avg_dur:>8.1f}s {avg_ph:>6.1f}")

    # Judge scores
    if judge_scores:
        print(f"\n{'Model':<25} {'Overall':>8} {'Complete':>10} {'Accuracy':>10} {'Depth':>8} {'Coherence':>10} {'Action':>8}")
        print("-" * 85)
        for model, scores in judge_scores.items():
            print(f"{model:<25} {scores['avg_overall']:>7.1f} {scores['avg_completeness']:>9.1f} "
                  f"{scores['avg_accuracy']:>9.1f} {scores['avg_depth']:>7.1f} "
                  f"{scores['avg_coherence']:>9.1f} {scores['avg_actionability']:>7.1f}")


def generate_report():
    """Generate a markdown report from existing results."""
    collector = ResultCollector()
    all_results = collector.load_all()

    if not all_results:
        print("No benchmark results found.")
        return

    # Group by model
    by_model = {}
    for r in all_results:
        by_model.setdefault(r["model_name"], []).append(r)

    report_lines = [
        "# Benchmark Evaluation Report",
        f"\nGenerated: {datetime.now().isoformat()}",
        f"\nTotal benchmark cells: {len(all_results)}",
        f"Models tested: {', '.join(by_model.keys())}",
        "",
        "## Performance Summary",
        "",
        "| Model | Cells | Success | Rate | Avg Duration | Avg Phases |",
        "|-------|-------|---------|------|--------------|------------|",
    ]

    for model, results in by_model.items():
        total = len(results)
        ok = [r for r in results if r["success"]]
        rate = f"{len(ok)/total*100:.0f}%" if total else "N/A"
        avg_dur = sum(r["duration_seconds"] for r in ok) / len(ok) if ok else 0
        avg_ph = sum(r["phases_completed"] for r in ok) / len(ok) if ok else 0
        report_lines.append(
            f"| {model} | {total} | {len(ok)} | {rate} | {avg_dur:.1f}s | {avg_ph:.1f} |"
        )

    # Workflow breakdown
    report_lines.extend([
        "",
        "## Per-Workflow Breakdown",
        "",
        "| Model | Workflow | Success | Avg Duration | Avg Phases |",
        "|-------|----------|---------|--------------|------------|",
    ])

    for model, results in by_model.items():
        by_wf = {}
        for r in results:
            by_wf.setdefault(r["workflow_name"], []).append(r)
        for wf, wf_results in sorted(by_wf.items()):
            ok = [r for r in wf_results if r["success"]]
            avg_dur = sum(r["duration_seconds"] for r in ok) / len(ok) if ok else 0
            avg_ph = sum(r["phases_completed"] for r in ok) / len(ok) if ok else 0
            report_lines.append(
                f"| {model} | {wf} | {len(ok)}/{len(wf_results)} | {avg_dur:.1f}s | {avg_ph:.1f} |"
            )

    # Judge scores if available
    judge_path = collector.results_dir / "judge_scores.jsonl"
    if judge_path.exists():
        judge_results = []
        with open(judge_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    judge_results.append(json.loads(line))

        if judge_results:
            agg = _aggregate_judge_scores(judge_results)
            report_lines.extend([
                "",
                "## LLM Judge Quality Scores (1-5 scale)",
                "",
                "| Model | Overall | Completeness | Accuracy | Depth | Coherence | Actionability |",
                "|-------|---------|-------------|----------|-------|-----------|--------------|",
            ])
            for model, scores in agg.items():
                report_lines.append(
                    f"| {model} | {scores['avg_overall']:.1f} | {scores['avg_completeness']:.1f} | "
                    f"{scores['avg_accuracy']:.1f} | {scores['avg_depth']:.1f} | "
                    f"{scores['avg_coherence']:.1f} | {scores['avg_actionability']:.1f} |"
                )

            # Individual judge entries
            report_lines.extend([
                "",
                "### Individual Judge Evaluations",
                "",
            ])
            for entry in judge_results:
                report_lines.append(
                    f"- **{entry['model']}** × {entry['workflow']} × doc[{entry['document_index']}]: "
                    f"overall={entry['overall']}/5 — {entry.get('reasoning', '')[:120]}"
                )

    report_lines.extend([
        "",
        "---",
        f"*Report generated by `scripts/run_benchmark_multimodel.py` on {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
    ])

    report_path = project_root / "docs" / "reports" / "benchmark_evaluation_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"Report saved to: {report_path}")


def main():
    parser = argparse.ArgumentParser(description="Multi-model benchmark comparison")
    parser.add_argument("--workflows", nargs="+", default=COMPARE_WORKFLOWS,
                        help="Workflows to compare")
    parser.add_argument("--docs", nargs="+", type=int, default=COMPARE_DOCS,
                        help="Document indices")
    parser.add_argument("--timeout", type=float, default=600.0,
                        help="Timeout per cell in seconds")
    parser.add_argument("--max-text", type=int, default=3000,
                        help="Max chars of input text per cell")
    parser.add_argument("--judge", action="store_true",
                        help="Run LLM judge evaluation on results")
    parser.add_argument("--report", action="store_true",
                        help="Generate markdown report from existing results")

    args = parser.parse_args()

    if args.report:
        generate_report()
        return

    asyncio.run(run_multimodel_comparison(
        workflows=args.workflows,
        doc_indices=args.docs,
        timeout=args.timeout,
        max_text_chars=args.max_text,
        run_judge=args.judge,
    ))


if __name__ == "__main__":
    main()
