#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour la création et l'initialisation des agents informels.
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
logger = logging.getLogger("TestInformalAgentCreation")

# Ajouter le répertoire racine au chemin Python pour pouvoir importer les modules
sys.path.append(os.path.abspath('..'))

# Utiliser les vraies bibliothèques numpy et pandas si disponibles
try:
    import numpy
    import pandas
    HAS_REAL_LIBS = True
except ImportError:
    # Importer les mocks pour numpy et pandas si les vraies bibliothèques ne sont pas disponibles
    from tests.mocks.numpy_mock import *
    from tests.mocks.pandas_mock import *
    
    # Patcher numpy et pandas avant d'importer le module à tester
    sys.modules['numpy'] = sys.modules.get('numpy')
    sys.modules['pandas'] = sys.modules.get('pandas')
    HAS_REAL_LIBS = False

# Mock pour semantic_kernel
class MockSemanticKernel:
    """Mock pour semantic_kernel."""
    
    def __init__(self):
        self.plugins = {}
    
    def add_plugin(self, plugin, name):
        """Ajoute un plugin au kernel."""
        self.plugins[name] = plugin
    
    def create_semantic_function(self, prompt, function_name=None, plugin_name=None, description=None, max_tokens=None, temperature=None, top_p=None):
        """Crée une fonction sémantique."""
        return MagicMock()
    
    def register_semantic_function(self, function, plugin_name, function_name):
        """Enregistre une fonction sémantique."""
        if plugin_name not in self.plugins:
            self.plugins[plugin_name] = {}
        self.plugins[plugin_name][function_name] = function

# Patcher semantic_kernel
sys.modules['semantic_kernel'] = MagicMock(
    Kernel=MockSemanticKernel
)

# Import du module à tester
from argumentation_analysis.agents.core.informal.informal_agent import InformalAgent
from argumentation_analysis.agents.core.informal.informal_definitions import InformalAnalysisPlugin


class TestInformalAgentCreation(unittest.TestCase):
    """Tests unitaires pour la création et l'initialisation des agents informels."""
    
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
    
    def test_initialization(self):
        """Teste l'initialisation de l'agent informel."""
        # Vérifier que l'agent a été correctement initialisé
        self.assertIsNotNone(self.agent)
        self.assertEqual(self.agent.agent_id, "test_agent")
        self.assertIsNotNone(self.agent.logger)
        
        # Vérifier que les outils ont été correctement assignés
        self.assertEqual(self.agent.tools["fallacy_detector"], self.fallacy_detector)
        self.assertEqual(self.agent.tools["rhetorical_analyzer"], self.rhetorical_analyzer)
        self.assertEqual(self.agent.tools["contextual_analyzer"], self.contextual_analyzer)
    
    def test_initialization_with_minimal_tools(self):
        """Teste l'initialisation de l'agent informel avec un minimum d'outils."""
        # Créer un agent avec seulement le détecteur de sophismes
        agent = InformalAgent(
            agent_id="minimal_agent",
            tools={
                "fallacy_detector": self.fallacy_detector
            }
        )
        
        # Vérifier que l'agent a été correctement initialisé
        self.assertIsNotNone(agent)
        self.assertEqual(agent.agent_id, "minimal_agent")
        
        # Vérifier que les outils ont été correctement assignés
        self.assertEqual(agent.tools["fallacy_detector"], self.fallacy_detector)
        self.assertNotIn("rhetorical_analyzer", agent.tools)
        self.assertNotIn("contextual_analyzer", agent.tools)
    
    def test_initialization_with_custom_config(self):
        """Teste l'initialisation de l'agent informel avec une configuration personnalisée."""
        # Créer une configuration personnalisée
        config = {
            "analysis_depth": "deep",
            "confidence_threshold": 0.6,
            "max_fallacies": 10,
            "include_context": True
        }
        
        # Créer un agent avec une configuration personnalisée
        agent = InformalAgent(
            agent_id="custom_agent",
            tools={
                "fallacy_detector": self.fallacy_detector
            },
            config=config
        )
        
        # Vérifier que l'agent a été correctement initialisé
        self.assertIsNotNone(agent)
        self.assertEqual(agent.agent_id, "custom_agent")
        
        # Vérifier que la configuration a été correctement assignée
        self.assertEqual(agent.config["analysis_depth"], "deep")
        self.assertEqual(agent.config["confidence_threshold"], 0.6)
        self.assertEqual(agent.config["max_fallacies"], 10)
        self.assertTrue(agent.config["include_context"])
    
    def test_initialization_with_semantic_kernel(self):
        """Teste l'initialisation de l'agent informel avec un kernel sémantique."""
        # Créer un kernel sémantique mock
        kernel = MockSemanticKernel()
        
        # Créer un plugin d'analyse informelle mock
        plugin = MagicMock(spec=InformalAnalysisPlugin)
        
        # Patcher la fonction setup_informal_kernel
        with patch('argumentation_analysis.agents.core.informal.informal_agent.setup_informal_kernel') as mock_setup:
            
            # Créer un agent avec un kernel sémantique
            agent = InformalAgent(
                agent_id="semantic_agent",
                tools={
                    "fallacy_detector": self.fallacy_detector
                },
                semantic_kernel=kernel,
                informal_plugin=plugin
            )
            
            # Vérifier que la fonction setup_informal_kernel a été appelée
            # L'appel réel est setup_informal_kernel(kernel, plugin)
            # car InformalAgent.__init__ passe self.informal_plugin comme deuxième argument.
            mock_setup.assert_called_once_with(kernel, plugin)
            
            # Vérifier que l'agent a été correctement initialisé
            self.assertIsNotNone(agent)
            self.assertEqual(agent.agent_id, "semantic_agent")
            self.assertEqual(agent.semantic_kernel, kernel)
            self.assertEqual(agent.informal_plugin, plugin)
    
    def test_initialization_with_invalid_tools(self):
        """Teste l'initialisation de l'agent informel avec des outils invalides."""
        # Créer un outil invalide
        invalid_tool = "not a tool"
        
        # Vérifier que l'initialisation avec un outil invalide lève une exception
        # Utiliser strict_validation=False pour tester seulement la validation de type
        with self.assertRaises(TypeError):
            agent = InformalAgent(
                agent_id="invalid_agent",
                tools={
                    "invalid_tool": invalid_tool
                },
                strict_validation=False
            )
    
    def test_initialization_with_missing_required_tool_flexible(self):
        """Teste l'initialisation de l'agent informel sans l'outil requis en mode flexible."""
        # Vérifier que l'initialisation sans le détecteur de sophismes fonctionne en mode flexible
        agent = InformalAgent(
            agent_id="flexible_agent",
            tools={
                "rhetorical_analyzer": self.rhetorical_analyzer
            },
            strict_validation=False
        )
        
        # Vérifier que l'agent a été correctement initialisé
        self.assertIsNotNone(agent)
        self.assertEqual(agent.agent_id, "flexible_agent")
        self.assertNotIn("fallacy_detector", agent.tools)
        self.assertIn("rhetorical_analyzer", agent.tools)
        
        # Vérifier que les capacités reflètent les outils disponibles
        capabilities = agent.get_agent_capabilities()
        self.assertFalse(capabilities["fallacy_detection"])
        self.assertTrue(capabilities["rhetorical_analysis"])
    
    def test_initialization_with_empty_tools(self):
        """Teste l'initialisation de l'agent informel sans outils."""
        # Vérifier que l'initialisation sans outils lève une exception
        with self.assertRaises(ValueError):
            agent = InformalAgent(
                agent_id="empty_agent",
                tools={}
            )
    
    def test_initialization_with_missing_required_tool(self):
        """Teste l'initialisation de l'agent informel sans l'outil requis."""
        # Vérifier que l'initialisation sans le détecteur de sophismes lève une exception
        with self.assertRaises(ValueError):
            agent = InformalAgent(
                agent_id="missing_tool_agent",
                tools={
                    "rhetorical_analyzer": self.rhetorical_analyzer
                }
            )
    
    def test_get_available_tools(self):
        """Teste la méthode get_available_tools."""
        # Appeler la méthode get_available_tools
        tools = self.agent.get_available_tools()
        
        # Vérifier le résultat
        self.assertIsInstance(tools, list)
        self.assertEqual(len(tools), 3)
        self.assertIn("fallacy_detector", tools)
        self.assertIn("rhetorical_analyzer", tools)
        self.assertIn("contextual_analyzer", tools)
    
    def test_get_agent_capabilities(self):
        """Teste la méthode get_agent_capabilities."""
        # Appeler la méthode get_agent_capabilities
        capabilities = self.agent.get_agent_capabilities()
        
        # Vérifier le résultat
        self.assertIsInstance(capabilities, dict)
        self.assertIn("fallacy_detection", capabilities)
        self.assertTrue(capabilities["fallacy_detection"])
        self.assertIn("rhetorical_analysis", capabilities)
        self.assertTrue(capabilities["rhetorical_analysis"])
        self.assertIn("contextual_analysis", capabilities)
        self.assertTrue(capabilities["contextual_analysis"])
    
    def test_get_agent_info(self):
        """Teste la méthode get_agent_info."""
        # Appeler la méthode get_agent_info
        info = self.agent.get_agent_info()
        
        # Vérifier le résultat
        self.assertIsInstance(info, dict)
        self.assertIn("agent_id", info)
        self.assertEqual(info["agent_id"], "test_agent")
        self.assertIn("agent_type", info)
        self.assertEqual(info["agent_type"], "informal")
        self.assertIn("capabilities", info)
        self.assertIsInstance(info["capabilities"], dict)
        self.assertIn("tools", info)
        self.assertIsInstance(info["tools"], list)
        self.assertEqual(len(info["tools"]), 3)


if __name__ == "__main__":
    unittest.main()