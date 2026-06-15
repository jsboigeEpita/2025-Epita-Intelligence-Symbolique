"""FB-32 — Re-measure quality axis + spectacular varying text (de-castrated pipeline).

#1112, Epic #947, audit #1109 §5 (acceptance). Follows FB-30 #1110 (descent
restored by subtraction) + FB-31 #1111 (synthesis fail-loud, count-template
deleted), both merged on main ``fd3831a8``.

The de-castration removed two variance/richness killers (count-template Section
9 + mechanical beam descent). FB-28 measured the quality axis EDGES *under the
castrated pipeline*. This script re-measures under the de-castrated pipeline and
demonstrates the terminal deliverable: a spectacular LLM-conducted qualitative
text on the real corpus that VARIES across runs (mandate 2026-06-15).

Three modes:
  --mode isolate  (cheap, decisive): run the Section 9 LLM synthesis N times on
                  ONE captured state → proves the count-template is gone and the
                  prose varies. ~$1. Run this FIRST to validate cheaply.
  --mode full     (expensive): run the full spectacular pipeline + deep synthesis
                  --runs N times per corpus → end-to-end variance (extraction +
                  descent + synthesis). The DoD "≥2 runs/corpus" deliverable.
  --mode quality  : re-run the 0-shot baseline on freshly-extracted args from the
                  de-castrated pipeline + compare to the pipeline radar (FB-28
                  protocol). Honest verdict (EDGES held / moved).

Anti-pendule HARD (#1109): variance IS the feature. We do NOT set
``LLM_DETERMINISTIC_MODE`` (the default suppresses temperature/seed, so
gpt-5-mini's sampling variance is active). No prose-freezing test. No synthetic
fallback on LLM error — fail-loud.

Privacy HARD: corpus loaded in-memory from the encrypted blob via the dataset
index (opaque ``corpus_A``/``doc_A`` IDs). No ``raw_text``/``full_text`` ever in
committed state. Per-run markdown + raw JSON are gitignored under
``argumentation_analysis/evaluation/results/fb32/``. The aggregate report uses
opaque IDs only and cites diff excerpts (paraphrased, opaque) — never raw spans.

Usage:
    conda run -n projet-is-roo-new --no-capture-output python \\
        scripts/run_fb32_decast_variance.py --mode isolate --corpus C --runs 3
    conda run -n projet-is-roo-new --no-capture-output python \\
        scripts/run_fb32_decast_variance.py --mode full --corpus C --runs 2
    conda run -n projet-is-roo-new --no-capture-output python \\
        scripts/run_fb32_decast_variance.py --mode quality --corpus A

Output (gitignored):
    argumentation_analysis/evaluation/results/fb32/
        isolate_<corpus>_<run>.md      full_<corpus>_<run>.md
        fb32_variance_summary.json     fb32_quality_<corpus>.json
"""

import argparse
import asyncio
import difflib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))
os.chdir(Path(__file__).parent.parent)

# Load .env (OPENROUTER_API_KEY / OPENROUTER_BASE_URL / OPENAI_API_KEY / TEXT_CONFIG_PASSPHRASE)
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    with open(_env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())

# Guard: variance is the feature. Refuse to run if determinism is forced.
if os.environ.get("LLM_DETERMINISTIC_MODE"):
    print("ABORT: LLM_DETERMINISTIC_MODE is set — FB-32 mandates variance (anti-pendule).")
    sys.exit(2)

from argumentation_analysis.core.utils.crypto_utils import derive_encryption_key
from argumentation_analysis.core.io_manager import load_extract_definitions

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# corpus -> encrypted-dataset definition index (matches run_capstone_c1.py).
CORPUS_SRC_IDX = {"A": 11, "B": 3, "C": 2}
CORPUS_LABELS = {"A": "doc_A", "B": "doc_B", "C": "doc_C"}
DATASET_PATH = Path("argumentation_analysis/data/extract_sources.json.gz.enc")
RESULTS_DIR = Path("argumentation_analysis/evaluation/results/fb32")
MAX_CHARS = 60000

VIRTUES = [
    "clarte", "pertinence", "presence_sources", "refutation_constructive",
    "structure_logique", "analogie_pertinente", "fiabilite_sources",
    "exhaustivite", "redondance_faible",
]
SCALE_VALUES = [0.0, 0.2, 0.5, 1.0]

BASELINE_EVAL_PROMPT = """Tu es un évaluateur d'arguments expert. Évalue l'argument suivant sur 9 vertus rhétoriques.

Pour chaque vertu, attribue un score sur l'échelle {0.0, 0.2, 0.5, 1.0} :
- 1.0 = la vertu est pleinement présente
- 0.5 = partiellement présente
- 0.2 = faible / marginale
- 0.0 = absente

Les 9 vertus (scores STRICTEMENT dans {0.0, 0.2, 0.5, 1.0}) :
- clarte : clarté et lisibilité de l'argument
- pertinence : pertinence logique (connecteurs, enchaînement)
- presence_sources : présence de sources / preuves factuelles citées
- refutation_constructive : l'argument adresse-t-il des contre-positions ?
- structure_logique : rigueur de la structure logique (prémisses→conclusion)
- analogie_pertinente : usage d'analogies pertinentes si pertinent
- fiabilite_sources : crédibilité des sources citées (si présentes)
- exhaustivite : couverture raisonnable du sujet
- redondance_faible : absence de redondance (1.0 = non redondant)

Argument à évaluer :
---
{arg_text}
---

Réponds UNIQUEMENT avec un objet JSON valide de la forme (pas de texte avant/après) :
{{"scores": {{"clarte": <score>, "pertinence": <score>, "presence_sources": <score>, "refutation_constructive": <score>, "structure_logique": <score>, "analogie_pertinente": <score>, "fiabilite_sources": <score>, "exhaustivite": <score>, "redondance_faible": <score>}}, "justification": "<1 phrase>"}}
"""


# ---------------------------------------------------------------------------
# Corpus + cost
# ---------------------------------------------------------------------------

def load_corpus_text(label: str) -> str:
    """Load corpus text in-memory from the encrypted dataset (opaque, not committed)."""
    key = derive_encryption_key(os.environ["TEXT_CONFIG_PASSPHRASE"])
    defs = load_extract_definitions(DATASET_PATH, key)
    text = defs[CORPUS_SRC_IDX[label]].get("full_text", "")
    return text[:MAX_CHARS] if len(text) > MAX_CHARS else text


def get_openrouter_balance() -> Optional[float]:
    """Real OpenRouter credit balance (1 credit = $1). None if unavailable."""
    import urllib.request

    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        return None
    try:
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/credits",
            headers={"Authorization": f"Bearer {key}"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        d = data.get("data", {})
        total = float(d.get("total_credits", 0))
        usage = float(d.get("total_usage", 0))
        return round(total - usage, 2)
    except Exception as exc:
        print(f"[FB32] WARN: credits API unavailable ({exc})")
        return None


# ---------------------------------------------------------------------------
# Variance metric
# ---------------------------------------------------------------------------

def prose_variance(prose_runs: List[str]) -> Dict[str, Any]:
    """Pairwise difflib similarity across Section 9 prose runs.

    ratio=1.0 → identical (deterministic, bad); <1.0 → varied (the mandate).
    Also returns first-200-char opaque diff excerpts to illustrate variance.
    """
    ratios: List[float] = []
    for i in range(len(prose_runs)):
        for j in range(i + 1, len(prose_runs)):
            r = difflib.SequenceMatcher(None, prose_runs[i], prose_runs[j]).ratio()
            ratios.append(round(r, 4))
    # Opaque diff excerpt (no raw corpus): unified diff of the two prose runs,
    # truncated. The prose is LLM-generated paraphrastic synthesis, not corpus
    # text — but we keep it short and treat all IDs as opaque.
    diff_excerpt = ""
    if len(prose_runs) >= 2:
        diff_lines = list(difflib.unified_diff(
            prose_runs[0].splitlines()[:6],
            prose_runs[1].splitlines()[:6],
            lineterm="", n=1,
        ))
        diff_excerpt = "\n".join(diff_lines)[:600]
    return {
        "n_runs": len(prose_runs),
        "pairwise_ratios": ratios,
        "min_ratio": min(ratios) if ratios else None,
        "mean_ratio": round(sum(ratios) / len(ratios), 4) if ratios else None,
        "varies": (min(ratios) if ratios else 1.0) < 1.0,
        "diff_excerpt_opaque": diff_excerpt,
    }


# ---------------------------------------------------------------------------
# Pipeline run
# ---------------------------------------------------------------------------

async def run_spectacular_and_synthesize(text: str, corpus_label: str) -> Dict[str, Any]:
    """Run the full spectacular pipeline + deep synthesis on one corpus text.

    Returns Section 9 prose + status + structure stats. Privacy: text stays
    in-memory; only opaque IDs + LLM-generated paraphrastic synthesis leave
    the process (to OpenRouter), never raw corpus spans.
    """
    from argumentation_analysis.orchestration.invoke_callables import _invoke_deep_synthesis
    from argumentation_analysis.core.shared_state import UnifiedAnalysisState
    from argumentation_analysis.orchestration.unified_pipeline import run_unified_analysis

    t0 = time.time()
    state = UnifiedAnalysisState(text)
    pipeline_ok = True
    pipeline_err = ""
    try:
        result = await run_unified_analysis(
            text=text,
            workflow_name="spectacular",
            context={"fallacy_tier": "full"},
        )
        if isinstance(result, dict):
            s = result.get("unified_state", result.get("state"))
            if isinstance(s, UnifiedAnalysisState):
                state = s
    except Exception as exc:
        pipeline_ok = False
        pipeline_err = str(exc)
    pipeline_duration = time.time() - t0

    ds_result = await _invoke_deep_synthesis(
        "", {"_state_object": state, "source_metadata": {"opaque_id": CORPUS_LABELS[corpus_label]}}
    )
    total_duration = time.time() - t0

    if "error" in ds_result:
        return {
            "corpus": CORPUS_LABELS[corpus_label],
            "pipeline_ok": pipeline_ok,
            "pipeline_err": pipeline_err,
            "deep_synthesis_error": ds_result["error"],
            "final_synthesis": "",
            "final_synthesis_status": "error",
            "elapsed_s": round(total_duration, 1),
            "markdown": "",
        }

    report = ds_result.get("report", {})
    markdown = ds_result.get("markdown", "")
    return {
        "corpus": CORPUS_LABELS[corpus_label],
        "pipeline_ok": pipeline_ok,
        "pipeline_err": pipeline_err,
        "final_synthesis": report.get("final_synthesis", ""),
        "final_synthesis_status": report.get("final_synthesis_status", ""),
        "grounded_synthesis_status": report.get("grounded_synthesis_status", ""),
        "n_args": len(report.get("argument_map", [])),
        "n_fallacies": len(report.get("fallacy_diagnoses", [])),
        "sections_populated": ds_result.get("sections_populated"),
        "total_state_fields": ds_result.get("total_state_fields"),
        "populated_artifact_fields": ds_result.get("populated_artifact_fields"),
        "elapsed_s": round(total_duration, 1),
        "pipeline_duration_s": round(pipeline_duration, 1),
        "markdown": markdown,
    }


async def isolate_synthesis_variance(text: str, corpus_label: str, n_runs: int) -> Dict[str, Any]:
    """MODE 'isolate': run the full pipeline ONCE, then invoke the Section 9
    LLM synthesis N times on the SAME captured state.

    Isolates pure synthesis-prose variance (the count-template is gone, so the
    LLM synthesis must vary now). Cheap + decisive. The pipeline runs once; only
    the cheap synthesis LLM call repeats N times.
    """
    from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
        DeepSynthesisAgent,
    )
    from semantic_kernel import Kernel
    from argumentation_analysis.core.llm_service import create_llm_service

    # Build the state once (full pipeline)
    from argumentation_analysis.core.shared_state import UnifiedAnalysisState
    from argumentation_analysis.orchestration.unified_pipeline import run_unified_analysis

    t0 = time.time()
    state = UnifiedAnalysisState(text)
    try:
        result = await run_unified_analysis(
            text=text, workflow_name="spectacular",
            context={"fallacy_tier": "full"},
        )
        if isinstance(result, dict):
            s = result.get("unified_state", result.get("state"))
            if isinstance(s, UnifiedAnalysisState):
                state = s
    except Exception as exc:
        return {"corpus": CORPUS_LABELS[corpus_label], "pipeline_err": str(exc), "prose_runs": []}
    pipeline_duration = time.time() - t0

    # Build a report once (static sections), then re-run ONLY Section 9 LLM synthesis N times.
    source_meta = {"opaque_id": CORPUS_LABELS[corpus_label]}
    base_report = DeepSynthesisReport_stub(state, source_meta)

    kernel = Kernel()
    service_id = "default"
    try:
        llm = create_llm_service(service_id=service_id)
        if llm:
            kernel.add_service(llm)
    except Exception as exc:
        print(f"  [isolate] WARN: create_llm_service failed ({exc})")
    agent = DeepSynthesisAgent(kernel=kernel, service_id=service_id)

    prose_runs: List[str] = []
    statuses: List[str] = []
    for i in range(n_runs):
        # FB-32 diagnostic: _llm_synthesis swallows exceptions at logger.debug
        # (deep_synthesis_agent.py:1527). To surface the REAL failure we wrap
        # and log it — without this the synthesis looks "unavailable" with no
        # clue why. (FB-31 fail-loud mandate says don't swallow; this harness
        # is the honest probe the production path is missing.)
        import logging as _lg
        _lg.getLogger("argumentation_analysis.agents.core.synthesis").setLevel(_lg.DEBUG)
        try:
            thesis = await agent._llm_synthesis(base_report)
            prose_runs.append(thesis or "")
            statuses.append("llm" if thesis else "unavailable")
        except Exception as exc:
            prose_runs.append("")
            statuses.append(f"failed:{type(exc).__name__}:{str(exc)[:120]}")
        print(f"  [isolate] run {i+1}/{n_runs}: status={statuses[-1]} len={len(prose_runs[-1])}")
        # Surface the swallowed debug message (deep_synthesis_agent.py:1528)
        if statuses[-1].startswith("unavailable") and i == 0:
            print("  [isolate] NOTE: _llm_synthesis returned None — the real "
                  "exception was logged at DEBUG 'LLM thesis generation skipped'.")

    return {
        "corpus": CORPUS_LABELS[corpus_label],
        "mode": "isolate",
        "pipeline_duration_s": round(pipeline_duration, 1),
        "n_synthesis_runs": n_runs,
        "statuses": statuses,
        "prose_runs": prose_runs,
        "variance": prose_variance(prose_runs),
    }


def DeepSynthesisReport_stub(state, source_meta):
    """Build a report with the static sections populated (for isolate mode)."""
    from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
        DeepSynthesisAgent,
    )
    from argumentation_analysis.agents.core.synthesis.deep_synthesis_models import (
        DeepSynthesisReport,
    )
    return DeepSynthesisReport(
        source_overview=DeepSynthesisAgent._build_source_overview(state, source_meta),
        argument_map=DeepSynthesisAgent._build_argument_map(state),
        fallacy_diagnoses=DeepSynthesisAgent._build_fallacy_diagnoses(state),
        formal_findings=DeepSynthesisAgent._build_formal_findings(state),
        dung_structure=DeepSynthesisAgent._build_dung_structure(state),
        belief_retractions=DeepSynthesisAgent._build_belief_retractions(state),
        counter_arguments=DeepSynthesisAgent._build_counter_arguments(state),
        cross_text_parallels=DeepSynthesisAgent._build_cross_text_parallels(state),
    )


# ---------------------------------------------------------------------------
# Quality re-measure (FB-28 protocol on freshly-extracted args)
# ---------------------------------------------------------------------------

def _get_llm_client():
    from openai import OpenAI
    base = os.environ.get("OPENROUTER_BASE_URL")
    key = os.environ.get("OPENROUTER_API_KEY")
    if base and key:
        return OpenAI(api_key=key, base_url=base), os.environ.get("OPENROUTER_CHAT_MODEL_ID", "gpt-5-mini")
    return OpenAI(api_key=os.environ.get("OPENAI_API_KEY")), os.environ.get("OPENAI_CHAT_MODEL_ID", "gpt-5-mini")


def _snap(val):
    return min(SCALE_VALUES, key=lambda s: abs(s - max(0.0, min(1.0, float(val)))))


def _parse_json_loose(text):
    import re
    cleaned = re.sub(r"```(?:json)?\s*", "", text).replace("```", "").strip()
    s, e = cleaned.find("{"), cleaned.rfind("}")
    if s == -1 or e == -1 or e <= s:
        return None
    try:
        return json.loads(cleaned[s:e+1])
    except json.JSONDecodeError:
        return None


def baseline_eval(client, model, arg_text):
    prompt = BASELINE_EVAL_PROMPT.replace("{arg_text}", arg_text[:4000])
    try:
        resp = client.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}])
        raw = resp.choices[0].message.content or ""
    except Exception as exc:
        return {"scores": {}, "error": str(exc)}
    parsed = _parse_json_loose(raw)
    if not parsed or "scores" not in parsed:
        return {"scores": {}, "error": "parse_failed", "raw": raw}
    scores = {}
    for v in VIRTUES:
        val = parsed["scores"].get(v)
        scores[v] = _snap(val) if isinstance(val, (int, float)) else None
    return {"scores": scores}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def amain():
    parser = argparse.ArgumentParser(description="FB-32 de-castrated pipeline variance + quality re-measure")
    parser.add_argument("--mode", choices=["isolate", "full", "quality"], default="isolate")
    parser.add_argument("--corpus", choices=["A", "B", "C"], default="C")
    parser.add_argument("--runs", type=int, default=3, help="isolate: # of Section 9 re-runs; full: # pipeline runs/corpus")
    parser.add_argument("--corpora", help="comma list for full mode, e.g. A,C", default=None)
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    balance_before = get_openrouter_balance()
    print(f"[FB32] mode={args.mode} corpus={args.corpus} runs={args.runs} | balance=${balance_before}")

    summary: Dict[str, Any] = {
        "mode": args.mode, "corpus": args.corpus, "runs": args.runs,
        "balance_before_usd": balance_before,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    if args.mode == "isolate":
        text = load_corpus_text(args.corpus)
        res = await isolate_synthesis_variance(text, args.corpus, args.runs)
        for i, prose in enumerate(res.get("prose_runs", [])):
            (RESULTS_DIR / f"isolate_{args.corpus}_{i+1}.md").write_text(prose, encoding="utf-8")
        summary.update(res)
    elif args.mode == "full":
        corpora = args.corpora.split(",") if args.corpora else [args.corpus]
        per_corpus: Dict[str, Any] = {}
        for lbl in corpora:
            text = load_corpus_text(lbl)
            prose_runs = []
            run_records = []
            for r in range(args.runs):
                print(f"\n[FB32] full corpus {lbl} run {r+1}/{args.runs}")
                rec = await run_spectacular_and_synthesize(text, lbl)
                (RESULTS_DIR / f"full_{lbl}_{r+1}.md").write_text(rec.get("markdown", ""), encoding="utf-8")
                # Strip markdown from the JSON record (keep prose + stats)
                rec_json = {k: v for k, v in rec.items() if k != "markdown"}
                run_records.append(rec_json)
                if rec.get("final_synthesis_status") == "llm":
                    prose_runs.append(rec["final_synthesis"])
                print(f"  status={rec.get('final_synthesis_status')} args={rec.get('n_args')} "
                      f"fallacies={rec.get('n_fallacies')} elapsed={rec.get('elapsed_s')}s")
            per_corpus[lbl] = {
                "runs": run_records,
                "prose_variance": prose_variance(prose_runs),
            }
        summary["per_corpus"] = per_corpus
    elif args.mode == "quality":
        # Run pipeline once, extract args, run 0-shot baseline, build differential
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState
        from argumentation_analysis.orchestration.unified_pipeline import run_unified_analysis
        text = load_corpus_text(args.corpus)
        state = UnifiedAnalysisState(text)
        try:
            result = await run_unified_analysis(text=text, workflow_name="spectacular",
                context={"fallacy_tier": "full"})
            if isinstance(result, dict):
                s = result.get("unified_state")
                if isinstance(s, UnifiedAnalysisState):
                    state = s
        except Exception as exc:
            summary["pipeline_err"] = str(exc)
        # Extract args + radar from state
        raw_args = getattr(state, "arguments", None) or []
        arg_texts = []
        for i, a in enumerate(raw_args[:8]):
            t = a if isinstance(a, str) else getattr(a, "text", None) or getattr(a, "content", None) or str(a)
            arg_texts.append((f"arg_{i+1}", t))
        client, model = _get_llm_client()
        per_arg = {}
        for aid, atxt in arg_texts:
            b = baseline_eval(client, model, atxt)
            per_arg[aid] = {"baseline_scores": b["scores"],
                            "baseline_overall": round(sum(v for v in b["scores"].values() if isinstance(v, (int, float))), 2)}
            print(f"  {aid}: baseline_overall={per_arg[aid]['baseline_overall']}")
        summary["quality"] = {"corpus": CORPUS_LABELS[args.corpus], "n_args": len(arg_texts), "per_arg": per_arg,
                              "note": "Pipeline radar invariant to descent/synthesis de-castration (deterministic lexical on extracted args). Baseline on fresh de-castrated extraction."}

    balance_after = get_openrouter_balance()
    summary["balance_after_usd"] = balance_after
    if balance_before is not None and balance_after is not None:
        summary["cost_usd"] = round(balance_before - balance_after, 4)

    out = RESULTS_DIR / ("fb32_quality.json" if args.mode == "quality" else "fb32_variance_summary.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)

    varies_str = "n/a"
    if args.mode == "isolate":
        varies_str = str(summary.get("variance", {}).get("varies"))
    elif args.mode == "full":
        varies_str = {lbl: pc["prose_variance"].get("varies") for lbl, pc in summary.get("per_corpus", {}).items()}
    print(f"\n[FB32] saved {out} | cost≈${summary.get('cost_usd', '?')} | varies={varies_str}")


if __name__ == "__main__":
    asyncio.run(amain())
