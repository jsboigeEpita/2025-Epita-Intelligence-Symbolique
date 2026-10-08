"""#2965 (R1077 corrected slice) — the verdict is framed on its ORIGIN.

The narrative used to frame the governance verdict on ``extraction_method``
(Track E #1281): ``== "llm"`` was read as "the verdict is a model
assessment". The R1077 paid pass on ``doc_A`` falsified the premise — the
record was ``llm`` + ``vote_aggregate``, i.e. an LLM assessment **ran** but a
**vote** decided. Act II then told the reader a vote was a model ranking.

The origin is ``winner_provenance`` (#2969). One vocabulary per origin, on
both Acts:

* ``vote_aggregate`` → the vote wording, no model warning (a
  model-recommended *method* is named, not the verdict);
* ``llm_resolution`` → the model-assessment warning + its wording;
* ``conflict_resolution`` → the conflict-resolution wording;
* unrecorded → the origin is stated unknown; the renderer does NOT guess it
  (anti-#1019: absence is not a vote, and a vote is not an absence).

Born red on ``ecfd3a092``: the real shape (``llm`` + ``vote_aggregate``)
carries the false model warning in Act II, and an ``llm_resolution`` record
reads as a vote in Act III.

Privacy: invented filler, opaque ids, no corpus sentence. Deterministic: no
JVM, no LLM.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_evidence,
    build_act2_prompt,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_evidence,
    build_act3_prompt,
)

_VOTE = "vote social-choice"
_MODEL = "évaluation d'un modèle"
_WARNING = "ÉVALUATION D'UN MODÈLE"


def _state(**fields: object) -> SimpleNamespace:
    base = dict(
        identified_arguments={},
        identified_fallacies={},
        argument_quality_scores={},
        counter_arguments=[],
        dung_frameworks={},
        fol_analysis_results=[],
        propositional_analysis_results=[],
        narrative_synthesis="",
        governance_decisions=[],
        debate_transcripts=[],
    )
    base.update(fields)
    return SimpleNamespace(**base)


def _gov_state(decision: dict, winner_key: str = "arg_1") -> SimpleNamespace:
    """One extracted unit (the winner) + one governance decision."""
    return _state(
        identified_arguments={
            winner_key: "La thèse retenue affirme une clause opératoire.",
        },
        governance_decisions=[{"method": "copeland", "winner": winner_key, **decision}],
    )


_PROMPTS = {
    "act2": lambda st: build_act2_prompt(build_act2_evidence(st)),
    "act3": lambda st: build_act3_prompt(build_act3_evidence(st)),
}


def _deliberation(prompt: str) -> str:
    """The whole deliberation region (governance warning + line)."""
    start = prompt.find("DÉLIBÉRATION COLLECTIVE")
    assert start != -1, "the prompt carries no deliberation block"
    return prompt[start:]


@pytest.mark.parametrize("act", ["act2", "act3"])
class TestTheVoteOriginIsNotAModelAssessment:
    def test_the_real_shape_is_a_vote_not_a_model_ranking(self, act: str) -> None:
        """The R1077 measured shape: ``extraction_method == "llm"`` AND
        ``winner_provenance == "vote_aggregate"``. On ``ecfd3a092`` the
        prompt warned that the verdict was a model ranking — false; the
        winner came from the vote. Born red on Act II and Act III."""
        st = _gov_state(
            {
                "extraction_method": "llm",
                "winner_provenance": "vote_aggregate",
                "method_provenance": "llm_recommendation",
            }
        )
        text = _deliberation(_PROMPTS[act](st))
        assert _VOTE in text.lower()  # the vote is the origin
        assert _WARNING not in text  # no model-assessment warning
        # the model is named as the METHOD's recommender, not the verdict's
        assert "méthode de vote recommandée par le modèle" in text

    def test_a_model_resolution_is_warned_as_such(self, act: str) -> None:
        """``llm_resolution`` → the model-assessment warning and wording.
        Act III had no warning at all: born red there."""
        st = _gov_state(
            {"extraction_method": "llm", "winner_provenance": "llm_resolution"}
        )
        text = _deliberation(_PROMPTS[act](st))
        assert _MODEL in text.lower()
        assert _WARNING in text
        assert _VOTE not in text.lower()


@pytest.mark.parametrize("act", ["act2", "act3"])
class TestAnUnrecordedOriginIsNotGuessed:
    def test_no_provenance_says_unknown_never_a_vote(self, act: str) -> None:
        """A pre-#2969 record has no ``winner_provenance``: the origin is
        unrecorded — neither a vote nor a model ranking is asserted.
        (Anti-pendulum: the vote claim is *removed*, not swapped.)"""
        st = _gov_state({"extraction_method": "llm"})  # llm alone decides nothing
        text = _deliberation(_PROMPTS[act](st))
        assert "origine non enregistrée" in text
        assert _VOTE not in text.lower()
        assert _WARNING not in text

    def test_the_text_of_the_winner_still_travels_when_the_origin_is_unknown(
        self, act: str
    ) -> None:
        """Bounding the origin must not drop the #2989 referent: the winner's
        text is still on the line (positive control against a fix that
        removes the claim by removing the line)."""
        st = _gov_state({"extraction_method": "heuristic"})
        text = _deliberation(_PROMPTS[act](st))
        assert "clause opératoire" in text


@pytest.mark.parametrize("act", ["act2", "act3"])
class TestAConflictResolutionIsNamedAsSuch:
    def test_conflict_resolution_is_not_dressed_as_a_vote(self, act: str) -> None:
        st = _gov_state({"winner_provenance": "conflict_resolution"})
        text = _deliberation(_PROMPTS[act](st))
        assert "résolution de conflit" in text
        assert _VOTE not in text.lower()
        assert _WARNING not in text
