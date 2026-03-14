#!/usr/bin/env python3
"""
Tests unitaires pour le module `environment` et sa fonction coupe-circuit `ensure_env`.
=====================================================================================

Ce fichier teste la nouvelle logique de `ensure_env`, qui ne doit plus activer
l'environnement mais seulement VÉRIFIER qu'il est correct et lever une exception
dans le cas contraire.

Note: conftest.py sets E2E_TESTING_MODE=1 globally, which makes ensure_env()
bypass conda checks. All tests must explicitly remove this var before calling
ensure_env() to test actual logic.

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


def _call_ensure_env(env_vars, **kwargs):
    """Call ensure_env with fully controlled environment.

    Removes E2E_TESTING_MODE and uses context manager pattern (not decorator)
    to ensure isolation even in full test suite where conftest.py sets
    E2E_TESTING_MODE=1 globally.
    """
    patched = dict(env_vars)
    if "E2E_TESTING_MODE" not in patched:
        patched["E2E_TESTING_MODE"] = ""

    with patch.dict(os.environ, patched, clear=False):
        # Explicitly remove E2E bypass inside the patched context
        os.environ.pop("E2E_TESTING_MODE", None)
        return ensure_env(load_dotenv=False, **kwargs)


class TestEnsureEnvAsGuard(unittest.TestCase):
    """
    Teste la fonction `ensure_env` en tant que garde-fou de l'environnement.
    La nouvelle version se base sur la variable d'environnement `CONDA_DEFAULT_ENV`.
    """

    def test_ensure_env_correct_environment(self):
        """
        Vérifie que ensure_env() réussit si 'CONDA_DEFAULT_ENV' correspond à
        l'environnement attendu.
        """
        result = _call_ensure_env(
            {"CONDA_DEFAULT_ENV": "projet-is", "IS_PYTEST_RUNNING": "true"},
            env_name="projet-is",
            silent=True,
        )
        self.assertTrue(result)

    def test_ensure_env_incorrect_environment_raises_error(self):
        """
        Vérifie que ensure_env() lève une RuntimeError si 'CONDA_DEFAULT_ENV'
        est incorrect.
        """
        with self.assertRaises(RuntimeError) as cm:
            _call_ensure_env(
                {"CONDA_DEFAULT_ENV": "wrong-env", "IS_PYTEST_RUNNING": "true"},
                env_name="projet-is",
                silent=False,
            )

        exception_message = str(cm.exception)
        self.assertIn("ERREUR CRITIQUE", exception_message)
        self.assertIn("MAUVAIS ENVIRONNEMENT CONDA ACTIF", exception_message)
        self.assertIn("Environnement attendu   : 'projet-is'", exception_message)
        self.assertIn(
            "Environnement détecté (CONDA_DEFAULT_ENV) : 'wrong-env'",
            exception_message,
        )

    def test_ensure_env_base_environment_raises_error(self):
        """
        Vérifie que ensure_env() lève une RuntimeError si 'CONDA_DEFAULT_ENV'
        est défini sur 'base'.
        """
        with self.assertRaises(RuntimeError) as cm:
            _call_ensure_env(
                {"CONDA_DEFAULT_ENV": "base", "IS_PYTEST_RUNNING": "true"},
                env_name="projet-is",
                silent=False,
            )

        exception_message = str(cm.exception)
        self.assertIn("ERREUR CRITIQUE", exception_message)
        self.assertIn("MAUVAIS ENVIRONNEMENT CONDA ACTIF", exception_message)
        self.assertIn("Environnement attendu   : 'projet-is'", exception_message)
        self.assertIn(
            "Environnement détecté (CONDA_DEFAULT_ENV) : 'base'", exception_message
        )

    def test_ensure_env_silent_mode(self):
        """Vérifie le mode silencieux et non silencieux."""
        # En mode non silencieux, on s'attend à un print
        env = {"CONDA_DEFAULT_ENV": "projet-is", "IS_PYTEST_RUNNING": "true"}
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("E2E_TESTING_MODE", None)
            with patch("builtins.print") as mock_print:
                ensure_env(env_name="projet-is", silent=False, load_dotenv=False)
                found_call = any(
                    "[auto_env] OK: Environnement Conda 'projet-is' correctement activé."
                    in str(call)
                    for call in mock_print.call_args_list
                )
                self.assertTrue(
                    found_call,
                    "Le message de succès n'a pas été affiché en mode non-silencieux.",
                )

        # En mode silencieux, on ne s'attend pas à un print
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("E2E_TESTING_MODE", None)
            with patch("builtins.print") as mock_print:
                ensure_env(env_name="projet-is", silent=True, load_dotenv=False)
                mock_print.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
