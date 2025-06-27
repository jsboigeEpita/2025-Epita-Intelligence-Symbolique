import unittest
from unittest.mock import MagicMock, patch
import os

# Assurez-vous que le PYTHONPATH est correctement configuré pour les tests
# Cela peut être géré via la configuration de pytest (pytest.ini) ou un script de lancement
from project_core.core_from_scripts.validation.validation_engine import ValidationEngine, ValidationRule, ValidationResult
from project_core.core_from_scripts.validation.rules.config_rules import ConfigValidationRule
from project_core.core_from_scripts.common_utils import Logger

class TestValidationEngine(unittest.TestCase):

    def setUp(self):
        """Configuration initiale pour les tests."""
        self.logger = Logger(verbose=True)
        # Mock de l'EnvironmentManager pour contrôler le chemin du projet
        self.env_manager_mock = MagicMock()
        self.env_manager_mock.project_root = os.path.abspath('.')

    @patch('project_core.core_from_scripts.validation.validation_engine.EnvironmentManager')
    def test_engine_loads_rules(self, mock_env_manager):
        """Vérifie que le moteur charge correctement les règles."""
        mock_env_manager.return_value = self.env_manager_mock
        
        engine = ValidationEngine(logger=self.logger)
        self.assertGreater(len(engine.rules), 0)
        self.assertIsInstance(engine.rules[0], ConfigValidationRule)

    @patch('project_core.core_from_scripts.validation.validation_engine.EnvironmentManager')
    @patch('os.path.exists')
    def test_config_rule_success(self, mock_exists, mock_env_manager):
        """Teste la ConfigValidationRule lorsque tous les fichiers existent."""
        mock_exists.return_value = True
        mock_env_manager.return_value = self.env_manager_mock
        
        engine = ValidationEngine(logger=self.logger)
        rule = ConfigValidationRule(engine)
        result = rule.validate()
        
        self.assertTrue(result.success)
        self.assertEqual(result.rule_name, "ConfigValidationRule")
        self.assertIn("Tous les fichiers de configuration essentiels sont présents", result.message)

    @patch('project_core.core_from_scripts.validation.validation_engine.EnvironmentManager')
    @patch('os.path.exists')
    def test_config_rule_failure(self, mock_exists, mock_env_manager):
        """Teste la ConfigValidationRule lorsqu'il manque un fichier."""
        # Simule qu'un fichier est manquant
        def side_effect(path):
            if "pyproject.toml" in path:
                return False
            return True
        mock_exists.side_effect = side_effect
        mock_env_manager.return_value = self.env_manager_mock
        
        engine = ValidationEngine(logger=self.logger)
        rule = ConfigValidationRule(engine)
        result = rule.validate()
        
        self.assertFalse(result.success)
        self.assertEqual(result.rule_name, "ConfigValidationRule")
        self.assertIn("Fichiers de configuration manquants", result.message)
        self.assertIn("pyproject.toml", result.message)
        self.assertEqual(result.details['missing_files'], ["pyproject.toml"])

    @patch('project_core.core_from_scripts.validation.validation_engine.EnvironmentManager')
    def test_engine_run(self, mock_env_manager):
        """Teste l'exécution complète du moteur avec une règle mockée."""
        mock_env_manager.return_value = self.env_manager_mock

        # Crée une règle mockée
        mock_rule = MagicMock(spec=ValidationRule)
        mock_rule.name = "MockRule"
        mock_rule.validate.return_value = ValidationResult(success=True, rule_name="MockRule", message="OK")

        engine = ValidationEngine(logger=self.logger)
        # Remplace les règles chargées par notre mock
        engine.rules = [mock_rule]
        
        results = engine.run()
        
        self.assertEqual(len(results), 1)
        mock_rule.validate.assert_called_once()
        self.assertEqual(results[0].rule_name, "MockRule")

if __name__ == '__main__':
    unittest.main()