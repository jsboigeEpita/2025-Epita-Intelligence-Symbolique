"""#3293 — the four review points on the vote's population (po-2023's review).

The review of #3293 (po-2023, COMMENTED on ``a6c42733c``) raised three
objections the coordinator arbitrated (comment 6522889451, R1125):

* **the render moved** — the Act I range sentence reads every key of
  ``analysis_coverage`` except ``anchor_census``/``stakes`` and renders
  ``min(k)..max(k)``. The vote's key entered that range and moved the
  sentence (« de 6 à 15 » became « de 3 à 15 ») on every run where governance
  is derivable. The sentence says what each MODULE SELECTED; the vote
  CONSUMES the quality phase's population. → ``governance_vote`` joins
  ``stakes`` in the exclusion tuple. Witnessed in the reporting suite
  (``test_governance_vote_render_3293.py``).
* **a stateless context fabricated its denominator** — ``N`` was
  ``max(len(units), len(options))``, so with no visible population ``N == k``
  and the record claimed a 100 % coverage over a population nobody can see.
* **k counted the options while the geometry measured the found ones** — an
  option the population does not carry was folded into k, so k, the bands and
  the span described two populations: the shadow of the very defect this PR
  closes, one level down.

This file witnesses the two points that belong to the orchestration side
(the render one lives with the render). No JVM, no LLM, opaque ids only.
"""

from __future__ import annotations

from typing import Any, Dict

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.invoke_callables import (
    _record_governance_vote_population,
)


def _state_with_units() -> UnifiedAnalysisState:
    """A real state carrying 12 units spread over the whole text."""
    raw = (
        "Premiere partie du discourse. " * 40
        + "Deuxieme partie du discourse. " * 40
        + "Troisieme partie du discourse. " * 40
    )
    state = UnifiedAnalysisState(raw)
    step = len(raw) // 12
    for i in range(12):
        state.add_argument(
            f"Synthese de l unite numero {i + 1} du corpus",
            producer="llm_extract",
            source_quote=f"partie {i + 1}",
            offset=i * step,
        )
    return state


def test_a_stateless_context_records_no_denominator():
    """No visible population ⇒ no ``N``.

    Before the fix the record carried ``N == k`` — a 100 % coverage claim over
    a population the record cannot see. The record now carries k and the ids,
    and says nothing about a denominator it cannot see.
    """
    options = ["arg_2", "arg_7", "arg_11"]
    record = _record_governance_vote_population(None, options)

    assert record is not None
    assert "N" not in record, (
        "the record invents a denominator over a population it cannot see — "
        "N == k reads as a 100 % coverage that nobody measured"
    )
    assert record["k"] == len(options)
    assert record["unit_ids"] == options


def test_k_counts_the_units_the_geometry_measured():
    """An option outside the population is recorded APART, never inside k.

    Before the fix ``k`` was the number of options while the bands, the span
    and the stretch described only the ones found in the population — two
    populations under one record. k, the ids and the geometry now describe
    one population; the leftover is named.
    """
    state = _state_with_units()
    options = ["arg_2", "arg_7", "arg_999"]  # arg_999 is not in the population

    record = _record_governance_vote_population(state, options)

    assert record is not None
    # k counts what the geometry measured — the two units it can see.
    assert record["k"] == 2
    assert record["unit_ids"] == ["arg_2", "arg_7"]
    # The unit outside the population is named apart, not folded into k.
    assert record["outside_population"] == ["arg_999"]
    assert "arg_999" not in record["unit_ids"]
    # The denominator is the population the figure is measured on.
    assert record["N"] == 12

    # And the coverage the state keeps describes the SAME two units.
    coverage: Dict[str, Any] = state.analysis_coverage["governance_vote"]
    assert coverage["k"] == 2
    assert coverage["unit_ids"] == ["arg_2", "arg_7"]


def test_the_record_of_a_vote_without_options_is_an_absence():
    """No options ⇒ no record at all — never a zero that reads as coverage."""
    assert _record_governance_vote_population(_state_with_units(), []) is None
