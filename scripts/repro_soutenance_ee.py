"""Reproducibility script for soutenance — Track EE (#691).

Regenerates the consolidated volet-1/2/3 report from known live-verified results
or runs the sequential probes if a funded API key is available.

Usage:
    # Static mode — generate report from known results (no API key needed):
    conda run -n projet-is-roo-new --no-capture-output python scripts/repro_soutenance_ee.py

    # Live mode — run sequential probes on corpus C (requires funded OPENROUTER_API_KEY):
    conda run -n projet-is-roo-new --no-capture-output python scripts/repro_soutenance_ee.py --live

Output: outputs/deep_analysis/corpus_dense_C/repro_soutenance_ee.json
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

OUTPUTS_DIR = Path("outputs/deep_analysis/corpus_dense_C")

KNOWN_RESULTS = {
    "volet_1_formula_survival": {
        "source": "R218 sequential probe (ai-01, 2026-05-23)",
        "pl_entries": 1,
        "pl_formulas_surviving": 46,
        "pl_verdict": "satisfiable=true",
        "fol_entries": 1,
        "fol_formulas_surviving": 26,
        "fol_verdict": "consistent=false",
        "total_surviving": 72,
        "dod_ge3_met": True,
        "probe_mode": "sequential full",
        "duration_s": 430.9,
        "phases_ok": "14/15",
    },
    "volet_2_convergence_depth": {
        "source": "R216c spectacular + R220 sequential (ai-01, 2026-05-23)",
        "spectacular_depth": 3,
        "sequential_depth": 4,
        "target_ge3_met": True,
        "corpus": "C",
    },
    "volet_3_signal_integrity": {
        "source": "R220 sequential probe (ai-01, 2026-05-23)",
        "sequential_signals": {
            "sophisme": 0,
            "qualite_faible": 8,
            "contre_argument": 4,
            "jtms_retracte": 1,
            "rejet_dung": 9,
        },
        "spectacular_signals_R216c": {
            "sophisme": 9,
            "qualite_faible": 0,
            "contre_argument": 5,
            "jtms_retracte": 0,
            "rejet_dung": 9,
        },
        "sequential_alive_count": "4/5",
        "spectacular_alive_count": "3/5",
        "note": "Signal-4 (JTMS retracte) verified live via ZZ fix #685",
    },
    "caveats": [
        "Sequential vs spectacular: formal logic (PL/FOL) only measurable on sequential path",
        "Run-to-run variance: gpt-5-mini is a reasoning model, sampling params suppressed (AA #686)",
        "Sophisme recall: sequential detects fewer fallacies than spectacular (DD #690 partially addresses)",
        "Tolerance bands: args ±2, fallacies ±3 per run",
    ],
}


def load_corpus_c() -> str:
    """Load corpus C text from encrypted dataset."""
    from argumentation_analysis.core.utils.crypto_utils import derive_encryption_key
    from argumentation_analysis.core.io_manager import load_extract_definitions

    key = derive_encryption_key(os.environ["TEXT_CONFIG_PASSPHRASE"])
    defs = load_extract_definitions(
        Path("argumentation_analysis/data/extract_sources.json.gz.enc"), key
    )
    src = defs[2]
    text = src.get("full_text", "")
    return text[:60000]


def count_state_formulas(state: Any) -> Dict[str, Any]:
    """Count surviving formulas in state PL/FOL results."""
    pl_results = getattr(state, "propositional_analysis_results", []) or []
    fol_results = getattr(state, "fol_analysis_results", []) or []
    pl_count = sum(len(r.get("formulas", [])) for r in pl_results)
    fol_count = sum(len(r.get("formulas", [])) for r in fol_results)
    return {
        "pl_entries": len(pl_results),
        "pl_formulas_surviving": pl_count,
        "fol_entries": len(fol_results),
        "fol_formulas_surviving": fol_count,
        "total_surviving": pl_count + fol_count,
        "dod_ge3_met": pl_count + fol_count >= 3,
    }


def analyze_convergence(state: Any) -> Dict[str, Any]:
    """Per-signal fire counts from convergence engine."""
    from argumentation_analysis.plugins.narrative_synthesis_plugin import (
        compute_argument_convergence,
    )
    from collections import Counter

    convergence = compute_argument_convergence(state)
    signal_counts = Counter()
    for arg_id, data in convergence.items():
        for method, _ in data["signals"]:
            signal_counts[method] += 1
    return {
        "max_depth": max((d["score"] for d in convergence.values()), default=0),
        "signal_fire_counts": dict(signal_counts),
        "total_args": len(convergence),
    }


async def run_sequential_probe(text: str) -> Dict[str, Any]:
    """Run sequential full pipeline on corpus C and collect volet-1/2/3."""
    from argumentation_analysis.orchestration.unified_pipeline import (
        run_unified_analysis,
    )

    start = time.time()
    result = await run_unified_analysis(text=text, workflow_name="full")
    duration = time.time() - start

    state = result.get("unified_state") if isinstance(result, dict) else result
    if state is None:
        return {"error": "No state returned", "duration_s": round(duration, 1)}

    formulas = count_state_formulas(state)
    convergence = analyze_convergence(state)

    return {
        "duration_s": round(duration, 1),
        "formulas": formulas,
        "convergence": convergence,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


async def run_live():
    """Run the sequential probe and merge with known spectacular results."""
    print("Loading corpus C...")
    text = load_corpus_c()
    print(f"  Loaded: {len(text):,} chars")

    print("\nRunning sequential full pipeline...")
    seq = await run_sequential_probe(text)
    print(f"  Completed in {seq.get('duration_s', '?')}s")

    formulas = seq.get("formulas", {})
    convergence = seq.get("convergence", {})

    results = {
        "mode": "live",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "volet_1_formula_survival": {
            "source": "live sequential probe (this run)",
            "pl_entries": formulas.get("pl_entries", 0),
            "pl_formulas_surviving": formulas.get("pl_formulas_surviving", 0),
            "fol_entries": formulas.get("fol_entries", 0),
            "fol_formulas_surviving": formulas.get("fol_formulas_surviving", 0),
            "total_surviving": formulas.get("total_surviving", 0),
            "dod_ge3_met": formulas.get("dod_ge3_met", False),
        },
        "volet_2_convergence_depth": {
            "source": "live sequential probe (this run)",
            "sequential_depth": convergence.get("max_depth", 0),
            "target_ge3_met": convergence.get("max_depth", 0) >= 3,
        },
        "volet_3_signal_integrity": {
            "source": "live sequential probe (this run)",
            "sequential_signals": convergence.get("signal_fire_counts", {}),
        },
        "caveats": KNOWN_RESULTS["caveats"],
    }

    return results


def run_static() -> Dict[str, Any]:
    """Generate report from known live-verified results."""
    return {
        "mode": "static",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "note": "Known results from ai-01 live probes R216c/R218/R220 (2026-05-23). "
        "Run with --live to regenerate from a fresh sequential probe.",
        **KNOWN_RESULTS,
    }


async def main():
    parser = argparse.ArgumentParser(description="Soutenance reproducibility script")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Run live sequential probe (requires funded API key)",
    )
    args = parser.parse_args()

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    if args.live:
        results = await run_live()
    else:
        results = run_static()

    with open(OUTPUTS_DIR / "repro_soutenance_ee.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    print(f"\nResults saved to {OUTPUTS_DIR / 'repro_soutenance_ee.json'}")

    v1 = results.get("volet_1_formula_survival", {})
    v2 = results.get("volet_2_convergence_depth", {})
    v3 = results.get("volet_3_signal_integrity", {})

    print("\n" + "=" * 60)
    print("SOUTENANCE REPRODUCIBILITY SUMMARY")
    print("=" * 60)
    total = v1.get("total_surviving", "N/A")
    print(f"  Volet-1 formulas: {total} (DoD >=3: {v1.get('dod_ge3_met', '?')})")
    depth = v2.get("sequential_depth", v2.get("spectacular_depth", "N/A"))
    print(f"  Volet-2 depth: {depth} (DoD >=3: {v2.get('target_ge3_met', '?')})")
    alive = v3.get("sequential_alive_count", "N/A")
    print(f"  Volet-3 signals: {alive} alive on sequential path")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
