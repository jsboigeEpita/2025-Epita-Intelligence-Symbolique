"""#1698 measurement — the sixth translator renders Dung attacks on real corpora.

DoD (issue #1698, R811 dispatch):

  1. ``BOTH_in > 0`` on 3 corpora — the id-validated ``translate_to_dung_attacks``
     keeps at least one attack whose BOTH endpoints are inventory members,
     per corpus (real prose windows, production pipeline path end to end).
  2. At least one Dung semantics EXCLUDES something at least once across the
     three corpora — the real criterion (a framework that decided), NOT an
     edge count. An extension set whose union omits at least one inventory
     argument is an exclusion.
  3. Honest causes: each run records the discriminated cause the wiring wrote
     (``evaluated`` / ``no_genuine_relations`` / ``translator_failed`` /
     ``translator_unconfigured``) — absence of rejection on one corpus is a
     legitimate result.

Dissociative control (R807 lesson): corpus_B offset 0 is a table of contents,
not prose (49 dates, ~2 sentences per window). The translator is expected to
find nothing there — a zero on the TOC window against non-zeros on the prose
windows shows the measurement reads CONTENT, not a mechanical artifact.

Method: single production path per run — real ``_invoke_fact_extraction`` for
the inventory, then the REAL ``_invoke_dung_extensions`` whose #1698 wiring
runs the translator internally (raw proposals captured by wrapping
``_llm_extract_relations``; BOTH_in also recomputed independently from the
raw ids vs the inventory). No prompt variant, no validator relaxation.

Privacy HARD: corpus content loads in-memory; the artifact lands under
evaluation/results/real_analysis/ (GITIGNORED). Console output carries opaque
IDs only (corpus_A/B/C, arg indices).

Usage:
    conda run -n projet-is-roo-new --no-capture-output python scripts/measure_1698_dung_translator.py
    conda run -n projet-is-roo-new --no-capture-output python scripts/measure_1698_dung_translator.py --n 3
"""

import argparse
import asyncio
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

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
from argumentation_analysis.orchestration import structured_arg_translator as tr
from argumentation_analysis.orchestration.invoke_callables import (
    _invoke_dung_extensions,
    _invoke_fact_extraction,
)

DATASET_PATH = Path("argumentation_analysis/data/extract_sources.json.gz.enc")
CORPUS_SRC_IDX = {"A": 11, "B": 3, "C": 2}
RESULTS_DIR = Path("argumentation_analysis/evaluation/results/real_analysis")

# Real-prose windows. B offset 30000 jumps past the table of contents (R807:
# the first 3000 chars of corpus_B are a TOC — 49 dates, ~2 sentences — and
# are NOT argumentative prose). C offset 10400 is the production window used
# by the #1710 ground truth. A offset 0 is prose from the start.
WINDOWS = {"A": 0, "B": 30000, "C": 10400}
CONTROL_WINDOW = {"corpus": "B", "offset": 0}  # TOC dissociative control

_DATE_RE = re.compile(r"\b(19|20)\d{2}\b")

# Raw proposals captured before validation (ids re-checked against the
# inventory here, independently of the production validator).
_raw_llm: Dict[str, Dict[str, Any]] = {}
_orig_llm = tr._llm_extract_relations


async def _capture_llm(
    input_text: str, arguments: List[str], relation_kind: str
) -> Dict[str, Any]:
    data = await _orig_llm(input_text, arguments, relation_kind)
    _raw_llm[relation_kind] = data if isinstance(data, dict) else {}
    return data


tr._llm_extract_relations = _capture_llm


def load_corpus_text(label: str, offset: int, max_chars: int = 3000) -> str:
    key = derive_encryption_key(os.environ["TEXT_CONFIG_PASSPHRASE"])
    defs = load_extract_definitions(DATASET_PATH, key)
    entry = defs[CORPUS_SRC_IDX[label]]
    text = entry.get("full_text", "") or ""
    return text[offset : offset + max_chars]


def fingerprint(text: str) -> Dict[str, int]:
    """Structural fingerprint — TOC detection BEFORE any famine diagnosis (R807)."""
    sentences = [s for s in re.split(r"[.!?]+", text) if len(s.strip()) > 10]
    return {
        "chars": len(text),
        "sentences_gt10": len(sentences),
        "year_tokens": len(_DATE_RE.findall(text)),
    }


def inventory_texts(extraction: Dict[str, Any]) -> List[str]:
    args = extraction.get("arguments", [])
    out = []
    for a in args:
        if isinstance(a, dict) and a.get("text"):
            out.append(str(a["text"]))
        elif a:
            out.append(str(a))
    return out


def both_in_from_raw(arguments: List[str]) -> Dict[str, int]:
    """Recompute BOTH_in from the RAW proposals, independent of the validator."""
    data = _raw_llm.get("dung_attacks", {})
    arg_by_id, _ = tr._build_inventory(arguments)
    proposals = data.get("attacks", []) if isinstance(data, dict) else []
    raw = src_in = tgt_in = both = 0
    for rel in proposals:
        if not isinstance(rel, dict):
            continue
        raw += 1
        s = str(rel.get("source", ""))
        t = str(rel.get("target", ""))
        s_ok = s in arg_by_id
        t_ok = t in arg_by_id
        src_in += int(s_ok)
        tgt_in += int(t_ok)
        both += int(s_ok and t_ok and s != t)
    return {"raw": raw, "src_in": src_in, "tgt_in": tgt_in, "both_in": both}


def exclusions(result: Dict[str, Any], arguments: List[str]) -> List[Dict[str, Any]]:
    """Semantics that EXCLUDE at least one inventory argument (the real criterion).

    Reads ``all_extensions`` — the per-semantics dict the Dung site builds
    ({sem: {"extensions": [[…]], "count": N, …}} or ``{"error": …}``).
    NB: ``result["extensions"]`` is NOT that dict — it is the PRIMARY
    semantics' ENRICHED payload ({extensions, count, sizes, all_members});
    iterating it (first version of this script) yields the garbage keys
    "extensions"/"sizes"/"all_members" as pseudo-semantics.

    A semantics excludes when the union of its extensions omits at least one
    argument (an attacked argument no extension accepts). Error-shaped entries
    are filtered out, not counted as zeros.
    """
    out: List[Dict[str, Any]] = []
    all_ext = result.get("all_extensions")
    if not isinstance(all_ext, dict):
        return out
    for sem, payload in all_ext.items():
        if not isinstance(payload, dict) or "error" in payload:
            continue  # semantics not computed
        ext_lists = payload.get("extensions")
        if not isinstance(ext_lists, list):
            continue
        accepted = set()
        for extension in ext_lists:
            if isinstance(extension, list):
                accepted.update(str(a) for a in extension)
        excluded = [a for a in arguments if a not in accepted]
        if excluded:
            out.append(
                {
                    "semantics": sem,
                    "n_extensions": len(ext_lists),
                    "n_excluded": len(excluded),
                    "excluded_idx": [
                        arguments.index(a) for a in excluded
                    ],  # opaque index only
                }
            )
    return out


async def one_run(label: str, offset: int, draw: int) -> Dict[str, Any]:
    text = load_corpus_text(label, offset)
    fp = fingerprint(text)
    _raw_llm.clear()

    extraction = await _invoke_fact_extraction(text, {"_state_object": None})
    arguments = inventory_texts(extraction)
    record: Dict[str, Any] = {
        "corpus": f"corpus_{label}",
        "offset": offset,
        "draw": draw,
        "fingerprint": fp,
        "extraction_status": extraction.get("extraction_status"),
        "n_arguments": len(arguments),
    }
    if not arguments:
        record.update(
            {
                "cause": "no_inventory",
                "raw": 0,
                "both_in": 0,
                "retained": 0,
                "exclusions": [],
            }
        )
        return record

    ctx: Dict[str, Any] = {
        "_state_object": None,
        "phase_extract_output": {"arguments": arguments},
    }
    result = await _invoke_dung_extensions(text, ctx)
    counts = both_in_from_raw(arguments)
    attacks = result.get("attacks", [])
    record.update(
        {
            "cause": ctx.get("_structured_arg_cause:dung_extensions"),
            "raw": counts["raw"],
            "src_in": counts["src_in"],
            "tgt_in": counts["tgt_in"],
            "both_in_independent": counts["both_in"],
            "retained": len(attacks) if isinstance(attacks, list) else 0,
            "attacks_submitted": result.get("attacks_submitted"),
            "attacks_retained": result.get("attacks_retained"),
            "degraded": result.get("degraded"),
            "semantics_computed": sorted(
                k
                for k, v in (result.get("all_extensions") or {}).items()
                if isinstance(v, dict) and "count" in v
            ),
            "exclusions": exclusions(result, arguments),
        }
    )
    return record


async def main_async(n: int) -> None:
    # DoD2 needs the real Tweety reasoner — without a live JVM every Dung run
    # degrades ("AFHandler instantiated before JVM is ready") and no semantics
    # is ever computed, making the exclusion criterion unobservable (measured:
    # first run of this script, all-degraded). Idempotent; degrades honestly
    # to degraded=True runs if the JDK is unavailable.
    try:
        from argumentation_analysis.core.jvm_setup import initialize_jvm

        jvm_ok = bool(initialize_jvm())
        if jvm_ok:
            # initialize_jvm() starts the JVM only; AFHandler additionally
            # requires the Tweety CLASSES to be loaded
            # (is_jvm_ready = started AND _classes_loaded — measured: JVM up
            # alone still degrades every run). Same call as
            # unified_pipeline's #529 warmup.
            from argumentation_analysis.agents.core.logic.tweety_initializer import (
                TweetyInitializer,
            )

            TweetyInitializer().ensure_jvm_and_components_are_ready()
    except Exception as e:
        jvm_ok = False
        print(f"[1698] JVM init failed ({type(e).__name__}) — Dung runs will degrade")
    print(f"[1698] JVM initialized: {jvm_ok}")

    runs: List[Dict[str, Any]] = []
    for label, offset in WINDOWS.items():
        for draw in range(1, n + 1):
            t0 = time.time()
            rec = await one_run(label, offset, draw)
            rec["wall_s"] = round(time.time() - t0, 1)
            runs.append(rec)
            print(
                f"[1698] {rec['corpus']}@{rec['offset']} draw{draw}: "
                f"args={rec['n_arguments']} raw={rec.get('raw')} "
                f"both_in={rec.get('both_in_independent', 0)} "
                f"retained={rec.get('retained', 0)} cause={rec.get('cause')} "
                f"excl={[(e['semantics'], e['n_excluded']) for e in rec.get('exclusions', [])]} "
                f"({rec['wall_s']}s)"
            )
    # Dissociative control: corpus_B offset 0 = TOC (expect no attacks).
    ctrl = await one_run(CONTROL_WINDOW["corpus"], CONTROL_WINDOW["offset"], 1)
    ctrl["control"] = "toc_window"
    runs.append(ctrl)
    print(
        f"[1698] CONTROL {ctrl['corpus']}@{ctrl['offset']} (TOC): "
        f"fp={ctrl['fingerprint']} args={ctrl['n_arguments']} "
        f"raw={ctrl.get('raw')} both_in={ctrl.get('both_in_independent', 0)} "
        f"cause={ctrl.get('cause')}"
    )

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    artifact = RESULTS_DIR / f"measure_1698_dung_translator_{ts}.json"
    with open(artifact, "w", encoding="utf-8") as f:
        json.dump({"generated": ts, "n_draws": n, "runs": runs}, f, indent=2)

    # Aggregate verdict (opaque IDs only).
    prose = [r for r in runs if r.get("control") is None]
    per_corpus_both = {
        c: max(
            (r.get("both_in_independent", 0) for r in prose if r["corpus"] == c),
            default=0,
        )
        for c in (f"corpus_{k}" for k in WINDOWS)
    }
    any_exclusion = [
        (r["corpus"], e["semantics"], e["n_excluded"])
        for r in prose
        for e in r.get("exclusions", [])
    ]
    print("\n=== #1698 aggregate ===")
    print(f"BOTH_in>0 per corpus (max over draws): {per_corpus_both}")
    print(
        f"DoD1 (BOTH_in>0 on 3 corpora): {all(v > 0 for v in per_corpus_both.values())}"
    )
    print(
        f"DoD2 (>=1 semantics excludes >=1 arg, >=1 corpus): {bool(any_exclusion)} -> {any_exclusion[:8]}"
    )
    print(f"artifact: {artifact}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=2, help="draws per corpus (default 2)")
    a = ap.parse_args()
    asyncio.run(main_async(a.n))
