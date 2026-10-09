"""#2965 (R1077 corrected slice) — the verdict is framed on its ORIGIN.

The narrative used to frame the governance verdict on ``extraction_method``
(Track E #1281): ``== "llm"`` was read as "the verdict is a model
assessment". The R1077 paid pass on ``doc_A`` falsified the premise — the
record was ``llm`` + ``vote_aggregate``, i.e. an LLM assessment **ran** but a
**vote** decided. Act II then told the reader a vote was a model ranking.

The origin is ``winner_provenance`` (#2969). One vocabulary per origin, on
both Acts — and, since the R1078 review of this PR, keyed on WHAT THE
ORIGIN'S PRODUCER WRITES INTO ``winner`` (measured on the real writer):

* ``vote_aggregate`` → the vote wording, no model warning (a
  model-recommended *method* is named, not the verdict); ``winner`` is a
  ranked unit id;
* ``llm_resolution`` → the writer stores the LLM's ``recommended_resolution``
  — a STRATEGY (``compromise``), never an argument: the R1078 blocker was
  exactly a prompt calling that strategy « l'argument arrivé en tête »;
* ``conflict_resolution`` → the writer stores the mediation's
  ``resolution_type`` (``collaborative``) — a mediation outcome, not a unit;
* unrecorded → the origin is stated unknown; the renderer does NOT guess it
  (anti-#1019: absence is not a vote, and a vote is not an absence).

The fallback-origin witnesses are PRODUCER-driven: the real
``_write_governance_to_state`` writes the decision, the real collectors and
prompt builders read it back — no hand-built record shape in between (the
R1078 finding: hand-built ``arg_1`` records certified producers that do not
exist).

Born red on ``ecfd3a092``: the real shape (``llm`` + ``vote_aggregate``)
carries the false model warning in Act II, and an ``llm_resolution`` record
reads as a vote in Act III.

Privacy: invented filler, opaque ids, no corpus sentence. Deterministic: no
JVM, no LLM.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.state_writers import (
    _write_governance_to_state,
)
from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_evidence,
    build_act2_prompt,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_evidence,
    build_act3_prompt,
)

_VOTE = "vote social-choice"
_STRATEGY_WARNING = "RECOMMANDATION DE STRATÉGIE"


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


def _written_state(output: dict) -> UnifiedAnalysisState:
    """The REAL writer on the REAL state class — the producer boundary.

    ``_write_governance_to_state`` decides the record's shape (winner value,
    provenance fields); hand-building the decision here would re-certify
    whatever shape the test imagines (the R1078 finding on this very PR).
    """
    state = UnifiedAnalysisState(
        initial_text="filler text for the witness, no corpus content."
    )
    _write_governance_to_state(output, state, {})
    return state


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
class TestTheRealProducerShapesReachTheActs:
    """R1078 — producer → state → both Acts, on the REAL writer.

    The fallback producers write a STRATEGY (``compromise``) and a MEDIATION
    TYPE (``collaborative``) into ``winner`` — never ``arg_1``. The Acts must
    frame those as what they are; the ranked-argument framing is reserved for
    ``vote_aggregate`` (and unrecorded records), the only kinds whose winner
    IS a unit id.
    """

    def test_an_llm_resolution_is_a_recommended_strategy_not_a_ranked_argument(
        self, act: str
    ) -> None:
        """The producer shape ``invoke_callables`` really emits: an LLM
        governance assessment whose ``recommended_resolution`` is a strategy.
        Born red on the pre-R1078 head: the prompt called « compromise »
        « l'option d'identifiant interne … désignée par une évaluation d'un
        modèle » and the warning said « classement évalué par le modèle »."""
        output = {
            "llm_governance_assessment": {
                "recommended_method": "copeland",
                "recommended_resolution": "compromise",
                "stakeholder_analysis": [
                    {"agent": "elector_a", "position": "x", "influence": 0.5}
                ],
            }
        }
        state = _written_state(output)
        decision = state.governance_decisions[-1]
        # producer → state: the strategy is the winner, tagged llm_resolution
        assert decision["winner"] == "compromise"
        assert decision["winner_provenance"] == "llm_resolution"
        # state → both Acts: a recommended STRATEGY, never a ranked argument
        text = _deliberation(_PROMPTS[act](state))
        assert "RECOMMANDE la stratégie de résolution « compromise »" in text
        assert _STRATEGY_WARNING in text  # single LLM call, no ranking claim
        assert _VOTE not in text.lower()
        assert "option d'identifiant interne" not in text  # not an option id

    def test_a_conflict_resolution_is_a_mediation_type_not_a_unit(
        self, act: str
    ) -> None:
        """The producer shape the conflict plugin really emits:
        ``resolutions[0].resolution_type`` — a mediation outcome. Born red on
        the pre-R1078 head: « collaborative » was « l'option d'identifiant
        interne » the prose had to dress as « l'argument arrivé en tête »."""
        output = {
            "conflicts": [{"agents": ["a", "b"], "description": "d"}],
            "resolutions": [
                {
                    "resolution_type": "collaborative",
                    "success_probability": None,
                    "agents": ["a", "b"],
                    "details": "Agents seek common ground.",
                }
            ],
        }
        state = _written_state(output)
        decision = state.governance_decisions[-1]
        # producer → state: the mediation type is the winner
        assert decision["winner"] == "collaborative"
        assert decision["winner_provenance"] == "conflict_resolution"
        # state → both Acts: a mediation, never a vote nor a ranked argument
        text = _deliberation(_PROMPTS[act](state))
        assert "MÉDIATION de type « collaborative »" in text
        assert _VOTE not in text.lower()
        assert "option d'identifiant interne" not in text
        assert _STRATEGY_WARNING not in text  # no LLM claim on this origin


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
        assert _STRATEGY_WARNING not in text  # no model-verdict warning
        # the model is named as the METHOD's recommender, not the verdict's
        assert "méthode de vote recommandée par le modèle" in text

    def test_a_vote_winner_is_framed_as_a_ranked_unit(self, act: str) -> None:
        """Only a vote writes a ranked unit into ``winner`` — so only a vote
        earns the ranked-argument framing (R1078: that framing on a strategy
        was the blocker). The unit's referent travels on the line (#2989)."""
        st = _gov_state({"winner_provenance": "vote_aggregate"})
        text = _deliberation(_PROMPTS[act](st))
        assert _VOTE in text.lower()
        assert "clause opératoire" in text  # the winner's text is on the line


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
        assert _STRATEGY_WARNING not in text

    def test_the_text_of_the_winner_still_travels_when_the_origin_is_unknown(
        self, act: str
    ) -> None:
        """Bounding the origin must not drop the #2989 referent: the winner's
        text is still on the line (positive control against a fix that
        removes the claim by removing the line)."""
        st = _gov_state({"extraction_method": "heuristic"})
        text = _deliberation(_PROMPTS[act](st))
        assert "clause opératoire" in text
