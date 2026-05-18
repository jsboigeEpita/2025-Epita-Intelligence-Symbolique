#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Shared utilities for soutenance demo scripts.

Provides corpus loading, metric extraction, tolerance checking,
and formatted summary printing. Each ``run_corpus_{a,b,c}.py``
imports from this module.
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

CORPORA = {
    "A": {
        "src_idx": 11,
        "label": "corpus_dense_A",
        "desc": "EN dense (~58K)",
        "tolerance": {
            "arguments_found": {"target": 20, "delta": 2},
            "fallacies_found": {"target": 13, "delta": 3},
            "unique_formal_categories": {"min": 3},
        },
    },
    "B": {
        "src_idx": 3,
        "label": "corpus_dense_B",
        "desc": "DE dense (~50K)",
        "tolerance": {
            "arguments_found": {"target": 17, "delta": 2},
            "fallacies_found": {"target": 17, "delta": 3},
            "unique_formal_categories": {"min": 3},
        },
    },
    "C": {
        "src_idx": 2,
        "label": "corpus_dense_C",
        "desc": "EN dense (~46K)",
        "tolerance": {
            "arguments_found": {"target": 10, "delta": 2},
            "fallacies_found": {"target": 14, "delta": 3},
            "unique_formal_categories": {"min": 3},
        },
    },
}


def bootstrap_env() -> None:
    """Set up sys.path and load .env variables."""
    os.chdir(_PROJECT_ROOT)
    sys.path.insert(0, str(_PROJECT_ROOT))

    _env_path = _PROJECT_ROOT / ".env"
    if _env_path.exists():
        with open(_env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    os.environ.setdefault(key.strip(), val.strip())


def load_corpus_text(corpus_id: str) -> str:
    """Decrypt and load corpus text.

    For corpus B, selects the best contiguous chunk (30K-60K chars)
    from the multi-speech source.
    """
    from argumentation_analysis.core.utils.crypto_utils import derive_encryption_key
    from argumentation_analysis.core.io_manager import load_extract_definitions

    info = CORPORA[corpus_id]
    passphrase = os.environ.get("TEXT_CONFIG_PASSPHRASE", "")
    if not passphrase:
        print("ERROR: TEXT_CONFIG_PASSPHRASE not set in .env")
        sys.exit(1)

    key = derive_encryption_key(passphrase)
    defs = load_extract_definitions(
        _PROJECT_ROOT / "argumentation_analysis" / "data" / "extract_sources.json.gz.enc",
        key,
    )
    src = defs[info["src_idx"]]
    text = src.get("full_text", "")

    # Corpus B: extract best contiguous chunk from multi-speech text
    if corpus_id == "B":
        speech_markers = re.split(r"(?=\d{4}\.\d{2}\.\d{2})", text)
        best_chunk = ""
        for chunk in speech_markers:
            if 30000 <= len(chunk) <= 60000:
                if len(chunk) > len(best_chunk):
                    best_chunk = chunk
        if not best_chunk:
            start = len(text) // 4
            boundary = text.find("\n\n", start)
            if boundary > 0:
                start = boundary
            best_chunk = text[start : start + 50000]
        text = best_chunk

    return text


def extract_metrics(state: Any, corpus_id: str) -> Dict[str, Any]:
    """Extract headline metrics from pipeline state."""
    info = CORPORA[corpus_id]
    metrics = {
        "corpus_id": corpus_id,
        "corpus_label": info["label"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "arguments_found": 0,
        "fallacies_found": 0,
        "unique_formal_categories": 0,
        "jtms_beliefs": 0,
        "counter_arguments": 0,
        "formal_category_details": [],
    }

    if state is None:
        return metrics

    args = getattr(state, "arguments", []) or []
    metrics["arguments_found"] = len(args)

    fallacies = getattr(state, "identified_fallacies", []) or []
    metrics["fallacies_found"] = len(fallacies)

    jtms = getattr(state, "jtms_beliefs", []) or []
    metrics["jtms_beliefs"] = len(jtms)

    counters = getattr(state, "counter_arguments", []) or []
    metrics["counter_arguments"] = len(counters)

    categories = set()
    for attr in (
        "dung_frameworks", "aspic_analyses", "fol_formulas",
        "pl_formulas", "modal_analyses", "belief_revisions",
    ):
        val = getattr(state, attr, None)
        if val:
            categories.add(attr)
            metrics["formal_category_details"].append(attr)
    metrics["unique_formal_categories"] = len(categories)

    return metrics


def check_tolerance(metrics: Dict[str, Any], corpus_id: str) -> List[str]:
    """Check metrics against tolerance bands. Returns list of warnings."""
    tolerance = CORPORA[corpus_id]["tolerance"]
    warnings = []
    for key, band in tolerance.items():
        actual = metrics.get(key, 0)
        if "delta" in band:
            lo = band["target"] - band["delta"]
            hi = band["target"] + band["delta"]
            if not (lo <= actual <= hi):
                warnings.append(
                    f"{key}: {actual} outside [{lo}, {hi}] "
                    f"(target={band['target']} ±{band['delta']})"
                )
        elif "min" in band:
            if actual < band["min"]:
                warnings.append(f"{key}: {actual} below minimum {band['min']}")
    return warnings


def print_summary(
    metrics: Dict[str, Any],
    duration: float,
    warnings: List[str],
    corpus_id: str,
) -> None:
    """Print formatted summary to stdout."""
    info = CORPORA[corpus_id]
    print(f"\n{'='*60}")
    print(f" SCDA Soutenance Demo — {info['label']} ({info['desc']})")
    print(f"{'='*60}")
    print(f"  Duration         : {duration:.1f}s ({duration/60:.1f} min)")
    print(f"  Arguments found  : {metrics['arguments_found']}")
    print(f"  Fallacies found  : {metrics['fallacies_found']}")
    print(f"  Formal categories: {metrics['unique_formal_categories']}")
    if metrics["formal_category_details"]:
        for cat in metrics["formal_category_details"]:
            print(f"    - {cat}")
    print(f"  JTMS beliefs     : {metrics['jtms_beliefs']}")
    print(f"  Counter-args     : {metrics['counter_arguments']}")
    print(f"{'='*60}")

    if warnings:
        print("\n  TOLERANCE WARNINGS:")
        for w in warnings:
            print(f"    WARNING: {w}")
    else:
        print("\n  All metrics within tolerance bands.")
    print()


def get_outputs_dir(corpus_id: str) -> Path:
    """Return the output directory for a corpus."""
    info = CORPORA[corpus_id]
    d = _PROJECT_ROOT / "outputs" / "soutenance_demo" / info["label"]
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_results(
    result: Dict[str, Any],
    metrics: Dict[str, Any],
    outputs_dir: Path,
) -> None:
    """Save state, summary, and report to disk."""
    state = result.get("unified_state")

    # State snapshot
    state_path = outputs_dir / "state.json"
    with open(state_path, "w", encoding="utf-8") as f:
        if state and hasattr(state, "get_state_snapshot"):
            snap = state.get_state_snapshot(summarize=True)
            json.dump(snap, f, indent=2, ensure_ascii=False, default=str)
        else:
            json.dump(metrics, f, indent=2, ensure_ascii=False, default=str)
    print(f"  State saved to {state_path}")

    # Summary
    summary_path = outputs_dir / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False, default=str)

    # Deep synthesis report
    deep_synth = result.get("deep_synthesis") or {}
    report_md = deep_synth.get("markdown", "")
    if report_md:
        report_path = outputs_dir / "deep_synthesis_report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_md)
        print(f"  Report saved to {report_path}")
