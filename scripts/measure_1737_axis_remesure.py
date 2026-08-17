"""#1737 step 4 — before/after re-measure of the #1710 attack axes on corpus_B.

#1710 measured a famine of ATTACK proposals (dung / weighted / setaf / aspic
contradictions) on corpus_B. Those measurements read the corpus_B TOC head
(offset 0) — every reading site sliced ``text[:3000]`` without checking what
the head is. Step 3 wired the reading sites to the computed selection
(``reading_window.selected_text``), so the SAME axes now read prose at the
selected offset (~15001).

This harness measures the axes BEFORE and AFTER with the SAME script and the
SAME inputs: run it on main (sites unwired, offset 0) for BEFORE, run it on
the wired branch for AFTER. The key design point: the full text is passed
everywhere — on main the unwired sites truncate to the head (the old
behaviour), on the wired branch the selector moves the window (the new
behaviour). No branch-dependent input, nothing pre-truncated.

Per draw (production path, no prompt variant, no seed):
  1. real ``_invoke_fact_extraction(text)`` -> inventory size
  2. for each attack axis (dung_attacks, weighted_attacks, setaf_attacks,
     aspic_rules): real ``translate_to_*_attacks`` -> raw proposals / edges
  3. selection probe: the computed offset + status (deterministic)

probe2 (R814): the deterministic selection part runs twice and must hash
identically — never compare axes if the window itself is not reproducible.

Privacy HARD: in-memory corpus, opaque IDs, artifact under gitignored
``evaluation/results/real_analysis/``.

Usage:
    conda run -n projet-is-roo-new --no-capture-output python scripts/measure_1737_axis_remesure.py --n 8 --label before
    conda run -n projet-is-roo-new --no-capture-output python scripts/measure_1737_axis_remesure.py --n 8 --label after
"""

import argparse
import asyncio
import hashlib
import json
import math
import os
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

from argumentation_analysis.core.utils.crypto_utils import derive_encryption_key  # noqa: E402
from argumentation_analysis.core.io_manager import load_extract_definitions  # noqa: E402
from argumentation_analysis.orchestration import structured_arg_translator as tr  # noqa: E402
from argumentation_analysis.orchestration.invoke_callables import (  # noqa: E402
    _invoke_fact_extraction,
)
from argumentation_analysis.orchestration.structured_arg_translator import (  # noqa: E402
    translate_to_aspic_rules,
    translate_to_dung_attacks,
    translate_to_setaf_attacks,
    translate_to_weighted_attacks,
)
from argumentation_analysis.core.reading_window import select_reading_head  # noqa: E402

DATASET_PATH = Path("argumentation_analysis/data/extract_sources.json.gz.enc")
CORPUS_B_SRC_IDX = 3
RESULTS_DIR = Path("argumentation_analysis/evaluation/results/real_analysis")

# How much of corpus_B is loaded. 30000 chars is past the TOC (prose starts
# ~15000); +3000 window covers any selected offset with its full span.
MAX_CHARS = 40000
EXTRACTION_WINDOW = 3000

AXES = {
    "dung_attacks": translate_to_dung_attacks,
    "weighted_attacks": translate_to_weighted_attacks,
    "setaf_attacks": translate_to_setaf_attacks,
    "aspic_rules": translate_to_aspic_rules,
}

_raw_llm: Dict[str, Dict[str, Any]] = {}
_orig_llm = tr._llm_extract_relations


async def _capture_llm(
    input_text: str, arguments: List[str], relation_kind: str
) -> Dict[str, Any]:
    data = await _orig_llm(input_text, arguments, relation_kind)
    _raw_llm[relation_kind] = data if isinstance(data, dict) else {}
    return data


tr._llm_extract_relations = _capture_llm


def load_corpus_b(max_chars: int) -> str:
    key = derive_encryption_key(os.environ["TEXT_CONFIG_PASSPHRASE"])
    defs = load_extract_definitions(DATASET_PATH, key)
    entry = defs[CORPUS_B_SRC_IDX]
    text = entry.get("full_text", "") or ""
    return text[:max_chars]


def selection_probe(text: str, window: int) -> Dict[str, Any]:
    sel = select_reading_head(text, window)
    return {
        "offset": sel.offset,
        "status": sel.status,
        "window": window,
        "slice_hash": hashlib.sha256(
            text[sel.offset : sel.offset + window].encode("utf-8")
        ).hexdigest()[:16],
    }


def inventory_texts(extraction: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    for a in extraction.get("arguments", []):
        if isinstance(a, dict) and a.get("text"):
            out.append(str(a["text"]))
        elif a:
            out.append(str(a))
    return out


async def one_draw(text: str) -> Dict[str, Any]:
    _raw_llm.clear()
    extraction = await _invoke_fact_extraction(text, {"_state_object": None})
    arguments = inventory_texts(extraction)
    rec: Dict[str, Any] = {
        "n_arguments": len(arguments),
        "extraction_status": extraction.get("extraction_status"),
    }
    if not arguments:
        rec["axes"] = {
            axis: {"raw_proposals": 0, "validated_edges": 0, "cause": "no_inventory"}
            for axis in AXES
        }
        return rec
    rec["axes"] = {}
    for axis, translate in AXES.items():
        outcome = await translate(text, arguments)
        proposals = _raw_llm.get(axis, {}).get("attacks", [])
        if not proposals and axis == "aspic_rules":
            # ASPIC returns {"rules"/"contradictions"/"undercuts"}; the raw
            # proposal count is the union of the three lists.
            raw = _raw_llm.get(axis, {})
            proposals = (
                raw.get("rules", [])
                + raw.get("contradictions", [])
                + raw.get("undercuts", [])
            )
        rec["axes"][axis] = {
            "raw_proposals": len(proposals) if isinstance(proposals, list) else 0,
            "validated_edges": len(outcome.relations),
            "cause": outcome.cause,
        }
    return rec


def summarize(values: List[float]) -> Dict[str, Any]:
    n = len(values)
    mean = sum(values) / n if n else 0.0
    var = sum((v - mean) ** 2 for v in values) / n if n else 0.0
    return {
        "values": values,
        "min": min(values) if values else None,
        "max": max(values) if values else None,
        "mean": round(mean, 2),
        "std": round(math.sqrt(var), 2),
        "zero_rate": round(sum(1 for v in values if v == 0) / n, 3) if n else None,
        "n": n,
    }


async def main_async(n: int, label: str, probe2: bool) -> None:
    text = load_corpus_b(MAX_CHARS)
    probe1 = selection_probe(text, EXTRACTION_WINDOW)

    probe2_hash = None
    if probe2:
        probe2 = selection_probe(text, EXTRACTION_WINDOW)
        h1 = hashlib.sha256(json.dumps(probe1, sort_keys=True).encode()).hexdigest()[:16]
        h2 = hashlib.sha256(json.dumps(probe2, sort_keys=True).encode()).hexdigest()[:16]
        if h1 != h2:
            print("NON-DETERMINISM IN SELECTION — do not compare (R814)")
            sys.exit(1)
        probe2_hash = h2

    draws: List[Dict[str, Any]] = []
    for d in range(1, n + 1):
        t0 = time.time()
        rec = await one_draw(text)
        rec["wall_s"] = round(time.time() - t0, 1)
        draws.append(rec)
        ax = ", ".join(
            f"{a}={rec['axes'][a]['raw_proposals']}/{rec['axes'][a]['validated_edges']}"
            for a in AXES
        )
        print(
            f"[1737-{label}] corpus_B draw{d}: args={rec['n_arguments']} "
            f"{ax} ({rec['wall_s']}s)"
        )

    summaries = {
        axis: {
            "raw_proposals": summarize([d["axes"][axis]["raw_proposals"] for d in draws]),
            "validated_edges": summarize([d["axes"][axis]["validated_edges"] for d in draws]),
        }
        for axis in AXES
    }
    summaries["n_arguments"] = summarize([d["n_arguments"] for d in draws])

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    artifact = RESULTS_DIR / f"measure_1737_axis_remesure_{label}_{ts}.json"
    with open(artifact, "w", encoding="utf-8") as f:
        json.dump(
            {
                "generated": ts,
                "label": label,
                "corpus": "corpus_B",
                "max_chars": MAX_CHARS,
                "n_draws": n,
                "selection": probe1,
                "probe2_hash": probe2_hash,
                "draws": draws,
                "summaries": summaries,
            },
            f,
            indent=2,
        )

    print(f"\n=== #1737 step-4 {label} — corpus_B (offset 0 head, unwired) ===" if label == "before" else f"\n=== #1737 step-4 {label} — corpus_B (selected offset {probe1['offset']}) ===")
    print(f"selection: {probe1}")
    for axis in AXES:
        for metric in ("raw_proposals", "validated_edges"):
            m = summaries[axis][metric]
            print(
                f"    {axis}.{metric}: {m['values']} | mean={m['mean']} "
                f"std={m['std']} zero_rate={m['zero_rate']}"
            )
    print(f"artifact: {artifact}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8, help="draws per axis (default 8)")
    ap.add_argument("--label", required=True, choices=["before", "after"])
    ap.add_argument("--probe2", action="store_true")
    a = ap.parse_args()
    asyncio.run(main_async(a.n, a.label, a.probe2))
