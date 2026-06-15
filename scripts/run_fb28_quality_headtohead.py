"""FB-28 — Quality axis content-dominance test (#1102, Epic #947).

Head-to-head: pipeline 9-virtue radar (deterministic, from FB-25 artifacts)
vs 0-shot LLM baseline evaluating the SAME extracted arguments on the SAME
9 virtues + SAME scale {0.0, 0.2, 0.5, 1.0}.

The comparison isolates *content-dominance* (does the pipeline's analytical
content separate from the baseline's?) from *existence-dominance* (does the
pipeline emit a radar the baseline does not?). By feeding the baseline the
SAME extracted args, we neutralise extraction-variance: both sides judge the
same units. The differential is then pure evaluation-capability.

Anti-théâtre (#1019): the pipeline radar is NOT tuned to score higher. The
deliverable is the honest differential, whichever direction it goes.

Privacy HARD: corpus/args are loaded in-memory from the encrypted blob via
the FB-25 artifacts (already scrubbed to opaque arg_N IDs + paraphrased text,
no raw_text / no speaker names). Results are gitignored under evaluation/.
The aggregate report (docs/reports/) uses opaque IDs only.

Usage:
    conda run -n projet-is-roo-new --no-capture-output python \\
        scripts/run_fb28_quality_headtohead.py [--corpus A]

Output (gitignored):
    evaluation/results/capstone_c1/
        fb28_headtohead_A.json  fb28_headtohead_B.json  fb28_headtohead_C.json
        fb28_summary.json
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))
os.chdir(Path(__file__).parent.parent)

# Load .env (OPENROUTER_API_KEY / OPENROUTER_BASE_URL / OPENAI_API_KEY)
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    with open(_env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())

RESULTS_DIR = Path("argumentation_analysis/evaluation/results/capstone_c1")
FB25_ARGS_DIR = RESULTS_DIR  # fb25_quality_args_{A,B,C}.json live here
CORPUS_LABELS = {"A": "doc_A", "B": "doc_B", "C": "doc_C"}

# The 9 virtues — EXACT match to ArgumentQualityEvaluator.VERTUES (quality_evaluator.py:217).
VIRTUES = [
    "clarte",
    "pertinence",
    "presence_sources",
    "refutation_constructive",
    "structure_logique",
    "analogie_pertinente",
    "fiabilite_sources",
    "exhaustivite",
    "redondance_faible",
]
SCALE_VALUES = [0.0, 0.2, 0.5, 1.0]
MAX_SCALE = 1.0
N_VIRTUES = len(VIRTUES)  # 9

# 0-shot baseline prompt: evaluate ONE argument on the SAME 9 virtues + SAME scale.
# This makes the differential apples-to-apples (same units, same rubric).
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


def load_pipeline_args(corpus_label: str) -> Tuple[Dict[str, str], Dict[str, Dict[str, Any]]]:
    """Load FB-25 extracted args + pipeline radar scores (replayable artifacts).

    Returns (arg_id -> paraphrased text, arg_id -> {scores, overall, llm_assessment}).
    The arg text here is already the pipeline's paraphrased extraction (opaque,
    no raw_text) — safe to feed the baseline.
    """
    path = FB25_ARGS_DIR / f"fb25_quality_args_{corpus_label}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"FB-25 artifact missing: {path}. Run scripts/run_capstone_c1.py first "
            "(or restore the FB-25 quality run)."
        )
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    args = data.get("arguments", {})
    pipeline_scores = data.get("argument_quality_scores", {})
    return args, pipeline_scores


def _get_llm_client():
    """OpenRouter-toggle-aware client (same provider as pipeline, FB-21 lesson)."""
    from openai import OpenAI

    openrouter_base_url = os.environ.get("OPENROUTER_BASE_URL")
    openrouter_api_key = os.environ.get("OPENROUTER_API_KEY")
    use_openrouter = bool(openrouter_base_url and openrouter_api_key)
    if use_openrouter:
        model = os.environ.get("OPENROUTER_CHAT_MODEL_ID", "gpt-5-mini")
        client = OpenAI(api_key=openrouter_api_key, base_url=openrouter_base_url)
    else:
        model = os.environ.get("OPENAI_CHAT_MODEL_ID", "gpt-5-mini")
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    return client, model


def baseline_eval_argument(client: Any, model: str, arg_text: str) -> Dict[str, Any]:
    """Ask the 0-shot baseline to evaluate one arg on the 9 virtues + scale.

    Returns {"scores": {virtue: float}, "justification": str, "raw": str}.
    On parse failure, scores default to None (honest unavailable, not fabricated).
    """
    prompt = BASELINE_EVAL_PROMPT.replace("{arg_text}", arg_text[:4000])
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = ""
        choice = response.choices[0]
        if choice.message and choice.message.content:
            raw = choice.message.content
    except Exception as exc:
        return {"scores": {}, "justification": "", "raw": "", "error": str(exc)}

    # Parse JSON (tolerate markdown code fences / leading text)
    parsed = _parse_json_loose(raw)
    if parsed is None or "scores" not in parsed:
        return {"scores": {}, "justification": "", "raw": raw, "error": "parse_failed"}

    scores_raw = parsed.get("scores", {})
    # Coerce to scale values; clamp to {0.0, 0.2, 0.5, 1.0} (snap to nearest).
    scores = {}
    for v in VIRTUES:
        val = scores_raw.get(v)
        if isinstance(val, (int, float)):
            scores[v] = _snap_to_scale(float(val))
        else:
            scores[v] = None  # honest unavailable
    return {
        "scores": scores,
        "justification": str(parsed.get("justification", ""))[:300],
        "raw": raw,
    }


def _snap_to_scale(val: float) -> float:
    """Snap a float to the nearest scale value {0.0, 0.2, 0.5, 1.0}."""
    return min(SCALE_VALUES, key=lambda s: abs(s - max(0.0, min(1.0, val))))


def _parse_json_loose(text: str) -> Any:
    """Parse JSON tolerating code fences and surrounding prose."""
    import re

    # Strip markdown code fences
    cleaned = re.sub(r"```(?:json)?\s*", "", text)
    cleaned = cleaned.replace("```", "").strip()
    # Find first {...} block
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError:
        return None


def overall_from_scores(scores: Dict[str, Any]) -> float:
    """Sum of non-None scores (same aggregation as pipeline: overall = sum)."""
    return round(sum(v for v in scores.values() if isinstance(v, (int, float))), 2)


def run_headtohead_corpus(corpus_label: str, max_args: int = 8) -> Dict[str, Any]:
    """Run head-to-head for one corpus: pipeline (loaded) vs baseline (live)."""
    args, pipeline_scores = load_pipeline_args(corpus_label)
    arg_ids = list(args.keys())[:max_args]  # cap to match pipeline radar window

    client, model = _get_llm_client()
    print(f"[FB28] corpus {corpus_label}: {len(arg_ids)} args to evaluate (baseline)")

    per_arg = {}
    for i, arg_id in enumerate(arg_ids, 1):
        arg_text = args[arg_id]
        t0 = time.time()
        baseline_result = baseline_eval_argument(client, model, arg_text)
        elapsed = time.time() - t0
        pipe = pipeline_scores.get(arg_id, {})
        per_arg[arg_id] = {
            "pipeline": {
                "scores": pipe.get("scores", {}),
                "overall": pipe.get("overall"),
            },
            "baseline": {
                "scores": baseline_result["scores"],
                "overall": overall_from_scores(baseline_result["scores"]),
                "justification": baseline_result.get("justification", ""),
                "parse_error": baseline_result.get("error"),
                "elapsed_s": round(elapsed, 1),
            },
        }
        print(
            f"  [{i}/{len(arg_ids)}] {arg_id}: "
            f"pipeline_overall={pipe.get('overall')}  "
            f"baseline_overall={per_arg[arg_id]['baseline']['overall']}  "
            f"({elapsed:.1f}s)"
        )

    return {
        "corpus": CORPUS_LABELS[corpus_label],
        "method": "fb28_headtohead",
        "model": model,
        "n_args": len(arg_ids),
        "per_argument": per_arg,
    }


def build_differential(results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Build the per-virtue + per-corpus differential table.

    For each virtue and corpus: mean pipeline score, mean baseline score,
    delta (pipeline - baseline), and the per-arg win/tie/lose counts.
    """
    diff = {}
    for corpus_label, corpus_res in results.items():
        per_arg = corpus_res.get("per_argument")
        if per_arg is None:
            # corpus errored (no per_argument) — record honest unavailable
            diff[corpus_label] = {
                "corpus": CORPUS_LABELS.get(corpus_label, corpus_label),
                "error": corpus_res.get("error", "no per_argument"),
            }
            continue
        n = len(per_arg)
        # Per-virtue means (only args where BOTH sides scored that virtue)
        virtue_means = {v: {"pipeline": [], "baseline": []} for v in VIRTUES}
        overall_pipe = []
        overall_base = []
        win_tie_lose = {"pipeline_gt": 0, "tie": 0, "baseline_ge": 0}
        for arg_id, entry in per_arg.items():
            ps = entry["pipeline"]["scores"]
            bs = entry["baseline"]["scores"]
            po = entry["pipeline"]["overall"]
            bo = entry["baseline"]["overall"]
            if isinstance(po, (int, float)):
                overall_pipe.append(po)
            if isinstance(bo, (int, float)):
                overall_base.append(bo)
            # overall comparison
            if isinstance(po, (int, float)) and isinstance(bo, (int, float)):
                if po > bo:
                    win_tie_lose["pipeline_gt"] += 1
                elif po == bo:
                    win_tie_lose["tie"] += 1
                else:
                    win_tie_lose["baseline_ge"] += 1
            for v in VIRTUES:
                pv = ps.get(v)
                bv = bs.get(v)
                if isinstance(pv, (int, float)):
                    virtue_means[v]["pipeline"].append(pv)
                if isinstance(bv, (int, float)):
                    virtue_means[v]["baseline"].append(bv)

        # Aggregate per-virtue
        per_virtue = {}
        for v in VIRTUES:
            p_list = virtue_means[v]["pipeline"]
            b_list = virtue_means[v]["baseline"]
            p_mean = round(sum(p_list) / len(p_list), 3) if p_list else None
            b_mean = round(sum(b_list) / len(b_list), 3) if b_list else None
            delta = round(p_mean - b_mean, 3) if (p_mean is not None and b_mean is not None) else None
            per_virtue[v] = {
                "pipeline_mean": p_mean,
                "baseline_mean": b_mean,
                "delta_pipeline_minus_baseline": delta,
            }

        diff[corpus_label] = {
            "corpus": CORPUS_LABELS[corpus_label],
            "n_args": n,
            "overall_mean": {
                "pipeline": round(sum(overall_pipe) / len(overall_pipe), 3) if overall_pipe else None,
                "baseline": round(sum(overall_base) / len(overall_base), 3) if overall_base else None,
            },
            "overall_win_tie_lose": win_tie_lose,
            "per_virtue": per_virtue,
        }
    return diff


def main():
    parser = argparse.ArgumentParser(description="FB-28 quality head-to-head")
    parser.add_argument("--corpus", choices=["A", "B", "C"], default=None)
    parser.add_argument("--max-args", type=int, default=8)
    args_cli = parser.parse_args()

    corpus_list = [args_cli.corpus] if args_cli.corpus else ["A", "B", "C"]
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    results = {}
    for label in corpus_list:
        print(f"\n{'='*60}\n[FB28] corpus {label}\n{'='*60}")
        try:
            res = run_headtohead_corpus(label, max_args=args_cli.max_args)
            results[label] = res
            out_path = RESULTS_DIR / f"fb28_headtohead_{label}.json"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(res, f, indent=2, ensure_ascii=False, default=str)
            print(f"[FB28] saved {out_path}")
        except Exception as exc:
            print(f"[FB28] corpus {label} FAILED: {exc}")
            results[label] = {"corpus": CORPUS_LABELS[label], "error": str(exc)}

    diff = build_differential(results)
    summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "method": "fb28_quality_headtohead",
        "description": "Pipeline 9-virtue radar vs 0-shot baseline on SAME extracted args",
        "differential": diff,
    }
    summary_path = RESULTS_DIR / "fb28_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n[FB28] Summary + differential saved to {summary_path}")

    # Console differential preview
    print(f"\n{'='*60}\n[FB28] DIFFERENTIAL (pipeline - baseline)\n{'='*60}")
    for label in corpus_list:
        d = diff.get(label, {})
        om = d.get("overall_mean", {})
        wtl = d.get("overall_win_tie_lose", {})
        print(
            f"  {CORPUS_LABELS[label]}: overall pipe={om.get('pipeline')} "
            f"base={om.get('baseline')} | win/tie/lose={wtl}"
        )


if __name__ == "__main__":
    main()
