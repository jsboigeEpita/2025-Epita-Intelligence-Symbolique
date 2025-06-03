#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour la création et l'initialisation des agents informels.
"""

import unittest # Rétabli
import pytest # Ajouté
from unittest.mock import MagicMock, patch
import logging

# Configurer le logging pour les tests
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("TestInformalAgentCreation")

# Import du module à tester et des dépendances nécessaires
import semantic_kernel as sk
from argumentation_analysis.agents.core.informal.informal_agent import InformalAnalysisAgent
from argumentation_analysis.agents.core.informal.informal_definitions import INFORMAL_AGENT_INSTRUCTIONS, InformalAnalysisPlugin


class TestInformalAgentCreationAndInfo(unittest.TestCase): # Renommé pour refléter le contenu
    """Tests unitaires pour la création, l'initialisation et l'information des agents informels."""

    def setUp(self):
        """Initialisation avant chaque test."""
        self.kernel = MagicMock(spec=sk.Kernel)
        self.kernel.add_plugin = MagicMock()
        self.kernel.add_function = MagicMock()
        self.kernel.get_prompt_execution_settings_from_service_id = MagicMock(return_value={"temperature": 0.7})
        
        # Patch pour InformalAnalysisPlugin pour contrôler son instanciation
        self.informal_plugin_patcher = patch('argumentation_analysis.agents.core.informal.informal_agent.InformalAnalysisPlugin')
        self.mock_informal_plugin_class = self.informal_plugin_patcher.start()
        self.mock_informal_plugin_instance = MagicMock(spec=InformalAnalysisPlugin)
        self.mock_informal_plugin_class.return_value = self.mock_informal_plugin_instance

        self.agent_name = "TestInformalAgentInstance"
        self.agent = InformalAnalysisAgent(
            kernel=self.kernel,
            agent_name=self.agent_name,
            taxonomy_file_path="argumentation_analysis/data/mock_taxonomy_small.csv"
        )
        
        self.llm_service_id = "test_llm_service_for_informal"
        # Appel explicite à setup_agent_components
        self.agent.setup_agent_components(llm_service_id=self.llm_service_id)

    def tearDown(self):
        self.informal_plugin_patcher.stop()

    def test_agent_initialization_and_setup_verification(self):
        """Vérifie l'initialisation correcte et l'appel à setup_agent_components."""
        self.assertIsNotNone(self.agent)
        self.assertEqual(self.agent.name, self.agent_name)
        self.assertEqual(self.agent.sk_kernel, self.kernel)
        self.assertEqual(self.agent.system_prompt, INFORMAL_AGENT_INSTRUCTIONS)
        self.assertEqual(self.agent._llm_service_id, self.llm_service_id)

        # Vérifier que InformalAnalysisPlugin a été instancié et ajouté au kernel
        self.mock_informal_plugin_class.assert_called_once()
        self.kernel.add_plugin.assert_called_once_with(self.mock_informal_plugin_instance, plugin_name="InformalAnalyzer")

        # Vérifier que les fonctions sémantiques ont été ajoutées
        # (identify_arguments, analyze_fallacies, justify_fallacy_attribution)
        self.assertEqual(self.kernel.add_function.call_count, 3)
        self.kernel.get_prompt_execution_settings_from_service_id.assert_called_with(self.llm_service_id)
        
        # Vérifier la config par défaut
        self.assertIn("analysis_depth", self.agent.config)
        self.assertEqual(self.agent.config["analysis_depth"], "standard")

    def test_get_agent_capabilities(self):
        """Teste la méthode get_agent_capabilities."""
        capabilities = self.agent.get_agent_capabilities()
        
        self.assertIsInstance(capabilities, dict)
        self.assertIn("identify_arguments", capabilities)
        self.assertIn("analyze_fallacies", capabilities)
        self.assertIn("explore_fallacy_hierarchy", capabilities)
        self.assertIn("get_fallacy_details", capabilities)
        self.assertIn("categorize_fallacies", capabilities)
        self.assertIn("perform_complete_analysis", capabilities)

    def test_get_agent_info(self):
        """Teste la méthode get_agent_info."""
        info = self.agent.get_agent_info()
        
        self.assertIsInstance(info, dict)
        self.assertEqual(info["name"], self.agent_name)
        self.assertEqual(info["class"], "InformalAnalysisAgent")
        self.assertEqual(info["system_prompt"], INFORMAL_AGENT_INSTRUCTIONS)
        self.assertEqual(info["llm_service_id"], self.llm_service_id)
        
        self.assertIn("capabilities", info)
        self.assertIsInstance(info["capabilities"], dict)
        self.assertIn("identify_arguments", info["capabilities"]) # Vérifier une capacité spécifique

# Les lignes commentées if __name__ == "__main__": et unittest.main() sont omises.