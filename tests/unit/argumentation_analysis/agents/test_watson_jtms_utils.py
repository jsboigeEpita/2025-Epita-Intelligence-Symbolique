"""
Tests for agents/watson_jtms/utils.py.

Covers pure utility functions used by the Watson JTMS agent:
logical structure extraction, hypothesis analysis, similarity,
conflict resolution, validation recommendations, etc.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock

from argumentation_analysis.agents.watson_jtms.utils import (
    _extract_logical_structure,
    _analyze_hypothesis_strengths_weaknesses,
    _calculate_overall_assessment,
    _analyze_justification_gaps,
    _generate_contextual_alternatives,
    _suggest_belief_strengthening,
    _generate_contradictory_tests,
    _resolve_single_conflict,
    _apply_conflict_resolutions,
    _analyze_logical_soundness,
    _generate_validation_recommendations,
    _assess_overall_validity,
    _build_logical_chains,
    _generate_final_assessment,
    _validate_logical_step,
    _calculate_text_similarity,
    _analyze_hypothesis_consistency,
)

# =============================================================================
# _extract_logical_structure
# =============================================================================


class TestExtractLogicalStructure:
    def test_conditional(self):
        result = _extract_logical_structure("Si il pleut alors la route est mouillée")
        assert result["type"] == "conditional"
        assert "implication" in result["logical_operators"]

    def test_conjunctive(self):
        result = _extract_logical_structure(
            "Le soleil brille et la température est élevée"
        )
        assert result["type"] == "conjunctive"

    def test_disjunctive(self):
        result = _extract_logical_structure("On va au parc ou à la plage")
        assert result["type"] == "disjunctive"

    def test_atomic(self):
        result = _extract_logical_structure("Le chat est noir")
        assert result["type"] == "atomic"

    def test_empty_text(self):
        result = _extract_logical_structure("")
        assert result["type"] == "atomic"


# =============================================================================
# _analyze_hypothesis_strengths_weaknesses
# =============================================================================


class TestAnalyzeHypothesisStrengthsWeaknesses:
    def test_high_confidence_strength(self):
        result = _analyze_hypothesis_strengths_weaknesses({"confidence": 0.9})
        assert "Haute confiance initiale" in result["strengths"]

    def test_low_confidence_weakness(self):
        result = _analyze_hypothesis_strengths_weaknesses({"confidence": 0.3})
        assert "Confiance insuffisante" in result["weaknesses"]

    def test_multiple_evidence_strength(self):
        result = _analyze_hypothesis_strengths_weaknesses(
            {
                "confidence": 0.5,
                "supporting_evidence": ["e1", "e2", "e3"],
            }
        )
        assert "Multiples évidences de support" in result["strengths"]

    def test_no_evidence_critical(self):
        result = _analyze_hypothesis_strengths_weaknesses(
            {
                "confidence": 0.3,
                "supporting_evidence": [],
            }
        )
        assert "Aucune évidence de support" in result["critical_issues"]

    def test_default_values(self):
        result = _analyze_hypothesis_strengths_weaknesses({})
        assert isinstance(result["strengths"], list)
        assert isinstance(result["weaknesses"], list)


# =============================================================================
# _calculate_overall_assessment
# =============================================================================


class TestCalculateOverallAssessment:
    def test_valid_strong(self):
        critique = {
            "consistency_check": {"consistent": True},
            "formal_validation": {"provable": True, "confidence": 0.9},
            "critical_issues": [],
        }
        result = _calculate_overall_assessment(critique)
        assert result["assessment"] == "valid_strong"

    def test_invalid(self):
        critique = {
            "consistency_check": {"consistent": False},
            "formal_validation": {"provable": False, "confidence": 0.0},
            "critical_issues": ["issue1", "issue2", "issue3", "issue4", "issue5"],
        }
        result = _calculate_overall_assessment(critique)
        assert result["assessment"] == "invalid"

    def test_questionable(self):
        critique = {
            "consistency_check": {"consistent": False},
            "formal_validation": {"provable": True, "confidence": 0.6},
            "critical_issues": ["issue1"],
        }
        result = _calculate_overall_assessment(critique)
        assert result["assessment"] in ("questionable", "valid_moderate")


# =============================================================================
# _calculate_text_similarity
# =============================================================================


class TestCalculateTextSimilarity:
    def test_identical_texts(self):
        s = _calculate_text_similarity("hello world", "hello world")
        assert s == 1.0

    def test_no_overlap(self):
        s = _calculate_text_similarity("hello", "world")
        assert s == 0.0

    def test_partial_overlap(self):
        s = _calculate_text_similarity("hello world", "hello there")
        assert 0.0 < s < 1.0

    def test_empty_text(self):
        assert _calculate_text_similarity("", "hello") == 0.0
        assert _calculate_text_similarity("hello", "") == 0.0
        assert _calculate_text_similarity("", "") == 0.0

    def test_contradiction_detection(self):
        s = _calculate_text_similarity("c'est vrai", "c'est faux")
        assert s < 0  # Contradiction detected

    def test_case_insensitive(self):
        s = _calculate_text_similarity("Hello", "hello")
        assert s == 1.0


# =============================================================================
# _validate_logical_step
# =============================================================================


class TestValidateLogicalStep:
    def test_valid_step(self):
        assert _validate_logical_step(["p1", "p2"], "conclusion") is True

    def test_no_premises(self):
        assert _validate_logical_step([], "conclusion") is False

    def test_no_conclusion(self):
        assert _validate_logical_step(["p1"], None) is False


# =============================================================================
# _generate_contradictory_tests
# =============================================================================


class TestGenerateContradictoryTests:
    def test_generates_test(self):
        tests = _generate_contradictory_tests("belief_a")
        assert len(tests) == 1
        assert tests[0]["type"] == "contradictory_test"
        assert "not_belief_a" in tests[0]["description"]


# =============================================================================
# _generate_final_assessment
# =============================================================================


class TestGenerateFinalAssessment:
    def test_excellent(self):
        result = _generate_final_assessment(
            {
                "high_confidence_conclusions": ["a", "b", "c"],
                "validated_beliefs": ["a", "b", "c"],
            }
        )
        assert result["assessment_level"] == "excellent"
        assert result["quality_score"] == 1.0

    def test_poor(self):
        result = _generate_final_assessment(
            {
                "high_confidence_conclusions": [],
                "validated_beliefs": ["a", "b", "c", "d"],
            }
        )
        assert result["assessment_level"] == "poor"

    def test_empty(self):
        result = _generate_final_assessment(
            {
                "high_confidence_conclusions": [],
                "validated_beliefs": [],
            }
        )
        assert result["quality_score"] == 0.0


# =============================================================================
# Async functions
# =============================================================================


class TestAsyncUtils:
    async def test_analyze_justification_gaps_unknown_belief(self):
        gaps = await _analyze_justification_gaps("unknown", {})
        assert gaps == []

    async def test_analyze_justification_gaps_no_justifications(self):
        belief = MagicMock()
        belief.justifications = []
        gaps = await _analyze_justification_gaps("b", {"b": belief})
        assert len(gaps) == 1
        assert gaps[0]["type"] == "missing_justification"

    async def test_analyze_justification_gaps_weak(self):
        justification = MagicMock()
        justification.in_list = []
        belief = MagicMock()
        belief.justifications = [justification]
        gaps = await _analyze_justification_gaps("b", {"b": belief})
        assert any(g["type"] == "weak_justification" for g in gaps)

    async def test_generate_contextual_alternatives_investigation(self):
        alts = await _generate_contextual_alternatives("b", {"type": "investigation"})
        assert len(alts) == 1
        assert alts[0]["type"] == "alternative_hypothesis"

    async def test_generate_contextual_alternatives_unknown(self):
        alts = await _generate_contextual_alternatives("b", {"type": "unknown"})
        assert alts == []

    async def test_analyze_hypothesis_consistency(self):
        def sim_fn(t1, t2):
            return 0.8

        result = await _analyze_hypothesis_consistency(
            {"hypothesis": "test"},
            {"beliefs": {"b1": {"context": {"description": "desc"}}}},
            sim_fn,
        )
        assert result["consistent"] is True
        assert len(result["supportive_beliefs"]) == 1

    async def test_analyze_hypothesis_consistency_contradiction(self):
        def sim_fn(t1, t2):
            return -0.5

        result = await _analyze_hypothesis_consistency(
            {"hypothesis": "test"},
            {"beliefs": {"b1": {"context": {"description": "desc"}}}},
            sim_fn,
        )
        assert result["consistent"] is False
        assert len(result["contradictory_beliefs"]) == 1

    async def test_analyze_logical_soundness_clean(self):
        result = await _analyze_logical_soundness({})
        assert result["sound"] is True

    async def test_analyze_logical_soundness_circular(self):
        beliefs = {
            "a": {"justifications": [{"in_list": ["a"]}]},
        }
        result = await _analyze_logical_soundness(beliefs)
        assert result["sound"] is False
        assert "a" in result["circular_reasoning"]

    async def test_resolve_conflict_confidence_based(self):
        b1 = MagicMock(confidence=0.9)
        b2 = MagicMock(confidence=0.3)
        conflict = {"beliefs": ["b1", "b2"]}

        resolution = await _resolve_single_conflict(
            conflict, 0, {"b1": b1, "b2": b2}, MagicMock
        )
        assert resolution is not None


class TestSuggestBeliefStrengthening:
    def test_low_confidence_suggestion(self):
        belief = MagicMock(confidence=0.4)
        suggestions = _suggest_belief_strengthening("b", {"b": belief})
        assert len(suggestions) == 1
        assert suggestions[0]["type"] == "strengthen_confidence"

    def test_high_confidence_no_suggestion(self):
        belief = MagicMock(confidence=0.9)
        suggestions = _suggest_belief_strengthening("b", {"b": belief})
        assert len(suggestions) == 0

    def test_unknown_belief(self):
        suggestions = _suggest_belief_strengthening("unknown", {})
        assert suggestions == []


class TestValidationRecommendations:
    def test_with_conflicts(self):
        report = {
            "consistency_analysis": {"conflicts_detected": ["c1"]},
            "beliefs_validated": {},
        }
        recs = _generate_validation_recommendations(report)
        assert any(r["type"] == "resolve_conflicts" for r in recs)

    def test_with_unproven(self):
        report = {
            "consistency_analysis": {"conflicts_detected": []},
            "beliefs_validated": {"b1": {"provable": False}},
        }
        recs = _generate_validation_recommendations(report)
        assert any(r["type"] == "strengthen_proofs" for r in recs)

    def test_all_clean(self):
        report = {
            "consistency_analysis": {"conflicts_detected": []},
            "beliefs_validated": {"b1": {"provable": True}},
        }
        recs = _generate_validation_recommendations(report)
        assert len(recs) == 0


class TestAssessOverallValidity:
    def test_highly_valid(self):
        report = {
            "consistency_analysis": {"is_consistent": True},
            "beliefs_validated": {"b1": {"provable": True}},
            "logical_soundness": {"sound": True},
        }
        result = _assess_overall_validity(report)
        assert result["status"] == "highly_valid"

    def test_invalid(self):
        report = {
            "consistency_analysis": {"is_consistent": False},
            "beliefs_validated": {"b1": {"provable": False}},
            "logical_soundness": {"sound": False},
        }
        result = _assess_overall_validity(report)
        assert result["status"] in ("invalid", "questionable")
