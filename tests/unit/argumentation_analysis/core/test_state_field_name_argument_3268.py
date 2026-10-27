"""#3268 — ``add_argument`` refuses a description that IS a state field name.

The committed CoursIA run shows ``arg_1 : "analysis_state"`` and
``arg_2 : "arguments"``: the extractor echoed a container name back as if it
were a substantive argument, and the trunk's writer accepted it without a
word. Every downstream reader (coverage, report, belief states) then counts a
phantom unit.

The DoD forbids the easy fix (a hardcoded blacklist of the two literals, which
is a pendulum and ages badly): the refused vocabulary is derived from the
state **instance** at run time. These witnesses hold that property — a
subclass adding its own field must be refused without touching the writer.

Born-red on ``main``: ``test_field_name_is_not_accepted_as_an_argument``
fails there because ``add_argument`` accepts any string.
"""

from __future__ import annotations

import pytest

from argumentation_analysis.core.shared_state import RhetoricalAnalysisState

RAW_TEXT = (
    "La réforme proposée réduit les dépenses de fonctionnement, mais elle "
    "transfère la charge sur les collectivités locales."
)


def make_state() -> RhetoricalAnalysisState:
    return RhetoricalAnalysisState(RAW_TEXT)


def test_field_name_is_not_accepted_as_an_argument() -> None:
    """Every field of THIS instance is refused — vocabulary derived, not listed."""
    state = make_state()
    fields = sorted(vars(state))
    assert fields, "vars(state) must expose the instance fields (#3268 relies on it)"
    for field_name in fields:
        with pytest.raises(ValueError):
            state.add_argument(field_name)


def test_refused_vocabulary_comes_from_the_instance_not_a_constant() -> None:
    """A subclass field is refused without editing the writer (anti-pendulum)."""

    class ExtendedState(RhetoricalAnalysisState):
        def __init__(self, initial_text: str) -> None:
            super().__init__(initial_text)
            self.verdict_ledger = {}

    state = ExtendedState(RAW_TEXT)
    assert "verdict_ledger" in vars(state)
    with pytest.raises(ValueError):
        state.add_argument("verdict_ledger")


def test_refusal_leaves_no_partial_entry() -> None:
    """A refused description writes nothing — no id consumed, no phantom unit."""
    state = make_state()
    with pytest.raises(ValueError):
        state.add_argument("identified_arguments")
    assert state.identified_arguments == {}
    assert state.argument_provenance == {}


def test_paraphrase_absent_from_raw_text_is_accepted() -> None:
    """Non-regression: the gate is about field names, never about quoting.

    A substantive description that does not appear literally in ``raw_text``
    stays accepted — the writer is not a quote checker.
    """
    state = make_state()
    paraphrase = "Le financement des communes reste flou"
    assert paraphrase not in RAW_TEXT
    arg_id = state.add_argument(paraphrase)
    assert state.identified_arguments[arg_id] == paraphrase


def test_provenance_path_still_accepts_a_real_argument() -> None:
    """The production signature (producer/quote/offset) is unchanged."""
    state = make_state()
    quote = "elle transfère la charge sur les collectivités locales"
    arg_id = state.add_argument(quote, producer="llm_extract", source_quote=quote)
    assert state.identified_arguments[arg_id] == quote
    assert state.argument_provenance[arg_id]["producer"] == "llm_extract"
