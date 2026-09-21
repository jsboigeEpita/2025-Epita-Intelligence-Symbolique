"""POSIX signal registration — the loop-acquisition contract, from a Windows seat.

#2334: ``UnifiedWebOrchestrator.__init__`` is synchronous and calls
``_setup_signal_handlers``, whose POSIX branch calls ``asyncio.get_running_loop()``
— which raises ``RuntimeError`` outside a coroutine. Constructing the
orchestrator from ordinary synchronous code — what a constructor invites —
crashes on Linux/macOS and cannot crash on Windows: the CI seat that makes
the win32 path safe makes the POSIX path unobservable.

The contract, both halves, reachable from Windows:

* constructed OFF-loop on the POSIX path → no crash, a NAMED degradation
  (warning log naming what was not registered and the remaining programmatic
  path, ``shutdown(signal=...)``);
* constructed ON-loop on the POSIX path → SIGINT and SIGTERM handlers are
  registered on that loop.

Substitutions, per the DoD: the PLATFORM is substituted (``sys.platform``)
and, for the on-loop half only, the loop state is substituted
(``get_running_loop`` returns a recording stub — a Windows loop cannot host
``add_signal_handler``). The thing under test is the branch's DECISION, not
the OS signal machinery. The off-loop half uses the REAL
``get_running_loop``: its ``RuntimeError`` outside a coroutine is exactly
the failure mode, and it fires on any platform.

No ``pytest.skip`` stands in for the platform — a skip here would restore
the blindness that let the defect live (STOP&REPAIR, #2334 DoD).
"""

import argparse
import signal
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, ".")

from argumentation_analysis.webapp.orchestrator import UnifiedWebOrchestrator


def _build_orchestrator(webapp_config, test_config_path, tmp_path):
    """Construct the orchestrator from ordinary SYNCHRONOUS code — the use a
    constructor invites, and the exact shape that crashed on POSIX (#2334).

    The orchestrator's log file is redirected to tmp_path: the named
    degradation is asserted on the channel an operator reads, not on pytest's
    capture plumbing."""
    import yaml

    log_file = tmp_path / "orch.log"
    webapp_config["logging"] = {"file": str(log_file)}
    # #2336 : l'identité du logger dérive désormais de la destination — chaque
    # fichier de log configuré a son propre logger. Le détachement de handlers
    # qui vivait ici (workaround du logger module-level capturé par la première
    # construction) est obsolète : ce tmp_path est unique par test, donc le
    # logger l'est aussi, et le workaround ne survit pas à sa réparation.
    with open(test_config_path, "w") as f:
        yaml.dump(webapp_config, f)
    args = argparse.Namespace(
        config=str(test_config_path),
        log_level="DEBUG",
        headless=True,
        visible=False,
        timeout=5,
        no_trace=True,
    )
    orchestrator = UnifiedWebOrchestrator(args=args)
    logged = log_file.read_text(encoding="utf-8") if log_file.exists() else ""
    return orchestrator, logged


class TestPosixOffLoopConstruction:
    def test_offloop_posix_construction_degrades_named_not_crash(
        self, webapp_config, test_config_path, tmp_path, monkeypatch
    ):
        """Born-red control (#2334 DoD 3): before the fix this construction
        RAISES RuntimeError('no running event loop'). After: no crash, and
        the degradation is NAMED — the operator is told the handlers were not
        registered and what the remaining path is."""
        monkeypatch.setattr(sys, "platform", "linux")
        orchestrator, logged = _build_orchestrator(
            webapp_config, test_config_path, tmp_path
        )

        assert orchestrator.app_info is not None  # constructed, not crashed
        assert "hors boucle" in logged, (
            "off-loop POSIX construction must log the named degradation — "
            "a silent no-op would rebuild the blindness #2334 repairs"
        )
        assert (
            "shutdown" in logged
        ), "the degradation must name the remaining programmatic path"


class TestPosixOnLoopConstruction:
    def test_onloop_posix_construction_registers_both_signals(
        self, webapp_config, test_config_path, tmp_path, monkeypatch
    ):
        """The on-loop half: a running loop exists, both signals get their
        handler on THAT loop. The loop is a recording stub (a Windows loop
        cannot host add_signal_handler) — the subject is the branch's
        decision, not the OS machinery."""
        import asyncio

        monkeypatch.setattr(sys, "platform", "linux")
        stub_loop = MagicMock()
        monkeypatch.setattr(asyncio, "get_running_loop", lambda: stub_loop)

        _build_orchestrator(webapp_config, test_config_path, tmp_path)

        registered = {
            call_.args[0] for call_ in stub_loop.add_signal_handler.call_args_list
        }
        assert registered == {
            signal.SIGINT,
            signal.SIGTERM,
        }, f"both signals must be registered on the running loop, got {registered}"


class TestWin32Unchanged:
    def test_win32_construction_still_skips_registration_named(
        self, webapp_config, test_config_path, tmp_path, monkeypatch
    ):
        """Anti-pendulum: the repair must not move the win32 contract. The
        platform is substituted to win32 (the branch is asserted by
        substitution, never skipped) and the named non-registration must
        still be logged."""
        monkeypatch.setattr(sys, "platform", "win32")
        _, logged = _build_orchestrator(webapp_config, test_config_path, tmp_path)

        assert (
            "Windows" in logged
        ), "the win32 branch must still log its named non-registration"
