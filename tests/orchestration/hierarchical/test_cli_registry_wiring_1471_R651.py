# -*- coding: utf-8 -*-
"""
Integration test for BO-1 #1471 continuation (R651) — the CLI entry-point
``argumentation_analysis/run_orchestration.py`` now wires a
``CapabilityRegistry`` (built via ``setup_registry()``) into the
hierarchical orchestrator. Before this fix the CLI passed
``capability_registry=None`` straight through, so ``--mode hierarchical
--hierarchical-mode delegation`` raised ``DelegationError`` from the
delegation orchestrator before any provider could run.

This test invokes the **real CLI** via ``subprocess.run`` (not the
function directly) and asserts:

1. Default invocation (no flag) → delegation completes E2E with the
   registry wired; no ``DelegationError``.
2. Bridge mode sanity → completes E2E; --registry is also wired (keeps
   both axes operational).
3. ``--no-registry`` → fails loud with the original ``DelegationError``
   (anti-pendule #1019 preserved for programmatic opt-out).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
CLI_SCRIPT = REPO_ROOT / "argumentation_analysis" / "run_orchestration.py"

SIMPLE_TEXT = (
    "Le president affirme que la politique economique est un succes incontestable."
)

DELEGATION_ERROR_MARKER = (
    "DelegationError: No operational_executor and no capability_registry provided"
)


def _run_cli(*extra_args: str) -> subprocess.CompletedProcess[str]:
    """Invoke the real CLI entry-point with conda-python and the
    ``projet-is`` environment, returning the CompletedProcess for the
    caller to inspect.

    ``-u`` (unbuffered) is added so stdout/stderr flush in order, so the
    subprocess output captures interleave with logging the same way the
    ``conda run`` probe captured them above (referenced in R651 dispatch
    acknowledgment).
    """
    return subprocess.run(
        [
            sys.executable,
            str(CLI_SCRIPT),
            *extra_args,
        ],
        capture_output=True,
        text=True,
        timeout=300,
        cwd=str(REPO_ROOT),
    )


class TestCLIRegistryWiring:
    """The real CLI must wire a CapabilityRegistry into the hierarchical
    orchestrator so delegation mode completes E2E. This is the R651 fix
    scope (per coord dispatch R650).

    Anti-pendule guard: the fail-loud ``DelegationError`` is preserved
    behind ``--no-registry`` so programmatic tests that explicitly opt
    out keep their safety net (no silent heuristic no-op fallback).
    """

    def test_cli_delegation_mode_completes_e2e(self) -> None:
        """``--mode hierarchical --hierarchical-mode delegation`` finishes
        E2E. The CLI prints ``Tâches complétées  : 5/5`` (or higher) and
        a graded conclusion. No ``DelegationError`` anywhere.
        """
        result = _run_cli(
            "--mode",
            "hierarchical",
            "--hierarchical-mode",
            "delegation",
            "--text",
            SIMPLE_TEXT,
        )
        combined = result.stdout + result.stderr

        assert DELEGATION_ERROR_MARKER not in combined, (
            "R651 regression: the CLI still raises DelegationError. "
            "The CapabilityRegistry was not wired into run_hierarchical_analysis.\n"
            f"--- STDOUT (tail) ---\n{result.stdout[-1500:]}\n"
            f"--- STDERR (tail) ---\n{result.stderr[-1500:]}"
        )
        assert "Tâches complétées" in combined, (
            "R651 expectation: the CLI prints the per-axis summary. "
            "Either the delegation chain did not reach the conclusion "
            "phase, or stdout interleaving swallowed the print block.\n"
            f"--- STDOUT (tail) ---\n{result.stdout[-1500:]}\n"
            f"--- STDERR (tail) ---\n{result.stderr[-1500:]}"
        )

    def test_cli_bridge_mode_completes_e2e(self) -> None:
        """``--mode hierarchical --hierarchical-mode bridge`` still
        completes 4/4 phases. Sanity axis 2 (per dispatch R650: 'Idem
        bridge — les 2 axes décident depuis le CLI').
        """
        result = _run_cli(
            "--mode",
            "hierarchical",
            "--hierarchical-mode",
            "bridge",
            "--text",
            SIMPLE_TEXT,
        )
        combined = result.stdout + result.stderr

        assert DELEGATION_ERROR_MARKER not in combined, (
            "R651 regression: bridge mode threw DelegationError. "
            "The registry wiring should not break the M2 path.\n"
            f"--- STDOUT (tail) ---\n{result.stdout[-1500:]}\n"
            f"--- STDERR (tail) ---\n{result.stderr[-1500:]}"
        )
        assert "Phases complétées" in combined, (
            "R651 bridge expectation: the per-axis phase summary is "
            "printed. The bridge chain did not reach the conclusion.\n"
            f"--- STDOUT (tail) ---\n{result.stdout[-1500:]}\n"
            f"--- STDERR (tail) ---\n{result.stderr[-1500:]}"
        )

    def test_cli_no_registry_preserves_fail_loud(self) -> None:
        """``--no-registry`` keeps the fail-loud ``DelegationError``.
        Anti-pendule #1019: programmatic opt-out must NOT silently
        degrade to a no-op. The CI mypy scope and R648/R651 contract
        both depend on this guard.
        """
        result = _run_cli(
            "--mode",
            "hierarchical",
            "--hierarchical-mode",
            "delegation",
            "--no-registry",
            "--text",
            SIMPLE_TEXT,
        )
        combined = result.stdout + result.stderr

        assert DELEGATION_ERROR_MARKER in combined, (
            "R651 anti-pendule breach: --no-registry did not raise the "
            "expected DelegationError. The fail-loud guard was removed "
            "or masked; future callers would silently degrade to "
            "heuristic no-ops.\n"
            f"--- STDOUT (tail) ---\n{result.stdout[-1500:]}\n"
            f"--- STDERR (tail) ---\n{result.stderr[-1500:]}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
