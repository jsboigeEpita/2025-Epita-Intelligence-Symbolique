"""#1620 — the appendix's "synthèse narrative" signal must not favour one voie.

The two orchestration voies file the *same* semantic object under two different
state keys:

* **pipeline** — ``state_writers`` (l.1266 / l.1305) write the narrative
  synthesis into ``state.narrative_synthesis``.
* **conversational** — the PM prompt (``pm/prompts.py`` l.95) instructs the
  agent to call ``StateManager.set_final_conclusion(conclusion="[Copie de votre
  synthèse ici]")``, which lands in ``state.final_conclusion``
  (``shared_state.py`` l.224).

``_provenance_counts`` read only the first key, so a conversational run that
*did* synthesise was reported ``synthese_narrative = "absente"``. That is the
one-lane-writer bias: the quieter report reads as the healthier one, which
skews any pipeline-vs-conversational comparison in favour of the louder voie.

Falsifiability — ``test_both_voies_agree_when_each_wrote_its_own_key`` asserts
the two voies produce the **same** value from the same content. On the pre-fix
code the conversational side yields "absente" while the pipeline side yields
"présente", so the equality fails. Degenerate substitution: delete the
``or _g("final_conclusion")`` term → the conversational case reverts to
"absente" → the test fails.

Scope: this is a *reader-side* resolver. The two state fields keep their own
histories and are deliberately NOT merged (a state migration would be a far
larger gesture for the same observable fix).
"""

from __future__ import annotations

from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    Act3Evidence,
)
from argumentation_analysis.reporting.restitution.appendix import _provenance_counts

# The synthesis text is identical on both voies — the voie is the only variable.
_SYNTHESIS = "Le discours articule trois mouvements argumentatifs distincts."


def _state(**overrides):
    """Minimal state; only the synthesis-carrying keys vary between cases."""
    base = {
        "identified_arguments": {"arg_1": "thèse A"},
        "identified_fallacies": {},
        "counter_arguments": [],
        "argument_quality_scores": {},
        "narrative_synthesis": "",
        "final_conclusion": None,
    }
    base.update(overrides)
    return base


class TestSynthesisPresenceAgreesAcrossVoies:
    """Same content in ⇒ same signal out, whichever voie wrote it."""

    def test_both_voies_agree_when_each_wrote_its_own_key(self) -> None:
        """The load-bearing assertion: agreement, not a particular wording.

        Pre-fix, the conversational state yields "absente" and the pipeline one
        "présente" — the inequality *is* the defect.
        """
        pipeline = _provenance_counts(_state(narrative_synthesis=_SYNTHESIS))
        conversational = _provenance_counts(_state(final_conclusion=_SYNTHESIS))

        assert (
            pipeline["synthese_narrative"] == conversational["synthese_narrative"]
        ), "the two voies must report the same synthesis presence for the same content"
        assert pipeline["synthese_narrative"] == "présente"

    def test_conversational_synthesis_is_not_reported_absent(self) -> None:
        """The concrete regression: a conversational synthesis exists and counts."""
        counts = _provenance_counts(_state(final_conclusion=_SYNTHESIS))
        assert counts["synthese_narrative"] == "présente"

    def test_neither_voie_wrote_anything_stays_absent(self) -> None:
        """Anti-pendule: the resolver must not fabricate presence from nothing."""
        counts = _provenance_counts(_state())
        assert counts["synthese_narrative"] == "absente"

    def test_empty_conversational_conclusion_stays_absent(self) -> None:
        """An empty/whitespace conclusion is not a synthesis (falsy, like the twin)."""
        assert (
            _provenance_counts(_state(final_conclusion=""))["synthese_narrative"]
            == "absente"
        )


class TestAct3DroppedTheUnreadFlag:
    """#1620 defect 1 — the flag is gone by subtraction, not relocated.

    ``Act3Evidence.narrative_synthesis_available`` was computed from
    ``state.narrative_synthesis`` and passed into the bundle, and no code ever
    read it (3 sites, all declaration/computation/construction). Measured on
    three real artifacts, the Acte III prose asserts nothing about a narrative
    synthesis even where the state carries a 5053-char one — so the flag
    guarded no claim.

    This test pins the *rule*, not the instance: a boolean on the evidence
    bundle exists to gate prose, so re-adding this one silently would restore
    the defect. Re-adding it **with a reader** is a different change and would
    come with its own test.
    """

    def test_flag_is_absent_from_the_evidence_bundle(self) -> None:
        assert not hasattr(Act3Evidence(), "narrative_synthesis_available")

    def test_evidence_builder_does_not_reintroduce_it(self) -> None:
        """Constructing the bundle must not accept the removed keyword."""
        import pytest

        with pytest.raises(TypeError):
            Act3Evidence(narrative_synthesis_available=True)
