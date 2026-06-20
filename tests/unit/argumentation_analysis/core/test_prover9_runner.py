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
    def test_called_without_check_true(self, mock_executable, mock_run):
        """FP-8: ``check`` must NOT be True. Prover9's exit code is semantic —
        exit 2 with "SEARCH FAILED" is the NORMAL outcome for a consistency
        check on a CONSISTENT KB. ``check=True`` raised on exactly that case,
        so a consistent KB could never be reported (théâtre). The runner now
        inspects the "Fatal error" marker in stdout instead.
        """
        mock_executable.is_file.return_value = True
        mock_run.return_value = MagicMock(stdout="ok", returncode=0)

        run_prover9("test input")
        call_kwargs = mock_run.call_args
        assert call_kwargs.kwargs.get("check") is not True

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
    @patch(
        "argumentation_analysis.core.prover9_runner.os.path.exists", return_value=True
    )
    @patch("argumentation_analysis.core.prover9_runner.os.remove")
    def test_temp_file_cleaned_up_on_success(
        self, mock_remove, mock_exists, mock_executable, mock_run
    ):
        mock_executable.is_file.return_value = True
        mock_run.return_value = MagicMock(stdout="ok", returncode=0)

        run_prover9("test")
        mock_remove.assert_called_once()

    @patch("argumentation_analysis.core.prover9_runner.subprocess.run")
    @patch("argumentation_analysis.core.prover9_runner.PROVER9_EXECUTABLE")
    @patch(
        "argumentation_analysis.core.prover9_runner.os.path.exists", return_value=True
    )
    @patch("argumentation_analysis.core.prover9_runner.os.remove")
    def test_temp_file_cleaned_up_on_error(
        self, mock_remove, mock_exists, mock_executable, mock_run
    ):
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

    @patch("argumentation_analysis.core.prover9_runner.subprocess.run")
    @patch("argumentation_analysis.core.prover9_runner.PROVER9_EXECUTABLE")
    def test_fatal_error_in_stdout_raises_not_silent_verdict(
        self, mock_executable, mock_run
    ):
        """FP-8 #1019: Prover9's .bat wrapper returns exit code 0 even on a
        fatal parse/syntax error. The runner must detect the "Fatal error"
        marker in stdout and raise — otherwise the malformed-input error string
        is returned as if it were a real consistency verdict (théâtre).
        """
        mock_executable.is_file.return_value = True
        # exit 0 (unreliable) but a fatal-error marker in stdout
        mock_run.return_value = MagicMock(
            stdout="Fatal error: Unrecognized command or list\n\n goals.\n",
            returncode=0,
        )
        with pytest.raises(RuntimeError, match="Prover9 reported a fatal error"):
            run_prover9("goals.\n$F.\nend_of_list.")

    def test_real_binary_inconsistent_kb_emits_theorem_proved(self):
        """FP-8 verify-the-verification: the REAL bundled Prover9 binary
        (2009-11A) emits "THEOREM PROVED" when it finds a proof (KB entails
        $F = inconsistent), and emits "SEARCH FAILED" (NOT an exception) when
        consistent. This empirically pins TWO contracts:
          (1) the proof-found marker the fol_handler must match (previous code
              looked for "END OF PROOF" in the wrong case — never matched), and
          (2) a non-zero exit code is SEMANTIC here: exit 2 = "SEARCH FAILED" on
              a consistent KB is the normal outcome the caller needs, so the
              runner must NOT raise on it (the previous ``check=True`` raised on
              exactly the consistent case → a consistent KB could never be
              reported = théâtre).
        Skipped if the binary is absent (CI without libs/).
        """
        if not PROVER9_EXECUTABLE.is_file():
            pytest.skip("Prover9 binary not bundled on this machine")
        inconsistent_input = (
            "formulas(assumptions).\np.\n-p.\nend_of_list.\n\n"
            "formulas(goals).\n$F.\nend_of_list.\n"
        )
        inconsistent_out = run_prover9(inconsistent_input)
        assert "THEOREM PROVED" in inconsistent_out  # proof of $F found
        consistent_input = (
            "formulas(assumptions).\np.\nend_of_list.\n\n"
            "formulas(goals).\nq.\nend_of_list.\n"
        )
        # Consistent KB: runner must RETURN (not raise) stdout with "SEARCH
        # FAILED" — the handler then reads "THEOREM PROVED not in out" = True.
        consistent_out = run_prover9(consistent_input)
        assert "THEOREM PROVED" not in consistent_out  # no proof = consistent
        assert "SEARCH FAILED" in consistent_out  # the normal no-proof marker
