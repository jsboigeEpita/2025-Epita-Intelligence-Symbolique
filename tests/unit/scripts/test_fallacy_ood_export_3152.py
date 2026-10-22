"""#3152 — the derived fallacy export removes the six audited defects.

Mission CoursIA-3. The producer is `scripts/coursia/fallacy_ood_export.py`; it
reads the student directory read-only and writes a gitignored export. These
tests exercise the pure repair functions on a fixture that **plants one of each
defect**, so a producer that silently stopped repairing would redden here
instead of only on the full corpus:

- an exact duplicate (same string twice) and a normalised one (case / spacing /
  final punctuation) — both must be dropped, and dropping only the exact one is
  a failure;
- an English label — it must come out mapped to the reviewed French one;
- duplicated rows inside a split — none may remain;
- a class ratio above 3:1 — the cap must bring it down without touching the
  minority class.

The control is a clean fixture: the export must keep every row and drop none.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter

import pytest

from scripts.coursia.fallacy_ood_export import (
    FRENCH_LABELS,
    build_export,
    cap_class_ratio,
    dedup_rows,
    french_label,
    is_english_label,
    measure,
    normalise_key,
    normalise_text,
    split_rows,
)


def _k(text: str) -> str:
    """The test's OWN normalisation, written here so the leak witness does not
    borrow the producer's function: a mutation inside that function would
    otherwise blind the instrument that is supposed to catch it."""
    s = unicodedata.normalize("NFKC", str(text)).casefold()
    s = re.sub(r"\s+", " ", s).strip()
    return re.sub(r"[^\w\s]", "", s)


_MANY = "faulty generalization"  # English on purpose: the mapping must repair it
_FEW = "faux dilemme"


def _row(text: str, label: str, factor: str = "edu") -> dict:
    return {"text": text, "label": label, "factor": factor}


def _base_rows(n_many: int = 6, n_few: int = 6):
    rows = [_row(f"Phrase edu numero {i}.", _MANY) for i in range(n_many)]
    rows += [_row(f"Phrase climate numero {i}.", _FEW, "climate") for i in range(n_few)]
    return rows


def _defective_rows():
    rows = _base_rows()
    rows.append(_row("Phrase edu numero 2.", _MANY))  # exact duplicate
    rows.append(_row("   PHRASE   EDU numero 3 ", _MANY))  # normalised duplicate
    return rows


def _splits():
    splits, _provenance = build_export(_defective_rows())
    return splits


class TestTheDefectsAreGone:
    def test_no_normalised_leak_between_any_two_splits(self):
        splits = _splits()
        keys = {name: {_k(r["text"]) for r in rows} for name, rows in splits.items()}
        for a, b in (("train", "test"), ("train", "val"), ("val", "test")):
            assert not (keys[a] & keys[b]), f"leak between {a} and {b}"

    def test_no_duplicate_inside_a_split(self):
        for name, rows in _splits().items():
            counts = Counter(_k(r["text"]) for r in rows)
            assert max(counts.values(), default=0) <= 1, f"duplicate inside {name}"

    def test_no_english_label_survives(self):
        for rows in _splits().values():
            for row in rows:
                assert not is_english_label(row["label"]), row["label"]
                assert row["label"] in FRENCH_LABELS.values()

    def test_both_duplicates_are_dropped_not_only_the_exact_one(self):
        # The mutation contract: drop the normalisation and only ONE of the two
        # planted duplicates is caught — this assertion goes red.
        _splits_ignored, provenance = build_export(_defective_rows())
        assert provenance["duplicates_dropped"] == 2

    def test_the_ratio_ceiling_holds(self):
        after = measure(_splits())
        assert after["class_ratio"] <= 3.0


class TestTheControl:
    def test_a_clean_fixture_keeps_every_row(self):
        rows = _base_rows()
        splits, provenance = build_export(rows)
        assert provenance["duplicates_dropped"] == 0
        assert provenance["row_shortfall_from_cap"] == 0
        assert sum(len(s) for s in splits.values()) == len(rows)

    def test_a_clean_fixture_has_no_defect_left(self):
        splits, _ = build_export(_base_rows())
        after = measure(splits)
        assert after["normalised_leak_all_pairs"] == 0
        assert after["duplicate_extra_copies_train"] == 0
        assert after["english_labels"] == 0


class TestTheRatioCap:
    def test_it_only_shrinks_the_majority(self):
        rows = [_row(f"majoritaire {i}", _MANY) for i in range(10)]
        rows += [_row(f"minoritaire {i}", _FEW) for i in range(2)]
        kept, caps = cap_class_ratio(rows, max_ratio=3.0)
        counts = Counter(r["label"] for r in kept)
        assert counts[_FEW] == 2, "the minority class is never touched"
        assert counts[_MANY] == 6, "10 -> 3 x 2"
        assert caps == {_MANY: 6}

    def test_a_balanced_corpus_is_left_alone(self):
        rows = [_row(f"a {i}", _MANY) for i in range(4)] + [
            _row(f"b {i}", _FEW) for i in range(3)
        ]
        kept, caps = cap_class_ratio(rows, max_ratio=3.0)
        assert caps == {}
        assert len(kept) == len(rows)


class TestDeterminism:
    def test_the_split_is_stable_and_order_independent(self):
        rows = _base_rows(n_many=12, n_few=12)
        first = split_rows(rows)
        second = split_rows(list(reversed(rows)))
        assert {k: [r["text"] for r in v] for k, v in first.items()} == {
            k: [r["text"] for r in v] for k, v in second.items()
        }

    def test_small_classes_go_to_train_whole(self):
        rows = _row("unique petit", _FEW)
        splits = split_rows([rows])
        assert splits["train"] and not splits["val"] and not splits["test"]


class TestTheLabelTable:
    def test_every_corpus_label_has_a_french_rendering(self):
        assert len(FRENCH_LABELS) == 13
        assert len(set(FRENCH_LABELS.values())) == 13, "one French label per class"
        for value in FRENCH_LABELS.values():
            assert not is_english_label(value), value

    def test_the_five_english_rows_are_translated_not_copied(self):
        # The audit's "5 of 13 English labels": those five keys must come out
        # with a different, French rendering.
        for key in (
            "fallacy of credibility",
            "fallacy of extension",
            "fallacy of logic",
            "faulty generalization",
            "intentional",
        ):
            assert is_english_label(key)
            assert FRENCH_LABELS[key] != key, key
            assert not is_english_label(FRENCH_LABELS[key])

    def test_an_unknown_label_fails_loudly(self):
        with pytest.raises(KeyError):
            french_label("sophisme inventé")

    def test_the_normalisation_ignores_case_space_and_punctuation(self):
        assert normalise_key("  Le Chat.  ") == normalise_key("le   chat")
        assert normalise_text("  Le Chat.  ") == "le chat."
