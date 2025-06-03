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

class TestInformalErrorHandling(unittest.TestCase):
    """Tests unitaires pour la gestion des erreurs des agents informels."""

    def setUp(self):
        """Initialisation avant chaque test."""
        self.mock_sk_kernel = MockSemanticKernel() 
        self.agent_name = "test_error_handling_agent"

        self.plugin_patcher = patch('argumentation_analysis.agents.core.informal.informal_agent.InformalAnalysisPlugin')
        mock_plugin_class = self.plugin_patcher.start()
        self.mock_informal_plugin_instance = MagicMock(spec=InformalAnalysisPlugin)
        # Configurer les fonctions sémantiques mockées sur l'instance du plugin mocké comme AsyncMock
        self.mock_informal_plugin_instance.semantic_AnalyzeFallacies = AsyncMock()
        self.mock_informal_plugin_instance.semantic_IdentifyArguments = AsyncMock()
        # ... autres fonctions sémantiques si nécessaire pour d'autres tests

        mock_plugin_class.return_value = self.mock_informal_plugin_instance
        
        self.agent = InformalAgent(kernel=self.mock_sk_kernel, agent_name=self.agent_name)
        # setup_agent_components est appelé dans _ensure_agent_setup si besoin.
        
        # Mocker la méthode analyze_text de l'agent avec AsyncMock pour les tests qui en dépendent
        self.agent.analyze_text = AsyncMock(return_value={
            "fallacies": [], "analysis_timestamp": "mock_time", "error": "Default mock error"
        })
        # La méthode analyze_fallacies est aussi async et est appelée par analyze_text
        self.agent.analyze_fallacies = AsyncMock(return_value=[])


        self.sample_text = "Ceci est un texte d'exemple pour les tests." # Valeur directe

    def tearDown(self):
        self.plugin_patcher.stop()

    def _ensure_agent_setup(self):
        if not hasattr(self.agent, '_llm_service_id') or not self.agent._llm_service_id:
             self.agent.setup_agent_components(llm_service_id="test_llm_service_errors")


    async def test_handle_empty_text(self):
        """Teste la gestion d'un texte vide."""
        self._ensure_agent_setup()
        agent = self.agent
        
        # Restaurer la vraie méthode analyze_text pour ce test spécifique
        original_analyze_text = agent.analyze_text 
        agent.analyze_text = InformalAgent.analyze_text.__get__(agent, InformalAgent) # Lier la méthode à l'instance

        result = await agent.analyze_text("") # Appel await
        
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Le texte est vide")
        self.assertIn("fallacies", result) 
        self.assertEqual(result["fallacies"], [])
        
        # Si analyze_fallacies est appelée par analyze_text, elle ne devrait pas l'être pour un texte vide.
        # On mock analyze_fallacies pour vérifier ses appels.
        agent.analyze_fallacies = AsyncMock(return_value=[]) # S'assurer qu'elle est mockée pour ce test
        await agent.analyze_text("") # Appel à nouveau pour vérifier l'appel à analyze_fallacies
        agent.analyze_fallacies.assert_not_called()

        agent.analyze_text = original_analyze_text # Restaurer le mock


    async def test_handle_none_text(self):
        """Teste la gestion d'un texte None."""
        self._ensure_agent_setup()
        agent = self.agent
        original_analyze_text = agent.analyze_text
        agent.analyze_text = InformalAnalysisAgent.analyze_text.__get__(agent, InformalAgent)

        result = await agent.analyze_text(None) # Appel await
        
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Le texte est vide")
        self.assertIn("fallacies", result)
        self.assertEqual(result["fallacies"], [])

        agent.analyze_fallacies = AsyncMock(return_value=[]) 
        await agent.analyze_text(None)
        agent.analyze_fallacies.assert_not_called()
        
        agent.analyze_text = original_analyze_text
    
    async def test_handle_fallacy_detector_exception(self):
        """Teste la gestion d'une exception du détecteur de sophismes (fonction SK)."""
        self._ensure_agent_setup()
        agent = self.agent
        text_to_analyze = self.sample_text
        
        original_analyze_text = agent.analyze_text
        agent.analyze_text = InformalAnalysisAgent.analyze_text.__get__(agent, InformalAgent)
        
        # La méthode analyze_text appelle analyze_fallacies.
        # Nous mockons analyze_fallacies pour qu'elle lève une exception.
        agent.analyze_fallacies = AsyncMock(side_effect=Exception("Erreur SK du détecteur de sophismes"))
        
        result = await agent.analyze_text(text_to_analyze) # Appel await
        
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        # Le message d'erreur exact est défini dans la méthode analyze_text de l'agent
        self.assertTrue("Erreur lors de l'analyse" in result["error"] or "Erreur lors de l'analyse du texte" in result["error"])
        self.assertTrue("Erreur SK du détecteur de sophismes" in result["error"])
        self.assertIn("fallacies", result)
        self.assertEqual(result["fallacies"], [])

        agent.analyze_text = original_analyze_text # Restaurer

    def test_handle_missing_required_tool(self):
        """
        Teste la gestion d'un "outil" requis manquant (fonction sémantique essentielle).
        """
        # Ne pas appeler _ensure_agent_setup ici car on teste l'échec de setup
        agent_no_setup = InformalAgent(kernel=self.mock_sk_kernel, agent_name="test_missing_func")
        
        # Mocker kernel.add_function pour qu'il lève une exception si une fonction clé est manquante.
        # La méthode setup_agent_components de InformalAnalysisAgent appelle kernel.add_function.
        original_add_function = self.mock_sk_kernel.add_function
        
        def mock_add_function_side_effect(*args, **kwargs):
            # Le nom de la fonction est dans kwargs['function_name']
            if kwargs.get('function_name') == "semantic_AnalyzeFallacies": 
                raise ValueError(f"Fonction sémantique essentielle '{kwargs.get('function_name')}' manquante.")
            return MagicMock() 

        self.mock_sk_kernel.add_function = MagicMock(side_effect=mock_add_function_side_effect)

        with self.assertRaises(ValueError) as context:
            agent_no_setup.setup_agent_components(llm_service_id="test_llm")
        
        self.assertIn("Fonction sémantique essentielle 'semantic_AnalyzeFallacies' manquante", str(context.exception))
        
        self.mock_sk_kernel.add_function = original_add_function # Restaurer