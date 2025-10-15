# -*- coding: utf-8 -*-
"""Tests pour les outils d'analyse rhétorique avancés simulés."""

import pytest
from argumentation_analysis.mocks.advanced_tools import (
    create_mock_advanced_rhetorical_tools,
    MockEnhancedComplexFallacyAnalyzer,
    MockEnhancedContextualFallacyAnalyzer,
    MockEnhancedFallacySeverityEvaluator,
    MockEnhancedRhetoricalResultAnalyzer,
)
from datetime import datetime


def test_create_mock_advanced_rhetorical_tools_structure():
    """Vérifie la structure du dictionnaire d'outils retourné."""
    tools = create_mock_advanced_rhetorical_tools()
    assert isinstance(tools, dict)
    assert "complex_fallacy_analyzer" in tools
    assert "contextual_fallacy_analyzer" in tools
    assert "fallacy_severity_evaluator" in tools
    assert "rhetorical_result_analyzer" in tools

    assert isinstance(
        tools["complex_fallacy_analyzer"], MockEnhancedComplexFallacyAnalyzer
    )
    assert isinstance(
        tools["contextual_fallacy_analyzer"], MockEnhancedContextualFallacyAnalyzer
    )
    assert isinstance(
        tools["fallacy_severity_evaluator"], MockEnhancedFallacySeverityEvaluator
    )
    assert isinstance(
        tools["rhetorical_result_analyzer"], MockEnhancedRhetoricalResultAnalyzer
    )


def test_mock_enhanced_complex_fallacy_analyzer():
    """Teste les méthodes de MockEnhancedComplexFallacyAnalyzer."""
    analyzer = MockEnhancedComplexFallacyAnalyzer()
    arguments = ["Argument 1.", "Argument 2."]
    context = {"source": "test_source"}
    result = analyzer.detect_composite_fallacies(arguments, context)

    assert isinstance(result, dict)
    assert result["individual_fallacies_count"] == len(arguments)
    assert "analysis_timestamp" in result
    assert "note" in result
    assert (
        result["note"] == "Analyse simulée - les outils réels ne sont pas disponibles"
    )


def test_mock_enhanced_contextual_fallacy_analyzer():
    """Teste les méthodes de MockEnhancedContextualFallacyAnalyzer."""
    analyzer = MockEnhancedContextualFallacyAnalyzer()
    text = "Ceci est un texte de test."
    context = {"audience": "general"}
    result = analyzer.analyze_context(text, context)

    assert isinstance(result, dict)
    assert "context_analysis" in result
    assert "potential_fallacies_count" in result
    assert "analysis_timestamp" in result
    assert (
        result["note"] == "Analyse simulée - les outils réels ne sont pas disponibles"
    )


def test_mock_enhanced_fallacy_severity_evaluator():
    """Teste les méthodes de MockEnhancedFallacySeverityEvaluator."""
    analyzer = MockEnhancedFallacySeverityEvaluator()
    arguments = ["Un argument avec un sophisme potentiel."]
    context = {"domain": "politics"}
    result = analyzer.evaluate_fallacy_severity(arguments, context)

    assert isinstance(result, dict)
    assert "overall_severity" in result
    assert "severity_level" in result
    assert "analysis_timestamp" in result
    assert (
        result["note"] == "Analyse simulée - les outils réels ne sont pas disponibles"
    )


def test_mock_enhanced_rhetorical_result_analyzer():
    """Teste les méthodes de MockEnhancedRhetoricalResultAnalyzer."""
    analyzer = MockEnhancedRhetoricalResultAnalyzer()
    results_input = {"some_previous_analysis": "data"}
    context = {"purpose": "persuade"}
    result = analyzer.analyze_rhetorical_results(results_input, context)

    assert isinstance(result, dict)
    assert "overall_analysis" in result
    assert "fallacy_analysis" in result
    assert "coherence_analysis" in result
    assert "persuasion_analysis" in result
    assert "recommendations" in result
    assert "analysis_timestamp" in result
    assert (
        result["note"] == "Analyse simulée - les outils réels ne sont pas disponibles"
    )


def test_mock_tools_handle_none_or_empty_inputs():
    """Teste le comportement des mocks avec des entrées None ou vides où applicable."""
    complex_analyzer = MockEnhancedComplexFallacyAnalyzer()
    result_none = complex_analyzer.detect_composite_fallacies(None, {})
    assert result_none["individual_fallacies_count"] == 0
    result_empty = complex_analyzer.detect_composite_fallacies([], {})
    assert result_empty["individual_fallacies_count"] == 0

    contextual_analyzer = MockEnhancedContextualFallacyAnalyzer()
    result_empty_text = contextual_analyzer.analyze_context(
        "", {}
    )  # Doit gérer str vide
    assert "context_analysis" in result_empty_text

    severity_evaluator = MockEnhancedFallacySeverityEvaluator()
    result_sev_none = severity_evaluator.evaluate_fallacy_severity(None, {})
    assert (
        result_sev_none["overall_severity"] is not None
    )  # Doit retourner une structure valide
    result_sev_empty = severity_evaluator.evaluate_fallacy_severity([], {})
    assert result_sev_empty["overall_severity"] is not None

    # Pour RhetoricalResultAnalyzer, l'entrée 'results' est un dict, donc un dict vide est un cas valide.
    rhetorical_analyzer = MockEnhancedRhetoricalResultAnalyzer()
    result_rhet_empty = rhetorical_analyzer.analyze_rhetorical_results({}, {})
    assert "overall_analysis" in result_rhet_empty
