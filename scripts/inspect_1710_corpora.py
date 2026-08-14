"""#1710 corpus structural fingerprint — is the famine CONTENT or TRUNCATION?

Production extraction + translation both see only ``text[:3000]``
(invoke_callables.py:5974 and structured_arg_translator.py:292). If a corpus's
first 3000 chars is a table of contents / compilation metadata (no attacks),
the famine is a SOURCE-CONTENT property, not a form property — and no
extraction-prompt change can fix it.

This script fingerprints each corpus's FULL text WITHOUT leaking content:
structural metrics only (length, newline/line density, date tokens, chapter
markers, short-line ratio, rough sentence count). A TOC = many short lines +
date/chapter markers + few sentences; a speech = long lines + many sentences.

Privacy HARD: no verbatim text is printed. Outputs a structural fingerprint.
Gitignored JSON optional. Opaque IDs only.

Usage:
    conda run -n projet-is-roo-new --no-capture-output python scripts/inspect_1710_corpora.py
"""

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.chdir(Path(__file__).parent.parent)

_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    with open(_env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

from argumentation_analysis.core.utils.crypto_utils import derive_encryption_key
from argumentation_analysis.core.io_manager import load_extract_definitions

DATASET_PATH = Path("argumentation_analysis/data/extract_sources.json.gz.enc")
CORPUS_SRC_IDX = {"A": 11, "B": 3, "C": 2}

_DATE_RE = re.compile(r"\b(1[89]\d{2}|20\d{2})\b")
_CHAPTER_RE = re.compile(
    r"\b(chapter|kapitel|chapitre|part|teil|section|abschnitt)\b", re.IGNORECASE
)
_SENT_SPLIT = re.compile(r"[\.!?]\s")


def fingerprint(text: str) -> dict:
    full = text
    head = text[:3000]
    lines = [ln for ln in full.splitlines() if ln.strip()]
    short_lines = [ln for ln in lines if len(ln) < 40]
    sents_head = [s for s in _SENT_SPLIT.split(head) if len(s.split()) > 4]
    sents_full = [s for s in _SENT_SPLIT.split(full) if len(s.split()) > 4]
    avg_line = (sum(len(ln) for ln in lines) / len(lines)) if lines else 0.0
    return {
        "raw_len": len(full),
        "n_lines": len(lines),
        "avg_line_len": round(avg_line, 1),
        "short_line_ratio": round(len(short_lines) / max(len(lines), 1), 3),
        "n_date_tokens_full": len(_DATE_RE.findall(full)),
        "n_date_tokens_head3000": len(_DATE_RE.findall(head)),
        "n_chapter_markers_full": len(_CHAPTER_RE.findall(full)),
        "n_chapter_markers_head3000": len(_CHAPTER_RE.findall(head)),
        "n_sentences_head3000": len(sents_head),
        "n_sentences_full": len(sents_full),
        "head3000_char_fraction": round(3000 / max(len(full), 1), 3),
    }


def classify(fp: dict) -> str:
    """Coarse TOC-vs-speech guess from the first 3000 chars only."""
    score = 0
    if fp["short_line_ratio"] > 0.4:
        score += 1
    if fp["n_date_tokens_head3000"] >= 5:
        score += 1
    if fp["n_chapter_markers_head3000"] >= 2:
        score += 1
    if fp["n_sentences_head3000"] < 12:
        score += 1
    if fp["avg_line_len"] < 60:
        score += 1
    label = "TOC/meta" if score >= 3 else "prose/speech"
    return f"{label} (score {score}/5)"


def window_fingerprint(text: str, start: int, width: int = 3000) -> dict:
    win = text[start : start + width]
    lines = [ln for ln in win.splitlines() if ln.strip()]
    sents = [s for s in _SENT_SPLIT.split(win) if len(s.split()) > 4]
    return {
        "offset": start,
        "n_chars": len(win),
        "n_lines": len(lines),
        "n_sentences": len(sents),
        "n_date_tokens": len(_DATE_RE.findall(win)),
        "n_chapter_markers": len(_CHAPTER_RE.findall(win)),
    }


def main() -> None:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument(
        "--corpus",
        choices=list(CORPUS_SRC_IDX),
        default=None,
        help="if set with --offsets, fingerprint windows of this corpus only",
    )
    p.add_argument(
        "--offsets",
        default="",
        help="comma-separated char offsets, e.g. 0,3000,30000,300000",
    )
    a = p.parse_args()

    key = derive_encryption_key(os.environ["TEXT_CONFIG_PASSPHRASE"])
    defs = load_extract_definitions(DATASET_PATH, key)

    if a.corpus and a.offsets:
        text = defs[CORPUS_SRC_IDX[a.corpus]].get("full_text", "") or ""
        print(
            f"[inspect] corpus {a.corpus}: {len(text)} chars — window fingerprints (width 3000)"
        )
        print(
            f"{'offset':<9} {'chars':<7} {'lines':<7} {'sentences':<10} {'dates':<7} {'chapter_kw':<11} verdict"
        )
        print("-" * 75)
        for off in [int(x) for x in a.offsets.split(",") if x.strip()]:
            w = window_fingerprint(text, off)
            toc = (
                "TOC/index-like"
                if (w["n_date_tokens"] >= 5 and w["n_sentences"] < 12)
                else "prose"
            )
            print(
                f"{off:<9} {w['n_chars']:<7} {w['n_lines']:<7} {w['n_sentences']:<10} "
                f"{w['n_date_tokens']:<7} {w['n_chapter_markers']:<11} {toc}"
            )
        return

    print(f"[inspect] dataset: {len(defs)} definitions\n")
    print(
        f"{'corpus':<7} {'raw_len':<8} {'head_frac':<10} {'short_line%':<12} {'dates(h)':<9} {'chap(h)':<8} {'sents(h)':<9} {'avg_line':<9} verdict"
    )
    print("-" * 105)
    out = {}
    for label, idx in CORPUS_SRC_IDX.items():
        entry = defs[idx]
        text = entry.get("full_text", "") or ""
        fp = fingerprint(text)
        out[label] = {"src_idx": idx, **fp, "verdict_head3000": classify(fp)}
        print(
            f"{label:<7} {fp['raw_len']:<8} {fp['head3000_char_fraction']:<10} "
            f"{fp['short_line_ratio']:<12} {fp['n_date_tokens_head3000']:<9} "
            f"{fp['n_chapter_markers_head3000']:<8} {fp['n_sentences_head3000']:<9} "
            f"{fp['avg_line_len']:<9} {out[label]['verdict_head3000']}"
        )
    print("\n[h = measured on first 3000 chars only — what production extraction sees]")
    res_path = Path(
        "argumentation_analysis/evaluation/results/real_analysis/inspect_1710_corpora.json"
    )
    res_path.parent.mkdir(parents=True, exist_ok=True)
    with open(res_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"[inspect] fingerprint artifact (gitignored) -> {res_path}")


if __name__ == "__main__":
    main()
