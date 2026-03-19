"""
Tests unitaires pour les analyseurs de sophismes (agents/tools/analysis/).

Couvre:
- FallacySeverityEvaluator: évaluation de gravité, classement, impact
- ContextualFallacyAnalyzer: détection contextuelle par mots-clés
- ComplexFallacyAnalyzer: combinaisons, structurels, motifs

Issue: #36 (test coverage)
"""

import pytest
from unittest.mock import patch, MagicMock

# ---------------------------------------------------------------------------
# Fixtures to isolate singleton state between tests
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_singletons():
    """Reset ServiceRegistry and ConfigManager caches between tests."""
    from argumentation_analysis.agents.tools.support.shared_services import (
        ServiceRegistry,
        ConfigManager,
    )

    old_services = ServiceRegistry._services.copy()
    old_configs = ConfigManager._configs.copy()
    yield
    ServiceRegistry._services = old_services
    ConfigManager._configs = old_configs


# ========================================================================
# FallacySeverityEvaluator
# ========================================================================


class TestFallacySeverityEvaluator:
    """Tests for FallacySeverityEvaluator."""

    @pytest.fixture
    def evaluator(self):
        from argumentation_analysis.agents.tools.analysis.fallacy_severity_evaluator import (
            FallacySeverityEvaluator,
        )

        return FallacySeverityEvaluator()

    # --- _determine_severity_level ---

    def test_severity_level_faible(self, evaluator):
        assert evaluator._determine_severity_level(0.1) == "Faible"
        assert evaluator._determine_severity_level(0.0) == "Faible"
        assert evaluator._determine_severity_level(0.29) == "Faible"

    def test_severity_level_modere(self, evaluator):
        assert evaluator._determine_severity_level(0.3) == "Modéré"
        assert evaluator._determine_severity_level(0.5) == "Modéré"
        assert evaluator._determine_severity_level(0.59) == "Modéré"

    def test_severity_level_eleve(self, evaluator):
        assert evaluator._determine_severity_level(0.6) == "Élevé"
        assert evaluator._determine_severity_level(0.7) == "Élevé"
        assert evaluator._determine_severity_level(0.79) == "Élevé"

    def test_severity_level_critique(self, evaluator):
        assert evaluator._determine_severity_level(0.8) == "Critique"
        assert evaluator._determine_severity_level(0.9) == "Critique"
        assert evaluator._determine_severity_level(1.0) == "Critique"

    # --- _determine_context_type ---

    def test_context_type_politique(self, evaluator):
        assert evaluator._determine_context_type("discours politique") == "politique"
        assert (
            evaluator._determine_context_type("élection présidentielle") == "politique"
        )

    def test_context_type_scientifique(self, evaluator):
        assert (
            evaluator._determine_context_type("recherche scientifique")
            == "scientifique"
        )
        assert evaluator._determine_context_type("étude clinique") == "scientifique"

    def test_context_type_commercial(self, evaluator):
        assert evaluator._determine_context_type("publicité produit") == "commercial"
        assert evaluator._determine_context_type("marketing digital") == "commercial"

    def test_context_type_juridique(self, evaluator):
        assert evaluator._determine_context_type("procès juridique") == "juridique"
        assert evaluator._determine_context_type("tribunal pénal") == "juridique"

    def test_context_type_academique(self, evaluator):
        assert evaluator._determine_context_type("thèse universitaire") == "académique"

    def test_context_type_general(self, evaluator):
        assert evaluator._determine_context_type("conversation informelle") == "général"
        assert evaluator._determine_context_type("") == "général"

    # --- _calculate_visibility ---

    def test_visibility_known_type_with_keywords(self, evaluator):
        score = evaluator._calculate_visibility(
            "Appel à l'autorité",
            "Les experts unanimes affirment que cette étude scientifique prouve tout.",
        )
        assert 0.0 < score <= 1.0

    def test_visibility_known_type_no_keywords(self, evaluator):
        score = evaluator._calculate_visibility(
            "Appel à l'autorité", "Le chat dort sur le canapé."
        )
        assert score == 0.0

    def test_visibility_unknown_type(self, evaluator):
        score = evaluator._calculate_visibility("Type Inconnu", "N'importe quel texte.")
        assert score == 0.5  # default for unknown types

    # --- _calculate_impact ---

    def test_impact_known_type(self, evaluator):
        score = evaluator._calculate_impact("Ad hominem", "Texte court.")
        assert score > 0.0
        assert score <= 1.0

    def test_impact_unknown_type(self, evaluator):
        score = evaluator._calculate_impact("Type Inconnu", "Un argument quelconque.")
        assert score == 0.5

    def test_impact_long_argument_reduces_modifier(self, evaluator):
        short_score = evaluator._calculate_impact("Ad hominem", "Court.")
        long_score = evaluator._calculate_impact("Ad hominem", "x" * 2000)
        # Long arguments get a smaller length_modifier
        assert long_score <= short_score

    # --- _generate_explanation ---

    def test_generate_explanation_all_levels(self, evaluator):
        for score, level_kw in [
            (0.1, "limité"),
            (0.4, "modéré"),
            (0.7, "important"),
            (0.9, "critique"),
        ]:
            explanation = evaluator._generate_explanation(
                "Ad hominem", "politique", score
            )
            assert isinstance(explanation, str)
            assert len(explanation) > 10

    # --- _calculate_validity_impact ---

    def test_validity_impact_low(self, evaluator):
        result = evaluator._calculate_validity_impact(0.1)
        assert "valide" in result.lower()

    def test_validity_impact_moderate(self, evaluator):
        result = evaluator._calculate_validity_impact(0.4)
        assert "affaibli" in result.lower()

    def test_validity_impact_high(self, evaluator):
        result = evaluator._calculate_validity_impact(0.7)
        assert "significativement" in result.lower()

    def test_validity_impact_critical(self, evaluator):
        result = evaluator._calculate_validity_impact(0.9)
        assert "invalidé" in result.lower()

    # --- _generate_correction_suggestions ---

    def test_correction_suggestions_known_type(self, evaluator):
        suggestions = evaluator._generate_correction_suggestions(
            "Ad hominem", "Vous êtes incompétent."
        )
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0

    def test_correction_suggestions_unknown_type(self, evaluator):
        suggestions = evaluator._generate_correction_suggestions(
            "Type Inconnu", "Texte quelconque."
        )
        assert isinstance(suggestions, list)
        assert len(suggestions) == 3  # generic suggestions

    # --- evaluate_severity (full pipeline) ---

    def test_evaluate_severity_returns_complete_result(self, evaluator):
        result = evaluator.evaluate_severity(
            "Appel à l'autorité",
            "Les experts unanimes confirment cette recherche scientifique.",
            "discours commercial",
        )
        assert "fallacy_type" in result
        assert "context_type" in result
        assert "base_score" in result
        assert "context_modifier" in result
        assert "visibility_score" in result
        assert "impact_score" in result
        assert "final_score" in result
        assert "severity_level" in result
        assert "explanation" in result
        assert result["fallacy_type"] == "Appel à l'autorité"
        assert result["context_type"] == "commercial"
        assert 0.0 <= result["final_score"] <= 1.0

    def test_evaluate_severity_context_modifier_applies(self, evaluator):
        # Political context gives a modifier for Ad hominem
        result_political = evaluator.evaluate_severity(
            "Ad hominem", "Texte.", "politique"
        )
        result_general = evaluator.evaluate_severity(
            "Ad hominem", "Texte.", "conversation informelle"
        )
        # Political context should add modifier, making score higher
        assert result_political["context_modifier"] > result_general["context_modifier"]

    def test_evaluate_severity_score_capped_at_1(self, evaluator):
        # Ad hominem has base 0.9 + political modifier 0.2 + impact + visibility
        result = evaluator.evaluate_severity(
            "Ad hominem",
            "personne caractère intégrité moralité crédibilité",
            "politique",
        )
        assert result["final_score"] <= 1.0

    # --- rank_fallacies ---

    def test_rank_fallacies_sorts_by_severity(self, evaluator):
        fallacies = [
            {"fallacy_type": "Appel à la tradition", "severity": 0.3},
            {"fallacy_type": "Ad hominem", "severity": 0.9},
            {"fallacy_type": "Appel à la popularité", "severity": 0.5},
        ]
        ranked = evaluator.rank_fallacies(fallacies)
        assert ranked[0]["fallacy_type"] == "Ad hominem"
        assert ranked[-1]["fallacy_type"] == "Appel à la tradition"

    def test_rank_fallacies_adds_missing_severity(self, evaluator):
        fallacies = [
            {"fallacy_type": "Ad hominem"},  # no severity, no argument/context
        ]
        ranked = evaluator.rank_fallacies(fallacies)
        assert "severity" in ranked[0]
        assert "severity_level" in ranked[0]

    def test_rank_fallacies_evaluates_with_argument_context(self, evaluator):
        fallacies = [
            {
                "fallacy_type": "Appel à l'autorité",
                "argument": "Les experts disent que...",
                "context": "scientifique",
            }
        ]
        ranked = evaluator.rank_fallacies(fallacies)
        assert ranked[0]["severity"] > 0

    def test_rank_fallacies_empty_list(self, evaluator):
        ranked = evaluator.rank_fallacies([])
        assert ranked == []

    # --- evaluate_impact ---

    def test_evaluate_impact_returns_complete_result(self, evaluator):
        result = evaluator.evaluate_impact(
            "Faux dilemme", "Soit vous acceptez, soit vous perdez tout.", "commercial"
        )
        assert "fallacy_type" in result
        assert "severity" in result
        assert "severity_level" in result
        assert "explanation" in result
        assert "impact_on_validity" in result
        assert "correction_suggestions" in result
        assert isinstance(result["correction_suggestions"], list)


# ========================================================================
# ContextualFallacyAnalyzer
# ========================================================================


class TestContextualFallacyAnalyzer:
    """Tests for ContextualFallacyAnalyzer."""

    @pytest.fixture
    def analyzer(self):
        from argumentation_analysis.agents.tools.analysis.contextual_fallacy_analyzer import (
            ContextualFallacyAnalyzer,
        )

        return ContextualFallacyAnalyzer()

    # --- _determine_context_type ---

    def test_context_type_politique(self, analyzer):
        assert analyzer._determine_context_type("discours politique") == "politique"

    def test_context_type_scientifique(self, analyzer):
        assert analyzer._determine_context_type("étude scientifique") == "scientifique"

    def test_context_type_commercial(self, analyzer):
        assert analyzer._determine_context_type("publicité produit") == "commercial"

    def test_context_type_juridique(self, analyzer):
        assert analyzer._determine_context_type("procès juridique") == "juridique"

    def test_context_type_academique(self, analyzer):
        assert analyzer._determine_context_type("thèse universitaire") == "académique"

    def test_context_type_general(self, analyzer):
        assert analyzer._determine_context_type("conversation informelle") == "général"

    # --- _identify_potential_fallacies ---

    def test_identify_authority_fallacy(self, analyzer):
        fallacies = analyzer._identify_potential_fallacies(
            "Les experts sont unanimes sur ce sujet."
        )
        types = [f["fallacy_type"] for f in fallacies]
        assert "Appel à l'autorité" in types

    def test_identify_popularity_fallacy(self, analyzer):
        fallacies = analyzer._identify_potential_fallacies(
            "Tout le monde sait que c'est vrai."
        )
        types = [f["fallacy_type"] for f in fallacies]
        assert "Appel à la popularité" in types

    def test_identify_emotion_fallacy(self, analyzer):
        fallacies = analyzer._identify_potential_fallacies(
            "Vous devriez avoir peur de ce qui va arriver."
        )
        types = [f["fallacy_type"] for f in fallacies]
        assert "Appel à l'émotion" in types

    def test_identify_false_dilemma(self, analyzer):
        fallacies = analyzer._identify_potential_fallacies(
            "Soit vous acceptez, ou bien vous refusez."
        )
        types = [f["fallacy_type"] for f in fallacies]
        assert "Faux dilemme" in types

    def test_identify_slippery_slope(self, analyzer):
        fallacies = analyzer._identify_potential_fallacies(
            "Cela mènera à une catastrophe inévitablement."
        )
        types = [f["fallacy_type"] for f in fallacies]
        assert "Pente glissante" in types

    def test_identify_no_fallacies_clean_text(self, analyzer):
        fallacies = analyzer._identify_potential_fallacies("Le chat dort paisiblement.")
        assert len(fallacies) == 0

    def test_identify_multiple_fallacies(self, analyzer):
        fallacies = analyzer._identify_potential_fallacies(
            "Les experts unanimes disent que tout le monde est d'accord."
        )
        types = set(f["fallacy_type"] for f in fallacies)
        assert len(types) >= 2

    def test_fallacy_has_expected_fields(self, analyzer):
        fallacies = analyzer._identify_potential_fallacies("Les experts sont unanimes.")
        assert len(fallacies) > 0
        f = fallacies[0]
        assert "fallacy_type" in f
        assert "keyword" in f
        assert "context_text" in f
        assert "confidence" in f
        assert f["confidence"] == 0.5  # default

    # --- _filter_by_context ---

    def test_filter_general_context_keeps_all(self, analyzer):
        fallacies = [
            {"fallacy_type": "Ad hominem", "confidence": 0.5},
            {"fallacy_type": "Appel à la tradition", "confidence": 0.5},
        ]
        filtered = analyzer._filter_by_context(fallacies, "général")
        assert len(filtered) == 2
        for f in filtered:
            assert f["contextual_relevance"] == "Générale"

    def test_filter_political_context_boosts_relevant(self, analyzer):
        fallacies = [
            {"fallacy_type": "Ad hominem", "confidence": 0.5},
            {"fallacy_type": "Appel à la tradition", "confidence": 0.5},
        ]
        filtered = analyzer._filter_by_context(fallacies, "politique")
        ad_hominem = [f for f in filtered if f["fallacy_type"] == "Ad hominem"][0]
        tradition = [
            f for f in filtered if f["fallacy_type"] == "Appel à la tradition"
        ][0]
        # Ad hominem is relevant in political context
        assert ad_hominem["confidence"] == 0.8
        assert ad_hominem["contextual_relevance"] == "Élevée"
        # Tradition is not particularly relevant
        assert tradition["confidence"] == 0.3
        assert tradition["contextual_relevance"] == "Faible"

    def test_filter_does_not_modify_original(self, analyzer):
        original = {"fallacy_type": "Ad hominem", "confidence": 0.5}
        fallacies = [original]
        analyzer._filter_by_context(fallacies, "politique")
        assert original["confidence"] == 0.5  # original not mutated

    # --- analyze_context ---

    def test_analyze_context_with_missing_taxonomy(self, analyzer):
        """When taxonomy is None, analyze_context returns empty dict."""
        with patch.object(analyzer, "_get_taxonomy_df", return_value=None):
            result = analyzer.analyze_context("Un texte quelconque.", "général")
            assert result == {}

    def test_analyze_context_returns_expected_keys(self, analyzer):
        """With a valid taxonomy, analyze_context returns structured result."""
        with patch.object(analyzer, "_get_taxonomy_df", return_value=MagicMock()):
            result = analyzer.analyze_context(
                "Les experts unanimes disent que tout le monde est d'accord.",
                "politique",
            )
            assert "context_type" in result
            assert "potential_fallacies_count" in result
            assert "contextual_fallacies_count" in result
            assert "contextual_fallacies" in result
            assert result["context_type"] == "politique"

    # --- identify_contextual_fallacies ---

    def test_identify_contextual_fallacies_filters_by_confidence(self, analyzer):
        with patch.object(analyzer, "_get_taxonomy_df", return_value=MagicMock()):
            fallacies = analyzer.identify_contextual_fallacies(
                "Les experts unanimes affirment que c'est vrai.", "général"
            )
            # All returned fallacies should have confidence >= 0.5
            for f in fallacies:
                assert f["confidence"] >= 0.5

    def test_identify_contextual_fallacies_empty_text(self, analyzer):
        with patch.object(analyzer, "_get_taxonomy_df", return_value=MagicMock()):
            fallacies = analyzer.identify_contextual_fallacies(
                "Le chat dort.", "général"
            )
            assert isinstance(fallacies, list)

    # --- get_contextual_fallacy_examples ---

    def test_examples_known_type_and_context(self, analyzer):
        examples = analyzer.get_contextual_fallacy_examples(
            "Appel à l'autorité", "politique"
        )
        assert isinstance(examples, list)
        assert len(examples) == 2

    def test_examples_known_type_unknown_context(self, analyzer):
        examples = analyzer.get_contextual_fallacy_examples(
            "Appel à l'autorité", "inconnu"
        )
        assert isinstance(examples, list)
        assert len(examples) == 1
        assert "Aucun exemple" in examples[0]

    def test_examples_unknown_type(self, analyzer):
        examples = analyzer.get_contextual_fallacy_examples("Type Inconnu", "politique")
        assert isinstance(examples, list)
        assert "Aucun exemple" in examples[0]


# ========================================================================
# ComplexFallacyAnalyzer
# ========================================================================


class TestComplexFallacyAnalyzer:
    """Tests for ComplexFallacyAnalyzer."""

    @pytest.fixture
    def mock_contextual(self):
        mock = MagicMock()
        mock.identify_contextual_fallacies.return_value = []
        return mock

    @pytest.fixture
    def mock_severity(self):
        mock = MagicMock()
        mock._determine_severity_level.return_value = "Modéré"
        return mock

    @pytest.fixture
    def analyzer(self, mock_contextual, mock_severity):
        """Create ComplexFallacyAnalyzer with mocked dependencies."""
        from argumentation_analysis.agents.tools.support.shared_services import (
            ServiceRegistry,
        )
        from argumentation_analysis.agents.tools.analysis.contextual_fallacy_analyzer import (
            ContextualFallacyAnalyzer,
        )
        from argumentation_analysis.agents.tools.analysis.fallacy_severity_evaluator import (
            FallacySeverityEvaluator,
        )

        # Pre-populate ServiceRegistry with mocks
        ServiceRegistry._services[ContextualFallacyAnalyzer] = mock_contextual
        ServiceRegistry._services[FallacySeverityEvaluator] = mock_severity

        from argumentation_analysis.agents.tools.analysis.complex_fallacy_analyzer import (
            ComplexFallacyAnalyzer,
        )

        return ComplexFallacyAnalyzer()

    # --- _detect_contradictions ---

    def test_detect_contradictions_finds_positive_negative_pair(self, analyzer):
        arguments = [
            "Ce produit est sûr et efficace.",
            "Ce produit n'est pas sûr pour les enfants.",
        ]
        contradictions = analyzer._detect_contradictions(arguments)
        assert len(contradictions) > 0
        assert contradictions[0]["involved_arguments"] == [0, 1]
        assert "positive_statement" in contradictions[0]["details"]
        assert "negative_statement" in contradictions[0]["details"]

    def test_detect_contradictions_no_contradiction(self, analyzer):
        arguments = [
            "Le ciel bleu.",
            "La mer verte.",
        ]
        contradictions = analyzer._detect_contradictions(arguments)
        assert len(contradictions) == 0

    def test_detect_contradictions_empty_list(self, analyzer):
        contradictions = analyzer._detect_contradictions([])
        assert contradictions == []

    def test_detect_contradictions_single_argument(self, analyzer):
        contradictions = analyzer._detect_contradictions(["Un seul argument."])
        assert contradictions == []

    # --- _detect_circular_arguments ---

    def test_circular_arguments_fewer_than_3(self, analyzer):
        circles = analyzer._detect_circular_arguments(["A", "B"])
        assert circles == []

    def test_circular_arguments_no_keywords(self, analyzer):
        circles = analyzer._detect_circular_arguments(
            [
                "Le chat dort.",
                "Le chien mange.",
                "L'oiseau chante.",
            ]
        )
        assert circles == []

    def test_circular_arguments_detected_with_keywords(self, analyzer):
        circles = analyzer._detect_circular_arguments(
            [
                "A est vrai, donc B est vrai.",
                "B est vrai, donc C est vrai.",
                "C est vrai, donc A est vrai.",
            ]
        )
        assert len(circles) > 0
        for circle in circles:
            assert len(circle["involved_arguments"]) == 3
            assert circle["details"]["arg1_supports_arg2"] is True

    # --- identify_combined_fallacies ---

    def test_combined_no_individual_fallacies(self, analyzer, mock_contextual):
        mock_contextual.identify_contextual_fallacies.return_value = []
        result = analyzer.identify_combined_fallacies("Un texte quelconque.")
        assert result == []

    def test_combined_single_fallacy_no_combination(self, analyzer, mock_contextual):
        mock_contextual.identify_contextual_fallacies.return_value = [
            {"fallacy_type": "Ad hominem", "confidence": 0.7}
        ]
        result = analyzer.identify_combined_fallacies("Un texte.")
        assert result == []

    def test_combined_matching_combination(
        self, analyzer, mock_contextual, mock_severity
    ):
        """When both components of a known combination are present, it's detected."""
        mock_contextual.identify_contextual_fallacies.return_value = [
            {"fallacy_type": "Appel à l'autorité", "confidence": 0.6},
            {"fallacy_type": "Appel à la popularité", "confidence": 0.7},
        ]
        mock_severity._determine_severity_level.return_value = "Élevé"

        result = analyzer.identify_combined_fallacies("Experts et tout le monde.")
        assert len(result) == 1
        assert result[0]["combination_name"] == "Double appel"
        assert "severity" in result[0]
        assert result[0]["severity"] <= 1.0
        assert "component_fallacies" in result[0]

    def test_combined_severity_capped_at_1(
        self, analyzer, mock_contextual, mock_severity
    ):
        mock_contextual.identify_contextual_fallacies.return_value = [
            {"fallacy_type": "Ad hominem", "confidence": 0.95},
            {"fallacy_type": "Généralisation hâtive", "confidence": 0.95},
        ]
        result = analyzer.identify_combined_fallacies("Texte.")
        assert len(result) == 1
        assert result[0]["severity"] <= 1.0

    # --- analyze_structural_fallacies ---

    def test_structural_with_contradictions(self, analyzer, mock_contextual):
        mock_contextual.identify_contextual_fallacies.return_value = []
        arguments = [
            "Ce produit est sûr.",
            "Ce produit n'est pas sûr.",
        ]
        result = analyzer.analyze_structural_fallacies(arguments)
        # Should find contradictions
        contradiction_types = [f["structural_fallacy_type"] for f in result]
        assert "Contradiction cachée" in contradiction_types

    def test_structural_with_circular_arguments(self, analyzer, mock_contextual):
        mock_contextual.identify_contextual_fallacies.return_value = []
        arguments = [
            "A est vrai, donc B est vrai.",
            "B est vrai, donc C est vrai.",
            "C est vrai, donc A est vrai.",
        ]
        result = analyzer.analyze_structural_fallacies(arguments)
        circle_types = [f["structural_fallacy_type"] for f in result]
        assert "Cercle argumentatif" in circle_types

    def test_structural_empty_arguments(self, analyzer, mock_contextual):
        mock_contextual.identify_contextual_fallacies.return_value = []
        result = analyzer.analyze_structural_fallacies([])
        assert result == []

    # --- _detect_alternation_patterns ---

    def test_alternation_fewer_than_4_paragraphs(self, analyzer):
        paragraphs = [
            {"paragraph_index": 0, "fallacies": []},
            {"paragraph_index": 1, "fallacies": []},
        ]
        result = analyzer._detect_alternation_patterns(paragraphs)
        assert result == []

    def test_alternation_pattern_detected(self, analyzer):
        paragraphs = [
            {"paragraph_index": 0, "fallacies": [{"fallacy_type": "A"}]},
            {"paragraph_index": 1, "fallacies": [{"fallacy_type": "B"}]},
            {"paragraph_index": 2, "fallacies": [{"fallacy_type": "A"}]},
            {"paragraph_index": 3, "fallacies": [{"fallacy_type": "B"}]},
            {"paragraph_index": 4, "fallacies": [{"fallacy_type": "A"}]},
        ]
        result = analyzer._detect_alternation_patterns(paragraphs)
        assert len(result) > 0
        pattern = result[0]
        assert pattern["alternation_count"] >= 2

    def test_alternation_no_pattern(self, analyzer):
        paragraphs = [
            {"paragraph_index": 0, "fallacies": [{"fallacy_type": "A"}]},
            {"paragraph_index": 1, "fallacies": [{"fallacy_type": "A"}]},
            {"paragraph_index": 2, "fallacies": [{"fallacy_type": "A"}]},
            {"paragraph_index": 3, "fallacies": [{"fallacy_type": "A"}]},
        ]
        result = analyzer._detect_alternation_patterns(paragraphs)
        assert result == []

    # --- _detect_escalation_patterns ---

    def test_escalation_fewer_than_3_paragraphs(self, analyzer):
        paragraphs = [
            {"paragraph_index": 0, "fallacies": []},
            {"paragraph_index": 1, "fallacies": []},
        ]
        result = analyzer._detect_escalation_patterns(paragraphs)
        assert result == []

    def test_escalation_detected(self, analyzer):
        # Escalation order: Appel à la tradition < Appel à la popularité < Ad hominem
        paragraphs = [
            {
                "paragraph_index": 0,
                "fallacies": [{"fallacy_type": "Appel à la tradition"}],
            },
            {
                "paragraph_index": 1,
                "fallacies": [{"fallacy_type": "Appel à la popularité"}],
            },
            {"paragraph_index": 2, "fallacies": [{"fallacy_type": "Ad hominem"}]},
        ]
        result = analyzer._detect_escalation_patterns(paragraphs)
        assert len(result) > 0
        pattern = result[0]
        assert pattern["start_fallacy_type"] == "Appel à la tradition"
        assert pattern["end_fallacy_type"] == "Ad hominem"
        assert len(pattern["fallacy_sequence"]) == 3

    def test_escalation_not_in_order(self, analyzer):
        # Reverse order should not be detected as escalation
        paragraphs = [
            {"paragraph_index": 0, "fallacies": [{"fallacy_type": "Ad hominem"}]},
            {
                "paragraph_index": 1,
                "fallacies": [{"fallacy_type": "Appel à la popularité"}],
            },
            {
                "paragraph_index": 2,
                "fallacies": [{"fallacy_type": "Appel à la tradition"}],
            },
        ]
        result = analyzer._detect_escalation_patterns(paragraphs)
        assert result == []

    def test_escalation_unknown_types_skipped(self, analyzer):
        paragraphs = [
            {"paragraph_index": 0, "fallacies": [{"fallacy_type": "Type Inconnu 1"}]},
            {"paragraph_index": 1, "fallacies": [{"fallacy_type": "Type Inconnu 2"}]},
            {"paragraph_index": 2, "fallacies": [{"fallacy_type": "Type Inconnu 3"}]},
        ]
        result = analyzer._detect_escalation_patterns(paragraphs)
        assert result == []

    # --- identify_fallacy_patterns (full pipeline) ---

    def test_fallacy_patterns_empty_text(self, analyzer, mock_contextual):
        mock_contextual.identify_contextual_fallacies.return_value = []
        result = analyzer.identify_fallacy_patterns("")
        assert isinstance(result, list)

    def test_fallacy_patterns_delegates_to_contextual(self, analyzer, mock_contextual):
        mock_contextual.identify_contextual_fallacies.return_value = []
        analyzer.identify_fallacy_patterns("Paragraphe 1\n\nParagraphe 2")
        # Should be called for each non-empty paragraph
        assert mock_contextual.identify_contextual_fallacies.call_count >= 2

    def test_fallacy_patterns_returns_pattern_dicts(self, analyzer, mock_contextual):
        # Simulate alternation pattern detection
        call_count = [0]

        def side_effect(argument, context):
            call_count[0] += 1
            if call_count[0] % 2 == 1:
                return [{"fallacy_type": "Appel à l'autorité", "confidence": 0.7}]
            else:
                return [{"fallacy_type": "Ad hominem", "confidence": 0.7}]

        mock_contextual.identify_contextual_fallacies.side_effect = side_effect
        text = "P1\n\nP2\n\nP3\n\nP4\n\nP5"
        result = analyzer.identify_fallacy_patterns(text)
        # Even if no patterns found (depends on alternation count), result is a list
        assert isinstance(result, list)
        for pattern in result:
            assert "pattern_type" in pattern
            assert "severity" in pattern


# ========================================================================
# Integration-level: ServiceRegistry and ConfigManager
# ========================================================================


class TestSharedServices:
    """Tests for the shared_services infrastructure used by analyzers."""

    def test_service_registry_creates_singleton(self):
        from argumentation_analysis.agents.tools.support.shared_services import (
            ServiceRegistry,
        )

        class DummyService:
            pass

        instance1 = ServiceRegistry.get(DummyService)
        instance2 = ServiceRegistry.get(DummyService)
        assert instance1 is instance2

    def test_config_manager_caches_config(self):
        from argumentation_analysis.agents.tools.support.shared_services import (
            ConfigManager,
        )

        call_count = [0]

        def loader():
            call_count[0] += 1
            return {"key": "value"}

        result1 = ConfigManager.load_config("test_config", loader)
        result2 = ConfigManager.load_config("test_config", loader)
        assert result1 == {"key": "value"}
        assert call_count[0] == 1  # only called once

    def test_config_manager_force_reload(self):
        from argumentation_analysis.agents.tools.support.shared_services import (
            ConfigManager,
        )

        call_count = [0]

        def loader():
            call_count[0] += 1
            return {"version": call_count[0]}

        ConfigManager.load_config("reload_test", loader)
        result = ConfigManager.load_config("reload_test", loader, force_reload=True)
        assert call_count[0] == 2
        assert result["version"] == 2

    def test_get_configured_logger(self):
        from argumentation_analysis.agents.tools.support.shared_services import (
            get_configured_logger,
        )
        import logging

        logger = get_configured_logger("TestLogger")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "TestLogger"
