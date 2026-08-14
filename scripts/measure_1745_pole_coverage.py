"""#1745 — does the single-pole inventory explain the attack famine, and does
ONE prompt instruction (extract cited/adversarial positions as discrete,
neutral items) lift it?

Issue #1745 protocol (pre-registered at
https://github.com/jsboigeEpita/2025-Epita-Intelligence-Symbolique/issues/1745#issuecomment-5295035932
BEFORE any run):

  * Arm CONTROL = the production ``_invoke_fact_extraction`` prompt VERBATIM
    (single variable design: nothing else moves — no schema, no window, no
    max_tokens).
  * Arm TREATED = the same body + ONE instruction (the "geste"): an
    argumentative text contains the positions it argues against; extract each
    as a STANDALONE item stated NEUTRALLY, never folded inside another item.
  * k >= 5 runs per arm (extraction is a draw). Report RATES, never a single
    value. "Effective coverage" = pair covered in >= 2/5 runs.
  * Pole coverage = for an annotated pair (A attacks B), the PRODUCTION
    inventory contains BOTH poles as DISTINCT items (each pole matching a
    different item at score >= 0.6, same exact/containment/Jaccard scale as
    the R808 harness). The membership input is ALWAYS the production output —
    never the annotations (anti-pendule).
  * Step 0 gate: if the CONTROL arm already covers >= 1 pair effectively
    (>= 2/5 runs), the hypothesis is REFUTED at extraction — report and stop.
  * Step 3 (reader): attack axes run over the PRODUCTION inventory of both
    arms; raw proposals captured before validation. If coverage rises but raw
    stays 0, the defect is at the NEXT hop — named, not counted as success.
  * Neutrality inspection: matched target-pole items are kept in the
    gitignored artifact; a heuristic flags disqualifying markers ("wrongly",
    "erroneous", ...) so a loaded item cannot silently pass as neutral.

Reuses the R808 harness (measure_1710_ground_truth) for extraction call
shape, raw capture, axis runs and similarity — identical measurement chain.

Privacy HARD: corpus content in-memory only; outputs under
evaluation/results/real_analysis/ (GITIGNORED); opaque IDs everywhere.

Usage:
    conda run -n projet-is-roo-new --no-capture-output python scripts/measure_1745_pole_coverage.py --passage C --arm control
    conda run -n projet-is-roo-new --no-capture-output python scripts/measure_1745_pole_coverage.py --passage C --arm treated
    conda run -n projet-is-roo-new --no-capture-output python scripts/measure_1745_pole_coverage.py --passage A --arm all
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))
os.chdir(Path(__file__).parent.parent)

import measure_1710_ground_truth as gt  # noqa: E402  (R808 harness, merged)

RESULTS_DIR = Path("argumentation_analysis/evaluation/results/real_analysis")
K_DEFAULT = 5
EFFECTIVE_MIN_RUNS = 2  # pre-registered: pair "effectively covered" iff >= 2/K runs

# ---------------------------------------------------------------------------
# The geste — ONE instruction appended to the production body. Two exigences
# from the issue: DISCRETE (standalone item, never folded) and NEUTRAL (as its
# holder would state it, not as the author disqualifies it).
# ---------------------------------------------------------------------------
_GESTE = (
    " An argumentative text also CONTAINS the positions it argues against - "
    "quoted, paraphrased, or reformulated. Extract each of those cited or "
    "opposing positions as a standalone item of the same rank as the "
    "positions the text defends: one item per position, stated NEUTRALLY "
    "(the assertion as its holder would state it, not as the author "
    "disqualifies it). Do NOT fold an opposing position inside the "
    "description of another item."
)

ARMS: Dict[str, str] = {
    "control": gt._BASELINE_BODY,
    "treated": gt._BASELINE_BODY + _GESTE,
}

# Heuristic disqualifying markers — a "target-pole" item carrying one of these
# is possibly loaded (stated as the author disqualifies it, not neutrally).
_LOADED_MARKERS = (
    "wrongly",
    "erroneous",
    "so-called",
    "false claim",
    "alleged",
    "myth",
    "supposedly",
    "falsely",
)


def pole_coverage(arg_texts: List[str], pair: Dict[str, Any]) -> Dict[str, Any]:
    """Both poles of the pair present as DISTINCT inventory items?

    A pole is "present" iff its best-matching item scores >= _SIM_THRESHOLD
    (same scale as R808). The pair is covered iff both poles are present AND
    their best items are different items.
    """
    atk_claim = pair["attacker"]["claim"]
    tgt_claim = pair["target"]["claim"]

    def best(claim: str) -> Tuple[Optional[int], float, Optional[str]]:
        best_i, best_s = None, 0.0
        for i, t in enumerate(arg_texts):
            s = gt._sim(claim, t)
            if s > best_s:
                best_i, best_s = i, s
        if best_i is None:
            return None, 0.0, None
        return best_i, best_s, arg_texts[best_i]

    a_i, a_s, a_t = best(atk_claim)
    t_i, t_s, t_t = best(tgt_claim)
    covered = (
        a_s >= gt._SIM_THRESHOLD
        and t_s >= gt._SIM_THRESHOLD
        and a_i is not None
        and t_i is not None
        and a_i != t_i
    )
    return {
        "pair_id": pair["id"],
        "covered": covered,
        "attacker": {
            "score": round(a_s, 3),
            "item_idx": a_i,
            "item_text": a_t,  # artifact-only (gitignored)
        },
        "target": {
            "score": round(t_s, 3),
            "item_idx": t_i,
            "item_text": t_t,
            "possibly_loaded": bool(
                t_t and any(m in t_t.lower() for m in _LOADED_MARKERS)
            ),
        },
    }


async def run_arm(
    arm_name: str,
    body: str,
    text: str,
    lang_clause: str,
    ann: Dict[str, Any],
    k: int,
    model_id: str,
) -> Dict[str, Any]:
    arm: Dict[str, Any] = {"body_len": len(body), "runs": []}
    for i in range(1, k + 1):
        t0 = time.time()
        args, summary = await gt.extract_inventory(text, body, lang_clause)
        arg_texts = [a["text"] for a in args if isinstance(a, dict) and a.get("text")]
        coverage = [pole_coverage(arg_texts, p) for p in ann["pairs"]]
        axes = await gt.run_path(text, arg_texts, model_id, arm_name, i)
        n_cov = sum(1 for c in coverage if c["covered"])
        print(
            f"   [{arm_name}] run {i}/{k}: {len(arg_texts)} items, "
            f"pairs covered this run: {n_cov}/{len(coverage)} "
            f"({round(time.time() - t0)}s)"
        )
        arm["runs"].append(
            {
                "run": i,
                "n_args": len(arg_texts),
                "elapsed_s": round(time.time() - t0, 1),
                "status": summary[:80],
                "arg_texts_full": arg_texts,
                "coverage": coverage,
                "axes": axes,
            }
        )
    # Aggregate: coverage rate per pair + effective coverage (>= EFFECTIVE_MIN_RUNS).
    agg_cov = []
    for p in ann["pairs"]:
        hits = sum(
            1
            for r in arm["runs"]
            for c in r["coverage"]
            if c["pair_id"] == p["id"] and c["covered"]
        )
        loaded = any(
            c["target"]["possibly_loaded"]
            for r in arm["runs"]
            for c in r["coverage"]
            if c["pair_id"] == p["id"] and c["covered"]
        )
        agg_cov.append(
            {
                "pair_id": p["id"],
                "covered_runs": hits,
                "rate": round(hits / k, 2),
                "effectively_covered": hits >= EFFECTIVE_MIN_RUNS,
                "any_matched_target_possibly_loaded": loaded,
            }
        )
    arm["coverage_aggregate"] = agg_cov
    arm["effective_pairs"] = sum(1 for c in agg_cov if c["effectively_covered"])
    # Raw attack counts per axis per run.
    arm["raw_attacks"] = {
        axis: [r["axes"][axis]["raw"] for r in arm["runs"]]
        for axis in ("setaf", "weighted", "aspic")
    }
    return arm


def render(result: Dict[str, Any]) -> str:
    p = result["passage"]
    lines = [
        f"\n=== #1745 pole-coverage — {p['corpus']} offset {p['offset']} ===",
        f"model={result['model']}  k={result['k']}  "
        f"effective = pair covered in >= {EFFECTIVE_MIN_RUNS}/{result['k']} runs",
        "",
    ]
    for arm_name, arm in result["arms"].items():
        lines.append(f"--- arm: {arm_name} ---")
        lines.append(
            f"{'pair':<8} {'covered':<10} {'rate':<6} {'target possibly loaded'}"
        )
        for c in arm["coverage_aggregate"]:
            eff = "YES" if c["effectively_covered"] else "no"
            loaded = "FLAG" if c["any_matched_target_possibly_loaded"] else "clean"
            lines.append(
                f"{c['pair_id']:<8} {eff:<10} {c['covered_runs']}/{result['k']}"
                f"     {loaded}"
            )
        lines.append(
            f"effective pairs: {arm['effective_pairs']}  |  raw attacks "
            f"(per run): {arm['raw_attacks']}"
        )
        lines.append("")
    gate = result.get("gate")
    if gate:
        lines.append(f"GATE (step 0): {gate}")
    return "\n".join(lines)


# passage_1 = the R808 annotated passage (corpus C); passage_2 = the #1745
# portée passage (corpus A, annotated to the same barème BEFORE any run on it).
PASSAGES: Dict[str, Dict[str, Any]] = {
    "C": {
        "corpus": "C",
        "offset": 10400,
        "width": 3000,
        "annot": "annotations_1710_gt_C.json",
    },
    "A": {
        "corpus": "A",
        "offset": 14000,
        "width": 3000,
        "annot": "annotations_1745_gt_A.json",
    },
}


async def main_async(arms: List[str], k: int, passage_key: str) -> None:
    passage = PASSAGES[passage_key]
    text = gt.load_corpus_text(passage["corpus"], passage["offset"], passage["width"])
    annot_path = RESULTS_DIR / passage["annot"]
    with open(annot_path, encoding="utf-8") as f:
        ann = json.load(f)
    lang_clause = gt._lang_clause(text)
    _client, model_id = gt._get_openai_client()
    if not model_id:
        model_id = "(unresolved)"
    print(
        f"[1745] passage_{passage_key} corpus {passage['corpus']} offset "
        f"{passage['offset']}: {len(text)} chars, "
        f"{len(ann['pairs'])} frozen annotated pairs, model={model_id}, "
        f"k={k}, arms={arms}"
    )
    print(
        "[1745] pre-registered verdict: "
        "https://github.com/jsboigeEpita/2025-Epita-Intelligence-Symbolique/"
        "issues/1745#issuecomment-5295035932"
    )

    result: Dict[str, Any] = {
        "issue": 1745,
        "passage": dict(passage),
        "model": model_id,
        "k": k,
        "effective_min_runs": EFFECTIVE_MIN_RUNS,
        "geste": _GESTE,
        "annotation_artifact": str(annot_path),
        "arms": {},
    }

    for arm_name in arms:
        result["arms"][arm_name] = await run_arm(
            arm_name, ARMS[arm_name], text, lang_clause, ann, k, model_id
        )
        # Step 0 gate fires right after the control arm.
        if arm_name == "control" and "treated" not in arms:
            eff = result["arms"]["control"]["effective_pairs"]
            result["gate"] = f"control arm effective pairs = {eff} -> " + (
                "HYPOTHESIS REFUTED AT EXTRACTION (>=1 pair already "
                "covered): report and STOP, dispatch retargets."
                if eff >= 1
                else "gate passes (0 effective pairs) -> proceed to " "treated arm."
            )

    # Pair-level raw-proposal overlap on the production inventories (both arms).
    for arm_name, arm in result["arms"].items():
        overlap_rows = []
        for pair in ann["pairs"]:
            hit_any, best, correct = False, 0.0, False
            for r in arm["runs"]:
                for axis_key in ("setaf", "weighted", "aspic"):
                    entry = r["axes"].get(axis_key, {})
                    hit, score, cd = gt._pair_overlap(entry.get("proposed", []), pair)
                    hit_any = hit_any or hit
                    best = max(best, score)
                    correct = correct or cd
            overlap_rows.append(
                {
                    "pair_id": pair["id"],
                    "proposed_in_any_run": hit_any,
                    "best_score": round(best, 3),
                    "correct_direction": correct,
                }
            )
        arm["overlap"] = overlap_rows

    result["date_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out_path = RESULTS_DIR / f"measure_1745_pole_coverage_{passage_key}.json"
    existing = {}
    if out_path.exists():
        try:
            with open(out_path, encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = {}
    # Merge by arm so control/treated can be run in separate invocations.
    # (Explicit key merge — a blanket dict.update would REPLACE the arms
    # dict wholesale and wipe arms from earlier invocations.)
    for key in (
        "issue",
        "passage",
        "model",
        "k",
        "effective_min_runs",
        "geste",
        "annotation_artifact",
    ):
        existing[key] = result[key]
    existing.setdefault("arms", {}).update(result["arms"])
    existing["date_utc"] = result["date_utc"]
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False, default=str)
    print(render(result))
    print(f"\n[1745] artifact (gitignored) -> {out_path}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--arm", choices=["control", "treated", "all"], default="all")
    p.add_argument("--k", type=int, default=K_DEFAULT, help="runs per arm")
    p.add_argument(
        "--passage",
        choices=list(PASSAGES),
        default="C",
        help="C = passage_1 (R808 annotations); A = passage_2 (portée)",
    )
    a = p.parse_args()
    arms = ["control", "treated"] if a.arm == "all" else [a.arm]
    asyncio.run(main_async(arms, a.k, a.passage))


if __name__ == "__main__":
    main()
