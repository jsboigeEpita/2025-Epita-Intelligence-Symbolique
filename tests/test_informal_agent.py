#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour l'agent informel.
"""

import unittest
import sys
import os
from unittest.mock import MagicMock, patch
import json
import logging

# Configurer le logging pour les tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("TestInformalAgent")

# Ajouter le répertoire racine au chemin Python pour pouvoir importer les modules
sys.path.append(os.path.abspath('..'))

# Mock pour semantic_kernel
class MockSemanticKernel:
    """Mock pour semantic_kernel."""
    
    def __init__(self):
        self.plugins = {}
    
    def add_plugin(self, plugin, plugin_name):
        """Ajoute un plugin au kernel."""
        self.plugins[plugin_name] = plugin
    
    def invoke(self, plugin_name, function_name, **kwargs):
        """Invoque une fonction du plugin."""
        if plugin_name in self.plugins and hasattr(self.plugins[plugin_name], function_name):
            return getattr(self.plugins[plugin_name], function_name)(**kwargs)
        return f"Invocation de {plugin_name}.{function_name} avec {kwargs}"

# Patcher semantic_kernel
sys.modules['semantic_kernel'] = MagicMock(
    Kernel=MockSemanticKernel
)

# Import du module à tester
from argumentation_analysis.agents.core.informal.informal_agent import InformalAgent


class TestInformalAgent(unittest.TestCase):
    """Tests unitaires pour l'agent informel."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        # Créer des mocks pour les outils
        self.fallacy_detector = MagicMock()
        self.fallacy_detector.detect = MagicMock(return_value=[
            {
                "fallacy_type": "Appel à l'autorité",
                "text": "Les experts affirment que ce produit est sûr.",
                "confidence": 0.7
            }
        ])
        
        self.rhetorical_analyzer = MagicMock()
        self.rhetorical_analyzer.analyze = MagicMock(return_value={
            "tone": "persuasif",
            "style": "émotionnel",
            "techniques": ["appel à l'émotion", "question rhétorique"],
            "effectiveness": 0.8
        })
        
        self.contextual_analyzer = MagicMock()
        self.contextual_analyzer.analyze_context = MagicMock(return_value={
            "context_type": "commercial",
            "confidence": 0.9
        })
        
        # Créer l'agent informel
        self.agent = InformalAgent(
            agent_id="test_agent",
            tools={
                "fallacy_detector": self.fallacy_detector,
                "rhetorical_analyzer": self.rhetorical_analyzer,
                "contextual_analyzer": self.contextual_analyzer
            }
        )
    
    def test_analyze_fallacies(self):
        """Teste la méthode analyze_fallacies."""
        # Appeler la méthode analyze_fallacies
        text = "Les experts affirment que ce produit est sûr."
        fallacies = self.agent.analyze_fallacies(text)
        
        # Vérifier que la méthode detect du détecteur de sophismes a été appelée
        self.fallacy_detector.detect.assert_called_once_with(text)
        
        # Vérifier le résultat
        self.assertEqual(len(fallacies), 1)
        self.assertEqual(fallacies[0]["fallacy_type"], "Appel à l'autorité")
        self.assertEqual(fallacies[0]["text"], "Les experts affirment que ce produit est sûr.")
        self.assertEqual(fallacies[0]["confidence"], 0.7)
    
    def test_analyze_rhetoric(self):
        """Teste la méthode analyze_rhetoric."""
        # Appeler la méthode analyze_rhetoric
        text = "N'est-il pas évident que ce produit va changer votre vie?"
        rhetoric = self.agent.analyze_rhetoric(text)
        
        # Vérifier que la méthode analyze de l'analyseur rhétorique a été appelée
        self.rhetorical_analyzer.analyze.assert_called_once_with(text)
        
        # Vérifier le résultat
        self.assertEqual(rhetoric["tone"], "persuasif")
        self.assertEqual(rhetoric["style"], "émotionnel")
        self.assertEqual(rhetoric["techniques"], ["appel à l'émotion", "question rhétorique"])
        self.assertEqual(rhetoric["effectiveness"], 0.8)
    
    def test_analyze_context(self):
        """Teste la méthode analyze_context."""
        # Appeler la méthode analyze_context
        text = "Achetez notre produit maintenant et bénéficiez d'une réduction de 20%!"
        context = self.agent.analyze_context(text)
        
        # Vérifier que la méthode analyze_context de l'analyseur contextuel a été appelée
        self.contextual_analyzer.analyze_context.assert_called_once_with(text)
        
        # Vérifier le résultat
        self.assertEqual(context["context_type"], "commercial")
        self.assertEqual(context["confidence"], 0.9)
    
    def test_analyze_argument(self):
        """Teste la méthode analyze_argument."""
        # Appeler la méthode analyze_argument
        text = "Les experts affirment que ce produit est sûr. N'est-il pas évident que vous devriez l'acheter?"
        result = self.agent.analyze_argument(text)
        
        # Vérifier que les méthodes des outils ont été appelées
        self.fallacy_detector.detect.assert_called_once_with(text)
        self.rhetorical_analyzer.analyze.assert_called_once_with(text)
        
        # Vérifier le résultat
        self.assertEqual(result["argument"], text)
        self.assertEqual(len(result["fallacies"]), 1)
        self.assertEqual(result["fallacies"][0]["fallacy_type"], "Appel à l'autorité")
        self.assertEqual(result["rhetoric"]["tone"], "persuasif")
    
    def test_analyze_text_with_semantic_kernel(self):
        """Teste la méthode analyze_text avec un kernel sémantique."""
        # Créer un kernel sémantique mock
        kernel = MockSemanticKernel()
        kernel.invoke = MagicMock(return_value="Argument 1\nArgument 2")
        
        # Créer un plugin informel mock
        informal_plugin = MagicMock()
        
        # Patcher la fonction setup_informal_kernel
        with patch('argumentation_analysis.agents.core.informal.informal_agent.setup_informal_kernel') as mock_setup:
            # Créer un agent avec un kernel sémantique
            agent = InformalAgent(
                agent_id="semantic_agent",
                tools={
                    "fallacy_detector": self.fallacy_detector
                },
                semantic_kernel=kernel,
                informal_plugin=informal_plugin
            )
        
        # Appeler la méthode analyze_text
        text = "Voici un texte avec plusieurs arguments."
        result = agent.analyze_text(text)
        
        # Vérifier que la méthode invoke du kernel a été appelée
        kernel.invoke.assert_called_once()
        
        # Vérifier le résultat
        self.assertEqual(result["text"], text)
        self.assertEqual(len(result["arguments"]), 2)
    
    def test_analyze_text_without_semantic_kernel(self):
        """Teste la méthode analyze_text sans kernel sémantique."""
        # Appeler la méthode analyze_text
        text = "Voici un texte avec un seul argument."
        result = self.agent.analyze_text(text)
        
        # Vérifier le résultat
        self.assertEqual(result["text"], text)
        self.assertEqual(len(result["arguments"]), 1)
        self.assertEqual(result["arguments"][0]["argument"], text)
    
    def test_get_agent_capabilities(self):
        """Teste la méthode get_agent_capabilities."""
        # Appeler la méthode get_agent_capabilities
        capabilities = self.agent.get_agent_capabilities()
        
        # Vérifier le résultat
        self.assertTrue(capabilities["fallacy_detection"])
        self.assertTrue(capabilities["rhetorical_analysis"])
        self.assertTrue(capabilities["contextual_analysis"])
    
    def test_get_agent_info(self):
        """Teste la méthode get_agent_info."""
        # Appeler la méthode get_agent_info
        info = self.agent.get_agent_info()
        
        # Vérifier le résultat
        self.assertEqual(info["agent_id"], "test_agent")
        self.assertEqual(info["agent_type"], "informal")
        self.assertTrue(info["capabilities"]["fallacy_detection"])
        self.assertEqual(len(info["tools"]), 3)
    
    def test_initialization_with_invalid_tools(self):
        """Teste l'initialisation de l'agent informel avec des outils invalides."""
        # Créer un outil invalide qui n'est ni callable ni un objet
        class MockTool:
            pass
        
        invalid_tool = 123  # Un entier n'est ni callable ni un objet complexe
        
        # Vérifier que l'initialisation avec un outil invalide lève une exception
        with self.assertRaises(TypeError):
            agent = InformalAgent(
                agent_id="invalid_agent",
                tools={
                    "fallacy_detector": self.fallacy_detector,
                    "invalid_tool": invalid_tool
                }
            )
    
    def test_initialization_without_fallacy_detector(self):
        """Teste l'initialisation de l'agent informel sans détecteur de sophismes."""
        # Vérifier que l'initialisation sans détecteur de sophismes lève une exception
        with self.assertRaises(ValueError):
            agent = InformalAgent(
                agent_id="missing_detector_agent",
                tools={
                    "rhetorical_analyzer": self.rhetorical_analyzer
                }
            )
    
    def test_analyze_rhetoric_without_analyzer(self):
        """Teste la méthode analyze_rhetoric sans analyseur rhétorique."""
        # Créer un agent sans analyseur rhétorique
        agent = InformalAgent(
            agent_id="no_rhetoric_agent",
            tools={
                "fallacy_detector": self.fallacy_detector
            }
        )
        
        # Vérifier que l'appel à analyze_rhetoric lève une exception
        with self.assertRaises(ValueError):
            agent.analyze_rhetoric("Texte à analyser")
    
    def test_analyze_context_without_analyzer(self):
        """Teste la méthode analyze_context sans analyseur contextuel."""
        # Créer un agent sans analyseur contextuel
        agent = InformalAgent(
            agent_id="no_context_agent",
            tools={
                "fallacy_detector": self.fallacy_detector
            }
        )
        
        # Vérifier que l'appel à analyze_context lève une exception
        with self.assertRaises(ValueError):
            agent.analyze_context("Texte à analyser")
    
    def test_identify_arguments_without_kernel(self):
        """Teste la méthode identify_arguments sans kernel sémantique."""
        # Vérifier que l'appel à identify_arguments sans kernel lève une exception
        with self.assertRaises(ValueError):
            self.agent.identify_arguments("Texte à analyser")


if __name__ == "__main__":
    unittest.main()