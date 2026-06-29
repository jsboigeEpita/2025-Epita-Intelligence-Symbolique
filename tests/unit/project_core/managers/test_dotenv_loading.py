"""Tests for deterministic multi-.env loading in EnvironmentManager (#1295).

Verifies:
  - root .env always wins (override=True) even when OPENAI_API_KEY is pre-set in os.environ
  - divergence WARNING is emitted when a secondary .env carries a different key
  - no WARNING when secondary .env has the same key as root
"""
import logging
import os
from pathlib import Path
from unittest.mock import patch

import pytest


def _write_env(path: Path, key: str, value: str) -> None:
    path.write_text(f'{key}="{value}"\n', encoding="utf-8")


# ---------------------------------------------------------------------------
# Module alias for patching
# ---------------------------------------------------------------------------
import project_core.managers.environment_manager as _em_mod
from project_core.managers.environment_manager import EnvironmentManager


class TestDotenvLoadingDeterministic:
    """Root .env override behaviour."""

    def test_root_env_overrides_pre_existing_env_var(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Root .env (override=True) must replace a stale value set by a prior sub-.env."""
        root_env = tmp_path / ".env"
        _write_env(root_env, "OPENAI_API_KEY", "sk-root-VALID")

        # Simulate a dead key already present in os.environ (first-import-wins scenario)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-dead-STALE")

        with patch.object(_em_mod, "_find_repo_root", return_value=tmp_path):
            EnvironmentManager()

        assert os.environ.get("OPENAI_API_KEY") == "sk-root-VALID", (
            "Root .env should have overridden the stale value via override=True"
        )

    def test_dotenv_path_points_to_root_env(self, tmp_path: Path) -> None:
        """dotenv_path attribute must reflect the root .env location."""
        root_env = tmp_path / ".env"
        root_env.write_text("DUMMY=1\n", encoding="utf-8")

        with patch.object(_em_mod, "_find_repo_root", return_value=tmp_path):
            mgr = EnvironmentManager()

        assert mgr.dotenv_path == str(root_env)
        assert mgr.dotenv_loaded is True


class TestDotenvDivergenceWarning:
    """Secondary .env divergence detection."""

    def test_warning_emitted_on_key_divergence(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """WARNING must be logged when secondary .env carries a different OPENAI_API_KEY."""
        root_env = tmp_path / ".env"
        _write_env(root_env, "OPENAI_API_KEY", "sk-root-AAAA")

        secondary_dir = tmp_path / "argumentation_analysis"
        secondary_dir.mkdir()
        _write_env(secondary_dir / ".env", "OPENAI_API_KEY", "sk-dead-ZZZZ")

        with patch.object(_em_mod, "_find_repo_root", return_value=tmp_path), \
             patch.object(_em_mod, "_SECONDARY_ENV_RELPATHS", ["argumentation_analysis/.env"]):
            with caplog.at_level(
                logging.WARNING, logger="project_core.managers.environment_manager"
            ):
                EnvironmentManager()

        assert any(
            "divergence" in record.message
            for record in caplog.records
        ), "Expected a WARNING containing 'divergence' for mismatched keys"

    def test_no_warning_when_keys_identical(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """No WARNING should be emitted when secondary .env key matches root."""
        root_env = tmp_path / ".env"
        _write_env(root_env, "OPENAI_API_KEY", "sk-same-BBBB")

        secondary_dir = tmp_path / "argumentation_analysis"
        secondary_dir.mkdir()
        _write_env(secondary_dir / ".env", "OPENAI_API_KEY", "sk-same-BBBB")

        with patch.object(_em_mod, "_find_repo_root", return_value=tmp_path), \
             patch.object(_em_mod, "_SECONDARY_ENV_RELPATHS", ["argumentation_analysis/.env"]):
            with caplog.at_level(
                logging.WARNING, logger="project_core.managers.environment_manager"
            ):
                EnvironmentManager()

        assert not any(
            "divergence" in record.message
            for record in caplog.records
        ), "No WARNING should be emitted when secondary key matches root"

    def test_warning_masks_key_values(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """WARNING log must not contain the full key — only masked prefix/suffix."""
        root_env = tmp_path / ".env"
        _write_env(root_env, "OPENAI_API_KEY", "sk-proj-LONGROOT12345")

        secondary_dir = tmp_path / "argumentation_analysis"
        secondary_dir.mkdir()
        _write_env(secondary_dir / ".env", "OPENAI_API_KEY", "sk-proj-LONGSECONDARY9")

        with patch.object(_em_mod, "_find_repo_root", return_value=tmp_path), \
             patch.object(_em_mod, "_SECONDARY_ENV_RELPATHS", ["argumentation_analysis/.env"]):
            with caplog.at_level(
                logging.WARNING, logger="project_core.managers.environment_manager"
            ):
                EnvironmentManager()

        for record in caplog.records:
            assert "LONGROOT12345" not in record.message, "Full root key must not appear in log"
            assert "LONGSECONDARY9" not in record.message, "Full secondary key must not appear in log"

    def test_no_warning_when_secondary_absent(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """No WARNING when secondary .env does not exist."""
        root_env = tmp_path / ".env"
        _write_env(root_env, "OPENAI_API_KEY", "sk-root-CCCC")

        with patch.object(_em_mod, "_find_repo_root", return_value=tmp_path), \
             patch.object(_em_mod, "_SECONDARY_ENV_RELPATHS", ["argumentation_analysis/.env"]):
            with caplog.at_level(
                logging.WARNING, logger="project_core.managers.environment_manager"
            ):
                EnvironmentManager()

        assert not any(
            "divergence" in record.message
            for record in caplog.records
        ), "No WARNING when there is no secondary .env to diverge from"
