#!/usr/bin/env python3
"""
Benchmark orchestration script for Issue #82.

Runs a grid of (workflow × model × document) cells using the evaluation module.
Stores results in JSONL format and prints a summary table.

Usage:
    # Calibration: 3 workflows × 2 documents = 6 cells
    python scripts/run_benchmark.py --workflows light standard full --docs 0 1 --model default

    # Full grid with all workflows and all documents
    python scripts/run_benchmark.py --full

    # Print summary of existing results
    python scripts/run_benchmark.py --summary
"""

import argparse
import asyncio
import json
import logging
import os
import sys
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
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("benchmark")

# Available workflows from unified_pipeline.py
ALL_WORKFLOWS = [
    "light", "standard", "full", "quality_gated",
    "democratech", "debate_tournament", "fact_check",
]

DATASET_PATH = str(
    project_root / "argumentation_analysis" / "data" / "extract_sources.json.gz.enc"
)


def print_summary(collector: ResultCollector):
    """Print a formatted summary of benchmark results."""
    summary = collector.generate_summary()
    if summary.get("total", 0) == 0:
        print("No benchmark results found.")
        return

    print("\n" + "=" * 80)
    print(f"BENCHMARK SUMMARY — {summary['generated_at']}")
    print(f"Total: {summary['total']} cells | "
          f"Success: {summary['successes']} | "
          f"Failures: {summary['failures']} | "
          f"Rate: {summary['successes']/summary['total']*100:.0f}%")
    print("=" * 80)

    print("\nBy Model:")
    print(f"{'Model':<30} {'Total':>6} {'OK':>4} {'Avg Duration':>14} {'Avg Phases':>12}")
    print("-" * 70)
    for model, stats in summary.get("by_model", {}).items():
        print(f"{model:<30} {stats['total']:>6} {stats['success']:>4} "
              f"{stats['avg_duration']:>12.1f}s {stats['avg_phases_completed']:>10.1f}")

    print("\nBy Workflow:")
    print(f"{'Workflow':<30} {'Total':>6} {'OK':>4} {'Avg Duration':>14}")
    print("-" * 54)
    for wf, stats in summary.get("by_workflow", {}).items():
        print(f"{wf:<30} {stats['total']:>6} {stats['success']:>4} "
              f"{stats['avg_duration']:>12.1f}s")

    # Detail table
    results = collector.load_all()
    print(f"\n{'Workflow':<20} {'Model':<20} {'Doc':<5} {'OK':>3} {'Dur':>7} {'Phases':>8} {'Error':>30}")
    print("-" * 95)
    for r in results[-30:]:  # Last 30 results
        ok = "Y" if r["success"] else "N"
        dur = f"{r['duration_seconds']:.1f}s" if r["duration_seconds"] > 0 else "-"
        phases = f"{r['phases_completed']}/{r['phases_total']}" if r["success"] else "-"
        err = (r.get("error") or "")[:28]
        print(f"{r['workflow_name']:<20} {r['model_name']:<20} {r['document_index']:>3}   "
              f"{ok:>3} {dur:>7} {phases:>8} {err:>30}")


async def run_benchmark(
    workflows: list,
    doc_indices: list,
    model_name: str,
    timeout: float = 120.0,
    max_text_chars: int = 3000,
):
    """Run a grid of benchmark cells."""
    registry = ModelRegistry.from_env()
    runner = BenchmarkRunner(registry)
    collector = ResultCollector()

    # Load dataset
    if not os.path.exists(DATASET_PATH):
        logger.error(f"Dataset not found: {DATASET_PATH}")
        return

    passphrase = os.getenv("TEXT_CONFIG_PASSPHRASE")
    if not passphrase:
        logger.error("TEXT_CONFIG_PASSPHRASE not set in environment (.env)")
        return
    runner.load_dataset_encrypted(DATASET_PATH, passphrase)
    total_docs = len(runner.dataset)
    logger.info(f"Dataset: {total_docs} documents")

    # Validate doc indices
    valid_docs = [i for i in doc_indices if i < total_docs]
    if not valid_docs:
        logger.error(f"No valid document indices (max: {total_docs - 1})")
        return

    total_cells = len(workflows) * len(valid_docs)
    logger.info(f"Running {total_cells} cells: {len(workflows)} workflows × {len(valid_docs)} docs")

    results = []
    for i, wf in enumerate(workflows):
        for j, doc_idx in enumerate(valid_docs):
            cell_num = i * len(valid_docs) + j + 1
            doc_name = runner.get_document_name(doc_idx)
            logger.info(f"[{cell_num}/{total_cells}] {wf} × {model_name} × doc[{doc_idx}] ({doc_name})")

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
            results.append(result)

    print_summary(collector)
    return results


def main():
    parser = argparse.ArgumentParser(description="Run evaluation benchmarks")
    parser.add_argument("--workflows", nargs="+", default=["light", "standard"],
                        help="Workflow names to benchmark")
    parser.add_argument("--docs", nargs="+", type=int, default=[0, 1],
                        help="Document indices to use")
    parser.add_argument("--model", default="default",
                        help="Model name from registry")
    parser.add_argument("--timeout", type=float, default=120.0,
                        help="Timeout per cell in seconds")
    parser.add_argument("--max-text", type=int, default=3000,
                        help="Max chars of input text per cell")
    parser.add_argument("--full", action="store_true",
                        help="Run all workflows × all documents")
    parser.add_argument("--summary", action="store_true",
                        help="Print summary of existing results only")
    parser.add_argument("--export-csv", action="store_true",
                        help="Export results to CSV")

    args = parser.parse_args()

    if args.summary:
        collector = ResultCollector()
        print_summary(collector)
        return

    if args.export_csv:
        collector = ResultCollector()
        path = collector.export_csv()
        print(f"Exported to: {path}")
        return

    workflows = ALL_WORKFLOWS if args.full else args.workflows
    doc_indices = list(range(6)) if args.full else args.docs

    asyncio.run(run_benchmark(
        workflows=workflows,
        doc_indices=doc_indices,
        model_name=args.model,
        timeout=args.timeout,
        max_text_chars=args.max_text,
    ))


if __name__ == "__main__":
    main()
