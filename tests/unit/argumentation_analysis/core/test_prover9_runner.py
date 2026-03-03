# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.core.prover9_runner
Covers run_prover9 with subprocess mocking.
"""

import pytest
import subprocess
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, ANY

from argumentation_analysis.core.prover9_runner import run_prover9, PROVER9_EXECUTABLE


# ============================================================
# run_prover9
# ============================================================

class TestRunProver9:
    """Tests for the run_prover9 function."""

    def test_executable_not_found(self):
        with patch.object(Path, "is_file", return_value=False):
            with pytest.raises(FileNotFoundError, match="Prover9 executable not found"):
                run_prover9("some input")

    @patch("argumentation_analysis.core.prover9_runner.subprocess.run")
    @patch("argumentation_analysis.core.prover9_runner.PROVER9_EXECUTABLE")
    def test_successful_run(self, mock_executable, mock_run):
        mock_executable.is_file.return_value = True
        mock_run.return_value = MagicMock(stdout="PROOF FOUND", returncode=0)

        result = run_prover9("formulas(assumptions).\nall x (P(x)).\nend_of_list.")
        assert result == "PROOF FOUND"
        mock_run.assert_called_once()

    @patch("argumentation_analysis.core.prover9_runner.subprocess.run")
    @patch("argumentation_analysis.core.prover9_runner.PROVER9_EXECUTABLE")
    def test_called_with_shell_true(self, mock_executable, mock_run):
        mock_executable.is_file.return_value = True
        mock_run.return_value = MagicMock(stdout="ok", returncode=0)

        run_prover9("test input")
        call_kwargs = mock_run.call_args
        assert call_kwargs.kwargs.get("shell") is True

    @patch("argumentation_analysis.core.prover9_runner.subprocess.run")
    @patch("argumentation_analysis.core.prover9_runner.PROVER9_EXECUTABLE")
    def test_called_with_check_true(self, mock_executable, mock_run):
        mock_executable.is_file.return_value = True
        mock_run.return_value = MagicMock(stdout="ok", returncode=0)

        run_prover9("test input")
        call_kwargs = mock_run.call_args
        assert call_kwargs.kwargs.get("check") is True

    @patch("argumentation_analysis.core.prover9_runner.subprocess.run")
    @patch("argumentation_analysis.core.prover9_runner.PROVER9_EXECUTABLE")
    def test_called_process_error(self, mock_executable, mock_run):
        mock_executable.is_file.return_value = True
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=2,
            cmd="prover9",
            output="partial output",
            stderr="error details",
        )

        with pytest.raises(subprocess.CalledProcessError) as exc_info:
            run_prover9("bad input")
        assert exc_info.value.returncode == 2

    @patch("argumentation_analysis.core.prover9_runner.subprocess.run")
    @patch("argumentation_analysis.core.prover9_runner.PROVER9_EXECUTABLE")
    @patch("argumentation_analysis.core.prover9_runner.os.path.exists", return_value=True)
    @patch("argumentation_analysis.core.prover9_runner.os.remove")
    def test_temp_file_cleaned_up_on_success(self, mock_remove, mock_exists, mock_executable, mock_run):
        mock_executable.is_file.return_value = True
        mock_run.return_value = MagicMock(stdout="ok", returncode=0)

        run_prover9("test")
        mock_remove.assert_called_once()

    @patch("argumentation_analysis.core.prover9_runner.subprocess.run")
    @patch("argumentation_analysis.core.prover9_runner.PROVER9_EXECUTABLE")
    @patch("argumentation_analysis.core.prover9_runner.os.path.exists", return_value=True)
    @patch("argumentation_analysis.core.prover9_runner.os.remove")
    def test_temp_file_cleaned_up_on_error(self, mock_remove, mock_exists, mock_executable, mock_run):
        mock_executable.is_file.return_value = True
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd="prover9", output="", stderr="error"
        )

        with pytest.raises(subprocess.CalledProcessError):
            run_prover9("test")
        mock_remove.assert_called_once()

    @patch("argumentation_analysis.core.prover9_runner.subprocess.run")
    @patch("argumentation_analysis.core.prover9_runner.PROVER9_EXECUTABLE")
    def test_uses_cp1252_encoding(self, mock_executable, mock_run):
        mock_executable.is_file.return_value = True
        mock_run.return_value = MagicMock(stdout="ok", returncode=0)

        run_prover9("test")
        call_kwargs = mock_run.call_args
        assert call_kwargs.kwargs.get("encoding") == "cp1252"
