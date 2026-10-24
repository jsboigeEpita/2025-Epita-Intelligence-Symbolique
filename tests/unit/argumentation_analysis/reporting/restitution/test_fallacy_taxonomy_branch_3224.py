# -*- coding: utf-8 -*-
"""#3224 — the three evidence sites print the taxonomy branch, one helper.

``act3_conclusion_plugin`` (:901) built ``f"{ftype} (famille {family})"`` and so
did ``act2_narrative_plugin`` at :1705 (the movement line) and :1790 (the
reported-move line). All three now ask ``fallacy_taxonomy_label``, so a
detection recorded at 4.1.3 reads « Effet cigogne (Erreur de raisonnement >
Causalité douteuse) » and the writer can answer the category the question
named. A detection with no recorded address keeps the old two-level label
(no guess), and a REPORTED move's label carries the branch too — attribution
decides where the line goes, not what the category is called.

Synthetic values only (invented French filler, opaque ids); deterministic — no
JVM, no LLM, no network.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict, List

from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_evidence,
    build_act2_prompt,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_evidence,
    build_act3_prompt,
)

_DESC_A = "Première unité : une revendication causale explicite, développée."


def _fallacy(**over: Any) -> Dict[str, Any]:
    base = {
        "type": "Effet cigogne",
        "family": "Erreur de raisonnement",
        "taxonomy_path": "4.1.3",
        "justification": "une corrélation lue comme un lien de cause à effet.",
        "target_argument_id": "arg_1",
    }
    base.update(over)
    return base


# --- Acte III ------------------------------------------------------------


def _act3_prompt(fallacy: Dict[str, Any]) -> str:
    state = SimpleNamespace(
        identified_arguments={"arg_1": _DESC_A},
        identified_fallacies={"fallacy_1": fallacy},
    )
    return build_act3_prompt(build_act3_evidence(state))


class TestAct3NamesTheBranch:
    def test_the_rebuilt_prompt_line_names_the_branch(self):
        """The issue's case 1, on a synthetic state: the line the writer reads
        carries « Causalité douteuse », the branch the question asked about."""
        prompt = _act3_prompt(_fallacy())
        assert "Effet cigogne" in prompt
        assert "Causalité douteuse" in prompt
        assert "arg_1" in prompt

    def test_a_detection_without_a_path_keeps_the_two_level_label(self):
        prompt = _act3_prompt(_fallacy(taxonomy_path=None))
        assert "Effet cigogne (famille Erreur de raisonnement)" in prompt
        assert "Causalité douteuse" not in prompt


# --- Acte II -------------------------------------------------------------


def _act2_state(fallacies: Dict[str, Dict[str, Any]]) -> SimpleNamespace:
    return SimpleNamespace(
        analysis_trace=[
            {
                "phase": "extract",
                "agent": "FactExtractionAgent",
                "reacts_to": ["arg_1"],
                "summary": "assert arg_1",
                "timestamp": "2026-10-24T00:00:00Z",
                "move": "assert",
                "anchor": {"offset": 40, "length": 5},
            }
        ],
        identified_arguments={"arg_1": _DESC_A},
        identified_fallacies=fallacies,
        argument_quality_scores={},
        counter_arguments=[],
        dung_frameworks={},
        fol_analysis_results=[],
        propositional_analysis_results=[],
        modal_analysis_results=[],
        governance_decisions=[],
        debate_transcripts=[],
        raw_text="x" * 400,
    )


def _act2_prompt(fallacies: Dict[str, Dict[str, Any]]) -> str:
    return build_act2_prompt(build_act2_evidence(_act2_state(fallacies)))


def _lines(prompt: str, marker: str) -> List[str]:
    return [ln for ln in prompt.splitlines() if marker in ln]


class TestAct2NamesTheBranch:
    def test_the_movement_line_names_the_branch(self):
        prompt = _act2_prompt({"fallacy_1": _fallacy()})
        procede = _lines(prompt, "Procédé :")
        assert procede, "no Procédé line"
        assert any("Causalité douteuse" in ln for ln in procede)

    def test_the_reported_line_names_the_branch_too(self):
        """#3180 — attribution decides WHICH line the detection rides, not
        what its category is called."""
        prompt = _act2_prompt(
            {
                "fallacy_1": _fallacy(
                    move_author="reported", move_author_label="un tiers"
                )
            }
        )
        reported = _lines(prompt, "un tiers")
        assert reported, "no reported line"
        assert any("Causalité douteuse" in ln for ln in reported)

    def test_a_detection_without_a_path_keeps_the_two_level_label(self):
        prompt = _act2_prompt({"fallacy_1": _fallacy(taxonomy_path=None)})
        procede = _lines(prompt, "Procédé :")
        assert procede, "no Procédé line"
        assert any(
            "« Effet cigogne » (famille Erreur de raisonnement)" in ln for ln in procede
        )
        assert "Causalité douteuse" not in prompt
