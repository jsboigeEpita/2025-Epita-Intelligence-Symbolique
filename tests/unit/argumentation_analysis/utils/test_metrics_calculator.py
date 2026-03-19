# tests/unit/argumentation_analysis/utils/test_metrics_calculator.py
"""Tests for metrics_calculator utility functions."""

import pytest

from argumentation_analysis.utils.metrics_calculator import (
    count_fallacies,
    extract_confidence_scores,
    analyze_contextual_richness,
)

# ── count_fallacies ──


class TestCountFallacies:
    def test_empty_results(self):
        result = count_fallacies([])
        assert result["base_contextual"] == 0
        assert result["advanced_contextual"] == 0
        assert result["advanced_complex"] == 0

    def test_base_contextual_from_argument_results(self):
        results = [
            {
                "contextual_fallacies": {
                    "argument_results": [
                        {"detected_fallacies": ["f1", "f2"]},
                        {"detected_fallacies": ["f3"]},
                    ]
                }
            }
        ]
        counts = count_fallacies(results)
        assert counts["base_contextual"] == 3

    def test_advanced_complex_individual(self):
        results = [
            {
                "complex_fallacies": {
                    "individual_fallacies_count": 5,
                    "basic_combinations": [],
                    "advanced_combinations": [],
                    "fallacy_patterns": [],
                }
            }
        ]
        counts = count_fallacies(results)
        assert counts["advanced_complex"] == 5

    def test_advanced_complex_combinations(self):
        results = [
            {
                "complex_fallacies": {
                    "individual_fallacies_count": 0,
                    "basic_combinations": ["c1", "c2"],
                    "advanced_combinations": ["a1"],
                    "fallacy_patterns": ["p1", "p2", "p3"],
                }
            }
        ]
        counts = count_fallacies(results)
        assert counts["advanced_complex"] == 6

    def test_advanced_contextual_count(self):
        results = [
            {
                "contextual_fallacies": {
                    "contextual_fallacies_count": 7,
                    "argument_results": [],
                }
            }
        ]
        counts = count_fallacies(results)
        assert counts["advanced_contextual"] == 7

    def test_with_analyses_wrapper(self):
        results = [
            {
                "analyses": {
                    "contextual_fallacies": {
                        "argument_results": [
                            {"detected_fallacies": ["f1"]},
                        ],
                        "contextual_fallacies_count": 2,
                    }
                }
            }
        ]
        counts = count_fallacies(results)
        assert counts["base_contextual"] == 1
        assert counts["advanced_contextual"] == 2

    def test_multiple_results(self):
        results = [
            {
                "contextual_fallacies": {
                    "argument_results": [{"detected_fallacies": ["f1"]}]
                }
            },
            {
                "contextual_fallacies": {
                    "argument_results": [{"detected_fallacies": ["f2", "f3"]}]
                }
            },
        ]
        counts = count_fallacies(results)
        assert counts["base_contextual"] == 3

    def test_no_relevant_keys(self):
        results = [{"unrelated": "data"}]
        counts = count_fallacies(results)
        assert counts["base_contextual"] == 0
        assert counts["advanced_complex"] == 0

    def test_non_dict_argument_result_skipped(self):
        results = [
            {
                "contextual_fallacies": {
                    "argument_results": ["not_a_dict", {"detected_fallacies": ["f1"]}]
                }
            }
        ]
        counts = count_fallacies(results)
        assert counts["base_contextual"] == 1

    def test_complex_fallacies_not_dict(self):
        results = [{"complex_fallacies": "not a dict"}]
        counts = count_fallacies(results)
        assert counts["advanced_complex"] == 0


# ── extract_confidence_scores ──


class TestExtractConfidenceScores:
    def test_empty_results(self):
        scores = extract_confidence_scores([])
        assert scores["base_coherence"] == 0.0
        assert scores["advanced_rhetorical"] == 0.0

    def test_base_coherence(self):
        results = [
            {"analyses": {"argument_coherence": {"overall_coherence": {"score": 0.85}}}}
        ]
        scores = extract_confidence_scores(results)
        assert abs(scores["base_coherence"] - 0.85) < 1e-6

    def test_advanced_rhetorical(self):
        results = [
            {
                "analyses": {
                    "rhetorical_results": {
                        "overall_analysis": {"rhetorical_quality": 0.7}
                    }
                }
            }
        ]
        scores = extract_confidence_scores(results)
        assert abs(scores["advanced_rhetorical"] - 0.7) < 1e-6

    def test_advanced_coherence_dict(self):
        results = [
            {
                "analyses": {
                    "rhetorical_results": {
                        "coherence_analysis": {"overall_coherence": {"score": 0.9}}
                    }
                }
            }
        ]
        scores = extract_confidence_scores(results)
        assert abs(scores["advanced_coherence"] - 0.9) < 1e-6

    def test_advanced_coherence_numeric(self):
        results = [
            {
                "analyses": {
                    "rhetorical_results": {
                        "coherence_analysis": {"overall_coherence": 0.75}
                    }
                }
            }
        ]
        scores = extract_confidence_scores(results)
        assert abs(scores["advanced_coherence"] - 0.75) < 1e-6

    def test_advanced_severity(self):
        results = [{"analyses": {"fallacy_severity": {"overall_severity": 0.3}}}]
        scores = extract_confidence_scores(results)
        assert abs(scores["advanced_severity"] - 0.3) < 1e-6

    def test_averaging_multiple(self):
        results = [
            {"analyses": {"argument_coherence": {"overall_coherence": {"score": 0.8}}}},
            {"analyses": {"argument_coherence": {"overall_coherence": {"score": 0.6}}}},
        ]
        scores = extract_confidence_scores(results)
        assert abs(scores["base_coherence"] - 0.7) < 1e-6

    def test_non_dict_analyses_skipped(self):
        results = [{"analyses": "not a dict"}]
        scores = extract_confidence_scores(results)
        assert scores["base_coherence"] == 0.0

    def test_missing_all_keys(self):
        results = [{"analyses": {}}]
        scores = extract_confidence_scores(results)
        assert all(v == 0.0 for v in scores.values())


# ── analyze_contextual_richness ──


class TestAnalyzeContextualRichness:
    def test_empty_results(self):
        scores = analyze_contextual_richness([])
        assert scores["base_contextual"] == 0.0
        assert scores["advanced_contextual"] == 0.0
        assert scores["advanced_rhetorical"] == 0.0

    def test_base_contextual_factors(self):
        results = [
            {
                "analyses": {
                    "contextual_fallacies": {
                        "contextual_factors": {"f1": "v1", "f2": "v2", "f3": "v3"}
                    }
                }
            }
        ]
        scores = analyze_contextual_richness(results)
        assert abs(scores["base_contextual"] - 3.0) < 1e-6

    def test_advanced_contextual_analysis(self):
        results = [
            {
                "analyses": {
                    "contextual_fallacies": {
                        "context_analysis": {
                            "context_type": "political",
                            "context_subtypes": ["s1", "s2"],
                            "audience_characteristics": ["a1"],
                            "formality_level": "formal",
                        }
                    }
                }
            }
        ]
        scores = analyze_contextual_richness(results)
        # 1 (context_type) + 2 (subtypes) + 1 (audience) + 1 (formality) = 5
        assert abs(scores["advanced_contextual"] - 5.0) < 1e-6

    def test_rhetorical_richness(self):
        results = [
            {
                "analyses": {
                    "rhetorical_results": {
                        "overall_analysis": {
                            "main_strengths": ["s1", "s2"],
                            "main_weaknesses": ["w1"],
                            "context_relevance": 0.8,
                        }
                    }
                }
            }
        ]
        scores = analyze_contextual_richness(results)
        # 2 (strengths) + 1 (weaknesses) + 0.8 (relevance) = 3.8
        assert abs(scores["advanced_rhetorical"] - 3.8) < 1e-6

    def test_context_relevance_boolean(self):
        results = [
            {
                "analyses": {
                    "rhetorical_results": {
                        "overall_analysis": {
                            "main_strengths": [],
                            "main_weaknesses": [],
                            "context_relevance": True,
                        }
                    }
                }
            }
        ]
        scores = analyze_contextual_richness(results)
        assert abs(scores["advanced_rhetorical"] - 1.0) < 1e-6

    def test_non_dict_analyses_skipped(self):
        results = [{"analyses": "not a dict"}]
        scores = analyze_contextual_richness(results)
        assert all(v == 0.0 for v in scores.values())

    def test_averaging_multiple_results(self):
        results = [
            {
                "analyses": {
                    "contextual_fallacies": {"contextual_factors": {"f1": "v1"}}
                }
            },
            {
                "analyses": {
                    "contextual_fallacies": {
                        "contextual_factors": {"f1": "v1", "f2": "v2", "f3": "v3"}
                    }
                }
            },
        ]
        scores = analyze_contextual_richness(results)
        # (1 + 3) / 2 = 2.0
        assert abs(scores["base_contextual"] - 2.0) < 1e-6

    def test_empty_context_analysis(self):
        results = [{"analyses": {"contextual_fallacies": {"context_analysis": {}}}}]
        scores = analyze_contextual_richness(results)
        assert abs(scores["advanced_contextual"] - 0.0) < 1e-6
