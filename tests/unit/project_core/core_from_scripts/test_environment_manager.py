"""
Tests unitaires pour le EnvironmentManager.
"""

import unittest
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock

from project_core.core_from_scripts.environment_manager import EnvironmentManager

# Désactiver le logging pour les tests
logging.disable(logging.CRITICAL)

class TestEnvironmentManager(unittest.TestCase):
    """Suite de tests pour le EnvironmentManager."""

    def setUp(self):
        """Configuration initiale pour chaque test."""
        self.test_dir = Path("test_temp_project")
        self.test_dir.mkdir(exist_ok=True)

        # Créer une structure de projet factice
        (self.test_dir / "config" / "environments").mkdir(parents=True, exist_ok=True)
        (self.test_dir / "config" / "templates").mkdir(parents=True, exist_ok=True)

        self.manager = EnvironmentManager(project_root=self.test_dir)

        # Créer des fichiers factices
        self.template_file = self.manager.template_path
        with open(self.template_file, "w") as f:
            f.write("KEY1=value1\n")
            f.write("KEY2=value2\n")

        self.dev_env_file = self.manager.env_files_dir / "dev.env"
        with open(self.dev_env_file, "w") as f:
            f.write("KEY1=dev1\n")
            f.write("KEY2=dev2\n")
            
        self.prod_env_file = self.manager.env_files_dir / "prod.env"
        with open(self.prod_env_file, "w") as f:
            f.write("KEY1=prod1\n")
            
    def tearDown(self):
        """Nettoyage après chaque test."""
        # Utiliser shutil.rmtree pour supprimer le répertoire et son contenu
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_switch_environment_success(self):
        """Teste le basculement réussi d'un environnement."""
        result = self.manager.switch_environment("dev")
        self.assertTrue(result)
        self.assertTrue(self.manager.target_env_file.exists())
        with open(self.manager.target_env_file, "r") as f:
            content = f.read()
            self.assertIn("KEY1=dev1", content)

    def test_switch_environment_source_not_found(self):
        """Teste le basculement avec un environnement source inexistant."""
        result = self.manager.switch_environment("non_existent")
        self.assertFalse(result)

    def test_create_environment_success(self):
        """Teste la création réussie d'un nouvel environnement."""
        result = self.manager.create_environment("staging")
        self.assertTrue(result)
        new_env_file = self.manager.env_files_dir / "staging.env"
        self.assertTrue(new_env_file.exists())
        with open(new_env_file, "r") as f:
            self.assertEqual(f.read(), "KEY1=value1\nKEY2=value2\n")

    def test_create_environment_already_exists(self):
        """Teste la création d'un environnement qui existe déjà."""
        result = self.manager.create_environment("dev")
        self.assertFalse(result)

    def test_validate_environment_success(self):
        """Teste la validation réussie d'un environnement."""
        result = self.manager.validate_environment("dev")
        self.assertTrue(result)

    def test_validate_environment_missing_keys(self):
        """Teste la validation d'un environnement avec des clés manquantes."""
        result = self.manager.validate_environment("prod")
        self.assertFalse(result)

    def test_validate_environment_file_not_found(self):
        """Teste la validation d'un fichier d'environnement inexistant."""
        result = self.manager.validate_environment("non_existent")
        self.assertFalse(result)

    @patch('project_core.core_from_scripts.environment_manager.run_shell_command')
    def test_fix_dependencies(self, mock_run_shell_command):
        """Teste la réparation ciblée de dépendances."""
        # Configure le mock pour simuler une exécution réussie
        mock_run_shell_command.return_value = (0, "Success", "")

        # Les paquets à réparer
        packages_to_fix = ["numpy", "pandas"]
        
        # Appelle la méthode à tester
        result = self.manager.fix_dependencies(packages=packages_to_fix)
        
        # Vérifie que le résultat est True
        self.assertTrue(result)
        
        # Vérifie que run_shell_command a été appelé une fois
        mock_run_shell_command.assert_called_once()
        
        # Récupère l'argument avec lequel la fonction mockée a été appelée
        called_command = mock_run_shell_command.call_args[0][0]
        
        # Vérifie que la commande contient les bons éléments
        self.assertIn("pip", called_command)
        self.assertIn("install", called_command)
        self.assertIn("--force-reinstall", called_command)
        self.assertIn("--no-cache-dir", called_command)
        self.assertIn("numpy", called_command)
        self.assertIn("pandas", called_command)

    @patch('project_core.core_from_scripts.environment_manager.run_shell_command')
    def test_fix_dependencies_from_requirements_file(self, mock_run_shell_command):
        """Teste la réparation depuis un fichier requirements.txt."""
        mock_run_shell_command.return_value = (0, "Success", "")
        
        requirements_path = self.test_dir / "requirements.txt"
        with open(requirements_path, "w") as f:
            f.write("requests\n")
            f.write("pytest\n")
            
        result = self.manager.fix_dependencies(requirements_file=str(requirements_path))
        
        self.assertTrue(result)
        mock_run_shell_command.assert_called_once()
        called_command = mock_run_shell_command.call_args[0][0]
        
        self.assertIn("pip", called_command)
        self.assertIn("install", called_command)
        self.assertIn("-r", called_command)
        self.assertIn(str(requirements_path), called_command)

    def test_fix_dependencies_mutually_exclusive_args(self):
        """Teste que les arguments packages et requirements_file sont mutuellement exclusifs."""
        with self.assertRaises(ValueError):
            self.manager.fix_dependencies(packages=["numpy"], requirements_file="reqs.txt")

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)