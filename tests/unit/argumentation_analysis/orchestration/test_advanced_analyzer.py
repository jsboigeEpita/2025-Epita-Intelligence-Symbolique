# Authentic gpt-5-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

from typing import Dict, Any, Optional

# -*- coding: utf-8 -*-
"""Tests pour l'orchestrateur d'analyse avancée."""

import pytest
import logging
from unittest.mock import MagicMock


from argumentation_analysis.orchestration.advanced_analyzer import (
    analyze_extract_advanced,
)
from argumentation_analysis.mocks.advanced_tools import (
    MockEnhancedComplexFallacyAnalyzer,
    MockEnhancedContextualFallacyAnalyzer,
    MockEnhancedFallacySeverityEvaluator,
    MockEnhancedRhetoricalResultAnalyzer,
)

from plugins.AnalysisToolsPlugin.plugin import AnalysisToolsPlugin


@pytest.fixture
def mock_plugin() -> MagicMock:
    """Fournit un mock du AnalysisToolsPlugin."""
    plugin = MagicMock(spec=AnalysisToolsPlugin)
    mock_analysis_result = {
        "complex_fallacies": {
            "mock_result": True,
            "details": "Mocked complex analysis",
        },
        "contextual_fallacies": {
            "mock_result": True,
            "details": "Mocked contextual analysis",
        },
        "fallacy_severity": {"mock_result": True, "score": 0.8},
        "rhetorical_results": {
            "overall_analysis": {
                "rhetorical_quality": 0.9,
                "clarity_score": 0.85,
                "engagement_score": 0.92,
            },
            "details": "This is a mocked rhetorical analysis.",
        },
    }
    plugin.analyze_text.return_value = mock_analysis_result
    return plugin


@pytest.fixture
def sample_extract_definition() -> Dict[str, Any]:
    """Fournit une définition d'extrait simple."""
    return {
        "extract_name": "Test Extrait 1",
        "extract_text": "Ceci est le premier argument. Et voici un second argument.",
        "context": {"domain": "general_test"},
    }


@pytest.fixture
def sample_base_result() -> Dict[str, Any]:
    """Fournit un résultat d'analyse de base simple."""
    return {
        "extract_name": "Test Extrait 1",
        "source_name": "TestSource",
        "analyses": {
            "contextual_fallacies": {"base_found": True, "count": 1},
            "argument_coherence": {"score": 0.7},
            "semantic_analysis": {"sentiment": "neutral"},
        },
    }


@pytest.fixture
def mock_generate_sample(mocker: MagicMock) -> MagicMock:
    """Mock la fonction generate_sample_text."""
    # On doit patcher la fonction là où elle est importée/utilisée, et non là où elle est définie.
    return mocker.patch(
        "argumentation_analysis.orchestration.advanced_analyzer.generate_sample_text"
    )


@pytest.fixture
def mock_split_args(mocker: MagicMock) -> MagicMock:
    """Mock la fonction split_text_into_arguments."""
    return mocker.patch(
        "argumentation_analysis.orchestration.advanced_analyzer.split_text_into_arguments"
    )


def test_analyze_extract_advanced_successful_run(
    sample_extract_definition: Dict[str, Any],
    mock_plugin: MagicMock,
    sample_base_result: Optional[Dict[str, Any]],
):
    """Teste un déroulement réussi de l'analyse avancée avec le plugin."""
    source_name = "TestSource"

    results = analyze_extract_advanced(
        sample_extract_definition, source_name, sample_base_result, plugin=mock_plugin
    )

    assert results["extract_name"] == sample_extract_definition["extract_name"]
    assert results["source_name"] == source_name
    assert "timestamp" in results

    # Les résultats d'analyse proviennent maintenant directement du mock_plugin
    analyses = results["analyses"]
    assert "complex_fallacies" in analyses
    assert analyses["complex_fallacies"]["details"] == "Mocked complex analysis"

    # La comparaison avec la base est toujours gérée par l'orchestrateur
    assert "comparison_with_base" in results
    assert "error" not in results["comparison_with_base"]

    # Vérifier que le plugin a bien été appelé
    mock_plugin.analyze_text.assert_called_once_with(
        text=sample_extract_definition["extract_text"],
        context=sample_extract_definition["context"],
    )


def test_analyze_extract_advanced_no_base_result(
    sample_extract_definition: Dict[str, Any], mock_plugin: MagicMock
):
    """Teste l'analyse sans résultat de base."""
    source_name = "TestSource"
    results = analyze_extract_advanced(
        sample_extract_definition, source_name, None, plugin=mock_plugin
    )

    assert "comparison_with_base" not in results
    assert "rhetorical_results" in results["analyses"]
    assert (
        results["analyses"]["rhetorical_results"]["details"]
        == "This is a mocked rhetorical analysis."
    )


def test_analyze_extract_advanced_missing_text_uses_sample(
    mock_generate_sample: MagicMock,
    sample_extract_definition: Dict[str, Any],
    mock_plugin: MagicMock,
):
    """Teste que generate_sample_text est appelé si extract_text est manquant."""
    mock_generate_sample.return_value = "Texte d'exemple généré."
    extract_def_no_text = sample_extract_definition.copy()
    extract_def_no_text.pop("extract_text", None)

    analyze_extract_advanced(
        extract_def_no_text, "TestSource", None, plugin=mock_plugin
    )
    mock_generate_sample.assert_called_once()


def test_analyze_extract_advanced_plugin_exception_handling(
    sample_extract_definition: Dict[str, Any], mock_plugin: MagicMock, caplog
):
    """Teste la gestion d'exception si le plugin.analyze_text échoue."""
    source_name = "TestSource"

    # Configurer le mock pour lever une exception
    test_error = ValueError("Erreur plugin test")
    mock_plugin.analyze_text.side_effect = test_error

    with caplog.at_level(logging.ERROR):
        results = analyze_extract_advanced(
            sample_extract_definition, source_name, None, plugin=mock_plugin
        )

    # L'orchestrateur doit attraper l'erreur et la retourner dans un format propre
    assert "error" in results
    assert "Erreur du plugin" in results["error"]
    assert str(test_error) in results["error"]
    assert "Erreur lors de l'appel au AnalysisToolsPlugin" in caplog.text
