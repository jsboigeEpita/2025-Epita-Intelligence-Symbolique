# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour le module text_analyzer.py.
"""

import pytest
import logging
from unittest.mock import MagicMock, patch, AsyncMock


# Cible pour le patching
# Le patch cible la fonction là où elle est définie, car elle est importée localement dans la fonction testée.
# Cibles pour le patching
APP_SETTINGS_PATH = "argumentation_analysis.analytics.text_analyzer.AppSettings"
ANALYSIS_RUNNER_PATH = "argumentation_analysis.analytics.text_analyzer.AnalysisRunner"

# Importation de la fonction à tester
from argumentation_analysis.analytics.text_analyzer import perform_text_analysis

@pytest.mark.asyncio
@patch(ANALYSIS_RUNNER_PATH)
@patch(APP_SETTINGS_PATH)
async def test_perform_text_analysis_nominal_case(mock_app_settings_class, mock_analysis_runner_class, caplog):
    """Teste le cas nominal de perform_text_analysis."""
    text_to_analyze = "Ceci est un texte d'exemple pour l'analyse."
    analysis_type = "default_test"
    expected_result = "Résultat de l'analyse"

    # Configurer les mocks
    mock_settings_instance = mock_app_settings_class.return_value
    mock_runner_instance = mock_analysis_runner_class.return_value
    mock_runner_instance.run_analysis = AsyncMock(return_value=expected_result)

    result = await perform_text_analysis(text_to_analyze, analysis_type)

    # Assertions
    mock_app_settings_class.assert_called_once()
    mock_analysis_runner_class.assert_called_once_with(mock_settings_instance)
    mock_runner_instance.run_analysis.assert_awaited_once_with(input_text=text_to_analyze)
    assert result == expected_result
    assert f"Initiating text analysis of type '{analysis_type}'" in caplog.text
    assert "Lancement de l'analyse principale (type: default_test) via AnalysisRunner..." in caplog.text
    assert "Analyse principale (type: 'default_test') terminée avec succès." in caplog.text

@pytest.mark.asyncio
@patch(APP_SETTINGS_PATH)
async def test_perform_text_analysis_settings_fail(mock_app_settings_class, caplog):
    """Teste le cas où l'initialisation de AppSettings échoue."""
    text_to_analyze = "Texte test."
    expected_exception = FileNotFoundError("Fichier de config manquant")
    mock_app_settings_class.side_effect = expected_exception

    with pytest.raises(FileNotFoundError) as excinfo:
        await perform_text_analysis(text_to_analyze)
    
    assert excinfo.value == expected_exception
    assert "Erreur de configuration critique" in caplog.text

@pytest.mark.asyncio
@patch(ANALYSIS_RUNNER_PATH)
@patch(APP_SETTINGS_PATH)
async def test_perform_text_analysis_runner_fails(mock_app_settings_class, mock_analysis_runner_class, caplog):
    """Teste le cas où la méthode run_analysis de AnalysisRunner lève une exception."""
    text_to_analyze = "Texte qui cause une erreur."
    analysis_type = "error_case"
    expected_exception = Exception("Erreur simulée dans run_analysis")

    # Configurer les mocks
    mock_settings_instance = mock_app_settings_class.return_value
    mock_runner_instance = mock_analysis_runner_class.return_value
    mock_runner_instance.run_analysis = AsyncMock(side_effect=expected_exception)

    with pytest.raises(Exception) as excinfo:
        await perform_text_analysis(text_to_analyze, analysis_type)

    assert excinfo.value == expected_exception
    mock_analysis_runner_class.assert_called_once_with(mock_settings_instance)
    mock_runner_instance.run_analysis.assert_awaited_once_with(input_text=text_to_analyze)
    assert f"Erreur lors de l'analyse du texte (type: {analysis_type}): {expected_exception}" in caplog.text


# Test pour vérifier le comportement si l'import initial de run_analysis_conversation échoue
# Ce test est plus complexe car il nécessite de manipuler sys.modules ou de restructurer
# l'import dans text_analyzer.py pour le rendre plus facilement testable dans ce scénario.
# Pour l'instant, on se concentre sur le mock de la fonction une fois importée.

# Exemple de test si l'import initial échoue (nécessiterait des ajustements dans le module testé ou un setup de test plus avancé)
# @pytest.mark.asyncio
# async def test_perform_text_analysis_initial_import_fails(sample_services, caplog):
#     """
#     Teste le comportement si l'import initial de run_analysis_conversation échoue.
#     NOTE: Ce test est conceptuel et peut nécessiter des ajustements.
#     """
#     caplog.set_level(logging.ERROR)
#     text_to_analyze = "Texte test."
# 
#     # Simuler l'échec de l'import au niveau du module text_analyzer
#     # Ceci est difficile à faire proprement sans modifier le module ou utiliser des techniques avancées de patching
#     with patch("sys.modules", {**sys.modules}) as mock_modules: # Copie pour éviter de modifier globalement
#         # Supprimer le module pour forcer un échec d'import, ou le remplacer par un mock qui lève ImportError
#         # Cela dépend de comment l'import est géré dans text_analyzer.py
#         if "argumentation_analysis.orchestration.analysis_runner" in mock_modules:
#             del mock_modules["argumentation_analysis.orchestration.analysis_runner"]
#         
#         # Alternative: Patcher la fonction placeholder qui est définie si l'import échoue
#         # Ceci suppose que la fonction placeholder est accessible pour le patch.
#         # Le chemin exact dépendra de la structure après l'échec de l'import.
#         # Exemple: with patch("argumentation_analysis.analytics.text_analyzer.run_analysis_conversation_placeholder", side_effect=ImportError("Simulated initial import error"))
# 
#         # Pour ce test, nous allons supposer que l'ImportError est levée par la fonction placeholder
#         # si elle est appelée.
#         # Il faudrait que la fonction perform_text_analysis tente d'appeler la version "cassée".
# 
#         # Ce test est plus pour illustrer la complexité.
#         # La gestion d'erreur actuelle dans text_analyzer.py (try-except autour de l'import)
#         # rend ce scénario spécifique (échec de l'import initial intercepté par perform_text_analysis)
#         # moins direct à tester sans modifier le code source pour le rendre plus testable.
# 
#         # Si l'import échoue au chargement du module text_analyzer, perform_text_analysis
#         # pourrait ne même pas être définissable ou utilisable.
#         # Si la fonction placeholder est appelée, elle lèvera ImportError.
# 
#         # Pour l'instant, on se concentre sur les cas où perform_text_analysis est appelée
#         # et la dépendance run_analysis_conversation est mockée.
#         pass # Ce test est laissé en commentaire car il est complexe à mettre en œuvre proprement.