# -*- coding: utf-8 -*-
"""
Comprehensive tests for analysis tools:
- ContextualFallacyDetector (rule-based, no external deps beyond numpy)
- RhetoricalResultVisualizer (pure string generation)
- ArgumentCoherenceEvaluator (needs mock for SemanticArgumentAnalyzer)
- FactClaimExtractor data structures (enums + dataclass, needs mock for spacy)
"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import datetime


# ---------------------------------------------------------------------------
# 1. ContextualFallacyDetector tests
# ---------------------------------------------------------------------------

from argumentation_analysis.agents.tools.analysis.new.contextual_fallacy_detector import (
    ContextualFallacyDetector,
)


class TestContextualFallacyDetector:
    """Tests for ContextualFallacyDetector rule-based fallacy detection."""

    @pytest.fixture
    def detector(self):
        return ContextualFallacyDetector()

    # -- Initialization --

    def test_init_creates_contextual_factors(self, detector):
        """__init__ should populate contextual_factors dict."""
        assert isinstance(detector.contextual_factors, dict)
        assert "domain" in detector.contextual_factors
        assert "audience" in detector.contextual_factors
        assert "medium" in detector.contextual_factors
        assert "purpose" in detector.contextual_factors

    def test_init_creates_contextual_fallacies(self, detector):
        """__init__ should populate contextual_fallacies dict with at least 5 types."""
        assert isinstance(detector.contextual_fallacies, dict)
        assert len(detector.contextual_fallacies) >= 5
        expected_keys = [
            "appel_inapproprié_autorité",
            "appel_inapproprié_émotion",
            "appel_inapproprié_tradition",
            "appel_inapproprié_nouveauté",
            "appel_inapproprié_popularité",
        ]
        for key in expected_keys:
            assert key in detector.contextual_fallacies

    def test_init_empty_detection_history(self, detector):
        """__init__ should start with empty detection_history."""
        assert detector.detection_history == []

    # -- _define_contextual_factors --

    def test_define_contextual_factors_structure(self, detector):
        """Each factor should have a description and a list of values."""
        factors = detector._define_contextual_factors()
        for factor_name, factor_data in factors.items():
            assert "description" in factor_data
            assert "values" in factor_data
            assert isinstance(factor_data["values"], list)
            assert len(factor_data["values"]) > 0

    # -- _define_contextual_fallacies --

    def test_define_contextual_fallacies_structure(self, detector):
        """Each fallacy type should have description, markers, and contextual_rules."""
        fallacies = detector._define_contextual_fallacies()
        for fallacy_type, fallacy_data in fallacies.items():
            assert "description" in fallacy_data
            assert "markers" in fallacy_data
            assert isinstance(fallacy_data["markers"], list)
            assert "contextual_rules" in fallacy_data

    # -- _infer_contextual_factors --

    def test_infer_domain_scientifique(self, detector):
        factors = detector._infer_contextual_factors("contexte de science et recherche")
        assert factors["domain"] == "scientifique"

    def test_infer_domain_politique(self, detector):
        factors = detector._infer_contextual_factors("un discours politique au parlement")
        assert factors["domain"] == "politique"

    def test_infer_domain_juridique(self, detector):
        factors = detector._infer_contextual_factors("une affaire juridique au tribunal")
        assert factors["domain"] == "juridique"

    def test_infer_domain_medical(self, detector):
        factors = detector._infer_contextual_factors("un contexte médical de santé publique")
        assert factors["domain"] == "médical"

    def test_infer_domain_commercial(self, detector):
        factors = detector._infer_contextual_factors("une campagne de marketing commercial")
        assert factors["domain"] == "commercial"

    def test_infer_domain_default_general(self, detector):
        factors = detector._infer_contextual_factors("une discussion quelconque")
        assert factors["domain"] == "général"

    def test_infer_audience_expert(self, detector):
        factors = detector._infer_contextual_factors("un public expert")
        assert factors["audience"] == "expert"

    def test_infer_audience_academique(self, detector):
        factors = detector._infer_contextual_factors("un contexte académique universitaire")
        assert factors["audience"] == "académique"

    def test_infer_audience_default_generaliste(self, detector):
        factors = detector._infer_contextual_factors("quelque chose de banal")
        assert factors["audience"] == "généraliste"

    def test_infer_medium_ecrit(self, detector):
        factors = detector._infer_contextual_factors("un article écrit dans un journal")
        assert factors["medium"] == "écrit"

    def test_infer_medium_default(self, detector):
        factors = detector._infer_contextual_factors("un sujet lambda")
        assert factors["medium"] == "général"

    def test_infer_purpose_informer(self, detector):
        factors = detector._infer_contextual_factors("un texte pour informer le lecteur")
        assert factors["purpose"] == "informer"

    def test_infer_purpose_default(self, detector):
        factors = detector._infer_contextual_factors("un sujet lambda")
        assert factors["purpose"] == "général"

    def test_infer_all_four_factors_present(self, detector):
        """Even a vague description should produce all four factor keys."""
        factors = detector._infer_contextual_factors("texte simple")
        assert set(factors.keys()) == {"domain", "audience", "medium", "purpose"}

    # -- _calculate_contextual_severity --

    def test_severity_scientific_authority(self, detector):
        """Authority appeal in scientific context should be high severity (0.9)."""
        severity = detector._calculate_contextual_severity(
            "appel_inapproprié_autorité", {"domain": "scientifique"}
        )
        assert severity == 0.9

    def test_severity_commercial_authority(self, detector):
        """Authority appeal in commercial context should have lower severity (0.6)."""
        severity = detector._calculate_contextual_severity(
            "appel_inapproprié_autorité", {"domain": "commercial"}
        )
        assert severity == 0.6

    def test_severity_unknown_domain_returns_base(self, detector):
        """Unknown domain should fall back to base severity 0.5."""
        severity = detector._calculate_contextual_severity(
            "appel_inapproprié_autorité", {"domain": "inconnu"}
        )
        assert severity == 0.5

    def test_severity_unknown_fallacy_returns_base(self, detector):
        """Unknown fallacy type should return base severity 0.5."""
        severity = detector._calculate_contextual_severity(
            "sophisme_inexistant", {"domain": "scientifique"}
        )
        assert severity == 0.5

    def test_severity_emotion_scientific(self, detector):
        """Emotion appeal in scientific context should be 0.9."""
        severity = detector._calculate_contextual_severity(
            "appel_inapproprié_émotion", {"domain": "scientifique"}
        )
        assert severity == 0.9

    def test_severity_tradition_religieux_low(self, detector):
        """Tradition appeal in religious context should be low severity (0.3)."""
        severity = detector._calculate_contextual_severity(
            "appel_inapproprié_tradition", {"domain": "religieux"}
        )
        assert severity == 0.3

    # -- detect_contextual_fallacies (single argument) --

    def test_detect_authority_marker_in_scientific_context(self, detector):
        """'expert' marker in scientific context should trigger authority fallacy."""
        result = detector.detect_contextual_fallacies(
            "Un expert a prouvé cette théorie.",
            "contexte de science",
        )
        assert "detected_fallacies" in result
        fallacies = result["detected_fallacies"]
        # Should detect at least the authority appeal (marker "expert", domain scientifique -> 0.9)
        types = [f["fallacy_type"] for f in fallacies]
        assert "appel_inapproprié_autorité" in types

    def test_detect_emotion_marker_in_scientific_context(self, detector):
        """Emotion markers in scientific context should detect emotion fallacy."""
        result = detector.detect_contextual_fallacies(
            "La peur de cette maladie est justifiée par les données.",
            "contexte de science",
        )
        fallacies = result["detected_fallacies"]
        types = [f["fallacy_type"] for f in fallacies]
        assert "appel_inapproprié_émotion" in types

    def test_no_markers_empty_fallacies(self, detector):
        """Text with no fallacy markers should return empty detected_fallacies list."""
        result = detector.detect_contextual_fallacies(
            "Le ciel est bleu.",
            "contexte de science",
        )
        assert result["detected_fallacies"] == []

    def test_detect_returns_argument_in_result(self, detector):
        """Result dict should contain the original argument."""
        arg = "Un argument quelconque."
        result = detector.detect_contextual_fallacies(arg, "contexte quelconque")
        assert result["argument"] == arg

    def test_detect_returns_context_description(self, detector):
        result = detector.detect_contextual_fallacies("texte", "un contexte précis")
        assert result["context_description"] == "un contexte précis"

    def test_detect_returns_timestamp(self, detector):
        result = detector.detect_contextual_fallacies("texte", "contexte")
        assert "analysis_timestamp" in result

    def test_detect_with_explicit_contextual_factors(self, detector):
        """Explicit contextual_factors should override inference."""
        result = detector.detect_contextual_fallacies(
            "L'expert recommande ce produit.",
            "contexte vague",
            contextual_factors={"domain": "scientifique"},
        )
        assert result["contextual_factors"]["domain"] == "scientifique"
        fallacies = result["detected_fallacies"]
        # In scientific context, "expert" should trigger authority appeal with severity > 0.5
        types = [f["fallacy_type"] for f in fallacies]
        assert "appel_inapproprié_autorité" in types

    def test_detect_commercial_low_severity_no_detection(self, detector):
        """Popularity appeal in commercial context has severity 0.4, below 0.5 threshold."""
        result = detector.detect_contextual_fallacies(
            "Tout le monde achète ce produit.",
            "marketing commercial",
        )
        fallacies = result["detected_fallacies"]
        types = [f["fallacy_type"] for f in fallacies]
        # appel_inapproprié_popularité in commercial domain has severity 0.4 -> NOT detected
        assert "appel_inapproprié_popularité" not in types

    def test_detected_fallacy_contains_severity(self, detector):
        """Each detected fallacy should include its severity score."""
        result = detector.detect_contextual_fallacies(
            "Selon l'expert, c'est vrai.",
            "contexte de science",
        )
        for f in result["detected_fallacies"]:
            assert "severity" in f
            assert isinstance(f["severity"], float)
            assert f["severity"] > 0.5

    def test_detected_fallacy_contains_marker(self, detector):
        """Each detected fallacy should reference the marker that triggered it."""
        result = detector.detect_contextual_fallacies(
            "L'expert dit que c'est correct.",
            "contexte de science",
        )
        for f in result["detected_fallacies"]:
            assert "marker" in f

    # -- detect_multiple_contextual_fallacies --

    def test_multiple_arguments_returns_argument_results(self, detector):
        """detect_multiple should return an argument_results list."""
        results = detector.detect_multiple_contextual_fallacies(
            ["Argument 1", "Argument 2"],
            "contexte de science",
        )
        assert "argument_results" in results
        assert len(results["argument_results"]) == 2

    def test_multiple_arguments_each_has_index(self, detector):
        """Each argument result should have its argument_index."""
        results = detector.detect_multiple_contextual_fallacies(
            ["Un expert parle.", "Le ciel est bleu."],
            "contexte de science",
        )
        for i, arg_result in enumerate(results["argument_results"]):
            assert arg_result["argument_index"] == i

    def test_multiple_arguments_updates_detection_history(self, detector):
        """detect_multiple should append to detection_history."""
        assert len(detector.detection_history) == 0
        detector.detect_multiple_contextual_fallacies(
            ["Arg 1"], "contexte de science"
        )
        assert len(detector.detection_history) == 1
        entry = detector.detection_history[0]
        assert entry["type"] == "multiple_contextual_fallacy_detection"
        assert entry["input_arguments_count"] == 1

    def test_multiple_calls_accumulate_history(self, detector):
        """Multiple calls to detect_multiple should accumulate history entries."""
        detector.detect_multiple_contextual_fallacies(["A"], "c1")
        detector.detect_multiple_contextual_fallacies(["B", "C"], "c2")
        assert len(detector.detection_history) == 2

    def test_multiple_mixed_results(self, detector):
        """One arg with markers and one without should give different fallacy counts."""
        results = detector.detect_multiple_contextual_fallacies(
            [
                "Un expert reconnu a validé cette hypothèse.",  # authority marker
                "Le ciel est bleu aujourd'hui.",  # no markers
            ],
            "contexte de science",
        )
        first_fallacies = results["argument_results"][0]["detected_fallacies"]
        second_fallacies = results["argument_results"][1]["detected_fallacies"]
        assert len(first_fallacies) > 0
        assert len(second_fallacies) == 0

    def test_multiple_returns_argument_count(self, detector):
        results = detector.detect_multiple_contextual_fallacies(
            ["a", "b", "c"], "ctx"
        )
        assert results["argument_count"] == 3


# ---------------------------------------------------------------------------
# 2. RhetoricalResultVisualizer tests
# ---------------------------------------------------------------------------

from argumentation_analysis.agents.tools.analysis.rhetorical_result_visualizer import (
    RhetoricalResultVisualizer,
)


class TestRhetoricalResultVisualizer:
    """Tests for RhetoricalResultVisualizer Mermaid diagram generation."""

    @pytest.fixture
    def visualizer(self):
        return RhetoricalResultVisualizer()

    @pytest.fixture
    def empty_state(self):
        return {}

    @pytest.fixture
    def state_with_args_only(self):
        return {
            "identified_arguments": {
                "arg_1": "First argument text",
                "arg_2": "Second argument text",
            },
            "identified_fallacies": {},
        }

    @pytest.fixture
    def full_state(self):
        return {
            "identified_arguments": {
                "arg_1": "Experts say this product is safe and effective.",
                "arg_2": "Millions of people already use this product.",
                "arg_3": "If you don't use this product, you risk health problems.",
            },
            "identified_fallacies": {
                "fallacy_1": {
                    "type": "Ad hominem",
                    "target_argument_id": "arg_1",
                },
                "fallacy_2": {
                    "type": "Straw man",
                    "target_argument_id": "arg_2",
                },
                "fallacy_3": {
                    "type": "Ad hominem",
                    "target_argument_id": "arg_3",
                },
            },
        }

    # -- generate_argument_graph --

    def test_argument_graph_empty_state(self, visualizer, empty_state):
        """Empty state should produce a graph with 'Aucun argument' message."""
        graph = visualizer.generate_argument_graph(empty_state)
        assert "Aucun argument identifié" in graph

    def test_argument_graph_with_arguments(self, visualizer, full_state):
        """Full state should produce 'graph TD' with argument and fallacy nodes."""
        graph = visualizer.generate_argument_graph(full_state)
        assert graph.startswith("graph TD")
        assert "arg_1" in graph
        assert "arg_2" in graph
        assert "fallacy_1" in graph
        # Check edges: arg -> fallacy links
        assert "arg_1 --> fallacy_1" in graph

    def test_argument_graph_truncates_long_text(self, visualizer):
        """Arguments longer than 50 chars should be truncated with '...'."""
        state = {
            "identified_arguments": {
                "arg_1": "A" * 100,
            },
            "identified_fallacies": {},
        }
        graph = visualizer.generate_argument_graph(state)
        assert "..." in graph
        # The node should not contain the full 100-char string
        assert "A" * 100 not in graph

    def test_argument_graph_fallacy_without_valid_target(self, visualizer):
        """A fallacy with an invalid target_argument_id should be an isolated node."""
        state = {
            "identified_arguments": {"arg_1": "Some text"},
            "identified_fallacies": {
                "fallacy_1": {"type": "Red herring", "target_argument_id": "arg_missing"},
            },
        }
        graph = visualizer.generate_argument_graph(state)
        assert "fallacy_1" in graph
        # Should not have an edge since target is missing
        assert "-->" not in graph

    def test_argument_graph_args_only_no_edges(self, visualizer, state_with_args_only):
        """State with only arguments and no fallacies should have no edges."""
        graph = visualizer.generate_argument_graph(state_with_args_only)
        assert "arg_1" in graph
        assert "-->" not in graph

    # -- generate_fallacy_distribution --

    def test_fallacy_distribution_empty(self, visualizer, empty_state):
        """Empty state should show 'Aucun sophisme identifié' pie chart."""
        pie = visualizer.generate_fallacy_distribution(empty_state)
        assert "Aucun sophisme identifié" in pie

    def test_fallacy_distribution_with_fallacies(self, visualizer, full_state):
        """Full state should generate a pie chart with fallacy type counts."""
        pie = visualizer.generate_fallacy_distribution(full_state)
        assert pie.startswith("pie")
        assert "Distribution des sophismes" in pie
        # Ad hominem appears 2 times, Straw man 1 time
        assert '"Ad hominem" : 2' in pie
        assert '"Straw man" : 1' in pie

    def test_fallacy_distribution_single_type(self, visualizer):
        """Single fallacy type should have count 1."""
        state = {
            "identified_fallacies": {
                "f1": {"type": "Slippery slope"},
            },
        }
        pie = visualizer.generate_fallacy_distribution(state)
        assert '"Slippery slope" : 1' in pie

    # -- generate_argument_quality_heatmap --

    def test_heatmap_empty_state(self, visualizer, empty_state):
        """Empty state should produce heatmap with 'Aucun argument identifié'."""
        hm = visualizer.generate_argument_quality_heatmap(empty_state)
        assert "Aucun argument identifié" in hm

    def test_heatmap_quality_formula(self, visualizer):
        """Quality = max(0, 10 - 2 * fallacy_count). Arg with 1 fallacy -> quality 8."""
        state = {
            "identified_arguments": {"arg_1": "Some argument text here"},
            "identified_fallacies": {
                "f1": {"type": "X", "target_argument_id": "arg_1"},
            },
        }
        hm = visualizer.generate_argument_quality_heatmap(state)
        assert ": 8" in hm

    def test_heatmap_no_fallacies_quality_10(self, visualizer, state_with_args_only):
        """Arguments with no fallacies should have quality 10."""
        hm = visualizer.generate_argument_quality_heatmap(state_with_args_only)
        assert ": 10" in hm

    def test_heatmap_many_fallacies_quality_zero(self, visualizer):
        """6 fallacies targeting one arg: quality = max(0, 10 - 12) = 0."""
        state = {
            "identified_arguments": {"arg_1": "Text"},
            "identified_fallacies": {
                f"f{i}": {"type": "X", "target_argument_id": "arg_1"}
                for i in range(6)
            },
        }
        hm = visualizer.generate_argument_quality_heatmap(state)
        assert ": 0" in hm

    def test_heatmap_truncates_long_arg_text(self, visualizer):
        """Arguments longer than 30 chars should be truncated in heatmap."""
        state = {
            "identified_arguments": {"arg_1": "B" * 50},
            "identified_fallacies": {},
        }
        hm = visualizer.generate_argument_quality_heatmap(state)
        assert "..." in hm

    # -- generate_all_visualizations --

    def test_all_visualizations_returns_three_keys(self, visualizer, full_state):
        """generate_all_visualizations should return a dict with 3 visualization keys."""
        result = visualizer.generate_all_visualizations(full_state)
        assert "argument_graph" in result
        assert "fallacy_distribution" in result
        assert "argument_quality_heatmap" in result

    def test_all_visualizations_values_are_strings(self, visualizer, full_state):
        result = visualizer.generate_all_visualizations(full_state)
        for key, value in result.items():
            assert isinstance(value, str)

    # -- generate_html_report --

    def test_html_report_is_valid_html(self, visualizer, full_state):
        """HTML report should contain basic HTML structure elements."""
        html = visualizer.generate_html_report(full_state)
        assert "<!DOCTYPE html>" in html
        assert "<html>" in html
        assert "</html>" in html
        assert "<head>" in html
        assert "<body>" in html

    def test_html_report_contains_mermaid_script(self, visualizer, full_state):
        """HTML report should include the Mermaid.js CDN script."""
        html = visualizer.generate_html_report(full_state)
        assert "mermaid" in html.lower()
        assert "cdn.jsdelivr.net" in html

    def test_html_report_contains_all_sections(self, visualizer, full_state):
        """HTML report should contain headings for all three visualization sections."""
        html = visualizer.generate_html_report(full_state)
        assert "Graphe des Arguments" in html
        assert "Distribution des Sophismes" in html
        assert "Qualité des Arguments" in html

    def test_html_report_contains_graph_data(self, visualizer, full_state):
        """HTML report should embed the Mermaid graph code."""
        html = visualizer.generate_html_report(full_state)
        assert "graph TD" in html


# ---------------------------------------------------------------------------
# 3. ArgumentCoherenceEvaluator tests (requires mocking SemanticArgumentAnalyzer)
# ---------------------------------------------------------------------------


class TestArgumentCoherenceEvaluator:
    """Tests for ArgumentCoherenceEvaluator with mocked SemanticArgumentAnalyzer."""

    @pytest.fixture
    def mock_analyzer(self):
        """Create a mock SemanticArgumentAnalyzer."""
        mock = MagicMock()
        mock.analyze_multiple_arguments.return_value = {
            "argument_count": 2,
            "analyses": [],
        }
        return mock

    @pytest.fixture
    def evaluator(self, mock_analyzer):
        """Create evaluator with mocked SemanticArgumentAnalyzer."""
        with patch(
            "argumentation_analysis.agents.tools.analysis.new.argument_coherence_evaluator.SemanticArgumentAnalyzer",
            return_value=mock_analyzer,
        ):
            from argumentation_analysis.agents.tools.analysis.new.argument_coherence_evaluator import (
                ArgumentCoherenceEvaluator,
            )
            return ArgumentCoherenceEvaluator()

    def test_init_creates_coherence_types(self, evaluator):
        """Evaluator should have 5 coherence type definitions."""
        assert len(evaluator.coherence_types) == 5
        expected = {"logique", "thématique", "structurelle", "rhétorique", "épistémique"}
        assert set(evaluator.coherence_types.keys()) == expected

    def test_coherence_types_importances_sum_to_one(self, evaluator):
        """The importance weights should sum to 1.0."""
        total = sum(ct["importance"] for ct in evaluator.coherence_types.values())
        assert abs(total - 1.0) < 1e-9

    def test_evaluate_coherence_returns_required_keys(self, evaluator):
        """evaluate_coherence should return overall, evaluations, recommendations, context."""
        result = evaluator.evaluate_coherence(
            ["Arg 1", "Arg 2"], context="test context"
        )
        assert "overall_coherence" in result
        assert "coherence_evaluations" in result
        assert "recommendations" in result
        assert "context" in result
        assert "timestamp" in result

    def test_evaluate_coherence_five_dimensions(self, evaluator):
        """coherence_evaluations should contain all 5 dimensions."""
        result = evaluator.evaluate_coherence(["A", "B"])
        evals = result["coherence_evaluations"]
        expected = {"logique", "thématique", "structurelle", "rhétorique", "épistémique"}
        assert set(evals.keys()) == expected

    def test_evaluate_coherence_each_dimension_has_score(self, evaluator):
        """Each dimension evaluation should contain a numeric score."""
        result = evaluator.evaluate_coherence(["A", "B"])
        for dim_name, dim_eval in result["coherence_evaluations"].items():
            assert "score" in dim_eval
            assert isinstance(dim_eval["score"], (int, float))
            assert 0.0 <= dim_eval["score"] <= 1.0

    def test_evaluate_coherence_overall_score_range(self, evaluator):
        """Overall score should be between 0 and 1."""
        result = evaluator.evaluate_coherence(["A", "B", "C"])
        score = result["overall_coherence"]["score"]
        assert 0.0 <= score <= 1.0

    def test_evaluate_coherence_overall_level(self, evaluator):
        """Overall coherence should have a textual level."""
        result = evaluator.evaluate_coherence(["A", "B"])
        level = result["overall_coherence"]["level"]
        assert level in ("Excellent", "Bon", "Moyen", "Faible", "Très faible")

    def test_evaluate_coherence_default_context(self, evaluator):
        """When no context is given, a default should be used."""
        result = evaluator.evaluate_coherence(["A"])
        assert result["context"] == "Analyse d'arguments"

    def test_evaluate_coherence_explicit_context(self, evaluator):
        """Explicit context should be preserved in result."""
        result = evaluator.evaluate_coherence(["A"], context="philosophie")
        assert result["context"] == "philosophie"

    def test_evaluate_coherence_recommendations_type(self, evaluator):
        """Recommendations should be a list of strings."""
        result = evaluator.evaluate_coherence(["A", "B"])
        recs = result["recommendations"]
        assert isinstance(recs, list)
        for rec in recs:
            assert isinstance(rec, str)

    def test_evaluate_coherence_few_args_recommendation(self, evaluator):
        """With fewer than 3 arguments, a recommendation to add more should appear."""
        result = evaluator.evaluate_coherence(["A", "B"])
        recs = result["recommendations"]
        has_add_more = any("supplémentaires" in r for r in recs)
        assert has_add_more, "Should recommend adding more arguments when < 3"

    def test_evaluate_coherence_many_args_recommendation(self, evaluator):
        """With more than 7 arguments, a consolidation recommendation should appear."""
        args = [f"Arg {i}" for i in range(8)]
        result = evaluator.evaluate_coherence(args)
        recs = result["recommendations"]
        has_consolidate = any("consolidation" in r for r in recs)
        assert has_consolidate, "Should recommend consolidation when > 7 args"

    def test_overall_coherence_strengths_weaknesses(self, evaluator):
        """Overall coherence should list strengths and weaknesses."""
        result = evaluator.evaluate_coherence(["A", "B", "C", "D"])
        overall = result["overall_coherence"]
        assert "strengths" in overall
        assert "weaknesses" in overall
        assert isinstance(overall["strengths"], list)
        assert isinstance(overall["weaknesses"], list)


# ---------------------------------------------------------------------------
# 4. FactClaim data structures (enums + dataclass, spacy mocked at import)
# ---------------------------------------------------------------------------


class TestFactClaimDataStructures:
    """Tests for ClaimType, ClaimVerifiability enums and FactualClaim dataclass."""

    def test_claim_type_has_10_values(self):
        """ClaimType enum should have exactly 10 members."""
        # We mock spacy at import time since the module imports it at top level
        mock_spacy = MagicMock()
        with patch.dict("sys.modules", {"spacy": mock_spacy}):
            from argumentation_analysis.agents.tools.analysis.fact_claim_extractor import (
                ClaimType,
            )
            assert len(ClaimType) == 10

    def test_claim_type_values(self):
        """ClaimType should include all expected enum values."""
        mock_spacy = MagicMock()
        with patch.dict("sys.modules", {"spacy": mock_spacy}):
            from argumentation_analysis.agents.tools.analysis.fact_claim_extractor import (
                ClaimType,
            )
            expected = {
                "statistical", "historical", "scientific", "geographical",
                "biographical", "numerical", "temporal", "causal",
                "definitional", "quote",
            }
            actual = {ct.value for ct in ClaimType}
            assert actual == expected

    def test_claim_verifiability_has_5_values(self):
        """ClaimVerifiability enum should have exactly 5 members."""
        mock_spacy = MagicMock()
        with patch.dict("sys.modules", {"spacy": mock_spacy}):
            from argumentation_analysis.agents.tools.analysis.fact_claim_extractor import (
                ClaimVerifiability,
            )
            assert len(ClaimVerifiability) == 5

    def test_claim_verifiability_values(self):
        """ClaimVerifiability should include all expected levels."""
        mock_spacy = MagicMock()
        with patch.dict("sys.modules", {"spacy": mock_spacy}):
            from argumentation_analysis.agents.tools.analysis.fact_claim_extractor import (
                ClaimVerifiability,
            )
            expected = {
                "highly_verifiable", "moderately_verifiable",
                "partially_verifiable", "subjective", "opinion",
            }
            actual = {cv.value for cv in ClaimVerifiability}
            assert actual == expected

    def test_factual_claim_creation(self):
        """FactualClaim dataclass should be instantiable with all required fields."""
        mock_spacy = MagicMock()
        with patch.dict("sys.modules", {"spacy": mock_spacy}):
            from argumentation_analysis.agents.tools.analysis.fact_claim_extractor import (
                FactualClaim, ClaimType, ClaimVerifiability,
            )
            claim = FactualClaim(
                claim_text="50% of people agree",
                claim_type=ClaimType.STATISTICAL,
                verifiability=ClaimVerifiability.HIGHLY_VERIFIABLE,
                confidence=0.85,
                context="In a survey, 50% of people agree with the statement.",
                start_pos=15,
                end_pos=35,
                entities=[{"text": "50%", "label": "PERCENT"}],
                keywords=["statistique"],
                temporal_references=[],
                numerical_values=[{"value": 50.0, "unit": "%"}],
                sources_mentioned=["survey"],
                extraction_method="pattern_based",
            )
            assert claim.claim_text == "50% of people agree"
            assert claim.claim_type == ClaimType.STATISTICAL
            assert claim.confidence == 0.85

    def test_factual_claim_to_dict(self):
        """FactualClaim.to_dict() should return a dict with enum values as strings."""
        mock_spacy = MagicMock()
        with patch.dict("sys.modules", {"spacy": mock_spacy}):
            from argumentation_analysis.agents.tools.analysis.fact_claim_extractor import (
                FactualClaim, ClaimType, ClaimVerifiability,
            )
            claim = FactualClaim(
                claim_text="In 1969, man landed on the moon.",
                claim_type=ClaimType.HISTORICAL,
                verifiability=ClaimVerifiability.HIGHLY_VERIFIABLE,
                confidence=0.95,
                context="In 1969, man landed on the moon during the Apollo mission.",
                start_pos=0,
                end_pos=31,
                entities=[],
                keywords=["historique"],
                temporal_references=["1969"],
                numerical_values=[{"value": 1969.0, "unit": ""}],
                sources_mentioned=[],
                extraction_method="pattern_based",
            )
            d = claim.to_dict()
            assert isinstance(d, dict)
            # Enum values should be serialized as strings
            assert d["claim_type"] == "historical"
            assert d["verifiability"] == "highly_verifiable"
            assert d["confidence"] == 0.95
            assert d["start_pos"] == 0
            assert d["end_pos"] == 31
            assert d["extraction_method"] == "pattern_based"
            assert d["temporal_references"] == ["1969"]

    def test_factual_claim_to_dict_all_keys(self):
        """to_dict() should produce all 12 expected keys."""
        mock_spacy = MagicMock()
        with patch.dict("sys.modules", {"spacy": mock_spacy}):
            from argumentation_analysis.agents.tools.analysis.fact_claim_extractor import (
                FactualClaim, ClaimType, ClaimVerifiability,
            )
            claim = FactualClaim(
                claim_text="test",
                claim_type=ClaimType.CAUSAL,
                verifiability=ClaimVerifiability.SUBJECTIVE,
                confidence=0.5,
                context="ctx",
                start_pos=0,
                end_pos=4,
                entities=[],
                keywords=[],
                temporal_references=[],
                numerical_values=[],
                sources_mentioned=[],
                extraction_method="test",
            )
            d = claim.to_dict()
            expected_keys = {
                "claim_text", "claim_type", "verifiability", "confidence",
                "context", "start_pos", "end_pos", "entities", "keywords",
                "temporal_references", "numerical_values", "sources_mentioned",
                "extraction_method",
            }
            assert set(d.keys()) == expected_keys
