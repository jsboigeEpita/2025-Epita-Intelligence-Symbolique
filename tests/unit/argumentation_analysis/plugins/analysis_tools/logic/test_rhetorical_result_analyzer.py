# tests/unit/argumentation_analysis/plugins/analysis_tools/logic/test_rhetorical_result_analyzer.py
"""Tests for EnhancedRhetoricalResultAnalyzer and RecommendationGenerator."""

import pytest
from unittest.mock import MagicMock, patch

from argumentation_analysis.plugins.analysis_tools.logic.rhetorical_result_analyzer import (
    RecommendationGenerator,
    EnhancedRhetoricalResultAnalyzer,
)


# ── RecommendationGenerator ──


class TestRecommendationGenerator:
    @pytest.fixture
    def gen(self):
        return RecommendationGenerator()

    # -- Structure --
    def test_generate_returns_all_categories(self, gen):
        recs = gen.generate({}, {}, {}, "général")
        assert "general_recommendations" in recs
        assert "fallacy_recommendations" in recs
        assert "coherence_recommendations" in recs
        assert "persuasion_recommendations" in recs
        assert "context_specific_recommendations" in recs

    def test_generate_empty_inputs_no_crash(self, gen):
        recs = gen.generate({}, {}, {}, "")
        assert all(isinstance(v, list) for v in recs.values())

    # -- Fallacy recommendations --
    def test_high_fallacy_count(self, gen):
        recs = gen.generate({"total_fallacies": 10}, {}, {}, "")
        assert any("sophismes" in r.lower() for r in recs["fallacy_recommendations"])

    def test_high_severity_triggers_recommendation(self, gen):
        recs = gen.generate({"overall_severity": 0.8}, {}, {}, "")
        assert any("graves" in r.lower() for r in recs["fallacy_recommendations"])

    def test_most_common_fallacies_emotion(self, gen):
        recs = gen.generate(
            {"overall_severity": 0.8, "most_common_fallacies": ["Appel à l'émotion"]},
            {}, {}, "",
        )
        assert any("émotionnel" in r for r in recs["fallacy_recommendations"])

    def test_most_common_fallacies_ad_hominem(self, gen):
        recs = gen.generate(
            {"overall_severity": 0.8, "most_common_fallacies": ["Ad hominem"]},
            {}, {}, "",
        )
        assert any("personnelles" in r for r in recs["fallacy_recommendations"])

    def test_most_common_fallacies_authority(self, gen):
        recs = gen.generate(
            {"overall_severity": 0.8, "most_common_fallacies": ["Appel à l'autorité"]},
            {}, {}, "",
        )
        assert any("crédibles" in r for r in recs["fallacy_recommendations"])

    def test_low_contextual_ratio(self, gen):
        recs = gen.generate({"contextual_ratio": 0.1}, {}, {}, "")
        assert any("contexte" in r.lower() for r in recs["fallacy_recommendations"])

    # -- Coherence recommendations --
    def test_low_coherence(self, gen):
        recs = gen.generate({}, {"overall_coherence": 0.3}, {}, "")
        assert any("cohérence" in r.lower() for r in recs["coherence_recommendations"])

    def test_contradiction_count(self, gen):
        recs = gen.generate({}, {"contradiction_count": 3}, {}, "")
        assert any("3" in r for r in recs["coherence_recommendations"])

    def test_thematic_shifts_issue(self, gen):
        recs = gen.generate(
            {}, {"main_coherence_issues": ["Thematic shifts"]}, {}, "",
        )
        assert any("thématique" in r for r in recs["coherence_recommendations"])

    def test_logical_gaps_issue(self, gen):
        recs = gen.generate(
            {}, {"main_coherence_issues": ["Logical gaps"]}, {}, "",
        )
        assert any("logiques" in r for r in recs["coherence_recommendations"])

    def test_multiple_themes_issue(self, gen):
        recs = gen.generate(
            {}, {"main_coherence_issues": ["Multiple unrelated themes"]}, {}, "",
        )
        assert any("thèmes" in r for r in recs["coherence_recommendations"])

    # -- Persuasion recommendations --
    def test_low_persuasion(self, gen):
        recs = gen.generate({}, {}, {"persuasion_score": 0.3}, "")
        assert any("persuasive" in r.lower() for r in recs["persuasion_recommendations"])

    def test_low_ethos_appeal(self, gen):
        recs = gen.generate(
            {}, {}, {"rhetorical_appeals": {"ethos": 0.2, "pathos": 0.8, "logos": 0.5}}, "",
        )
        assert any("crédibilité" in r for r in recs["persuasion_recommendations"])

    def test_low_pathos_appeal(self, gen):
        recs = gen.generate(
            {}, {}, {"rhetorical_appeals": {"ethos": 0.8, "pathos": 0.2, "logos": 0.5}}, "",
        )
        assert any("émotionnel" in r for r in recs["persuasion_recommendations"])

    def test_low_logos_appeal(self, gen):
        recs = gen.generate(
            {}, {}, {"rhetorical_appeals": {"ethos": 0.8, "pathos": 0.8, "logos": 0.1}}, "",
        )
        assert any("logique" in r for r in recs["persuasion_recommendations"])

    # -- Context-specific recommendations --
    def test_politique_context(self, gen):
        recs = gen.generate(
            {}, {},
            {"emotional_appeal": 0.9, "logical_appeal": 0.2},
            "politique",
        )
        assert len(recs["context_specific_recommendations"]) >= 1

    def test_scientifique_context(self, gen):
        recs = gen.generate({}, {}, {"logical_appeal": 0.3}, "scientifique")
        assert any("rigueur" in r for r in recs["context_specific_recommendations"])

    def test_commercial_context(self, gen):
        recs = gen.generate({}, {}, {"credibility_appeal": 0.3}, "commercial")
        assert any("crédibilité" in r for r in recs["context_specific_recommendations"])

    # -- General recommendations --
    def test_general_recommendation_high_severity_low_coherence(self, gen):
        recs = gen.generate(
            {"overall_severity": 0.8},
            {"overall_coherence": 0.3},
            {},
            "",
        )
        assert any("Restructurer" in r for r in recs["general_recommendations"])

    def test_general_recommendation_low_persuasion(self, gen):
        recs = gen.generate({}, {}, {"persuasion_score": 0.3}, "")
        assert any("stratégie" in r.lower() for r in recs["general_recommendations"])


# ── EnhancedRhetoricalResultAnalyzer ──


def _make_analyzer():
    """Create analyzer with mock dependencies to avoid heavy init."""
    return EnhancedRhetoricalResultAnalyzer(
        complex_fallacy_analyzer=MagicMock(),
        severity_evaluator=MagicMock(),
        recommendation_generator=RecommendationGenerator(),
    )


class TestEnhancedRhetoricalResultAnalyzerInit:
    def test_custom_dependencies(self):
        mock_fallacy = MagicMock()
        mock_severity = MagicMock()
        mock_recs = MagicMock()
        analyzer = EnhancedRhetoricalResultAnalyzer(
            complex_fallacy_analyzer=mock_fallacy,
            severity_evaluator=mock_severity,
            recommendation_generator=mock_recs,
        )
        assert analyzer.complex_fallacy_analyzer is mock_fallacy
        assert analyzer.severity_evaluator is mock_severity
        assert analyzer.recommendation_generator is mock_recs
        assert analyzer.analysis_history == []


class TestAnalyzeFallacyDistribution:
    @pytest.fixture
    def analyzer(self):
        return _make_analyzer()

    def test_empty_results(self, analyzer):
        result = analyzer._analyze_fallacy_distribution({})
        assert result["total_fallacies"] == 0
        assert result["most_common_fallacies"] == []
        assert result["composite_fallacies"] == 0

    def test_with_individual_fallacies(self, analyzer):
        results = {
            "complex_fallacy_analysis": {
                "individual_fallacies_count": 5,
                "basic_combinations": [{"id": 1}],
                "advanced_combinations": [{"id": 2}, {"id": 3}],
            },
        }
        result = analyzer._analyze_fallacy_distribution(results)
        assert result["total_fallacies"] == 8  # 5 + 1 + 2
        assert result["composite_fallacies"] == 3  # 1 + 2

    def test_contextual_fallacy_types(self, analyzer):
        results = {
            "contextual_fallacy_analysis": {
                "contextual_fallacies": [
                    {"fallacy_type": "Ad hominem", "confidence": 0.9},
                    {"fallacy_type": "Ad hominem", "confidence": 0.7},
                    {"fallacy_type": "Appel à l'émotion", "confidence": 0.8},
                ],
            },
        }
        result = analyzer._analyze_fallacy_distribution(results)
        assert result["fallacy_types_distribution"]["Ad hominem"] == 2
        assert result["most_common_fallacies"][0] == "Ad hominem"

    def test_severity_from_composite(self, analyzer):
        results = {
            "complex_fallacy_analysis": {
                "composite_severity": {
                    "adjusted_severity": 0.85,
                    "severity_level": "Grave",
                },
            },
        }
        result = analyzer._analyze_fallacy_distribution(results)
        assert result["overall_severity"] == 0.85
        assert result["severity_level"] == "Grave"


class TestAnalyzeCoherenceQuality:
    @pytest.fixture
    def analyzer(self):
        return _make_analyzer()

    def test_empty_results(self, analyzer):
        result = analyzer._analyze_coherence_quality({})
        assert result["overall_coherence"] == 0.5
        assert result["coherence_level"] == "Modéré"

    def test_with_coherence_data(self, analyzer):
        results = {
            "argument_coherence_evaluation": {
                "coherence_score": 0.8,
                "coherence_level": "Bon",
                "thematic_clusters": [{"id": 1}],
                "logical_flows": [{"id": 1}],
            },
        }
        result = analyzer._analyze_coherence_quality(results)
        assert result["overall_coherence"] == 0.8
        assert result["coherence_level"] == "Bon"
        assert result["thematic_coherence"] == 0.7  # <= 2 clusters
        assert result["logical_coherence"] == 0.6  # logical_flows present

    def test_many_clusters_lowers_thematic(self, analyzer):
        results = {
            "argument_coherence_evaluation": {
                "thematic_clusters": [1, 2, 3],
            },
        }
        result = analyzer._analyze_coherence_quality(results)
        assert result["thematic_coherence"] == 0.5
        assert "Multiple unrelated themes" in result["main_coherence_issues"]

    def test_no_logical_flows(self, analyzer):
        result = analyzer._analyze_coherence_quality({})
        assert result["logical_coherence"] == 0.3
        assert "Logical gaps" in result["main_coherence_issues"]


class TestAnalyzePersuasionEffectiveness:
    @pytest.fixture
    def analyzer(self):
        return _make_analyzer()

    def test_empty_results(self, analyzer):
        result = analyzer._analyze_persuasion_effectiveness({}, "général")
        assert "persuasion_score" in result
        assert "persuasion_level" in result
        assert result["emotional_appeal"] == 0.0
        assert result["logical_appeal"] == 0.0
        assert result["credibility_appeal"] == 0.0

    def test_persuasion_levels(self, analyzer):
        # Test excellent level
        with patch.object(analyzer, "_identify_rhetorical_appeals", return_value={"ethos": 1.0, "pathos": 1.0, "logos": 1.0}):
            with patch.object(analyzer, "_evaluate_context_appropriateness", return_value=1.0):
                with patch.object(analyzer, "_evaluate_audience_alignment", return_value=1.0):
                    result = analyzer._analyze_persuasion_effectiveness({}, "")
                    assert result["persuasion_level"] == "Excellent"

    def test_low_persuasion_level(self, analyzer):
        with patch.object(analyzer, "_identify_rhetorical_appeals", return_value={"ethos": 0.0, "pathos": 0.0, "logos": 0.0}):
            with patch.object(analyzer, "_evaluate_context_appropriateness", return_value=0.0):
                with patch.object(analyzer, "_evaluate_audience_alignment", return_value=0.0):
                    result = analyzer._analyze_persuasion_effectiveness({}, "")
                    assert result["persuasion_level"] == "Très faible"


class TestContextAppropriateness:
    @pytest.fixture
    def analyzer(self):
        return _make_analyzer()

    def test_politique_context(self, analyzer):
        appeals = {"ethos": 0.5, "pathos": 0.5, "logos": 0.5}
        score = analyzer._evaluate_context_appropriateness(appeals, "politique")
        assert 0.0 <= score <= 1.0

    def test_scientifique_context(self, analyzer):
        appeals = {"ethos": 0.5, "pathos": 0.5, "logos": 0.5}
        score = analyzer._evaluate_context_appropriateness(appeals, "scientifique")
        assert 0.0 <= score <= 1.0

    def test_unknown_context_uses_default(self, analyzer):
        appeals = {"ethos": 0.5, "pathos": 0.5, "logos": 0.5}
        score = analyzer._evaluate_context_appropriateness(appeals, "inconnu")
        assert 0.0 <= score <= 1.0

    def test_score_capped_at_one(self, analyzer):
        appeals = {"ethos": 2.0, "pathos": 2.0, "logos": 2.0}
        score = analyzer._evaluate_context_appropriateness(appeals, "général")
        assert score <= 1.0

    @pytest.mark.parametrize("context", [
        "politique", "scientifique", "commercial", "juridique", "académique", "général",
    ])
    def test_all_defined_contexts(self, analyzer, context):
        appeals = {"ethos": 0.5, "pathos": 0.5, "logos": 0.5}
        score = analyzer._evaluate_context_appropriateness(appeals, context)
        assert 0.0 <= score <= 1.0


class TestAudienceAlignment:
    @pytest.fixture
    def analyzer(self):
        return _make_analyzer()

    def test_generaliste_audience(self, analyzer):
        appeals = {"ethos": 0.5, "pathos": 0.5, "logos": 0.5}
        score = analyzer._evaluate_audience_alignment(appeals, ["généraliste"])
        assert 0.0 <= score <= 1.0

    def test_expert_audience(self, analyzer):
        appeals = {"ethos": 0.5, "pathos": 0.5, "logos": 0.5}
        score = analyzer._evaluate_audience_alignment(appeals, ["expert"])
        assert 0.0 <= score <= 1.0

    def test_empty_characteristics(self, analyzer):
        appeals = {"ethos": 0.5, "pathos": 0.5, "logos": 0.5}
        score = analyzer._evaluate_audience_alignment(appeals, [])
        assert 0.0 <= score <= 1.0

    def test_unknown_characteristic(self, analyzer):
        appeals = {"ethos": 0.5, "pathos": 0.5, "logos": 0.5}
        score = analyzer._evaluate_audience_alignment(appeals, ["inconnu"])
        assert 0.0 <= score <= 1.0

    def test_multiple_characteristics(self, analyzer):
        appeals = {"ethos": 0.5, "pathos": 0.5, "logos": 0.5}
        score = analyzer._evaluate_audience_alignment(appeals, ["expert", "senior"])
        assert 0.0 <= score <= 1.0


class TestOverallRhetoricalQuality:
    @pytest.fixture
    def analyzer(self):
        return _make_analyzer()

    def test_excellent_quality(self, analyzer):
        score, level = analyzer._calculate_overall_rhetorical_quality(
            {"overall_severity": 0.0},  # fallacy_quality = 1.0
            {"overall_coherence": 0.9},
            {"persuasion_score": 0.9},
        )
        assert level == "Excellent"
        assert score > 0.8

    def test_moderate_quality(self, analyzer):
        score, level = analyzer._calculate_overall_rhetorical_quality(
            {"overall_severity": 0.5},
            {"overall_coherence": 0.5},
            {"persuasion_score": 0.5},
        )
        assert level == "Modéré"

    def test_very_low_quality(self, analyzer):
        score, level = analyzer._calculate_overall_rhetorical_quality(
            {"overall_severity": 1.0},  # fallacy_quality = 0.0
            {"overall_coherence": 0.0},
            {"persuasion_score": 0.0},
        )
        assert level == "Très faible"
        assert score < 0.2

    def test_formula(self, analyzer):
        """Verify the exact formula: (1-severity)*0.3 + coherence*0.3 + persuasion*0.4"""
        score, _ = analyzer._calculate_overall_rhetorical_quality(
            {"overall_severity": 0.2},  # fallacy_quality = 0.8
            {"overall_coherence": 0.6},
            {"persuasion_score": 0.7},
        )
        expected = 0.8 * 0.3 + 0.6 * 0.3 + 0.7 * 0.4
        assert abs(score - expected) < 0.001


class TestStrengthsAndWeaknesses:
    @pytest.fixture
    def analyzer(self):
        return _make_analyzer()

    def test_no_fallacies_is_strength(self, analyzer):
        s, w = analyzer._identify_strengths_and_weaknesses(
            {"total_fallacies": 0}, {}, {},
        )
        assert any("Absence" in x for x in s)

    def test_moderate_fallacies_is_strength(self, analyzer):
        s, w = analyzer._identify_strengths_and_weaknesses(
            {"total_fallacies": 3, "overall_severity": 0.3}, {}, {},
        )
        assert any("modérée" in x for x in s)

    def test_severe_fallacies_is_weakness(self, analyzer):
        s, w = analyzer._identify_strengths_and_weaknesses(
            {"total_fallacies": 5, "overall_severity": 0.8}, {}, {},
        )
        assert any("excessive" in x for x in w)

    def test_high_coherence_strength(self, analyzer):
        s, w = analyzer._identify_strengths_and_weaknesses(
            {}, {"overall_coherence": 0.8}, {},
        )
        assert any("cohérence argumentative" in x for x in s)

    def test_low_coherence_weakness(self, analyzer):
        s, w = analyzer._identify_strengths_and_weaknesses(
            {}, {"overall_coherence": 0.3}, {},
        )
        assert any("cohérence argumentative" in x for x in w)

    def test_high_persuasion_strength(self, analyzer):
        s, w = analyzer._identify_strengths_and_weaknesses(
            {}, {}, {"persuasion_score": 0.8},
        )
        assert any("persuasive" in x.lower() for x in s)

    def test_low_persuasion_weakness(self, analyzer):
        s, w = analyzer._identify_strengths_and_weaknesses(
            {}, {}, {"persuasion_score": 0.3},
        )
        assert any("persuasive" in x.lower() for x in w)

    def test_strong_emotional_appeal(self, analyzer):
        s, _ = analyzer._identify_strengths_and_weaknesses(
            {}, {}, {"emotional_appeal": 0.8},
        )
        assert any("émotionnel" in x for x in s)

    def test_strong_logical_appeal(self, analyzer):
        s, _ = analyzer._identify_strengths_and_weaknesses(
            {}, {}, {"logical_appeal": 0.8},
        )
        assert any("logique" in x for x in s)

    def test_strong_credibility_appeal(self, analyzer):
        s, _ = analyzer._identify_strengths_and_weaknesses(
            {}, {}, {"credibility_appeal": 0.8},
        )
        assert any("crédibilité" in x for x in s)


class TestContextRelevance:
    @pytest.fixture
    def analyzer(self):
        return _make_analyzer()

    def test_matching_context(self, analyzer):
        results = {
            "contextual_fallacy_analysis": {
                "context_analysis": {
                    "context_type": "politique",
                    "confidence": 0.9,
                },
            },
        }
        score = analyzer._evaluate_context_relevance(results, "politique")
        assert score == pytest.approx(0.9, abs=0.01)

    def test_mismatched_context(self, analyzer):
        results = {
            "contextual_fallacy_analysis": {
                "context_analysis": {
                    "context_type": "scientifique",
                    "confidence": 0.9,
                },
            },
        }
        score = analyzer._evaluate_context_relevance(results, "politique")
        assert score < 0.9  # 0.9 * 0.7

    def test_empty_results(self, analyzer):
        score = analyzer._evaluate_context_relevance({}, "général")
        assert 0.0 <= score <= 1.0


class TestRhetoricalAppeals:
    @pytest.fixture
    def analyzer(self):
        return _make_analyzer()

    def test_no_fallacies_returns_zeros(self, analyzer):
        result = analyzer._identify_rhetorical_appeals({})
        assert result == {"ethos": 0.0, "pathos": 0.0, "logos": 0.0}

    def test_ethos_fallacies(self, analyzer):
        data = {
            "contextual_fallacies": [
                {"fallacy_type": "Appel à l'autorité", "confidence": 0.8},
            ],
        }
        result = analyzer._identify_rhetorical_appeals(data)
        assert result["ethos"] > 0
        # Should be normalized
        assert abs(sum(result.values()) - 1.0) < 0.01

    def test_pathos_fallacies(self, analyzer):
        data = {
            "contextual_fallacies": [
                {"fallacy_type": "Appel à la peur", "confidence": 0.7},
                {"fallacy_type": "Appel à la pitié", "confidence": 0.6},
            ],
        }
        result = analyzer._identify_rhetorical_appeals(data)
        assert result["pathos"] > result["ethos"]

    def test_logos_fallacies(self, analyzer):
        data = {
            "contextual_fallacies": [
                {"fallacy_type": "Faux dilemme", "confidence": 0.9},
            ],
        }
        result = analyzer._identify_rhetorical_appeals(data)
        assert result["logos"] > 0

    def test_mixed_fallacies_normalized(self, analyzer):
        data = {
            "contextual_fallacies": [
                {"fallacy_type": "Ad hominem", "confidence": 0.5},  # ethos
                {"fallacy_type": "Appel à la peur", "confidence": 0.5},  # pathos
                {"fallacy_type": "Pente glissante", "confidence": 0.5},  # logos
            ],
        }
        result = analyzer._identify_rhetorical_appeals(data)
        total = sum(result.values())
        assert abs(total - 1.0) < 0.01


class TestPersuasionStrategies:
    @pytest.fixture
    def analyzer(self):
        return _make_analyzer()

    def test_no_fallacies_empty_strategies(self, analyzer):
        result = analyzer._identify_persuasion_strategies({})
        assert result == {}

    def test_authority_strategy(self, analyzer):
        data = {
            "contextual_fallacies": [
                {"fallacy_type": "Appel à l'autorité", "confidence": 0.8},
            ],
        }
        result = analyzer._identify_persuasion_strategies(data)
        assert "Appel à l'autorité" in result

    def test_personal_attack_strategy(self, analyzer):
        data = {
            "contextual_fallacies": [
                {"fallacy_type": "Ad hominem", "confidence": 0.7},
                {"fallacy_type": "Tu quoque", "confidence": 0.6},
            ],
        }
        result = analyzer._identify_persuasion_strategies(data)
        assert "Attaque personnelle" in result

    def test_normalized_scores(self, analyzer):
        data = {
            "contextual_fallacies": [
                {"fallacy_type": "Ad hominem", "confidence": 0.5},
                {"fallacy_type": "Appel à la peur", "confidence": 0.5},
            ],
        }
        result = analyzer._identify_persuasion_strategies(data)
        total = sum(result.values())
        assert abs(total - 1.0) < 0.01


class TestAnalyzeRhetoricalResults:
    @pytest.fixture
    def analyzer(self):
        return _make_analyzer()

    def test_full_analysis_structure(self, analyzer):
        result = analyzer.analyze_rhetorical_results({}, "général")
        assert "overall_analysis" in result
        assert "fallacy_analysis" in result
        assert "coherence_analysis" in result
        assert "persuasion_analysis" in result
        assert "recommendations" in result
        assert "context" in result
        assert "analysis_timestamp" in result

    def test_overall_analysis_fields(self, analyzer):
        result = analyzer.analyze_rhetorical_results({}, "général")
        overall = result["overall_analysis"]
        assert "rhetorical_quality" in overall
        assert "rhetorical_quality_level" in overall
        assert "main_strengths" in overall
        assert "main_weaknesses" in overall
        assert "context_relevance" in overall

    def test_history_updated(self, analyzer):
        assert len(analyzer.analysis_history) == 0
        analyzer.analyze_rhetorical_results({}, "politique")
        assert len(analyzer.analysis_history) == 1
        assert analyzer.analysis_history[0]["context"] == "politique"

    def test_multiple_analyses_accumulate_history(self, analyzer):
        analyzer.analyze_rhetorical_results({}, "politique")
        analyzer.analyze_rhetorical_results({}, "scientifique")
        assert len(analyzer.analysis_history) == 2

    def test_context_preserved(self, analyzer):
        result = analyzer.analyze_rhetorical_results({}, "juridique")
        assert result["context"] == "juridique"

    def test_rich_results_input(self, analyzer):
        results = {
            "complex_fallacy_analysis": {
                "individual_fallacies_count": 3,
                "basic_combinations": [{"id": 1}],
                "advanced_combinations": [],
                "composite_severity": {
                    "adjusted_severity": 0.6,
                    "severity_level": "Modéré",
                },
            },
            "contextual_fallacy_analysis": {
                "contextual_fallacies": [
                    {"fallacy_type": "Ad hominem", "confidence": 0.8},
                ],
                "context_analysis": {
                    "context_type": "politique",
                    "confidence": 0.7,
                },
            },
            "argument_coherence_evaluation": {
                "coherence_score": 0.7,
                "coherence_level": "Bon",
                "thematic_clusters": [{"id": 1}],
                "logical_flows": [{"id": 1}],
            },
        }
        result = analyzer.analyze_rhetorical_results(results, "politique")
        assert result["fallacy_analysis"]["total_fallacies"] == 4
        assert result["coherence_analysis"]["overall_coherence"] == 0.7
        assert isinstance(result["overall_analysis"]["rhetorical_quality"], float)
