"""#2344: Sherlock's ``instant_deduction`` tool says it is a positional guess.

Measured on ``main`` ``6dd102927``, the tool returned:
- a pick by list position (last suspect, middle weapon, first room);
- ``confidence: 0.85`` and a rationale, both fabricated;
- ``method: "instant_sherlock_logic"``.

It used no clue (``partial_info`` was ignored). Given input that was not JSON,
it invented a default game. Given empty lists, it invented placeholder names.
The model that calls the tool read all of that as a deduction.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from semantic_kernel import Kernel

from argumentation_analysis.agents.core.pm.sherlock_enquete_agent import SherlockTools

ELEMENTS = {
    "suspects": ["A", "B", "C"],
    "armes": ["W1", "W2", "W3", "W4"],
    "lieux": ["L1", "L2"],
}


def _tools() -> SherlockTools:
    return SherlockTools(MagicMock(spec=Kernel))


async def test_the_pick_is_labelled_a_guess_without_a_confidence():
    result = json.loads(
        await _tools().instant_deduction(
            json.dumps(ELEMENTS), partial_info="B a montré la carte W3"
        )
    )
    assert result["method"] == "positional_guess"
    assert result["clues_used"] is False
    assert "confidence" not in result
    assert "pas une déduction" in result["reasoning"]


async def test_the_positional_pick_itself_is_unchanged():
    # Control: the capability stays, only its label changes.
    result = json.loads(await _tools().instant_deduction(json.dumps(ELEMENTS)))
    assert (result["suspect"], result["arme"], result["lieu"]) == ("C", "W3", "L1")


async def test_non_json_elements_are_refused_not_replaced_by_an_invented_game():
    result = await _tools().instant_deduction("suspects: A, B, C")
    assert result.startswith("Erreur déduction")
    assert "get_cluedo_game_elements" in result
    for invented in ("Colonel Moutarde", "Mme Leblanc", "Mme Pervenche"):
        assert invented not in result


async def test_an_empty_list_is_refused_not_filled_with_a_placeholder():
    elements = dict(ELEMENTS, armes=[])
    result = await _tools().instant_deduction(json.dumps(elements))
    assert result.startswith("Erreur déduction")
    assert "armes" in result
    assert "Inconnue" not in result


async def test_the_model_is_told_the_tool_does_not_deduce():
    # The function-calling schema is what the model reads before calling it.
    description = SherlockTools.instant_deduction.__kernel_function_description__
    assert "PAS une déduction" in description
    assert "faire_suggestion" in description
