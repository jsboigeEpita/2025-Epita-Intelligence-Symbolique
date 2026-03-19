"""
Tests for analytics/effectiveness_analyzer.py.

Covers analyze_agent_effectiveness() with various corpus structures.
"""

import pytest
from argumentation_analysis.analytics.effectiveness_analyzer import (
    analyze_agent_effectiveness,
)


class TestAnalyzeAgentEffectiveness:
    """Tests for the analyze_agent_effectiveness function."""

    def test_empty_corpus(self):
        """Empty corpus returns valid structure with no agents."""
        result = analyze_agent_effectiveness([], "empty_corpus")
        assert result["corpus_name"] == "empty_corpus"
        assert result["total_results_analyzed"] == 0
        assert result["agents_evaluated"] == []
        assert result["best_agent_overall"] == "N/A"
        assert len(result["recommendations"]) == 1
        assert "Aucun agent" in result["recommendations"][0]

    def test_single_agent_single_result(self):
        """Single agent with one result computes scores."""
        corpus = [
            {
                "agent_name": "AgentA",
                "fallacies": [
                    {"fallacy_type": "ad_hominem", "confidence": 0.9},
                    {"fallacy_type": "straw_man", "confidence": 0.8},
                ],
                "confidence_score": 0.85,
            }
        ]
        result = analyze_agent_effectiveness(corpus, "test_corpus")
        assert result["total_results_analyzed"] == 1
        assert result["agents_evaluated"] == ["AgentA"]
        assert result["best_agent_overall"] == "AgentA"
        det = result["fallacy_detection_by_agent"]["AgentA"]
        assert det["total_fallacies_detected"] == 2
        assert det["average_fallacies_per_item"] == 2.0
        assert det["average_confidence"] == 0.85
        assert det["fallacy_types_summary"]["ad_hominem"] == 1
        assert det["fallacy_types_summary"]["straw_man"] == 1
        assert result["effectiveness_scores"]["AgentA"] > 0

    def test_multiple_agents_best_picked(self):
        """With two agents, the one with higher score is best."""
        corpus = [
            {
                "agent_name": "WeakAgent",
                "fallacies": [],
                "confidence_score": 0.5,
            },
            {
                "agent_name": "StrongAgent",
                "fallacies": [
                    {"fallacy_type": "circular", "confidence": 0.95},
                    {"fallacy_type": "slippery_slope", "confidence": 0.88},
                    {"fallacy_type": "appeal_to_emotion", "confidence": 0.92},
                ],
                "confidence_score": 0.9,
            },
        ]
        result = analyze_agent_effectiveness(corpus, "multi")
        assert result["best_agent_overall"] == "StrongAgent"
        assert result["agents_evaluated"] == ["StrongAgent", "WeakAgent"]
        assert result["effectiveness_scores"]["WeakAgent"] == 0.0
        assert result["effectiveness_scores"]["StrongAgent"] > 0

    def test_fallback_to_source_name(self):
        """Uses source_name when agent_name is missing."""
        corpus = [
            {"source_name": "FallbackAgent", "fallacies": [], "confidence_score": 0.5}
        ]
        result = analyze_agent_effectiveness(corpus)
        assert "FallbackAgent" in result["agents_evaluated"]

    def test_fallback_to_unknown_agent(self):
        """Uses UnknownAgent when both agent_name and source_name are missing."""
        corpus = [{"fallacies": [], "confidence_score": 0.5}]
        result = analyze_agent_effectiveness(corpus)
        assert "UnknownAgent" in result["agents_evaluated"]

    def test_nested_analysis_key(self):
        """Handles fallacies inside an 'analysis' subdict."""
        corpus = [
            {
                "agent_name": "Nested",
                "analysis": {
                    "fallacies": [{"type": "red_herring"}],
                    "overall_confidence": 0.7,
                },
            }
        ]
        result = analyze_agent_effectiveness(corpus)
        det = result["fallacy_detection_by_agent"]["Nested"]
        assert det["total_fallacies_detected"] == 1
        assert det["fallacy_types_summary"]["red_herring"] == 1

    def test_confidence_fallback_overall_confidence(self):
        """Uses overall_confidence when confidence_score is absent."""
        corpus = [
            {
                "agent_name": "X",
                "fallacies": [{"fallacy_type": "a"}],
                "overall_confidence": 0.6,
            }
        ]
        result = analyze_agent_effectiveness(corpus)
        assert result["fallacy_detection_by_agent"]["X"]["average_confidence"] == 0.6

    def test_non_dict_fallacy_ignored(self):
        """Non-dict items in fallacies list are counted but types not extracted."""
        corpus = [
            {
                "agent_name": "MixedAgent",
                "fallacies": ["string_fallacy", {"fallacy_type": "real"}],
                "confidence_score": 0.5,
            }
        ]
        result = analyze_agent_effectiveness(corpus)
        det = result["fallacy_detection_by_agent"]["MixedAgent"]
        assert det["total_fallacies_detected"] == 2
        assert det["fallacy_types_summary"].get("real", 0) == 1

    def test_non_numeric_confidence_ignored(self):
        """Non-numeric confidence values are skipped."""
        corpus = [
            {
                "agent_name": "BadConf",
                "fallacies": [],
                "confidence_score": "high",
            }
        ]
        result = analyze_agent_effectiveness(corpus)
        assert (
            result["fallacy_detection_by_agent"]["BadConf"]["average_confidence"] == 0.0
        )

    def test_multiple_results_same_agent(self):
        """Multiple results for same agent are aggregated."""
        corpus = [
            {
                "agent_name": "AgentA",
                "fallacies": [{"fallacy_type": "x"}],
                "confidence_score": 0.8,
            },
            {
                "agent_name": "AgentA",
                "fallacies": [{"fallacy_type": "y"}, {"fallacy_type": "z"}],
                "confidence_score": 0.6,
            },
        ]
        result = analyze_agent_effectiveness(corpus)
        det = result["fallacy_detection_by_agent"]["AgentA"]
        assert det["total_fallacies_detected"] == 3
        assert det["average_fallacies_per_item"] == 1.5
        assert det["average_confidence"] == 0.7

    def test_default_corpus_name(self):
        """Default corpus_name is N/A."""
        result = analyze_agent_effectiveness([])
        assert result["corpus_name"] == "N/A"

    def test_recommendation_includes_best_agent(self):
        """Recommendation mentions the best agent and corpus name."""
        corpus = [
            {
                "agent_name": "TopAgent",
                "fallacies": [{"fallacy_type": "a"}],
                "confidence_score": 0.9,
            }
        ]
        result = analyze_agent_effectiveness(corpus, "my_corpus")
        assert "TopAgent" in result["recommendations"][0]
        assert "my_corpus" in result["recommendations"][0]

    def test_fallacy_type_fallback_to_type_key(self):
        """Falls back to 'type' key when 'fallacy_type' is missing."""
        corpus = [
            {
                "agent_name": "A",
                "fallacies": [{"type": "appeal_to_fear"}],
                "confidence_score": 0.5,
            }
        ]
        result = analyze_agent_effectiveness(corpus)
        types = result["fallacy_detection_by_agent"]["A"]["fallacy_types_summary"]
        assert "appeal_to_fear" in types

    def test_fallacy_type_unknown_fallback(self):
        """Falls back to 'unknown' when neither fallacy_type nor type is present."""
        corpus = [
            {
                "agent_name": "A",
                "fallacies": [{"description": "some fallacy"}],
                "confidence_score": 0.5,
            }
        ]
        result = analyze_agent_effectiveness(corpus)
        types = result["fallacy_detection_by_agent"]["A"]["fallacy_types_summary"]
        assert "unknown" in types
