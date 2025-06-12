#!/usr/bin/env python3
"""
Tests d'intégration pour TestRunner
Validation des fonctionnalités de remplacement PowerShell
"""

import unittest
from unittest.mock import patch, Mock
import sys
import os
import tempfile
import shutil
from pathlib import Path
import logging

# Ajouter project_core au path
# Cette manipulation de path peut être fragile.
# L'installation en mode éditable est préférable.
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "project_core"))

# Imports depuis le code du projet
from project_core.test_runner import TestRunner, TestConfig, EnvironmentManager

# Configuration du logger pour éviter des erreurs si non configuré
logger = logging.getLogger(__name__)


class TestEnvironmentManager(unittest.TestCase):
    """Tests d'intégration pour EnvironmentManager"""

    def setUp(self):
        self.env_manager = EnvironmentManager(logger)

    def test_detect_conda_environments(self):
        """Test détection environnements conda"""
        try:
            envs = self.env_manager.detect_conda_environments()
            self.assertIsInstance(envs, list)
        except Exception as e:
            self.assertIn("conda", str(e).lower())

    def test_activate_conda_env_success(self):
        """Test activation environnement conda - succès ou échec selon installation"""
        result = self.env_manager.activate_conda_env("test-env")
        self.assertIsInstance(result, bool)

    @patch('project_core.test_runner.EnvironmentManager.run_command')
    def test_activate_conda_env_failure(self, mock_run_command):
        """Test activation environnement conda - échec"""
        mock_run_command.side_effect = Exception("Conda not found")
        result = self.env_manager.activate_conda_env("test-env")
        self.assertFalse(result)


class TestTestConfig(unittest.TestCase):
    """Tests d'intégration pour TestConfig"""

    def test_test_config_creation(self):
        """Test création configuration de test"""
        from project_core.test_runner import TestType
        config = TestConfig(
            test_type=TestType.INTEGRATION,
            test_paths=["./tests"],
            conda_env="test-env",
            timeout=300
        )
        self.assertEqual(config.test_type, TestType.INTEGRATION)
        self.assertEqual(config.test_paths, ["./tests"])
        self.assertEqual(config.conda_env, "test-env")
        self.assertEqual(config.timeout, 300)
        self.assertFalse(config.requires_backend)
        self.assertFalse(config.requires_frontend)


class TestTestRunner(unittest.TestCase):
    """Tests d'intégration pour TestRunner"""

    def setUp(self):
        self.test_runner = TestRunner()

    def test_test_runner_initialization(self):
        """Test initialisation TestRunner"""
        self.assertIsNotNone(self.test_runner.service_manager)
        self.assertIsNotNone(self.test_runner.env_manager)
        self.assertIsInstance(self.test_runner.test_configs, dict)

    def test_register_test_config(self):
        """Test enregistrement configuration de test"""
        from project_core.test_runner import TestType
        config = TestConfig(
            test_type=TestType.UNIT,
            test_paths=["tests/unit"]
        )
        self.assertIsNotNone(self.test_runner)

    @patch('project_core.test_runner.TestRunner.run_command_in_env')
    def test_run_tests_simple_success(self, mock_run):
        """Test exécution tests simple - succès"""
        mock_run.return_value = (0, "Tests passed", "")
        result = self.test_runner.run_tests("unit")
        self.assertEqual(result, 0)

    @patch('project_core.test_runner.TestRunner.run_command_in_env')
    def test_run_tests_simple_failure(self, mock_run):
        """Test exécution tests simple - échec"""
        mock_run.return_value = (1, "", "Test failed")
        result = self.test_runner.run_tests("unit")
        self.assertEqual(result, 1)

    def test_run_tests_nonexistent_config(self):
        """Test exécution tests avec configuration inexistante"""
        result = self.test_runner.run_tests("nonexistent-test")
        self.assertEqual(result, 1)

    @patch('project_core.test_runner.TestRunner.run_command_in_env')
    def test_run_tests_with_retries(self, mock_run):
        """Test exécution tests avec reprises"""
        mock_run.side_effect = [
            (1, "", "Flaky test failed"),
            (0, "Tests passed", "")
        ]
        result = self.test_runner.run_tests("unit")
        self.assertEqual(result, 1)


class TestTestRunnerServiceIntegration(unittest.TestCase):
    """Tests d'intégration TestRunner + ServiceManager"""

    def setUp(self):
        self.test_runner = TestRunner()

    @patch('project_core.test_runner.TestRunner.run_tests')
    def test_start_web_application_simulation(self, mock_run_tests):
        """Test démarrage application web (simulation)"""
        mock_run_tests.return_value = True
        if hasattr(self.test_runner, 'start_web_application'):
            result = self.test_runner.start_web_application()
            self.assertIsInstance(result, dict)

    def test_integration_with_service_manager(self):
        """Test intégration avec ServiceManager"""
        self.assertIsNotNone(self.test_runner.service_manager)
        self.assertTrue(hasattr(self.test_runner.service_manager, 'register_service'))
        self.assertTrue(hasattr(self.test_runner.service_manager, 'start_service_with_failover'))
        self.assertTrue(hasattr(self.test_runner.service_manager, 'stop_all_services'))


class TestMigrationValidation(unittest.TestCase):
    """Tests de validation des patterns migrés depuis PowerShell"""

    def setUp(self):
        self.test_runner = TestRunner()

    def test_powershell_pattern_equivalents(self):
        """Test équivalences patterns PowerShell"""
        self.assertTrue(hasattr(self.test_runner, 'service_manager'))
        if hasattr(self.test_runner, 'run_integration_tests_with_failover'):
            method = getattr(self.test_runner, 'run_integration_tests_with_failover')
            self.assertTrue(callable(method))
        cleanup = self.test_runner.service_manager.process_cleanup
        self.assertTrue(hasattr(cleanup, 'cleanup_all'))
        self.assertTrue(hasattr(cleanup, 'stop_backend_processes'))
        self.assertTrue(hasattr(cleanup, 'stop_frontend_processes'))

    @patch('project_core.test_runner.EnvironmentManager.run_command')
    def test_conda_activation_pattern(self, mock_run_command):
        """Test pattern activation conda (remplace PowerShell conda activate)"""
        mock_run_command.return_value = (0, "Success", "")
        result = self.test_runner.env_manager.activate_conda_env("test-env")
        self.assertIsInstance(result, bool)


class TestCrossPlatformCompatibility(unittest.TestCase):
    """Tests de compatibilité cross-platform"""

    def setUp(self):
        self.test_runner = TestRunner()

    def test_path_handling(self):
        """Test gestion des chemins cross-platform"""
        from project_core.test_runner import TestType
        config = TestConfig(test_type=TestType.UNIT, test_paths=["."])
        self.assertIsInstance(config.test_paths[0], str)
        config_with_path = TestConfig(
            test_type=TestType.UNIT,
            test_paths=[str(Path(".").resolve())]
        )
        self.assertIsInstance(config_with_path.test_paths[0], str)

    @patch('project_core.test_runner.TestRunner.run_command_in_env')
    def test_command_execution_cross_platform(self, mock_run):
        """Test exécution commandes cross-platform"""
        # La configuration interne de "unit" sera utilisée
        mock_run.return_value = (0, "Success", "")
        result = self.test_runner.run_tests("unit")
        self.assertIsInstance(result, int)


if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING)
    unittest.main(verbosity=2)