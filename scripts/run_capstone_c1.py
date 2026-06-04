"""Capstone C1 — Pipeline Intégral (MAX config) vs 0-Shot LLM Baseline.

Runs the full spectacular pipeline (all components activated) on 3 corpus,
then runs a 0-shot LLM baseline on the same texts, saves scrubbed results
under argumentation_analysis/evaluation/results/capstone_c1/ (gitignored).

Usage:
    conda run -n projet-is-roo-new --no-capture-output python scripts/run_capstone_c1.py [--corpus A]

Output:
    evaluation/results/capstone_c1/
        integral_A.json  integral_B.json  integral_C.json
        baseline_A.json  baseline_B.json  baseline_C.json
        summary.json
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
os.chdir(Path(__file__).parent.parent)

# Load .env
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

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

CORPUS_SRC_IDX = {"A": 11, "B": 3, "C": 2}
RESULTS_DIR = Path("argumentation_analysis/evaluation/results/capstone_c1")
DATASET_PATH = Path("argumentation_analysis/data/extract_sources.json.gz.enc")

# 0-shot prompt (from CAPSTONE_INTEGRAL_VS_ZEROSHOT.md)
ZEROSHOT_PROMPT = """Tu es un analyste rhétorique expert. Analyse le texte suivant de manière exhaustive.

Pour chaque argument identifié, fournis :
1. La thèse de l'argument
2. Les prémisses explicites et implicites
3. Le type de raisonnement (déductif, inductif, analogique, causal, etc.)
4. Tout sophisme ou erreur de raisonnement détecté (avec la famille : appel à l'autorité, homme de paille, faux dilemme, pente glissante, etc.)
5. La force persuasive de l'argument (1-10)

Ensuite, fournis une évaluation globale :
6. La structure argumentative du texte (nombre et types d'arguments)
7. Les stratégies rhétoriques employées
8. Les points forts et les faiblesses de l'argumentation
9. Une conclusion sur la qualité globale de l'argumentation

Texte :
---
{text}
---"""

# Privacy: opaque IDs
CORPUS_LABELS = {"A": "doc_A", "B": "doc_B", "C": "doc_C"}


# ---------------------------------------------------------------------------
# Corpus loading
# ---------------------------------------------------------------------------

def load_corpus_text(label: str, max_chars: int = 60000) -> str:
    """Load corpus text from encrypted dataset."""
    key = derive_encryption_key(os.environ["TEXT_CONFIG_PASSPHRASE"])
    defs = load_extract_definitions(DATASET_PATH, key)
    text = defs[CORPUS_SRC_IDX[label]].get("full_text", "")
    return text[:max_chars] if len(text) > max_chars else text


# ---------------------------------------------------------------------------
# Integral pipeline run
# ---------------------------------------------------------------------------

async def run_integral_pipeline(corpus_label: str, text: str) -> Dict[str, Any]:
    """Run the full spectacular pipeline with MAX config."""
    from argumentation_analysis.orchestration.unified_pipeline import run_unified_analysis

    context = {
        "fallacy_tier": "full",
        "shield_config": {"preset": "advanced", "fail_open": True},
        # Defaults (copeland, 0.7, tweety, auto, all) — no need to override
    }

    print(f"[C1] Starting integral pipeline for corpus {corpus_label}...")
    t0 = time.time()
    result = await run_unified_analysis(
        text=text,
        workflow_name="spectacular",
        context=context,
    )
    elapsed = time.time() - t0
    print(f"[C1] Integral pipeline for {corpus_label} completed in {elapsed:.1f}s")

    # Extract structured output
    state = result.get("unified_state")
    output = {
        "corpus": CORPUS_LABELS[corpus_label],
        "method": "integral_pipeline",
        "elapsed_seconds": round(elapsed, 1),
        "phases": {},
    }

    if state is not None:
        snap = state.get_state_snapshot(summarize=False)
        output["phases"] = _extract_phase_metrics(snap)
    else:
        output["phases"] = {"error": "no state available"}

    return output


def _extract_phase_metrics(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """Extract privacy-clean metrics from state snapshot.

    Note: get_state_snapshot(summarize=False) returns raw attribute names.
    identified_arguments is a DICT (not list), same for identified_fallacies.
    dung_frameworks (not dung_extensions), governance_decisions, debate_transcripts.
    """
    metrics = {}

    # Arguments (dict: arg_id -> description)
    args = snapshot.get("identified_arguments", {})
    metrics["arguments_count"] = len(args) if isinstance(args, dict) else (
        len(args) if isinstance(args, list) else 0
    )

    # Fallacies (dict: fallacy_id -> entry)
    fallacies = snapshot.get("identified_fallacies", {})
    metrics["fallacies_count"] = len(fallacies) if isinstance(fallacies, dict) else (
        len(fallacies) if isinstance(fallacies, list) else 0
    )
    if isinstance(fallacies, dict) and fallacies:
        families = {}
        for _fid, fdata in fallacies.items():
            fam = fdata.get("family", fdata.get("fallacy_type", "unknown")) if isinstance(fdata, dict) else "unknown"
            families[fam] = families.get(fam, 0) + 1
        metrics["fallacy_families"] = families
    elif isinstance(fallacies, list) and fallacies:
        families = {}
        for f in fallacies:
            fam = f.get("family", f.get("fallacy_type", "unknown")) if isinstance(f, dict) else "unknown"
            families[fam] = families.get(fam, 0) + 1
        metrics["fallacy_families"] = families

    # PL formulas
    pl_results = snapshot.get("propositional_analysis_results", [])
    if isinstance(pl_results, list):
        pl_formulas = sum(len(r.get("formulas", [])) for r in pl_results if isinstance(r, dict))
        pl_verified = sum(
            1 for r in pl_results if isinstance(r, dict) and r.get("satisfiable") is not None
            for _ in r.get("formulas", [])
        )
        metrics["pl_formulas"] = pl_formulas
        metrics["pl_verified"] = pl_verified
    elif isinstance(pl_results, dict):
        # Single result dict
        metrics["pl_formulas"] = len(pl_results.get("formulas", []))
        metrics["pl_verified"] = sum(
            1 for _ in pl_results.get("formulas", [])
        ) if pl_results.get("satisfiable") is not None else 0

    # FOL formulas
    fol_results = snapshot.get("fol_analysis_results", [])
    if isinstance(fol_results, list):
        fol_formulas = sum(len(r.get("formulas", [])) for r in fol_results if isinstance(r, dict))
        fol_verified = sum(
            1 for r in fol_results if isinstance(r, dict) and r.get("satisfiable") is not None
            for _ in r.get("formulas", [])
        )
        metrics["fol_formulas"] = fol_formulas
        metrics["fol_verified"] = fol_verified
    elif isinstance(fol_results, dict):
        metrics["fol_formulas"] = len(fol_results.get("formulas", []))
        metrics["fol_verified"] = len(fol_results.get("formulas", [])) if fol_results.get("satisfiable") is not None else 0

    # Dung extensions — field is dung_frameworks (dict)
    dung = snapshot.get("dung_frameworks", snapshot.get("dung_extensions", {}))
    if isinstance(dung, dict):
        all_ext = dung.get("all_extensions", dung)
        if isinstance(all_ext, dict):
            metrics["dung_semantics_count"] = len(all_ext)
            metrics["dung_extensions"] = {
                k: {"count": v.get("count", 0) if isinstance(v, dict) else 0}
                for k, v in all_ext.items()
                if k not in ("arguments", "attacks", "provider", "semantics")
            }

    # Counter-arguments
    counter_args = snapshot.get("counter_arguments", [])
    metrics["counter_arguments_count"] = len(counter_args) if isinstance(counter_args, (list, dict)) else 0

    # Quality scores — field is argument_quality_scores
    quality = snapshot.get("argument_quality_scores", snapshot.get("quality_evaluation", {}))
    if isinstance(quality, dict):
        metrics["quality_scores"] = {
            k: round(v, 2) if isinstance(v, (int, float)) else v
            for k, v in quality.items()
            if not k.startswith("_")
        }

    # JTMS beliefs
    beliefs = snapshot.get("jtms_beliefs", [])
    metrics["jtms_beliefs_count"] = len(beliefs) if isinstance(beliefs, (list, dict)) else 0

    # Governance — field is governance_decisions
    gov = snapshot.get("governance_decisions", snapshot.get("governance_results", {}))
    if isinstance(gov, dict):
        metrics["governance"] = {
            "conflicts": len(gov.get("conflicts", [])),
            "consensus": gov.get("consensus_level"),
            "vote_method": gov.get("vote_method"),
        }
    elif isinstance(gov, list):
        metrics["governance"] = {"decisions_count": len(gov)}

    # Debate — field is debate_transcripts
    debate = snapshot.get("debate_transcripts", snapshot.get("debate_results", {}))
    if isinstance(debate, dict):
        metrics["debate"] = {
            "rounds": debate.get("total_rounds", 0),
            "winner": debate.get("winner"),
            "quality": debate.get("quality_score"),
        }
    elif isinstance(debate, list):
        metrics["debate"] = {"transcripts_count": len(debate)}

    # Trace entries count
    trace = snapshot.get("trace_entries", [])
    metrics["trace_entries_count"] = len(trace) if isinstance(trace, (list, dict)) else 0

    return metrics


# ---------------------------------------------------------------------------
# 0-Shot baseline run
# ---------------------------------------------------------------------------

async def run_zeroshot_baseline(corpus_label: str, text: str) -> Dict[str, Any]:
    """Run 0-shot LLM baseline (single prompt, no tools)."""
    print(f"[C1] Starting 0-shot baseline for corpus {corpus_label}...")
    t0 = time.time()

    # Use OpenAI client directly (no SK needed for a single prompt)
    from openai import OpenAI
    client = OpenAI()  # reads OPENAI_API_KEY from env
    model = os.environ.get("OPENAI_CHAT_MODEL_ID", "gpt-5-mini")

    prompt = ZEROSHOT_PROMPT.format(text=text[:8000])  # Limit text for baseline (token budget)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_completion_tokens=4096,
    )

    elapsed = time.time() - t0
    print(f"[C1] 0-shot baseline for {corpus_label} completed in {elapsed:.1f}s")

    # Parse the 0-shot response for structured metrics
    response_text = response.choices[0].message.content or ""
    output = {
        "corpus": CORPUS_LABELS[corpus_label],
        "method": "zeroshot_baseline",
        "elapsed_seconds": round(elapsed, 1),
        "response_length": len(response_text),
        "analysis_text": response_text,  # Will be scrubbed before save
    }

    return output


def _scrub_baseline(output: Dict[str, Any]) -> Dict[str, Any]:
    """Remove raw analysis text, keep only metrics."""
    scrubbed = dict(output)
    # Replace raw text with length only
    raw_len = len(scrubbed.pop("analysis_text", ""))
    scrubbed["analysis_text_length"] = raw_len

    # Try to extract counts from the text
    text = output.get("analysis_text", "")
    scrubbed["estimated_arguments"] = text.lower().count("argument")
    scrubbed["estimated_fallacies"] = sum(
        1 for word in ["sophisme", "fallacy", "homme de paille", "faux dilemme",
                        "pente glissante", "autorité", "appel à"]
        if word in text.lower()
    )

    return scrubbed


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

async def run_capstone_c1(corpus_list: List[str]) -> None:
    """Run C1 for all specified corpus."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "corpus": {},
    }

    for label in corpus_list:
        print(f"\n{'='*60}")
        print(f"[C1] Processing corpus {label} ({CORPUS_LABELS[label]})")
        print(f"{'='*60}")

        text = load_corpus_text(label)
        print(f"[C1] Corpus {label}: {len(text)} chars loaded")

        # 1. Integral pipeline
        try:
            integral = await run_integral_pipeline(label, text)
            integral_path = RESULTS_DIR / f"integral_{label}.json"
            with open(integral_path, "w", encoding="utf-8") as f:
                json.dump(integral, f, indent=2, ensure_ascii=False, default=str)
            print(f"[C1] Integral results saved to {integral_path}")
        except Exception as e:
            integral = {"error": str(e), "corpus": CORPUS_LABELS[label]}
            print(f"[C1] Integral pipeline FAILED for {label}: {e}")

        # 2. 0-shot baseline
        try:
            baseline = await run_zeroshot_baseline(label, text)
            baseline_scrubbed = _scrub_baseline(baseline)
            baseline_path = RESULTS_DIR / f"baseline_{label}.json"
            with open(baseline_path, "w", encoding="utf-8") as f:
                json.dump(baseline_scrubbed, f, indent=2, ensure_ascii=False, default=str)
            print(f"[C1] Baseline results saved to {baseline_path}")
        except Exception as e:
            baseline_scrubbed = {"error": str(e), "corpus": CORPUS_LABELS[label]}
            print(f"[C1] 0-shot baseline FAILED for {label}: {e}")

        # Summary entry
        summary["corpus"][label] = {
            "integral": {
                "elapsed": integral.get("elapsed_seconds"),
                "arguments": integral.get("phases", {}).get("arguments_count"),
                "fallacies": integral.get("phases", {}).get("fallacies_count"),
                "pl_formulas": integral.get("phases", {}).get("pl_formulas"),
                "fol_formulas": integral.get("phases", {}).get("fol_formulas"),
                "counter_arguments": integral.get("phases", {}).get("counter_arguments_count"),
                "dung_semantics": integral.get("phases", {}).get("dung_semantics_count"),
            },
            "baseline": {
                "elapsed": baseline_scrubbed.get("elapsed_seconds"),
                "response_length": baseline_scrubbed.get("analysis_text_length"),
                "estimated_arguments": baseline_scrubbed.get("estimated_arguments"),
                "estimated_fallacies": baseline_scrubbed.get("estimated_fallacies"),
            },
        }

    # Save summary
    summary_path = RESULTS_DIR / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n[C1] Summary saved to {summary_path}")
    print(f"[C1] Capstone C1 complete!")


def main():
    parser = argparse.ArgumentParser(description="Capstone C1 — Integral vs 0-Shot")
    parser.add_argument("--corpus", choices=["A", "B", "C"], default=None,
                        help="Run on single corpus (default: all 3)")
    args = parser.parse_args()

    corpus_list = [args.corpus] if args.corpus else ["A", "B", "C"]
    asyncio.run(run_capstone_c1(corpus_list))


if __name__ == "__main__":
    main()
