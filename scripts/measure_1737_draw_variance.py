"""#1737 second deliverable — inter-draw variance at CONSTANT reading window.

Coord R813 measured, at a constant 6000-char window, derived edges varying
0->11 on one corpus and the extraction inventory 8->17 on another — the same
order of magnitude as the effect a window comparison would claim to isolate.
R814's directive: publish the variance as a MEASURED FACT (n draws, rates,
dispersion) before comparing any windows; no seed, no silent averaging. What
gets decided afterwards is the n a window comparison needs to be readable.

Windows measured (head-nature controlled by the #1737 instrument, PR #1770):
corpus_A@0, corpus_B@30000, corpus_C@10400 — all three classify ``prose`` at
every site window, so the draw variance measured here is NOT confounded by
the corpus_B TOC head (that corpus's production head is metadata at every
current window — a separate deterministic finding).

Per draw (pure production path, no prompt variant):
  1. real ``_invoke_fact_extraction`` on text[:3000] -> inventory size
  2. real ``translate_to_dung_attacks`` -> raw proposals / validated edges

Metrics published per corpus: per-draw values, min/max, mean, population
std, zero-rate (draws rendering nothing). Raw proposals AND validated edges
are both recorded — proposal variance and validation variance are different
facts (a stable raw with unstable kept would point at the validator, not the
LLM).

Privacy HARD: in-memory corpus, artifact under gitignored
``evaluation/results/real_analysis/``, opaque IDs only.

Usage:
    conda run -n projet-is-roo-new --no-capture-output python scripts/measure_1737_draw_variance.py
    conda run -n projet-is-roo-new --no-capture-output python scripts/measure_1737_draw_variance.py --n 8
"""

import argparse
import asyncio
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

from argumentation_analysis.core.utils.crypto_utils import derive_encryption_key
from argumentation_analysis.core.io_manager import load_extract_definitions
from argumentation_analysis.orchestration import structured_arg_translator as tr
from argumentation_analysis.orchestration.invoke_callables import (
    _invoke_fact_extraction,
)
from argumentation_analysis.orchestration.structured_arg_translator import (
    translate_to_dung_attacks,
)

DATASET_PATH = Path("argumentation_analysis/data/extract_sources.json.gz.enc")
CORPUS_SRC_IDX = {"A": 11, "B": 3, "C": 2}
RESULTS_DIR = Path("argumentation_analysis/evaluation/results/real_analysis")

# Prose-headed windows (instrument-verified prose, PR #1770). Constant across
# all draws — the ONLY thing varying between draws is the LLM draw itself.
WINDOWS = {"A": 0, "B": 30000, "C": 10400}
EXTRACTION_WINDOW = 3000  # production fact_extraction window (invoke :6090)

_raw_llm: Dict[str, Dict[str, Any]] = {}
_orig_llm = tr._llm_extract_relations


async def _capture_llm(
    input_text: str, arguments: List[str], relation_kind: str
) -> Dict[str, Any]:
    data = await _orig_llm(input_text, arguments, relation_kind)
    _raw_llm[relation_kind] = data if isinstance(data, dict) else {}
    return data


tr._llm_extract_relations = _capture_llm


def load_corpus_text(label: str, offset: int, max_chars: int) -> str:
    key = derive_encryption_key(os.environ["TEXT_CONFIG_PASSPHRASE"])
    defs = load_extract_definitions(DATASET_PATH, key)
    entry = defs[CORPUS_SRC_IDX[label]]
    text = entry.get("full_text", "") or ""
    return text[offset : offset + max_chars]


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
        rec.update({"raw_proposals": 0, "validated_edges": 0, "cause": "no_inventory"})
        return rec
    outcome = await translate_to_dung_attacks(text[:EXTRACTION_WINDOW], arguments)
    proposals = _raw_llm.get("dung_attacks", {}).get("attacks", [])
    rec.update(
        {
            "raw_proposals": len(proposals) if isinstance(proposals, list) else 0,
            "validated_edges": len(outcome.relations),
            "cause": outcome.cause,
        }
    )
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


async def main_async(n: int) -> None:
    runs: List[Dict[str, Any]] = []
    for label, offset in WINDOWS.items():
        text = load_corpus_text(label, offset, EXTRACTION_WINDOW)
        draws = []
        for d in range(1, n + 1):
            t0 = time.time()
            rec = await one_draw(text)
            rec["wall_s"] = round(time.time() - t0, 1)
            draws.append(rec)
            print(
                f"[1737-var] corpus_{label}@{offset} draw{d}: "
                f"args={rec['n_arguments']} raw={rec.get('raw_proposals')} "
                f"edges={rec.get('validated_edges')} cause={rec.get('cause')} "
                f"({rec['wall_s']}s)"
            )
        runs.append(
            {
                "corpus": f"corpus_{label}",
                "offset": offset,
                "window": EXTRACTION_WINDOW,
                "draws": draws,
                "summary": {
                    "n_arguments": summarize([d["n_arguments"] for d in draws]),
                    "raw_proposals": summarize(
                        [d.get("raw_proposals", 0) for d in draws]
                    ),
                    "validated_edges": summarize(
                        [d.get("validated_edges", 0) for d in draws]
                    ),
                },
            }
        )

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    artifact = RESULTS_DIR / f"measure_1737_draw_variance_{ts}.json"
    with open(artifact, "w", encoding="utf-8") as f:
        json.dump(
            {
                "generated": ts,
                "n_draws": n,
                "constant_window": EXTRACTION_WINDOW,
                "runs": runs,
            },
            f,
            indent=2,
        )

    print("\n=== #1737 variance at constant window (the fact, not corrected) ===")
    for run in runs:
        s = run["summary"]
        print(f"{run['corpus']}@{run['offset']} (window {run['window']}):")
        for metric in ("n_arguments", "raw_proposals", "validated_edges"):
            m = s[metric]
            print(
                f"    {metric}: {m['values']} | mean={m['mean']} std={m['std']} "
                f"zero_rate={m['zero_rate']}"
            )
    print(f"artifact: {artifact}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8, help="draws per corpus (default 8)")
    a = ap.parse_args()
    asyncio.run(main_async(a.n))
