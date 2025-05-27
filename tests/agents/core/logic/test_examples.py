# tests/agents/core/logic/test_examples.py
"""
Tests unitaires pour vérifier que les exemples de code fonctionnent correctement.
"""

import unittest
import importlib.util
import os
import sys
from unittest.mock import patch, MagicMock

from semantic_kernel import Kernel


class TestLogicExamples(unittest.TestCase):
    """Tests unitaires pour les exemples de code des agents logiques."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        # Mock du kernel
        self.kernel_patcher = patch('semantic_kernel.Kernel')
        self.mock_kernel_class = self.kernel_patcher.start()
        self.mock_kernel = MagicMock(spec=Kernel)
        self.mock_kernel_class.return_value = self.mock_kernel
        
        # Mock des plugins
        self.mock_kernel.plugins = {
            "PLAnalyzer": {
                "semantic_TextToPLBeliefSet": MagicMock(),
                "semantic_GeneratePLQueries": MagicMock(),
                "semantic_InterpretPLResult": MagicMock(),
                "execute_pl_query": MagicMock()
            },
            "FOLAnalyzer": {
                "semantic_TextToFOLBeliefSet": MagicMock(),
                "semantic_GenerateFOLQueries": MagicMock(),
                "semantic_InterpretFOLResult": MagicMock(),
                "execute_fol_query": MagicMock()
            },
            "ModalAnalyzer": {
                "semantic_TextToModalBeliefSet": MagicMock(),
                "semantic_GenerateModalQueries": MagicMock(),
                "semantic_InterpretModalResult": MagicMock(),
                "execute_modal_query": MagicMock()
            }
        }
        
        # Configurer les mocks des fonctions
        for plugin in self.mock_kernel.plugins.values():
            for func in plugin.values():
                func.invoke.return_value = MagicMock(result="Mock result")
        
        # Patcher TweetyBridge
        self.tweety_bridge_patcher = patch('argumentation_analysis.agents.core.logic.tweety_bridge.TweetyBridge')
        self.mock_tweety_bridge_class = self.tweety_bridge_patcher.start()
        self.mock_tweety_bridge = MagicMock()
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
        self.mock_response = MagicMock()
        self.mock_response.json.return_value = {"success": True, "result": {"result": True}}
        self.mock_response.status_code = 200
        self.mock_requests_post.return_value = self.mock_response
    
    def tearDown(self):
        """Nettoyage après chaque test."""
        self.kernel_patcher.stop()
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
    
    def test_propositional_logic_example(self):
        """Test de l'exemple de logique propositionnelle."""
        with patch('builtins.print'):  # Supprimer les sorties
            # Importer le module
            example_path = os.path.join('examples', 'logic_agents', 'propositional_logic_example.py')
            try:
                self._import_module_from_file(example_path)
                # Si aucune exception n'est levée, le test réussit
                self.assertTrue(True)
            except Exception as e:
                self.fail(f"L'exemple de logique propositionnelle a échoué: {str(e)}")
    
    def test_first_order_logic_example(self):
        """Test de l'exemple de logique du premier ordre."""
        with patch('builtins.print'):  # Supprimer les sorties
            # Importer le module
            example_path = os.path.join('examples', 'logic_agents', 'first_order_logic_example.py')
            try:
                self._import_module_from_file(example_path)
                # Si aucune exception n'est levée, le test réussit
                self.assertTrue(True)
            except Exception as e:
                self.fail(f"L'exemple de logique du premier ordre a échoué: {str(e)}")
    
    def test_modal_logic_example(self):
        """Test de l'exemple de logique modale."""
        with patch('builtins.print'):  # Supprimer les sorties
            # Importer le module
            example_path = os.path.join('examples', 'logic_agents', 'modal_logic_example.py')
            try:
                self._import_module_from_file(example_path)
                # Si aucune exception n'est levée, le test réussit
                self.assertTrue(True)
            except Exception as e:
                self.fail(f"L'exemple de logique modale a échoué: {str(e)}")
    
    def test_api_integration_example(self):
        """Test de l'exemple d'intégration de l'API."""
        with patch('builtins.print'):  # Supprimer les sorties
            # Importer le module
            example_path = os.path.join('examples', 'logic_agents', 'api_integration_example.py')
            try:
                self._import_module_from_file(example_path)
                # Si aucune exception n'est levée, le test réussit
                self.assertTrue(True)
            except Exception as e:
                self.fail(f"L'exemple d'intégration de l'API a échoué: {str(e)}")
    
    def test_combined_logic_example(self):
        """Test de l'exemple combinant différents types de logique."""
        with patch('builtins.print'):  # Supprimer les sorties
            # Importer le module
            example_path = os.path.join('examples', 'logic_agents', 'combined_logic_example.py')
            try:
                self._import_module_from_file(example_path)
                # Si aucune exception n'est levée, le test réussit
                self.assertTrue(True)
            except Exception as e:
                self.fail(f"L'exemple combinant différents types de logique a échoué: {str(e)}")


if __name__ == "__main__":
    unittest.main()