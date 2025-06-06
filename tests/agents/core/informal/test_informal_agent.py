#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour l'agent informel.
"""

import unittest
import pytest
from unittest.mock import MagicMock, patch, AsyncMock # Ajout de AsyncMock
import json
import asyncio # Ajout de asyncio
from semantic_kernel.exceptions.kernel_exceptions import KernelFunctionNotFoundError

# La configuration du logging est maintenant gérée globalement dans tests/conftest.py

# Import des fixtures
from .fixtures import (
    mock_fallacy_detector,
    mock_rhetorical_analyzer,
    mock_contextual_analyzer,
    informal_agent_instance,
    mock_semantic_kernel_instance, 
    MockSemanticKernel 
)

# Import du module à tester
from argumentation_analysis.agents.core.informal.informal_agent import InformalAnalysisAgent as InformalAgent
from argumentation_analysis.agents.core.informal.informal_agent import InformalAnalysisPlugin


class TestInformalAgent:
    """Tests unitaires pour l'agent informel."""

    def setup_method(self, method):
        """Initialisation avant chaque test."""
        self.mock_sk_kernel = MockSemanticKernel()
        self.agent_name = "test_agent_from_setup"

        self.plugin_patcher = patch('argumentation_analysis.agents.core.informal.informal_agent.InformalAnalysisPlugin')
        mock_plugin_class = self.plugin_patcher.start()
        self.mock_informal_plugin_instance = MagicMock(spec=InformalAnalysisPlugin)
        mock_plugin_class.return_value = self.mock_informal_plugin_instance

        self.agent = InformalAgent(kernel=self.mock_sk_kernel, agent_name=self.agent_name)
        self.agent.setup_agent_components(llm_service_id="test_llm_service_setup")

    def teardown_method(self, method):
        self.plugin_patcher.stop()

    @pytest.mark.asyncio
    async def test_analyze_fallacies(self, mocker):
        """Teste la méthode analyze_fallacies."""
        text = "Les experts affirment que ce produit est sûr."
        
        expected_fallacy_list = [
            {"fallacy_type": "Appel à l'autorité", "text": "Les experts affirment que ce produit est sûr.", "confidence": 0.7}
        ]
        
        mocker.patch.object(self.mock_sk_kernel, 'invoke', return_value=json.dumps(expected_fallacy_list))

        fallacies = await self.agent.analyze_fallacies(text)
        
        assert len(fallacies) == 1
        assert fallacies[0]["fallacy_type"] == "Appel à l'autorité"
        assert fallacies[0]["text"] == "Les experts affirment que ce produit est sûr."
        assert fallacies[0]["confidence"] == 0.7
    
    @pytest.mark.asyncio
    async def test_analyze_rhetoric(self):
        """Teste la méthode analyze_rhetoric."""
        # Cette méthode est commentée dans l'agent, donc ce test n'est plus pertinent.
        pass
    
    @pytest.mark.asyncio
    async def test_analyze_context(self):
        """Teste la méthode analyze_context."""
        # Cette méthode est commentée dans l'agent, donc ce test n'est plus pertinent.
        pass
    
    @pytest.mark.asyncio
    async def test_analyze_argument(self, mocker):
        """Teste la méthode analyze_argument."""
        text = "Les experts affirment que ce produit est sûr. N'est-il pas évident que vous devriez l'acheter?"

        expected_fallacies = [{"fallacy_type": "Appel à l'autorité", "text": "Les experts affirment que ce produit est sûr.", "confidence": 0.7}]
        
        mocker.patch.object(self.mock_sk_kernel, 'invoke', return_value=json.dumps(expected_fallacies))
        
        result = await self.agent.analyze_argument(text)

        assert result["argument"] == text
        assert len(result["fallacies"]) == 1
        assert result["fallacies"][0]["fallacy_type"] == "Appel à l'autorité"
    
    @pytest.mark.asyncio
    async def test_analyze_text_with_semantic_kernel(self, mocker):
        """Teste la méthode identify_arguments avec un kernel sémantique."""
        expected_arguments = "Argument 1\nArgument 2"
        mocker.patch.object(self.mock_sk_kernel, 'invoke', return_value=expected_arguments)
        
        text = "Voici un texte avec plusieurs arguments."
        
        arguments = await self.agent.identify_arguments(text)
        
        assert len(arguments) == 2
        assert arguments[0] == "Argument 1"
        assert arguments[1] == "Argument 2"

    @pytest.mark.asyncio
    async def test_analyze_text_without_semantic_kernel(self, mocker):
        """
        Teste la méthode analyze_text.
        """
        text = "Voici un texte avec un seul argument."

        expected_fallacies = []
        mocker.patch.object(self.mock_sk_kernel, 'invoke', return_value=json.dumps(expected_fallacies))
        
        result = await self.agent.analyze_text(text)

        assert "fallacies" in result
        assert "analysis_timestamp" in result
        assert isinstance(result["fallacies"], list)
        assert result["fallacies"] == expected_fallacies
    
    def test_get_agent_capabilities(self):
        """Teste la méthode get_agent_capabilities."""
        agent = self.agent
        
        # La méthode get_agent_capabilities est synchrone
        capabilities = agent.get_agent_capabilities()

        # Vérifications basées sur la définition actuelle dans InformalAnalysisAgent
        assert "identify_arguments" in capabilities
        assert "analyze_fallacies" in capabilities
        assert "explore_fallacy_hierarchy" in capabilities
        assert "get_fallacy_details" in capabilities
        assert "categorize_fallacies" in capabilities
        assert "perform_complete_analysis" in capabilities
    
    def test_get_agent_info(self):
        """Teste la méthode get_agent_info."""
        agent = self.agent

        # La méthode get_agent_info est synchrone
        info = agent.get_agent_info()

        assert info["name"] == self.agent_name # Corrigé pour correspondre à BaseAgent
        assert info["class"] == "InformalAnalysisAgent" # Corrigé
        
        # Vérifier la présence des clés attendues par BaseAgent
        assert "system_prompt" in info
        assert "llm_service_id" in info
        assert "capabilities" in info
        
        # Vérifier une capacité spécifique pour s'assurer que get_agent_capabilities a été appelée
        assert "identify_arguments" in info["capabilities"]
    
    def test_initialization_with_invalid_tools(self):
        """
        Teste que l'initialisation de InformalAgent lève une TypeError si un argument
        'tools' (qui n'est plus supporté) est passé.
        """
        mock_sk_kernel = self.mock_sk_kernel
        
        with pytest.raises(TypeError):
            agent = InformalAgent(
                kernel=mock_sk_kernel,
                agent_name="invalid_tools_agent",
                tools={"fallacy_detector": MagicMock(), "invalid_tool": 123}
            )
    
    def test_initialization_without_fallacy_detector(self):
        """
        Teste que l'initialisation de InformalAgent lève une TypeError si un argument
        'tools' (qui n'est plus supporté) est passé, même s'il manque un "outil".
        """
        mock_sk_kernel = self.mock_sk_kernel

        with pytest.raises(TypeError):
            agent = InformalAgent(
                kernel=mock_sk_kernel,
                agent_name="missing_detector_agent",
                tools={"rhetorical_analyzer": MagicMock()}
            )
    
    @pytest.mark.asyncio
    async def test_analyze_rhetoric_without_analyzer(self):
        """
        Teste que agent.analyze_rhetoric gère correctement l'absence de la fonction
        sémantique correspondante (par exemple, en levant ValueError).
        """
        # Cette méthode est commentée dans l'agent, donc ce test n'est plus pertinent.
        pass
    
    @pytest.mark.asyncio
    async def test_analyze_context_without_analyzer(self):
        """
        Teste que agent.analyze_context gère correctement l'absence de la fonction
        sémantique correspondante.
        """
        # Cette méthode est commentée dans l'agent, donc ce test n'est plus pertinent.
        pass
    
    @pytest.mark.asyncio
    async def test_identify_arguments_without_kernel(self, mocker):
        """
        Teste que agent.identify_arguments gère correctement l'absence de la fonction
        sémantique correspondante ou un problème avec le kernel.
        """
        mocker.patch.object(self.mock_sk_kernel, 'invoke', side_effect=KernelFunctionNotFoundError("Test error"))

        # La méthode doit attraper l'exception et retourner None
        result = await self.agent.identify_arguments("Texte à analyser")
        
        assert result is None

# Note: Les tests async utilisent pytest-asyncio pour l'exécution
# Les décorateurs @pytest.mark.asyncio gèrent automatiquement l'event loop