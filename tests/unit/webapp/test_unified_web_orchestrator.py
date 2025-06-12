import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock, call

# On s'assure que le chemin est correct pour importer l'orchestrateur
import sys
sys.path.insert(0, '.')

from project_core.webapp_from_scripts.unified_web_orchestrator import UnifiedWebOrchestrator, WebAppStatus

# We need to mock the manager classes before they are imported by the orchestrator
sys.modules['project_core.webapp_from_scripts.backend_manager'] = MagicMock()
sys.modules['project_core.webapp_from_scripts.frontend_manager'] = MagicMock()
sys.modules['project_core.webapp_from_scripts.playwright_runner'] = MagicMock()
sys.modules['project_core.webapp_from_scripts.process_cleaner'] = MagicMock()

# This patch will apply to all tests in this module for signal handlers
@pytest.fixture(autouse=True)
def mock_signal_handlers():
    with patch('project_core.webapp_from_scripts.unified_web_orchestrator.UnifiedWebOrchestrator._setup_signal_handlers') as mock_setup:
        yield mock_setup

@pytest.fixture
def mock_managers():
    """Mocks all the specialized manager classes."""
    with patch('project_core.webapp_from_scripts.unified_web_orchestrator.BackendManager') as MockBackend, \
         patch('project_core.webapp_from_scripts.unified_web_orchestrator.FrontendManager') as MockFrontend, \
         patch('project_core.webapp_from_scripts.unified_web_orchestrator.PlaywrightRunner') as MockPlaywright, \
         patch('project_core.webapp_from_scripts.unified_web_orchestrator.ProcessCleaner') as MockCleaner:
        
        yield {
            "backend": MockBackend.return_value,
            "frontend": MockFrontend.return_value,
            "playwright": MockPlaywright.return_value,
            "cleaner": MockCleaner.return_value,
        }

@pytest.fixture
def orchestrator(webapp_config, test_config_path, mock_managers):
    """Initializes the orchestrator with mocked managers."""
    # Prevent logging setup from failing
    with patch('project_core.webapp_from_scripts.unified_web_orchestrator.UnifiedWebOrchestrator._setup_logging'):
        orch = UnifiedWebOrchestrator(config_path=test_config_path)
        # Attach mocks for easy access in tests
        orch.backend_manager = mock_managers['backend']
        orch.frontend_manager = mock_managers['frontend']
        orch.playwright_runner = mock_managers['playwright']
        orch.process_cleaner = mock_managers['cleaner']
        # Also mock add_trace to avoid printing during tests and for assertion
        orch.add_trace = MagicMock()
        return orch

def test_initialization(orchestrator, mock_managers):
    """Tests that the orchestrator initializes its managers."""
    assert orchestrator.backend_manager is not None
    assert orchestrator.frontend_manager is not None
    assert orchestrator.playwright_runner is not None
    assert orchestrator.process_cleaner is not None
    assert orchestrator.app_info.status == WebAppStatus.STOPPED

@pytest.mark.asyncio
async def test_start_webapp_success_flow(orchestrator):
    """Tests the successful startup flow of the webapp."""
    # Configure mocks to simulate success
    orchestrator._cleanup_previous_instances = AsyncMock()
    orchestrator.backend_manager.start_with_failover = AsyncMock(return_value={'success': True, 'url': 'http://b', 'port': 1, 'pid': 10})
    orchestrator.frontend_manager.start = AsyncMock(return_value={'success': True, 'url': 'http://f', 'port': 2, 'pid': 20})
    orchestrator.config['frontend']['enabled'] = True # Ensure frontend is enabled for this test
    orchestrator._validate_services = AsyncMock(return_value=True)
    orchestrator._launch_playwright_browser = AsyncMock()

    result = await orchestrator.start_webapp()

    assert result is True
    orchestrator._cleanup_previous_instances.assert_called_once()
    orchestrator.backend_manager.start_with_failover.assert_called_once()
    orchestrator.frontend_manager.start.assert_called_once()
    orchestrator._validate_services.assert_called_once()
    orchestrator._launch_playwright_browser.assert_called_once()
    assert orchestrator.app_info.status == WebAppStatus.RUNNING
    assert orchestrator.app_info.backend_pid == 10
    assert orchestrator.app_info.frontend_pid == 20

@pytest.mark.asyncio
async def test_start_webapp_backend_fails(orchestrator):
    """Tests the startup flow when the backend fails to start."""
    orchestrator._cleanup_previous_instances = AsyncMock()
    orchestrator.backend_manager.start_with_failover = AsyncMock(return_value={'success': False, 'error': 'failure'})
    
    result = await orchestrator.start_webapp()

    assert result is False
    orchestrator.backend_manager.start_with_failover.assert_called_once()
    orchestrator.frontend_manager.start.assert_not_called() # Should not be called if backend fails
    assert orchestrator.app_info.status == WebAppStatus.ERROR

@pytest.mark.asyncio
async def test_stop_webapp_flow(orchestrator):
    """Tests the graceful shutdown sequence."""
    # Simulate a running state
    orchestrator.app_info.status = WebAppStatus.RUNNING
    orchestrator.app_info.backend_pid = 123
    orchestrator.app_info.frontend_pid = 456
    
    # Mock stop methods
    orchestrator._close_playwright_browser = AsyncMock()
    orchestrator.frontend_manager.stop = AsyncMock()
    orchestrator.backend_manager.stop = AsyncMock()
    orchestrator.process_cleaner.cleanup_webapp_processes = AsyncMock()

    await orchestrator.stop_webapp()

    orchestrator._close_playwright_browser.assert_called_once()
    orchestrator.frontend_manager.stop.assert_called_once()
    orchestrator.backend_manager.stop.assert_called_once()
    orchestrator.process_cleaner.cleanup_webapp_processes.assert_called_once()
    assert orchestrator.app_info.status == WebAppStatus.STOPPED

@pytest.mark.asyncio
async def test_full_integration_test_flow_success(orchestrator):
    """Tests the main integration method flow on success."""
    # Mock all sub-methods to return success
    orchestrator.start_webapp = AsyncMock(return_value=True)
    orchestrator.run_tests = AsyncMock(return_value=True)
    orchestrator.stop_webapp = AsyncMock()
    orchestrator._save_trace_report = AsyncMock()

    # We need to patch sleep to avoid actually sleeping
    with patch('asyncio.sleep', new_callable=AsyncMock):
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
    orchestrator.run_tests = AsyncMock(return_value=False) # Simulate test failure
    orchestrator.stop_webapp = AsyncMock()
    orchestrator._save_trace_report = AsyncMock()

    with patch('asyncio.sleep', new_callable=AsyncMock):
        result = await orchestrator.full_integration_test()

    assert result is False
    orchestrator.stop_webapp.assert_called_once() # Stop should still be called
    orchestrator._save_trace_report.assert_called_once()
    # Check that error trace was added
    error_trace_call = call("[ERROR] ECHEC INTEGRATION", "Certains tests ont échoué", "Voir logs détaillés", status="error")
    orchestrator.add_trace.assert_has_calls([error_trace_call])