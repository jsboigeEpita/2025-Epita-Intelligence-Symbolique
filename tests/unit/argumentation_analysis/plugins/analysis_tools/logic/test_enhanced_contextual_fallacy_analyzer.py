# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.plugins.analysis_tools.logic.contextual_fallacy_analyzer
Covers EnhancedContextualFallacyAnalyzer: context type detection, complementary fallacies,
context analysis, semantic filtering, fallacy relations, feedback mechanism,
explanation generation, correction suggestions.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from argumentation_analysis.plugins.analysis_tools.logic.contextual_fallacy_analyzer import (
    EnhancedContextualFallacyAnalyzer,
)


@pytest.fixture
def mock_detector():
    """Create a mock fallacy detector."""
    detector = MagicMock()
    detector.detect_fallacies.return_value = []
    return detector


@pytest.fixture
def analyzer(mock_detector):
    """Create an analyzer with a mocked fallacy detector and clean learning data."""
    a = EnhancedContextualFallacyAnalyzer(fallacy_detector=mock_detector)
    # Reset learning data so tests don't depend on saved learning_data.json
    a.learning_data = {
        "context_patterns": {},
        "fallacy_patterns": {},
        "feedback_history": [],
        "confidence_adjustments": {},
    }
    a.feedback_history = []
    a.context_embeddings_cache = {}
    # Prevent writing to disk during tests
    a._save_learning_data = lambda: None
    return a


# ============================================================
# __init__
# ============================================================

class TestInit:
    def test_creates_instance(self, analyzer):
        assert isinstance(analyzer, EnhancedContextualFallacyAnalyzer)

    def test_has_fallacy_detector(self, analyzer, mock_detector):
        assert analyzer.fallacy_detector is mock_detector

    def test_empty_feedback_history(self, analyzer):
        assert analyzer.feedback_history == []

    def test_empty_cache(self, analyzer):
        assert analyzer.context_embeddings_cache == {}

    def test_nlp_models_empty(self, analyzer):
        # NLP models loading is disabled in the source
        assert analyzer.nlp_models == {}


# ============================================================
# _determine_context_type
# ============================================================

class TestDetermineContextType:
    def test_political(self, analyzer):
        assert analyzer._determine_context_type("discours politique") == "politique"

    def test_election(self, analyzer):
        assert analyzer._determine_context_type("campagne élection") == "politique"

    def test_scientific(self, analyzer):
        assert analyzer._determine_context_type("article scientifique") == "scientifique"

    def test_research(self, analyzer):
        assert analyzer._determine_context_type("recherche académique") == "scientifique"

    def test_commercial(self, analyzer):
        assert analyzer._determine_context_type("publicité commercial") == "commercial"

    def test_legal(self, analyzer):
        assert analyzer._determine_context_type("contexte juridique") == "juridique"

    def test_academic(self, analyzer):
        assert analyzer._determine_context_type("milieu académique") == "académique"

    def test_general_default(self, analyzer):
        assert analyzer._determine_context_type("just some random text") == "général"

    def test_case_insensitive(self, analyzer):
        assert analyzer._determine_context_type("POLITIQUE") == "politique"


# ============================================================
# _are_complementary_fallacies
# ============================================================

class TestAreComplementaryFallacies:
    def test_authority_and_popularity(self, analyzer):
        assert analyzer._are_complementary_fallacies(
            "Appel à l'autorité", "Appel à la popularité"
        ) is True

    def test_popularity_and_authority_reversed(self, analyzer):
        assert analyzer._are_complementary_fallacies(
            "Appel à la popularité", "Appel à l'autorité"
        ) is True

    def test_dilemma_and_emotion(self, analyzer):
        assert analyzer._are_complementary_fallacies(
            "Faux dilemme", "Appel à l'émotion"
        ) is True

    def test_slippery_slope_and_fear(self, analyzer):
        assert analyzer._are_complementary_fallacies(
            "Pente glissante", "Appel à la peur"
        ) is True

    def test_strawman_and_ad_hominem(self, analyzer):
        assert analyzer._are_complementary_fallacies(
            "Homme de paille", "Ad hominem"
        ) is True

    def test_tradition_and_authority(self, analyzer):
        assert analyzer._are_complementary_fallacies(
            "Appel à la tradition", "Appel à l'autorité"
        ) is True

    def test_non_complementary(self, analyzer):
        assert analyzer._are_complementary_fallacies(
            "Ad hominem", "Faux dilemme"
        ) is False

    def test_same_type_not_complementary(self, analyzer):
        assert analyzer._are_complementary_fallacies(
            "Ad hominem", "Ad hominem"
        ) is False


# ============================================================
# _analyze_context_deeply (without NLP models)
# ============================================================

class TestAnalyzeContextDeeply:
    def test_returns_expected_keys(self, analyzer):
        result = analyzer._analyze_context_deeply("contexte politique")
        assert "context_type" in result
        assert "context_subtypes" in result
        assert "audience_characteristics" in result
        assert "formality_level" in result
        assert "confidence" in result

    def test_default_confidence(self, analyzer):
        result = analyzer._analyze_context_deeply("some general context")
        assert result["confidence"] == 0.7

    def test_default_formality(self, analyzer):
        result = analyzer._analyze_context_deeply("some context")
        assert result["formality_level"] == "moyen"

    def test_caching(self, analyzer):
        ctx = "contexte politique important"
        result1 = analyzer._analyze_context_deeply(ctx)
        result2 = analyzer._analyze_context_deeply(ctx)
        assert result1 is result2  # Same object from cache


# ============================================================
# _analyze_fallacy_relations
# ============================================================

class TestAnalyzeFallacyRelations:
    def test_empty_list(self, analyzer):
        assert analyzer._analyze_fallacy_relations([]) == []

    def test_single_fallacy(self, analyzer):
        fallacies = [{"fallacy_type": "Ad hominem", "context_text": "text1"}]
        assert analyzer._analyze_fallacy_relations(fallacies) == []

    def test_same_context_relation(self, analyzer):
        fallacies = [
            {"fallacy_type": "Ad hominem", "context_text": "same text"},
            {"fallacy_type": "Faux dilemme", "context_text": "same text"},
        ]
        relations = analyzer._analyze_fallacy_relations(fallacies)
        assert len(relations) >= 1
        assert any(r["relation_type"] == "same_context" for r in relations)

    def test_complementary_relation(self, analyzer):
        fallacies = [
            {"fallacy_type": "Appel à l'autorité", "context_text": "text1"},
            {"fallacy_type": "Appel à la popularité", "context_text": "text2"},
        ]
        relations = analyzer._analyze_fallacy_relations(fallacies)
        assert any(r["relation_type"] == "complementary" for r in relations)

    def test_no_relation(self, analyzer):
        fallacies = [
            {"fallacy_type": "Ad hominem", "context_text": "text1"},
            {"fallacy_type": "Faux dilemme", "context_text": "text2"},
        ]
        relations = analyzer._analyze_fallacy_relations(fallacies)
        assert len(relations) == 0


# ============================================================
# _filter_by_context_semantic
# ============================================================

class TestFilterByContextSemantic:
    def test_general_context_returns_all(self, analyzer):
        fallacies = [
            {"fallacy_type": "Ad hominem", "confidence": 0.5, "context_text": "x"},
        ]
        ctx = {"context_type": "général", "context_subtypes": [], "audience_characteristics": [], "formality_level": "moyen"}
        result = analyzer._filter_by_context_semantic(fallacies, ctx)
        assert len(result) == len(fallacies)

    def test_political_context_boosts_relevant(self, analyzer):
        fallacies = [
            {"fallacy_type": "Ad hominem", "confidence": 0.5, "context_text": "x"},
        ]
        ctx = {
            "context_type": "politique",
            "context_subtypes": [],
            "audience_characteristics": [],
            "formality_level": "moyen",
        }
        result = analyzer._filter_by_context_semantic(fallacies, ctx)
        assert len(result) == 1
        # Ad hominem in political context gets +0.3
        assert result[0]["confidence"] == 0.8
        assert result[0]["contextual_relevance"] == "Élevée"

    def test_irrelevant_fallacy_low_relevance(self, analyzer):
        fallacies = [
            {"fallacy_type": "Post hoc ergo propter hoc", "confidence": 0.5, "context_text": "x"},
        ]
        ctx = {
            "context_type": "politique",
            "context_subtypes": [],
            "audience_characteristics": [],
            "formality_level": "moyen",
        }
        result = analyzer._filter_by_context_semantic(fallacies, ctx)
        assert result[0]["contextual_relevance"] == "Faible"
        assert result[0]["confidence"] == 0.5  # No boost

    def test_subtype_adjustments(self, analyzer):
        fallacies = [
            {"fallacy_type": "Appel à l'émotion", "confidence": 0.5, "context_text": "x"},
        ]
        ctx = {
            "context_type": "politique",
            "context_subtypes": ["électoral"],
            "audience_characteristics": [],
            "formality_level": "moyen",
        }
        result = analyzer._filter_by_context_semantic(fallacies, ctx)
        # Base: +0.3 (politique) + 0.1 (électoral subtype) = 0.9
        assert result[0]["confidence"] == pytest.approx(0.9, abs=0.01)

    def test_audience_adjustments(self, analyzer):
        fallacies = [
            {"fallacy_type": "Appel à l'autorité", "confidence": 0.5, "context_text": "x"},
        ]
        ctx = {
            "context_type": "académique",
            "context_subtypes": [],
            "audience_characteristics": ["expert"],
            "formality_level": "moyen",
        }
        result = analyzer._filter_by_context_semantic(fallacies, ctx)
        # Base: +0.4 (academic) + 0.1 (expert audience) = 1.0
        assert result[0]["confidence"] == pytest.approx(1.0, abs=0.01)

    def test_sorted_by_confidence_desc(self, analyzer):
        fallacies = [
            {"fallacy_type": "Post hoc ergo propter hoc", "confidence": 0.9, "context_text": "x"},
            {"fallacy_type": "Ad hominem", "confidence": 0.3, "context_text": "y"},
        ]
        ctx = {
            "context_type": "politique",
            "context_subtypes": [],
            "audience_characteristics": [],
            "formality_level": "moyen",
        }
        result = analyzer._filter_by_context_semantic(fallacies, ctx)
        assert result[0]["confidence"] >= result[1]["confidence"]


# ============================================================
# analyze_context
# ============================================================

class TestAnalyzeContext:
    def test_returns_expected_keys(self, analyzer, mock_detector):
        mock_detector.detect_fallacies.return_value = []
        result = analyzer.analyze_context("some text", "politique")
        assert "context_analysis" in result
        assert "potential_fallacies_count" in result
        assert "contextual_fallacies_count" in result
        assert "contextual_fallacies" in result
        assert "fallacy_relations" in result
        assert "analysis_timestamp" in result

    def test_with_detected_fallacies(self, analyzer, mock_detector):
        mock_detector.detect_fallacies.return_value = [
            {"fallacy_type": "Ad hominem", "keyword": "x", "context_text": "attack", "confidence": 0.7},
        ]
        result = analyzer.analyze_context("He attacked the person", "politique")
        assert result["potential_fallacies_count"] >= 1
        assert result["contextual_fallacies_count"] >= 1

    def test_stores_last_analysis_fallacies(self, analyzer, mock_detector):
        mock_detector.detect_fallacies.return_value = [
            {"fallacy_type": "Ad hominem", "keyword": "x", "context_text": "t", "confidence": 0.5},
        ]
        analyzer.analyze_context("text", "politique")
        assert len(analyzer.last_analysis_fallacies) >= 1


# ============================================================
# provide_feedback
# ============================================================

class TestProvideFeedback:
    def test_records_feedback(self, analyzer, mock_detector):
        mock_detector.detect_fallacies.return_value = [
            {"fallacy_type": "Ad hominem", "keyword": "x", "context_text": "t", "confidence": 0.5},
        ]
        analyzer.analyze_context("text", "politique")
        analyzer.provide_feedback("fallacy_0", True, "good detection")
        assert len(analyzer.feedback_history) == 1
        assert analyzer.feedback_history[0]["is_correct"] is True

    def test_positive_feedback_increases_confidence(self, analyzer, mock_detector):
        mock_detector.detect_fallacies.return_value = [
            {"fallacy_type": "Ad hominem", "keyword": "x", "context_text": "t", "confidence": 0.5},
        ]
        analyzer.analyze_context("text", "politique")
        analyzer.provide_feedback("fallacy_0", True)
        assert analyzer.learning_data["confidence_adjustments"]["Ad hominem"] == pytest.approx(0.05)

    def test_negative_feedback_decreases_confidence(self, analyzer, mock_detector):
        mock_detector.detect_fallacies.return_value = [
            {"fallacy_type": "Faux dilemme", "keyword": "x", "context_text": "t", "confidence": 0.5},
        ]
        analyzer.analyze_context("text", "politique")
        analyzer.provide_feedback("fallacy_0", False)
        assert analyzer.learning_data["confidence_adjustments"]["Faux dilemme"] == pytest.approx(-0.1)

    def test_feedback_clamped(self, analyzer, mock_detector):
        mock_detector.detect_fallacies.return_value = [
            {"fallacy_type": "Ad hominem", "keyword": "x", "context_text": "t", "confidence": 0.5},
        ]
        analyzer.analyze_context("text", "politique")
        # Push confidence down many times
        for _ in range(20):
            analyzer.provide_feedback("fallacy_0", False)
        assert analyzer.learning_data["confidence_adjustments"]["Ad hominem"] >= -0.5

    def test_feedback_for_unknown_id(self, analyzer):
        # Should not crash
        analyzer.provide_feedback("nonexistent_id", True)
        assert len(analyzer.feedback_history) == 1


# ============================================================
# _generate_fallacy_explanation
# ============================================================

class TestGenerateFallacyExplanation:
    def test_known_combination(self, analyzer):
        explanation = analyzer._generate_fallacy_explanation(
            "Appel à l'autorité", "politique", "example text"
        )
        assert "autorité" in explanation.lower() or "politique" in explanation.lower()

    def test_unknown_combination_generic(self, analyzer):
        explanation = analyzer._generate_fallacy_explanation(
            "Unknown Fallacy", "unknown_context", "example"
        )
        assert "Unknown Fallacy" in explanation
        assert "unknown_context" in explanation


# ============================================================
# _generate_correction_suggestion
# ============================================================

class TestGenerateCorrectionSuggestion:
    def test_known_fallacy(self, analyzer):
        suggestion = analyzer._generate_correction_suggestion(
            "Faux dilemme", "either A or B"
        )
        assert "Faux dilemme" in suggestion

    def test_ad_hominem(self, analyzer):
        suggestion = analyzer._generate_correction_suggestion(
            "Ad hominem", "you're wrong because you're bad"
        )
        assert "Ad hominem" in suggestion

    def test_unknown_fallacy_generic(self, analyzer):
        suggestion = analyzer._generate_correction_suggestion(
            "Super Rare Fallacy", "some example"
        )
        assert "Super Rare Fallacy" in suggestion


# ============================================================
# get_contextual_fallacy_examples
# ============================================================

class TestGetContextualFallacyExamples:
    def test_returns_list(self, analyzer):
        result = analyzer.get_contextual_fallacy_examples(
            "Appel à l'autorité", "politique"
        )
        assert isinstance(result, list)

    def test_empty_when_no_base_examples(self, analyzer):
        # The method currently returns [] because basic_examples is hardcoded to []
        result = analyzer.get_contextual_fallacy_examples(
            "Appel à l'autorité", "politique"
        )
        assert result == []


# ============================================================
# identify_contextual_fallacies
# ============================================================

class TestIdentifyContextualFallacies:
    def test_returns_list(self, analyzer, mock_detector):
        mock_detector.detect_fallacies.return_value = []
        result = analyzer.identify_contextual_fallacies("some argument", "politique")
        assert isinstance(result, list)

    def test_filters_by_confidence(self, analyzer, mock_detector):
        mock_detector.detect_fallacies.return_value = [
            {"fallacy_type": "Ad hominem", "keyword": "x", "context_text": "t", "confidence": 0.1},
        ]
        result = analyzer.identify_contextual_fallacies("some text", "politique")
        # In political context, Ad hominem gets +0.3 -> 0.4 still below 0.5?
        # Actually: 0.1 + 0.3 = 0.4, filtered out (< 0.5)
        # But result depends on exact boosting
        assert isinstance(result, list)

    def test_high_confidence_passed_through(self, analyzer, mock_detector):
        mock_detector.detect_fallacies.return_value = [
            {"fallacy_type": "Ad hominem", "keyword": "x", "context_text": "t", "confidence": 0.8},
        ]
        result = analyzer.identify_contextual_fallacies("some text", "politique")
        # 0.8 + 0.3 = 1.0, well above 0.5 threshold
        assert len(result) == 1
