"""#1737 instrument — deterministic head-nature counter per reading-window site.

First deliverable of the #1737 lane (coord R813/R814/R815): NOT a
window->quality curve. The inter-draw variance measured by the coord at
CONSTANT window (edges 0->11 on one corpus, inventory 8->17) is the same
order of magnitude as the effect the window comparison would claim to
isolate, so no window comparison is readable until the variance is published.
Before even that, this script pins WHAT each site actually reads.

The 12+ sites that read the head of the source text (`text[:2000..4000]`)
have never had the NATURE of that head measured: on corpus_B the first 3000
chars are a table of contents (R807: 49 year-tokens, ~2 real sentences), so
a site reading `text[:3000]` on corpus_B analyses a TOC, not prose. The
hypothesized defect is "the head is not prose", NOT "the window is too
short" (anti-pendule: widening would move the problem, not measure it).

What this instrument is:

- DETERMINISTIC: pure structural classification, zero LLM calls. Same input
  -> same verdict, twice (demonstrated: the script hashes its own output and
  the double-probe mode runs the classification twice and asserts identity).
- RE-PLAYABLE: the site list is explicit below with file:line anchors; each
  row records the structural features alongside the verdict so a threshold
  can be audited without re-deriving it.
- CALIBRATION IS HONEST: the thresholds are calibrated on two known points
  (corpus_B@0 = TOC, measured R807; corpus_C@10400 = production prose, the
  #1710 ground-truth window). Two-point calibration — the features are the
  evidence, the verdict is the summary.

Verdicts: ``prose`` / ``metadata`` (TOC, index, date list) /
``boilerplate`` (repeated-header dominance) / ``mixed`` (none dominates).

Privacy HARD: corpus content is loaded in-memory and never written out. The
artifact records FEATURES (counts, ratios) and opaque IDs only
(corpus_A/B/C, site names). Output lands under gitignored
``evaluation/results/real_analysis/``.

Usage:
    conda run -n projet-is-roo-new --no-capture-output python scripts/measure_1737_head_nature.py
    conda run -n projet-is-roo-new --no-capture-output python scripts/measure_1737_head_nature.py --probe2
"""

import argparse
import hashlib
import json
import os
import re
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
                os.environ.setdefault(key.strip(), val.strip())

from argumentation_analysis.core.utils.crypto_utils import derive_encryption_key
from argumentation_analysis.core.io_manager import load_extract_definitions

DATASET_PATH = Path("argumentation_analysis/data/extract_sources.json.gz.enc")
CORPUS_SRC_IDX = {"A": 11, "B": 3, "C": 2}
RESULTS_DIR = Path("argumentation_analysis/evaluation/results/real_analysis")

# Reading-window sites (file:line anchors, verified 2026-08-16 on main
# fa8b64bd). Window = the slice the site feeds onward.
SITES = [
    {"site": "debate_analysis", "anchor": "invoke_callables.py:1611", "window": 1500},
    {
        "site": "collaborative_debate",
        "anchor": "collaborative_debate.py:148",
        "window": 1500,
    },
    {"site": "governance", "anchor": "invoke_callables.py:2079", "window": 2000},
    {
        "site": "strategic_objectives",
        "anchor": "hierarchical/strategic/manager.py:350",
        "window": 2000,
    },
    {"site": "fact_extraction", "anchor": "invoke_callables.py:6090", "window": 3000},
    {
        "site": "language_detection",
        "anchor": "conversational_orchestrator.py:98",
        "window": 3000,
    },
    {
        "site": "structured_translators",
        "anchor": "structured_arg_translator.py:309",
        "window": 3000,
    },
    {
        "site": "propositional_logic",
        "anchor": "invoke_callables.py:6342,6457",
        "window": 4000,
    },
    {"site": "fol_reasoning", "anchor": "invoke_callables.py:6781", "window": 4000},
]

_DATE_RE = re.compile(r"\b(19|20)\d{2}\b")
_SENT_SPLIT_RE = re.compile(r"[.!?]+")
_LIST_MARKER_RE = re.compile(r"^\s*(?:[-*•·]|\d{1,2}[.)])\s+")


def head_features(head: str) -> Dict[str, Any]:
    """Structural fingerprint of a reading window (deterministic, no LLM)."""
    n = len(head)
    if n == 0:
        return {
            "chars": 0,
            "alpha_ratio": 0.0,
            "avg_sentence_len": 0.0,
            "sentences_per_kchar": 0.0,
            "year_tokens_per_kchar": 0.0,
            "list_marker_lines_pct": 0.0,
            "short_line_pct": 0.0,
            "top5gram_repetition_pct": 0.0,
        }
    sentences = [s for s in _SENT_SPLIT_RE.split(head) if len(s.strip()) > 10]
    lines = head.splitlines()
    nonempty = [ln for ln in lines if ln.strip()]
    alpha = sum(c.isalpha() for c in head)
    year_tokens = len(_DATE_RE.findall(head))
    list_marked = sum(1 for ln in nonempty if _LIST_MARKER_RE.match(ln))
    short_lines = sum(1 for ln in nonempty if len(ln.strip()) <= 60)
    # Repeated 5-gram dominance (boilerplate detector): share of the window
    # covered by the single most-repeated 5-word shingle.
    words = head.lower().split()
    shingles: Dict[str, int] = {}
    for i in range(len(words) - 4):
        key = " ".join(words[i : i + 5])
        shingles[key] = shingles.get(key, 0) + 1
    top5 = max(shingles.values(), default=0)
    # words covered by repeats of the top shingle (first occurrence is content)
    top5_cov = max(0, top5 - 1) * 5 if top5 > 1 else 0
    return {
        "chars": n,
        "alpha_ratio": round(alpha / n, 3),
        "avg_sentence_len": (
            round(sum(len(s) for s in sentences) / len(sentences), 1)
            if sentences
            else 0.0
        ),
        "sentences_per_kchar": round(len(sentences) / (n / 1000), 2),
        "year_tokens_per_kchar": round(year_tokens / (n / 1000), 2),
        "list_marker_lines_pct": (
            round(100 * list_marked / len(nonempty), 1) if nonempty else 0.0
        ),
        "short_line_pct": (
            round(100 * short_lines / len(nonempty), 1) if nonempty else 0.0
        ),
        "top5gram_repetition_pct": round(100 * top5_cov / max(1, len(words)), 2),
    }


def classify_head(f: Dict[str, Any]) -> str:
    """Verdict from features. Two-point calibration (see module docstring).

    ``metadata``: date-dense (TOC/index — corpus_B@0 measures 16.3
    year-tokens/kchar, 49 dates in 3000 chars) OR list-marker line dominance.
    ``boilerplate``: one 5-gram shingle covers >=15% of the window
    (repeated header/footer).
    ``prose``: long sentences (>=40 chars avg), alphabetic (>=0.70),
    sentence-sparse enough to be paragraphs (<25/kchar).
    """
    if f["chars"] == 0:
        return "empty"
    if f["year_tokens_per_kchar"] >= 8 or f["list_marker_lines_pct"] >= 50:
        return "metadata"
    if f["top5gram_repetition_pct"] >= 15:
        return "boilerplate"
    if (
        f["avg_sentence_len"] >= 40
        and f["alpha_ratio"] >= 0.70
        and f["sentences_per_kchar"] < 25
    ):
        return "prose"
    return "mixed"


def load_corpus_text(label: str, max_chars: int = 6000) -> str:
    key = derive_encryption_key(os.environ["TEXT_CONFIG_PASSPHRASE"])
    defs = load_extract_definitions(DATASET_PATH, key)
    entry = defs[CORPUS_SRC_IDX[label]]
    return entry.get("full_text", "") or entry[:max_chars]


def classify_all() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    texts = {label: load_corpus_text(label) for label in CORPUS_SRC_IDX}
    for label, text in texts.items():
        for site in SITES:
            head = text[: site["window"]]
            feats = head_features(head)
            rows.append(
                {
                    "corpus": f"corpus_{label}",
                    "site": site["site"],
                    "anchor": site["anchor"],
                    "window": site["window"],
                    "verdict": classify_head(feats),
                    **feats,
                }
            )
    # Calibration rows: the two known points, so the artifact carries its own
    # validation (TOC head must classify metadata; production prose must
    # classify prose — a threshold drift shows here first).
    for label, offset, expected in (("B", 0, "metadata"), ("C", 10400, "prose")):
        head = texts[label][offset : offset + 3000]
        feats = head_features(head)
        got = classify_head(feats)
        rows.append(
            {
                "corpus": f"corpus_{label}",
                "site": f"CALIBRATION@{offset}",
                "anchor": "known-window",
                "window": 3000,
                "verdict": got,
                "expected": expected,
                "calibration_ok": got == expected,
                **feats,
            }
        )
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--probe2",
        action="store_true",
        help="run the classification twice and assert identical output "
        "(the coord's probe-twice requirement, demonstrated not claimed)",
    )
    a = ap.parse_args()

    rows = classify_all()
    run_hash = hashlib.sha256(
        json.dumps(rows, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()[:16]

    if a.probe2:
        rows2 = classify_all()
        hash2 = hashlib.sha256(
            json.dumps(rows2, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()[:16]
        identical = rows == rows2
        print(f"probe1 hash: {run_hash}")
        print(f"probe2 hash: {hash2}")
        print(f"probe identical: {identical}")
        if not identical:
            print("NON-DETERMINISM DETECTED — do not compare anything (R814)")
            sys.exit(1)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    artifact = RESULTS_DIR / f"measure_1737_head_nature_{ts}.json"
    with open(artifact, "w", encoding="utf-8") as f:
        json.dump(
            {
                "generated": ts,
                "deterministic": True,
                "rows_sha256_16": run_hash,
                "probe2": bool(a.probe2),
                "rows": rows,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    # Console summary: opaque IDs + features only.
    print(f"\n=== #1737 head-nature instrument (hash {run_hash}) ===")
    verdict_by_corpus: Dict[str, Dict[str, str]] = {}
    for r in rows:
        if r["site"].startswith("CALIBRATION"):
            print(
                f"{r['corpus']} {r['site']}: verdict={r['verdict']} "
                f"expected={r['expected']} ok={r['calibration_ok']}"
            )
            continue
        verdict_by_corpus.setdefault(r["corpus"], {})[r["site"]] = r["verdict"]
    for corpus, per_site in verdict_by_corpus.items():
        counts: Dict[str, int] = {}
        for v in per_site.values():
            counts[v] = counts.get(v, 0) + 1
        print(f"{corpus}: {counts}")
        # A corpus head is ONE thing; sites differ only by window length.
        for site, v in sorted(per_site.items()):
            row = next(r for r in rows if r["corpus"] == corpus and r["site"] == site)
            print(
                f"    {site}[:{row['window']}]: {v} "
                f"(avg_sent={row['avg_sentence_len']} "
                f"yr/kchar={row['year_tokens_per_kchar']} "
                f"alpha={row['alpha_ratio']} "
                f"list%={row['list_marker_lines_pct']})"
            )
    print(f"artifact: {artifact}")


if __name__ == "__main__":
    main()
