import pytest
import asyncio
import argparse
from unittest.mock import MagicMock, patch, AsyncMock, call

# On s'assure que le chemin est correct pour importer l'orchestrateur
import sys

sys.path.insert(0, ".")

from argumentation_analysis.webapp.orchestrator import (
    UnifiedWebOrchestrator,
    WebAppStatus,
)


# This patch will apply to all tests in this module for signal handlers
@pytest.fixture(autouse=True)
def mock_signal_handlers():
    with patch(
        "argumentation_analysis.webapp.orchestrator.UnifiedWebOrchestrator._setup_signal_handlers"
    ) as mock_setup:
        yield mock_setup


@pytest.fixture
def mock_managers():
    """Mocks all the specialized manager classes."""
    with patch(
        "argumentation_analysis.webapp.orchestrator.MinimalBackendManager"
    ) as MockBackend, patch(
        "argumentation_analysis.webapp.orchestrator.MinimalFrontendManager"
    ) as MockFrontend, patch(
        "argumentation_analysis.webapp.orchestrator.MinimalProcessCleaner"
    ) as MockCleaner:
        mocks = {
            "backend": MockBackend.return_value,
            "frontend": MockFrontend.return_value,
            "cleaner": MockCleaner.return_value,
        }
        # Configure async methods on the mock instances
        mocks["backend"].start = AsyncMock(
            return_value={"success": True, "url": "http://b", "port": 1, "pid": 10}
        )
        mocks["frontend"].start = AsyncMock(
            return_value={"success": True, "url": "http://f", "port": 2, "pid": 20}
        )
        mocks["cleaner"].cleanup_webapp_processes = AsyncMock()

        yield mocks


@pytest.fixture
def orchestrator(webapp_config, test_config_path, mock_managers):
    """Initializes the orchestrator with mocked managers."""
    mock_args = MagicMock(spec=argparse.Namespace)
    mock_args.config = str(test_config_path)
    mock_args.log_level = "DEBUG"
    mock_args.headless = True
    mock_args.visible = False
    mock_args.timeout = 20
    mock_args.no_trace = False

    with patch(
        "argumentation_analysis.webapp.orchestrator.UnifiedWebOrchestrator._setup_logging"
    ), patch(
        "argumentation_analysis.webapp.orchestrator.UnifiedWebOrchestrator._load_config"
    ) as mock_load_config, patch(
        "argumentation_analysis.webapp.orchestrator.MinimalBackendManager",
        return_value=mock_managers["backend"],
    ), patch(
        "argumentation_analysis.webapp.orchestrator.MinimalFrontendManager",
        return_value=mock_managers["frontend"],
    ), patch(
        "argumentation_analysis.webapp.orchestrator.MinimalProcessCleaner",
        return_value=mock_managers["cleaner"],
    ):
        mock_load_config.return_value = webapp_config

        orch = UnifiedWebOrchestrator(args=mock_args)

        orch.add_trace = MagicMock()
        return orch


def test_initialization(orchestrator, mock_managers):
    """Tests that the orchestrator initializes its managers."""
    assert orchestrator.backend_manager == mock_managers["backend"]
    assert orchestrator.frontend_manager is None
    assert orchestrator.process_cleaner == mock_managers["cleaner"]
    assert orchestrator.app_info.status == WebAppStatus.STOPPED


@pytest.mark.asyncio
async def test_start_webapp_success_flow(orchestrator):
    """Tests the successful startup flow of the webapp."""
    # Configure mocks for success
    orchestrator.config["frontend"]["enabled"] = True
    orchestrator.config["playwright"]["enabled"] = True
    orchestrator._validate_services = AsyncMock(return_value=True)
    orchestrator._launch_playwright_browser = AsyncMock()

    with patch.object(
        orchestrator, "_cleanup_previous_instances", new_callable=AsyncMock
    ) as mock_cleanup:
        result = await orchestrator.start_webapp(frontend_enabled=True)

    assert result is True
    mock_cleanup.assert_called_once()
    orchestrator.backend_manager.start.assert_called_once()
    assert orchestrator.frontend_manager is not None
    orchestrator.frontend_manager.start.assert_called_once()
    orchestrator._validate_services.assert_called_once()
    orchestrator._launch_playwright_browser.assert_called_once()
    assert orchestrator.app_info.status == WebAppStatus.RUNNING
    assert orchestrator.app_info.backend_pid == 10
    assert orchestrator.app_info.frontend_pid == 20


@pytest.mark.asyncio
async def test_start_webapp_backend_fails(orchestrator):
    """Tests the startup flow when the backend fails to start."""
    # Configure the mock to simulate failure
    orchestrator.backend_manager.start.return_value = {
        "success": False,
        "error": "simulated failure",
    }

    with patch.object(
        orchestrator, "_cleanup_previous_instances", new_callable=AsyncMock
    ) as mock_cleanup:
        result = await orchestrator.start_webapp()

    assert result is False
    mock_cleanup.assert_called_once()
    orchestrator.backend_manager.start.assert_called_once()
    # frontend_manager is not even instantiated if backend fails
    assert orchestrator.frontend_manager is None
    assert orchestrator.app_info.status == WebAppStatus.ERROR


@pytest.mark.asyncio
async def test_stop_webapp_flow(orchestrator, mock_managers):
    """Tests the graceful shutdown sequence."""
    # Simulate a running state
    orchestrator.app_info.status = WebAppStatus.RUNNING
    orchestrator.app_info.backend_pid = 123
    orchestrator.app_info.frontend_pid = 456
    orchestrator.frontend_manager = mock_managers[
        "frontend"
    ]  # Manually set for this test
    orchestrator.backend_manager.stop = AsyncMock()
    orchestrator.frontend_manager.stop = AsyncMock()

    orchestrator._close_playwright_browser = AsyncMock()

    await orchestrator.stop_webapp()

    orchestrator._close_playwright_browser.assert_called_once()
    orchestrator.backend_manager.stop.assert_called_once()
    orchestrator.frontend_manager.stop.assert_called_once()
    orchestrator.process_cleaner.cleanup_webapp_processes.assert_called_once()
    assert orchestrator.app_info.status == WebAppStatus.STOPPED


@pytest.mark.asyncio
async def test_full_integration_test_flow_success(orchestrator):
    """Tests the main integration method flow on success."""
    orchestrator.start_webapp = AsyncMock(return_value=True)
    orchestrator.run_tests = AsyncMock(return_value=True)
    orchestrator.stop_webapp = AsyncMock()
    orchestrator._save_trace_report = AsyncMock()

    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await orchestrator.full_integration_test()

    assert result is True
    orchestrator.start_webapp.assert_called_once()
    orchestrator.run_tests.assert_called_once()
    orchestrator.stop_webapp.assert_called_once()
    orchestrator._save_trace_report.assert_called_once()


@pytest.mark.asyncio
async def test_full_integration_test_flow_tests_fail(orchestrator):
    """Tests the main integration method flow when tests fail."""
    orchestrator.start_webapp = AsyncMock(return_value=True)
    # Simulate test failure by raising an exception, as run_tests would do
    orchestrator.run_tests = AsyncMock(side_effect=Exception("Tests failed"))
    orchestrator.stop_webapp = AsyncMock()
    orchestrator._save_trace_report = AsyncMock()

    with patch("asyncio.sleep", new_callable=AsyncMock):
        # The test expects the orchestrator's full_integration_test to catch the exception
        # and return False. If the exception propagates, this test will fail,
        # indicating an issue in the orchestrator's error handling.
        result = await orchestrator.full_integration_test()

    assert (
        result is False
    ), "The orchestrator should have caught the exception and returned False."
    orchestrator.stop_webapp.assert_called_once()  # Stop should still be called
    orchestrator._save_trace_report.assert_called_once()

    # Verify that the correct trace was added for the failure
    error_trace_call = call(
        "[ERROR] ECHEC INTEGRATION",
        "Certains tests ont échoué",
        "Voir logs détaillés",
        status="error",
    )
    # Use assert_any_call as other trace calls might exist
    orchestrator.add_trace.assert_any_call(
        *error_trace_call.args, **error_trace_call.kwargs
    )
