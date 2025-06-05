#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour la gestion des erreurs des agents informels.
"""

import unittest
import pytest 
from unittest.mock import MagicMock, patch, AsyncMock # Ajout de AsyncMock
import json 
import asyncio # Ajout de asyncio
from semantic_kernel.exceptions.kernel_exceptions import KernelFunctionNotFoundError

# La configuration du logging et les imports conditionnels de numpy/pandas
# sont maintenant gérés globalement dans tests/conftest.py

# Import des fixtures (certaines seront appelées dans setUp)
from .fixtures import (
    mock_fallacy_detector, 
    mock_rhetorical_analyzer, 
    mock_contextual_analyzer, 
    informal_agent_instance, 
    # sample_test_text, # Plus besoin d'importer la fixture directement
    MockSemanticKernel # Importer la classe MockSemanticKernel directement
)

# Import du module à tester
from argumentation_analysis.agents.core.informal.informal_agent import InformalAnalysisAgent as InformalAgent
from argumentation_analysis.agents.core.informal.informal_agent import InformalAnalysisPlugin

class TestInformalErrorHandling:
    """Tests unitaires pour la gestion des erreurs des agents informels."""

    def setup_method(self, method):
        """Initialisation avant chaque test."""
        self.mock_sk_kernel = MockSemanticKernel()
        self.agent_name = "test_error_handling_agent"

        self.plugin_patcher = patch('argumentation_analysis.agents.core.informal.informal_agent.InformalAnalysisPlugin')
        mock_plugin_class = self.plugin_patcher.start()
        self.mock_informal_plugin_instance = MagicMock(spec=InformalAnalysisPlugin)
        self.mock_informal_plugin_instance.semantic_AnalyzeFallacies = AsyncMock()
        self.mock_informal_plugin_instance.semantic_IdentifyArguments = AsyncMock()
        mock_plugin_class.return_value = self.mock_informal_plugin_instance
        
        self.agent = InformalAgent(kernel=self.mock_sk_kernel, agent_name=self.agent_name)
        self.sample_text = "Ceci est un texte d'exemple pour les tests."

    def teardown_method(self, method):
        self.plugin_patcher.stop()

    def _ensure_agent_setup(self):
        if not hasattr(self.agent, '_llm_service_id') or not self.agent._llm_service_id:
             self.agent.setup_agent_components(llm_service_id="test_llm_service_errors")

    @pytest.mark.asyncio
    async def test_handle_empty_text(self, mocker):
        """Teste la gestion d'un texte vide."""
        self._ensure_agent_setup()
        
        # On ne mock rien, on teste la logique interne de la vraie méthode
        result = await self.agent.analyze_text("")
        
        assert isinstance(result, dict)
        assert "error" in result
        assert result["error"] == "Le texte est vide"
        assert "fallacies" in result
        assert result["fallacies"] == []

        # Vérifier que analyze_fallacies n'est pas appelée
        mocked_analyze_fallacies = mocker.patch('argumentation_analysis.agents.core.informal.informal_agent.InformalAnalysisAgent.analyze_fallacies', new_callable=AsyncMock)
        await self.agent.analyze_text("")
        mocked_analyze_fallacies.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_none_text(self, mocker):
        """Teste la gestion d'un texte None."""
        self._ensure_agent_setup()

        result = await self.agent.analyze_text(None)
        
        assert isinstance(result, dict)
        assert "error" in result
        assert result["error"] == "Le texte est vide"
        assert "fallacies" in result
        assert result["fallacies"] == []

        mocked_analyze_fallacies = mocker.patch('argumentation_analysis.agents.core.informal.informal_agent.InformalAnalysisAgent.analyze_fallacies', new_callable=AsyncMock)
        await self.agent.analyze_text(None)
        mocked_analyze_fallacies.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_handle_fallacy_detector_exception(self, mocker):
        """Teste la gestion d'une exception du détecteur de sophismes (fonction SK)."""
        self._ensure_agent_setup()
        text_to_analyze = self.sample_text
        
        # La méthode analyze_text appelle analyze_fallacies.
        # Nous mockons analyze_fallacies pour qu'elle lève une exception.
        mocker.patch('argumentation_analysis.agents.core.informal.informal_agent.InformalAnalysisAgent.analyze_fallacies', side_effect=Exception("Erreur SK du détecteur de sophismes"))
        
        result = await self.agent.analyze_text(text_to_analyze)
        
        assert isinstance(result, dict)
        assert "error" in result
        assert "Erreur lors de l'analyse" in result["error"]
        assert "Erreur SK du détecteur de sophismes" in result["error"]
        assert "fallacies" in result
        assert result["fallacies"] == []

    def test_handle_missing_required_tool(self, mocker):
        """
        Teste la gestion d'un "outil" requis manquant (fonction sémantique essentielle).
        """
        agent_no_setup = InformalAgent(kernel=self.mock_sk_kernel, agent_name="test_missing_func")
        
        # Mocker kernel.add_function pour qu'il lève une exception si une fonction clé est manquante.
        def mock_add_function_side_effect(*args, **kwargs):
            if kwargs.get('function_name') == "semantic_AnalyzeFallacies":
                raise ValueError(f"Fonction sémantique essentielle '{kwargs.get('function_name')}' manquante.")
            return MagicMock()

        mocker.patch.object(self.mock_sk_kernel, 'add_function', side_effect=mock_add_function_side_effect)

        with pytest.raises(ValueError, match="Fonction sémantique essentielle 'semantic_AnalyzeFallacies' manquante"):
            agent_no_setup.setup_agent_components(llm_service_id="test_llm")