# tests/unit/argumentation_analysis/agents/core/debate/test_debate_scoring.py
"""Tests for ArgumentAnalyzer — 8-metric argument quality evaluation."""

import pytest
from argumentation_analysis.agents.core.debate.debate_scoring import ArgumentAnalyzer
from argumentation_analysis.agents.core.debate.debate_definitions import (
    ArgumentMetrics,
    ArgumentType,
    DebatePhase,
    EnhancedArgument,
)


@pytest.fixture
def analyzer():
    return ArgumentAnalyzer()


def _make_arg(content, agent="Alice", position="for"):
    return EnhancedArgument(
        agent_name=agent,
        position=position,
        content=content,
        argument_type=ArgumentType.CLAIM,
        timestamp="2025-01-01T00:00:00",
        phase=DebatePhase.MAIN_ARGUMENTS,
    )


# ── Init ──


class TestAnalyzerInit:
    def test_indicators_loaded(self, analyzer):
        assert len(analyzer.logical_indicators) > 0
        assert len(analyzer.evidence_indicators) > 0
        assert len(analyzer.emotional_indicators) > 0

    def test_logical_indicators_contain_therefore(self, analyzer):
        assert "therefore" in analyzer.logical_indicators

    def test_evidence_indicators_contain_studies(self, analyzer):
        assert "studies show" in analyzer.evidence_indicators


# ── Logical Coherence ──


class TestLogicalCoherence:
    def test_baseline(self, analyzer):
        score = analyzer._assess_logical_coherence("Simple statement.")
        assert 0.4 <= score <= 0.6  # baseline ~0.5

    def test_with_connectors(self, analyzer):
        text = "Because A is true, therefore B follows. Since C, thus D."
        score = analyzer._assess_logical_coherence(text)
        assert score > 0.6

    def test_with_structure_words(self, analyzer):
        text = "The premise is valid. The conclusion follows logically."
        score = analyzer._assess_logical_coherence(text)
        assert score > 0.5

    def test_with_ordering(self, analyzer):
        text = "First we consider X. Second we observe Y."
        score = analyzer._assess_logical_coherence(text)
        assert score > 0.5

    def test_capped_at_one(self, analyzer):
        text = "therefore because since thus hence consequently as a result it follows that given that due to premise conclusion first second"
        score = analyzer._assess_logical_coherence(text)
        assert score <= 1.0


# ── Evidence Quality ──


class TestEvidenceQuality:
    def test_baseline(self, analyzer):
        score = analyzer._assess_evidence_quality("Simple opinion.")
        assert 0.2 <= score <= 0.4  # baseline ~0.3

    def test_with_citations(self, analyzer):
        text = (
            "Studies show that 85% of participants improved. According to the journal."
        )
        score = analyzer._assess_evidence_quality(text)
        assert score > 0.5

    def test_with_numbers(self, analyzer):
        text = "The rate went from 12.5% to 23.7% in 3 months."
        score = analyzer._assess_evidence_quality(text)
        assert score > 0.3

    def test_with_academic_refs(self, analyzer):
        text = "A study published by the university confirms this."
        score = analyzer._assess_evidence_quality(text)
        assert score >= 0.4

    def test_capped_at_one(self, analyzer):
        text = "studies show research indicates data suggests according to evidence statistics findings survey analysis report study university journal published 10 20 30 40 50 60%"
        score = analyzer._assess_evidence_quality(text)
        assert score <= 1.0


# ── Relevance ──


class TestRelevance:
    def test_no_context(self, analyzer):
        arg = _make_arg("Climate change is real.")
        score = analyzer._assess_relevance(arg, [])
        assert score == 0.8  # default for no context

    def test_high_overlap(self, analyzer):
        arg = _make_arg("Climate change is a serious threat.")
        context = [_make_arg("Climate change threatens our future.")]
        score = analyzer._assess_relevance(arg, context)
        assert score > 0.2

    def test_low_overlap(self, analyzer):
        arg = _make_arg("The economy is growing.")
        context = [_make_arg("Butterflies migrate south in winter.")]
        score = analyzer._assess_relevance(arg, context)
        assert score < 0.5

    def test_uses_recent_context(self, analyzer):
        old = [_make_arg(f"Old topic {i}") for i in range(10)]
        recent = _make_arg("Current discussion topic")
        old.append(recent)
        arg = _make_arg("Current discussion topic matters")
        score = analyzer._assess_relevance(arg, old)
        assert score > 0.0  # uses last 3


# ── Emotional Appeal ──


class TestEmotionalAppeal:
    def test_neutral(self, analyzer):
        score = analyzer._assess_emotional_appeal("The data is clear.")
        assert score < 0.2

    def test_emotional_words(self, analyzer):
        text = "I feel this is crucial and important for our vital future!"
        score = analyzer._assess_emotional_appeal(text)
        assert score > 0.2

    def test_exclamations(self, analyzer):
        text = "This is wrong! Very wrong! Unacceptable!"
        score = analyzer._assess_emotional_appeal(text)
        assert score > 0.1

    def test_caps_words(self, analyzer):
        text = "This is ABSOLUTELY WRONG and TERRIBLE"
        score = analyzer._assess_emotional_appeal(text)
        assert score > 0.0

    def test_capped_at_one(self, analyzer):
        text = "feel believe think important crucial vital devastating wonderful terrible amazing ! ! ! ! ! STOP THIS NOW PLEASE"
        score = analyzer._assess_emotional_appeal(text)
        assert score <= 1.0


# ── Readability ──


class TestReadability:
    def test_short_sentences(self, analyzer):
        text = "Short sentence. Another one. Easy to read."
        score = analyzer._assess_readability(text)
        assert score > 0.3

    def test_long_sentences(self, analyzer):
        text = "This is an extremely long and convoluted sentence that goes on and on with many subordinate clauses and parenthetical expressions that make it very difficult for the average reader to follow the argument being presented in a clear and coherent manner."
        score = analyzer._assess_readability(text)
        assert score < 0.8

    def test_within_range(self, analyzer):
        text = "Normal text. With moderate length sentences. Not too complex."
        score = analyzer._assess_readability(text)
        assert 0 <= score <= 1.0


# ── Fact Check ──


class TestFactCheck:
    def test_hedging_language(self, analyzer):
        text = "This might possibly be true. It could likely happen."
        score = analyzer._basic_fact_check(text)
        assert score == 0.7

    def test_absolute_language(self, analyzer):
        text = "This is always true. All people definitely agree. Never wrong."
        score = analyzer._basic_fact_check(text)
        assert score == 0.4

    def test_balanced(self, analyzer):
        text = "Normal statement without hedging or absolutism."
        score = analyzer._basic_fact_check(text)
        assert score == 0.6


# ── Novelty ──


class TestNovelty:
    def test_no_context(self, analyzer):
        arg = _make_arg("Novel idea")
        score = analyzer._assess_novelty(arg, [])
        assert score == 0.8

    def test_unique_argument(self, analyzer):
        arg = _make_arg("Quantum computing changes everything", agent="Alice")
        context = [_make_arg("Traditional methods are fine", agent="Bob")]
        score = analyzer._assess_novelty(arg, context)
        assert score > 0.5

    def test_repeated_argument(self, analyzer):
        arg = _make_arg("The sky is blue and beautiful", agent="Alice")
        context = [_make_arg("The sky is blue and beautiful", agent="Bob")]
        score = analyzer._assess_novelty(arg, context)
        assert score < 0.3

    def test_same_agent_ignored(self, analyzer):
        """Same agent's args excluded from comparison => no opponents => novelty=1.0."""
        arg = _make_arg("Repeated by same person", agent="Alice")
        context = [_make_arg("Repeated by same person", agent="Alice")]
        score = analyzer._assess_novelty(arg, context)
        assert score == 1.0  # no opponent args => avg_similarity=0 => 1-0=1


# ── Full Analysis ──


class TestAnalyzeArgument:
    def test_returns_metrics(self, analyzer):
        arg = _make_arg("Because of the evidence, therefore the conclusion follows.")
        metrics = analyzer.analyze_argument(arg, [])
        assert isinstance(metrics, ArgumentMetrics)

    def test_all_scores_in_range(self, analyzer):
        arg = _make_arg("A comprehensive argument with many facets.")
        metrics = analyzer.analyze_argument(arg, [])
        assert 0 <= metrics.logical_coherence <= 1.0
        assert 0 <= metrics.evidence_quality <= 1.0
        assert 0 <= metrics.relevance_score <= 1.0
        assert 0 <= metrics.emotional_appeal <= 1.0
        assert 0 <= metrics.readability_score <= 1.0
        assert 0 <= metrics.fact_check_score <= 1.0
        assert 0 <= metrics.novelty_score <= 1.0
        assert 0 <= metrics.persuasiveness <= 1.0

    def test_persuasiveness_is_weighted_combo(self, analyzer):
        arg = _make_arg(
            "Because studies show evidence, therefore the conclusion follows."
        )
        metrics = analyzer.analyze_argument(arg, [])
        expected = min(
            metrics.logical_coherence * 0.25
            + metrics.evidence_quality * 0.25
            + metrics.relevance_score * 0.15
            + metrics.readability_score * 0.15
            + metrics.fact_check_score * 0.10
            + metrics.novelty_score * 0.10,
            1.0,
        )
        assert metrics.persuasiveness == pytest.approx(expected, abs=0.01)
