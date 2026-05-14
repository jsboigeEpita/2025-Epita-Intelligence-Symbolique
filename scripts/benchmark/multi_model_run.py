#!/usr/bin/env python3
"""Multi-model benchmark for the spectacular workflow (#452).

Runs the spectacular workflow on 3 sample texts across available models,
capturing per-model metrics: wall-clock, tokens, cost, arguments extracted,
fallacies detected, FOL formulas validated, counter-arguments generated.

Usage:
    # Run benchmark (requires API keys)
    python scripts/benchmark/multi_model_run.py

    # Generate report from existing results
    python scripts/benchmark/multi_model_run.py --report

    # Override models to test
    python scripts/benchmark/multi_model_run.py --models default gpt-5-nano openrouter
"""
import argparse
import asyncio
import csv
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("benchmark.spectacular")

# --- Sample texts (3 scenarios from examples/) ---
SAMPLE_TEXTS = {
    "science": (project_root / "examples" / "scenarios" / "science.txt").read_text(
        encoding="utf-8"
    )[:3000],
    "politics": (project_root / "examples" / "scenarios" / "politics.txt").read_text(
        encoding="utf-8"
    )[:3000],
    "philosophy": (project_root / "examples" / "scenarios" / "philosophy.txt").read_text(
        encoding="utf-8"
    )[:3000],
}

# Cost per 1M tokens (input/output) — approximate 2025 pricing
COST_TABLE = {
    "gpt-5-mini": {"input": 0.15, "output": 0.60},
    "gpt-5": {"input": 2.50, "output": 10.00},
    "gpt-5-nano": {"input": 0.05, "output": 0.20},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "claude-haiku-4-5": {"input": 0.80, "output": 4.00},
}

RESULTS_DIR = project_root / "argumentation_analysis" / "evaluation" / "results"
REPORT_PATH = project_root / "docs" / "benchmarks" / "multi_model_comparison.md"
RAW_CSV_PATH = RESULTS_DIR / "spectacular_benchmark_raw.csv"


def _estimate_cost(model_id: str, input_tokens: int, output_tokens: int) -> float:
    rates = COST_TABLE.get(model_id, {"input": 1.0, "output": 4.0})
    return (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1_000_000


def _count_metrics(state: Dict[str, Any]) -> Dict[str, int]:
    """Extract analysis metrics from a UnifiedAnalysisState snapshot."""
    args_count = len(state.get("extracted_arguments", state.get("arguments", [])))
    fallacies_count = len(state.get("detected_fallacies", []))
    fol_count = len(state.get("fol_analysis", {}).get("formulas", []))
    counter_args_count = len(state.get("counter_arguments", []))

    return {
        "arguments_extracted": args_count,
        "fallacies_detected": fallacies_count,
        "fol_validated": fol_count,
        "counter_arguments": counter_args_count,
    }


async def run_single_benchmark(
    model_name: str,
    model_config: Any,
    text_id: str,
    text: str,
    timeout: float = 600.0,
) -> Dict[str, Any]:
    """Run the spectacular workflow for a single model × text combination."""
    from argumentation_analysis.evaluation import BenchmarkRunner, ModelRegistry

    registry = ModelRegistry()
    registry.register(model_name, model_config)
    saved_env = registry.save_env()
    registry.activate(model_name)

    runner = BenchmarkRunner(registry)
    runner.load_text(text_id, text)

    start = time.monotonic()
    try:
        result = await runner.run_cell(
            workflow_name="spectacular",
            model_name=model_name,
            document_index=0,
            max_text_chars=len(text),
            timeout=timeout,
        )
    except Exception as e:
        logger.error(f"Benchmark failed: {model_name} × {text_id}: {e}")
        return {
            "model": model_name,
            "text_id": text_id,
            "success": False,
            "error": str(e),
            "duration_seconds": time.monotonic() - start,
        }
    finally:
        registry.restore_env(saved_env)

    duration = time.monotonic() - start
    state = result.state_snapshot or {}
    metrics = _count_metrics(state)

    return {
        "model": model_name,
        "text_id": text_id,
        "success": result.success,
        "duration_seconds": round(duration, 2),
        "phases_completed": result.phases_completed,
        "phases_total": result.phases_total,
        "input_tokens": result.input_tokens if hasattr(result, "input_tokens") else 0,
        "output_tokens": result.output_tokens if hasattr(result, "output_tokens") else 0,
        "estimated_cost_usd": round(
            _estimate_cost(
                model_config.model_id,
                getattr(result, "input_tokens", 0),
                getattr(result, "output_tokens", 0),
            ),
            4,
        ),
        **metrics,
    }


async def run_benchmark(
    model_names: Optional[List[str]] = None,
    text_ids: Optional[List[str]] = None,
    timeout: float = 600.0,
) -> List[Dict[str, Any]]:
    """Run the full multi-model benchmark matrix."""
    from argumentation_analysis.evaluation import ModelRegistry

    registry = ModelRegistry.from_env()
    available = list(registry.list_models().keys())
    models = model_names or available
    texts = text_ids or list(SAMPLE_TEXTS.keys())

    unknown = [m for m in models if m not in available]
    if unknown:
        logger.warning(f"Models not in registry, skipping: {unknown}")
        models = [m for m in models if m in available]

    total = len(models) * len(texts)
    logger.info(f"Benchmark: {len(models)} models × {len(texts)} texts = {total} cells")

    results = []
    cell = 0
    for model_name in models:
        config = registry.get(model_name)
        for text_id in texts:
            cell += 1
            text = SAMPLE_TEXTS[text_id]
            logger.info(f"[{cell}/{total}] {model_name} × {text_id}")
            result = await run_single_benchmark(
                model_name, config, text_id, text, timeout=timeout
            )
            results.append(result)
            status = "OK" if result["success"] else f"FAIL: {result.get('error', '?')[:60]}"
            logger.info(f"  → {status} ({result['duration_seconds']:.1f}s)")

    return results


def save_raw_csv(results: List[Dict[str, Any]]) -> Path:
    """Save raw results as CSV (gitignored)."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "model", "text_id", "success", "duration_seconds",
        "phases_completed", "phases_total", "input_tokens", "output_tokens",
        "estimated_cost_usd", "arguments_extracted", "fallacies_detected",
        "fol_validated", "counter_arguments", "error",
    ]
    with open(RAW_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)
    logger.info(f"Raw CSV saved to {RAW_CSV_PATH}")
    return RAW_CSV_PATH


def generate_report(results: Optional[List[Dict[str, Any]]] = None) -> str:
    """Generate markdown comparison report."""
    if results is None:
        if not RAW_CSV_PATH.exists():
            return "No benchmark results found. Run with --run first."
        with open(RAW_CSV_PATH, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            results = list(reader)
        # Convert numeric strings
        for r in results:
            for k in ("duration_seconds", "estimated_cost_usd", "arguments_extracted",
                       "fallacies_detected", "fol_validated", "counter_arguments",
                       "input_tokens", "output_tokens"):
                r[k] = float(r.get(k, 0))

    # Group by model
    by_model: Dict[str, List[Dict]] = {}
    for r in results:
        by_model.setdefault(r["model"], []).append(r)

    lines = [
        "# Multi-Model Spectacular Workflow Benchmark",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Workflow: spectacular_analysis",
        f"Sample texts: {', '.join(SAMPLE_TEXTS.keys())}",
        f"Models tested: {len(by_model)}",
        "",
        "## Summary",
        "",
        "| Model | Cells | OK | Rate | Avg Duration | Est. Cost | Args | Fallacies | FOL | Counter-Args |",
        "|-------|-------|----|------|-------------|-----------|------|-----------|-----|-------------|",
    ]

    for model, cells in sorted(by_model.items()):
        ok = [c for c in cells if c.get("success") in (True, "True", "true")]
        total = len(cells)
        rate = f"{len(ok)/total*100:.0f}%" if total else "N/A"
        avg_dur = sum(c["duration_seconds"] for c in ok) / len(ok) if ok else 0
        total_cost = sum(c["estimated_cost_usd"] for c in ok)
        avg_args = sum(c["arguments_extracted"] for c in ok) / len(ok) if ok else 0
        avg_fall = sum(c["fallacies_detected"] for c in ok) / len(ok) if ok else 0
        avg_fol = sum(c["fol_validated"] for c in ok) / len(ok) if ok else 0
        avg_ca = sum(c["counter_arguments"] for c in ok) / len(ok) if ok else 0
        lines.append(
            f"| {model} | {total} | {len(ok)} | {rate} | {avg_dur:.1f}s | "
            f"${total_cost:.4f} | {avg_args:.1f} | {avg_fall:.1f} | {avg_fol:.1f} | {avg_ca:.1f} |"
        )

    lines.extend([
        "",
        "## Per-Text Breakdown",
        "",
        "| Model | Text | Duration | Phases | Args | Fallacies | FOL | Counter-Args |",
        "|-------|------|----------|--------|------|-----------|-----|-------------|",
    ])
    for model, cells in sorted(by_model.items()):
        for c in cells:
            lines.append(
                f"| {model} | {c['text_id']} | {c['duration_seconds']:.1f}s | "
                f"{c['phases_completed']}/{c['phases_total']} | "
                f"{c['arguments_extracted']} | {c['fallacies_detected']} | "
                f"{c['fol_validated']} | {c['counter_arguments']} |"
            )

    lines.extend([
        "",
        "---",
        f"*Report generated by `scripts/benchmark/multi_model_run.py` on {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        "",
        "## Methodology",
        "",
        "Each model runs the `spectacular_analysis` workflow (full-chain: extraction → fallacy detection → FOL → counter-arguments → quality → governance → synthesis) on 3 French argumentative texts (science, politics, philosophy, ~3000 chars each). Metrics are extracted from the UnifiedAnalysisState snapshot.",
        "",
        "## Cost Estimation",
        "",
        "Costs are estimated from token counts × published per-token pricing. Actual costs may vary.",
        "",
        "## How to Reproduce",
        "",
        "```bash",
        "# Ensure .env has OPENAI_API_KEY and optionally OPENROUTER_API_KEY",
        "python scripts/benchmark/multi_model_run.py --run",
        "python scripts/benchmark/multi_model_run.py --report",
        "```",
    ])

    report = "\n".join(lines)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    logger.info(f"Report saved to {REPORT_PATH}")
    return report


def main():
    parser = argparse.ArgumentParser(
        description="Multi-model spectacular workflow benchmark (#452)"
    )
    parser.add_argument("--run", action="store_true", help="Run benchmark")
    parser.add_argument("--report", action="store_true", help="Generate report from results")
    parser.add_argument("--models", nargs="+", default=None, help="Model names to test")
    parser.add_argument("--texts", nargs="+", default=None, help="Text IDs to test")
    parser.add_argument("--timeout", type=float, default=600.0, help="Timeout per cell (s)")
    args = parser.parse_args()

    if args.report:
        generate_report()
        return

    if args.run:
        results = asyncio.run(run_benchmark(
            model_names=args.models,
            text_ids=args.texts,
            timeout=args.timeout,
        ))
        save_raw_csv(results)
        generate_report(results)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
