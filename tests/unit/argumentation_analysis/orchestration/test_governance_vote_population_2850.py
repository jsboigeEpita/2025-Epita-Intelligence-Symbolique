"""#2850 R1107 — the VOTE's own population, recorded apart from the conflict's.

One key, two producers. On the R1106 state the record named the CONFLICT
selection (``analysis_coverage["governance"]`` — 6 units of the merged
population: arg_16/27/42/50/70/85) while the verdict was decided over the
QUALITY population (the keys of ``per_argument_scores``: arg_15/23/29/39/46/53/70/85).
The two sets differ, and the winner (arg_15) was not even among the units
the record named. Any reader asking "the deliberation examined k of N units"
would have quoted the wrong k AND the wrong units.

The witness (this file):

* the CONFLICT keeps its own record, untouched;
* the VOTE records its own population — ``governance_vote`` coverage plus
  ``vote_population`` on the verdict and on the decision record;
* the winner IS a member of the recorded vote population;
* a degraded vote (no collective choice) records NO population — an
  honest absence, never a zero that reads as a coverage.

No JVM, no LLM, synthetic opaque ids only (privacy HARD).
"""

from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import patch

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.invoke_callables import _invoke_governance
from argumentation_analysis.orchestration.state_writers import (
    _write_governance_to_state,
)

#: The vote's population — a strict subset of the merged population, and
#: deliberately NOT the conflict's six units.
_VOTE_IDS = ["arg_2", "arg_7", "arg_11"]


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


def _quality(vote_ids: List[str]) -> Dict[str, Any]:
    """A quality profile over ``vote_ids`` — the population the vote reads."""
    return {
        "per_argument_scores": {
            vote_ids[0]: {"scores_par_vertu": {"clarte": 9.0, "pertinence": 8.0}},
            vote_ids[1]: {"scores_par_vertu": {"clarte": 5.0, "pertinence": 6.0}},
            vote_ids[2]: {"scores_par_vertu": {"clarte": 2.0, "pertinence": 3.0}},
        }
    }


async def _run(state: UnifiedAnalysisState, quality: Dict[str, Any]) -> Dict[str, Any]:
    context: Dict[str, Any] = {
        "phase_extract_output": {"arguments": []},
        "phase_quality_output": quality,
        "_state_object": state,
    }
    with patch(
        "argumentation_analysis.orchestration.invoke_callables._get_openai_client",
        return_value=(None, ""),
    ):
        return await _invoke_governance("texte de travail", context)


@pytest.mark.asyncio
async def test_the_vote_records_its_own_population_apart_from_the_conflicts():
    """The defect: one key, two producers. Two populations ⇒ two records."""
    state = _state_with_units()
    result = await _run(state, _quality(_VOTE_IDS))

    coverage = state.analysis_coverage

    # The conflict detection keeps its own record — unchanged by this fix.
    assert "governance" in coverage
    conflict = coverage["governance"]
    assert conflict["k"] == 6
    assert conflict["N"] == 12

    # The vote records ITS population. Before the fix this key does not exist.
    assert "governance_vote" in coverage, (
        "the vote records no population of its own — the conflict's record is "
        "the only one, and it names another set of units"
    )
    vote = coverage["governance_vote"]
    assert set(vote["unit_ids"]) == set(_VOTE_IDS)
    assert vote["k"] == 3
    assert vote["N"] == 12

    # Two populations, two keys — the conflict's record is NOT the vote's.
    assert vote["unit_ids"] != conflict["unit_ids"]
    assert set(vote["unit_ids"]) & set(conflict["unit_ids"]) != set(_VOTE_IDS)


@pytest.mark.asyncio
async def test_the_winner_is_a_member_of_the_recorded_vote_population():
    """The witness the coordinator asked for: the winner belongs to the
    population the vote recorded. Before the fix nothing tied the two."""
    state = _state_with_units()
    result = await _run(state, _quality(_VOTE_IDS))

    verdict = result["governance_verdict"]
    winner = verdict["winner"]
    assert winner is not None
    recorded = state.analysis_coverage["governance_vote"]["unit_ids"]
    assert winner in recorded

    # The verdict carries the population too (the decision is self-describing).
    population = verdict["vote_population"]
    assert population["unit_ids"] == recorded
    assert population["k"] == 3
    assert population["N"] == 12
    assert winner in population["unit_ids"]


@pytest.mark.asyncio
async def test_the_decision_record_carries_the_vote_population():
    """The record the readers read (``state.governance_decisions``) names the
    population the winner was chosen from."""
    state = _state_with_units()
    result = await _run(state, _quality(_VOTE_IDS))

    _write_governance_to_state(result, state, {})

    assert state.governance_decisions, "the governance decision was not written"
    decision = state.governance_decisions[-1]
    assert decision["winner"] in decision["vote_population"]["unit_ids"]
    assert set(decision["vote_population"]["unit_ids"]) == set(_VOTE_IDS)


@pytest.mark.asyncio
async def test_a_degraded_vote_records_no_population():
    """No collective choice ⇒ no population to record. An honest absence —
    never a zero that renders as a coverage."""
    state = _state_with_units()
    result = await _run(
        state,
        {"per_argument_scores": {"arg_2": {"scores_par_vertu": {"clarte": 9.0}}}},
    )

    assert "governance_vote" not in state.analysis_coverage
    assert "vote_population" not in result["governance_verdict"]
