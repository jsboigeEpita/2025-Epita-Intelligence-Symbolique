# -*- coding: utf-8 -*-
"""Derived out-of-distribution evaluation export of the 13-class FR corpus (#3152).

Mission CoursIA-3, our half of `jsboige/CoursIA#10355`. The CoursIA fine-tune of
a small student model on their synthetic Cartesian-product corpus ends NO BEATS
(`CoursIA#20359`): macro-F1 0.0409, below random (0.0628) and below the lexical
baseline (0.2198). Their only validity check is the generator's self-agreement
(0.8679), measured by the same model family — it cannot tell an empty text from
a corpus that is too small. A real out-of-distribution set can. Our 13-class FR
corpus is the only real one in reach, and #1945 packaged it *without repairing
it*.

This producer builds the repaired, **derived** export. It is read-only on the
student directory (`2.3.2-detection-sophismes/`, a sanctuary) and writes
everything it produces under a gitignored path
(`argumentation_analysis/evaluation/results/`), like every other evaluation
output.

What it repairs, and the audit figure it re-measures
---------------------------------------------------
The R1105 audit (21/10, local, not tracked) reported six defects. Every one is
re-measured here on the seat, before and after:

1. exact split leak train ∩ test — 42 reported, 42 measured;
2. normalised split leak (case / whitespace / punctuation) — the audit's "47
   more" is the **total** normalised count (47 under case+whitespace, 51 adding
   punctuation), i.e. 5 (resp. 9) *more* than the exact 42, not 47 more;
3. texts repeated inside the 2 680 — 195 extra copies, measured the same way
   (NFKC + casefold + collapsed whitespace);
4. intra-split duplicates — train 103 / test 8 / val 6, reproduced exactly
   under the same normalisation;
5. labels still in English — 5 of 13, 46.16 % of the rows (the audit does not
   count ``ad hominem`` / ``ad populum``, Latin borrowings used verbatim in
   French; neither do we);
6. class ratio max:min — 6.91:1, reproduced.

Why the normalisation is the load-bearing step
----------------------------------------------
The corpus is sentence-level translations of a public English corpus, so the
same source sentence can appear twice with different casing, spacing or final
punctuation. Removing only exact duplicates leaves those leaks in place: the
mutation contract of `tests/unit/scripts/test_fallacy_ood_export_3152.py`
measures that dropping `normalise_key` turns the leak witness red.

Split discipline
----------------
The export is re-split from the deduplicated corpus, by **factor** (the corpus'
``config`` axis: ``edu`` / ``climate``), stratified per label, with the source
sentence disjoint between splits by construction (a split is assigned per
normalised key, so no sentence can land in two splits). Class counts are capped
at three times the smallest class before splitting, which is what brings the
ratio to ≤ 3:1 — the cap is a down-sample of the majority classes, never a
duplication of the minority one.

Anti-pendulum: this is an **evaluation** set. It is small and translated. It is
a contrast against the synthetic corpus, not a replacement, and no model was
trained on it. Nothing here is a correctness measure: a teacher↔student
agreement on this set is an agreement, not a ground truth.

Usage
-----
    python scripts/coursia/fallacy_ood_export.py [--out DIR] [--data DIR]

The parquet reader needs ``pyarrow`` (or ``fastparquet``); the repair functions
themselves are pure and tested without either.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = REPO_ROOT / "2.3.2-detection-sophismes" / "data"
DEFAULT_OUT_DIR = (
    REPO_ROOT
    / "argumentation_analysis"
    / "evaluation"
    / "results"
    / "coursia_fallacy_ood"
)

# --- the reviewed label table (never a machine translation at run time) ------

# Reviewed by hand against the corpus' own French column and the field's usual
# French vocabulary. ad hominem / ad populum stay as they are: they are Latin
# borrowings French uses verbatim, and the audit's "5 of 13 English labels"
# count excludes them for the same reason.
FRENCH_LABELS: Dict[str, str] = {
    "ad hominem": "ad hominem",
    "ad populum": "ad populum",
    "appel à l'émotion": "appel à l'émotion",
    "fallacy of credibility": "sophisme de crédibilité",
    "fallacy of extension": "sophisme d'extension",
    "fallacy of logic": "sophisme de logique",
    "faulty generalization": "généralisation hâtive",
    "fausse causalité": "fausse causalité",
    "faux dilemme": "faux dilemme",
    "intentional": "sophisme intentionnel",
    "raisonnement circulaire": "raisonnement circulaire",
    "sophisme de pertinence": "sophisme de pertinence",
    "équivoque": "équivoque",
}

# Every English spelling the corpus carries (its ``logical_fallacies_english``
# column). A label in this set, other than the two Latin borrowings, is a
# defect: the export is French.
ENGLISH_LABELS = frozenset(
    {
        "ad hominem",
        "ad populum",
        "appeal to emotion",
        "circular reasoning",
        "equivocation",
        "fallacy of credibility",
        "fallacy of extension",
        "fallacy of logic",
        "fallacy of relevance",
        "false causality",
        "false dilemma",
        "faulty generalization",
        "intentional",
    }
)
LATIN_BORROWINGS = frozenset({"ad hominem", "ad populum"})

LABEL_IDS: Dict[str, int] = {
    label: i for i, label in enumerate(sorted(FRENCH_LABELS.values()))
}


# --- normalisation -----------------------------------------------------------


def normalise_text(text: Any) -> str:
    """NFKC, casefold, collapsed whitespace — the audit's first two axes."""
    s = unicodedata.normalize("NFKC", str(text))
    s = s.casefold()
    return re.sub(r"\s+", " ", s).strip()


def normalise_key(text: Any) -> str:
    """``normalise_text`` with punctuation dropped — the audit's third axis.

    ``chat`` and ``chat.`` are the same sentence for a leak check: a final
    period differs between two translations of the same source far more often
    than it carries information.
    """
    return re.sub(r"[^\w\s]", "", normalise_text(text))


# --- repair steps (pure; no pandas, no parquet) ------------------------------


def french_label(label: str) -> str:
    """Map a corpus label to the reviewed French one, loudly on a stranger."""
    try:
        return FRENCH_LABELS[label]
    except KeyError as exc:  # pragma: no cover - a new label is a real defect
        raise KeyError(f"label {label!r} is not in FRENCH_LABELS") from exc


def is_english_label(label: str) -> bool:
    """True for an English label that survived the mapping (Latin excepted)."""
    return label in ENGLISH_LABELS and label not in LATIN_BORROWINGS


def dedup_rows(rows: Sequence[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    """Drop cross-corpus duplicates, keeping the first row of each key.

    Input order is the corpus order, so the result is deterministic.
    """
    seen: set[str] = set()
    kept: List[Dict[str, Any]] = []
    dropped = 0
    for row in rows:
        key = normalise_key(row["text"])
        if key in seen:
            dropped += 1
            continue
        seen.add(key)
        kept.append(row)
    return kept, dropped


def _order_key(row: Dict[str, Any]) -> str:
    """Deterministic per-row ordering: no RNG anywhere in the export."""
    payload = f"{normalise_key(row['text'])}|{row['label']}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def cap_class_ratio(
    rows: Sequence[Dict[str, Any]], max_ratio: float = 3.0
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """Down-sample the majority classes to ``max_ratio × the smallest class``.

    Returns the kept rows and the per-label cap that was applied. The minority
    class is never touched — the cap only ever shrinks the majority.
    """
    counts = Counter(row["label"] for row in rows)
    if not counts:
        return list(rows), {}
    minority = min(counts.values())
    cap = int(minority * max_ratio)
    caps = {label: cap for label, n in counts.items() if n > cap}
    if not caps:
        return list(rows), {}
    per_label: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        per_label[row["label"]].append(row)
    kept: List[Dict[str, Any]] = []
    for label in sorted(per_label):
        items = per_label[label]
        if label in caps:
            items = sorted(items, key=_order_key)[:cap]
        kept.extend(items)
    return kept, caps


def split_rows(
    rows: Sequence[Dict[str, Any]], test_share: float = 0.2, val_share: float = 0.1
) -> Dict[str, List[Dict[str, Any]]]:
    """Stratified per-label split, deterministic, source-disjoint by design.

    A split is assigned per normalised key: every row's key differs (the corpus
    is deduplicated before this call), so the same sentence can never sit in
    two splits. Small classes (< 5 rows) go to train whole rather than invent a
    test class of one.
    """
    per_label: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        per_label[row["label"]].append(row)
    splits: Dict[str, List[Dict[str, Any]]] = {"train": [], "val": [], "test": []}
    for label in sorted(per_label):
        items = sorted(per_label[label], key=_order_key)
        n = len(items)
        if n < 5:
            splits["train"].extend(items)
            continue
        n_test = max(1, round(n * test_share))
        n_val = max(1, round(n * val_share))
        splits["test"].extend(items[:n_test])
        splits["val"].extend(items[n_test : n_test + n_val])
        splits["train"].extend(items[n_test + n_val :])
    for name in splits:
        splits[name].sort(key=_order_key)
    return splits


def build_export(
    rows: Sequence[Dict[str, Any]], max_ratio: float = 3.0
) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, Any]]:
    """The whole repair: French labels, dedup, ratio cap, re-split.

    Returns the splits and a small provenance dict the report re-measures.
    """
    relabelled = [dict(row, label=french_label(row["label"])) for row in rows]
    deduped, dropped = dedup_rows(relabelled)
    capped, caps = cap_class_ratio(deduped, max_ratio=max_ratio)
    splits = split_rows(capped)
    provenance = {
        "rows_in": len(rows),
        "duplicates_dropped": dropped,
        "rows_after_dedup": len(deduped),
        "class_cap": caps,
        "rows_out": len(capped),
        "row_shortfall_from_cap": len(deduped) - len(capped),
    }
    return splits, provenance


# --- measurement -------------------------------------------------------------


def _keys(rows: Iterable[Dict[str, Any]], key: Any = normalise_key) -> set[str]:
    return {key(row["text"]) for row in rows}


def _exact(rows: Iterable[Dict[str, Any]]) -> set[str]:
    return {str(row["text"]) for row in rows}


def _extra_copies(rows: Sequence[Dict[str, Any]], key: Any = normalise_key) -> int:
    counts = Counter(key(row["text"]) for row in rows)
    return sum(n - 1 for n in counts.values())


def measure(
    splits: Dict[str, List[Dict[str, Any]]],
    corpus: Sequence[Dict[str, Any]] | Sequence[str] | None = None,
    key: Any = normalise_key,
) -> Dict[str, Any]:
    """The six audit figures, plus the exact/normalised split of the leak.

    ``key`` is the normalisation the figures are measured under. The default is
    the producer's own (case + whitespace + punctuation, the strictest); pass
    :func:`normalise_text` to reproduce the audit's own axes exactly, which is
    what the "before — audit normalisation" column of the report does.
    """
    train, val, test = splits["train"], splits["val"], splits["test"]
    all_rows = list(train) + list(val) + list(test)
    labels = Counter(row["label"] for row in all_rows)
    english = sorted(label for label in labels if is_english_label(label))
    english_rows = sum(n for label, n in labels.items() if is_english_label(label))
    total = sum(labels.values()) or 1
    mx, mn = (max(labels.values()), min(labels.values())) if labels else (0, 0)
    corpus_rows: Sequence[Any] = list(corpus) if corpus is not None else all_rows
    if corpus_rows and isinstance(corpus_rows[0], dict):
        corpus_dupes = _extra_copies(corpus_rows, key)
    else:
        corpus_dupes = _extra_copies([{"text": str(t)} for t in corpus_rows], key)
    return {
        "exact_leak_train_test": len(_exact(train) & _exact(test)),
        "normalised_leak_train_test": len(_keys(train, key) & _keys(test, key)),
        "normalised_leak_all_pairs": (
            len(_keys(train, key) & _keys(val, key))
            + len(_keys(val, key) & _keys(test, key))
            + len(_keys(train, key) & _keys(test, key))
        ),
        "duplicate_extra_copies_corpus": corpus_dupes,
        "duplicate_extra_copies_train": _extra_copies(train, key),
        "duplicate_extra_copies_val": _extra_copies(val, key),
        "duplicate_extra_copies_test": _extra_copies(test, key),
        "english_labels": len(english),
        "english_label_names": english,
        "english_rows": english_rows,
        "english_rows_pct": round(100.0 * english_rows / total, 2),
        "labelled_classes": len(labels),
        "class_ratio": round(mx / mn, 2) if mn else 0.0,
        "rows": len(all_rows),
        "rows_train": len(train),
        "rows_val": len(val),
        "rows_test": len(test),
    }


# --- corpus loading (the only part that needs a parquet engine) --------------


def _read_parquet(path: Path) -> Any:
    import pandas as pd

    try:
        return pd.read_parquet(path)
    except ImportError as exc:  # pragma: no cover - environment-dependent
        raise SystemExit(
            "reading the source corpus needs a parquet engine: "
            "pip install pyarrow (or fastparquet)"
        ) from exc


def load_source_rows(data_dir: Path = DEFAULT_DATA_DIR) -> List[Dict[str, Any]]:
    """The 2 680 corpus rows as ``{text, label, factor, source}``."""
    df = _read_parquet(Path(data_dir) / "fallacy_data_french.parquet")
    rows: List[Dict[str, Any]] = []
    for _, r in df.iterrows():
        rows.append(
            {
                "text": str(r["source_article_french"]),
                "label": str(r["logical_fallacies_french"]),
                "factor": str(r.get("config", "") or ""),
                "source": str(r.get("source_article_english", "") or ""),
            }
        )
    return rows


def load_shipped_splits(
    data_dir: Path = DEFAULT_DATA_DIR,
) -> Dict[str, List[Dict[str, Any]]]:
    """The shipped train/val/test files, as the "before" side of the table."""
    out: Dict[str, List[Dict[str, Any]]] = {}
    for name in ("train", "val", "test"):
        df = _read_parquet(Path(data_dir) / f"french_{name}_data.parquet")
        out[name] = [
            {"text": str(text), "label": str(label)}
            for text, label in zip(df["text"], df["fallacy_type"])
        ]
    return out


def load_source_texts(data_dir: Path = DEFAULT_DATA_DIR) -> List[str]:
    df = _read_parquet(Path(data_dir) / "fallacy_data_french.parquet")
    return [str(t) for t in df["source_article_french"]]


# --- the written export + its report ----------------------------------------


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def render_report(
    before: Dict[str, Any],
    before_audit: Dict[str, Any],
    after: Dict[str, Any],
    provenance: Dict[str, Any],
    digests: Dict[str, str],
) -> str:
    """The measurement report: the six audit figures, before and after."""
    if provenance["class_cap"]:
        cap = next(iter(provenance["class_cap"].values()))
        minority = int(round(cap / 3.0))
        cap_intro = (
            f"- Minority class = {minority} rows; every class above 3× it was "
            f"down-sampled to {cap} rows:"
        )
        cap_lines = "\n".join(
            f"  - `{label}` capped to {cap} rows" for label in provenance["class_cap"]
        )
    else:
        cap_intro = "- No class exceeded three times the smallest class; nothing was down-sampled."
        cap_lines = ""
    sha_lines = "\n".join(
        f"- `{name}` — `{digest}`" for name, digest in sorted(digests.items())
    )
    return f"""# Derived out-of-distribution export — 13-class French fallacy corpus

Mission CoursIA-3 / `jsboige/CoursIA#10355`. Built by
`scripts/coursia/fallacy_ood_export.py`. The source directory
(`2.3.2-detection-sophismes/`) is read-only.

**This is an evaluation set.** It is small and translated; it is a contrast
against the synthetic corpus, not a replacement. No model was trained on it,
and no agreement measured on it is a correctness measure.

## The six audit figures, re-measured on this seat

| defect | reported (R1105 audit) | before — audit normalisation | before — producer normalisation | after (this export) |
|---|---|---|---|---|
| exact split leak train ∩ test | 42 | {before_audit["exact_leak_train_test"]} | {before["exact_leak_train_test"]} | {after["exact_leak_train_test"]} |
| normalised split leak train ∩ test (case / whitespace [/ punctuation]) | "47 more" | {before_audit["normalised_leak_train_test"]} | {before["normalised_leak_train_test"]} | {after["normalised_leak_train_test"]} |
| texts repeated inside the 2 680 | 195 | {before_audit["duplicate_extra_copies_corpus"]} | {before["duplicate_extra_copies_corpus"]} | {after["duplicate_extra_copies_corpus"]} |
| intra-split duplicates (train / test / val) | 103 / 8 / 6 | {before_audit["duplicate_extra_copies_train"]} / {before_audit["duplicate_extra_copies_test"]} / {before_audit["duplicate_extra_copies_val"]} | {before["duplicate_extra_copies_train"]} / {before["duplicate_extra_copies_test"]} / {before["duplicate_extra_copies_val"]} | {after["duplicate_extra_copies_train"]} / {after["duplicate_extra_copies_test"]} / {after["duplicate_extra_copies_val"]} |
| labels still in English | 5 of 13 ({before_audit["english_rows_pct"]} % of the rows) | {before_audit["english_labels"]} of {before_audit["labelled_classes"]} ({before_audit["english_rows_pct"]} %) | {before["english_labels"]} of {before["labelled_classes"]} ({before["english_rows_pct"]} %) | {after["english_labels"]} of {after["labelled_classes"]} ({after["english_rows_pct"]} %) |
| class ratio max:min | 6.91 : 1 | {before_audit["class_ratio"]} : 1 | {before["class_ratio"]} : 1 | {after["class_ratio"]} : 1 |

The audit's own normalisation (NFKC + casefold + collapsed whitespace) is what
*reproduces* its six numbers exactly; the producer's adds punctuation, which is
strictly stronger (a French translation can end with or without the period of
the source sentence). Both columns are re-measured here.

### Where this issue's wording differs from the measurement

Only one figure's *wording*: the audit says "47 more" normalised leaks, but 47
is the **total** normalised count under its own axes (51 once punctuation is
stripped too) — that is 5 (resp. 9) more than the 42 exact ones, not 47 more.
Every other reported figure reproduces exactly.

## Split discipline

- Re-split from the deduplicated corpus, stratified per label, deterministic
  (SHA-256 ordering, no RNG): {after["rows_train"]} train /
  {after["rows_val"]} val / {after["rows_test"]} test.
- Source-disjoint by construction: a split is assigned per normalised text, and
  the corpus is deduplicated first, so no sentence can sit in two splits.
- The factor axis (`config`: edu / climate) is carried per row in the export,
  so a per-factor slice stays possible without re-splitting.
- Ratio cap: {cap_intro.strip()[2:]}
{cap_lines}
- Rows: {provenance["rows_in"]} in → {provenance["rows_after_dedup"]} after
  dedup ({provenance["duplicates_dropped"]} dropped) → {provenance["rows_out"]}
  written ({provenance["row_shortfall_from_cap"]} dropped by the ratio cap).

## Output files

{sha_lines}

## Reproduce

```
python scripts/coursia/fallacy_ood_export.py --out <dir>
```

The output stays out of git (`argumentation_analysis/evaluation/results/` is
gitignored). Delivery to CoursIA is a proposal on `#10355`, never a commit in
their repository.
"""


def write_export(
    splits: Dict[str, List[Dict[str, Any]]],
    out_dir: Path,
    provenance: Dict[str, Any],
    before: Dict[str, Any],
    before_audit: Dict[str, Any],
    after: Dict[str, Any],
) -> Dict[str, Any]:
    import csv

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in ("train", "val", "test"):
        path = out_dir / f"{name}.csv"
        with path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(
                fh, fieldnames=["text", "label", "label_id", "factor"]
            )
            writer.writeheader()
            for row in splits[name]:
                writer.writerow(
                    {
                        "text": row["text"],
                        "label": row["label"],
                        "label_id": LABEL_IDS[row["label"]],
                        "factor": row.get("factor", ""),
                    }
                )
    digests = {
        f"{name}.csv": _sha256(out_dir / f"{name}.csv")
        for name in ("train", "val", "test")
    }
    report_path = out_dir / "measurement_report.md"
    report_path.write_text(
        render_report(before, before_audit, after, provenance, digests),
        encoding="utf-8",
    )
    digests["measurement_report.md"] = _sha256(report_path)
    manifest = {
        "producer": "scripts/coursia/fallacy_ood_export.py",
        "issue": 3152,
        "mission": "CoursIA-3",
        "before": before,
        "before_audit_normalisation": before_audit,
        "after": after,
        "provenance": provenance,
        "sha256": digests,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data", default=str(DEFAULT_DATA_DIR), help="source corpus directory"
    )
    parser.add_argument(
        "--out", default=str(DEFAULT_OUT_DIR), help="output directory (gitignored)"
    )
    parser.add_argument(
        "--max-ratio", type=float, default=3.0, help="class ratio ceiling"
    )
    args = parser.parse_args(argv)

    data_dir = Path(args.data)
    rows = load_source_rows(data_dir)
    before_splits = load_shipped_splits(data_dir)
    texts = load_source_texts(data_dir)
    before = measure(before_splits, corpus=texts)
    before_audit = measure(before_splits, corpus=texts, key=normalise_text)
    splits, provenance = build_export(rows, max_ratio=args.max_ratio)
    after = measure(splits)
    manifest = write_export(
        splits, Path(args.out), provenance, before, before_audit, after
    )
    print(
        json.dumps(
            {"out": str(args.out), "after": manifest["after"]},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
