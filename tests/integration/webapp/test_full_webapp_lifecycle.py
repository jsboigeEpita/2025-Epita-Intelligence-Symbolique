import pytest
import sys
import psutil
import asyncio
from pathlib import Path

sys.path.insert(0, ".")

from argumentation_analysis.webapp.orchestrator import (
    UnifiedWebOrchestrator,
    WebAppStatus,
)


def _webapp_log_offset(orchestrator) -> int:
    """Byte offset of the orchestrator's log file before the attempt (#1840)."""
    for handler in getattr(orchestrator.logger, "handlers", []):
        base = getattr(handler, "baseFilename", None)
        if base and Path(base).exists():
            return Path(base).stat().st_size
    return 0


def _webapp_failure_reason(orchestrator, log_offset: int = 0) -> str:
    """The orchestrator's own reason for a failed start (#1840).

    ``start_webapp()`` returns a bare bool; the orchestrator knows why it
    failed (port, startup timeout, mute health endpoint) and writes it to its
    log — with ``propagate = False``, so caplog cannot see it. Read the state
    it leaves (status, attempted port, pid) plus the log lines written during
    THIS run only (the log file appends across runs).
    """
    info = orchestrator.app_info
    parts = [
        f"status={getattr(info.status, 'value', info.status)}",
        "port_tente="
        f"{getattr(getattr(orchestrator, 'backend_manager', None), 'port', None)}",
        f"backend_pid={info.backend_pid}",
    ]
    for handler in getattr(orchestrator.logger, "handlers", []):
        base = getattr(handler, "baseFilename", None)
        if not base or not Path(base).exists():
            continue
        with open(base, "r", encoding="utf-8", errors="replace") as f:
            f.seek(log_offset)
            lines = f.read().splitlines()
        tail = "\n".join(lines[-40:]) if lines else "(log vide pour ce run)"
        parts.append(
            "\n--- log orchestrateur (40 dernières lignes de ce run) ---\n" + tail
        )
        break
    else:
        parts.append("(aucun fichier de log trouvé)")
    return "\n".join(parts)


@pytest.fixture
def integration_config(webapp_config, tmp_path):
    """Override the config for integration tests to use the real backend."""
    config = webapp_config

    # The command_list is now inherited from the orchestrator's default config,
    # which launches the real uvicorn backend.

    # config['backend']['command_list'] = fake_backend_command_list
    # config['backend']['command'] = None # Ensure list is used
    config["backend"]["health_endpoint"] = "/api/health"
    config["backend"]["start_port"] = 9020  # Use a higher port to be safer
    config["backend"]["fallback_ports"] = [9021, 9022]
    # #1853: the live target (api.main:app) runs initialize_project_environment
    # — JVM bootstrap included — in its startup event; the previous 20s budget
    # was calibrated on the archived Flask stub, which skipped all of it
    # (measured locally: 18.4s wall for the whole test).
    config["backend"]["timeout_seconds"] = 60
    # config['backend']['module'] = None # Let the orchestrator use the default real module

    config["frontend"]["enabled"] = False
    config["playwright"]["enabled"] = False

    return config


@pytest.fixture
def orchestrator(integration_config, test_config_path, mocker):
    """Fixture to get an orchestrator instance for integration tests."""
    import argparse
    import yaml

    mocker.patch(
        "argumentation_analysis.webapp.orchestrator.UnifiedWebOrchestrator._setup_signal_handlers"
    )

    with open(test_config_path, "w") as f:
        yaml.dump(integration_config, f)

    # Create a mock args object that mirrors the one from command line parsing
    mock_args = argparse.Namespace(
        config=str(test_config_path),
        log_level="DEBUG",
        headless=True,
        visible=False,
        timeout=5,  # 5 minutes for integration tests
        no_trace=True,  # Disable trace generation for speed
    )

    return UnifiedWebOrchestrator(args=mock_args)


def test_backend_lifecycle(orchestrator):
    """
    Tests the full start and stop lifecycle of the backend through the orchestrator.
    """

    async def run_test():
        pid_before_stop = None
        try:
            # Start the webapp (only backend enabled)
            log_offset = _webapp_log_offset(orchestrator)
            success = await orchestrator.start_webapp()

            assert success is True, _webapp_failure_reason(orchestrator, log_offset)
            assert orchestrator.app_info.status == WebAppStatus.RUNNING
            assert orchestrator.app_info.backend_pid is not None
            pid_before_stop = orchestrator.app_info.backend_pid

            # Check if the process actually exists
            assert psutil.pid_exists(pid_before_stop)
            proc = psutil.Process(pid_before_stop)
            # Check for 'uvicorn' which indicates the real backend is running
            assert "uvicorn" in " ".join(proc.cmdline())

            # Check that the port is in use
            assert orchestrator.app_info.backend_port in [9020, 9021, 9022]

        finally:
            # Ensure cleanup
            await orchestrator.stop_webapp()

            assert orchestrator.app_info.status == WebAppStatus.STOPPED
            assert orchestrator.app_info.backend_pid is None

            # Check that the process is actually gone
            if pid_before_stop:
                await asyncio.sleep(1)
                assert not psutil.pid_exists(pid_before_stop)

    asyncio.run(run_test())
