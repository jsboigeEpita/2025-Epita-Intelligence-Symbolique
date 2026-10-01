# -*- coding: utf-8 -*-
"""#2895: JTMS premise beliefs carry the selected units' own ids.

Since #2887's stratified selection, ``_invoke_jtms`` labelled its premise
beliefs ``arg_{i+1}`` by position in the SELECTION — on the #2850 paid run,
10/10 beliefs carried another unit's label, and ``compute_argument_convergence``
counted the 3 retraction signals on the wrong units (belief confidences were
read by the same index, and Step 6's quality annotations indexed the same
way). The ids are now the selected units' own ``unit_id``.

Born red on ``main`` (``229ed66ff``): a stratified pick over 30 units at
budget 10 is not a prefix — its second unit is ``arg_4``, not ``arg_2``.
"""

import asyncio

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.invoke_callables import _invoke_jtms
from argumentation_analysis.orchestration.selection import (
    merged_population_units,
    select_for_budget,
    state_text_length,
)
from argumentation_analysis.orchestration.state_writers import _write_jtms_to_state
from argumentation_analysis.plugins.narrative_synthesis_plugin import (
    compute_argument_convergence,
)

_N_UNITS = 30
_BUDGET = 10


def _population_state():
    """A state whose merged population (30 units, permutation-scattered
    offsets) makes the stratified pick at 10 differ from the population's
    head: the offset order of the ids is not the insertion order."""
    text = " ".join(
        f"Sentence {i:02d} of the source document unfolds here." for i in range(60)
    )
    state = UnifiedAnalysisState(text)
    state.identified_arguments = {
        f"arg_{i}": f"Unit {i:02d} claims something specific about point {i:02d}."
        for i in range(1, _N_UNITS + 1)
    }
    # (i * 7) % 31 is a bijection on 1..30 — distinct offsets, and the
    # offset order of the ids is not 1, 2, 3, …
    state.argument_provenance = {
        f"arg_{i}": {"producer": "test", "offset": ((i * 7) % 31) * 95}
        for i in range(1, _N_UNITS + 1)
    }
    return state


def _context_for(state, target_unit=None):
    extract = {"arguments": [], "claims": []}
    fallacies = []
    if target_unit is not None:
        fallacies.append({"type": "ad_hominem", "target_argument": target_unit.text})
    return {
        "_state_object": state,
        "phase_extract_output": extract,
        "phase_hierarchical_fallacy_output": {"fallacies": fallacies},
    }


def _premise_names(result):
    return [
        name
        for name, data in result["beliefs"].items()
        if isinstance(data.get("context"), dict)
        and data["context"].get("belief_type") == "premise"
    ]


def _selection_of(state):
    return select_for_budget(
        merged_population_units(state), _BUDGET, text_length=state_text_length(state)
    ).selected


def test_premise_beliefs_carry_the_selected_units_ids():
    """DoD 1: each belief name starts with its unit's own id — on main the
    second belief said ``arg_2:`` while the second selected unit was not
    ``arg_2``."""
    state = _population_state()
    selected = _selection_of(state)

    # The witness's precondition: a stratified pick that is not a prefix.
    assert selected[1].unit_id != "arg_2", "population no longer discriminates"

    result = asyncio.run(_invoke_jtms(state.raw_text, _context_for(state)))
    premises = _premise_names(result)
    assert len(premises) == _BUDGET

    for unit, name in zip(selected, premises):
        assert name.startswith(
            f"{unit.unit_id}:"
        ), f"belief {name!r} does not carry unit {unit.unit_id}'s id"


def test_convergence_attributes_the_retraction_to_the_real_unit():
    """DoD 2: a fallacy undermining the 5th selected unit produces a
    'JTMS retracte' signal on THAT unit's id — on main the signal landed on
    the 5th belief's positional label instead."""
    state = _population_state()
    selected = _selection_of(state)
    target = selected[4]
    positional_wrong_id = f"arg_{5}"  # 5th belief's label on main
    assert target.unit_id != positional_wrong_id, "population no longer discriminates"

    result = asyncio.run(
        _invoke_jtms(state.raw_text, _context_for(state, target_unit=target))
    )
    _write_jtms_to_state(result, state, {})

    convergence = compute_argument_convergence(state)
    retracted_ids = [
        arg_id
        for arg_id, data in convergence.items()
        if any(method == "JTMS retracte" for method, _ in data["signals"])
    ]

    assert retracted_ids == [
        target.unit_id
    ], f"retraction attributed to {retracted_ids}, expected [{target.unit_id}]"
