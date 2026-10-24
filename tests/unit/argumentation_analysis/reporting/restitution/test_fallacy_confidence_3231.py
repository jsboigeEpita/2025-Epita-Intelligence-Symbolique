# -*- coding: utf-8 -*-
"""#3231 — a detection's standing reaches the acts, as its detector stated it.

The R1110b render presented ``fallacy_13`` — confidence 0.4, its own detector
calling the match tentative — as an established fault: ``FallacyEvidence``
carried no confidence, no act read one, and the 200-character head cut of the
justification dropped the hedge that lives at the END of the producer's
reasoning. Meanwhile the same report's synthesis printed the confidence
(#3029): two surfaces, two standings for one detection.

The acts now carry the detector's confidence (#3029's contract: unmeasured is
None, printed as « non mesurée », never a default value), print it on the
fallacy lines, and the consigne weighs it — a detection its producer rates
low, or calls tentative, is told as a tentative reading, never as an
established fault. No numeric threshold: the standing follows the two channels
the detector itself wrote (printed confidence, written hedge).

Synthetic values only (invented French/English filler, opaque ids);
deterministic — no JVM, no LLM, no network.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict, List

from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_evidence,
    build_act2_prompt,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    StructuringWeakPoint,
    build_act3_evidence,
    build_act3_prompt,
)

_DESC_A = "Première unité : une revendication causale explicite, développée."

# The issue's witness shape (fallacy_13): the hedge lies ONLY past the 200-cap.
_HEDGE = "The analogy itself is not shown in the excerpt, so this match is tentative."
_LONG_SETUP = (
    "The unit draws a parallel between two situations that differ in scale. "
    "The reasoning leans on the similarity of one feature. "
    "The comparison carries the weight of the whole claim. "
) * 3


def _fallacy(**over: Any) -> Dict[str, Any]:
    base = {
        "type": "Effet cigogne",
        "family": "Erreur de raisonnement",
        "taxonomy_path": "4.1.3",
        "justification": _LONG_SETUP + _HEDGE,
        "target_argument_id": "arg_1",
        "confidence": 0.4,
    }
    base.update(over)
    return base


# --- Acte III ------------------------------------------------------------


def _act3(state: SimpleNamespace) -> str:
    return build_act3_prompt(build_act3_evidence(state))


def _act3_state(fallacies: Dict[str, Dict[str, Any]]) -> SimpleNamespace:
    return SimpleNamespace(
        identified_arguments={"arg_1": _DESC_A},
        identified_fallacies=fallacies,
    )


def _lines(prompt: str, marker: str) -> List[str]:
    return [ln for ln in prompt.splitlines() if marker in ln]


class TestAct3CarriesTheStanding:
    def test_the_weak_point_line_prints_the_confidence(self):
        """The issue's witness, on a synthetic state of the same shape: a 0.4
        detection whose hedge lies past the cap."""
        prompt = _act3(_act3_state({"fallacy_1": _fallacy()}))
        wp = _lines(prompt, "[fallacy]")
        assert wp, "no fallacy weak point"
        assert any("confiance du détecteur : 0,4" in ln for ln in wp)

    def test_the_hedge_survives_the_cap(self):
        prompt = _act3(_act3_state({"fallacy_1": _fallacy()}))
        assert _HEDGE in prompt
        assert "[…]" in prompt

    def test_an_unmeasured_confidence_prints_as_unmeasured(self):
        fallacy = _fallacy()
        del fallacy["confidence"]
        prompt = _act3(_act3_state({"fallacy_1": fallacy}))
        wp = _lines(prompt, "[fallacy]")
        assert any("confiance du détecteur : non mesurée" in ln for ln in wp)

    def test_a_formal_weak_point_prints_no_detector_confidence(self):
        """A Dung/PL/FOL verdict is a computation, not a measurement: the note
        is a fallacy line's, never a formal line's."""
        evidence = build_act3_evidence(_act3_state({"fallacy_1": _fallacy()}))
        evidence.weak_points.append(
            StructuringWeakPoint(
                source="dung",
                label="argument rejeté par le cadre de Dung (sémantique stable)",
                target_arg_id="arg_9",
                detail="[dung-stable] — la preuve repliée",
            )
        )
        prompt = build_act3_prompt(evidence)
        dung_lines = _lines(prompt, "[dung]")
        assert dung_lines, "no dung weak point"
        assert all("confiance du détecteur" not in ln for ln in dung_lines)

    def test_the_consigne_weighs_the_standing(self):
        prompt = _act3(_act3_state({"fallacy_1": _fallacy()}))
        assert "lecture provisoire" in prompt
        assert "jamais comme une faute établie" in prompt


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


def _act2(fallacies: Dict[str, Dict[str, Any]]) -> str:
    return build_act2_prompt(build_act2_evidence(_act2_state(fallacies)))


class TestAct2CarriesTheStanding:
    def test_the_procedure_line_prints_the_confidence_next_to_the_verdict(self):
        prompt = _act2({"fallacy_1": _fallacy()})
        procede = _lines(prompt, "Procédé :")
        assert procede, "no Procédé line"
        assert any(
            "« Effet cigogne » (Erreur de raisonnement > Causalité douteuse) "
            "— confiance du détecteur : 0,4. Justification :" in ln
            for ln in procede
        )

    def test_the_hedge_survives_the_cap(self):
        prompt = _act2({"fallacy_1": _fallacy()})
        assert _HEDGE in prompt
        assert "[…]" in prompt

    def test_an_unmeasured_confidence_prints_as_unmeasured_never_a_number(self):
        fallacy = _fallacy()
        del fallacy["confidence"]
        prompt = _act2({"fallacy_1": fallacy})
        procede = _lines(prompt, "Procédé :")
        assert any("confiance du détecteur : non mesurée" in ln for ln in procede)

    def test_the_consigne_weighs_without_inventing_a_threshold(self):
        """The fault rule survives (an established fault keeps its verdict);
        the standing rule reads the detector's own two channels — printed
        confidence and written hedge — and names no number."""
        prompt = _act2({"fallacy_1": _fallacy()})
        assert "GARDE son verdict de sophisme" in prompt
        assert "lecture PROVISOIRE" in prompt
        assert "confiance du détecteur" in prompt

    def test_a_reported_move_carries_no_standing_note(self):
        """#3180 — the reported block is a third party's move, not a speaker
        fault: no verdict standing to weigh, so no note on its line."""
        prompt = _act2(
            {
                "fallacy_1": _fallacy(
                    move_author="reported", move_author_label="un tiers"
                )
            }
        )
        assert _lines(prompt, "un tiers"), "no reported line"
        assert "confiance du détecteur : 0,4" not in prompt


class TestEverySpeakerDetectionReachesBothActs:
    """The census shape (DoD 2): before, 0 of the speaker detections'
    confidences reached an act prompt; after, every one does — the
    coordinator replays the count on the stored R1110b state (23/23)."""

    def test_each_detections_confidence_reaches_act2_and_act3(self):
        fallacies = {
            "f1": _fallacy(confidence=0.4, target_argument_id="arg_1"),
            "f2": _fallacy(
                confidence=0.9, target_argument_id="arg_1", type="Faux dilemme"
            ),
            "f3": _fallacy(
                confidence=0.35, target_argument_id="arg_1", type="Pente glissante"
            ),
        }
        for prompt in (_act2(fallacies), _act3(_act3_state(fallacies))):
            for note in (
                "confiance du détecteur : 0,4",
                "confiance du détecteur : 0,9",
                "confiance du détecteur : 0,35",
            ):
                assert note in prompt, note
