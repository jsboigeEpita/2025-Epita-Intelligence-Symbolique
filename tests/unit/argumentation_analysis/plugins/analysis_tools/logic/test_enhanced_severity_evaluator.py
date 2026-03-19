# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.plugins.analysis_tools.logic.fallacy_severity_evaluator
Covers EnhancedFallacySeverityEvaluator: context impact, severity calculation,
severity levels, overall severity, keyword-based detection.
"""

import pytest

from argumentation_analysis.plugins.analysis_tools.logic.fallacy_severity_evaluator import (
    EnhancedFallacySeverityEvaluator,
)


@pytest.fixture
def evaluator():
    return EnhancedFallacySeverityEvaluator()


# ============================================================
# __init__
# ============================================================


class TestInit:
    def test_creates_instance(self, evaluator):
        assert isinstance(evaluator, EnhancedFallacySeverityEvaluator)

    def test_has_base_severities(self, evaluator):
        assert len(evaluator.fallacy_severity_base) > 0
        assert "Appel à l'autorité" in evaluator.fallacy_severity_base

    def test_has_context_modifiers(self, evaluator):
        assert "académique" in evaluator.context_severity_modifiers
        assert "général" in evaluator.context_severity_modifiers

    def test_has_audience_modifiers(self, evaluator):
        assert "experts" in evaluator.audience_severity_modifiers
        assert "grand public" in evaluator.audience_severity_modifiers

    def test_has_domain_modifiers(self, evaluator):
        assert "santé" in evaluator.domain_severity_modifiers
        assert "général" in evaluator.domain_severity_modifiers


# ============================================================
# _determine_severity_level
# ============================================================


class TestDetermineSeverityLevel:
    def test_low(self, evaluator):
        assert evaluator._determine_severity_level(0.0) == "Faible"
        assert evaluator._determine_severity_level(0.39) == "Faible"

    def test_moderate(self, evaluator):
        assert evaluator._determine_severity_level(0.4) == "Modéré"
        assert evaluator._determine_severity_level(0.69) == "Modéré"

    def test_elevated(self, evaluator):
        assert evaluator._determine_severity_level(0.7) == "Élevé"
        assert evaluator._determine_severity_level(0.89) == "Élevé"

    def test_critical(self, evaluator):
        assert evaluator._determine_severity_level(0.9) == "Critique"
        assert evaluator._determine_severity_level(1.0) == "Critique"


# ============================================================
# _analyze_context_impact
# ============================================================


class TestAnalyzeContextImpact:
    def test_known_context(self, evaluator):
        result = evaluator._analyze_context_impact("académique")
        assert result["context_type"] == "académique"
        assert result["audience_type"] == "experts"
        assert result["domain_type"] == "sciences"
        assert result["context_severity_modifier"] == 0.2

    def test_unknown_context_defaults_to_general(self, evaluator):
        result = evaluator._analyze_context_impact("random_nonsense")
        assert result["context_type"] == "général"
        assert result["context_severity_modifier"] == 0.0

    def test_scientific_context(self, evaluator):
        result = evaluator._analyze_context_impact("scientifique")
        assert result["context_type"] == "scientifique"
        assert result["audience_type"] == "experts"
        assert result["domain_type"] == "sciences"
        assert result["context_severity_modifier"] == 0.3

    def test_commercial_context(self, evaluator):
        result = evaluator._analyze_context_impact("commercial")
        assert result["context_type"] == "commercial"
        assert result["audience_type"] == "grand public"
        assert result["domain_type"] == "finance"

    def test_medical_context(self, evaluator):
        result = evaluator._analyze_context_impact("médical")
        assert result["context_type"] == "médical"
        assert result["domain_type"] == "santé"

    def test_case_insensitive(self, evaluator):
        result = evaluator._analyze_context_impact("Académique")
        assert result["context_type"] == "académique"

    def test_entertainment_has_negative_modifier(self, evaluator):
        result = evaluator._analyze_context_impact("divertissement")
        assert result["context_severity_modifier"] < 0


# ============================================================
# _calculate_fallacy_severity
# ============================================================


class TestCalculateFallacySeverity:
    def test_known_fallacy_general_context(self, evaluator):
        fallacy = {"fallacy_type": "Appel à l'autorité", "context_text": "test"}
        ctx = evaluator._analyze_context_impact("général")
        result = evaluator._calculate_fallacy_severity(fallacy, ctx)
        assert result["fallacy_type"] == "Appel à l'autorité"
        assert result["base_severity"] == 0.6
        assert 0.0 <= result["final_severity"] <= 1.0

    def test_unknown_fallacy_uses_default(self, evaluator):
        fallacy = {"fallacy_type": "Unknown Fallacy", "context_text": "x"}
        ctx = evaluator._analyze_context_impact("général")
        result = evaluator._calculate_fallacy_severity(fallacy, ctx)
        assert result["base_severity"] == 0.5  # default

    def test_high_context_increases_severity(self, evaluator):
        fallacy = {"fallacy_type": "Ad hominem", "context_text": "test"}
        ctx_general = evaluator._analyze_context_impact("général")
        ctx_science = evaluator._analyze_context_impact("scientifique")
        sev_general = evaluator._calculate_fallacy_severity(fallacy, ctx_general)[
            "final_severity"
        ]
        sev_science = evaluator._calculate_fallacy_severity(fallacy, ctx_science)[
            "final_severity"
        ]
        assert sev_science > sev_general

    def test_severity_clamped_to_one(self, evaluator):
        # Appel à la peur (0.8) + médical context (0.3) + pro audience (0.1) + santé domain (0.2) = 1.4 -> clamped to 1.0
        fallacy = {"fallacy_type": "Appel à la peur", "context_text": "risque"}
        ctx = evaluator._analyze_context_impact("médical")
        result = evaluator._calculate_fallacy_severity(fallacy, ctx)
        assert result["final_severity"] <= 1.0

    def test_severity_has_level(self, evaluator):
        fallacy = {"fallacy_type": "Appel à l'autorité", "context_text": "test"}
        ctx = evaluator._analyze_context_impact("général")
        result = evaluator._calculate_fallacy_severity(fallacy, ctx)
        assert result["severity_level"] in ("Faible", "Modéré", "Élevé", "Critique")


# ============================================================
# _calculate_overall_severity
# ============================================================


class TestCalculateOverallSeverity:
    def test_empty_list(self, evaluator):
        severity, level = evaluator._calculate_overall_severity([])
        assert severity == 0.0
        assert level == "Faible"

    def test_single_evaluation(self, evaluator):
        evals = [{"final_severity": 0.5}]
        severity, level = evaluator._calculate_overall_severity(evals)
        # (0.5 * 0.7) + (0.5 * 0.3) = 0.5
        assert abs(severity - 0.5) < 0.01

    def test_multiple_evaluations(self, evaluator):
        evals = [{"final_severity": 0.4}, {"final_severity": 0.8}]
        severity, level = evaluator._calculate_overall_severity(evals)
        # avg = 0.6, max = 0.8 -> (0.6 * 0.7) + (0.8 * 0.3) = 0.42 + 0.24 = 0.66
        assert abs(severity - 0.66) < 0.01

    def test_max_weights_more(self, evaluator):
        evals = [{"final_severity": 0.1}, {"final_severity": 0.9}]
        severity, _ = evaluator._calculate_overall_severity(evals)
        # avg = 0.5, max = 0.9 -> (0.5 * 0.7) + (0.9 * 0.3) = 0.35 + 0.27 = 0.62
        assert severity > 0.5

    def test_overall_clamped(self, evaluator):
        evals = [{"final_severity": 1.0}, {"final_severity": 1.0}]
        severity, _ = evaluator._calculate_overall_severity(evals)
        assert severity <= 1.0


# ============================================================
# evaluate_fallacy_severity (keyword-based detection)
# ============================================================


class TestEvaluateFallacySeverity:
    def test_detects_authority_keyword(self, evaluator):
        result = evaluator.evaluate_fallacy_severity(
            ["Les experts disent que c'est vrai."], "général"
        )
        assert len(result["fallacy_evaluations"]) >= 1
        types = [e["fallacy_type"] for e in result["fallacy_evaluations"]]
        assert "Appel à l'autorité" in types

    def test_detects_popularity_keyword(self, evaluator):
        result = evaluator.evaluate_fallacy_severity(
            ["Des millions de personnes utilisent ce produit."], "général"
        )
        types = [e["fallacy_type"] for e in result["fallacy_evaluations"]]
        assert "Appel à la popularité" in types

    def test_detects_fear_keyword(self, evaluator):
        result = evaluator.evaluate_fallacy_severity(
            ["Le danger est imminent."], "général"
        )
        types = [e["fallacy_type"] for e in result["fallacy_evaluations"]]
        assert "Appel à la peur" in types

    def test_no_keyword_no_detection(self, evaluator):
        result = evaluator.evaluate_fallacy_severity(
            ["Le soleil brille aujourd'hui."], "général"
        )
        assert len(result["fallacy_evaluations"]) == 0
        assert result["overall_severity"] == 0.0

    def test_has_timestamp(self, evaluator):
        result = evaluator.evaluate_fallacy_severity(["test"], "général")
        assert "analysis_timestamp" in result

    def test_context_affects_result(self, evaluator):
        args = ["Les experts affirment que ce résultat est fiable."]
        gen = evaluator.evaluate_fallacy_severity(args, "général")
        sci = evaluator.evaluate_fallacy_severity(args, "scientifique")
        if gen["fallacy_evaluations"] and sci["fallacy_evaluations"]:
            assert (
                sci["fallacy_evaluations"][0]["final_severity"]
                >= gen["fallacy_evaluations"][0]["final_severity"]
            )


# ============================================================
# evaluate_fallacy_list (pre-identified fallacies)
# ============================================================


class TestEvaluateFallacyList:
    def test_empty_list(self, evaluator):
        result = evaluator.evaluate_fallacy_list([], "général")
        assert result["overall_severity"] == 0.0
        assert len(result["fallacy_evaluations"]) == 0

    def test_single_fallacy(self, evaluator):
        fallacies = [{"fallacy_type": "Ad hominem", "context_text": "attack"}]
        result = evaluator.evaluate_fallacy_list(fallacies, "général")
        assert len(result["fallacy_evaluations"]) == 1
        assert result["fallacy_evaluations"][0]["fallacy_type"] == "Ad hominem"

    def test_multiple_fallacies(self, evaluator):
        fallacies = [
            {"fallacy_type": "Ad hominem", "context_text": "attack"},
            {"fallacy_type": "Faux dilemme", "context_text": "choice"},
        ]
        result = evaluator.evaluate_fallacy_list(fallacies, "académique")
        assert len(result["fallacy_evaluations"]) == 2
        assert result["overall_severity"] > 0.0

    def test_context_modifies_score(self, evaluator):
        fallacies = [{"fallacy_type": "Appel à la peur", "context_text": "risk"}]
        gen = evaluator.evaluate_fallacy_list(fallacies, "général")
        med = evaluator.evaluate_fallacy_list(fallacies, "médical")
        assert (
            med["fallacy_evaluations"][0]["final_severity"]
            > gen["fallacy_evaluations"][0]["final_severity"]
        )

    def test_result_structure(self, evaluator):
        result = evaluator.evaluate_fallacy_list(
            [{"fallacy_type": "Ad hominem"}], "général"
        )
        assert "overall_severity" in result
        assert "severity_level" in result
        assert "fallacy_evaluations" in result
        assert "context_analysis" in result
        assert "analysis_timestamp" in result
