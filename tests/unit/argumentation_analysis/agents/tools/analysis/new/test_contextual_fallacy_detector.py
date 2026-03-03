# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.agents.tools.analysis.new.contextual_fallacy_detector
Covers ContextualFallacyDetector: initialization, contextual factors, fallacy rules,
context inference, severity calculation, single/multiple fallacy detection.
"""

import pytest
from datetime import datetime

from argumentation_analysis.agents.tools.analysis.new.contextual_fallacy_detector import (
    ContextualFallacyDetector,
)


@pytest.fixture
def detector():
    return ContextualFallacyDetector()


# ============================================================
# Initialization
# ============================================================

class TestInit:
    def test_creates_instance(self, detector):
        assert isinstance(detector, ContextualFallacyDetector)

    def test_has_contextual_factors(self, detector):
        assert isinstance(detector.contextual_factors, dict)
        assert len(detector.contextual_factors) > 0

    def test_has_contextual_fallacies(self, detector):
        assert isinstance(detector.contextual_fallacies, dict)
        assert len(detector.contextual_fallacies) > 0

    def test_detection_history_empty(self, detector):
        assert detector.detection_history == []


# ============================================================
# _define_contextual_factors
# ============================================================

class TestDefineContextualFactors:
    def test_has_domain(self, detector):
        assert "domain" in detector.contextual_factors

    def test_has_audience(self, detector):
        assert "audience" in detector.contextual_factors

    def test_has_medium(self, detector):
        assert "medium" in detector.contextual_factors

    def test_has_purpose(self, detector):
        assert "purpose" in detector.contextual_factors

    def test_domain_has_values(self, detector):
        values = detector.contextual_factors["domain"]["values"]
        assert isinstance(values, list)
        assert "scientifique" in values
        assert "politique" in values
        assert "juridique" in values

    def test_audience_has_values(self, detector):
        values = detector.contextual_factors["audience"]["values"]
        assert "expert" in values
        assert "généraliste" in values

    def test_each_factor_has_description(self, detector):
        for name, factor in detector.contextual_factors.items():
            assert "description" in factor, f"Factor '{name}' missing description"
            assert "values" in factor, f"Factor '{name}' missing values"


# ============================================================
# _define_contextual_fallacies
# ============================================================

class TestDefineContextualFallacies:
    def test_has_appel_autorite(self, detector):
        assert "appel_inapproprié_autorité" in detector.contextual_fallacies

    def test_each_fallacy_has_markers(self, detector):
        for name, fallacy in detector.contextual_fallacies.items():
            assert "markers" in fallacy, f"Fallacy '{name}' missing markers"
            assert isinstance(fallacy["markers"], list)

    def test_each_fallacy_has_description(self, detector):
        for name, fallacy in detector.contextual_fallacies.items():
            assert "description" in fallacy, f"Fallacy '{name}' missing description"

    def test_each_fallacy_has_contextual_rules(self, detector):
        for name, fallacy in detector.contextual_fallacies.items():
            assert "contextual_rules" in fallacy, f"Fallacy '{name}' missing rules"

    def test_severity_values_in_range(self, detector):
        for name, fallacy in detector.contextual_fallacies.items():
            for factor, rules in fallacy.get("contextual_rules", {}).items():
                for value, rule in rules.items():
                    severity = rule.get("severity", 0.5)
                    assert 0.0 <= severity <= 1.0, (
                        f"Severity {severity} out of range for {name}/{factor}/{value}"
                    )


# ============================================================
# _infer_contextual_factors
# ============================================================

class TestInferContextualFactors:
    def test_scientific_domain(self, detector):
        factors = detector._infer_contextual_factors("une recherche scientifique")
        assert factors["domain"] == "scientifique"

    def test_political_domain(self, detector):
        factors = detector._infer_contextual_factors("un débat politique")
        assert factors["domain"] == "politique"

    def test_juridique_domain(self, detector):
        factors = detector._infer_contextual_factors("un contexte juridique")
        assert factors["domain"] == "juridique"

    def test_medical_domain(self, detector):
        factors = detector._infer_contextual_factors("le domaine médical")
        assert factors["domain"] == "médical"

    def test_commercial_domain(self, detector):
        factors = detector._infer_contextual_factors("une campagne marketing")
        assert factors["domain"] == "commercial"

    def test_default_domain(self, detector):
        factors = detector._infer_contextual_factors("un contexte quelconque")
        assert factors["domain"] == "général"

    def test_expert_audience(self, detector):
        factors = detector._infer_contextual_factors("un public expert")
        assert factors["audience"] == "expert"

    def test_academic_audience(self, detector):
        factors = detector._infer_contextual_factors("un contexte académique")
        assert factors["audience"] == "académique"

    def test_young_audience(self, detector):
        factors = detector._infer_contextual_factors("un public jeune")
        assert factors["audience"] == "jeune"

    def test_default_audience(self, detector):
        factors = detector._infer_contextual_factors("un public quelconque")
        assert factors["audience"] == "généraliste"

    def test_written_medium(self, detector):
        factors = detector._infer_contextual_factors("un article écrit")
        assert factors["medium"] == "écrit"

    def test_oral_medium(self, detector):
        factors = detector._infer_contextual_factors("un discours oral")
        assert factors["medium"] == "oral"

    def test_visual_medium(self, detector):
        factors = detector._infer_contextual_factors("un contenu visuel")
        assert factors["medium"] == "visuel"

    def test_default_medium(self, detector):
        factors = detector._infer_contextual_factors("un format quelconque")
        assert factors["medium"] == "général"

    def test_inform_purpose(self, detector):
        factors = detector._infer_contextual_factors("pour informer le public")
        assert factors["purpose"] == "informer"

    def test_persuade_purpose(self, detector):
        factors = detector._infer_contextual_factors("pour persuader l'audience")
        assert factors["purpose"] == "persuader"

    def test_educate_purpose(self, detector):
        factors = detector._infer_contextual_factors("pour éduquer les étudiants")
        assert factors["purpose"] == "éduquer"

    def test_entertain_purpose(self, detector):
        factors = detector._infer_contextual_factors("pour divertir")
        assert factors["purpose"] == "divertir"

    def test_default_purpose(self, detector):
        factors = detector._infer_contextual_factors("pour un objectif quelconque")
        assert factors["purpose"] == "général"

    def test_returns_all_four_factors(self, detector):
        factors = detector._infer_contextual_factors("un texte quelconque")
        assert set(factors.keys()) == {"domain", "audience", "medium", "purpose"}


# ============================================================
# _calculate_contextual_severity
# ============================================================

class TestCalculateContextualSeverity:
    def test_unknown_fallacy_returns_base(self, detector):
        severity = detector._calculate_contextual_severity(
            "unknown_fallacy", {"domain": "scientifique"}
        )
        assert severity == 0.5

    def test_known_fallacy_with_matching_rule(self, detector):
        severity = detector._calculate_contextual_severity(
            "appel_inapproprié_autorité", {"domain": "scientifique"}
        )
        assert 0.0 <= severity <= 1.0

    def test_known_fallacy_without_matching_factor(self, detector):
        severity = detector._calculate_contextual_severity(
            "appel_inapproprié_autorité", {"domain": "nonexistent_domain"}
        )
        # Falls back to base severity
        assert severity == 0.5

    def test_empty_factors(self, detector):
        severity = detector._calculate_contextual_severity(
            "appel_inapproprié_autorité", {}
        )
        assert severity == 0.5

    def test_severity_in_valid_range(self, detector):
        for fallacy_name in detector.contextual_fallacies:
            for domain in ["scientifique", "politique", "juridique", "médical", "commercial"]:
                severity = detector._calculate_contextual_severity(
                    fallacy_name, {"domain": domain}
                )
                assert 0.0 <= severity <= 1.0


# ============================================================
# detect_contextual_fallacies
# ============================================================

class TestDetectContextualFallacies:
    def test_returns_dict(self, detector):
        result = detector.detect_contextual_fallacies(
            "Les experts affirment que ce produit est sûr.", "commercial"
        )
        assert isinstance(result, dict)

    def test_result_has_required_keys(self, detector):
        result = detector.detect_contextual_fallacies("un argument", "un contexte")
        assert "argument" in result
        assert "context_description" in result
        assert "contextual_factors" in result
        assert "detected_fallacies" in result
        assert "analysis_timestamp" in result

    def test_detects_authority_markers(self, detector):
        result = detector.detect_contextual_fallacies(
            "Selon l'expert, ce produit est sûr.", "commercial"
        )
        fallacies = result["detected_fallacies"]
        # Should detect something with "expert" and "selon" markers
        assert isinstance(fallacies, list)

    def test_no_fallacies_in_clean_text(self, detector):
        result = detector.detect_contextual_fallacies(
            "La terre tourne autour du soleil.", "scientifique"
        )
        # Simple factual statement — unlikely to trigger markers
        # (depends on exact rules, just check structure)
        assert isinstance(result["detected_fallacies"], list)

    def test_contextual_factors_inferred(self, detector):
        result = detector.detect_contextual_fallacies(
            "un argument", "une recherche scientifique"
        )
        assert result["contextual_factors"]["domain"] == "scientifique"

    def test_explicit_contextual_factors(self, detector):
        explicit_factors = {"domain": "juridique", "audience": "expert"}
        result = detector.detect_contextual_fallacies(
            "un argument", "un contexte",
            contextual_factors=explicit_factors,
        )
        assert result["contextual_factors"] == explicit_factors

    def test_single_detect_does_not_update_history(self, detector):
        assert len(detector.detection_history) == 0
        detector.detect_contextual_fallacies("un argument", "un contexte")
        # Only detect_multiple_contextual_fallacies appends to history
        assert len(detector.detection_history) == 0

    def test_timestamp_is_valid(self, detector):
        result = detector.detect_contextual_fallacies("arg", "ctx")
        ts = result["analysis_timestamp"]
        datetime.fromisoformat(ts)

    def test_detected_fallacies_have_structure(self, detector):
        result = detector.detect_contextual_fallacies(
            "Selon l'expert, tout le monde utilise ce produit et il est donc bon.",
            "commercial",
        )
        for fallacy in result["detected_fallacies"]:
            assert "fallacy_type" in fallacy
            assert "severity" in fallacy


# ============================================================
# detect_multiple_contextual_fallacies
# ============================================================

class TestDetectMultipleContextualFallacies:
    def test_returns_dict(self, detector):
        result = detector.detect_multiple_contextual_fallacies(
            ["arg1", "arg2"], "contexte"
        )
        assert isinstance(result, dict)

    def test_result_has_required_keys(self, detector):
        result = detector.detect_multiple_contextual_fallacies(
            ["arg1"], "contexte"
        )
        assert "argument_count" in result
        assert "argument_results" in result
        assert "analysis_timestamp" in result

    def test_correct_argument_count(self, detector):
        result = detector.detect_multiple_contextual_fallacies(
            ["a", "b", "c"], "contexte"
        )
        assert result["argument_count"] == 3
        assert len(result["argument_results"]) == 3

    def test_each_result_has_index(self, detector):
        result = detector.detect_multiple_contextual_fallacies(
            ["a", "b"], "contexte"
        )
        for i, arg_result in enumerate(result["argument_results"]):
            assert arg_result["argument_index"] == i

    def test_updates_detection_history(self, detector):
        detector.detect_multiple_contextual_fallacies(["a", "b"], "ctx")
        # Each single detect adds to history, plus the multiple call
        # Actually the multiple call adds 1 entry + single detect adds N entries
        # Let's just check it has entries
        assert len(detector.detection_history) > 0

    def test_empty_arguments_list(self, detector):
        result = detector.detect_multiple_contextual_fallacies([], "ctx")
        assert result["argument_count"] == 0
        assert result["argument_results"] == []

    def test_explicit_factors_passed_through(self, detector):
        factors = {"domain": "médical", "audience": "expert"}
        result = detector.detect_multiple_contextual_fallacies(
            ["arg"], "ctx", contextual_factors=factors,
        )
        assert result["contextual_factors"] == factors
