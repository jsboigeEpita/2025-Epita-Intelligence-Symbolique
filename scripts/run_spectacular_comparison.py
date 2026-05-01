#!/usr/bin/env python3
"""
Spectacular vs Baseline comparison script for Issues #366 and #367.

Runs both standard and spectacular workflows on documents from the encrypted
dataset, collects metrics, and generates comparison reports.

Usage:
    # Run comparison on 3 docs and generate reports
    python scripts/run_spectacular_comparison.py --docs 0 1 2

    # Use specific model
    python scripts/run_spectacular_comparison.py --docs 0 1 2 --model default

    # Generate reports from cached results (no re-run)
    python scripts/run_spectacular_comparison.py --report-only

Privacy: All reports use opaque IDs (doc_A, doc_B, doc_C) — no plaintext.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

load_dotenv(project_root / ".env")

from argumentation_analysis.evaluation import (
    BenchmarkRunner,
    ModelRegistry,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("spectacular_comparison")

DATASET_PATH = str(
    project_root / "argumentation_analysis" / "data" / "extract_sources.json.gz.enc"
)

RESULTS_DIR = project_root / "argumentation_analysis" / "evaluation" / "results"
REPORTS_DIR = project_root / "docs" / "reports"

OPAQUE_IDS = {0: "doc_A", 1: "doc_B", 2: "doc_C", 3: "doc_D", 4: "doc_E", 5: "doc_F"}

WORKFLOWS = ["standard", "spectacular"]


def _opaque(doc_index: int) -> str:
    return OPAQUE_IDS.get(doc_index, f"doc_{doc_index}")


def _count_populated_fields(state: Optional[Dict[str, Any]]) -> int:
    """Count non-empty fields in a state snapshot."""
    if not state:
        return 0

    # Fields that indicate populated analysis results
    field_keys = [
        "identified_arguments",
        "identified_fallacies",
        "belief_sets",
        "extracts",
        "counter_arguments",
        "argument_quality_scores",
        "jtms_beliefs",
        "jtms_retraction_chain",
        "dung_frameworks",
        "governance_decisions",
        "debate_transcripts",
        "neural_fallacy_scores",
        "ranking_results",
        "aspic_results",
        "fol_analysis_results",
        "propositional_analysis_results",
        "modal_analysis_results",
        "formal_synthesis_reports",
        "nl_to_logic_translations",
        "atms_contexts",
        "narrative_synthesis",
        "final_conclusion",
        "answers",
        "query_log",
        "belief_revision_results",
        "dialogue_results",
        "probabilistic_results",
        "bipolar_results",
        "fol_signature",
        "workflow_results",
        "semantic_index_refs",
        "transcription_segments",
    ]
    count = 0
    for key in field_keys:
        val = state.get(key)
        if val is None:
            continue
        if isinstance(val, (list, dict, str)) and len(val) > 0:
            count += 1
        elif isinstance(val, bool) and val:
            count += 1
        elif isinstance(val, (int, float)) and val != 0:
            count += 1
    return count


def _extract_metrics(state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Extract key metrics from a state snapshot."""
    if not state:
        return {}

    fallacies = state.get("identified_fallacies", {})
    neural = state.get("neural_fallacy_scores", [])
    fol = state.get("fol_analysis_results", [])
    jtms_beliefs = state.get("jtms_beliefs", {})
    jtms_chain = state.get("jtms_retraction_chain", [])
    atms = state.get("atms_contexts", [])
    dung = state.get("dung_frameworks", {})
    narrative = state.get("narrative_synthesis", "")
    counter = state.get("counter_arguments", [])
    quality = state.get("argument_quality_scores", {})
    governance = state.get("governance_decisions", [])
    debate = state.get("debate_transcripts", [])

    return {
        "populated_fields": _count_populated_fields(state),
        "total_fields": 32,
        "field_coverage_pct": round(
            _count_populated_fields(state) / 32 * 100, 1
        ),
        "arguments_count": len(state.get("identified_arguments", {})),
        "fallacies_count": len(fallacies),
        "neural_fallacy_count": len(neural),
        "fol_formulas_count": len(fol),
        "fol_signature_count": len(state.get("fol_signature", [])),
        "jtms_belief_count": len(jtms_beliefs),
        "jtms_retraction_cascades": len(jtms_chain),
        "atms_hypotheses_count": len(atms),
        "dung_frameworks_count": len(dung),
        "counter_arguments_count": len(counter),
        "quality_scores_count": len(quality),
        "governance_decisions_count": len(governance),
        "debate_transcripts_count": len(debate),
        "narrative_present": bool(narrative and len(narrative.strip()) > 0),
        "narrative_length": len(narrative) if narrative else 0,
        "state_size_kb": round(
            len(json.dumps(state, default=str)) / 1024, 1
        ),
    }


async def run_comparison(
    doc_indices: List[int],
    model_name: str = "default",
    timeout: float = 600.0,
    max_text_chars: int = 3000,
) -> List[Dict[str, Any]]:
    """Run standard and spectacular workflows on specified docs."""
    registry = ModelRegistry.from_env()
    runner = BenchmarkRunner(registry)

    passphrase = os.getenv("TEXT_CONFIG_PASSPHRASE")
    if not passphrase:
        logger.error("TEXT_CONFIG_PASSPHRASE not set")
        return []

    runner.load_dataset_encrypted(DATASET_PATH, passphrase)
    total_docs = len(runner.dataset)
    logger.info(f"Dataset: {total_docs} documents")

    valid_docs = [i for i in doc_indices if i < total_docs]
    if not valid_docs:
        logger.error(f"No valid doc indices (max: {total_docs - 1})")
        return []

    results = []
    for wf in WORKFLOWS:
        for doc_idx in valid_docs:
            doc_name = _opaque(doc_idx)
            logger.info(f"Running {wf} × {doc_name}...")

            start_wall = time.monotonic()
            result = await runner.run_cell(
                workflow_name=wf,
                model_name=model_name,
                document_index=doc_idx,
                max_text_chars=max_text_chars,
                timeout=timeout,
            )
            wall_clock = time.monotonic() - start_wall

            metrics = _extract_metrics(result.state_snapshot)

            entry = {
                "workflow": wf,
                "doc_id": doc_name,
                "doc_index": doc_idx,
                "success": result.success,
                "wall_clock_s": round(wall_clock, 1),
                "phases_completed": result.phases_completed,
                "phases_total": result.phases_total,
                "state_size_kb": metrics.get("state_size_kb", 0),
                "metrics": metrics,
                "error": result.error,
            }
            results.append(entry)

            status = "OK" if result.success else f"FAIL: {result.error}"
            logger.info(
                f"  -> {status} ({wall_clock:.1f}s, "
                f"{result.phases_completed}/{result.phases_total} phases, "
                f"{metrics.get('populated_fields', 0)}/32 fields)"
            )

    return results


def generate_comparison_report(results: List[Dict[str, Any]]) -> str:
    """Generate the #366 comparison report (baseline vs spectacular)."""
    lines = [
        "# Spectacular vs Baseline Comparison Report",
        "",
        "Generated from encrypted dataset using opaque IDs only.",
        "",
        "## Overview",
        "",
        "Side-by-side comparison of standard (baseline) and spectacular workflows",
        "on documents from the encrypted corpus.",
        "",
        "| Metric | Standard (Baseline) | Spectacular | Delta |",
        "|--------|--------------------:|------------:|------:|",
    ]

    # Aggregate by workflow
    by_wf: Dict[str, List[Dict]] = {}
    for r in results:
        if not r["success"]:
            continue
        by_wf.setdefault(r["workflow"], []).append(r)

    if "standard" in by_wf and "spectacular" in by_wf:
        std_metrics = _aggregate_metrics(by_wf["standard"])
        spec_metrics = _aggregate_metrics(by_wf["spectacular"])

        rows = [
            ("Avg populated fields", "populated_fields", "/32"),
            ("Field coverage %", "field_coverage_pct", "%"),
            ("Avg fallacies", "fallacies_count", ""),
            ("Avg FOL formulas", "fol_formulas_count", ""),
            ("Avg JTMS beliefs", "jtms_belief_count", ""),
            ("Avg JTMS cascades", "jtms_retraction_cascades", ""),
            ("Avg ATMS hypotheses", "atms_hypotheses_count", ""),
            ("Avg counter-arguments", "counter_arguments_count", ""),
            ("Avg quality scores", "quality_scores_count", ""),
            ("Narrative present", "narrative_present_pct", "%"),
        ]
        for label, key, unit in rows:
            s = std_metrics.get(key, 0)
            sp = spec_metrics.get(key, 0)
            delta = sp - s
            sign = "+" if delta > 0 else ""
            lines.append(
                f"| {label} | {s}{unit} | {sp}{unit} | {sign}{delta}{unit} |"
            )

    # Per-document detail
    lines.extend([
        "",
        "## Per-Document Detail",
        "",
    ])

    docs = sorted(set(r["doc_id"] for r in results))
    for doc_id in docs:
        lines.append(f"### {doc_id}")
        lines.append("")
        lines.append("| Workflow | Fields | Coverage | Fallacies | FOL | JTMS | ATMS | Narrative | Phases |")
        lines.append("|----------|-------:|---------:|----------:|----:|-----:|-----:|:---------|-------:|")

        for r in results:
            if r["doc_id"] != doc_id or not r["success"]:
                continue
            m = r["metrics"]
            narr = "Yes" if m.get("narrative_present") else "No"
            lines.append(
                f"| {r['workflow']} | {m.get('populated_fields', 0)}/32 | "
                f"{m.get('field_coverage_pct', 0)}% | "
                f"{m.get('fallacies_count', 0)} | {m.get('fol_formulas_count', 0)} | "
                f"{m.get('jtms_belief_count', 0)} | {m.get('atms_hypotheses_count', 0)} | "
                f"{narr} | {r['phases_completed']}/{r['phases_total']} |"
            )
        lines.append("")

    # Verdict
    lines.extend([
        "## Verdict",
        "",
    ])
    if "standard" in by_wf and "spectacular" in by_wf:
        std_avg = _aggregate_metrics(by_wf["standard"])
        spec_avg = _aggregate_metrics(by_wf["spectacular"])
        std_cov = std_avg.get("field_coverage_pct", 0)
        spec_cov = spec_avg.get("field_coverage_pct", 0)
        if spec_cov > std_cov:
            ratio = spec_cov / std_cov if std_cov > 0 else float("inf")
            lines.append(
                f"Spectacular workflow achieves **{ratio:.1f}x** higher field coverage "
                f"({spec_cov}% vs {std_cov}%)."
            )
            if spec_avg.get("narrative_present_pct", 0) > 0:
                lines.append(
                    "Narrative synthesis provides coherent multi-perspective summaries."
                )
            if spec_avg.get("atms_hypotheses_count", 0) > 0:
                lines.append(
                    "ATMS multi-context analysis enables explicit hypothesis branching."
                )
        else:
            lines.append("Spectacular workflow did not show significant improvement over baseline.")
    else:
        lines.append("Insufficient data for verdict (check errors above).")

    lines.append("")
    return "\n".join(lines)


def generate_perf_report(results: List[Dict[str, Any]]) -> str:
    """Generate the #367 performance benchmark report."""
    lines = [
        "# Spectacular Performance Benchmark",
        "",
        "Performance comparison: wall-clock time and state size for standard vs spectacular.",
        "Opaque IDs only.",
        "",
        "## Summary",
        "",
        "| Workflow | Docs | Avg Time (s) | Max Time (s) | Avg State Size (KB) | Avg Fields |",
        "|----------|-----:|-------------:|-------------:|--------------------:|-----------:|",
    ]

    for wf in WORKFLOWS:
        wf_results = [r for r in results if r["workflow"] == wf and r["success"]]
        if not wf_results:
            lines.append(f"| {wf} | 0 | - | - | - | - |")
            continue
        times = [r["wall_clock_s"] for r in wf_results]
        sizes = [r["metrics"].get("state_size_kb", 0) for r in wf_results]
        fields = [r["metrics"].get("populated_fields", 0) for r in wf_results]
        avg_t = sum(times) / len(times)
        max_t = max(times)
        avg_s = sum(sizes) / len(sizes)
        avg_f = sum(fields) / len(fields)
        lines.append(
            f"| {wf} | {len(wf_results)} | "
            f"{avg_t:.1f} | {max_t:.1f} | {avg_s:.1f} | {avg_f:.1f} |"
        )

    lines.extend([
        "",
        "## Per-Cell Detail",
        "",
        "| Workflow | Doc | Time (s) | Phases | State Size (KB) | Fields | Status |",
        "|----------|-----|---------:|-------:|----------------:|-------:|--------|",
    ])

    for r in sorted(results, key=lambda x: (x["workflow"], x["doc_id"])):
        status = "OK" if r["success"] else f"FAIL: {r.get('error', 'unknown')[:30]}"
        m = r["metrics"]
        lines.append(
            f"| {r['workflow']} | {r['doc_id']} | {r['wall_clock_s']:.1f} | "
            f"{r['phases_completed']}/{r['phases_total']} | "
            f"{m.get('state_size_kb', 0):.1f} | {m.get('populated_fields', 0)}/32 | "
            f"{status} |"
        )

    lines.extend(["", "## Notes", ""])
    lines.append("- Wall-clock includes all phases (extraction, analysis, synthesis).")
    lines.append("- State size measured as JSON serialization of UnifiedAnalysisState.")
    lines.append("- Token counts are estimated from LLM service logs (not directly tracked).")
    lines.append("- Timeout per cell: 600s.")
    lines.append("")
    return "\n".join(lines)


def _aggregate_metrics(results: List[Dict]) -> Dict[str, float]:
    """Average metrics across multiple results."""
    if not results:
        return {}

    metrics_list = [r["metrics"] for r in results if r.get("metrics")]
    if not metrics_list:
        return {}

    numeric_keys = [
        "populated_fields", "field_coverage_pct", "fallacies_count",
        "fol_formulas_count", "jtms_belief_count", "jtms_retraction_cascades",
        "atms_hypotheses_count", "counter_arguments_count", "quality_scores_count",
    ]

    avg = {}
    for key in numeric_keys:
        vals = [m.get(key, 0) for m in metrics_list if isinstance(m.get(key), (int, float))]
        avg[key] = round(sum(vals) / len(vals), 1) if vals else 0

    # Narrative presence as percentage
    narr = sum(1 for m in metrics_list if m.get("narrative_present"))
    avg["narrative_present_pct"] = round(narr / len(metrics_list) * 100, 0)

    return avg


def save_results(results: List[Dict[str, Any]]) -> Path:
    """Save raw results to JSONL."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    path = RESULTS_DIR / f"spectacular_comparison_{ts}.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, default=str) + "\n")
    logger.info(f"Results saved to {path}")
    return path


def load_results(path: str) -> List[Dict[str, Any]]:
    """Load results from JSONL file."""
    results = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                results.append(json.loads(line))
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Run spectacular vs baseline comparison (#366, #367)"
    )
    parser.add_argument(
        "--docs", nargs="+", type=int, default=[0, 1, 2],
        help="Document indices (default: 0 1 2 = doc_A doc_B doc_C)",
    )
    parser.add_argument("--model", default="default", help="Model name")
    parser.add_argument(
        "--timeout", type=float, default=600.0, help="Timeout per cell (s)"
    )
    parser.add_argument(
        "--max-text", type=int, default=3000, help="Max chars of input text"
    )
    parser.add_argument(
        "--report-only", action="store_true",
        help="Generate reports from latest cached results",
    )
    parser.add_argument(
        "--from-file", type=str, help="Load results from JSONL file",
    )

    args = parser.parse_args()

    if args.report_only:
        result_files = sorted(RESULTS_DIR.glob("spectacular_comparison_*.jsonl"))
        if not result_files:
            logger.error("No cached results found")
            sys.exit(1)
        latest = result_files[-1]
        logger.info(f"Using cached results: {latest}")
        results = load_results(str(latest))
    elif args.from_file:
        results = load_results(args.from_file)
    else:
        results = asyncio.run(run_comparison(
            doc_indices=args.docs,
            model_name=args.model,
            timeout=args.timeout,
            max_text_chars=args.max_text,
        ))
        if results:
            save_results(results)

    if not results:
        logger.error("No results to generate reports from")
        sys.exit(1)

    # Generate reports
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    comp_path = REPORTS_DIR / "spectacular_vs_baseline.md"
    comp_path.write_text(generate_comparison_report(results), encoding="utf-8")
    logger.info(f"Comparison report: {comp_path}")

    perf_path = REPORTS_DIR / "spectacular_perf_bench.md"
    perf_path.write_text(generate_perf_report(results), encoding="utf-8")
    logger.info(f"Performance report: {perf_path}")


if __name__ == "__main__":
    main()
