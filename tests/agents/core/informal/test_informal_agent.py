#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour l'agent informel.
"""

import unittest
from unittest.mock import MagicMock, patch
# import json # Semble inutilisé

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
from argumentation_analysis.agents.core.informal.informal_agent import InformalAgent
from argumentation_analysis.agents.core.informal.informal_definitions import InformalAnalysisPlugin # Gardé pour spec


class TestInformalAgent(unittest.TestCase):
    """Tests unitaires pour l'agent informel."""
    
    # setUp n'est plus nécessaire si les tests utilisent directement les fixtures

    def test_analyze_fallacies(self, informal_agent_instance, mock_fallacy_detector):
        """Teste la méthode analyze_fallacies."""
        agent = informal_agent_instance
        text = "Les experts affirment que ce produit est sûr."
        fallacies = agent.analyze_fallacies(text)
        
        mock_fallacy_detector.detect.assert_called_once_with(text)
        
        self.assertEqual(len(fallacies), 1)
        self.assertEqual(fallacies[0]["fallacy_type"], "Appel à l'autorité")
        self.assertEqual(fallacies[0]["text"], "Les experts affirment que ce produit est sûr.")
        self.assertEqual(fallacies[0]["confidence"], 0.7)
    
    def test_analyze_rhetoric(self, informal_agent_instance, mock_rhetorical_analyzer):
        """Teste la méthode analyze_rhetoric."""
        agent = informal_agent_instance
        text = "N'est-il pas évident que ce produit va changer votre vie?"
        rhetoric = agent.analyze_rhetoric(text)
        
        mock_rhetorical_analyzer.analyze.assert_called_once_with(text)
        
        self.assertEqual(rhetoric["tone"], "persuasif")
        self.assertEqual(rhetoric["style"], "émotionnel")
        self.assertEqual(rhetoric["techniques"], ["appel à l'émotion", "question rhétorique"])
        self.assertEqual(rhetoric["effectiveness"], 0.8)
    
    def test_analyze_context(self, informal_agent_instance, mock_contextual_analyzer):
        """Teste la méthode analyze_context."""
        agent = informal_agent_instance
        text = "Achetez notre produit maintenant et bénéficiez d'une réduction de 20%!"
        context = agent.analyze_context(text)
        
        mock_contextual_analyzer.analyze_context.assert_called_once_with(text)
        
        self.assertEqual(context["context_type"], "commercial")
        self.assertEqual(context["confidence"], 0.9)
    
    def test_analyze_argument(self, informal_agent_instance, mock_fallacy_detector, mock_rhetorical_analyzer):
        """Teste la méthode analyze_argument."""
        agent = informal_agent_instance
        text = "Les experts affirment que ce produit est sûr. N'est-il pas évident que vous devriez l'acheter?"
        result = agent.analyze_argument(text)
        
        mock_fallacy_detector.detect.assert_called_once_with(text)
        mock_rhetorical_analyzer.analyze.assert_called_once_with(text)
        
        self.assertEqual(result["argument"], text)
        self.assertEqual(len(result["fallacies"]), 1)
        self.assertEqual(result["fallacies"][0]["fallacy_type"], "Appel à l'autorité")
        self.assertEqual(result["rhetoric"]["tone"], "persuasif")
    
    def test_analyze_text_with_semantic_kernel(self, mock_semantic_kernel_instance, mock_fallacy_detector):
        """Teste la méthode analyze_text avec un kernel sémantique."""
        kernel = mock_semantic_kernel_instance
        kernel.invoke = MagicMock(return_value="Argument 1\nArgument 2") # Mock spécifique pour ce test
        
        informal_plugin = MagicMock(spec=InformalAnalysisPlugin)
        
        # patch_semantic_kernel est autouse, donc pas besoin de patcher sys.modules ici
        # setup_informal_kernel est appelé dans __init__ si kernel et plugin sont fournis
        with patch('argumentation_analysis.agents.core.informal.informal_agent.setup_informal_kernel') as mock_setup:
            agent = InformalAgent(
                agent_id="semantic_agent",
                tools={"fallacy_detector": mock_fallacy_detector},
                semantic_kernel=kernel,
                informal_plugin=informal_plugin
            )
            mock_setup.assert_called_once_with(kernel, informal_plugin)

        text = "Voici un texte avec plusieurs arguments."
        arguments = agent.identify_arguments(text)
        
        kernel.invoke.assert_called_once() # Vérifie que la méthode mockée du kernel a été appelée
        
        self.assertEqual(len(arguments), 2)
        self.assertEqual(arguments[0], "Argument 1")
        self.assertEqual(arguments[1], "Argument 2")
    
    def test_analyze_text_without_semantic_kernel(self, informal_agent_instance, mock_fallacy_detector):
        """Teste la méthode analyze_text sans kernel sémantique."""
        agent = informal_agent_instance
        text = "Voici un texte avec un seul argument."
        result = agent.analyze_text(text)
        
        self.assertIn("fallacies", result)
        self.assertIn("analysis_timestamp", result)
        self.assertIsInstance(result["fallacies"], list)
        mock_fallacy_detector.detect.assert_called_with(text) # `assert_called_with` car peut être appelé plusieurs fois
    
    def test_get_agent_capabilities(self, informal_agent_instance):
        """Teste la méthode get_agent_capabilities."""
        agent = informal_agent_instance
        capabilities = agent.get_agent_capabilities()
        
        self.assertTrue(capabilities["fallacy_detection"])
        self.assertTrue(capabilities["rhetorical_analysis"])
        self.assertTrue(capabilities["contextual_analysis"])
    
    def test_get_agent_info(self, informal_agent_instance):
        """Teste la méthode get_agent_info."""
        agent = informal_agent_instance
        info = agent.get_agent_info()
        
        self.assertEqual(info["agent_id"], "test_agent_fixture") # Id de la fixture
        self.assertEqual(info["agent_type"], "informal")
        self.assertTrue(info["capabilities"]["fallacy_detection"])
        self.assertEqual(len(info["tools"]), 3)
    
    def test_initialization_with_invalid_tools(self, mock_fallacy_detector):
        """Teste l'initialisation de l'agent informel avec des outils invalides."""
        invalid_tool = 123
        
        with self.assertRaises(TypeError):
            agent = InformalAgent( # pylint: disable=unused-variable
                agent_id="invalid_agent",
                tools={
                    "fallacy_detector": mock_fallacy_detector,
                    "invalid_tool": invalid_tool
                }
            )
    
    def test_initialization_without_fallacy_detector(self, mock_rhetorical_analyzer):
        """Teste l'initialisation de l'agent informel sans détecteur de sophismes."""
        with self.assertRaises(ValueError):
            agent = InformalAgent( # pylint: disable=unused-variable
                agent_id="missing_detector_agent",
                tools={
                    "rhetorical_analyzer": mock_rhetorical_analyzer
                }
            )
    
    def test_analyze_rhetoric_without_analyzer(self, mock_fallacy_detector):
        """Teste la méthode analyze_rhetoric sans analyseur rhétorique."""
        agent = InformalAgent(
            agent_id="no_rhetoric_agent",
            tools={
                "fallacy_detector": mock_fallacy_detector
            }
        )
        
        with self.assertRaises(ValueError):
            agent.analyze_rhetoric("Texte à analyser")
    
    def test_analyze_context_without_analyzer(self, mock_fallacy_detector):
        """Teste la méthode analyze_context sans analyseur contextuel."""
        agent = InformalAgent(
            agent_id="no_context_agent",
            tools={
                "fallacy_detector": mock_fallacy_detector
            }
        )
        
        with self.assertRaises(ValueError):
            agent.analyze_context("Texte à analyser")
    
    def test_identify_arguments_without_kernel(self, informal_agent_instance):
        """Teste la méthode identify_arguments sans kernel sémantique."""
        agent = informal_agent_instance # Cet agent n'a pas de kernel par défaut via la fixture
        with self.assertRaises(ValueError): # Devrait lever une erreur car kernel est None
            agent.identify_arguments("Texte à analyser")


if __name__ == "__main__":
    unittest.main()