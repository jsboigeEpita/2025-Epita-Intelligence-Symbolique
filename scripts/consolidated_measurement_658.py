"""Consolidated measurement for Track #658 (MM DoD) + RR verification + signal integrity.

Runs the pipeline on corpus C (smallest, ~46K) to:
  1. Measure formal formula survival (pl_metrics/fol_metrics) — DoD ≥3 formulas
  2. Verify RR — corpus C convergence depth ≥3 post-#670
  3. Signal integrity — per-signal fire counts on all 5 convergence methods

Usage:
    conda run -n projet-is-roo-new --no-capture-output python scripts/consolidated_measurement_658.py

Output: outputs/deep_analysis/corpus_dense_C/consolidated_measurement_658.json
"""

import asyncio
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))
os.chdir(Path(__file__).parent.parent)

_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    with open(_env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())

from argumentation_analysis.core.utils.crypto_utils import derive_encryption_key
from argumentation_analysis.core.io_manager import load_extract_definitions

CORPUS_C = {"src_idx": 2, "label": "corpus_dense_C", "desc": "EN dense (~46K)"}
OUTPUTS_DIR = Path("outputs/deep_analysis")


def load_corpus_c() -> str:
    key = derive_encryption_key(os.environ["TEXT_CONFIG_PASSPHRASE"])
    defs = load_extract_definitions(
        Path("argumentation_analysis/data/extract_sources.json.gz.enc"), key
    )
    src = defs[CORPUS_C["src_idx"]]
    text = src.get("full_text", "")
    if len(text) > 60000:
        text = text[:60000]
    return text


def analyze_signal_integrity(state: Any) -> Dict[str, Any]:
    """Per-signal fire counts across all 5 convergence methods."""
    from argumentation_analysis.plugins.narrative_synthesis_plugin import (
        compute_argument_convergence,
    )

    convergence = compute_argument_convergence(state)

    signal_counts = Counter()
    signal_details = {}
    for arg_id, data in convergence.items():
        for method, detail in data["signals"]:
            signal_counts[method] += 1
            signal_details.setdefault(method, []).append(
                {"arg_id": arg_id, "detail": detail}
            )

    return {
        "total_args_with_signals": len(convergence),
        "signal_fire_counts": dict(signal_counts),
        "max_convergence": max((d["score"] for d in convergence.values()), default=0),
        "per_signal_details": signal_details,
        "all_signals_alive": all(
            signal_counts.get(m, 0) > 0
            for m in [
                "sophisme",
                "qualite faible",
                "contre-argument",
                "JTMS retracte",
                "rejet Dung",
            ]
        ),
    }


def count_state_formulas(state: Any) -> Dict[str, Any]:
    """Count surviving formulas in state PL/FOL results."""
    pl_results = getattr(state, "propositional_analysis_results", []) or []
    fol_results = getattr(state, "fol_analysis_results", []) or []

    pl_formula_count = sum(len(r.get("formulas", [])) for r in pl_results)
    fol_formula_count = sum(len(r.get("formulas", [])) for r in fol_results)

    return {
        "pl_entries": len(pl_results),
        "pl_total_formulas": pl_formula_count,
        "fol_entries": len(fol_results),
        "fol_total_formulas": fol_formula_count,
        "dod_met": pl_formula_count + fol_formula_count >= 3,
        "pl_detail": [
            {
                "id": r.get("id"),
                "formula_count": len(r.get("formulas", [])),
                "satisfiable": r.get("satisfiable"),
            }
            for r in pl_results
        ],
        "fol_detail": [
            {
                "id": r.get("id"),
                "formula_count": len(r.get("formulas", [])),
                "consistent": r.get("consistent"),
            }
            for r in fol_results
        ],
    }


async def run_measurement():
    print("=" * 60)
    print("Consolidated Measurement #658 — Corpus C")
    print("=" * 60)

    text = load_corpus_c()
    print(f"Loaded corpus C: {len(text):,} chars")

    out_dir = OUTPUTS_DIR / CORPUS_C["label"]
    out_dir.mkdir(parents=True, exist_ok=True)

    # Run pipeline
    print("\n--- Running SCDA pipeline (spectacular) ---")
    from argumentation_analysis.orchestration.conversational_orchestrator import (
        run_conversational_analysis,
    )

    start = time.time()
    pipeline_result = await run_conversational_analysis(
        text=text,
        max_turns_per_phase=10,
        spectacular=True,
    )
    duration = time.time() - start
    print(f"Pipeline completed in {duration:.1f}s")

    state = pipeline_result.get("unified_state")

    if not state:
        print("ERROR: No state returned from pipeline")
        return

    # Save state snapshot
    if hasattr(state, "get_state_snapshot"):
        snap = state.get_state_snapshot(summarize=True)
        with open(out_dir / "pipeline_state.json", "w", encoding="utf-8") as f:
            json.dump(snap, f, indent=2, ensure_ascii=False, default=str)

    # Volet 1: Formal formula survival
    print("\n=== VOLET 1: Formal Formula Survival ===")
    formula_analysis = count_state_formulas(state)
    print(
        f"  PL entries: {formula_analysis['pl_entries']}, total formulas: {formula_analysis['pl_total_formulas']}"
    )
    print(
        f"  FOL entries: {formula_analysis['fol_entries']}, total formulas: {formula_analysis['fol_total_formulas']}"
    )
    print(f"  DoD ≥3 formulas met: {formula_analysis['dod_met']}")

    # Volet 2: RR verification — corpus C convergence depth
    print("\n=== VOLET 2: RR Verification — Corpus C Depth ===")
    signal_integrity = analyze_signal_integrity(state)
    max_depth = signal_integrity["max_convergence"]
    print(f"  Max convergence depth: {max_depth}")
    print(f"  Target ≥3: {'PASS' if max_depth >= 3 else 'FAIL'}")

    # Volet 3: Signal integrity
    print("\n=== VOLET 3: Signal Integrity ===")
    for method, count in sorted(signal_integrity["signal_fire_counts"].items()):
        print(f"  {method}: {count} fires")
    print(f"  All 5 signals alive: {signal_integrity['all_signals_alive']}")

    # DeepSynthesis report
    deep_synth_data = pipeline_result.get("deep_synthesis") or {}
    deepsynth_report = deep_synth_data.get("markdown", "")
    if deepsynth_report:
        with open(out_dir / "deepsynth_report.md", "w", encoding="utf-8") as f:
            f.write(deepsynth_report)

    # Compile results
    results = {
        "corpus": "C",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "pipeline_duration_s": round(duration, 1),
        "volet_1_formula_survival": formula_analysis,
        "volet_2_rr_verification": {
            "corpus": "C",
            "max_convergence_depth": max_depth,
            "target_ge3": max_depth >= 3,
            "verdict_count": signal_integrity["total_args_with_signals"],
        },
        "volet_3_signal_integrity": signal_integrity,
        "dod_summary": {
            "mm_dod_ge3_formulas": formula_analysis["dod_met"],
            "rr_depth_ge3": max_depth >= 3,
            "all_signals_alive": signal_integrity["all_signals_alive"],
        },
    }

    with open(
        out_dir / "consolidated_measurement_658.json", "w", encoding="utf-8"
    ) as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    print(f"\nResults saved to {out_dir / 'consolidated_measurement_658.json'}")
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  DoD ≥3 formulas: {'PASS' if formula_analysis['dod_met'] else 'FAIL'}")
    print(f"  RR depth ≥3:     {'PASS' if max_depth >= 3 else 'FAIL'}")
    print(
        f"  All signals:     {'PASS' if signal_integrity['all_signals_alive'] else 'FAIL'}"
    )

    return results


if __name__ == "__main__":
    asyncio.run(run_measurement())
