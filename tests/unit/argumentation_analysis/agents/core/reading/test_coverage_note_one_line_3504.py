"""#3504 — one line per item, even when a field carries a line break.

The coordinator's replay measured the promise broken: 5 of 27 recorded FOL
translations carry line breaks (19 in all), so the 45 modal/FOL items of the
R1156 records rendered as 65 lines — and 32 breaks across the 56 recorded
quotes. A continuation line starts with neither the item marker nor its
position: Act II reads a fragment as a line of its own.

The witnesses pin the render's one rule and its limit:

* a quote, a formula, a conclusion, a reason or a retained label that carries
  a line break still renders as exactly ONE line;
* a note with N items has N + 1 lines (the header, then one per item);
* the render leaves the RECORDED fields untouched — the quote keeps its
  verbatim form (what ``anchor_quote_in`` matches), the formula what the
  solver read.

The document and its passages are made up: no corpus text, no source name.
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.agents.core.reading.coverage_review import (
    LENS_BY_CLASS,
    coverage_review_note,
)


def item_with_breaks(**overrides) -> dict:
    """One review item whose every free-text field carries a line break."""
    base = {
        "unit_id": "",
        "quote": "Première ligne de la citation,\ndeuxième ligne de la citation.",
        "offset": 42,
        "class": "inferential",
        "lens": LENS_BY_CLASS["inferential"],
        "reason": "une raison\nsur deux lignes",
        "conclusion": "conclut ceci\net cela",
        "rank": 1,
        "routed": {
            "lens": LENS_BY_CLASS["inferential"],
            "status": "answered",
            "finding": {
                "status": "answered",
                "verdict": "consistent_with_run_kb",
                "formula": "premise_one\n=> conclusion",
                "shared_symbols": 2,
            },
        },
    }
    base.update(overrides)
    return base


def record_with(*items: dict) -> dict:
    return {
        "status": "ok",
        "items": list(items),
        "examined": 1,
        "examined_by_class": {},
        "document_chars": 1000,
        "dropped": {},
        "reason": "",
        "basis": "coverage_review",
    }


def state_with(record: dict) -> SimpleNamespace:
    return SimpleNamespace(coverage_review=record, raw_text="x" * 1000)


def test_an_item_whose_fields_carry_breaks_renders_as_one_line():
    state = state_with(record_with(item_with_breaks()))

    note = coverage_review_note(state)
    lines = [line for line in note.splitlines() if line.strip()]

    assert len(lines) == 2  # the header, then EXACTLY one line for the item
    item_line = lines[1]
    # Every field IS rendered — flattened, never truncated, never split.
    assert "Première ligne de la citation, deuxième ligne de la citation." in item_line
    assert "premise_one => conclusion" in item_line
    assert "une raison sur deux lignes" in item_line
    assert "conclut ceci et cela" in item_line


def test_a_note_with_n_items_has_n_plus_one_lines():
    items = [
        item_with_breaks(rank=1),
        item_with_breaks(quote="Citation simple sans retour.", rank=2, unit_id=""),
        item_with_breaks(quote="Troisième citation\navec retour.", rank=3),
    ]
    state = state_with(record_with(*items))

    note = coverage_review_note(state)
    lines = [line for line in note.splitlines() if line.strip()]

    assert len(lines) == 1 + 3


def test_the_render_leaves_the_recorded_fields_as_recorded():
    raw = item_with_breaks()
    state = state_with(record_with(raw))

    note = coverage_review_note(state)

    assert "Première ligne" in note  # the render ran
    # The RECORD keeps its verbatim form: the quote stays what the document
    # carries (the anchor's own input), the formula what the solver read.
    assert "\n" in state.coverage_review["items"][0]["quote"]
    assert "\n" in state.coverage_review["items"][0]["routed"]["finding"]["formula"]


def test_a_retained_label_with_a_break_stays_on_the_item_line():
    item = item_with_breaks(
        routed={
            "lens": LENS_BY_CLASS["statistical"],
            "status": "answered",
            "finding": {
                "status": "answered",
                "fallacies": [
                    {
                        "fallacy_type": "Un nom de procédé\nsur deux lignes",
                        "family": "Influence",
                    }
                ],
            },
        },
    )
    item["class"] = "statistical"
    item["lens"] = LENS_BY_CLASS["statistical"]
    state = state_with(record_with(item))

    note = coverage_review_note(state)
    lines = [line for line in note.splitlines() if line.strip()]

    assert len(lines) == 2
    assert "Un nom de procédé sur deux lignes" in lines[1]
