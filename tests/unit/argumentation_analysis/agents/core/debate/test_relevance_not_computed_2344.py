"""#2344: debate relevance and novelty are computed on content, or not at all.

Measured on ``main`` ``6dd102927``:
- The one production path, ``DebatePlugin.analyze_argument_quality``, passes
  no context. Relevance and novelty were then a constant 0.8, which carried
  25 % of persuasiveness's weight. On the tax sentence below, the heuristic
  ``debate_quality`` (persuasiveness x 5) was 3.06/5, and 1.0 of it came from
  that constant. With the two metrics dropped and the weights renormalized,
  it is 2.75/5.
- Two unrelated French sentences scored 0.27 relevance on function words
  alone ("la", "le", "de", "est"), and "Non." never matched "non".
- With no opponent argument, novelty was a perfect 1.0.
"""

from __future__ import annotations

import json

import pytest

from argumentation_analysis.agents.core.debate.debate_agent import DebatePlugin
from argumentation_analysis.agents.core.debate.debate_definitions import (
    ArgumentType,
    DebatePhase,
    EnhancedArgument,
)
from argumentation_analysis.agents.core.debate.debate_scoring import ArgumentAnalyzer
from argumentation_analysis.workflows.debate_tournament import (
    _debate_score_converged,
)

TAX = "La taxe sur le carbone est une mesure injuste pour les ménages de la classe moyenne."
FOOTBALL = "Le football est le sport le plus populaire de la planète et de loin."
REBUTTAL = "La taxe carbone protège le climat, et les ménages modestes reçoivent une compensation."


def _arg(content: str, agent: str = "Alice") -> EnhancedArgument:
    return EnhancedArgument(
        agent_name=agent,
        position="for",
        content=content,
        argument_type=ArgumentType.CLAIM,
        timestamp="t",
        phase=DebatePhase.MAIN_ARGUMENTS,
    )


@pytest.fixture
def analyzer() -> ArgumentAnalyzer:
    return ArgumentAnalyzer()


class TestProductionPathDoesNotInventAComparison:
    def test_plugin_reports_relevance_and_novelty_as_not_computed(self):
        scores = json.loads(DebatePlugin().analyze_argument_quality(TAX))
        assert scores["relevance_score"] is None
        assert scores["novelty_score"] is None

    def test_persuasiveness_carries_no_constant_for_them(self):
        scores = json.loads(DebatePlugin().analyze_argument_quality(TAX))
        computed_only = (
            scores["logical_coherence"] * 0.25
            + scores["evidence_quality"] * 0.25
            + scores["readability_score"] * 0.15
            + scores["fact_check_score"] * 0.10
        ) / 0.75
        assert scores["persuasiveness"] == pytest.approx(min(computed_only, 1.0))


class TestRelevanceReadsContentWords:
    def test_unrelated_sentences_share_no_relevance(self, analyzer):
        assert analyzer._assess_relevance(_arg(TAX), [_arg(FOOTBALL, "Bob")]) == 0.0

    def test_an_on_topic_rebuttal_is_relevant(self, analyzer):
        assert analyzer._assess_relevance(_arg(REBUTTAL), [_arg(TAX, "Bob")]) > 0.3

    def test_punctuation_does_not_hide_a_shared_word(self, analyzer):
        assert (
            analyzer._assess_relevance(_arg("Non, jamais."), [_arg("Non.", "Bob")]) > 0
        )

    def test_an_argument_without_content_words_is_not_scored(self, analyzer):
        # Only function words: nothing to compare, so not a 0.0 either.
        assert (
            analyzer._assess_relevance(_arg("Et la, de le."), [_arg(TAX, "Bob")])
            is None
        )


class TestNoveltyNeedsAnOpponent:
    def test_no_opponent_argument_is_not_a_perfect_novelty(self, analyzer):
        own = [_arg(TAX, "Alice")]
        assert analyzer._assess_novelty(_arg(REBUTTAL, "Alice"), own) is None

    def test_an_echo_of_the_opponent_has_no_novelty(self, analyzer):
        # Control: with an opponent to compare with, novelty is computed.
        assert analyzer._assess_novelty(_arg(TAX, "Alice"), [_arg(TAX, "Bob")]) == 0.0


class TestConsumersSkipWhatWasNotComputed:
    def test_tournament_convergence_ignores_a_missing_relevance(self):
        prev = {
            "logical_coherence": 0.6,
            "evidence_quality": 0.4,
            "relevance_score": None,
            "persuasiveness": 0.5,
        }
        curr = dict(prev, persuasiveness=0.52)
        assert _debate_score_converged(prev, curr) is True

    def test_weakness_ignores_arguments_without_novelty(self, analyzer):
        from argumentation_analysis.agents.core.debate.debate_agent import DebateAgent

        first, second = _arg(TAX, "Alice"), _arg(TAX, "Bob")
        first.metrics = analyzer.analyze_argument(first, [])
        second.metrics = analyzer.analyze_argument(second, [first])
        assert first.metrics.novelty_score is None
        # Must not raise on the None, and the echo's 0.0 novelty is the weakness.
        weakness = DebateAgent._identify_weakness(None, [first, second])
        assert weakness == "novelty_score"
