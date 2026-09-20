"""Signal handling — the orchestrator's shutdown path, held honestly.

This file was born 0-byte in ``727ae7c72`` and never filled (#2330). The
feature it promised is real: ``UnifiedWebOrchestrator._setup_signal_handlers``
(orchestrator.py) registers SIGINT/SIGTERM handlers on POSIX and — the
documented Windows contract — logs and skips registration on win32 (the
Proactor loop cannot host them).

What IS testable on every platform this suite runs on (Windows CI included):

* constructing the orchestrator does NOT crash on the win32 branch — the
  lifecycle suite's fixture patches ``_setup_signal_handlers`` away, so
  nothing currently proves the real win32 branch is harmless;
* ``shutdown(signal=...)`` records the signal in the trace and actually
  stops the webapp;
* shutdown is IDEMPOTENT — a second signal during teardown must not restart
  the teardown (the double-signal case is the normal Ctrl-C experience).

What is deliberately NOT tested here: the POSIX registration branch
(``loop.add_signal_handler``) — on Windows it cannot run for SIGTERM
(NotImplementedError on the event loops Windows provides), and faking the
loop would mock the thing under test. The POSIX branch also calls
``asyncio.get_running_loop()`` from the synchronous ``__init__`` — a latent
crash outside an async context that only a POSIX run can surface; noted on
#2330, not widened here.

No LLM, no network, no browser.
"""

import asyncio
import signal
import sys
from pathlib import Path

import pytest

sys.path.insert(0, ".")

from argumentation_analysis.webapp.orchestrator import (
    UnifiedWebOrchestrator,
    WebAppStatus,
)


@pytest.fixture
def orchestrator(webapp_config, test_config_path):
    """Signal-shaped: handlers NOT patched (the real win32 branch runs) and
    traces ENABLED — ``add_trace`` is a no-op under ``no_trace=True``.

    Backend/frontend disabled so the REAL ``stop_webapp`` (which the repair
    lets run on a never-started app) walks an empty port list —
    ``MinimalProcessCleaner`` returns immediately on ``ports_to_check == []``,
    keeping the test hermetic on a dev machine that happens to host
    something on the default ports."""
    import argparse

    import yaml

    webapp_config["backend"]["enabled"] = False
    webapp_config["frontend"]["enabled"] = False
    webapp_config["playwright"] = {"enabled": False}
    with open(test_config_path, "w") as f:
        yaml.dump(webapp_config, f)
    mock_args = argparse.Namespace(
        config=str(test_config_path),
        log_level="DEBUG",
        headless=True,
        visible=False,
        timeout=5,
        no_trace=False,
    )
    return UnifiedWebOrchestrator(args=mock_args)


class TestWin32Contract:
    @pytest.mark.skipif(sys.platform != "win32", reason="win32 branch contract")
    def test_constructor_survives_the_win32_branch(self, orchestrator):
        """The lifecycle fixture patches the real handlers away — this is
        the only test that runs the branch as shipped: log, skip, no crash."""
        assert orchestrator.app_info.status == WebAppStatus.STOPPED


class TestShutdownPath:
    def test_shutdown_records_the_signal_and_stops(self, orchestrator, mocker):
        stop_calls = mocker.patch.object(
            orchestrator, "stop_webapp", wraps=orchestrator.stop_webapp
        )
        asyncio.run(orchestrator.shutdown(signal=signal.SIGINT))
        assert any(
            "SIGNAL RECU" in entry.action for entry in orchestrator.trace_log
        ), "the received signal must be traceable — an operator reading the "
        "trace has to see WHY the app stopped"
        assert stop_calls.call_count == 1
        assert orchestrator.app_info.status == WebAppStatus.STOPPED

    def test_second_signal_during_teardown_is_absorbed(self, orchestrator, mocker):
        """Idempotence: the normal Ctrl-C experience is a SECOND signal
        arriving MID-teardown (status STOPPING), while the first teardown is
        still running. It must be absorbed, not queued, and the first
        teardown must proceed to completion. The teardown is held open on an
        event so the overlap is deterministic, not timing-dependent."""

        entered = asyncio.Event()
        release = asyncio.Event()
        calls = []

        async def slow_stop():
            calls.append("stop")
            # the state the REAL stop_webapp sets at entry (:1161)
            orchestrator.app_info.status = WebAppStatus.STOPPING
            entered.set()
            await release.wait()
            orchestrator.app_info.status = WebAppStatus.STOPPED

        mocker.patch.object(orchestrator, "stop_webapp", side_effect=slow_stop)

        async def run_test():
            first = asyncio.create_task(orchestrator.shutdown(signal=signal.SIGTERM))
            await asyncio.wait_for(entered.wait(), timeout=5)
            second = asyncio.create_task(orchestrator.shutdown(signal=signal.SIGINT))
            # the mid-teardown signal returns promptly instead of queueing
            await asyncio.wait_for(second, timeout=5)
            assert calls == [
                "stop"
            ], "a signal arriving mid-teardown must not restart the teardown"
            release.set()
            await first
            assert calls == ["stop"]

        asyncio.run(run_test())

    def test_shutdown_without_signal_stops_silently(self, orchestrator, mocker):
        mocker.patch.object(orchestrator, "stop_webapp", wraps=orchestrator.stop_webapp)
        asyncio.run(orchestrator.shutdown())
        assert not any(
            "SIGNAL RECU" in entry.action for entry in orchestrator.trace_log
        ), "a programmatic shutdown (no signal) must not fake a received signal"
        assert orchestrator.app_info.status == WebAppStatus.STOPPED
