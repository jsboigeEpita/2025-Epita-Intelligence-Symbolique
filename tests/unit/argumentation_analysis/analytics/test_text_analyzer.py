#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour le module text_analyzer.py.
"""

import pytest
import logging
from unittest.mock import MagicMock, patch, AsyncMock

# Cibles pour le patching
ENHANCED_RUNNER_PATH = "argumentation_analysis.orchestration.enhanced_pm_analysis_runner.EnhancedPMAnalysisRunner"

# Importation de la fonction à tester
from argumentation_analysis.analytics.text_analyzer import perform_text_analysis

@pytest.fixture
def mock_services():
    """Fixture pour mocker le dictionnaire de services."""
    return {"llm_service": MagicMock()}

@pytest.mark.asyncio
@patch(ENHANCED_RUNNER_PATH)
async def test_perform_text_analysis_nominal_case(mock_enhanced_runner_class, mock_services, caplog):
    """Teste le cas nominal de perform_text_analysis avec la nouvelle architecture."""
    text_to_analyze = "Ceci est un texte d'exemple pour l'analyse."
    analysis_type = "default_test"
    expected_result = "Résultat de l'analyse améliorée"

    # Configurer le mock pour l'orchestrateur amélioré
    mock_runner_instance = mock_enhanced_runner_class.return_value
    mock_runner_instance.run_enhanced_analysis = AsyncMock(return_value=expected_result)

    result = await perform_text_analysis(text_to_analyze, mock_services, analysis_type)

    # Assertions
    mock_enhanced_runner_class.assert_called_once_with()
    mock_runner_instance.run_enhanced_analysis.assert_awaited_once_with(
        text_content=text_to_analyze,
        llm_service=mock_services["llm_service"]
    )
    assert result == expected_result
    assert f"Lancement de l'analyse de texte améliorée de type '{analysis_type}'" in caplog.text
    assert f"Lancement de l'analyse principale (type: {analysis_type}) via EnhancedPMAnalysisRunner..." in caplog.text
    assert f"Analyse principale (type: '{analysis_type}') terminée avec succès via EnhancedPMAnalysisRunner." in caplog.text


@pytest.mark.asyncio
async def test_perform_text_analysis_no_llm_service(caplog):
    """Teste que la fonction échoue correctement si llm_service est manquant."""
    text_to_analyze = "Texte test."
    services_without_llm = {}

    # La fonction devrait retourner None et logger une erreur critique
    result = await perform_text_analysis(text_to_analyze, services_without_llm)
    
    assert result is None
    assert "Le service LLM n'est pas disponible dans les services fournis." in caplog.text


@pytest.mark.asyncio
@patch(ENHANCED_RUNNER_PATH)
async def test_perform_text_analysis_runner_fails(mock_enhanced_runner_class, mock_services, caplog):
    """Teste le cas où la méthode run_enhanced_analysis lève une exception."""
    text_to_analyze = "Texte qui cause une erreur."
    analysis_type = "error_case"
    expected_exception = ValueError("Erreur simulée dans run_enhanced_analysis")

    # Configurer le mock
    mock_runner_instance = mock_enhanced_runner_class.return_value
    mock_runner_instance.run_enhanced_analysis = AsyncMock(side_effect=expected_exception)

    with pytest.raises(ValueError) as excinfo:
        await perform_text_analysis(text_to_analyze, mock_services, analysis_type)

    assert excinfo.value == expected_exception
    mock_enhanced_runner_class.assert_called_once_with()
    mock_runner_instance.run_enhanced_analysis.assert_awaited_once_with(
        text_content=text_to_analyze,
        llm_service=mock_services["llm_service"]
    )
    assert f"Erreur lors de l'analyse du texte (type: {analysis_type}): {expected_exception}" in caplog.text