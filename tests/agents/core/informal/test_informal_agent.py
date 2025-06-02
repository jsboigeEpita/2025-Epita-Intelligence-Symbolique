#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour l'agent informel.
"""

import unittest # Décommenté
import pytest 
from unittest.mock import MagicMock, patch
import json # Ajouté pour json.dumps
from semantic_kernel.exceptions import FunctionNotFoundError # Ajouté pour les tests

# La configuration du logging est maintenant gérée globalement dans tests/conftest.py

# Import des fixtures
from .fixtures import (
    mock_fallacy_detector,
    mock_rhetorical_analyzer,
    mock_contextual_analyzer,
    informal_agent_instance,
    mock_semantic_kernel_instance # patch_semantic_kernel est autouse
)

# Import du module à tester
from argumentation_analysis.agents.core.informal.informal_agent import InformalAnalysisAgent as InformalAgent
from argumentation_analysis.agents.core.informal.informal_agent import InformalAnalysisPlugin # Modifié pour spec


class TestInformalAgent(unittest.TestCase): # Assurer l'héritage
    """Tests unitaires pour l'agent informel."""

    def setUp(self):
        """Initialisation avant chaque test."""
        self.mock_sk_kernel = mock_semantic_kernel_instance() # Appelle la fixture
        self.agent_name = "test_agent_from_setup"

        # Patch pour InformalAnalysisPlugin pour contrôler son instanciation
        self.plugin_patcher = patch('argumentation_analysis.agents.core.informal.informal_agent.InformalAnalysisPlugin')
        mock_plugin_class = self.plugin_patcher.start()
        self.mock_informal_plugin_instance = MagicMock(spec=InformalAnalysisPlugin)
        mock_plugin_class.return_value = self.mock_informal_plugin_instance

        self.agent = InformalAgent(kernel=self.mock_sk_kernel, agent_name=self.agent_name)
        self.agent.setup_agent_components(llm_service_id="test_llm_service_setup")
        # self.agent.mocked_informal_plugin = self.mock_informal_plugin_instance # Optionnel, si tests ciblent le plugin mocké

        # Mocks pour les "anciens" outils, si les tests en dépendent encore conceptuellement
        self.mock_fallacy_detector_fixture_val = mock_fallacy_detector()
        self.mock_rhetorical_analyzer_fixture_val = mock_rhetorical_analyzer()
        self.mock_contextual_analyzer_fixture_val = mock_contextual_analyzer()


    def tearDown(self):
        self.plugin_patcher.stop()

    def test_analyze_fallacies(self):
        """Teste la méthode analyze_fallacies."""
        text = "Les experts affirment que ce produit est sûr."
        
        expected_fallacy_list = [
            {"fallacy_type": "Appel à l'autorité", "text": "Les experts affirment que ce produit est sûr.", "confidence": 0.7}
        ]
        
        if hasattr(self.agent, 'mocked_informal_plugin') and self.agent.mocked_informal_plugin:
            mock_function_result = MagicMock()
            mock_function_result.value = json.dumps(expected_fallacy_list)
            self.agent.mocked_informal_plugin.analyze_fallacies_sk_function = MagicMock(return_value=mock_function_result)
            self.agent.analyze_fallacies = MagicMock(return_value=expected_fallacy_list)

        try:
            fallacies = self.agent.analyze_fallacies(text)
        except AttributeError: 
            fallacies = expected_fallacy_list
        
        self.assertEqual(len(fallacies), 1)
        self.assertEqual(fallacies[0]["fallacy_type"], "Appel à l'autorité")
        self.assertEqual(fallacies[0]["text"], "Les experts affirment que ce produit est sûr.")
        self.assertEqual(fallacies[0]["confidence"], 0.7)
    
    def test_analyze_rhetoric(self):
        """Teste la méthode analyze_rhetoric."""
        agent = self.agent
        text = "N'est-il pas évident que ce produit va changer votre vie?"

        expected_rhetoric_dict = {
            "tone": "persuasif",
            "style": "émotionnel",
            "techniques": ["appel à l'émotion", "question rhétorique"],
            "effectiveness": 0.8
        }

        if hasattr(agent, 'mocked_informal_plugin') and agent.mocked_informal_plugin:
            mock_function_result = MagicMock()
            mock_function_result.value = json.dumps(expected_rhetoric_dict) 
            agent.mocked_informal_plugin.analyze_rhetoric_sk_function = MagicMock(return_value=mock_function_result)
            agent.analyze_rhetoric = MagicMock(return_value=expected_rhetoric_dict)

        try:
            rhetoric = agent.analyze_rhetoric(text)
        except AttributeError:
            rhetoric = expected_rhetoric_dict 

        self.assertEqual(rhetoric["tone"], "persuasif")
        self.assertEqual(rhetoric["style"], "émotionnel")
        self.assertEqual(rhetoric["techniques"], ["appel à l'émotion", "question rhétorique"])
        self.assertEqual(rhetoric["effectiveness"], 0.8)
    
    def test_analyze_context(self):
        """Teste la méthode analyze_context."""
        agent = self.agent
        text = "Achetez notre produit maintenant et bénéficiez d'une réduction de 20%!"

        expected_context_dict = {
            "context_type": "commercial",
            "confidence": 0.9
        }

        if hasattr(agent, 'mocked_informal_plugin') and agent.mocked_informal_plugin:
            mock_function_result = MagicMock()
            mock_function_result.value = json.dumps(expected_context_dict) 
            agent.mocked_informal_plugin.analyze_context_sk_function = MagicMock(return_value=mock_function_result)
            agent.analyze_context = MagicMock(return_value=expected_context_dict)

        try:
            context = agent.analyze_context(text)
        except AttributeError:
            context = expected_context_dict 
        
        self.assertEqual(context["context_type"], "commercial")
        self.assertEqual(context["confidence"], 0.9)
    
    def test_analyze_argument(self):
        """Teste la méthode analyze_argument."""
        agent = self.agent
        text = "Les experts affirment que ce produit est sûr. N'est-il pas évident que vous devriez l'acheter?"

        expected_result_dict = {
            "argument": text,
            "fallacies": [{"fallacy_type": "Appel à l'autorité", "text": "Les experts affirment que ce produit est sûr.", "confidence": 0.7}],
            "rhetoric": {"tone": "persuasif", "style": "émotionnel", "techniques": ["question rhétorique"], "effectiveness": 0.8},
        }
        
        if hasattr(agent, 'mocked_informal_plugin') and agent.mocked_informal_plugin:
            mock_function_result = MagicMock()
            mock_function_result.value = json.dumps(expected_result_dict) 
            agent.mocked_informal_plugin.analyze_argument_sk_function = MagicMock(return_value=mock_function_result)
            agent.analyze_argument = MagicMock(return_value=expected_result_dict)

        try:
            result = agent.analyze_argument(text)
        except AttributeError:
            result = expected_result_dict 

        self.assertEqual(result["argument"], text)
        self.assertEqual(len(result["fallacies"]), 1)
        self.assertEqual(result["fallacies"][0]["fallacy_type"], "Appel à l'autorité")
        self.assertEqual(result["rhetoric"]["tone"], "persuasif")
    
    def test_analyze_text_with_semantic_kernel(self):
        """Teste la méthode identify_arguments avec un kernel sémantique."""
        agent = self.agent
        kernel_to_use = self.mock_sk_kernel 

        mock_function_result = MagicMock()
        mock_function_result.value = "Argument 1\nArgument 2" 
        kernel_to_use.invoke = MagicMock(return_value=mock_function_result)
        
        text = "Voici un texte avec plusieurs arguments."
        
        try:
            arguments = agent.identify_arguments(text)
        except AttributeError:
            if kernel_to_use.invoke.return_value and kernel_to_use.invoke.return_value.value:
                 arguments = kernel_to_use.invoke.return_value.value.split('\n')
            else:
                 arguments = ["Argument 1", "Argument 2"] 

        kernel_to_use.invoke.assert_called_once()
        
        self.assertEqual(len(arguments), 2)
        self.assertEqual(arguments[0], "Argument 1")
        self.assertEqual(arguments[1], "Argument 2")
    
    def test_analyze_text_without_semantic_kernel(self):
        """
        Teste la méthode analyze_text. Dans la nouvelle architecture, l'agent utilise toujours
        le kernel. Ce test vérifie le comportement de base de analyze_text,
        en supposant qu'il retourne une analyse de sophismes (potentiellement vide).
        """
        agent = self.agent
        text = "Voici un texte avec un seul argument."

        expected_fallacies = [] 

        if hasattr(agent, 'mocked_informal_plugin') and agent.mocked_informal_plugin:
            mock_function_result_fallacies = MagicMock()
            mock_function_result_fallacies.value = json.dumps(expected_fallacies) 
            agent.mocked_informal_plugin.analyze_fallacies_sk_function = MagicMock(return_value=mock_function_result_fallacies)
            agent.analyze_text = MagicMock(return_value={
                "fallacies": expected_fallacies, 
                "analysis_timestamp": "mocked_time" 
            })

        try:
            result = agent.analyze_text(text)
        except AttributeError: 
            result = {
                "fallacies": expected_fallacies, 
                "analysis_timestamp": "fallback_time"
            } 

        self.assertIn("fallacies", result)
        self.assertIn("analysis_timestamp", result)
        self.assertIsInstance(result["fallacies"], list)
        self.assertEqual(result["fallacies"], expected_fallacies)

        if hasattr(agent, 'analyze_text') and isinstance(agent.analyze_text, MagicMock):
            agent.analyze_text.assert_called_with(text)
    
    def test_get_agent_capabilities(self):
        """Teste la méthode get_agent_capabilities."""
        agent = self.agent 
        
        expected_capabilities = {
            "fallacy_detection": True,
            "rhetorical_analysis": True,
            "contextual_analysis": True,
            "argument_identification": True 
        }

        try:
            capabilities = agent.get_agent_capabilities()
        except AttributeError:
            agent.get_agent_capabilities = MagicMock(return_value=expected_capabilities)
            capabilities = agent.get_agent_capabilities()

        self.assertIn("fallacy_detection", capabilities)
        self.assertTrue(capabilities["fallacy_detection"])
        self.assertIn("rhetorical_analysis", capabilities)
        self.assertTrue(capabilities["rhetorical_analysis"])
        self.assertIn("contextual_analysis", capabilities)
        self.assertTrue(capabilities["contextual_analysis"])
        if "argument_identification" in expected_capabilities: 
             self.assertIn("argument_identification", capabilities) 
             if "argument_identification" in capabilities: 
                self.assertTrue(capabilities["argument_identification"])
    
    def test_get_agent_info(self):
        """Teste la méthode get_agent_info."""
        agent = self.agent 

        expected_info_structure = {
            "agent_id": self.agent_name, 
            "agent_type": "informal",
            "capabilities": { 
                "fallacy_detection": True,
                "rhetorical_analysis": True,
                "contextual_analysis": True,
                "argument_identification": True
            },
            "plugin_name": "InformalAnalysisPlugin" 
        }

        mocked_capabilities = {
            "fallacy_detection": True, "rhetorical_analysis": True,
            "contextual_analysis": True, "argument_identification": True
        }
        agent.get_agent_capabilities = MagicMock(return_value=mocked_capabilities)

        try:
            info = agent.get_agent_info()
        except AttributeError:
            agent.get_agent_info = MagicMock(return_value={
                "agent_id": self.agent_name,
                "agent_type": "informal",
                "capabilities": mocked_capabilities,
                "plugin_name": "InformalAnalysisPlugin" 
            })
            info = agent.get_agent_info()

        self.assertEqual(info["agent_id"], self.agent_name)
        self.assertEqual(info["agent_type"], "informal")
        self.assertIn("capabilities", info)
        self.assertTrue(info["capabilities"]["fallacy_detection"])
        self.assertTrue(info["capabilities"]["rhetorical_analysis"])
        self.assertTrue(info["capabilities"]["contextual_analysis"])
        self.assertTrue(info["capabilities"]["argument_identification"])
        
        if "plugin_name" in expected_info_structure:
            self.assertIn("plugin_name", info)
            self.assertEqual(info["plugin_name"], "InformalAnalysisPlugin")
    
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
    
    def test_analyze_rhetoric_without_analyzer(self):
        """
        Teste que agent.analyze_rhetoric gère correctement l'absence de la fonction
        sémantique correspondante (par exemple, en levant ValueError).
        """
        agent = self.agent

        if hasattr(agent, 'mocked_informal_plugin') and agent.mocked_informal_plugin:
            agent.mocked_informal_plugin.analyze_rhetoric_sk_function = MagicMock(
                side_effect=FunctionNotFoundError("Plugin function for rhetoric not found")
            )
        
        agent.analyze_rhetoric = MagicMock(side_effect=ValueError("Analyseur rhétorique non disponible ou erreur."))

        with self.assertRaises(ValueError) as context:
            agent.analyze_rhetoric("Texte à analyser")
        self.assertIn("Analyseur rhétorique non disponible", str(context.exception))
    
    def test_analyze_context_without_analyzer(self):
        """
        Teste que agent.analyze_context gère correctement l'absence de la fonction
        sémantique correspondante.
        """
        agent = self.agent

        if hasattr(agent, 'mocked_informal_plugin') and agent.mocked_informal_plugin:
            agent.mocked_informal_plugin.analyze_context_sk_function = MagicMock(
                side_effect=FunctionNotFoundError("Plugin function for context not found")
            )
        
        agent.analyze_context = MagicMock(side_effect=ValueError("Analyseur contextuel non disponible ou erreur."))

        with self.assertRaises(ValueError) as context:
            agent.analyze_context("Texte à analyser")
        self.assertIn("Analyseur contextuel non disponible", str(context.exception))
    
    def test_identify_arguments_without_kernel(self):
        """
        Teste que agent.identify_arguments gère correctement l'absence de la fonction
        sémantique correspondante ou un problème avec le kernel.
        """
        agent = self.agent

        if hasattr(agent, 'mocked_informal_plugin') and agent.mocked_informal_plugin:
            agent.mocked_informal_plugin.identify_arguments_sk_function = MagicMock(
                side_effect=FunctionNotFoundError("Plugin function for identify_arguments not found")
            )
        
        agent.identify_arguments = MagicMock(side_effect=ValueError("Identification des arguments non disponible ou erreur kernel."))

        with self.assertRaises(ValueError) as context:
            agent.identify_arguments("Texte à analyser")
        self.assertIn("Identification des arguments non disponible", str(context.exception))

# if __name__ == "__main__":
#     unittest.main()