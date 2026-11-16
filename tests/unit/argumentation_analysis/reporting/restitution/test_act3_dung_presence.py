"""#3587 — the Dung axis' PRESENCE for Act III's claim gate.

Before this, the gate saw the Dung axis only through a rejection: a native
framework that ran and rejected nothing counted as an absent axis, so a TRUE
sentence about the frameworks that DID run was retracted as unestablished
(« Affirmation retirée »), and the note claimed a dimension the state
contradicts.

The witness is synthetic (invented neutral text, opaque ids) — no corpus, no
network, no LLM: the writer is an injectable async stub and the state is a
``SimpleNamespace`` (the plugin reads attributes via ``getattr``).

Three cases, one per answer of the gate:

- a framework that ran and rejected nothing, and a sentence naming it: the
  sentence SURVIVES (red on ``main``, green on the branch);
- the same framework, and a sentence ATTRIBUTING A REJECTION to Dung: the
  sentence is removed (red on ``main``, green on the branch — the presence of
  the axis does not license a rejection the decoder does not report);
- no framework at all: the sentence is removed, with the note (green on both —
  the gate keeps its teeth).
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any, Dict, Optional

from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_conclusion,
)

# --- synthetic state ---------------------------------------------------------


def _state(dung_frameworks: Optional[Dict[str, Any]] = None) -> SimpleNamespace:
    """A minimal state: one argument, one quality score, no other axis.

    The quality axis is here on purpose — ``G2_one_dimension_nontrivial``
    requires at least one non-trivial axis for the verdict band to exist, and
    the gate only runs when the band exists.
    """
    return SimpleNamespace(
        identified_arguments={
            "arg_1": "Le locuteur A affirme que la mesure proposée est efficace.",
        },
        identified_fallacies={},
        argument_quality_scores={
            "arg_1": {
                "overall": 6.0,
                "scores": {"pertinence": 6.0, "clarte": 6.0},
            },
        },
        counter_arguments=[],
        dung_frameworks=dict(dung_frameworks or {}),
        fol_analysis_results=[],
        propositional_analysis_results=[],
        modal_analysis_results=[],
        narrative_synthesis="",
        governance_decisions=[],
        debate_transcripts=[],
    )


# A native framework whose extension was computed and which rejects NOTHING:
# every argument is unattacked, so the grounded labelling settles them all IN.
# « nothing was rejected » is a result (#3153), not an absence.
_FRAMEWORK_NO_REJECTION: Dict[str, Any] = {
    "fw_1": {
        "name": "verification_grounded",
        "arguments": ["arg_1"],
        "attacks": [],
        "extensions": {"all_members": ["arg_1"]},
        "semantics": "grounded",
    }
}

# A native framework DECLARED but with no computed extension: the solver never
# ran on it. Not a result — the axis stays absent.
_FRAMEWORK_NO_EXTENSION: Dict[str, Any] = {
    "fw_1": {
        "name": "verification_grounded",
        "arguments": ["arg_1"],
        "attacks": [],
    }
}


def _stub(return_value: str) -> Any:
    """An async LLM callable stub returning a fixed conclusion."""

    async def _call(_prompt: str) -> str:
        return return_value

    return _call


def _run(state: Any, conclusion: str) -> Any:
    return asyncio.run(build_act3_conclusion(state, _stub(conclusion)))


# --- synthetic narratives ----------------------------------------------------

# A sentence TRUE of the run: the framework was conducted. It names no other
# axis (a « sophisme » would bring the fallacies axis into the sentence).
_DUNG_SENTENCE = "Le cadre de l'argumentation abstraite (Dung) a été conduit."

# A sentence attributing a REJECTION to Dung. The state holds no rejection:
# the claim has nothing behind it.
_DUNG_REJECTION_SENTENCE = "La sémantique de Dung rejette l'argument central."

# An honest absence statement: it names the axis to SAY nothing was rejected.
_DUNG_ABSENCE_SENTENCE = (
    "L'argumentation abstraite (Dung) n'a rejeté aucun argument sur ce texte."
)

_NARRATIVE = (
    "### Ce que le discours dit\n\n"
    f"{_DUNG_SENTENCE} Le locuteur A avance sa thèse avec des exemples "
    "concrets.\n\n"
    "### Ce qui tient\n\n"
    "Le raisonnement causal tient et reste lisible pour qui suit le débat.\n"
)

# The same shape, with the rejection claim instead of the conducted-framework
# claim. The rest of the conclusion survives, so the removal is a partial one
# and the note is the « Affirmation retirée » one.
_NARRATIVE_REJECTION = (
    "### Ce que le discours dit\n\n"
    "Le locuteur A avance sa thèse avec des exemples concrets. "
    f"{_DUNG_REJECTION_SENTENCE}\n\n"
    "### Ce qui tient\n\n"
    "Le raisonnement causal tient et reste lisible pour qui suit le débat.\n"
)


class TestDungAxisPresence:
    """The gate reads the Dung axis' PRESENCE, not only its failures."""

    def test_framework_that_rejected_nothing_keeps_the_dung_sentence(self) -> None:
        """RED on main: the sentence was retracted as unestablished."""
        result = _run(_state(_FRAMEWORK_NO_REJECTION), _NARRATIVE)
        assert _DUNG_SENTENCE in result.narrative
        assert "Affirmation retirée" not in result.narrative
        assert "act3_claim_blocked" not in result.degraded

    def test_rejection_claim_is_removed_although_the_framework_ran(self) -> None:
        """The axis' presence does not license a rejection nobody reports."""
        result = _run(_state(_FRAMEWORK_NO_REJECTION), _NARRATIVE_REJECTION)
        assert _DUNG_REJECTION_SENTENCE not in result.narrative
        assert "Affirmation retirée" in result.narrative

    def test_the_note_never_says_the_axis_produced_nothing(self) -> None:
        """#3587 ask 4: the axis IS in the state — the note must not deny it."""
        result = _run(_state(_FRAMEWORK_NO_REJECTION), _NARRATIVE_REJECTION)
        assert "Affirmation retirée" in result.narrative
        assert "n'a pas pu établir" not in result.narrative
        assert "sans résultat dans l'état" not in result.narrative

    def test_honest_absence_statement_is_not_blocked(self) -> None:
        """Naming the axis to say it rejected nothing is what #1609 asks for."""
        result = _run(_state(_FRAMEWORK_NO_REJECTION), _DUNG_ABSENCE_SENTENCE)
        assert _DUNG_ABSENCE_SENTENCE in result.narrative
        assert "Affirmation retirée" not in result.narrative


class TestDungAxisAbsence:
    """The gate keeps its teeth: no framework, no Dung sentence."""

    def test_without_any_framework_the_dung_sentence_is_removed(self) -> None:
        result = _run(_state({}), _NARRATIVE)
        assert _DUNG_SENTENCE not in result.narrative
        assert "Affirmation retirée" in result.narrative
        assert "l'argumentation abstraite (Dung)" in result.narrative

    def test_a_framework_without_computed_extension_is_not_a_result(self) -> None:
        """The issue's « Not »: a declared framework is not a computed one."""
        result = _run(_state(_FRAMEWORK_NO_EXTENSION), _NARRATIVE)
        assert _DUNG_SENTENCE not in result.narrative
        assert "Affirmation retirée" in result.narrative

    def test_rejection_claim_is_removed_without_any_framework(self) -> None:
        result = _run(_state({}), _NARRATIVE_REJECTION)
        assert _DUNG_REJECTION_SENTENCE not in result.narrative
        assert "Affirmation retirée" in result.narrative


class TestOtherAxesUntouched:
    """The fix is scoped to Dung: the other axes keep blocking."""

    def test_a_claim_on_another_absent_axis_is_still_removed(self) -> None:
        conclusion = (
            "### Ce que le discours dit\n\n"
            "La logique propositionnelle confirme la satisfiabilité de la thèse.\n\n"
            "### Ce qui tient\n\n"
            "Le raisonnement causal tient et reste lisible pour qui suit le "
            "débat.\n"
        )
        result = _run(_state(_FRAMEWORK_NO_REJECTION), conclusion)
        assert "La logique propositionnelle confirme" not in result.narrative
        assert "Affirmation retirée" in result.narrative

    def test_the_rest_of_the_conclusion_survives(self) -> None:
        result = _run(_state(_FRAMEWORK_NO_REJECTION), _NARRATIVE)
        assert "Le locuteur A avance sa thèse" in result.narrative
        assert "Le raisonnement causal tient" in result.narrative
        assert result.status == "woven"
