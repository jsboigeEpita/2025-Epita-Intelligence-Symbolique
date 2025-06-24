
# Authentic gpt-4o-mini imports (replacing mocks)
#!/usr/bin/env python3
"""
Tests unitaires pour le module environment_manager en mode CLI.
==============================================================

Ce fichier teste l'interface en ligne de commande (CLI) du module
`environment_manager.py`. Les tests simulent des appels en ligne
de commande pour vérifier que les arguments sont correctement parsés
et que les fonctions correspondantes (`setup_environment_variables`
et `run_command`) sont appelées comme attendu.

Auteur: Intelligence Symbolique EPITA
Date: 23/06/2025
"""

import unittest
import os
import sys
from unittest.mock import patch, MagicMock
from pathlib import Path

# Assurer que le module à tester est dans le path
# Le test est dans tests/unit/scripts/, le module dans project_core/core_from_scripts/
# On remonte de 4 niveaux pour être à la racine du projet
current_dir = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(current_dir))

from project_core.core_from_scripts import environment_manager

class TestEnvironmentManagerCLI(unittest.TestCase):
    """
    Classe de test pour le point d'entrée CLI (`main`) de `environment_manager`.
    """

    def setUp(self):
        """Sauvegarde l'environnement et `sys.argv` avant chaque test."""
        self.original_env = os.environ.copy()
        self.original_argv = sys.argv

    def tearDown(self):
        """Restaure l'environnement et `sys.argv` après chaque test."""
        os.environ.clear()
        os.environ.update(self.original_env)
        sys.argv = self.original_argv
    
    @patch('project_core.core_from_scripts.environment_manager.EnvironmentManager')
    def test_main_with_setup_vars(self, MockEnvironmentManager):
        """Vérifie que --setup-vars appelle setup_environment_variables."""
        sys.argv = ['__main__', '--setup-vars']
        
        mock_instance = MockEnvironmentManager.return_value
        
        # Le script appelle sys.exit(), il faut l'intercepter
        with self.assertRaises(SystemExit) as cm:
            environment_manager.main()
        
        self.assertEqual(cm.exception.code, 0) # Doit quitter avec succès
        mock_instance.setup_environment_variables.assert_called_once()
        mock_instance.run_command.assert_not_called()

    def test_setup_environment_variables_integration(self):
        """Test d'intégration. Vérifie que les variables sont bien positionnées."""
        manager = environment_manager.EnvironmentManager()
        
        # Nettoyer les variables potentiellement déjà présentes
        os.environ.pop('PYTHONPATH', None)
        os.environ.pop('KMP_DUPLICATE_LIB_OK', None)
        os.environ.pop('OPENAI_API_KEY', None)

        manager.setup_environment_variables()
        
        self.assertIn(str(manager.project_root), os.environ.get('PYTHONPATH'))
        self.assertEqual(os.environ.get('KMP_DUPLICATE_LIB_OK'), 'TRUE')
        self.assertIsNone(os.environ.get('OPENAI_API_KEY'))

    @patch('project_core.core_from_scripts.environment_manager.EnvironmentManager')
    def test_main_with_run_command(self, MockEnvironmentManager):
        """Vérifie que --run-command appelle run_command avec les bons arguments."""
        command_to_run = ['python', 'my_script.py', '--arg1']
        sys.argv = ['__main__', '--run-command'] + command_to_run
        
        mock_instance = MockEnvironmentManager.return_value
        mock_instance.run_command.return_value = 123 # Code de sortie arbitraire
        
        with self.assertRaises(SystemExit) as cm:
            environment_manager.main()
            
        self.assertEqual(cm.exception.code, 123)
        mock_instance.run_command.assert_called_once_with(command_to_run)
        mock_instance.setup_environment_variables.assert_not_called()

    @patch('project_core.core_from_scripts.environment_manager.EnvironmentManager')
    def test_main_with_setup_and_run_command(self, MockEnvironmentManager):
        """Vérifie que les deux flags peuvent être utilisés ensemble."""
        command_to_run = ['pytest', '-s']
        sys.argv = ['__main__', '--setup-vars', '--run-command'] + command_to_run

        mock_instance = MockEnvironmentManager.return_value
        mock_instance.run_command.return_value = 0
        
        with self.assertRaises(SystemExit) as cm:
            environment_manager.main()

        self.assertEqual(cm.exception.code, 0)
        
        # Vérifier que les deux méthodes sont appelées
        mock_instance.setup_environment_variables.assert_called_once()
        mock_instance.run_command.assert_called_once_with(command_to_run)

    @patch('project_core.core_from_scripts.environment_manager.argparse.ArgumentParser.print_help')
    def test_main_with_no_args(self, mock_print_help):
        """Vérifie que l'aide est affichée si aucun argument n'est fourni."""
        sys.argv = ['__main__']
        
        with self.assertRaises(SystemExit) as cm:
            environment_manager.main()
            
        self.assertEqual(cm.exception.code, 0)
        mock_print_help.assert_called_once()

    @patch('subprocess.run')
    def test_run_command_integration_success(self, mock_subprocess_run):
        """Test d'intégration de la méthode run_command en cas de succès."""
        manager = environment_manager.EnvironmentManager()
        
        # Configurer le mock pour simuler une exécution réussie
        mock_subprocess_run.return_value = MagicMock(returncode=0)
        
        command = ['ls', '-l']
        return_code = manager.run_command(command)
        
        self.assertEqual(return_code, 0)
        # La commande est jointe en une chaîne, et shell=True est utilisé.
        mock_subprocess_run.assert_called_once()
        args, kwargs = mock_subprocess_run.call_args
        self.assertEqual(args[0], ' '.join(command))
        self.assertTrue(kwargs.get('shell'))

    @patch('subprocess.run')
    def test_run_command_integration_failure(self, mock_subprocess_run):
        """Test d'intégration de la méthode run_command en cas d'échec."""
        manager = environment_manager.EnvironmentManager()
        
        # Configurer le mock pour simuler un échec
        mock_subprocess_run.return_value = MagicMock(returncode=1)
        
        command = ['command_qui_echoue']
        return_code = manager.run_command(command)
        
        self.assertEqual(return_code, 1)
        mock_subprocess_run.assert_called_once()
        args, kwargs = mock_subprocess_run.call_args
        self.assertEqual(args[0], ' '.join(command))
        self.assertTrue(kwargs.get('shell'))

    @patch('subprocess.run', side_effect=FileNotFoundError("Commande non trouvée"))
    def test_run_command_file_not_found(self, mock_subprocess_run):
        """Test la gestion de l'erreur FileNotFoundError."""
        manager = environment_manager.EnvironmentManager()
        
        command = ['commande_inexistante']
        return_code = manager.run_command(command)
        
        self.assertEqual(return_code, 1)
        mock_subprocess_run.assert_called_once()
        args, kwargs = mock_subprocess_run.call_args
        self.assertEqual(args[0], ' '.join(command))
        self.assertTrue(kwargs.get('shell'))

if __name__ == '__main__':
    unittest.main(verbosity=2)