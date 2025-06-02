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


class TestInformalAgent(unittest.TestCase):
    """Tests unitaires pour l'agent informel."""

    def setUp(self):
        """Initialisation avant chaque test."""
        self.mock_sk_kernel = MockSemanticKernel()
        self.agent_name = "test_agent_from_setup"

        self.plugin_patcher = patch('argumentation_analysis.agents.core.informal.informal_agent.InformalAnalysisPlugin')
        mock_plugin_class = self.plugin_patcher.start()
        self.mock_informal_plugin_instance = MagicMock(spec=InformalAnalysisPlugin)
        mock_plugin_class.return_value = self.mock_informal_plugin_instance

        self.agent = InformalAgent(kernel=self.mock_sk_kernel, agent_name=self.agent_name)
        self.agent.setup_agent_components(llm_service_id="test_llm_service_setup")
        
        # Rendre les méthodes de l'agent mockables avec AsyncMock si elles sont async
        # Cela est crucial si les méthodes originales sont async
        self.agent.analyze_fallacies = AsyncMock(return_value=[])
        self.agent.analyze_rhetoric = AsyncMock(return_value={})
        self.agent.analyze_context = AsyncMock(return_value={})
        self.agent.analyze_argument = AsyncMock(return_value={})
        self.agent.identify_arguments = AsyncMock(return_value=[])
        self.agent.analyze_text = AsyncMock(return_value={"fallacies": [], "analysis_timestamp": "mock_time"})


    def tearDown(self):
        self.plugin_patcher.stop()

    async def test_analyze_fallacies(self):
        """Teste la méthode analyze_fallacies."""
        text = "Les experts affirment que ce produit est sûr."
        
        expected_fallacy_list = [
            {"fallacy_type": "Appel à l'autorité", "text": "Les experts affirment que ce produit est sûr.", "confidence": 0.7}
        ]
        
        self.agent.analyze_fallacies.return_value = expected_fallacy_list

        fallacies = await self.agent.analyze_fallacies(text)
        
        self.assertEqual(len(fallacies), 1)
        self.assertEqual(fallacies[0]["fallacy_type"], "Appel à l'autorité")
        self.assertEqual(fallacies[0]["text"], "Les experts affirment que ce produit est sûr.")
        self.assertEqual(fallacies[0]["confidence"], 0.7)
    
    async def test_analyze_rhetoric(self):
        """Teste la méthode analyze_rhetoric."""
        agent = self.agent # Utiliser self.agent directement
        text = "N'est-il pas évident que ce produit va changer votre vie?"

        expected_rhetoric_dict = {
            "tone": "persuasif",
            "style": "émotionnel",
            "techniques": ["appel à l'émotion", "question rhétorique"],
            "effectiveness": 0.8
        }
        
        agent.analyze_rhetoric.return_value = expected_rhetoric_dict
        
        rhetoric = await agent.analyze_rhetoric(text)

        self.assertEqual(rhetoric["tone"], "persuasif")
        self.assertEqual(rhetoric["style"], "émotionnel")
        self.assertEqual(rhetoric["techniques"], ["appel à l'émotion", "question rhétorique"])
        self.assertEqual(rhetoric["effectiveness"], 0.8)
    
    async def test_analyze_context(self):
        """Teste la méthode analyze_context."""
        agent = self.agent
        text = "Achetez notre produit maintenant et bénéficiez d'une réduction de 20%!"

        expected_context_dict = {
            "context_type": "commercial",
            "confidence": 0.9
        }
        
        agent.analyze_context.return_value = expected_context_dict
        
        context = await agent.analyze_context(text)
        
        self.assertEqual(context["context_type"], "commercial")
        self.assertEqual(context["confidence"], 0.9)
    
    async def test_analyze_argument(self):
        """Teste la méthode analyze_argument."""
        agent = self.agent
        text = "Les experts affirment que ce produit est sûr. N'est-il pas évident que vous devriez l'acheter?"

        expected_result_dict = {
            "argument": text,
            "fallacies": [{"fallacy_type": "Appel à l'autorité", "text": "Les experts affirment que ce produit est sûr.", "confidence": 0.7}],
            "rhetoric": {"tone": "persuasif", "style": "émotionnel", "techniques": ["question rhétorique"], "effectiveness": 0.8},
        }
        
        agent.analyze_argument.return_value = expected_result_dict
        
        result = await agent.analyze_argument(text)

        self.assertEqual(result["argument"], text)
        self.assertEqual(len(result["fallacies"]), 1)
        self.assertEqual(result["fallacies"][0]["fallacy_type"], "Appel à l'autorité")
        self.assertEqual(result["rhetoric"]["tone"], "persuasif")
    
    async def test_analyze_text_with_semantic_kernel(self):
        """Teste la méthode identify_arguments avec un kernel sémantique."""
        agent = self.agent
        kernel_to_use = self.mock_sk_kernel 

        # Mock direct de la méthode de l'agent qui utilise le kernel
        expected_arguments = ["Argument 1", "Argument 2"]
        agent.identify_arguments.return_value = expected_arguments
        
        text = "Voici un texte avec plusieurs arguments."
        
        arguments = await agent.identify_arguments(text)
        
        # Vérifier que la méthode mockée de l'agent a été appelée
        agent.identify_arguments.assert_called_once_with(text)
        
        self.assertEqual(len(arguments), 2)
        self.assertEqual(arguments[0], "Argument 1")
        self.assertEqual(arguments[1], "Argument 2")

    async def test_analyze_text_without_semantic_kernel(self):
        """
        Teste la méthode analyze_text.
        """
        agent = self.agent
        text = "Voici un texte avec un seul argument."

        expected_result = {
            "fallacies": [], 
            "analysis_timestamp": "mocked_time" 
        }
        
        agent.analyze_text.return_value = expected_result
        
        result = await agent.analyze_text(text)

        self.assertIn("fallacies", result)
        self.assertIn("analysis_timestamp", result)
        self.assertIsInstance(result["fallacies"], list)
        self.assertEqual(result["fallacies"], expected_result["fallacies"])
        
        agent.analyze_text.assert_called_once_with(text)
    
    def test_get_agent_capabilities(self):
        """Teste la méthode get_agent_capabilities."""
        agent = self.agent 
        
        # La méthode get_agent_capabilities est synchrone
        capabilities = agent.get_agent_capabilities()

        # Vérifications basées sur la définition actuelle dans InformalAnalysisAgent
        self.assertIn("identify_arguments", capabilities)
        self.assertIn("analyze_fallacies", capabilities)
        self.assertIn("explore_fallacy_hierarchy", capabilities)
        self.assertIn("get_fallacy_details", capabilities)
        self.assertIn("categorize_fallacies", capabilities)
        self.assertIn("perform_complete_analysis", capabilities)
    
    def test_get_agent_info(self):
        """Teste la méthode get_agent_info."""
        agent = self.agent 

        # La méthode get_agent_info est synchrone
        info = agent.get_agent_info()

        self.assertEqual(info["name"], self.agent_name) # Corrigé pour correspondre à BaseAgent
        self.assertEqual(info["class"], "InformalAnalysisAgent") # Corrigé
        
        # Vérifier la présence des clés attendues par BaseAgent
        self.assertIn("system_prompt", info) 
        self.assertIn("llm_service_id", info)
        self.assertIn("capabilities", info)
        
        # Vérifier une capacité spécifique pour s'assurer que get_agent_capabilities a été appelée
        self.assertIn("identify_arguments", info["capabilities"])
    
    def test_initialization_with_invalid_tools(self):
        """
        Teste que l'initialisation de InformalAgent lève une TypeError si un argument
        'tools' (qui n'est plus supporté) est passé.
        """
        mock_sk_kernel = self.mock_sk_kernel 
        
        with self.assertRaises(TypeError):
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

        with self.assertRaises(TypeError):
            agent = InformalAgent( 
                kernel=mock_sk_kernel,
                agent_name="missing_detector_agent",
                tools={"rhetorical_analyzer": MagicMock()} 
            )
    
    async def test_analyze_rhetoric_without_analyzer(self):
        """
        Teste que agent.analyze_rhetoric gère correctement l'absence de la fonction
        sémantique correspondante (par exemple, en levant ValueError).
        """
        agent = self.agent
        
        # Simuler l'échec de la fonction sémantique via le mock de la méthode de l'agent
        agent.analyze_rhetoric.side_effect = ValueError("Analyseur rhétorique non disponible ou erreur.")

        with self.assertRaises(ValueError) as context:
            await agent.analyze_rhetoric("Texte à analyser")
        self.assertIn("Analyseur rhétorique non disponible", str(context.exception))
    
    async def test_analyze_context_without_analyzer(self):
        """
        Teste que agent.analyze_context gère correctement l'absence de la fonction
        sémantique correspondante.
        """
        agent = self.agent
        
        agent.analyze_context.side_effect = ValueError("Analyseur contextuel non disponible ou erreur.")

        with self.assertRaises(ValueError) as context:
            await agent.analyze_context("Texte à analyser")
        self.assertIn("Analyseur contextuel non disponible", str(context.exception))
    
    async def test_identify_arguments_without_kernel(self):
        """
        Teste que agent.identify_arguments gère correctement l'absence de la fonction
        sémantique correspondante ou un problème avec le kernel.
        """
        agent = self.agent
        
        agent.identify_arguments.side_effect = ValueError("Identification des arguments non disponible ou erreur kernel.")

        with self.assertRaises(ValueError) as context:
            await agent.identify_arguments("Texte à analyser")
        self.assertIn("Identification des arguments non disponible", str(context.exception))

# Pour exécuter les tests async avec unittest, on peut utiliser asyncio.run
# ou un runner de test compatible async comme pytest-asyncio (déjà utilisé via pytest)

def async_test_runner(test_case_class, test_method_name):
    """Exécute un cas de test asynchrone."""
    test_instance = test_case_class(test_method_name)
    # unittest.TestCase.setUp et tearDown sont synchrones par défaut
    # Si elles deviennent async, il faudra les await ici.
    test_instance.setUp() 
    try:
        asyncio.run(getattr(test_instance, test_method_name)())
    finally:
        test_instance.tearDown()

# Exemple de comment exécuter un test spécifique si besoin (principalement pour débogage)
# if __name__ == "__main__":
#     # Créer une suite de tests pour les méthodes async
#     suite = unittest.TestSuite()
#     # Ajouter les tests async à la suite en les wrappant
#     async_tests = [
#         'test_analyze_fallacies',
#         'test_analyze_rhetoric',
#         'test_analyze_context',
#         'test_analyze_argument',
#         'test_analyze_text_with_semantic_kernel',
#         'test_analyze_text_without_semantic_kernel',
#         'test_analyze_rhetoric_without_analyzer',
#         'test_analyze_context_without_analyzer',
#         'test_identify_arguments_without_kernel'
#     ]
#     for test_name in async_tests:
#         # Créer une fonction wrapper pour chaque test async
#         def wrapper_factory(name):
#             def test_wrapper(self): # self est l'instance de TestCase
#                 asyncio.run(getattr(self, name)())
#             return test_wrapper
        
#         # Ajouter le test wrappé à la classe de test dynamiquement
#         # Cela n'est pas la manière standard, pytest gère cela mieux.
#         # setattr(TestInformalAgent, test_name + "_sync", wrapper_factory(test_name))
#         # suite.addTest(TestInformalAgent(test_name + "_sync"))

#     # Ajouter les tests synchrones
#     sync_tests = [
#         'test_get_agent_capabilities',
#         'test_get_agent_info',
#         'test_initialization_with_invalid_tools',
#         'test_initialization_without_fallacy_detector'
#     ]
#     for test_name in sync_tests:
#         suite.addTest(TestInformalAgent(test_name))
        
#     runner = unittest.TextTestRunner()
#     runner.run(suite)

#     # Alternative plus simple pour un seul test async:
#     # test_instance = TestInformalAgent("test_analyze_fallacies")
#     # test_instance.setUp()
#     # asyncio.run(test_instance.test_analyze_fallacies())
#     # test_instance.tearDown()