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
from unittest.mock import patch, MagicMock

# Assurer que le module à tester est dans le path
current_dir = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(current_dir))

# Importer la fonction à tester
from argumentation_analysis.core.environment import ensure_env

class TestEnsureEnvAsGuard(unittest.TestCase):
    """
    Teste la fonction `ensure_env` en tant que garde-fou de l'environnement.
    La nouvelle version se base sur la variable d'environnement `CONDA_DEFAULT_ENV`.
    """

    @patch.dict('os.environ', {'CONDA_DEFAULT_ENV': 'projet-is', 'IS_PYTEST_RUNNING': 'true'}, clear=True)
    def test_ensure_env_correct_environment(self):
        """
        Vérifie que ensure_env() réussit si 'CONDA_DEFAULT_ENV' correspond à
        l'environnement attendu.
        """
        result = ensure_env(env_name="projet-is", silent=True)
        self.assertTrue(result)

    @patch.dict('os.environ', {'CONDA_DEFAULT_ENV': 'wrong-env', 'IS_PYTEST_RUNNING': 'true'}, clear=True)
    def test_ensure_env_incorrect_environment_raises_error(self):
        """
        Vérifie que ensure_env() lève une RuntimeError si 'CONDA_DEFAULT_ENV'
        est incorrect.
        """
        with self.assertRaises(RuntimeError) as cm:
            ensure_env(env_name="projet-is", silent=False)  # Mettre silent=False pour couvrir le message d'erreur
        
        exception_message = str(cm.exception)
        self.assertIn("ERREUR CRITIQUE", exception_message)
        self.assertIn("MAUVAIS ENVIRONNEMENT CONDA ACTIF", exception_message)
        self.assertIn("Environnement attendu   : 'projet-is'", exception_message)
        self.assertIn("Environnement détecté (CONDA_DEFAULT_ENV) : 'wrong-env'", exception_message)

    @patch.dict('os.environ', {'CONDA_DEFAULT_ENV': 'base', 'IS_PYTEST_RUNNING': 'true'}, clear=True)
    def test_ensure_env_base_environment_raises_error(self):
        """
        Vérifie que ensure_env() lève une RuntimeError si 'CONDA_DEFAULT_ENV'
        est défini sur 'base'.
        """
        with self.assertRaises(RuntimeError) as cm:
            ensure_env(env_name="projet-is", silent=False)
            
        exception_message = str(cm.exception)
        self.assertIn("ERREUR CRITIQUE", exception_message)
        self.assertIn("MAUVAIS ENVIRONNEMENT CONDA ACTIF", exception_message)
        self.assertIn("Environnement attendu   : 'projet-is'", exception_message)
        self.assertIn("Environnement détecté (CONDA_DEFAULT_ENV) : 'base'", exception_message)

    @patch.dict('os.environ', {'CONDA_DEFAULT_ENV': 'projet-is', 'IS_PYTEST_RUNNING': 'true'}, clear=True)
    def test_ensure_env_silent_mode(self):
        """Vérifie le mode silencieux et non silencieux."""
        # En mode non silencieux, on s'attend à un print
        with patch('builtins.print') as mock_print:
            ensure_env(env_name="projet-is", silent=False)
            # Vérifier que l'un des appels contient le bon message.
            # La sortie exacte peut être wrapped, donc on vérifie la sous-chaîne.
            found_call = any("[auto_env] OK: L'environnement 'projet-is' est correctement activé." in call.args[0] for call in mock_print.call_args_list)
            self.assertTrue(found_call, "Le message de succès n'a pas été affiché en mode non-silencieux.")

        # En mode silencieux, on ne s'attend pas à un print
        with patch('builtins.print') as mock_print:
            ensure_env(env_name="projet-is", silent=True)
            mock_print.assert_not_called()

if __name__ == '__main__':
    unittest.main(verbosity=2)