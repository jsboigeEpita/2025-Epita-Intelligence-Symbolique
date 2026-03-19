# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.agents.tools.analysis.new.argument_coherence_evaluator
Covers ArgumentCoherenceEvaluator: init, evaluate_coherence, individual evaluations,
overall calculation, recommendations.
"""

import pytest
from unittest.mock import patch, MagicMock

from argumentation_analysis.agents.tools.analysis.new.argument_coherence_evaluator import (
    ArgumentCoherenceEvaluator,
)


@pytest.fixture
def evaluator():
    ev = ArgumentCoherenceEvaluator()
    # Mock semantic_analyzer.analyze_multiple_arguments which doesn't exist
    ev.semantic_analyzer.analyze_multiple_arguments = MagicMock(return_value={})
    return ev


SAMPLE_ARGS = [
    "La technologie améliore notre productivité.",
    "Les outils numériques facilitent la collaboration.",
    "La surcharge d'informations réduit la concentration.",
]


# ============================================================
# Initialization
# ============================================================


class TestInit:
    def test_creates_instance(self, evaluator):
        assert isinstance(evaluator, ArgumentCoherenceEvaluator)

    def test_has_coherence_types(self, evaluator):
        assert "logique" in evaluator.coherence_types
        assert "thématique" in evaluator.coherence_types
        assert "structurelle" in evaluator.coherence_types
        assert "rhétorique" in evaluator.coherence_types
        assert "épistémique" in evaluator.coherence_types

    def test_coherence_types_have_importance(self, evaluator):
        for name, ct in evaluator.coherence_types.items():
            assert "importance" in ct
            assert 0.0 <= ct["importance"] <= 1.0

    def test_importance_sums_to_one(self, evaluator):
        total = sum(ct["importance"] for ct in evaluator.coherence_types.values())
        assert abs(total - 1.0) < 0.01

    def test_has_semantic_analyzer(self, evaluator):
        assert evaluator.semantic_analyzer is not None


# ============================================================
# evaluate_coherence (integration)
# ============================================================


class TestEvaluateCoherence:
    def test_returns_dict(self, evaluator):
        result = evaluator.evaluate_coherence(SAMPLE_ARGS)
        assert isinstance(result, dict)

    def test_has_overall_coherence(self, evaluator):
        result = evaluator.evaluate_coherence(SAMPLE_ARGS)
        assert "overall_coherence" in result
        assert "score" in result["overall_coherence"]
        assert "level" in result["overall_coherence"]

    def test_has_coherence_evaluations(self, evaluator):
        result = evaluator.evaluate_coherence(SAMPLE_ARGS)
        assert "coherence_evaluations" in result
        evals = result["coherence_evaluations"]
        assert "logique" in evals
        assert "thématique" in evals
        assert "structurelle" in evals
        assert "rhétorique" in evals
        assert "épistémique" in evals

    def test_has_recommendations(self, evaluator):
        result = evaluator.evaluate_coherence(SAMPLE_ARGS)
        assert "recommendations" in result
        assert isinstance(result["recommendations"], list)

    def test_has_timestamp(self, evaluator):
        result = evaluator.evaluate_coherence(SAMPLE_ARGS)
        assert "timestamp" in result

    def test_uses_provided_context(self, evaluator):
        result = evaluator.evaluate_coherence(SAMPLE_ARGS, context="Mon contexte")
        assert result["context"] == "Mon contexte"

    def test_default_context(self, evaluator):
        result = evaluator.evaluate_coherence(SAMPLE_ARGS)
        assert result["context"] == "Analyse d'arguments"

    def test_empty_context_gets_default(self, evaluator):
        result = evaluator.evaluate_coherence(SAMPLE_ARGS, context="")
        assert result["context"] == "Analyse d'arguments"


# ============================================================
# Individual coherence evaluations (simulated)
# ============================================================


class TestIndividualEvaluations:
    def test_logical_coherence_structure(self, evaluator):
        result = evaluator._evaluate_logical_coherence(SAMPLE_ARGS, {})
        assert "score" in result
        assert "level" in result
        assert "criteria_scores" in result
        assert "importance" in result

    def test_logical_coherence_criteria(self, evaluator):
        result = evaluator._evaluate_logical_coherence(SAMPLE_ARGS, {})
        assert "absence_contradictions" in result["criteria_scores"]
        assert "validite_inferences" in result["criteria_scores"]

    def test_thematic_coherence_structure(self, evaluator):
        result = evaluator._evaluate_thematic_coherence(SAMPLE_ARGS, {})
        assert "score" in result
        assert "criteria_scores" in result
        assert "unite_thematique" in result["criteria_scores"]

    def test_structural_coherence_structure(self, evaluator):
        result = evaluator._evaluate_structural_coherence(SAMPLE_ARGS, {})
        assert "score" in result
        assert "criteria_scores" in result
        assert "organisation_hierarchique" in result["criteria_scores"]

    def test_rhetorical_coherence_structure(self, evaluator):
        result = evaluator._evaluate_rhetorical_coherence(SAMPLE_ARGS, {})
        assert "score" in result
        assert "criteria_scores" in result
        assert "coherence_style" in result["criteria_scores"]

    def test_epistemic_coherence_structure(self, evaluator):
        result = evaluator._evaluate_epistemic_coherence(SAMPLE_ARGS, {})
        assert "score" in result
        assert "criteria_scores" in result
        assert "coherence_standards_preuve" in result["criteria_scores"]

    def test_all_scores_in_range(self, evaluator):
        for method in [
            evaluator._evaluate_logical_coherence,
            evaluator._evaluate_thematic_coherence,
            evaluator._evaluate_structural_coherence,
            evaluator._evaluate_rhetorical_coherence,
            evaluator._evaluate_epistemic_coherence,
        ]:
            result = method(SAMPLE_ARGS, {})
            assert 0.0 <= result["score"] <= 1.0


# ============================================================
# _calculate_overall_coherence
# ============================================================


class TestCalculateOverallCoherence:
    def test_returns_score_and_level(self, evaluator):
        evals = {
            "logique": {"score": 0.8},
            "thématique": {"score": 0.7},
            "structurelle": {"score": 0.6},
            "rhétorique": {"score": 0.7},
            "épistémique": {"score": 0.6},
        }
        result = evaluator._calculate_overall_coherence(evals)
        assert "score" in result
        assert "level" in result

    def test_score_in_range(self, evaluator):
        evals = {
            "logique": {"score": 0.5},
            "thématique": {"score": 0.5},
            "structurelle": {"score": 0.5},
            "rhétorique": {"score": 0.5},
            "épistémique": {"score": 0.5},
        }
        result = evaluator._calculate_overall_coherence(evals)
        assert 0.0 <= result["score"] <= 1.0

    def test_excellent_level(self, evaluator):
        evals = {k: {"score": 0.9} for k in evaluator.coherence_types}
        result = evaluator._calculate_overall_coherence(evals)
        assert result["level"] == "Excellent"

    def test_bon_level(self, evaluator):
        evals = {k: {"score": 0.7} for k in evaluator.coherence_types}
        result = evaluator._calculate_overall_coherence(evals)
        assert result["level"] == "Bon"

    def test_moyen_level(self, evaluator):
        evals = {k: {"score": 0.5} for k in evaluator.coherence_types}
        result = evaluator._calculate_overall_coherence(evals)
        assert result["level"] == "Moyen"

    def test_faible_level(self, evaluator):
        evals = {k: {"score": 0.3} for k in evaluator.coherence_types}
        result = evaluator._calculate_overall_coherence(evals)
        assert result["level"] == "Faible"

    def test_tres_faible_level(self, evaluator):
        evals = {k: {"score": 0.1} for k in evaluator.coherence_types}
        result = evaluator._calculate_overall_coherence(evals)
        assert result["level"] == "Très faible"

    def test_strengths_for_high_scores(self, evaluator):
        evals = {k: {"score": 0.9} for k in evaluator.coherence_types}
        result = evaluator._calculate_overall_coherence(evals)
        assert len(result["strengths"]) > 0

    def test_weaknesses_for_low_scores(self, evaluator):
        evals = {k: {"score": 0.3} for k in evaluator.coherence_types}
        result = evaluator._calculate_overall_coherence(evals)
        assert len(result["weaknesses"]) > 0


# ============================================================
# _generate_recommendations
# ============================================================


class TestGenerateRecommendations:
    def test_returns_list(self, evaluator):
        evals = {k: {"score": 0.7} for k in evaluator.coherence_types}
        overall = {"level": "Bon", "weaknesses": []}
        recs = evaluator._generate_recommendations(SAMPLE_ARGS, evals, overall)
        assert isinstance(recs, list)

    def test_excellent_recommendation(self, evaluator):
        evals = {k: {"score": 0.9} for k in evaluator.coherence_types}
        overall = {"level": "Excellent", "weaknesses": []}
        recs = evaluator._generate_recommendations(SAMPLE_ARGS, evals, overall)
        assert any("excellente" in r.lower() for r in recs)

    def test_faible_recommendation(self, evaluator):
        evals = {k: {"score": 0.3} for k in evaluator.coherence_types}
        overall = {"level": "Faible", "weaknesses": []}
        recs = evaluator._generate_recommendations(SAMPLE_ARGS, evals, overall)
        assert any("restructuration" in r.lower() for r in recs)

    def test_weakness_recommendations(self, evaluator):
        evals = {k: {"score": 0.5} for k in evaluator.coherence_types}
        overall = {
            "level": "Moyen",
            "weaknesses": ["Faible cohérence logique (0.30)"],
        }
        recs = evaluator._generate_recommendations(SAMPLE_ARGS, evals, overall)
        assert any("logique" in r.lower() for r in recs)

    def test_few_arguments_recommendation(self, evaluator):
        evals = {k: {"score": 0.7} for k in evaluator.coherence_types}
        overall = {"level": "Bon", "weaknesses": []}
        recs = evaluator._generate_recommendations(["arg1", "arg2"], evals, overall)
        assert any(
            "davantage" in r.lower() or "supplémentaires" in r.lower() for r in recs
        )

    def test_many_arguments_recommendation(self, evaluator):
        evals = {k: {"score": 0.7} for k in evaluator.coherence_types}
        overall = {"level": "Bon", "weaknesses": []}
        many_args = [f"arg{i}" for i in range(10)]
        recs = evaluator._generate_recommendations(many_args, evals, overall)
        assert any("consolidation" in r.lower() or "concise" in r.lower() for r in recs)
