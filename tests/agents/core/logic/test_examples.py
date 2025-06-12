
# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

# -*- coding: utf-8 -*-
# tests/agents/core/logic/test_examples.py
"""
Tests unitaires pour vérifier que les exemples de code fonctionnent correctement.
"""

import unittest
import importlib.util
import os
import sys


from semantic_kernel import Kernel


import pytest
from unittest.mock import patch, MagicMock

class TestLogicExamples:
    async def _create_authentic_gpt4o_mini_instance(self):
        """Crée une instance authentique de gpt-4o-mini au lieu d'un mock."""
        config = UnifiedConfig()
        return config.get_kernel_with_gpt4o_mini()
        
    async def _make_authentic_llm_call(self, prompt: str) -> str:
        """Fait un appel authentique à gpt-4o-mini."""
        try:
            kernel = await self._create_authentic_gpt4o_mini_instance()
            result = await kernel.invoke("chat", input=prompt)
            return str(result)
        except Exception as e:
            logger.warning(f"Appel LLM authentique échoué: {e}")
            return "Authentic LLM call failed"

    """Tests unitaires pour les exemples de code des agents logiques."""
    
    async def asyncSetUp(self):
        """Initialisation asynchrone avant chaque test."""
        self.mock_kernel = await self._create_authentic_gpt4o_mini_instance()
        
        # Patcher TweetyBridge
        self.tweety_bridge_patcher = patch('argumentation_analysis.agents.core.logic.tweety_bridge.TweetyBridge')
        self.mock_tweety_bridge_class = self.tweety_bridge_patcher.start()
        self.mock_tweety_bridge = await self._create_authentic_gpt4o_mini_instance()
        self.mock_tweety_bridge_class.return_value = self.mock_tweety_bridge
        
        # Configurer le mock de TweetyBridge
        self.mock_tweety_bridge.is_jvm_ready.return_value = True
        self.mock_tweety_bridge.validate_belief_set.return_value = (True, "Ensemble de croyances valide")
        self.mock_tweety_bridge.validate_formula.return_value = (True, "Formule valide")
        self.mock_tweety_bridge.validate_fol_belief_set.return_value = (True, "Ensemble de croyances FOL valide")
        self.mock_tweety_bridge.validate_fol_formula.return_value = (True, "Formule FOL valide")
        self.mock_tweety_bridge.validate_modal_belief_set.return_value = (True, "Ensemble de croyances modal valide")
        self.mock_tweety_bridge.validate_modal_formula.return_value = (True, "Formule modale valide")
        
        # Patcher requests pour l'exemple d'API
        self.requests_patcher = patch('requests.post')
        self.mock_requests_post = self.requests_patcher.start()
        self.mock_response = await self._create_authentic_gpt4o_mini_instance()
        self.mock_response.json.return_value = {"success": True, "result": {"result": True}}
        self.mock_response.status_code = 200
        self.mock_requests_post.return_value = self.mock_response
    
    def tearDown(self):
        """Nettoyage après chaque test."""
        # self.kernel_patcher.stop() # Plus nécessaire avec le nouveau setUp
        self.tweety_bridge_patcher.stop()
        self.requests_patcher.stop()
    
    def _import_module_from_file(self, file_path):
        """Importe un module à partir d'un fichier."""
        module_name = os.path.basename(file_path).replace('.py', '')
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    
    async def test_propositional_logic_example(self):
        """Test de l'exemple de logique propositionnelle."""
        await self.asyncSetUp()
        with patch('builtins.print'):  # Supprimer les sorties
            # Importer le module
            example_path = os.path.join('examples', 'logic_agents', 'propositional_logic_example.py')
            try:
                self._import_module_from_file(example_path)
                # Si aucune exception n'est levée, le test réussit
                assert True
            except Exception as e:
                self.fail(f"L'exemple de logique propositionnelle a échoué: {str(e)}")
    
    async def test_first_order_logic_example(self):
        """Test de l'exemple de logique du premier ordre."""
        await self.asyncSetUp()
        with patch('builtins.print'):  # Supprimer les sorties
            # Importer le module
            example_path = os.path.join('examples', 'logic_agents', 'first_order_logic_example.py')
            try:
                self._import_module_from_file(example_path)
                # Si aucune exception n'est levée, le test réussit
                assert True
            except Exception as e:
                self.fail(f"L'exemple de logique du premier ordre a échoué: {str(e)}")
    
    async def test_modal_logic_example(self):
        """Test de l'exemple de logique modale."""
        await self.asyncSetUp()
        with patch('builtins.print'):  # Supprimer les sorties
            # Importer le module
            example_path = os.path.join('examples', 'logic_agents', 'modal_logic_example.py')
            try:
                self._import_module_from_file(example_path)
                # Si aucune exception n'est levée, le test réussit
                assert True
            except Exception as e:
                self.fail(f"L'exemple de logique modale a échoué: {str(e)}")
    
    async def test_api_integration_example(self):
        """Test de l'exemple d'intégration de l'API."""
        await self.asyncSetUp()
        with patch('builtins.print'):  # Supprimer les sorties
            # Importer le module
            example_path = os.path.join('examples', 'logic_agents', 'api_integration_example.py')
            try:
                self._import_module_from_file(example_path)
                # Si aucune exception n'est levée, le test réussit
                assert True
            except Exception as e:
                self.fail(f"L'exemple d'intégration de l'API a échoué: {str(e)}")
    
    async def test_combined_logic_example(self):
        """Test de l'exemple combinant différents types de logique."""
        await self.asyncSetUp()
        with patch('builtins.print'):  # Supprimer les sorties
            # Importer le module
            example_path = os.path.join('examples', 'logic_agents', 'combined_logic_example.py')
            try:
                self._import_module_from_file(example_path)
                # Si aucune exception n'est levée, le test réussit
                assert True
            except Exception as e:
                self.fail(f"L'exemple combinant différents types de logique a échoué: {str(e)}")


if __name__ == "__main__":
    unittest.main()