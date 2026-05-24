"""Head-to-head measurement: DAG-spectacular vs Conversational vs Zero-shot.

Exposes the real gaps with real numbers across EVERY dimension, on a single
corpus, so we can see where each orchestration path beats / loses to zero-shot.

  - Path A: run_unified_analysis(workflow_name="spectacular")  [DAG, single run]
  - Path B: run_conversational_analysis(spectacular=True)       [SK AgentGroupChat]
  - Zero-shot reference: docs/reports/BASELINE_0SHOT_2026-05-16.md (corpus C)

Counts are privacy-clean (cardinalities only, no dataset text). Output goes
under outputs/ (gitignored).

Usage:
    conda run -n projet-is-roo-new --no-capture-output python scripts/measure_both_paths_vs_zeroshot.py [--corpus C]

Output: outputs/deep_analysis/both_paths_vs_zeroshot_<corpus>.json
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict

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

# Zero-shot reference numbers (BASELINE_0SHOT_2026-05-16.md), per corpus.
ZERO_SHOT = {
    "A": {"counter_arguments": 15, "pl_formulas": 14, "fol_formulas": 8, "fallacies": 0},
    "B": {"counter_arguments": 12, "pl_formulas": 15, "fol_formulas": 13, "fallacies": 0},
    "C": {"counter_arguments": 18, "pl_formulas": 12, "fol_formulas": 12, "fallacies": 0},
}
CORPUS_SRC_IDX = {"A": 11, "B": 3, "C": 2}
OUTPUTS_DIR = Path("outputs/deep_analysis")


def load_corpus(label: str) -> str:
    key = derive_encryption_key(os.environ["TEXT_CONFIG_PASSPHRASE"])
    defs = load_extract_definitions(
        Path("argumentation_analysis/data/extract_sources.json.gz.enc"), key
    )
    text = defs[CORPUS_SRC_IDX[label]].get("full_text", "")
    return text[:60000] if len(text) > 60000 else text


def count_dimensions(state: Any) -> Dict[str, Any]:
    """Privacy-clean cardinalities across every analysis dimension."""
    if state is None:
        return {"error": "no state"}

    def _list(attr):
        return getattr(state, attr, []) or []

    def _dict(attr):
        return getattr(state, attr, {}) or {}

    pl_results = _list("propositional_analysis_results")
    fol_results = _list("fol_analysis_results")
    pl_formulas = sum(len(r.get("formulas", [])) for r in pl_results)
    fol_formulas = sum(len(r.get("formulas", [])) for r in fol_results)
    pl_verified = sum(
        len(r.get("formulas", []))
        for r in pl_results
        if r.get("satisfiable") is not None
    )
    fol_verified = sum(
        len(r.get("formulas", []))
        for r in fol_results
        if r.get("consistent") is not None
    )

    # Convergence depth (in-run if narrative ran, else recompute)
    try:
        from argumentation_analysis.plugins.narrative_synthesis_plugin import (
            compute_argument_convergence,
        )

        conv = compute_argument_convergence(state)
        max_conv = max((d["score"] for d in conv.values()), default=0)
        args_with_signals = len(conv)
    except Exception as e:
        max_conv = -1
        args_with_signals = -1
        conv = {"_err": str(e)}

    return {
        "identified_arguments": len(_dict("identified_arguments")),
        "identified_fallacies": len(_dict("identified_fallacies")),
        "counter_arguments": len(_list("counter_arguments")),
        "argument_quality_scores": len(_dict("argument_quality_scores")),
        "jtms_beliefs": len(_dict("jtms_beliefs")),
        "jtms_retraction_chain": len(_list("jtms_retraction_chain")),
        "dung_frameworks": len(_dict("dung_frameworks")),
        "aspic_results": len(_list("aspic_results")),
        "belief_sets": len(_dict("belief_sets")),
        "nl_to_logic_translations": len(_list("nl_to_logic_translations")),
        "pl_entries": len(pl_results),
        "pl_formulas": pl_formulas,
        "pl_verified": pl_verified,
        "fol_entries": len(fol_results),
        "fol_formulas": fol_formulas,
        "fol_verified": fol_verified,
        "convergence_max_depth": max_conv,
        "convergence_args_with_signals": args_with_signals,
        "narrative_synthesis_len": len(getattr(state, "narrative_synthesis", "") or ""),
    }


def verdict_vs_zeroshot(dims: Dict[str, Any], zs: Dict[str, int]) -> Dict[str, str]:
    """For each quantitative axis zero-shot competes on: WIN / TIE / LOSS."""
    out = {}
    for axis in ("counter_arguments", "pl_formulas", "fol_formulas"):
        ours = dims.get(axis, 0)
        theirs = zs.get(axis, 0)
        if ours > theirs:
            out[axis] = f"WIN ({ours} vs {theirs})"
        elif ours == theirs:
            out[axis] = f"TIE ({ours} vs {theirs})"
        else:
            out[axis] = f"LOSS ({ours} vs {theirs})"
    # Formal verification: zero-shot is 0-verified by construction.
    out["pl_verified"] = f"ours={dims.get('pl_verified', 0)} vs zero-shot=0"
    out["fol_verified"] = f"ours={dims.get('fol_verified', 0)} vs zero-shot=0"
    return out


async def run_path_dag(text: str) -> Dict[str, Any]:
    from argumentation_analysis.orchestration.unified_pipeline import (
        run_unified_analysis,
    )

    start = time.time()
    raw = await run_unified_analysis(text=text, workflow_name="spectacular")
    duration = time.time() - start
    state = raw.get("unified_state")
    return {
        "path": "dag_spectacular",
        "duration_s": round(duration, 1),
        "summary": raw.get("summary", {}),
        "capabilities_missing": raw.get("capabilities_missing", []),
        "dimensions": count_dimensions(state),
    }


async def run_path_conversational(text: str) -> Dict[str, Any]:
    from argumentation_analysis.orchestration.conversational_orchestrator import (
        run_conversational_analysis,
    )

    start = time.time()
    res = await run_conversational_analysis(
        text=text, max_turns_per_phase=10, spectacular=True
    )
    duration = time.time() - start
    state = res.get("unified_state")
    return {
        "path": "conversational",
        "duration_s": round(duration, 1),
        "summary": res.get("summary", {}),
        "dimensions": count_dimensions(state),
    }


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="C", choices=["A", "B", "C"])
    ap.add_argument(
        "--paths",
        default="dag,conversational",
        help="comma list: dag,conversational",
    )
    args = ap.parse_args()

    label = args.corpus
    zs = ZERO_SHOT[label]
    text = load_corpus(label)
    print(f"[corpus {label}] loaded {len(text):,} chars")

    out_dir = OUTPUTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    results: Dict[str, Any] = {
        "corpus": label,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "zero_shot_reference": zs,
        "paths": {},
    }

    wanted = [p.strip() for p in args.paths.split(",")]

    if "dag" in wanted:
        print("\n=== PATH A: DAG spectacular (run_unified_analysis) ===")
        try:
            r = await run_path_dag(text)
            r["verdict_vs_zeroshot"] = verdict_vs_zeroshot(r["dimensions"], zs)
            results["paths"]["dag_spectacular"] = r
            print(json.dumps(r["dimensions"], indent=2))
            print("VERDICT:", json.dumps(r["verdict_vs_zeroshot"], indent=2))
        except Exception as e:
            import traceback

            results["paths"]["dag_spectacular"] = {
                "error": str(e),
                "traceback": traceback.format_exc(),
            }
            print(f"DAG path FAILED: {e}")

    if "conversational" in wanted:
        print("\n=== PATH B: Conversational (run_conversational_analysis) ===")
        try:
            r = await run_path_conversational(text)
            r["verdict_vs_zeroshot"] = verdict_vs_zeroshot(r["dimensions"], zs)
            results["paths"]["conversational"] = r
            print(json.dumps(r["dimensions"], indent=2))
            print("VERDICT:", json.dumps(r["verdict_vs_zeroshot"], indent=2))
        except Exception as e:
            import traceback

            results["paths"]["conversational"] = {
                "error": str(e),
                "traceback": traceback.format_exc(),
            }
            print(f"Conversational path FAILED: {e}")

    out_file = out_dir / f"both_paths_vs_zeroshot_{label}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nSaved: {out_file}")


if __name__ == "__main__":
    asyncio.run(main())
