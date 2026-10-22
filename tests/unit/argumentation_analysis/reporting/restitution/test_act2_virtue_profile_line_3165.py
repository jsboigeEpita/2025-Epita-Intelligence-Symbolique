# -*- coding: utf-8 -*-
"""#3165 — Act II « Profil de vertus (caractère) » listed the EVALUABLE
dimensions, not the held ones.

Since #1907 ``ArgEvidence.virtues`` holds the dimensions the instrument
could judge on the unit, whatever their score; the line's label still said
what the unit IS. Measured on the R1107c rebuilt prompt: identical on 7 of 8
scored units — it discriminates nothing, and it stays one misreading away
from « this unit has the full virtue profile » for a unit that fails 6 of 8
(#1019 family: the field changed meaning, the label did not).

The line is deleted. The very next line already carries the evaluated set
TOGETHER with what holds and what fails — that line is the control: it must
be unchanged.

Census (#3165 DoD): one production site (``act2_narrative_plugin.py``), one
unrelated doc mention of the honest-absence message (« Profil de vertus
indisponible… », a different code path), no test reader — nothing to re-pin.
"""

from types import SimpleNamespace

from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_evidence,
    build_act2_prompt,
)


def _state():
    # 8 evaluable dimensions, 2 hold (>= 0.75), 6 fail (<= 0.25).
    return SimpleNamespace(
        propositional_analysis_results=None,
        fol_analysis_results=None,
        modal_analysis_results=None,
        identified_arguments={
            "arg_1": {"id": "arg_1", "description": "Une description quelconque."}
        },
        identified_fallacies=None,
        argument_quality_scores={
            "arg_1": {
                "scores": {
                    "clarte": 1.0,
                    "pertinence": 0.9,
                    "presence_sources": 0.1,
                    "refutation_constructive": 0.2,
                    "structure_logique": 0.1,
                    "analogie_pertinente": 0.0,
                    "fiabilite_sources": 0.2,
                    "exhaustivite": 0.1,
                }
            }
        },
    )


def _prompt():
    return build_act2_prompt(build_act2_evidence(_state()))


class TestVirtueProfileLineDeleted:
    def test_the_prompt_puts_no_failing_dimension_under_a_virtue_profile_label(self):
        """Born red on main: the « Profil de vertus (caractère) » line listed
        all 8 evaluable dimensions — the 6 that fail included — under a
        label that reads as what the unit is."""
        assert "Profil de vertus" not in _prompt()

    def test_the_jugeables_line_is_unchanged(self):
        """Control: the honest line keeps the evaluated set WITH what holds
        and what fails — green before and after the deletion."""
        prompt = _prompt()
        assert "8 dimensions sur 9 étaient jugeables" in prompt
        assert "tiennent : clarte, pertinence" in prompt
        assert "ne tiennent pas" in prompt
