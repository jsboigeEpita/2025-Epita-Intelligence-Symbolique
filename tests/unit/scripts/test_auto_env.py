#!/usr/bin/env python3
"""
Tests unitaires pour le module `environment` et sa fonction coupe-circuit `ensure_env`.
=====================================================================================

Ce fichier teste la nouvelle logique de `ensure_env`, qui ne doit plus activer
l'environnement mais seulement VÉRIFIER qu'il est correct et lever une exception
dans le cas contraire.

Auteur: Intelligence Symbolique EPITA
Date: 23/06/2025
"""

import unittest
import os
import sys
from pathlib import Path
from unittest.mock import patch

# Assurer que le module à tester est dans le path
current_dir = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(current_dir))

# Importer la fonction à tester
from argumentation_analysis.core.environment import ensure_env

class TestEnsureEnvAsGuard(unittest.TestCase):
    """
    Teste la fonction `ensure_env` en tant que garde-fou de l'environnement.
    """

    def setUp(self):
        """Sauvegarde l'environnement."""
        self.original_env = os.environ.copy()
        # On s'assure que la variable de test pytest est définie
        # pour empêcher l'auto-exécution de `ensure_env` à l'import
        os.environ["IS_PYTEST_RUNNING"] = "true"

    def tearDown(self):
        """Restaure l'environnement."""
        os.environ.clear()
        os.environ.update(self.original_env)

    @patch('sys.prefix', 'C:\\Users\\Test\\miniconda3\\envs\\projet-is')
    @patch('sys.base_prefix', 'C:\\Users\\Test\\miniconda3')
    def test_ensure_env_correct_environment(self):
        """
        Vérifie que ensure_env() réussit si le `sys.prefix` correspond à
        l'environnement attendu ('projet-is').
        """
        result = ensure_env(env_name="projet-is", silent=True)
        self.assertTrue(result)

    @patch('sys.prefix', 'C:\\Users\\Test\\miniconda3\\envs\\wrong-env')
    @patch('sys.base_prefix', 'C:\\Users\\Test\\miniconda3')
    def test_ensure_env_incorrect_environment_raises_error(self):
        """
        Vérifie que ensure_env() lève une RuntimeError si `sys.prefix`
        ne correspond pas à l'environnement attendu.
        """
        with self.assertRaises(RuntimeError) as cm:
            ensure_env(env_name="projet-is", silent=True)
        
        exception_message = str(cm.exception)
        self.assertIn("ERREUR CRITIQUE", exception_message)
        self.assertIn("L'INTERPRÉTEUR PYTHON EST INCORRECT", exception_message)
        self.assertIn("Environnement attendu : 'projet-is'", exception_message)
        self.assertIn("Environnement détecté : 'wrong-env'", exception_message)

    @patch('sys.prefix', 'C:\\Users\\Test\\miniconda3')
    @patch('sys.base_prefix', 'C:\\Users\\Test\\miniconda3')
    def test_ensure_env_base_environment_raises_error(self):
        """
        Vérifie que ensure_env() lève une RuntimeError si l'environnement
        détecté est 'base'.
        """
        with self.assertRaises(RuntimeError) as cm:
            ensure_env(env_name="projet-is", silent=True)
            
        exception_message = str(cm.exception)
        self.assertIn("ERREUR CRITIQUE", exception_message)
        self.assertIn("L'INTERPRÉTEUR PYTHON EST INCORRECT", exception_message)
        self.assertIn("Environnement attendu : 'projet-is'", exception_message)
        self.assertIn("Environnement détecté : 'miniconda3'", exception_message)

    @patch('sys.prefix', 'C:\\Users\\Test\\miniconda3\\envs\\projet-is')
    @patch('sys.base_prefix', 'C:\\Users\\Test\\miniconda3')
    def test_ensure_env_silent_mode(self, ):
        """Vérifie le mode silencieux et non silencieux."""
        # En mode non silencieux, on s'attend à un print
        with patch('builtins.print') as mock_print:
            ensure_env(env_name="projet-is", silent=False)
            mock_print.assert_called_with("[auto_env] OK: L'environnement 'projet-is' est correctement activé.")

        # En mode silencieux, on ne s'attend pas à un print
        with patch('builtins.print') as mock_print:
            ensure_env(env_name="projet-is", silent=True)
            mock_print.assert_not_called()

if __name__ == '__main__':
    unittest.main(verbosity=2)