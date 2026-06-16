"""FB-29 — Agentic blindspot-virtue head-to-head (#1105, Epic #947).

Re-runs the FB-28 quality head-to-head methodology, but with the pipeline's
TWO joint-zero blindspot virtues upgraded to **multi-step agentic detectors**
(see ``agentic_virtue_detectors.py``): ``refutation_constructive`` and
``analogie_pertinente``. The other 7 virtues stay deterministic/lexical.

Question (FB-29 #1105 DoD): does the UPGRADED pipeline now **separate** from
the 0-shot baseline on the content of those 2 virtues — i.e. exhibit STRUCTURE
(located rebuttal-target / domain-mapping) the 0-shot call does not surface?

Honest fork (anti-#1019, anti-pendule):
- Higher numbers ALONE do NOT count (FB-28 proved stricter≠better). The
  content-separation claim requires DEMONSTRATED structure shown on real args.
- The agentic detectors emit ``exhibit`` fields (the located opposing claim +
  engagement verdict, or the domains + structural mapping). Those exhibits ARE
  the content-separation evidence: a 0-shot call emits one score, not a chain.
- If the exhibits are vacuous (no located target / surface mapping) even where
  the score rose → the rise is theatre, EDGES stands.

Privacy HARD: corpus/args are loaded in-memory from the encrypted blob via the
FB-25 artifacts (already scrubbed to opaque arg_N IDs + paraphrased text, no
raw_text / no speaker names). Results gitignored under evaluation/. The
aggregate report uses opaque IDs only.

Usage:
    conda run -n projet-is-roo-new --no-capture-output python \\
        scripts/run_fb29_agentic_headtohead.py [--corpus A]

Output (gitignored):
    evaluation/results/capstone_c1/
        fb29_agentic_A.json  fb29_agentic_B.json  fb29_agentic_C.json
        fb29_summary.json
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

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

RESULTS_DIR = Path("argumentation_analysis/evaluation/results/capstone_c1")
FB25_ARGS_DIR = RESULTS_DIR
CORPUS_LABELS = {"A": "doc_A", "B": "doc_B", "C": "doc_C"}

# The 9 virtues + scale — EXACT match to ArgumentQualityEvaluator (FB-28 reuse).
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
# The virtues upgraded to agentic multi-step detection. FB-29 #1105: the 2
# joint-zero blindspot virtues. FB-38 #1127: +5 remaining tractable virtues
# (clarte, pertinence, structure_logique, exhaustivite, redondance_faible).
# Derived from the registry (source of truth) so this harness always runs every
# agentic detector wired into the evaluator. Only presence_sources /
# fiabilite_sources stay lexical (genuine absence of citations — #1127 forbids
# fabricating them).
from argumentation_analysis.agents.core.quality.agentic_virtue_detectors import (
    AGENTIC_DETECTORS,
)

AGENTIC_UPGRADED_VIRTUES = list(AGENTIC_DETECTORS.keys())

# 0-shot baseline prompt — IDENTICAL to FB-28 (apples-to-apples: same rubric,
# same scale). The baseline side must not change between FB-28 and FB-29 so the
# differential isolates the AGENTIC UPGRADE on the pipeline side.
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
    """Load FB-25 extracted args + the FB-28 lexical pipeline scores (baseline-for-comparison).

    The FB-28 lexical scores let the FB-29 report show the BEFORE (lexical 0.0)
    vs AFTER (agentic) delta on the 2 upgraded virtues, isolating the upgrade.
    """
    path = FB25_ARGS_DIR / f"fb25_quality_args_{corpus_label}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"FB-25 artifact missing: {path}. Run scripts/run_capstone_c1.py first."
        )
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    args = data.get("arguments", {})
    fb28_pipeline_scores = data.get("argument_quality_scores", {})
    return args, fb28_pipeline_scores


def _get_llm_client():
    """OpenRouter-toggle-aware client (FB-21 lesson, FB-28 reuse).

    FB-38: a per-call ``timeout`` + bounded ``max_retries`` is mandatory. The
    default OpenAI client has an effectively-unbounded read timeout, so a single
    hung upstream call blocks the whole run indefinitely (observed: 25 min
    wall, 2% CPU, zero per-arg progress — indistinguishable from a hang). This
    is a fail-loud bound on an unbounded operation, not a counterweight
    (anti-pendule): the operation is unchanged when it succeeds, it just fails
    loudly instead of hanging silently when the upstream stalls.
    """
    from openai import OpenAI

    openrouter_base_url = os.environ.get("OPENROUTER_BASE_URL")
    openrouter_api_key = os.environ.get("OPENROUTER_API_KEY")
    use_openrouter = bool(openrouter_base_url and openrouter_api_key)
    # Generous ceiling for reasoning-model calls on complex detector prompts.
    call_timeout = float(os.environ.get("FB38_CALL_TIMEOUT", "120"))
    if use_openrouter:
        model = os.environ.get("OPENROUTER_CHAT_MODEL_ID", "gpt-5-mini")
        client = OpenAI(
            api_key=openrouter_api_key,
            base_url=openrouter_base_url,
            timeout=call_timeout,
            max_retries=1,
        )
    else:
        model = os.environ.get("OPENAI_CHAT_MODEL_ID", "gpt-5-mini")
        client = OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY"),
            timeout=call_timeout,
            max_retries=1,
        )
    return client, model


def _make_llm_callable(client: Any, model: str) -> Callable[[str], str]:
    """Wrap the chat-completions client as a ``str -> str`` callable for the
    agentic detectors (which expect that contract).

    FB-38: logs per-call elapsed + reasoning-token count to stderr, so a
    slow-but-progressing run is visible and distinguishable from a hang.
    """

    def call(prompt: str) -> str:
        t0 = time.time()
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        dt = time.time() - t0
        usage = getattr(response, "usage", None)
        rtoks = (
            getattr(usage.completion_tokens_details, "reasoning_tokens", None)
            if usage and getattr(usage, "completion_tokens_details", None)
            else None
        )
        print(
            f"    [llm] {dt:.1f}s rtok={rtoks} prompt_len={len(prompt)}",
            file=sys.stderr,
            flush=True,
        )
        choice = response.choices[0]
        return (choice.message.content if choice.message and choice.message.content else "") or ""

    return call


def _snap_to_scale(val: Any) -> float:
    return min(SCALE_VALUES, key=lambda s: abs(s - max(0.0, min(1.0, float(val)))))


def _parse_json_loose(text: str) -> Any:
    import re

    cleaned = re.sub(r"```(?:json)?\s*", "", text)
    cleaned = cleaned.replace("```", "").strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError:
        return None


def agentic_pipeline_eval_argument(
    llm_callable: Callable[[str], str], arg_text: str
) -> Dict[str, Any]:
    """Run the UPGRADED pipeline radar on one arg (agentic on the 2 virtues).

    Returns the full 9-virtue scores + the exhibits for the upgraded virtues.
    The exhibits (located opposing claim + verdict / domains + mapping) are the
    content-separation evidence — a 0-shot call does not emit them.
    """
    from argumentation_analysis.agents.core.quality.quality_evaluator import (
        ArgumentQualityEvaluator,
    )
    from argumentation_analysis.agents.core.quality.agentic_virtue_detectors import (
        AgenticDetectorError,
    )

    evaluator = ArgumentQualityEvaluator()
    exhibits: Dict[str, str] = {}
    scores: Dict[str, float] = {}

    # Run the 2 upgraded virtues through their agentic chains directly (to
    # capture the exhibit), the other 7 through the standard evaluator.
    # This mirrors evaluate(agentic_llm=...) but exposes the per-virtue comment.
    from argumentation_analysis.agents.core.quality.agentic_virtue_detectors import (
        AGENTIC_DETECTORS,
    )

    for virtue in AGENTIC_UPGRADED_VIRTUES:
        try:
            score, comment = AGENTIC_DETECTORS[virtue](arg_text, llm=llm_callable)
            scores[virtue] = score
            exhibits[virtue] = comment  # embeds the located structure
        except AgenticDetectorError as exc:
            # Fail-loud: record the failure honestly (not a synthetic 0.0).
            scores[virtue] = None  # type: ignore[assignment]
            exhibits[virtue] = f"AGENTIC_FAIL: {exc}"

    # The 7 lexical virtues via the standard evaluator (deterministic).
    try:
        full = evaluator.evaluate(arg_text)  # no agentic_llm → lexical for all
        lexical_scores = full.get("scores_par_vertu", {})
        for v in VIRTUES:
            if v not in scores:  # not an upgraded virtue
                scores[v] = lexical_scores.get(v, 0.0)
    except RuntimeError as exc:
        # spacy/textstat unavailable on this env — record honestly. The 7
        # lexical scores are unavailable, but the 2 upgraded ones (already
        # computed) stand.
        for v in VIRTUES:
            if v not in scores:
                scores[v] = None  # type: ignore[assignment]
        exhibits["_lexical_error"] = str(exc)[:200]

    overall = round(
        sum(s for s in scores.values() if isinstance(s, (int, float))), 2
    )
    return {"scores": scores, "overall": overall, "exhibits": exhibits}


def baseline_eval_argument(client: Any, model: str, arg_text: str) -> Dict[str, Any]:
    """0-shot baseline: identical rubric to FB-28 (apples-to-apples)."""
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

    parsed = _parse_json_loose(raw)
    if parsed is None or "scores" not in parsed:
        return {"scores": {}, "justification": "", "raw": raw, "error": "parse_failed"}

    scores_raw = parsed.get("scores", {})
    scores: Dict[str, Any] = {}
    for v in VIRTUES:
        val = scores_raw.get(v)
        if isinstance(val, (int, float)):
            scores[v] = _snap_to_scale(float(val))
        else:
            scores[v] = None
    return {
        "scores": scores,
        "justification": str(parsed.get("justification", ""))[:300],
        "raw": raw,
    }


def run_corpus(corpus_label: str, max_args: int = 8) -> Dict[str, Any]:
    """Run FB-29 head-to-head for one corpus: agentic pipeline vs 0-shot baseline."""
    args, fb28_scores = load_pipeline_args(corpus_label)
    arg_ids = list(args.keys())[:max_args]

    client, model = _get_llm_client()
    llm_callable = _make_llm_callable(client, model)
    print(f"[FB29] corpus {corpus_label}: {len(arg_ids)} args (agentic pipeline + 0-shot baseline)")

    per_arg: Dict[str, Any] = {}
    for i, arg_id in enumerate(arg_ids, 1):
        arg_text = args[arg_id]
        t0 = time.time()
        pipe = agentic_pipeline_eval_argument(llm_callable, arg_text)
        base = baseline_eval_argument(client, model, arg_text)
        elapsed = time.time() - t0
        fb28 = fb28_scores.get(arg_id, {})
        per_arg[arg_id] = {
            "agentic_pipeline": {
                "scores": pipe["scores"],
                "overall": pipe["overall"],
                "exhibits": pipe["exhibits"],
            },
            "baseline_0shot": {
                "scores": base["scores"],
                "overall": round(
                    sum(s for s in base["scores"].values() if isinstance(s, (int, float))), 2
                ),
                "justification": base.get("justification", ""),
                "parse_error": base.get("error"),
            },
            "fb28_lexical": {  # BEFORE the upgrade — to show the delta isolates the upgrade
                "scores": fb28.get("scores", {}),
                "overall": fb28.get("overall"),
            },
        }
        # Console preview: how many upgraded virtues does the agentic pipeline
        # separate ABOVE the 0-shot baseline on THIS arg (pipe>base). The
        # content-separation claim lives in these per-arg separations + exhibits.
        ps = pipe["scores"]
        bs = base["scores"]
        base_overall = round(
            sum(s for s in bs.values() if isinstance(s, (int, float))), 2
        )
        up_separating = sum(
            1
            for v in AGENTIC_UPGRADED_VIRTUES
            if isinstance(ps.get(v), (int, float))
            and isinstance(bs.get(v), (int, float))
            and float(ps[v]) > float(bs[v])
        )
        print(
            f"  [{i}/{len(arg_ids)}] {arg_id}: "
            f"pipe={pipe['overall']}/base={base_overall} | "
            f"upgraded-separating={up_separating}/{len(AGENTIC_UPGRADED_VIRTUES)} "
            f"({elapsed:.1f}s)"
        )

    return {
        "corpus": CORPUS_LABELS[corpus_label],
        "method": "fb29_agentic_headtohead",
        "model": model,
        "n_args": len(arg_ids),
        "per_argument": per_arg,
    }


def build_differential(results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Per-virtue differential: agentic pipeline vs 0-shot baseline, with the
    upgrade-delta (FB-28 lexical → FB-29 agentic) on the 2 upgraded virtues."""
    diff: Dict[str, Any] = {}
    for corpus_label, corpus_res in results.items():
        per_arg = corpus_res.get("per_argument")
        if per_arg is None:
            diff[corpus_label] = {
                "corpus": CORPUS_LABELS.get(corpus_label, corpus_label),
                "error": corpus_res.get("error", "no per_argument"),
            }
            continue

        virtue_pipe: Dict[str, List[float]] = {v: [] for v in VIRTUES}
        virtue_base: Dict[str, List[float]] = {v: [] for v in VIRTUES}
        virtue_fb28: Dict[str, List[float]] = {v: [] for v in VIRTUES}
        upgraded_exhibits: Dict[str, List[str]] = {v: [] for v in AGENTIC_UPGRADED_VIRTUES}

        for arg_id, entry in per_arg.items():
            ps = entry["agentic_pipeline"]["scores"]
            bs = entry["baseline_0shot"]["scores"]
            fbs = entry["fb28_lexical"]["scores"]
            for v in VIRTUES:
                if isinstance(ps.get(v), (int, float)):
                    virtue_pipe[v].append(float(ps[v]))
                if isinstance(bs.get(v), (int, float)):
                    virtue_base[v].append(float(bs[v]))
                if isinstance(fbs.get(v), (int, float)):
                    virtue_fb28[v].append(float(fbs[v]))
            ex = entry["agentic_pipeline"].get("exhibits", {})
            for v in AGENTIC_UPGRADED_VIRTUES:
                if ex.get(v):
                    upgraded_exhibits[v].append(str(ex[v]))

        per_virtue: Dict[str, Any] = {}
        for v in VIRTUES:
            p_mean = round(sum(virtue_pipe[v]) / len(virtue_pipe[v]), 3) if virtue_pipe[v] else None
            b_mean = round(sum(virtue_base[v]) / len(virtue_base[v]), 3) if virtue_base[v] else None
            f28_mean = round(sum(virtue_fb28[v]) / len(virtue_fb28[v]), 3) if virtue_fb28[v] else None
            delta = round(p_mean - b_mean, 3) if (p_mean is not None and b_mean is not None) else None
            upgrade_delta = (
                round(p_mean - f28_mean, 3)
                if v in AGENTIC_UPGRADED_VIRTUES and p_mean is not None and f28_mean is not None
                else None
            )
            per_virtue[v] = {
                "agentic_pipeline_mean": p_mean,
                "baseline_0shot_mean": b_mean,
                "fb28_lexical_mean": f28_mean,
                "delta_pipe_minus_baseline": delta,
                "upgrade_delta_agentic_minus_fb28": upgrade_delta,
            }

        diff[corpus_label] = {
            "corpus": CORPUS_LABELS[corpus_label],
            "n_args": len(per_arg),
            "per_virtue": per_virtue,
            "upgraded_virtue_exhibits_sample": {
                v: upgraded_exhibits[v][:3] for v in AGENTIC_UPGRADED_VIRTUES
            },
        }
    return diff


def main():
    parser = argparse.ArgumentParser(description="FB-29/FB-38 agentic head-to-head")
    parser.add_argument("--corpus", choices=["A", "B", "C"], default=None)
    parser.add_argument("--max-args", type=int, default=8)
    parser.add_argument(
        "--out-prefix",
        default="fb38",
        help="Output filename prefix (default fb38; FB-29 frozen results are fb29_*).",
    )
    args_cli = parser.parse_args()

    corpus_list = [args_cli.corpus] if args_cli.corpus else ["A", "B", "C"]
    out_prefix = args_cli.out_prefix
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    results: Dict[str, Any] = {}
    for label in corpus_list:
        print(f"\n{'='*60}\n[{out_prefix.upper()}] corpus {label}\n{'='*60}")
        try:
            res = run_corpus(label, max_args=args_cli.max_args)
            results[label] = res
            out_path = RESULTS_DIR / f"{out_prefix}_agentic_{label}.json"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(res, f, indent=2, ensure_ascii=False, default=str)
            print(f"[{out_prefix.upper()}] saved {out_path}")
        except Exception as exc:
            print(f"[{out_prefix.upper()}] corpus {label} FAILED: {exc}")
            results[label] = {"corpus": CORPUS_LABELS[label], "error": str(exc)}

    diff = build_differential(results)
    summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "method": f"{out_prefix}_agentic_headtohead",
        "description": (
            f"Upgraded pipeline (agentic multi-step on {len(AGENTIC_UPGRADED_VIRTUES)} "
            f"virtues: {', '.join(AGENTIC_UPGRADED_VIRTUES)}) vs 0-shot baseline, "
            "same rubric/scale as FB-28"
        ),
        "upgraded_virtues": AGENTIC_UPGRADED_VIRTUES,
        "differential": diff,
    }
    summary_path = RESULTS_DIR / f"{out_prefix}_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n[{out_prefix.upper()}] Summary + differential saved to {summary_path}")

    print(f"\n{'='*60}\n[{out_prefix.upper()}] UPGRADED-VIRTUE DIFFERENTIAL (agentic pipe vs 0-shot base)\n{'='*60}")
    for label in corpus_list:
        d = diff.get(label, {})
        pv = d.get("per_virtue", {})
        for v in AGENTIC_UPGRADED_VIRTUES:
            row = pv.get(v, {})
            print(
                f"  {CORPUS_LABELS[label]} {v}: "
                f"agentic={row.get('agentic_pipeline_mean')} "
                f"base={row.get('baseline_0shot_mean')} "
                f"fb28_lex={row.get('fb28_lexical_mean')} "
                f"Δ(pipe-base)={row.get('delta_pipe_minus_baseline')} "
                f"upgradeΔ={row.get('upgrade_delta_agentic_minus_fb28')}"
            )


if __name__ == "__main__":
    main()
