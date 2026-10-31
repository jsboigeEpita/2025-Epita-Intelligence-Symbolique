# -*- coding: utf-8 -*-
"""#3308 — Act III must not read an unexamined unit as a unit without defects.

R1127a's paid pass (``doc_A``) had Act III conclude, of a divergent vote
winner, that « les unités citées ne portent pas de défaut net ». Neither
divergent winner (``arg_13``, ``arg_21``) was in the fallacy pass's coverage
record (k = 10 of N = 89); the writer saw no fallacy listed and read that as
no defect. That is #2966's family — a zero never evaluated read as an
evaluated zero (#1019) — and Act II of the same render already says it
correctly (« leur absence de faute est une absence d'examen », #2976).

Two halves are pinned here:

* the **evidence**: every unit Act III cites as a vote winner carries whether
  the fallacy pass examined it and what it found when it did, so the writer
  is never handed "no record" as if it were "no defect";
* the **check**: ``check_reading_license`` flags a "no defect" claim made on a
  cited unit the pass did not examine.

Born red: on main ``Act3Evidence`` has no examination field at all and the
licence has no such flag.
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.agents.core.synthesis.reading_license import (
    check_reading_license,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_evidence,
    build_act3_prompt,
)

_WINNER = "arg_27"
_DIVERGENT = "arg_13"
_OTHER_DIVERGENT = "arg_21"

_TEXTS = {
    _WINNER: "Une revendication appuyée par un raisonnement causal étayé.",
    _DIVERGENT: "La mesure annoncée ne suit pas les prémisses du raisonnement.",
    _OTHER_DIVERGENT: "Le contre-exemple invoqué déplace la question posée.",
}


def _state(**fields: object) -> SimpleNamespace:
    base = dict(
        identified_arguments=dict(_TEXTS),
        identified_fallacies={},
        argument_quality_scores={},
        counter_arguments=[],
        dung_frameworks={},
        fol_analysis_results=[],
        propositional_analysis_results=[],
        modal_analysis_results=[],
        narrative_synthesis="",
        governance_decisions=[
            {
                "method": "vote",
                "winner": _WINNER,
                "winners": [_WINNER, _DIVERGENT, _OTHER_DIVERGENT],
                "scores": {_WINNER: 9.0, _DIVERGENT: 1.0, _OTHER_DIVERGENT: 1.0},
                "support_by_option": {_WINNER: 9, _DIVERGENT: 1, _OTHER_DIVERGENT: 1},
                "n_methods_decided": 11,
            }
        ],
        debate_transcripts=[],
    )
    base.update(fields)
    return SimpleNamespace(**base)


def _coverage(*examined: str) -> dict:
    """The #2966 coverage record, holding the ids the pass SUBMITTED."""
    return {
        "fallacy_per_argument": {
            "k": len(examined),
            "n": len(_TEXTS),
            "unit_ids": list(examined),
        }
    }


class TestTheEvidenceCarriesTheExaminationStatus:
    def test_a_divergent_winner_outside_the_pass_is_marked_unexamined(self):
        """The R1127a shape: the divergence clause names arg_13 by what it
        says, so the examination status must travel on that same line."""
        evidence = build_act3_evidence(_state(analysis_coverage=_coverage(_WINNER)))

        label = evidence.examination_by_unit.get(_DIVERGENT, "")
        assert "examin" in label.lower(), evidence.examination_by_unit
        assert "non examin" in label.lower(), (
            "an unexamined divergent winner must be marked as unexamined, "
            "never left to read as 'no defect': " + label
        )
        assert _OTHER_DIVERGENT in evidence.examination_by_unit

        # and the line the writer reads carries it
        prompt = build_act3_prompt(evidence)
        assert label in prompt, (
            "the examination status must reach the Act III prompt, not only "
            "the evidence object"
        )

    def test_positive_control_an_examined_winner_keeps_its_findings(self):
        """Anti-pendulum: the repair must not mark an examined unit as a
        blank — a clean examined unit says so, and a defective one says what
        was found."""
        clean = build_act3_evidence(_state(analysis_coverage=_coverage(_WINNER)))
        label = clean.examination_by_unit[_WINNER]
        assert "non examin" not in label.lower(), label
        assert "aucun" in label.lower(), (
            "an examined unit with no finding must say the pass looked and "
            "found nothing: " + label
        )

        with_finding = build_act3_evidence(
            _state(
                analysis_coverage=_coverage(_WINNER),
                identified_fallacies={
                    "fl_1": {
                        "target_argument_id": _WINNER,
                        "family": "ad hominem",
                        "type": "ad hominem circonstanciel",
                    }
                },
            )
        )
        found = with_finding.examination_by_unit[_WINNER]
        assert "non examin" not in found.lower(), found
        assert "1" in found and "défaut" in found.lower(), (
            "an examined unit with a recorded fallacy must carry the count: " + found
        )

    def test_no_coverage_record_degrades_to_honest_silence(self):
        """#2966: absence of the record is not coverage. The line says the
        record is missing — it never asserts the unit was examined, and it
        never claims a defect either."""
        evidence = build_act3_evidence(_state())
        label = evidence.examination_by_unit.get(_WINNER, "")
        assert "non examin" not in label.lower(), label
        assert "enregistr" in label.lower() or "non" in label.lower(), label


class TestTheLicenceFlagsTheClaim:
    _CLAIM = (
        "Les unités citées ne portent pas de défaut net, et la mesure "
        "annoncée ne suit pas les prémisses du raisonnement."
    )

    def _flags(self, text: str, *, examined: tuple = (_WINNER,)):
        return check_reading_license(
            text, _state(analysis_coverage=_coverage(*examined))
        )["flags"]

    def test_a_no_defect_claim_on_an_unexamined_unit_is_flagged(self):
        flags = self._flags(self._CLAIM)
        kinds = [f["kind"] for f in flags]
        assert "no_defect_claim_on_unexamined_unit" in kinds, kinds

    def test_the_same_claim_on_an_examined_unit_is_not_flagged(self):
        flags = self._flags(
            self._CLAIM, examined=(_WINNER, _DIVERGENT, _OTHER_DIVERGENT)
        )
        kinds = [f["kind"] for f in flags]
        assert "no_defect_claim_on_unexamined_unit" not in kinds, kinds

    def test_without_a_coverage_record_the_licence_stays_silent(self):
        """Absence of a record is not evidence of non-examination — the
        licence degrades to honest silence, like every #2966 reader."""
        flags = check_reading_license(self._CLAIM, _state())["flags"]
        kinds = [f["kind"] for f in flags]
        assert "no_defect_claim_on_unexamined_unit" not in kinds, kinds
