"""
Tests unitaires pour argumentation_analysis/core/environment.py.

Couvre:
- ensure_env: dotenv loading, conda env verification, error handling
- get_one_liner: legacy one-liner
- get_simple_import: recommended import pattern

Issue: #36 (test coverage)
"""

import pytest
import os
import sys
from unittest.mock import patch, MagicMock


class TestEnsureEnv:
    """Tests for the ensure_env() function.

    Note: conftest.py sets E2E_TESTING_MODE=1 globally, which makes ensure_env()
    bypass conda checks. Tests that verify conda checking must remove this var.
    """

    def _call_ensure_env(self, env_vars, **kwargs):
        """Call ensure_env with fully controlled environment variables.

        Removes E2E_TESTING_MODE to test actual conda checking logic.
        """
        # Build clean env: remove E2E bypass unless caller explicitly sets it
        patched = dict(env_vars)
        if "E2E_TESTING_MODE" not in patched:
            patched["E2E_TESTING_MODE"] = ""  # disable the bypass

        with patch.dict(os.environ, patched, clear=False):
            # Also ensure E2E_TESTING_MODE is truly cleared
            if not patched.get("E2E_TESTING_MODE"):
                os.environ.pop("E2E_TESTING_MODE", None)
            from argumentation_analysis.core.environment import ensure_env
            return ensure_env(**kwargs)

    # --- E2E testing mode bypass ---

    def test_e2e_mode_skips_conda_check(self):
        """When E2E_TESTING_MODE=1, ensure_env returns True without checking conda."""
        from argumentation_analysis.core.environment import ensure_env
        with patch.dict(os.environ, {"E2E_TESTING_MODE": "1"}):
            result = ensure_env(silent=True, load_dotenv=False)
            assert result is True

    def test_e2e_mode_skips_even_wrong_env(self):
        """E2E mode bypasses conda check even with wrong env."""
        from argumentation_analysis.core.environment import ensure_env
        with patch.dict(os.environ, {"E2E_TESTING_MODE": "1", "CONDA_DEFAULT_ENV": "wrong"}):
            result = ensure_env(env_name="projet-is", silent=True, load_dotenv=False)
            assert result is True

    # --- Correct conda env ---

    def test_correct_conda_env(self):
        """When CONDA_DEFAULT_ENV matches expected, returns True."""
        result = self._call_ensure_env(
            {"CONDA_DEFAULT_ENV": "projet-is"},
            env_name="projet-is", silent=True, load_dotenv=False
        )
        assert result is True

    def test_correct_conda_env_roo_new(self):
        """When CONDA_DEFAULT_ENV matches explicitly-given env name, returns True."""
        result = self._call_ensure_env(
            {"CONDA_DEFAULT_ENV": "projet-is-roo-new"},
            env_name="projet-is-roo-new", silent=True, load_dotenv=False
        )
        assert result is True

    # --- CI/CD fallback (projet-is-roo -> projet-is accepted) ---

    def test_cicd_fallback_projet_is_roo(self):
        """When expected is 'projet-is-roo' and active is 'projet-is', it's accepted."""
        result = self._call_ensure_env(
            {"CONDA_DEFAULT_ENV": "projet-is"},
            env_name="projet-is-roo", silent=True, load_dotenv=False
        )
        assert result is True

    # --- Wrong conda env ---

    def test_wrong_conda_env_raises(self):
        """When CONDA_DEFAULT_ENV doesn't match, raises RuntimeError."""
        with pytest.raises(RuntimeError, match="MAUVAIS ENVIRONNEMENT CONDA"):
            self._call_ensure_env(
                {"CONDA_DEFAULT_ENV": "wrong-env"},
                env_name="projet-is", silent=True, load_dotenv=False
            )

    def test_missing_conda_env_raises(self):
        """When CONDA_DEFAULT_ENV is not set, raises RuntimeError."""
        with pytest.raises(RuntimeError, match="MAUVAIS ENVIRONNEMENT CONDA"):
            # Use a clean env without CONDA_DEFAULT_ENV
            env_copy = {k: v for k, v in os.environ.items()
                        if k not in ("CONDA_DEFAULT_ENV", "E2E_TESTING_MODE")}
            with patch.dict(os.environ, env_copy, clear=True):
                from argumentation_analysis.core.environment import ensure_env
                ensure_env(env_name="projet-is", silent=True, load_dotenv=False)

    # --- Error message content ---

    def test_error_message_includes_expected_env(self):
        with pytest.raises(RuntimeError) as exc_info:
            self._call_ensure_env(
                {"CONDA_DEFAULT_ENV": "wrong"},
                env_name="my-expected-env", silent=True, load_dotenv=False
            )
        assert "my-expected-env" in str(exc_info.value)
        assert "wrong" in str(exc_info.value)

    def test_error_message_includes_solution(self):
        with pytest.raises(RuntimeError) as exc_info:
            self._call_ensure_env(
                {"CONDA_DEFAULT_ENV": "bad"},
                env_name="good", silent=True, load_dotenv=False
            )
        assert "conda activate" in str(exc_info.value)

    # --- dotenv loading ---

    def test_load_dotenv_false_skips(self):
        """When load_dotenv=False, EnvironmentManager is not called."""
        result = self._call_ensure_env(
            {"CONDA_DEFAULT_ENV": "projet-is"},
            env_name="projet-is", silent=True, load_dotenv=False
        )
        assert result is True

    def test_load_dotenv_handles_import_error(self):
        """When EnvironmentManager can't be imported, ensure_env continues gracefully."""
        with patch.dict(sys.modules, {"project_core.managers.environment_manager": None}):
            result = self._call_ensure_env(
                {"CONDA_DEFAULT_ENV": "projet-is"},
                env_name="projet-is", silent=True, load_dotenv=True
            )
            assert result is True


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_one_liner_returns_string(self):
        from argumentation_analysis.core.environment import get_one_liner
        result = get_one_liner()
        assert isinstance(result, str)
        assert len(result) > 50
        assert "ensure_env" in result

    def test_get_simple_import_returns_string(self):
        from argumentation_analysis.core.environment import get_simple_import
        result = get_simple_import()
        assert isinstance(result, str)
        assert "argumentation_analysis.core.environment" in result
        assert "import" in result
