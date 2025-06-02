#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour le module text_analyzer.py.
"""

import pytest
import logging
from unittest.mock import patch, MagicMock, AsyncMock

# Cible pour le patching
RUN_ANALYSIS_CONVERSATION_PATH = "argumentation_analysis.analytics.text_analyzer.run_analysis_conversation"

# Importation de la fonction à tester après avoir défini le chemin de patch
from argumentation_analysis.analytics.text_analyzer import perform_text_analysis


@pytest.fixture
def mock_llm_service():
    """Fixture pour un service LLM mocké."""
    return MagicMock(name="MockLLMService")

@pytest.fixture
def sample_services(mock_llm_service):
    """Fixture pour un dictionnaire de services avec le LLM mocké."""
    return {"llm_service": mock_llm_service, "jvm_ready": True}

@pytest.mark.asyncio
async def test_perform_text_analysis_nominal_case(sample_services, mock_llm_service, caplog):
    """Teste le cas nominal de perform_text_analysis."""
    caplog.set_level(logging.INFO)
    text_to_analyze = "Ceci est un texte d'exemple pour l'analyse."
    analysis_type = "default_test"

    with patch(RUN_ANALYSIS_CONVERSATION_PATH, new_callable=AsyncMock) as mock_run_analysis:
        # `perform_text_analysis` retourne None en cas de succès (résultats journalisés)
        result = await perform_text_analysis(text_to_analyze, sample_services, analysis_type)
        
        mock_run_analysis.assert_awaited_once_with(
            texte_a_analyser=text_to_analyze,
            llm_service=mock_llm_service
        )
        assert result is None # Ou un indicateur de succès spécifique si la fonction évolue
        assert f"Initiating text analysis of type '{analysis_type}'" in caplog.text
        assert f"Lancement de l'analyse principale (type: {analysis_type}) via run_analysis_conversation..." in caplog.text
        assert f"Analyse principale (type: '{analysis_type}') terminée avec succès (via run_analysis_conversation)." in caplog.text

@pytest.mark.asyncio
async def test_perform_text_analysis_llm_service_missing(sample_services, caplog):
    """Teste le cas où le service LLM est manquant."""
    caplog.set_level(logging.CRITICAL)
    services_without_llm = {"jvm_ready": True} # Pas de llm_service
    text_to_analyze = "Texte test."

    with patch(RUN_ANALYSIS_CONVERSATION_PATH, new_callable=AsyncMock) as mock_run_analysis:
        result = await perform_text_analysis(text_to_analyze, services_without_llm, "test_no_llm")
        
        assert result is None # Indique un échec critique
        mock_run_analysis.assert_not_awaited() # Ne doit pas être appelé
        assert "Le service LLM n'est pas disponible" in caplog.text

@pytest.mark.asyncio
async def test_perform_text_analysis_run_analysis_raises_exception(sample_services, mock_llm_service, caplog):
    """Teste le cas où run_analysis_conversation lève une exception."""
    caplog.set_level(logging.ERROR)
    text_to_analyze = "Texte qui cause une erreur."
    analysis_type = "error_case"
    expected_exception = Exception("Erreur simulée dans run_analysis_conversation")

    with patch(RUN_ANALYSIS_CONVERSATION_PATH, new_callable=AsyncMock, side_effect=expected_exception) as mock_run_analysis:
        with pytest.raises(Exception) as excinfo:
            await perform_text_analysis(text_to_analyze, sample_services, analysis_type)
        
        assert excinfo.value == expected_exception # Vérifie que l'exception originale est propagée
        mock_run_analysis.assert_awaited_once_with(
            texte_a_analyser=text_to_analyze,
            llm_service=mock_llm_service
        )
        assert f"Erreur lors de l'analyse du texte (type: {analysis_type}): {expected_exception}" in caplog.text

@pytest.mark.asyncio
async def test_perform_text_analysis_run_analysis_raises_import_error(sample_services, mock_llm_service, caplog):
    """Teste le cas où run_analysis_conversation lève une ImportError."""
    caplog.set_level(logging.ERROR)
    text_to_analyze = "Texte pour test d'ImportError."
    analysis_type = "import_error_case"
    expected_exception = ImportError("Erreur d'import simulée")

    # Simuler que run_analysis_conversation lève une ImportError
    with patch(RUN_ANALYSIS_CONVERSATION_PATH, new_callable=AsyncMock, side_effect=expected_exception) as mock_run_analysis:
        with pytest.raises(ImportError) as excinfo:
            await perform_text_analysis(text_to_analyze, sample_services, analysis_type)
        
        assert excinfo.value == expected_exception
        mock_run_analysis.assert_awaited_once_with(
            texte_a_analyser=text_to_analyze,
            llm_service=mock_llm_service
        )
        assert f"Échec de l'importation ou de l'utilisation des composants d'analyse pour le type '{analysis_type}': {expected_exception}" in caplog.text


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