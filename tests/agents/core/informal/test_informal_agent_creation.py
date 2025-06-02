#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour la création et l'initialisation des agents informels.
"""

import unittest
from unittest.mock import MagicMock, patch
# import json # Semble inutilisé

# La configuration du logging et les imports conditionnels de numpy/pandas
# sont maintenant gérés globalement dans tests/conftest.py

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
from argumentation_analysis.agents.core.informal.informal_definitions import InformalAnalysisPlugin


class TestInformalAgentCreation(unittest.TestCase):
    """Tests unitaires pour la création et l'initialisation des agents informels."""
    
    # setUp n'est plus nécessaire si les tests utilisent directement les fixtures pour les instances
    # def setUp(self):
    #     """Initialisation avant chaque test."""
    #     pass

    def test_initialization(self, informal_agent_instance, mock_fallacy_detector, mock_rhetorical_analyzer, mock_contextual_analyzer):
        """Teste l'initialisation de l'agent informel."""
        agent = informal_agent_instance # Utilise la fixture
        # Vérifier que l'agent a été correctement initialisé
        self.assertIsNotNone(agent)
        self.assertEqual(agent.agent_id, "test_agent_fixture") # Id de la fixture
        self.assertIsNotNone(agent.logger)
        
        # Vérifier que les outils ont été correctement assignés
        self.assertEqual(agent.tools["fallacy_detector"], mock_fallacy_detector)
        self.assertEqual(agent.tools["rhetorical_analyzer"], mock_rhetorical_analyzer)
        self.assertEqual(agent.tools["contextual_analyzer"], mock_contextual_analyzer)
    
    def test_initialization_with_minimal_tools(self, mock_fallacy_detector):
        """Teste l'initialisation de l'agent informel avec un minimum d'outils."""
        # Créer un agent avec seulement le détecteur de sophismes
        agent = InformalAgent(
            agent_id="minimal_agent",
            tools={
                "fallacy_detector": mock_fallacy_detector # Utilise la fixture
            }
        )
        
        # Vérifier que l'agent a été correctement initialisé
        self.assertIsNotNone(agent)
        self.assertEqual(agent.agent_id, "minimal_agent")
        
        # Vérifier que les outils ont été correctement assignés
        self.assertEqual(agent.tools["fallacy_detector"], mock_fallacy_detector)
        self.assertNotIn("rhetorical_analyzer", agent.tools)
        self.assertNotIn("contextual_analyzer", agent.tools)
    
    def test_initialization_with_custom_config(self, mock_fallacy_detector):
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
                "fallacy_detector": mock_fallacy_detector # Utilise la fixture
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
    
    def test_initialization_with_semantic_kernel(self, mock_semantic_kernel_instance, mock_fallacy_detector):
        """Teste l'initialisation de l'agent informel avec un kernel sémantique."""
        kernel = mock_semantic_kernel_instance # Utilise la fixture
        
        # Créer un plugin d'analyse informelle mock
        # Note: Si InformalAnalysisPlugin a des dépendances complexes,
        # une fixture dédiée pourrait être nécessaire. Ici, on suppose qu'un MagicMock suffit.
        plugin = MagicMock(spec=InformalAnalysisPlugin)
        
        # Patcher la fonction setup_informal_kernel
        with patch('argumentation_analysis.agents.core.informal.informal_agent.setup_informal_kernel') as mock_setup:
            
            # Créer un agent avec un kernel sémantique
            agent = InformalAgent(
                agent_id="semantic_agent",
                tools={
                    "fallacy_detector": mock_fallacy_detector # Utilise la fixture
                },
                semantic_kernel=kernel,
                informal_plugin=plugin
            )
            
            # Vérifier que la fonction setup_informal_kernel a été appelée
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
        with self.assertRaises(TypeError):
            agent = InformalAgent( # pylint: disable=unused-variable
                agent_id="invalid_agent",
                tools={
                    "invalid_tool": invalid_tool
                },
                strict_validation=False
            )
    
    def test_initialization_with_missing_required_tool_flexible(self, mock_rhetorical_analyzer):
        """Teste l'initialisation de l'agent informel sans l'outil requis en mode flexible."""
        agent = InformalAgent(
            agent_id="flexible_agent",
            tools={
                "rhetorical_analyzer": mock_rhetorical_analyzer # Utilise la fixture
            },
            strict_validation=False
        )
        
        self.assertIsNotNone(agent)
        self.assertEqual(agent.agent_id, "flexible_agent")
        self.assertNotIn("fallacy_detector", agent.tools)
        self.assertIn("rhetorical_analyzer", agent.tools)
        
        capabilities = agent.get_agent_capabilities()
        self.assertFalse(capabilities["fallacy_detection"])
        self.assertTrue(capabilities["rhetorical_analysis"])
    
    def test_initialization_with_empty_tools(self):
        """Teste l'initialisation de l'agent informel sans outils."""
        with self.assertRaises(ValueError):
            agent = InformalAgent( # pylint: disable=unused-variable
                agent_id="empty_agent",
                tools={}
            )
    
    def test_initialization_with_missing_required_tool(self, mock_rhetorical_analyzer):
        """Teste l'initialisation de l'agent informel sans l'outil requis."""
        with self.assertRaises(ValueError):
            agent = InformalAgent( # pylint: disable=unused-variable
                agent_id="missing_tool_agent",
                tools={
                    "rhetorical_analyzer": mock_rhetorical_analyzer # Utilise la fixture
                }
            )
    
    def test_get_available_tools(self, informal_agent_instance):
        """Teste la méthode get_available_tools."""
        agent = informal_agent_instance # Utilise la fixture
        tools = agent.get_available_tools()
        
        self.assertIsInstance(tools, list)
        self.assertEqual(len(tools), 3)
        self.assertIn("fallacy_detector", tools)
        self.assertIn("rhetorical_analyzer", tools)
        self.assertIn("contextual_analyzer", tools)
    
    def test_get_agent_capabilities(self, informal_agent_instance):
        """Teste la méthode get_agent_capabilities."""
        agent = informal_agent_instance # Utilise la fixture
        capabilities = agent.get_agent_capabilities()
        
        self.assertIsInstance(capabilities, dict)
        self.assertIn("fallacy_detection", capabilities)
        self.assertTrue(capabilities["fallacy_detection"])
        self.assertIn("rhetorical_analysis", capabilities)
        self.assertTrue(capabilities["rhetorical_analysis"])
        self.assertIn("contextual_analysis", capabilities)
        self.assertTrue(capabilities["contextual_analysis"])
    
    def test_get_agent_info(self, informal_agent_instance):
        """Teste la méthode get_agent_info."""
        agent = informal_agent_instance # Utilise la fixture
        info = agent.get_agent_info()
        
        self.assertIsInstance(info, dict)
        self.assertIn("agent_id", info)
        self.assertEqual(info["agent_id"], "test_agent_fixture") # Id de la fixture
        self.assertIn("agent_type", info)
        self.assertEqual(info["agent_type"], "informal")
        self.assertIn("capabilities", info)
        self.assertIsInstance(info["capabilities"], dict)
        self.assertIn("tools", info)
        self.assertIsInstance(info["tools"], list)
        self.assertEqual(len(info["tools"]), 3)


if __name__ == "__main__":
    unittest.main()