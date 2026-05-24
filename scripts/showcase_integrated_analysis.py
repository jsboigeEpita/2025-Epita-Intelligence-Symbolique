#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Showcase: complete integrated analysis on corpora A/B/C.

Runs BOTH orchestration paths per corpus:
  1. Sequential `full` workflow (run_unified_analysis) — formal logic, Tweety, JTMS
  2. Spectacular conversational (run_conversational_analysis) — high-recall fallacies, debate

Outputs privacy-clean state snapshots under outputs/showcase_ff/ (gitignored).
The integrated report is assembled separately from those snapshots.

Usage:
    conda run -n projet-is-roo-new --no-capture-output \
        python scripts/showcase_integrated_analysis.py [--corpus A B C] [--skip-sequential] [--skip-spectacular]
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))


def bootstrap_env() -> None:
    os.chdir(_PROJECT_ROOT)
    env_path = _PROJECT_ROOT / ".env"
    if env_path.exists():
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    os.environ.setdefault(key.strip(), val.strip())


CORPORA = {
    "A": {"src_idx": 11, "label": "corpus_dense_A", "desc": "EN dense (~58K)"},
    "B": {"src_idx": 3, "label": "corpus_dense_B", "desc": "DE dense (~50K)"},
    "C": {"src_idx": 2, "label": "corpus_dense_C", "desc": "EN dense (~46K)"},
}


def load_corpus_text(corpus_id: str) -> str:
    from argumentation_analysis.core.utils.crypto_utils import derive_encryption_key
    from argumentation_analysis.core.io_manager import load_extract_definitions

    info = CORPORA[corpus_id]
    passphrase = os.environ.get("TEXT_CONFIG_PASSPHRASE", "")
    if not passphrase:
        print("ERROR: TEXT_CONFIG_PASSPHRASE not set")
        sys.exit(1)

    key = derive_encryption_key(passphrase)
    defs = load_extract_definitions(
        _PROJECT_ROOT / "argumentation_analysis" / "data" / "extract_sources.json.gz.enc",
        key,
    )
    src = defs[info["src_idx"]]
    text = src.get("full_text", "")
    return text


def get_output_dir(corpus_id: str) -> Path:
    d = _PROJECT_ROOT / "outputs" / "showcase_ff" / CORPORA[corpus_id]["label"]
    d.mkdir(parents=True, exist_ok=True)
    return d


def privacy_clean_snapshot(snapshot: Any) -> Dict[str, Any]:
    """Strip raw text fields from state snapshot, keep only metrics and typed results."""
    if not isinstance(snapshot, dict):
        return {}
    clean = {}
    for key in (
        "identified_arguments", "identified_fallacies", "jtms_beliefs",
        "counter_arguments", "dung_frameworks", "aspic_analyses",
        "fol_formulas", "pl_formulas", "modal_analyses", "belief_revisions",
        "formal_category_details", "convergence_signals", "convergence_depth",
        "governance_outcomes", "debate_results", "quality_scores",
        "balance_score", "cross_reference_graph", "extraction_method",
    ):
        val = snapshot.get(key)
        if val is not None:
            clean[key] = val
    return clean


def extract_metrics_from_state(state: Any, path: str) -> Dict[str, Any]:
    """Extract headline metrics from a UnifiedAnalysisState or snapshot."""
    snap = {}
    if state is not None:
        if hasattr(state, "get_state_snapshot"):
            snap = state.get_state_snapshot(summarize=False)
        elif isinstance(state, dict):
            snap = state

    metrics = {
        "path": path,
        "arguments_found": 0,
        "fallacies_found": 0,
        "unique_formal_categories": 0,
        "jtms_beliefs": 0,
        "counter_arguments": 0,
        "convergence_signals": {},
        "convergence_depth": 0,
        "formal_category_details": [],
        "fallacy_details": [],
        "extraction_method": None,
    }

    args = snap.get("identified_arguments") or {}
    metrics["arguments_found"] = len(args) if isinstance(args, dict) else len(args) if isinstance(args, list) else 0

    fallacies = snap.get("identified_fallacies") or []
    if isinstance(fallacies, dict):
        fallacies = list(fallacies.values())
    metrics["fallacies_found"] = len(fallacies)
    import re as _re
    for f in fallacies:
        if isinstance(f, dict):
            ftype = f.get("fallacy_type") or f.get("type") or "unknown"
            # Parse embedded [taxonomy:PK] [confidence:N] from justification
            just = f.get("justification", "")
            pk_match = _re.search(r"\[taxonomy:([^\]]+)\]", just)
            conf_match = _re.search(r"\[confidence:([0-9.]+)\]", just)
            target_match = _re.search(r"\[target_arg:([^\]]+)\]", just)
            metrics["fallacy_details"].append({
                "type": ftype,
                "taxonomy_pk": pk_match.group(1) if pk_match else f.get("taxonomy_pk"),
                "confidence": float(conf_match.group(1)) if conf_match else f.get("confidence"),
                "target_arg_id": f.get("target_argument_id") or target_match.group(1) if target_match else f.get("target_argument_id"),
            })

    jtms = snap.get("jtms_beliefs") or []
    if isinstance(jtms, dict):
        jtms = list(jtms.values())
    metrics["jtms_beliefs"] = len(jtms)
    metrics["jtms_retracted"] = sum(
        1 for b in jtms if isinstance(b, dict) and b.get("valid") is False
    )

    counters = snap.get("counter_arguments") or []
    metrics["counter_arguments"] = len(counters)

    categories = set()
    for attr in (
        "dung_frameworks", "aspic_analyses", "fol_formulas",
        "pl_formulas", "modal_analyses", "belief_revisions",
    ):
        val = snap.get(attr)
        if val:
            categories.add(attr)
            metrics["formal_category_details"].append(attr)
    metrics["unique_formal_categories"] = len(categories)

    metrics["convergence_signals"] = snap.get("convergence_signals") or {}
    metrics["convergence_depth"] = snap.get("convergence_depth") or 0
    metrics["extraction_method"] = snap.get("extraction_method")

    # Compute convergence signals from state if not already set
    if not metrics["convergence_signals"]:
        signals = {}
        if metrics["fallacies_found"] > 0:
            signals["sophisme"] = True
        if metrics["counter_arguments"] > 0:
            signals["contre_argument"] = True
        if metrics["jtms_retracted"] > 0:
            signals["jtms_retracte"] = True
        dung = snap.get("dung_frameworks")
        if dung and isinstance(dung, dict):
            for dk, dv in dung.items():
                if isinstance(dv, dict) and dv.get("extensions"):
                    signals["rejet_dung"] = True
                    break
        metrics["convergence_signals"] = signals
        metrics["convergence_depth"] = len(signals)

    return metrics


async def run_sequential_full(text: str) -> Dict[str, Any]:
    """Run the sequential `full` workflow."""
    from argumentation_analysis.orchestration.unified_pipeline import run_unified_analysis

    result = await run_unified_analysis(
        text=text,
        workflow_name="full",
    )
    return result


async def run_spectacular(text: str) -> Dict[str, Any]:
    """Run the spectacular conversational analysis."""
    from argumentation_analysis.orchestration.conversational_orchestrator import (
        run_conversational_analysis,
    )

    result = await run_conversational_analysis(
        text=text,
        max_turns_per_phase=10,
        spectacular=True,
    )
    return result


async def run_corpus(corpus_id: str, skip_seq: bool, skip_spec: bool) -> Dict[str, Any]:
    """Run both paths on a single corpus and collect metrics."""
    info = CORPORA[corpus_id]
    print(f"\n{'='*60}")
    print(f" Corpus {corpus_id}: {info['label']} ({info['desc']})")
    print(f"{'='*60}")

    text = load_corpus_text(corpus_id)
    print(f"  Loaded {len(text):,} characters")

    out_dir = get_output_dir(corpus_id)
    corpus_result = {
        "corpus_id": corpus_id,
        "label": info["label"],
        "desc": info["desc"],
        "text_length": len(text),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sequential": None,
        "spectacular": None,
    }

    # --- Sequential full path ---
    if not skip_seq:
        print(f"\n  [1/2] Running sequential `full` workflow...")
        t0 = time.time()
        try:
            seq_result = await run_sequential_full(text)
            dur = time.time() - t0
            seq_state = seq_result.get("unified_state")
            seq_metrics = extract_metrics_from_state(seq_state, "sequential_full")
            seq_metrics["duration_seconds"] = round(dur, 1)

            # Save privacy-clean snapshot
            if seq_state and hasattr(seq_state, "get_state_snapshot"):
                snap = seq_state.get_state_snapshot(summarize=False)
                clean = privacy_clean_snapshot(snap)
                with open(out_dir / "sequential_snapshot.json", "w", encoding="utf-8") as f:
                    json.dump(clean, f, indent=2, ensure_ascii=False, default=str)

            # Save summary
            with open(out_dir / "sequential_metrics.json", "w", encoding="utf-8") as f:
                json.dump(seq_metrics, f, indent=2, ensure_ascii=False, default=str)

            corpus_result["sequential"] = seq_metrics
            print(f"    Done in {dur:.1f}s — {seq_metrics['arguments_found']} args, "
                  f"{seq_metrics['fallacies_found']} fallacies, "
                  f"{seq_metrics['unique_formal_categories']} formal categories")
        except Exception as e:
            dur = time.time() - t0
            print(f"    FAILED after {dur:.1f}s: {e}")
            corpus_result["sequential"] = {"error": str(e), "path": "sequential_full"}
    else:
        print(f"  [1/2] Sequential — SKIPPED")

    # --- Spectacular conversational path ---
    if not skip_spec:
        print(f"\n  [2/2] Running spectacular conversational analysis...")
        t0 = time.time()
        try:
            spec_result = await run_spectacular(text)
            dur = time.time() - t0
            spec_state = spec_result.get("unified_state")
            spec_metrics = extract_metrics_from_state(spec_state, "spectacular_conversational")
            spec_metrics["duration_seconds"] = round(dur, 1)

            # Save privacy-clean snapshot
            if spec_state and hasattr(spec_state, "get_state_snapshot"):
                snap = spec_state.get_state_snapshot(summarize=False)
                clean = privacy_clean_snapshot(snap)
                with open(out_dir / "spectacular_snapshot.json", "w", encoding="utf-8") as f:
                    json.dump(clean, f, indent=2, ensure_ascii=False, default=str)

            # Save deep synthesis if available
            deep_synth = spec_result.get("deep_synthesis") or {}
            if deep_synth.get("markdown"):
                with open(out_dir / "deep_synthesis.md", "w", encoding="utf-8") as f:
                    f.write(deep_synth["markdown"])

            with open(out_dir / "spectacular_metrics.json", "w", encoding="utf-8") as f:
                json.dump(spec_metrics, f, indent=2, ensure_ascii=False, default=str)

            corpus_result["spectacular"] = spec_metrics
            print(f"    Done in {dur:.1f}s — {spec_metrics['arguments_found']} args, "
                  f"{spec_metrics['fallacies_found']} fallacies, "
                  f"{spec_metrics['unique_formal_categories']} formal categories")
        except Exception as e:
            dur = time.time() - t0
            print(f"    FAILED after {dur:.1f}s: {e}")
            corpus_result["spectacular"] = {"error": str(e), "path": "spectacular_conversational"}
    else:
        print(f"  [2/2] Spectacular — SKIPPED")

    # Save combined corpus result
    with open(out_dir / "corpus_result.json", "w", encoding="utf-8") as f:
        json.dump(corpus_result, f, indent=2, ensure_ascii=False, default=str)

    return corpus_result


async def main() -> None:
    parser = argparse.ArgumentParser(description="Showcase integrated analysis")
    parser.add_argument("--corpus", nargs="+", default=["A", "B", "C"],
                        choices=["A", "B", "C", "D"])
    parser.add_argument("--skip-sequential", action="store_true")
    parser.add_argument("--skip-spectacular", action="store_true")
    args = parser.parse_args()

    bootstrap_env()

    all_results = []
    for cid in args.corpus:
        result = await run_corpus(cid, args.skip_sequential, args.skip_spectacular)
        all_results.append(result)

    # Save master results
    master_path = _PROJECT_ROOT / "outputs" / "showcase_ff" / "all_results.json"
    master_path.parent.mkdir(parents=True, exist_ok=True)
    with open(master_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False, default=str)

    # Print summary table
    print(f"\n{'='*70}")
    print(f" SHOWCASE INTEGRATED ANALYSIS — SUMMARY")
    print(f"{'='*70}")
    print(f" {'Corpus':<20} {'Path':<15} {'Args':>5} {'Fall':>5} {'Form':>5} {'JTMS':>5} {'Dur':>8}")
    print(f" {'-'*68}")
    for r in all_results:
        for path_key in ("sequential", "spectacular"):
            m = r.get(path_key)
            if m and "error" not in m:
                dur = f"{m.get('duration_seconds', 0):.0f}s"
                print(f" {r['label']:<20} {path_key:<15} "
                      f"{m.get('arguments_found', 0):>5} "
                      f"{m.get('fallacies_found', 0):>5} "
                      f"{m.get('unique_formal_categories', 0):>5} "
                      f"{m.get('jtms_beliefs', 0):>5} {dur:>8}")
            elif m and "error" in m:
                print(f" {r['label']:<20} {path_key:<15} {'ERROR':>5}")
    print(f"{'='*70}")

    # DD live-verify for corpus C
    for r in all_results:
        if r["corpus_id"] == "C":
            seq = r.get("sequential", {})
            if seq and "error" not in seq:
                fallacies = seq.get("fallacies_found", 0)
                targets_resolved = sum(
                    1 for fd in seq.get("fallacy_details", [])
                    if fd.get("target_arg_id")
                )
                print(f"\n DD LIVE-VERIFY (corpus C, sequential path):")
                print(f"   Fallacies found: {fallacies}")
                print(f"   Targets resolved: {targets_resolved}")
                dd_pass = fallacies >= 3 and targets_resolved >= 1
                print(f"   DD DoD (≥3 fallacies, ≥1 target): {'PASS' if dd_pass else 'FAIL'}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
