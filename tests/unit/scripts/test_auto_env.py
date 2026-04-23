# -*- coding: utf-8 -*-
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

import pytest
import os
from unittest.mock import patch

from argumentation_analysis.core.environment import ensure_env


# Fixture pour isoler les tests de la pollution globale
@pytest.fixture(autouse=True)
def _isolate_from_global_pollution():
    """Isole les tests de toute pollution d'environnement globale."""
    # Sauvegarder l'état original
    original_e2e = os.environ.get("E2E_TESTING_MODE")
    original_conda = os.environ.get("CONDA_DEFAULT_ENV")

    yield

    # Restaurer l'état original
    if original_e2e is None:
        os.environ.pop("E2E_TESTING_MODE", None)
    else:
        os.environ["E2E_TESTING_MODE"] = original_e2e

    if original_conda is None:
        os.environ.pop("CONDA_DEFAULT_ENV", None)
    else:
        os.environ["CONDA_DEFAULT_ENV"] = original_conda


def _call_ensure_env(env_vars, **kwargs):
    """Call ensure_env with fully controlled environment.

    Uses clear=True to fully isolate from global state (conftest.py sets
    E2E_TESTING_MODE=1 globally, which bypasses conda checks).
    """
    with patch.dict(os.environ, env_vars, clear=True):
        return ensure_env(load_dotenv=False, **kwargs)


class TestEnsureEnvAsGuard:
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
        assert result is True

    def test_ensure_env_incorrect_environment_raises_error(self):
        """
        Vérifie que ensure_env() lève une RuntimeError si 'CONDA_DEFAULT_ENV'
        est incorrect.
        """
        with pytest.raises(RuntimeError) as cm:
            _call_ensure_env(
                {"CONDA_DEFAULT_ENV": "wrong-env", "IS_PYTEST_RUNNING": "true"},
                env_name="projet-is",
                silent=False,
            )

        exception_message = str(cm.value)
        assert "ERREUR CRITIQUE" in exception_message
        assert "MAUVAIS ENVIRONNEMENT CONDA ACTIF" in exception_message
        assert "Environnement attendu   : 'projet-is'" in exception_message
        assert (
            "Environnement détecté (CONDA_DEFAULT_ENV) : 'wrong-env'"
            in exception_message
        )

    def test_ensure_env_base_environment_raises_error(self):
        """
        Vérifie que ensure_env() lève une RuntimeError si 'CONDA_DEFAULT_ENV'
        est défini sur 'base'.
        """
        with pytest.raises(RuntimeError) as cm:
            _call_ensure_env(
                {"CONDA_DEFAULT_ENV": "base", "IS_PYTEST_RUNNING": "true"},
                env_name="projet-is",
                silent=False,
            )

        exception_message = str(cm.value)
        assert "ERREUR CRITIQUE" in exception_message
        assert "MAUVAIS ENVIRONNEMENT CONDA ACTIF" in exception_message
        assert "Environnement attendu   : 'projet-is'" in exception_message
        assert (
            "Environnement détecté (CONDA_DEFAULT_ENV) : 'base'" in exception_message
        )

    def test_ensure_env_silent_mode(self):
        """Vérifie le mode silencieux et non silencieux."""
        env = {"CONDA_DEFAULT_ENV": "projet-is", "IS_PYTEST_RUNNING": "true"}
        # En mode non silencieux, on s'attend à un print
        with patch.dict(os.environ, env, clear=True):
            with patch("builtins.print") as mock_print:
                ensure_env(env_name="projet-is", silent=False, load_dotenv=False)
                found_call = any(
                    "[auto_env] OK: Environnement Conda 'projet-is' correctement activé."
                    in str(call)
                    for call in mock_print.call_args_list
                )
                assert found_call, "Le message de succès n'a pas été affiché en mode non-silencieux."

        # En mode silencieux, on ne s'attend pas à un print
        with patch.dict(os.environ, env, clear=True):
            with patch("builtins.print") as mock_print:
                ensure_env(env_name="projet-is", silent=True, load_dotenv=False)
                mock_print.assert_not_called()
