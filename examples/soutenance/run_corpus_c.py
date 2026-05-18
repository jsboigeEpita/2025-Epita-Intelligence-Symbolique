#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Soutenance demo — Corpus C (EN dense ~46K).

One-shot end-to-end SCDA pipeline run on corpus_dense_C.
Produces a state JSON snapshot and a readable summary with
headline metrics. Wall-clock target: ~20 min.

Usage:
    conda activate projet-is
    python examples/soutenance/run_corpus_c.py

Expected output (tolerance bands):
    arguments_found : 10 ± 2
    fallacies_found : 14 ± 3
    unique_formal_categories : ≥ 3

All outputs go to ``outputs/soutenance_demo/corpus_dense_C/`` (gitignored).
"""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _shared import (
    bootstrap_env,
    check_tolerance,
    extract_metrics,
    get_outputs_dir,
    load_corpus_text,
    print_summary,
    save_results,
    CORPORA,
)

CORPUS_ID = "C"


async def run_demo() -> None:
    """Main demo entry point."""
    bootstrap_env()
    info = CORPORA[CORPUS_ID]

    print(f"\n{'='*60}")
    print(f" Loading {info['label']} ({info['desc']})...")
    print(f"{'='*60}")

    text = load_corpus_text(CORPUS_ID)
    print(f"  Loaded {len(text):,} characters")

    outputs_dir = get_outputs_dir(CORPUS_ID)

    print(f"\n  Running SCDA Spectacular Conversational Deep Analysis...")
    print(f"  (expected ~20 min wall-clock)")

    from argumentation_analysis.orchestration.conversational_orchestrator import (
        run_conversational_analysis,
    )

    start = time.time()
    result = await run_conversational_analysis(
        text=text,
        max_turns_per_phase=10,
        spectacular=True,
    )
    duration = time.time() - start

    state = result.get("unified_state")
    metrics = extract_metrics(state, CORPUS_ID)
    metrics["duration_seconds"] = round(duration, 1)
    warnings = check_tolerance(metrics, CORPUS_ID)

    save_results(result, metrics, outputs_dir)
    print_summary(metrics, duration, warnings, CORPUS_ID)


if __name__ == "__main__":
    asyncio.run(run_demo())
