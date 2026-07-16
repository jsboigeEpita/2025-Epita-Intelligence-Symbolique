# -*- coding: utf-8 -*-
"""
Integration test for BO-1 #1471 continuation (R652) — the CLI entry-point
``argumentation_analysis/run_orchestration.py`` now creates a
``MessageMiddleware`` with the standard channel set (HIERARCHICAL + DATA)
registered, via the new :func:`create_default_middleware` factory.

Before this fix the delegation path emitted 17 ``Channel not found`` errors
per run (16× ``hierarchical`` + 1× ``data``) and the inter-tier results
fell back to file-drop (``results/task-obj-*.json``) instead of the live
bus. The R644/R648/R651 chain made the chain decide E2E — but the
plumbing was still degraded. The R652 fix wires the channels at every
``self.middleware = middleware or MessageMiddleware()`` site under
``orchestration/hierarchical/``.

Anti-pendule guard: a single helper centralises the channel set so a
future addition (e.g. FEEDBACK) is a one-line change — no scattered
``register_channel`` calls to forget at any of the 6 call sites.

This test invokes the **real CLI** via ``subprocess.run`` (not the
function directly) and asserts:

1. The combined stdout/stderr contains **0 occurrences** of
   ``Channel not found`` (the dispatch's primary DoD marker).
2. The combined output contains at least one ``Channel registered:
   hierarchical`` and one ``Channel registered: data`` (witness that
   the helper wired the channels upstream).
3. The run still completes 5/5 tasks with a graded conclusion (no
   regression on the R648/R651 contract).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
CLI_SCRIPT = REPO_ROOT / "argumentation_analysis" / "run_orchestration.py"

SIMPLE_TEXT = "Le soleil brille. Il fait beau."

# These exact substrings come from the BO-1 #1471 R652 dispatch's DoD
# markers. They pin the contract that ``create_default_middleware``
# registers BOTH channels.
HIERARCHICAL_REGISTERED_MARKER = "Channel registered: hierarchical"
DATA_REGISTERED_MARKER = "Channel registered: data"
CHANNEL_NOT_FOUND_MARKER = "Channel not found"


def _run_cli(*extra_args: str) -> subprocess.CompletedProcess[str]:
    """Invoke the real CLI entry-point and return the CompletedProcess.

    ``-u`` (unbuffered) so stdout/stderr flush in order, mirroring the
    probe captured in the dispatch acknowledgment.
    """
    return subprocess.run(
        [
            sys.executable,
            "-u",
            str(CLI_SCRIPT),
            *extra_args,
        ],
        capture_output=True,
        text=True,
        timeout=300,
        cwd=str(REPO_ROOT),
    )


class TestChannelRegistration:
    """The R652 fix wires HIERARCHICAL + DATA channels into the
    ``MessageMiddleware`` used by the hierarchical orchestrator, so
    the live bus is used instead of file-drop fallback. Anti-pendule:
    centralised in :func:`create_default_middleware` (1 source of
    truth) — no scattered ``register_channel`` calls.
    """

    def test_cli_delegation_mode_has_no_channel_not_found(self) -> None:
        """The dispatch's primary DoD: ``--mode hierarchical
        --hierarchical-mode delegation`` runs end-to-end with **zero**
        ``Channel not found`` errors in the combined log.

        Before the R652 fix this run emitted 17 such errors (16×
        ``hierarchical`` + 1× ``data``).
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

        occurrences = combined.count(CHANNEL_NOT_FOUND_MARKER)
        assert occurrences == 0, (
            "R652 regression: 'Channel not found' still appears "
            f"{occurrences} time(s) on the CLI delegation path. "
            "The HIERARCHICAL+DATA channels are not registered on the "
            "per-tier MessageMiddleware instances.\n"
            f"--- STDOUT (tail) ---\n{result.stdout[-2000:]}\n"
            f"--- STDERR (tail) ---\n{result.stderr[-2000:]}"
        )

    def test_cli_delegation_mode_registers_both_channels(self) -> None:
        """Witness that the helper actually wired the channels upstream
        (positive control on the previous assertion). Both
        ``hierarchical`` and ``data`` must appear in ``Channel
        registered:`` log lines.
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

        assert HIERARCHICAL_REGISTERED_MARKER in combined, (
            "R652 regression: no 'Channel registered: hierarchical' "
            "log line. create_default_middleware() did not wire the "
            "HierarchicalChannel upstream.\n"
            f"--- STDOUT (tail) ---\n{result.stdout[-2000:]}\n"
            f"--- STDERR (tail) ---\n{result.stderr[-2000:]}"
        )
        assert DATA_REGISTERED_MARKER in combined, (
            "R652 regression: no 'Channel registered: data' log "
            "line. create_default_middleware() did not wire the "
            "DataChannel upstream.\n"
            f"--- STDOUT (tail) ---\n{result.stdout[-2000:]}\n"
            f"--- STDERR (tail) ---\n{result.stderr[-2000:]}"
        )

    def test_cli_delegation_mode_still_completes_e2e(self) -> None:
        """No regression on the R648/R651 contract: 5/5 tasks complete
        and a graded conclusion is printed. The R652 plumbing fix must
        not regress the decision chain.
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

        assert "Tâches complétées" in combined, (
            "R652 regression: the per-axis summary is missing. The "
            "delegation chain did not reach the conclusion phase.\n"
            f"--- STDOUT (tail) ---\n{result.stdout[-2000:]}\n"
            f"--- STDERR (tail) ---\n{result.stderr[-2000:]}"
        )
        assert "Conclu" in combined and "performance" in combined, (
            "R652 regression: the graded conclusion is missing. The "
            "decision phase did not render.\n"
            f"--- STDOUT (tail) ---\n{result.stdout[-2000:]}\n"
            f"--- STDERR (tail) ---\n{result.stderr[-2000:]}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
