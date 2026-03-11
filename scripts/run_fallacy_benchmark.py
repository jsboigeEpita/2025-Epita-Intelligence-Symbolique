#!/usr/bin/env python
"""Runner for the comparative fallacy detection benchmark (#84 Phase 4).

Usage:
    conda run -n projet-is-roo-new --no-capture-output python scripts/run_fallacy_benchmark.py
    conda run -n projet-is-roo-new --no-capture-output python scripts/run_fallacy_benchmark.py --parallel 3

Runs 10 test cases × 3 detection modes = 30 LLM calls.
Saves JSON report + prints summary table.
"""
import argparse
import asyncio
import logging
import os
import sys

# Ensure project root is on path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, ".env"))

from argumentation_analysis.evaluation.fallacy_benchmark import (
    FallacyBenchmarkRunner,
    BENCHMARK_CASES,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)


async def main():
    parser = argparse.ArgumentParser(description="Fallacy detection benchmark")
    parser.add_argument("--parallel", type=int, default=1,
                        help="Max concurrent LLM tasks (1=sequential, 3+=parallel)")
    parser.add_argument("--modes", nargs="+", default=["free", "one_shot", "constrained"],
                        help="Detection modes to run")
    args = parser.parse_args()

    print("=" * 70)
    print("  Fallacy Detection Comparative Benchmark (#84 Phase 4)")
    print(f"  Model: {os.environ.get('OPENAI_CHAT_MODEL_ID', 'gpt-5-mini')}")
    print(f"  Cases: {len(BENCHMARK_CASES)}")
    print(f"  Modes: {', '.join(args.modes)}")
    print(f"  Concurrency: {args.parallel}")
    print("=" * 70)

    runner = FallacyBenchmarkRunner()

    if not runner.taxonomy_data:
        print("ERROR: Taxonomy file not found. Cannot run benchmark.")
        sys.exit(1)
    print(f"  Taxonomy: {len(runner.taxonomy_data)} nodes loaded\n")

    report = await runner.run_benchmark(
        modes=args.modes, concurrency=args.parallel
    )

    # Print results table
    print("\n" + "=" * 70)
    print("  DETAILED RESULTS")
    print("=" * 70)
    header = f"{'Case':<10} {'Mode':<13} {'Expected':<25} {'Detected':<25} {'PK?':>4} {'Fam?':>4} {'Sim':>5} {'Dpth':>4} {'Time':>5}"
    print(header)
    print("-" * len(header))
    for r in report.results:
        case = next(c for c in BENCHMARK_CASES if c["id"] == r.case_id)
        pk_ok = "Y" if r.exact_pk_match else "N"
        fam_ok = "Y" if r.family_match else "N"
        print(
            f"{r.case_id:<10} {r.mode:<13} "
            f"{case['expected_name'][:24]:<25} "
            f"{r.detected_name[:24]:<25} "
            f"{pk_ok:>4} {fam_ok:>4} "
            f"{r.name_similarity:>5.2f} {r.depth_reached:>4} "
            f"{r.duration_seconds:>5.1f}s"
        )

    # Print summary
    print("\n" + report.summary)

    # Save report
    report_path = os.path.join(ROOT, "docs", "reports", "fallacy_benchmark_results.json")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    runner.save_report(report, report_path)
    print(f"\nReport saved: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
