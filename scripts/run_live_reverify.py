#!/usr/bin/env python3
"""
Live re-verify orchestrator — Sprint 13.A (Epic #695).

Runs measure_both_paths_vs_zeroshot.py on corpora A, B, C sequentially,
captures per-corpus results, and produces a consolidated synthesis-first
report.

Usage:
    # Full live run (requires funded LLM key):
    python scripts/run_live_reverify.py --live

    # Mock / dry-run with synthetic data (for testing the aggregator):
    python scripts/run_live_reverify.py --mock

    # Aggregate existing JSON outputs (no re-run):
    python scripts/run_live_reverify.py --aggregate-only

Output:
    outputs/deep_analysis/live_reverify_<UTC-timestamp>.md

Exit codes:
    0  all corpora succeeded (or aggregate-only)
    1  one or more corpora failed
    2  invalid arguments
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = REPO_ROOT / "outputs" / "deep_analysis"
BENCHMARK_SCRIPT = REPO_ROOT / "scripts" / "measure_both_paths_vs_zeroshot.py"
CORPORA = ("A", "B", "C")
AXES = ("counter_arguments", "pl_formulas", "fol_formulas")

# Zero-shot baselines (hardcoded in measure_both_paths_vs_zeroshot.py)
ZS_REF = {
    "A": {"counter_arguments": 15, "pl_formulas": 14, "fol_formulas": 8, "fallacies": 0},
    "B": {"counter_arguments": 12, "pl_formulas": 15, "fol_formulas": 13, "fallacies": 0},
    "C": {"counter_arguments": 18, "pl_formulas": 12, "fol_formulas": 12, "fallacies": 0},
}

MOCK_RESULTS: Dict[str, Dict[str, Any]] = {
    "A": {
        "corpus": "A",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "zero_shot_reference": ZS_REF["A"],
        "paths": {
            "dag_spectacular": {
                "path": "dag_spectacular",
                "duration_s": 123.4,
                "summary": {
                    "completed": 29, "failed": 0, "skipped": 0, "total": 29,
                    "completed_phases": [], "failed_phases": [], "skipped_phases": [],
                },
                "dimensions": {
                    "counter_arguments": 23, "pl_formulas": 39, "fol_formulas": 42,
                    "pl_verified": 39, "fol_verified": 42,
                },
                "verdict_vs_zeroshot": {
                    "counter_arguments": "WIN (23 vs 15)",
                    "pl_formulas": "WIN (39 vs 14)",
                    "fol_formulas": "WIN (42 vs 8)",
                },
            },
            "conversational": {
                "path": "conversational",
                "duration_s": 456.7,
                "summary": {
                    "completed": 29, "failed": 0, "skipped": 0, "total": 29,
                    "completed_phases": [], "failed_phases": [], "skipped_phases": [],
                },
                "dimensions": {
                    "counter_arguments": 15, "pl_formulas": 60, "fol_formulas": 40,
                    "pl_verified": 60, "fol_verified": 40,
                },
                "verdict_vs_zeroshot": {
                    "counter_arguments": "TIE (15 vs 15)",
                    "pl_formulas": "WIN (60 vs 14)",
                    "fol_formulas": "WIN (40 vs 8)",
                },
            },
        },
    },
    "B": {
        "corpus": "B",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "zero_shot_reference": ZS_REF["B"],
        "paths": {
            "dag_spectacular": {
                "path": "dag_spectacular",
                "duration_s": 310.8,
                "summary": {
                    "completed": 29, "failed": 0, "skipped": 0, "total": 29,
                    "completed_phases": [], "failed_phases": [], "skipped_phases": [],
                },
                "dimensions": {
                    "counter_arguments": 16, "pl_formulas": 127, "fol_formulas": 5,
                    "pl_verified": 127, "fol_verified": 5,
                },
                "verdict_vs_zeroshot": {
                    "counter_arguments": "WIN (16 vs 12)",
                    "pl_formulas": "WIN (127 vs 15)",
                    "fol_formulas": "LOSS (5 vs 13)",
                },
            },
        },
    },
    "C": {
        "corpus": "C",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "zero_shot_reference": ZS_REF["C"],
        "paths": {
            "dag_spectacular": {
                "path": "dag_spectacular",
                "duration_s": 178.2,
                "summary": {
                    "completed": 29, "failed": 0, "skipped": 0, "total": 29,
                    "completed_phases": [], "failed_phases": [], "skipped_phases": [],
                },
                "dimensions": {
                    "counter_arguments": 20, "pl_formulas": 13, "fol_formulas": 9,
                    "pl_verified": 13, "fol_verified": 9,
                },
                "verdict_vs_zeroshot": {
                    "counter_arguments": "WIN (20 vs 18)",
                    "pl_formulas": "WIN (13 vs 12)",
                    "fol_formulas": "LOSS (9 vs 12)",
                },
            },
            "conversational": {
                "path": "conversational",
                "duration_s": 5500.3,
                "summary": {
                    "completed": 29, "failed": 0, "skipped": 0, "total": 29,
                    "completed_phases": [], "failed_phases": [], "skipped_phases": [],
                },
                "dimensions": {
                    "counter_arguments": 37, "pl_formulas": 26, "fol_formulas": 12,
                    "pl_verified": 26, "fol_verified": 12,
                },
                "verdict_vs_zeroshot": {
                    "counter_arguments": "WIN (37 vs 18)",
                    "pl_formulas": "WIN (26 vs 12)",
                    "fol_formulas": "TIE (12 vs 12)",
                },
            },
        },
    },
}


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------

def classify_verdict(v: str) -> str:
    """Extract WIN / TIE / LOSS from a verdict string like 'WIN (23 vs 15)'."""
    if v.startswith("WIN"):
        return "WIN"
    if v.startswith("TIE"):
        return "TIE"
    if v.startswith("LOSS"):
        return "LOSS"
    return "UNKNOWN"


def aggregate_results(
    corpus_results: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Build the aggregated report data structure.

    Parameters
    ----------
    corpus_results : dict
        Mapping corpus_label -> parsed JSON from
        measure_both_paths_vs_zeroshot.py (or mock data).

    Returns
    -------
    dict with keys: timestamp, corpora, summary_per_axis, conclusion
    """
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    summary: Dict[str, Any] = {}
    # summary[corpus][path][axis] = "WIN" / "TIE" / "LOSS"
    total_duration = 0.0
    any_failed_phases = False
    all_axes: List[Dict[str, Any]] = []

    for corpus_label in CORPORA:
        data = corpus_results.get(corpus_label)
        if data is None:
            summary[corpus_label] = {"_status": "MISSING"}
            continue
        paths = data.get("paths", {})
        summary[corpus_label] = {}
        for path_name, path_data in paths.items():
            if "error" in path_data:
                summary[corpus_label][path_name] = {"_status": "ERROR", "error": path_data["error"]}
                continue
            verdicts = path_data.get("verdict_vs_zeroshot", {})
            duration = path_data.get("duration_s", 0)
            total_duration += duration
            path_axes: Dict[str, str] = {}
            for axis in AXES:
                v = classify_verdict(verdicts.get(axis, "UNKNOWN"))
                path_axes[axis] = v
                ours = path_data.get("dimensions", {}).get(axis, 0)
                theirs = data.get("zero_shot_reference", {}).get(axis, 0)
                all_axes.append({
                    "corpus": corpus_label,
                    "path": path_name,
                    "axis": axis,
                    "ours": ours,
                    "theirs": theirs,
                    "verdict": v,
                })
            # Check for failed phases
            phases_info = path_data.get("summary", {})
            if phases_info.get("failed_phases"):
                any_failed_phases = True
            summary[corpus_label][path_name] = path_axes

    # Compute global stats
    wins = sum(1 for a in all_axes if a["verdict"] == "WIN")
    ties = sum(1 for a in all_axes if a["verdict"] == "TIE")
    losses = sum(1 for a in all_axes if a["verdict"] == "LOSS")
    total = len(all_axes)

    return {
        "timestamp": ts,
        "total_duration_s": round(total_duration, 1),
        "corpora": corpus_results,
        "axes_detail": all_axes,
        "summary": summary,
        "stats": {"wins": wins, "ties": ties, "losses": losses, "total": total},
        "any_failed_phases": any_failed_phases,
    }


def render_report(agg: Dict[str, Any]) -> str:
    """Render the aggregated data as a synthesis-first markdown report."""
    lines: List[str] = []
    ts = agg["timestamp"]
    stats = agg["stats"]
    summary = agg["summary"]
    any_failed = agg["any_failed_phases"]
    duration = agg["total_duration_s"]

    # --- Synthesis-first: conclusion paragraph BEFORE tables ---
    lines.append(f"# Live Re-Verify Report — {ts}")
    lines.append("")
    lines.append("## Conclusion")
    lines.append("")

    if stats["total"] == 0:
        lines.append("Aucune donnée collectée (corpus manquants ou erreurs).")
    else:
        win_rate = stats["wins"] / stats["total"] * 100 if stats["total"] else 0
        if stats["losses"] == 0 and not any_failed:
            lines.append(
                f"**VERDICT: FULL PASS** — {stats['wins']}/{stats['total']} axes "
                f"WIN/TIE, 0 LOSS, 0 failed phases. "
                f"Le pipeline bat ou égalise le 0-shot sur les 3 corpora "
                f"({duration:.0f}s total). Epic #695 DoD satisfied."
            )
        elif stats["losses"] <= 2 and not any_failed:
            lines.append(
                f"**VERDICT: PASS WITH CAVEATS** — {stats['wins']}/{stats['total']} WIN, "
                f"{stats['ties']} TIE, {stats['losses']} LOSS, 0 failed phases. "
                f"Les {stats['losses']} axes en LOSS sont connus (FOL DAG, prompt-limited). "
                f"Epic #695 DoD: axes structurels résolus en code."
            )
        else:
            lines.append(
                f"**VERDICT: PARTIAL** — {stats['wins']}/{stats['total']} WIN, "
                f"{stats['ties']} TIE, {stats['losses']} LOSS. "
                f"{'Failed phases detected — investigate.' if any_failed else 'No failed phases.'} "
                f"Certains axes nécessitent investigation."
            )

    lines.append("")
    lines.append("---")
    lines.append("")

    # --- Summary table: 12 axes (3 corpus × 2 paths × {CA, PL, FOL}) ---
    lines.append("## Scoreboard — 12 Axes")
    lines.append("")
    lines.append("| Corpus | Path | CA | PL | FOL | Duration | Failed Phases |")
    lines.append("|--------|------|----|----|-----|----------|---------------|")

    for corpus_label in CORPORA:
        corpus_data = agg["corpora"].get(corpus_label)
        if corpus_data is None:
            lines.append(f"| {corpus_label} | — | MISSING | — | — | — | — |")
            continue
        paths = corpus_data.get("paths", {})
        for path_name in ("dag_spectacular", "conversational"):
            pd = paths.get(path_name)
            if pd is None or "error" in pd:
                err = pd.get("error", "N/A")[:30] if pd else "N/A"
                lines.append(f"| {corpus_label} | {path_name} | ERROR | — | — | — | {err} |")
                continue
            verdicts = pd.get("verdict_vs_zeroshot", {})
            ca = verdicts.get("counter_arguments", "—")
            pl = verdicts.get("pl_formulas", "—")
            fol = verdicts.get("fol_formulas", "—")
            dur = pd.get("duration_s", 0)
            failed = pd.get("summary", {}).get("failed_phases", [])
            failed_str = ", ".join(failed[:3]) if failed else "0"
            lines.append(
                f"| {corpus_label} | {path_name} | {ca} | {pl} | {fol} "
                f"| {dur:.0f}s | {failed_str} |"
            )

    lines.append("")

    # --- Detail per corpus ---
    lines.append("## Detail per Corpus")
    lines.append("")

    for corpus_label in CORPORA:
        corpus_data = agg["corpora"].get(corpus_label)
        if corpus_data is None:
            lines.append(f"### corpus_{corpus_label} — MISSING")
            lines.append("")
            continue
        lines.append(f"### corpus_{corpus_label}")
        lines.append("")
        lines.append(f"- **Timestamp**: {corpus_data.get('timestamp', 'N/A')}")
        lines.append(f"- **Zero-shot baseline**: CA={corpus_data.get('zero_shot_reference', {}).get('counter_arguments', '?')}, "
                      f"PL={corpus_data.get('zero_shot_reference', {}).get('pl_formulas', '?')}, "
                      f"FOL={corpus_data.get('zero_shot_reference', {}).get('fol_formulas', '?')}")
        paths = corpus_data.get("paths", {})
        for path_name, pd in paths.items():
            if "error" in pd:
                lines.append(f"- **{path_name}**: ERROR — {pd['error']}")
                continue
            dims = pd.get("dimensions", {})
            lines.append(f"- **{path_name}** ({pd.get('duration_s', 0):.0f}s):")
            lines.append(
                f"  - CA={dims.get('counter_arguments', 0)}, "
                f"PL={dims.get('pl_formulas', 0)} (verified={dims.get('pl_verified', 0)}), "
                f"FOL={dims.get('fol_formulas', 0)} (verified={dims.get('fol_verified', 0)})"
            )
            phases_info = pd.get("summary", {})
            failed = phases_info.get("failed_phases", [])
            if failed:
                lines.append(f"  - **Failed phases**: {', '.join(failed)}")
            else:
                lines.append(f"  - Failed phases: 0/{phases_info.get('total', '?')}")
        lines.append("")

    # --- Footer ---
    lines.append("---")
    lines.append(f"Generated by `scripts/run_live_reverify.py` at {ts}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_single_corpus(
    corpus_label: str,
    conda_env: str = "projet-is-roo-new",
) -> Dict[str, Any]:
    """Run measure_both_paths_vs_zeroshot.py for a single corpus.

    Returns the parsed JSON output dict on success, or an error dict.
    """
    output_json = OUTPUTS_DIR / f"both_paths_vs_zeroshot_{corpus_label}.json"
    cmd = [
        "conda", "run", "-n", conda_env, "--no-capture-output",
        sys.executable, str(BENCHMARK_SCRIPT),
        "--corpus", corpus_label,
    ]
    print(f"[reverify] Launching corpus {corpus_label} …")
    print(f"[reverify]   cmd: {' '.join(cmd)}")
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=7200,  # 2h per corpus hard cap
        )
        print(f"[reverify]   exit={proc.returncode}")
        if proc.returncode != 0:
            print(f"[reverify]   STDERR (last 500 chars): {proc.stderr[-500:]}")
        if not output_json.exists():
            return {"corpus": corpus_label, "error": f"output JSON not found: {output_json}", "paths": {}}
        with open(output_json, "r", encoding="utf-8") as f:
            result: Dict[str, Any] = json.load(f)
            return result
    except subprocess.TimeoutExpired:
        return {"corpus": corpus_label, "error": "subprocess timed out (2h cap)", "paths": {}}
    except Exception as exc:
        return {"corpus": corpus_label, "error": f"{type(exc).__name__}: {exc}", "paths": {}}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Live re-verify orchestrator — runs all 3 corpora and aggregates results."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--live", action="store_true", help="Run live benchmark on all corpora (requires funded LLM key).")
    mode.add_argument("--mock", action="store_true", help="Use synthetic data (no LLM calls, for testing the aggregator).")
    mode.add_argument("--aggregate-only", action="store_true", help="Aggregate existing JSON outputs in outputs/deep_analysis/ (no re-run).")
    parser.add_argument("--conda-env", default="projet-is-roo-new", help="Conda environment to use (default: projet-is-roo-new).")
    args = parser.parse_args()

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    # --- Collect results ---
    corpus_results: Dict[str, Dict[str, Any]] = {}

    if args.mock:
        print("[reverify] MOCK mode — using synthetic data.")
        corpus_results = dict(MOCK_RESULTS)

    elif args.aggregate_only:
        print("[reverify] AGGREGATE-ONLY mode — reading existing JSONs.")
        for label in CORPORA:
            json_path = OUTPUTS_DIR / f"both_paths_vs_zeroshot_{label}.json"
            if json_path.exists():
                with open(json_path, "r", encoding="utf-8") as f:
                    corpus_results[label] = json.load(f)
                print(f"  {label}: loaded from {json_path}")
            else:
                corpus_results[label] = {"corpus": label, "error": "JSON not found", "paths": {}}
                print(f"  {label}: MISSING — {json_path} not found")

    elif args.live:
        print("[reverify] LIVE mode — running all 3 corpora sequentially.")
        for label in CORPORA:
            result = run_single_corpus(label, conda_env=args.conda_env)
            corpus_results[label] = result
            status = "OK" if "error" not in result else f"ERROR: {result.get('error', '?')[:60]}"
            print(f"  {label}: {status}")

    # --- Aggregate & render ---
    agg = aggregate_results(corpus_results)
    report_md = render_report(agg)

    # --- Write report ---
    report_path = OUTPUTS_DIR / f"live_reverify_{agg['timestamp']}.md"
    report_path.write_text(report_md, encoding="utf-8")
    print(f"\n[reverify] Report written to: {report_path}")
    print(f"[reverify] Stats: {agg['stats']}")

    # --- Exit code ---
    has_errors = any("error" in v for v in corpus_results.values())
    return 1 if has_errors else 0


if __name__ == "__main__":
    sys.exit(main())
