"""#1647 step 1 — raw / kept / dropped (+ cardinality) of the SetAF translator on real corpora.

The last measured state of #1647 (coord, 2026-08-10): the write-side loss is
FIXED (sidecar ``formalism_specific.set_attacks``), the R787 states carry 43
set-attacks — 43 singletons, ZERO collective — and the instrument could not
say whether the model proposes nothing (``raw=0``) or proposes and gets
dropped (``raw>0, kept=0``). #1706/#1707 made ``raw/kept/dropped`` observable;
this harness reads it on the REAL corpus, per draw, and adds the datum the
issue's step 1 asks for: the CARDINALITY distribution of the RAW proposals —
"0 of N collective" vs "k of N collective" are opposite conclusions (prompt
contract vs validation plumbing).

Design (modeled on ``measure_1737_axis_remesure.py``, production path only):
  - fact extraction ONCE per corpus, then N SetAF draws on that same
    inventory — the question isolates the TRANSLATOR's variance, not the
    extractor's; the inventory size is recorded either way.
  - per draw: real ``translate_to_setaf_attacks(text, arguments)`` with the
    ``_llm_extract_relations`` capture (same hook as #1737) for the RAW side;
    ``TranslationResult.relations`` is the KEPT side; ``raw - kept`` = dropped.
  - cardinality of a raw proposal = ``len(item["attackers"])``.

Privacy HARD: in-memory corpus, opaque IDs only (corpus_A/B/C), artifact under
the gitignored ``evaluation/results/real_analysis/``. Rationale strings are
NEVER persisted — they are LLM prose over real corpus text; only counts and
cardinalities leave the process.

Usage:
    conda run -n projet-is-roo-new --no-capture-output python scripts/measure_1647_setaf_raw_kept.py --draws 6
"""

import argparse
import asyncio
import json
import os
import sys
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
                val = val.strip().strip('"').strip("'")
                os.environ.setdefault(key.strip(), val)

from argumentation_analysis.core.utils.crypto_utils import derive_encryption_key  # noqa: E402
from argumentation_analysis.core.io_manager import load_extract_definitions  # noqa: E402
from argumentation_analysis.orchestration import structured_arg_translator as tr  # noqa: E402
from argumentation_analysis.orchestration.invoke_callables import (  # noqa: E402
    _invoke_fact_extraction,
)

DATASET_PATH = Path("argumentation_analysis/data/extract_sources.json.gz.enc")
CORPUS_SRC_IDX = {"A": 11, "B": 3, "C": 2}
RESULTS_DIR = Path("argumentation_analysis/evaluation/results/real_analysis")
MAX_CHARS = 40000

_raw_llm: Dict[str, Any] = {}
_orig_llm = tr._llm_extract_relations


async def _capture_llm(input_text, arguments, relation_kind):
    data = await _orig_llm(input_text, arguments, relation_kind)
    if relation_kind == "setaf_attacks":
        _raw_llm["setaf_attacks"] = data if isinstance(data, dict) else {}
    return data


tr._llm_extract_relations = _capture_llm


def load_corpus(label: str) -> str:
    key = derive_encryption_key(os.environ["TEXT_CONFIG_PASSPHRASE"])
    defs = load_extract_definitions(DATASET_PATH, key)
    entry = defs[CORPUS_SRC_IDX[label]]
    text = entry.get("full_text", "") or ""
    return text[:MAX_CHARS]


def inventory_texts(extraction: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    for a in extraction.get("arguments", []):
        if isinstance(a, dict) and a.get("text"):
            out.append(str(a["text"]))
        elif a:
            out.append(str(a))
    return out


def cardinalities(items: List[Any]) -> Dict[str, Any]:
    cards = []
    for it in items if isinstance(items, list) else []:
        if isinstance(it, dict):
            atk = it.get("attackers", [])
            if isinstance(atk, str):
                atk = [atk]
            if isinstance(atk, list):
                cards.append(len(atk))
    dist: Dict[int, int] = {}
    for c in cards:
        dist[c] = dist.get(c, 0) + 1
    return {
        "n": len(cards),
        "dist": {str(k): v for k, v in sorted(dist.items())},
        "max": max(cards) if cards else 0,
        "collective": sum(1 for c in cards if c >= 2),
    }


async def main_async(draws: int, labels: List[str]) -> Dict[str, Any]:
    report: Dict[str, Any] = {
        "issue": 1647,
        "step": "raw/kept/dropped + raw cardinality of setaf translator",
        "generated": datetime.now(timezone.utc).isoformat(),
        "draws_per_corpus": draws,
        "corpora": {},
    }
    for label in labels:
        text = load_corpus(label)
        extraction = await _invoke_fact_extraction(text, {"_state_object": None})
        arguments = inventory_texts(extraction)
        rec: Dict[str, Any] = {
            "n_chars": len(text),
            "extraction_status": extraction.get("extraction_status"),
            "n_arguments": len(arguments),
            "draws": [],
        }
        for _ in range(draws):
            _raw_llm.clear()
            outcome = await tr.translate_to_setaf_attacks(text, arguments)
            raw_items = (_raw_llm.get("setaf_attacks") or {}).get("attacks", [])
            raw = cardinalities(raw_items)
            kept = cardinalities(outcome.relations)
            rec["draws"].append(
                {
                    "raw_n": raw["n"],
                    "raw_dist": raw["dist"],
                    "raw_max_card": raw["max"],
                    "raw_collective": raw["collective"],
                    "kept_n": kept["n"],
                    "kept_collective": kept["collective"],
                    "dropped": raw["n"] - kept["n"],
                    "cause": outcome.cause,
                }
            )
            print(
                f"[corpus_{label}] raw={raw['n']} (dist {raw['dist']}, "
                f"collective {raw['collective']}) kept={kept['n']} "
                f"(collective {kept['collective']}) dropped={raw['n'] - kept['n']} "
                f"cause={outcome.cause}"
            )
        runs = rec["draws"]
        rec["summary"] = {
            "raw_zero_rate": sum(1 for d in runs if d["raw_n"] == 0) / len(runs),
            "raw_total": sum(d["raw_n"] for d in runs),
            "raw_collective_total": sum(d["raw_collective"] for d in runs),
            "kept_total": sum(d["kept_n"] for d in runs),
            "kept_collective_total": sum(d["kept_collective"] for d in runs),
            "dropped_total": sum(d["dropped"] for d in runs),
        }
        report["corpora"][f"corpus_{label}"] = rec
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--draws", type=int, default=6)
    ap.add_argument("--corpora", default="A,B,C")
    args = ap.parse_args()

    labels = [x.strip() for x in args.corpora.split(",") if x.strip()]
    report = asyncio.run(main_async(args.draws, labels))

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / f"setaf_raw_kept_dropped_{datetime.now():%Y%m%d_%H%M%S}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print()
    print("=== summary (per corpus) ===")
    for name, rec in report["corpora"].items():
        s = rec["summary"]
        print(
            f"{name}: inventory={rec['n_arguments']} args | "
            f"raw total {s['raw_total']} (collective {s['raw_collective_total']}, "
            f"zero-rate {s['raw_zero_rate']:.2f}) | kept {s['kept_total']} "
            f"(collective {s['kept_collective_total']}) | dropped {s['dropped_total']}"
        )
    print(f"\nartifact: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
