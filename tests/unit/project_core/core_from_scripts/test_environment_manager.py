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

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)