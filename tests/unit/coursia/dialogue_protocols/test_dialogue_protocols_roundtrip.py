"""Guard for the surviving surface of the dialogue-protocols CoursIA notebook
(#1961 Phase 5, trimmed #2137).

The three protocol classes (DialogueProtocol / InquiryProtocol / PersuasionProtocol)
were withdrawn (#2137): dead twins of the living JVM ``logic/dialogue_handler.py``.
The transition/termination replay tests and the CLAIM→CONCEDE asymmetry check
went with them — the committed notebook keeps its executed outputs as a
historical teaching artifact but can no longer be re-run against this code.
This guard now pins what survives: the 6 dialogue types, the 9 speech acts,
the scheme junction with the argumentation-schemes classifier, and that the
committed notebook ships with executed outputs.
"""

from __future__ import annotations

import json
from pathlib import Path

from argumentation_analysis.agents.core.debate.argumentation_schemes import (
    classify_scheme,
)
from argumentation_analysis.agents.core.debate.protocols import (
    DialogueType,
    FormalArgument,
    Proposition,
    SpeechAct,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
NOTEBOOK_PATH = REPO_ROOT / "docs" / "coursia_contrib" / "dialogue_protocols.ipynb"


def test_six_dialogue_types_and_nine_speech_acts() -> None:
    assert len(DialogueType) == 6
    assert len(SpeechAct) == 9


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
