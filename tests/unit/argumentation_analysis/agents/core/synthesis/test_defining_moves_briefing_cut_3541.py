"""A bounded synthesis briefing must cover the whole synthetic document."""

import hashlib
import re
from types import SimpleNamespace

from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
    DeepSynthesisAgent,
)


def _state(count):
    moves = []
    for i in range(count):
        slot = "thesis" if i == 31 else "mechanism" if i == 27 else "pillar"
        moves.append(
            {
                "slot": slot,
                "kind": slot,
                "reading": f"move {i}",
                "quote": "synthetic",
                "offset": i * 300,
            }
        )
    return SimpleNamespace(raw_text="x" * 10000, defining_moves={"moves": moves})


def test_capped_moves_include_slots_and_all_quarters():
    briefing = DeepSynthesisAgent.build_artifact_briefing(_state(33))
    lines = [
        line for line in briefing.splitlines() if "[artifact:defining_moves." in line
    ]
    offsets = [int(re.search(r"offset=(\d+)", line).group(1)) for line in lines]
    assert len(lines) == 15
    assert 9300 in offsets and 8100 in offsets
    assert {min(offset // 2500, 3) for offset in offsets} == {0, 1, 2, 3}
    assert offsets == sorted(offsets)
    assert "- defining_moves: 15 of 33 shown (cap 15 per field)" in briefing


def test_small_population_is_not_truncated():
    briefing = DeepSynthesisAgent.build_artifact_briefing(_state(12))
    lines = [
        line for line in briefing.splitlines() if "[artifact:defining_moves." in line
    ]
    assert len(lines) == 12
    assert "- defining_moves:" not in briefing
    # Measured from origin/main on the identical synthetic state.
    assert hashlib.sha256(briefing.encode("utf-8")).hexdigest() == (
        "7811eef409a8eda8e178e3ecec85aeaf1b2f9148dad9e4f188fd49d4d123c1c7"
    )


def test_missing_positions_still_obeys_cap():
    state = _state(33)
    for move in state.defining_moves["moves"]:
        move.pop("offset")
    briefing = DeepSynthesisAgent.build_artifact_briefing(state)
    lines = [
        line for line in briefing.splitlines() if "[artifact:defining_moves." in line
    ]
    assert len(lines) == 15
    assert any("move 31" in line for line in lines)
    assert any("move 27" in line for line in lines)


def test_zero_budget_selects_no_moves():
    briefing = DeepSynthesisAgent.build_artifact_briefing(
        _state(33), max_items_per_field=0
    )
    assert "[artifact:defining_moves." not in briefing


def test_two_slots_take_precedence_when_budget_is_two():
    briefing = DeepSynthesisAgent.build_artifact_briefing(
        _state(33), max_items_per_field=2
    )
    lines = [
        line for line in briefing.splitlines() if "[artifact:defining_moves." in line
    ]
    assert len(lines) == 2
    assert "move 27" in lines[0]
    assert "move 31" in lines[1]


def test_repeated_slots_do_not_crowd_out_other_quarters():
    state = _state(33)
    state.defining_moves["moves"][0]["slot"] = "thesis"
    briefing = DeepSynthesisAgent.build_artifact_briefing(state, max_items_per_field=6)
    lines = [
        line for line in briefing.splitlines() if "[artifact:defining_moves." in line
    ]
    offsets = [int(re.search(r"offset=(\d+)", line).group(1)) for line in lines]
    assert len(lines) == 6
    assert {offset // 2500 for offset in offsets} == {0, 1, 2, 3}
    assert 8100 in offsets
    assert offsets == sorted(offsets)
