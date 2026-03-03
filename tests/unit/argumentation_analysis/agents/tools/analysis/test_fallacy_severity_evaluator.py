# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.agents.tools.analysis.fallacy_severity_evaluator
Covers FallacySeverityEvaluator: severity config, evaluate_severity, visibility,
impact, severity levels, explanations, rank_fallacies, evaluate_impact, corrections.
"""

import pytest
from argumentation_analysis.agents.tools.analysis.fallacy_severity_evaluator import (
    _load_severity_config,
    FallacySeverityEvaluator,
)


# ============================================================
# _load_severity_config
# ============================================================

class TestLoadSeverityConfig:
    def test_returns_dict(self):
        config = _load_severity_config()
        assert isinstance(config, dict)

    def test_has_base_severity(self):
        config = _load_severity_config()
        assert "base_severity" in config
        assert len(config["base_severity"]) == 15

    def test_has_context_modifiers(self):
        config = _load_severity_config()
        assert "context_modifiers" in config
        assert set(config["context_modifiers"].keys()) == {
            "politique", "scientifique", "commercial", "juridique", "académique"
        }

    def test_base_severity_values_in_range(self):
        config = _load_severity_config()
        for name, val in config["base_severity"].items():
            assert 0.0 <= val <= 1.0, f"{name} has invalid severity {val}"

    def test_context_modifier_values_in_range(self):
        config = _load_severity_config()
        for ctx, mods in config["context_modifiers"].items():
            for name, val in mods.items():
                assert 0.0 <= val <= 1.0, f"{ctx}/{name} has invalid modifier {val}"


# ============================================================
# FallacySeverityEvaluator.__init__
# ============================================================

class TestEvaluatorInit:
    def test_creates_instance(self):
        evaluator = FallacySeverityEvaluator()
        assert evaluator is not None

    def test_has_base_severity(self):
        evaluator = FallacySeverityEvaluator()
        assert len(evaluator.base_severity) == 15

    def test_has_context_modifiers(self):
        evaluator = FallacySeverityEvaluator()
        assert "politique" in evaluator.context_modifiers


# ============================================================
# _determine_context_type
# ============================================================

class TestDetermineContextType:
    @pytest.fixture
    def evaluator(self):
        return FallacySeverityEvaluator()

    def test_politique(self, evaluator):
        assert evaluator._determine_context_type("discours politique") == "politique"

    def test_politique_election(self, evaluator):
        assert evaluator._determine_context_type("campagne d'élection") == "politique"

    def test_scientifique(self, evaluator):
        assert evaluator._determine_context_type("article scientifique") == "scientifique"

    def test_scientifique_recherche(self, evaluator):
        assert evaluator._determine_context_type("résultat de recherche") == "scientifique"

    def test_commercial(self, evaluator):
        assert evaluator._determine_context_type("publicité télévisée") == "commercial"

    def test_juridique(self, evaluator):
        assert evaluator._determine_context_type("contexte juridique") == "juridique"

    def test_juridique_tribunal(self, evaluator):
        assert evaluator._determine_context_type("audience au tribunal") == "juridique"

    def test_academique(self, evaluator):
        assert evaluator._determine_context_type("débat académique") == "académique"

    def test_general_fallback(self, evaluator):
        assert evaluator._determine_context_type("conversation informelle") == "général"

    def test_case_insensitive(self, evaluator):
        assert evaluator._determine_context_type("POLITIQUE nationale") == "politique"


# ============================================================
# _calculate_visibility
# ============================================================

class TestCalculateVisibility:
    @pytest.fixture
    def evaluator(self):
        return FallacySeverityEvaluator()

    def test_known_fallacy_with_keywords(self, evaluator):
        score = evaluator._calculate_visibility(
            "Appel à l'autorité",
            "Les experts sont unanimes que cette étude prouve tout."
        )
        assert 0.0 <= score <= 1.0
        assert score > 0.0  # Should find keywords

    def test_known_fallacy_no_keywords(self, evaluator):
        score = evaluator._calculate_visibility(
            "Appel à l'autorité",
            "Le ciel est bleu."
        )
        assert score == 0.0

    def test_unknown_fallacy_returns_default(self, evaluator):
        score = evaluator._calculate_visibility("Sophisme inconnu XYZ", "texte")
        assert score == 0.5

    def test_all_keywords_max_score(self, evaluator):
        score = evaluator._calculate_visibility(
            "Faux dilemme",
            "soit on choisit ou bien l'alternative unique, uniquement ce choix"
        )
        assert score == 1.0


# ============================================================
# _calculate_impact
# ============================================================

class TestCalculateImpact:
    @pytest.fixture
    def evaluator(self):
        return FallacySeverityEvaluator()

    def test_known_fallacy(self, evaluator):
        score = evaluator._calculate_impact("Ad hominem", "Tu es un menteur.")
        assert 0.0 <= score <= 1.0

    def test_unknown_fallacy_default(self, evaluator):
        score = evaluator._calculate_impact("Inconnu", "argument")
        assert score == 0.5

    def test_short_argument_higher_impact(self, evaluator):
        short_score = evaluator._calculate_impact("Faux dilemme", "court")
        long_score = evaluator._calculate_impact("Faux dilemme", "x" * 2000)
        assert short_score >= long_score

    def test_impact_capped_at_one(self, evaluator):
        score = evaluator._calculate_impact("Ad hominem", "x")
        assert score <= 1.0


# ============================================================
# _determine_severity_level
# ============================================================

class TestDetermineSeverityLevel:
    @pytest.fixture
    def evaluator(self):
        return FallacySeverityEvaluator()

    def test_faible(self, evaluator):
        assert evaluator._determine_severity_level(0.1) == "Faible"
        assert evaluator._determine_severity_level(0.29) == "Faible"

    def test_modere(self, evaluator):
        assert evaluator._determine_severity_level(0.3) == "Modéré"
        assert evaluator._determine_severity_level(0.59) == "Modéré"

    def test_eleve(self, evaluator):
        assert evaluator._determine_severity_level(0.6) == "Élevé"
        assert evaluator._determine_severity_level(0.79) == "Élevé"

    def test_critique(self, evaluator):
        assert evaluator._determine_severity_level(0.8) == "Critique"
        assert evaluator._determine_severity_level(1.0) == "Critique"

    def test_boundary_zero(self, evaluator):
        assert evaluator._determine_severity_level(0.0) == "Faible"


# ============================================================
# _generate_explanation
# ============================================================

class TestGenerateExplanation:
    @pytest.fixture
    def evaluator(self):
        return FallacySeverityEvaluator()

    def test_contains_fallacy_type(self, evaluator):
        expl = evaluator._generate_explanation("Ad hominem", "politique", 0.9)
        assert "Ad hominem" in expl
        assert "politique" in expl

    def test_faible_explanation(self, evaluator):
        expl = evaluator._generate_explanation("Test", "général", 0.1)
        assert "impact limité" in expl

    def test_critique_explanation(self, evaluator):
        expl = evaluator._generate_explanation("Test", "général", 0.9)
        assert "invalide complètement" in expl


# ============================================================
# evaluate_severity (integration)
# ============================================================

class TestEvaluateSeverity:
    @pytest.fixture
    def evaluator(self):
        return FallacySeverityEvaluator()

    def test_returns_dict_with_expected_keys(self, evaluator):
        result = evaluator.evaluate_severity(
            "Appel à l'autorité",
            "Les experts sont unanimes.",
            "discours politique"
        )
        expected_keys = {
            "fallacy_type", "context_type", "base_score", "context_modifier",
            "visibility_score", "impact_score", "final_score",
            "severity_level", "explanation"
        }
        assert expected_keys == set(result.keys())

    def test_final_score_in_range(self, evaluator):
        result = evaluator.evaluate_severity(
            "Faux dilemme", "Soit A soit B.", "contexte juridique"
        )
        assert 0.0 <= result["final_score"] <= 1.0

    def test_context_modifier_applied(self, evaluator):
        result = evaluator.evaluate_severity(
            "Appel à l'émotion",
            "Pensez aux enfants !",
            "discours politique"
        )
        assert result["context_modifier"] == 0.3  # politique -> Appel à l'émotion = 0.3

    def test_unknown_fallacy_uses_default_base(self, evaluator):
        result = evaluator.evaluate_severity(
            "Sophisme inexistant", "arg", "général"
        )
        assert result["base_score"] == 0.5

    def test_general_context_no_modifier(self, evaluator):
        result = evaluator.evaluate_severity(
            "Ad hominem", "Tu es nul.", "conversation informelle"
        )
        assert result["context_modifier"] == 0.0

    def test_severity_level_matches_score(self, evaluator):
        result = evaluator.evaluate_severity(
            "Ad hominem", "Tu es un menteur.", "contexte juridique"
        )
        score = result["final_score"]
        level = result["severity_level"]
        if score < 0.3:
            assert level == "Faible"
        elif score < 0.6:
            assert level == "Modéré"
        elif score < 0.8:
            assert level == "Élevé"
        else:
            assert level == "Critique"


# ============================================================
# rank_fallacies
# ============================================================

class TestRankFallacies:
    @pytest.fixture
    def evaluator(self):
        return FallacySeverityEvaluator()

    def test_sorts_by_severity_descending(self, evaluator):
        fallacies = [
            {"fallacy_type": "Appel à la tradition", "argument": "C'est la tradition.", "context": "général"},
            {"fallacy_type": "Ad hominem", "argument": "Tu es un menteur.", "context": "politique"},
        ]
        ranked = evaluator.rank_fallacies(fallacies)
        assert ranked[0]["severity"] >= ranked[1]["severity"]

    def test_preserves_existing_severity(self, evaluator):
        fallacies = [
            {"fallacy_type": "Test", "severity": 0.99, "severity_level": "Critique"},
        ]
        ranked = evaluator.rank_fallacies(fallacies)
        assert ranked[0]["severity"] == 0.99

    def test_uses_base_severity_when_no_context(self, evaluator):
        fallacies = [
            {"fallacy_type": "Ad hominem"},
        ]
        ranked = evaluator.rank_fallacies(fallacies)
        assert ranked[0]["severity"] == 0.9  # base severity for Ad hominem

    def test_empty_list(self, evaluator):
        ranked = evaluator.rank_fallacies([])
        assert ranked == []

    def test_unknown_fallacy_gets_default_severity(self, evaluator):
        fallacies = [
            {"fallacy_type": "Inconnu XYZ"},
        ]
        ranked = evaluator.rank_fallacies(fallacies)
        assert ranked[0]["severity"] == 0.5


# ============================================================
# evaluate_impact
# ============================================================

class TestEvaluateImpact:
    @pytest.fixture
    def evaluator(self):
        return FallacySeverityEvaluator()

    def test_returns_expected_keys(self, evaluator):
        result = evaluator.evaluate_impact(
            "Faux dilemme", "Soit A, soit B.", "juridique"
        )
        expected_keys = {
            "fallacy_type", "severity", "severity_level",
            "explanation", "impact_on_validity", "correction_suggestions"
        }
        assert expected_keys == set(result.keys())

    def test_correction_suggestions_not_empty(self, evaluator):
        result = evaluator.evaluate_impact(
            "Ad hominem", "Tu es nul.", "politique"
        )
        assert len(result["correction_suggestions"]) > 0


# ============================================================
# _calculate_validity_impact
# ============================================================

class TestCalculateValidityImpact:
    @pytest.fixture
    def evaluator(self):
        return FallacySeverityEvaluator()

    def test_low_severity(self, evaluator):
        assert "reste globalement valide" in evaluator._calculate_validity_impact(0.1)

    def test_medium_severity(self, evaluator):
        assert "partiellement affaibli" in evaluator._calculate_validity_impact(0.4)

    def test_high_severity(self, evaluator):
        assert "significativement affaibli" in evaluator._calculate_validity_impact(0.7)

    def test_critical_severity(self, evaluator):
        assert "invalidé" in evaluator._calculate_validity_impact(0.9)


# ============================================================
# _generate_correction_suggestions
# ============================================================

class TestGenerateCorrectionSuggestions:
    @pytest.fixture
    def evaluator(self):
        return FallacySeverityEvaluator()

    def test_known_fallacy_specific_suggestions(self, evaluator):
        suggestions = evaluator._generate_correction_suggestions(
            "Appel à l'autorité", "Les experts disent..."
        )
        assert len(suggestions) == 3
        assert any("preuves" in s for s in suggestions)

    def test_unknown_fallacy_generic_suggestions(self, evaluator):
        suggestions = evaluator._generate_correction_suggestions(
            "Inconnu XYZ", "arg"
        )
        assert len(suggestions) == 3
        assert any("preuves objectives" in s for s in suggestions)

    def test_faux_dilemme_suggestions(self, evaluator):
        suggestions = evaluator._generate_correction_suggestions(
            "Faux dilemme", "Soit A soit B."
        )
        assert any("alternatives" in s for s in suggestions)

    def test_ad_hominem_suggestions(self, evaluator):
        suggestions = evaluator._generate_correction_suggestions(
            "Ad hominem", "Tu es nul."
        )
        assert any("arguments" in s.lower() for s in suggestions)
