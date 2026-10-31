# -*- coding: utf-8 -*-
"""#3317 — the per-act Greek letters must not reach the reader's prose.

#3305 replaced the bare ``arg_N`` handed to the *writer* by a per-act letter
table whose legend decodes it. The legend lives in the PROMPT only; the
render carries none. So a letter printed into an act is an unresolvable
designation for the reader — the #3296 defect the repair was meant to remove,
with a letter in place of the id. Measured on the first paid pass after
#3305 (R1129a, ``doc_A``): 18 letter tokens in Act II, 0 before the change
(R1127a/b/c).

Two halves are pinned here:

* the **source** (``unit_labels``): the legend stops ORDERING the letter for
  a textless unit, and the intro states the designation rule — in prose a
  unit is designated by what it says, a textless one by its role or by the
  named absence. The table itself stays (anti-pendulum: it is what gives the
  writer one shared handle per unit across the act's blocks);
* the **check** (``readability_gate``): a #2980-shaped rule counts standalone
  Greek-letter tokens in the acts and the assembled body (WARN 1–2, FAIL ≥3,
  a reason with an example, never a silent rewrite), and never fires on a
  letter inside a « … » quotation.

Born red: on main the legend says « désigne-le par sa lettre » and the gate
carries no such rule (its comment says the letters "are the DESIGNED label
and never match").
"""

from __future__ import annotations

import re

from argumentation_analysis.reporting.restitution.acts import RestitutionActs
from argumentation_analysis.reporting.restitution.readability_gate import (
    ReadabilityGate,
)
from argumentation_analysis.reporting.restitution.unit_labels import (
    LEGEND_HEADING,
    label_writer_prompt,
)

#: Two units in the prompt; only ``arg_1`` has text in the state, so the
#: legend's missing-referent line is exercised too. ``arg_1`` appears twice —
#: the same unit in two blocks must keep ONE letter.
_PROMPT = (
    "Bloc A — l'argument arg_1 soutient la thèse.\n"
    "\n"
    "Bloc B — l'argument arg_2 la nuance, et arg_1 revient plus loin.\n"
    "\n"
    "CONSIGNE DE RÉDACTION : écris l'acte II.\n"
)


def _labelled() -> str:
    return label_writer_prompt(_PROMPT, {"arg_1": "these mesurée"})


def _legend(prompt: str) -> str:
    assert LEGEND_HEADING in prompt, "the per-act legend is missing"
    return prompt[prompt.index(LEGEND_HEADING) :]


class TestTheLegendStopsOrderingTheLetter:
    """Source half — the legend is a decoding table for the writer, not an
    instruction to reproduce its letters in the prose."""

    def test_the_missing_referent_line_no_longer_orders_the_letter(self):
        legend = _legend(_labelled())
        assert "par sa lettre" not in legend, (
            "the legend still orders a textless unit to be designated by its "
            "letter — the writer copies it into the rendered prose: " + legend
        )
        # The named absence itself survives (the #2969 controls read it).
        assert "texte non joint" in legend, legend

    def test_the_intro_states_the_designation_rule(self):
        intro = _legend(_labelled()).splitlines()[0]
        assert "poignée" in intro, (
            "the intro must say what the letters ARE (reading handles), not "
            "just hand them over: " + intro
        )
        assert "ce qu'elle dit" in intro, (
            "the intro must say how a unit is designated in prose (by what it "
            "says): " + intro
        )
        assert "rôle" in intro and "absence" in intro, (
            "the intro must say how a TEXTLESS unit is designated (its role or "
            "the named absence, never its letter): " + intro
        )

    def test_positive_control_the_table_and_the_legend_are_still_built(self):
        """Anti-pendulum: removing the directive must not remove the table."""
        labelled = _labelled()
        assert "arg_1" not in labelled and "arg_2" not in labelled
        legend = _legend(labelled)
        assert "these mesurée" in legend, "the legend lost its referent"
        assert legend.count("•") == 2, legend
        letters = re.findall(r"[α-ω]+", legend)
        assert len(set(letters)) == 2, letters
        body = labelled[: labelled.index(LEGEND_HEADING)]
        assert body.count(letters[0]) == 2, (
            "the same unit cited in two blocks must keep ONE letter: " + body
        )


class TestTheGateReadsPrintedLetters:
    """Check half — a letter printed into the render is an unresolvable
    designation (#2980's shape: WARN 1–2, FAIL ≥3, with an example)."""

    def _acts(self, act2: str) -> RestitutionActs:
        return RestitutionActs(
            act1_framing="Acte I — mise en situation du propos.\n",
            act2_narrative=act2,
            act3_conclusion="Acte III — conclusion actionnable.\n",
            source_id="doc_A",
        )

    def test_three_printed_letters_fail_the_act(self):
        verdict = ReadabilityGate().check_acts(
            self._acts(
                "L'argument α cherche à convaincre. En β, la thèse se "
                "prolonge. Le mouvement (κκ) revient ensuite.\n"
            )
        )
        assert not verdict.passed, verdict.reasons
        assert any("lettre" in r.lower() for r in verdict.reasons), verdict.reasons
        assert any("κκ" in r or "α" in r for r in verdict.reasons), verdict.reasons

    def test_one_printed_letter_warns_but_does_not_fail(self):
        verdict = ReadabilityGate().check_acts(
            self._acts("L'argument α cherche à convaincre.\n")
        )
        assert verdict.band == "WARN", verdict.reasons

    def test_units_designated_by_content_pass(self):
        verdict = ReadabilityGate().check_acts(
            self._acts(
                "L'argument selon lequel la mesure tient cherche à convaincre. "
                "Ensuite, la thèse se prolonge sur le même mouvement.\n"
            )
        )
        assert verdict.band == "PASS", verdict.reasons

    def test_a_letter_inside_a_quotation_does_not_fire(self):
        verdict = ReadabilityGate().check_acts(
            self._acts(
                "Le locuteur écrit « l'argument α tient » puis cite « (κκ) » "
                "comme on citerait une formule.\n"
            )
        )
        assert verdict.band == "PASS", verdict.reasons

    def test_the_assembled_body_check_reads_them_too(self):
        verdict = ReadabilityGate().check_body(
            "L'argument α cherche à convaincre. En β, la thèse se prolonge. "
            "Le mouvement (κκ) revient ensuite.\n"
        )
        assert verdict.band == "FAIL", verdict.reasons
        assert any("lettre" in r.lower() for r in verdict.reasons), verdict.reasons
