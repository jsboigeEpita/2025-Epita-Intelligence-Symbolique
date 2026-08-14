"""#1710 ground-truth control — attack axes vs hand-annotated real-prose pairs.

R807 bis dispatch (msg-20260814T110731-l306ar): the missing cell is a
ground-truth measurement on REAL prose. Every prior control was either
synthetic-with-known-ground-truth (planted attack => raw=1) or real-but-
unannotated (raw=0, ambiguous). A zero against an unannotated input does not
distinguish "correctly found zero" from "missed what is there".

This script:

  1. Loads the hand-annotated pairs (gitignored artifact
     evaluation/results/real_analysis/annotations_1710_gt_C.json) — real prose,
     passage = corpus C, offset 10400, 3000 chars.
  2. Runs the attack axes (SetAF, Weighted, ASPIC contradictions/undercuts) on
     EXACTLY that passage, n>=2 draws, same model/determinism/schema as the
     R807 baseline (measure_1710_form_control.py).
  3. Two inventory paths:
       P1 production: baseline extraction inventory (what the pipeline feeds)
       P2 probe:      the annotated propositions THEMSELVES as the inventory
     Per draw/axis: raw/kept/cause + the proposed relations captured BEFORE
     validation (ids re-mapped to inventory texts), so the overlap with the
     annotated pairs is computable independently of the validator.
  4. Overlap: does each annotated (attacker, target) pair appear among the
     proposals? (exact-normalized then token-Jaccard fallback)
  5. Membership (P1): which annotated claims the extraction surfaces.

Anti-pendules honored (dispatch): NO validator relaxation, NO attack example
in any prompt, NO fabricated target — the annotated propositions are only ever
used as inventory items (what the model is allowed to cite), never injected
into a prompt as an example. The verdict is pre-registered in the annotation
artifact BEFORE this run and adjudicated after, on #1710.

Privacy HARD: corpus content loads in-memory; all outputs land under
evaluation/results/real_analysis/ (GITIGNORED). Opaque IDs on GitHub surfaces.

Usage:
    conda run -n projet-is-roo-new --no-capture-output python scripts/measure_1710_ground_truth.py
    conda run -n projet-is-roo-new --no-capture-output python scripts/measure_1710_ground_truth.py --n 3
"""

import argparse
import asyncio
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))
os.chdir(Path(__file__).parent.parent)

# Load .env (mirrors run_real_analysis.py — root .env wins).
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
from argumentation_analysis.orchestration import structured_arg_translator as tr
from argumentation_analysis.orchestration.structured_arg_translator import (
    translate_to_aspic_rules,
    translate_to_bipolar_supports,
    translate_to_setaf_attacks,
    translate_to_weighted_attacks,
)
from argumentation_analysis.orchestration.invoke_callables import (
    _EXTRACTION_MAX_ATTEMPTS,
    _EXTRACTION_MAX_TOKENS,
    _guarded_chat_completion,
    _get_determinism_params,
    _get_openai_client,
    _normalize_items_with_quotes,
    _parse_json_from_llm,
)

DATASET_PATH = Path("argumentation_analysis/data/extract_sources.json.gz.enc")
CORPUS_SRC_IDX = {"A": 11, "B": 3, "C": 2}
RESULTS_DIR = Path("argumentation_analysis/evaluation/results/real_analysis")
ANNOT_PATH = RESULTS_DIR / "annotations_1710_gt_C.json"
PASSAGE = {"corpus": "C", "offset": 10400, "width": 3000}

# ---------------------------------------------------------------------------
# Capture the raw LLM relations BEFORE validation (ids re-mapped later).
# The translators call the module-global _llm_extract_relations; wrapping it
# records the raw dict per relation_kind without touching production code.
# ---------------------------------------------------------------------------
_raw_llm: Dict[str, Dict[str, Any]] = {}
_orig_llm = tr._llm_extract_relations


async def _capture_llm(
    input_text: str, arguments: List[str], relation_kind: str
) -> Dict[str, Any]:
    data = await _orig_llm(input_text, arguments, relation_kind)
    _raw_llm[relation_kind] = data if isinstance(data, dict) else {}
    return data


tr._llm_extract_relations = _capture_llm

# Same diagnostics capture as the R807 script: the #1649 warning counts the
# raw/kept contradictions and undercuts channels.
_DIAG_RE = re.compile(
    r"proposed\s+(\d+)\s+contradiction\(s\)\s+\(kept\s+(\d+).*?"
    r"and\s+(\d+)\s+undercut\(s\)\s+\(kept\s+(\d+)",
    re.IGNORECASE | re.DOTALL,
)


class _DiagHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        msg = record.getMessage()
        if "#1649 diagnostics" in msg:
            m = _DIAG_RE.search(msg)
            if m:
                _aspic_diag["contradictions_raw"] = int(m.group(1))
                _aspic_diag["contradictions_kept"] = int(m.group(2))
                _aspic_diag["undercuts_raw"] = int(m.group(3))
                _aspic_diag["undercuts_kept"] = int(m.group(4))


_aspic_diag: Dict[str, int] = {}
_unified_logger = logging.getLogger("UnifiedPipeline")
_unified_logger.addHandler(_DiagHandler())
_unified_logger.setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# Baseline extraction prompt — VERBATIM production copy (same as the R807
# baseline body in measure_1710_form_control.py).
# ---------------------------------------------------------------------------
def _lang_clause(text: str) -> str:
    try:
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _detect_language,
        )

        _lang = _detect_language(text)
        _lang_names = {"de": "German", "fr": "French", "en": "English"}
        if _lang in _lang_names and _lang != "en":
            return (
                f" The source text is in {_lang_names[_lang]}. Analyze it in "
                f"its original language and extract ALL distinct arguments and "
                f"claims with the SAME thoroughness as you would for English — "
                f"do not under-extract because the text is non-English. Keep "
                f"the 'text' descriptions in {_lang_names[_lang]}."
            )
    except Exception:
        pass
    return ""


_JSON_SHAPE = (
    " Respond with ONLY a JSON object:\n"
    '{"arguments": [{"text": "...", "source_quote": "exact quote..."}], '
    '"claims": [{"text": "...", "source_quote": "exact quote..."}], '
    '"summary": "brief analysis summary"}'
)

_BASELINE_BODY = (
    "You are an expert argument analyst. Extract the key arguments "
    "and verifiable claims from the text. "
    "For each argument and claim, include the exact quote from the "
    "source text that supports it (verbatim, max 150 chars). "
    "Do NOT detect fallacies — that is handled by a separate specialist. "
    "Focus on: (1) identifying distinct argumentative positions, "
    "(2) extracting factual claims that can be verified, "
    "(3) noting rhetorical strategies used (without labeling them as fallacies)."
)


# ---------------------------------------------------------------------------
# Passage + annotation loading.
# ---------------------------------------------------------------------------
def load_corpus_text(label: str, offset: int, max_chars: int = 3000) -> str:
    key = derive_encryption_key(os.environ["TEXT_CONFIG_PASSPHRASE"])
    defs = load_extract_definitions(DATASET_PATH, key)
    entry = defs[CORPUS_SRC_IDX[label]]
    text = entry.get("full_text", "") or ""
    return text[offset : offset + max_chars]


def load_annotations() -> Dict[str, Any]:
    with open(ANNOT_PATH, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Extraction mirror (identical to measure_1710_form_control.py / production).
# ---------------------------------------------------------------------------
async def extract_inventory(
    text: str, body: str, lang_clause: str
) -> Tuple[List[Dict[str, Any]], str]:
    system_content = body + lang_clause + _JSON_SHAPE
    client, model_id = _get_openai_client()
    if client is None:
        return [], "no-openai-client"
    det_params = _get_determinism_params()
    use_json_mode = True
    use_max_tokens = _EXTRACTION_MAX_TOKENS > 0
    last_reason = "no-parse"
    for attempt in range(1, _EXTRACTION_MAX_ATTEMPTS + 1):
        kw: Dict[str, Any] = dict(det_params)
        if use_json_mode:
            kw["response_format"] = {"type": "json_object"}
        if use_max_tokens:
            kw["max_tokens"] = _EXTRACTION_MAX_TOKENS
        try:
            resp = await _guarded_chat_completion(
                client,
                model=model_id,
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": text[:3000]},
                ],
                **kw,
            )
            data = _parse_json_from_llm(resp.choices[0].message.content or "")
            if data:
                args = _normalize_items_with_quotes(data.get("arguments", []))
                return args, data.get("summary", "")
            last_reason = f"no-json(attempt={attempt})"
        except Exception as e:
            low = str(e).lower()
            dropped = False
            if use_json_mode and ("response_format" in low or "json_object" in low):
                use_json_mode = False
                dropped = True
            if use_max_tokens and (
                "max_tokens" in low or "max_completion_tokens" in low
            ):
                use_max_tokens = False
                dropped = True
            if dropped:
                continue
            last_reason = f"call-error({type(e).__name__}:{attempt})"
    return [], f"extraction-failed({last_reason})"


def _state(raw: int, kept: int) -> str:
    if raw == 0:
        return "famine_proposal"
    if kept == 0:
        return "famine_match"
    return "renders"


# ---------------------------------------------------------------------------
# Proposed-relation extraction from the RAW llm dict (ids -> inventory texts).
# ---------------------------------------------------------------------------
def _map_proposals(relation_kind: str, arguments: List[str]) -> List[Dict[str, Any]]:
    """Id-mapped proposed relations, independent of validation.

    Returns handler-shaped dicts: setaf -> {attackers, target},
    weighted -> {source, target, weight}, aspic -> {attacker, target}
    (contradictions) and {attacker, target_rule} (undercuts).
    """
    data = _raw_llm.get(relation_kind, {})
    arg_by_id, _ = tr._build_inventory(arguments)
    out: List[Dict[str, Any]] = []
    if relation_kind == "setaf_attacks":
        for item in data.get("attacks", []):
            if not isinstance(item, dict):
                continue
            atk_ids = item.get("attackers", [])
            if isinstance(atk_ids, str):
                atk_ids = [atk_ids]
            tgt = str(item.get("target", ""))
            if tgt in arg_by_id:
                atk_texts = [arg_by_id[a] for a in atk_ids if a in arg_by_id]
                if atk_texts:
                    out.append({"attackers": atk_texts, "target": arg_by_id[tgt]})
    elif relation_kind == "weighted_attacks":
        for item in data.get("attacks", []):
            if not isinstance(item, dict):
                continue
            src, tgt = str(item.get("source", "")), str(item.get("target", ""))
            if src in arg_by_id and tgt in arg_by_id:
                try:
                    w = float(item.get("weight", 0.5))
                except (TypeError, ValueError):
                    w = None
                out.append(
                    {"source": arg_by_id[src], "target": arg_by_id[tgt], "weight": w}
                )
    elif relation_kind == "aspic_rules":
        for item in data.get("contradictions", []):
            if not isinstance(item, dict):
                continue
            atk, tgt = str(item.get("attacker", "")), str(item.get("target", ""))
            if atk in arg_by_id and tgt in arg_by_id:
                out.append({"attacker": arg_by_id[atk], "target": arg_by_id[tgt]})
        for item in data.get("undercuts", []):
            if not isinstance(item, dict):
                continue
            atk = str(item.get("attacker", ""))
            if atk in arg_by_id:
                out.append(
                    {"attacker": arg_by_id[atk], "target_rule": item.get("target_rule")}
                )
    return out


# ---------------------------------------------------------------------------
# Text similarity for the annotated-vs-proposed overlap.
# ---------------------------------------------------------------------------
def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower().strip())


def _jaccard(a: str, b: str) -> float:
    wa, wb = set(_norm(a).split()), set(_norm(b).split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def _sim(a: str, b: str) -> float:
    na, nb = _norm(a), _norm(b)
    if na == nb:
        return 1.0
    if na and (na in nb or nb in na):
        return 0.95
    return _jaccard(a, b)


_SIM_THRESHOLD = 0.6


def _pair_overlap(
    proposed: List[Dict[str, Any]], ann: Dict[str, Any]
) -> Tuple[bool, float, bool]:
    """Does any proposed relation cover the annotated pair (either direction)?

    Returns (proposed, best_score, correct_direction).
    """
    atk_claim = ann["attacker"]["claim"]
    tgt_claim = ann["target"]["claim"]
    best: float = 0.0
    correct = False
    for rel in proposed:
        # extract the two node texts of the relation
        if "attackers" in rel and "target" in rel:  # setaf
            a_text = rel["attackers"][0] if rel["attackers"] else ""
            b_text = rel["target"]
        elif "source" in rel and "target" in rel:  # weighted
            a_text, b_text = rel["source"], rel["target"]
        elif "attacker" in rel and "target" in rel:  # aspic contradiction
            a_text, b_text = rel["attacker"], rel["target"]
        else:
            continue
        # forward
        s_fwd = (_sim(a_text, atk_claim) + _sim(b_text, tgt_claim)) / 2
        # reverse
        s_rev = (_sim(a_text, tgt_claim) + _sim(b_text, atk_claim)) / 2
        best = max(best, s_fwd, s_rev)
        if s_fwd >= _SIM_THRESHOLD:
            correct = True
    return best >= _SIM_THRESHOLD, best, correct


# ---------------------------------------------------------------------------
# Main measurement.
# ---------------------------------------------------------------------------
ATTACK_AXES = [
    ("setaf", "SetAF", translate_to_setaf_attacks, "setaf_attacks"),
    ("weighted", "Weighted", translate_to_weighted_attacks, "weighted_attacks"),
    ("aspic", "ASPIC+", translate_to_aspic_rules, "aspic_rules"),
]
CONTROL_AXES = [("bipolar", "Bipolar", translate_to_bipolar_supports, "supports")]


async def run_path(
    text: str,
    inventory: List[str],
    model_id: str,
    path_name: str,
    draw: int,
) -> Dict[str, Any]:
    axes: Dict[str, Any] = {}
    for key, label, fn, kind in ATTACK_AXES + CONTROL_AXES:
        _raw_llm.clear()
        _aspic_diag.clear()
        t0 = time.time()
        try:
            res = await fn(text, inventory)
            kept = len(res.relations) if isinstance(res.relations, (list, dict)) else 0
        except Exception as e:
            axes[key] = {
                "cause": f"exception:{type(e).__name__}",
                "raw": None,
                "kept": None,
                "state": "exception",
            }
            continue
        raw = sum(tr._raw_count(_raw_llm.get(kind, {}), k) for k in _REL_KEYS[key])
        proposed = _map_proposals(kind, inventory)
        entry = {
            "cause": res.cause,
            "raw": raw,
            "kept": kept,
            "state": _state(raw, kept),
            "elapsed_s": round(time.time() - t0, 1),
            "n_proposed_raw": len(proposed),
            "proposed": proposed,
        }
        if key == "aspic":
            entry["contradictions_raw"] = _aspic_diag.get("contradictions_raw", 0)
            entry["contradictions_kept"] = _aspic_diag.get("contradictions_kept", 0)
            entry["undercuts_raw"] = _aspic_diag.get("undercuts_raw", 0)
        axes[key] = entry
        print(
            f"   [{path_name}] draw {draw}: {label:<9} state={entry['state']:<15} "
            f"raw={entry['raw']} kept={entry['kept']} n_raw_rel={entry['n_proposed_raw']} "
            f"({round(entry['elapsed_s'])}s)"
        )
    return axes


_REL_KEYS = {
    "setaf": ("attacks",),
    "weighted": ("attacks",),
    "aspic": ("rules", "contradictions", "undercuts"),
    "bipolar": ("supports",),
}


async def main_async(n: int) -> None:
    text = load_corpus_text(PASSAGE["corpus"], PASSAGE["offset"], PASSAGE["width"])
    ann = load_annotations()
    claims: List[str] = []
    for p in ann["pairs"]:
        claims.append(p["attacker"]["claim"])
        claims.append(p["target"]["claim"])
    lang_clause = _lang_clause(text)
    client, model_id = _get_openai_client()
    if not model_id:
        model_id = "(unresolved)"
    print(
        f"[1710] GT passage corpus C offset {PASSAGE['offset']} width "
        f"{PASSAGE['width']}: {len(text)} chars, {len(ann['pairs'])} annotated pairs, "
        f"{len(claims)} probe claims, model={model_id}, n={n}"
    )
    print(
        f"[1710] pre-registered verdict (annotation artifact): V1 dead / V2 alive / V3 partial"
    )

    result: Dict[str, Any] = {
        "corpus": PASSAGE["corpus"],
        "offset": PASSAGE["offset"],
        "width": PASSAGE["width"],
        "model": model_id,
        "n": n,
        "annotation_artifact": str(ANNOT_PATH),
        "pairs": [{"id": p["id"], "relation": p["relation"]} for p in ann["pairs"]],
        "paths": {},
    }

    # Path P1 — production extraction inventory (per draw, like production).
    p1: Dict[str, Any] = {"extraction": [], "axes": []}
    for i in range(1, n + 1):
        t0 = time.time()
        args, summary = await extract_inventory(text, _BASELINE_BODY, lang_clause)
        arg_texts = [a["text"] for a in args if isinstance(a, dict) and a.get("text")]
        p1["extraction"].append(
            {
                "draw": i,
                "n_args": len(arg_texts),
                "elapsed_s": round(time.time() - t0, 1),
                "status": summary[:80],
                "args_sample": [a[:60] for a in arg_texts[:4]],
                "arg_texts_full": arg_texts,
            }
        )
        axes = await run_path(text, arg_texts, model_id, "P1", i)
        p1["axes"].append({"draw": i, "axes": axes})

    # Path P2 — annotated propositions as the inventory (fixed).
    p2: Dict[str, Any] = {"axes": []}
    for i in range(1, n + 1):
        axes = await run_path(text, claims, model_id, "P2", i)
        p2["axes"].append({"draw": i, "axes": axes})

    result["paths"]["P1_production"] = p1
    result["paths"]["P2_probe"] = p2

    # --- Overlap + membership -------------------------------------------------
    for path_name, path in (("P1_production", p1), ("P2_probe", p2)):
        overlap_rows = []
        for pair in ann["pairs"]:
            proposed_any = False
            best: float = 0.0
            correct_dir = False
            n_proposals = 0
            for d in path["axes"]:
                for axis_key in ("setaf", "weighted", "aspic"):
                    entry = d["axes"].get(axis_key, {})
                    n_proposals += entry.get("n_proposed_raw", 0)
                    hit, score, cd = _pair_overlap(entry.get("proposed", []), pair)
                    if hit:
                        proposed_any = True
                    best = max(best, score)
                    correct_dir = correct_dir or cd
            overlap_rows.append(
                {
                    "pair_id": pair["id"],
                    "proposed_in_any_draw": proposed_any,
                    "best_score": round(best, 3),
                    "correct_direction": correct_dir,
                    "total_raw_proposals": n_proposals,
                }
            )
        path["overlap"] = overlap_rows

    # Membership: which annotated claims does the extraction inventory surface?
    # (best Jaccard vs any E item across draws, threshold _SIM_THRESHOLD)
    flat_e: List[str] = []
    for d in p1["extraction"]:
        flat_e.extend(d.get("arg_texts_full", []))
    p1["membership"] = []
    for pair in ann["pairs"]:
        for role in ("attacker", "target"):
            claim = pair[role]["claim"]
            best = max((_sim(claim, e) for e in flat_e), default=0.0)
            p1["membership"].append(
                {
                    "pair_id": pair["id"],
                    "role": role,
                    "claim": claim,
                    "best_match_score": round(best, 3),
                    "in_inventory": best >= _SIM_THRESHOLD,
                }
            )

    # ---------- render ----------
    print("\n=== #1710 ground-truth — overlap annoté ↔ proposé ===")
    print(f"{'pair':<8} {'P1 production':<20} {'P2 probe':<20}")
    print("-" * 50)
    for row in p1["overlap"]:
        pid = row["pair_id"]
        p1hit = "PROPOSED" if row["proposed_in_any_draw"] else "absent"
        p1score = row["best_score"]
        p2row = next(r for r in p2["overlap"] if r["pair_id"] == pid)
        p2hit = "PROPOSED" if p2row["proposed_in_any_draw"] else "absent"
        p2score = p2row["best_score"]
        print(f"{pid:<8} {p1hit:<12}({p1score:.2f})  {p2hit:<12}({p2score:.2f})")

    result["date_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out_path = RESULTS_DIR / "measure_1710_ground_truth_C.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n[1710] artifact (gitignored) -> {out_path}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--n", type=int, default=2, help="draws per path (LLM is stochastic)"
    )
    a = p.parse_args()
    asyncio.run(main_async(a.n))


if __name__ == "__main__":
    main()
