"""Round-trip guard for the dialogue-protocols CoursIA notebook (#1961 Phase 5).

Every transition and termination verdict the notebook displays comes from
``docs/coursia_contrib/dialogue_protocols_examples.json`` — the single source of
truth shared by the notebook and this guard. This test replays each example
against the real protocols (``is_valid_move`` / ``is_terminal_state``): allowed
transitions must pass, forbidden ones must fail, terminal histories must
terminate, healthy ones must not. It also pins the structural claims the
notebook teaches — 6 dialogue types, 9 speech acts, the CLAIM→CONCEDE
asymmetry between inquiry and persuasion, the scheme junction with the
argumentation-schemes classifier — and that the committed notebook ships
with executed outputs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from argumentation_analysis.agents.core.debate.argumentation_schemes import (
    classify_scheme,
)
from argumentation_analysis.agents.core.debate.protocols import (
    DialogueMove,
    DialogueProtocol,
    DialogueType,
    FormalArgument,
    InquiryProtocol,
    PersuasionProtocol,
    Proposition,
    SpeechAct,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
EXAMPLES_PATH = (
    REPO_ROOT / "docs" / "coursia_contrib" / "dialogue_protocols_examples.json"
)
NOTEBOOK_PATH = REPO_ROOT / "docs" / "coursia_contrib" / "dialogue_protocols.ipynb"

# The protocol constructors carry no return annotations in the source module
# (the CI strict scope covers core orchestration only), hence the targeted ignores.
PROTOCOLS: dict[str, DialogueProtocol] = {
    "inquiry": InquiryProtocol(),  # type: ignore[no-untyped-call]
    "persuasion": PersuasionProtocol(),  # type: ignore[no-untyped-call]
}


def _load_examples() -> dict[str, Any]:
    with open(EXAMPLES_PATH, encoding="utf-8") as fh:
        data: dict[str, Any] = json.load(fh)
    return data


def _history(acts: list[str]) -> list[DialogueMove]:
    return [
        DialogueMove(speaker=f"loc{i % 2}", act=SpeechAct[a], content="—")
        for i, a in enumerate(acts)
    ]


def test_examples_file_is_well_formed() -> None:
    data = _load_examples()
    transitions = data["transitions"]
    terminations = data["terminations"]
    assert len(transitions) == 9
    assert len(terminations) == 7
    for ex in transitions:
        assert ex["dialogue"] in PROTOCOLS
        SpeechAct[ex["from"]]
        SpeechAct[ex["to"]]
        assert isinstance(ex["allowed"], bool)
    for ex in terminations:
        assert ex["dialogue"] in PROTOCOLS
        for act in ex["acts"]:
            SpeechAct[act]


@pytest.mark.parametrize(
    "dialogue,from_act,to_act,allowed",
    [
        (ex["dialogue"], ex["from"], ex["to"], ex["allowed"])
        for ex in _load_examples()["transitions"]
    ],
)
def test_transition_round_trips(
    dialogue: str, from_act: str, to_act: str, allowed: bool
) -> None:
    got = PROTOCOLS[dialogue].is_valid_move(SpeechAct[from_act], SpeechAct[to_act])
    assert got == allowed


@pytest.mark.parametrize(
    "dialogue,acts,terminal",
    [
        (ex["dialogue"], ex["acts"], ex["terminal"])
        for ex in _load_examples()["terminations"]
    ],
)
def test_termination_round_trips(
    dialogue: str, acts: list[str], terminal: bool
) -> None:
    got = PROTOCOLS[dialogue].is_terminal_state(_history(acts))
    assert got == terminal


def test_six_dialogue_types_and_nine_speech_acts() -> None:
    assert len(DialogueType) == 6
    assert len(SpeechAct) == 9


def test_concede_asymmetry_between_inquiry_and_persuasion() -> None:
    assert not PROTOCOLS["inquiry"].is_valid_move(SpeechAct.CLAIM, SpeechAct.CONCEDE)
    assert PROTOCOLS["persuasion"].is_valid_move(SpeechAct.CLAIM, SpeechAct.CONCEDE)


def test_protocols_expose_non_empty_response_tables() -> None:
    for proto in PROTOCOLS.values():
        assert proto.get_allowed_responses(SpeechAct.CLAIM)
        assert proto.allowed_transitions
        assert proto.termination_conditions


def test_scheme_junction_populates_formal_argument() -> None:
    text = "Selon un chercheur spécialiste du domaine, la méthode est fiable."
    scheme = classify_scheme(text)
    assert scheme is not None
    argument = FormalArgument(
        premises=[
            Proposition(
                content="Le chercheur est spécialiste du domaine", confidence=0.9
            )
        ],
        conclusion=Proposition(content="La méthode est fiable", confidence=0.8),
        scheme=scheme.key,
    )
    assert argument.scheme == "expert_opinion"


def test_committed_notebook_carries_executed_outputs() -> None:
    with open(NOTEBOOK_PATH, encoding="utf-8") as fh:
        nb = json.load(fh)
    code_cells = [c for c in nb["cells"] if c["cell_type"] == "code"]
    assert code_cells, "notebook has code cells"
    for cell in code_cells:
        assert cell.get("outputs"), "every code cell ships an executed output"
        assert cell.get("execution_count") is not None
