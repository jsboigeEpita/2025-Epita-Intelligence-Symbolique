import pytest
import asyncio
import logging
from unittest.mock import MagicMock, patch, AsyncMock

# On s'assure que le chemin est correct pour importer le manager
import sys
sys.path.insert(0, '.')

from scripts.webapp.backend_manager import BackendManager

@pytest.fixture
def backend_config(webapp_config):
    """Provides a base backend config."""
    return webapp_config['backend']

@pytest.fixture
def logger_mock():
    """Mocks the logger."""
    return MagicMock(spec=logging.Logger)

@pytest.fixture
def manager(backend_config, logger_mock):
    """Initializes BackendManager with a default config."""
    return BackendManager(backend_config, logger_mock)

def test_initialization(manager, backend_config):
    """Tests that the manager initializes correctly."""
    assert manager.config == backend_config
    assert manager.logger is not None
    assert manager.start_port == backend_config['start_port']
    assert manager.fallback_ports == backend_config['fallback_ports'] # Fix: Check 'fallback_ports'
    assert manager.process is None

@pytest.mark.asyncio
async def test_start_with_failover_success_first_port(manager, mock_popen):
    """
    Tests successful start on the primary port.
    """
    manager._is_port_occupied = AsyncMock(return_value=False)
    manager._start_on_port = AsyncMock(return_value={
        'success': True, 'url': f'http://localhost:{manager.start_port}',
        'port': manager.start_port, 'pid': 1234
    })
    manager._save_backend_info = AsyncMock()

    result = await manager.start_with_failover()

    assert result['success'] is True
    assert result['port'] == manager.start_port
    manager._is_port_occupied.assert_called_once_with(manager.start_port)
    manager._start_on_port.assert_called_once_with(manager.start_port)
    manager._save_backend_info.assert_called_once()

@pytest.mark.asyncio
async def test_start_with_failover_uses_fallback_port(manager, mock_popen):
    """
    Tests that failover to a fallback port works correctly.
    """
    manager._is_port_occupied = AsyncMock(side_effect=[True, False]) # First busy, second free
    manager._start_on_port = AsyncMock(return_value={
        'success': True, 'url': f'http://localhost:{manager.fallback_ports[0]}',
        'port': manager.fallback_ports[0], 'pid': 1234
    })
    manager._save_backend_info = AsyncMock()

    result = await manager.start_with_failover()

    assert result['success'] is True
    assert result['port'] == manager.fallback_ports[0]
    assert manager._is_port_occupied.call_count == 2
    manager._start_on_port.assert_called_once_with(manager.fallback_ports[0])

@pytest.mark.asyncio
async def test_start_with_failover_all_ports_fail(manager):
    """
    Tests failure when all ports are unavailable.
    """
    manager._is_port_occupied = AsyncMock(return_value=True) # All ports are busy
    manager._start_on_port = AsyncMock() # Should not be called

    result = await manager.start_with_failover()

    assert result['success'] is False
    assert "Impossible de démarrer" in result['error']
    assert manager._is_port_occupied.call_count == len(manager.fallback_ports) + 1
    manager._start_on_port.assert_not_called()

@pytest.mark.asyncio
@patch('scripts.webapp.backend_manager.BackendManager._get_conda_env_python_executable', new_callable=AsyncMock)
async def test_start_on_port_success(mock_get_python_exe, manager, mock_popen):
    """
    Tests the "_start_on_port" method for a successful start.
    """
    mock_get_python_exe.return_value = "/fake/conda/python"
    manager._wait_for_backend = AsyncMock(return_value=True)
    port = 8000

    result = await manager._start_on_port(port)

    assert result['success'] is True
    assert result['port'] == port
    assert result['pid'] == 1234
    mock_popen.assert_called_once()
    manager._wait_for_backend.assert_called_once_with(port)

@pytest.mark.asyncio
@patch('scripts.webapp.backend_manager.BackendManager._get_conda_env_python_executable', new_callable=AsyncMock)
async def test_start_on_port_backend_wait_fails(mock_get_python_exe, manager, mock_popen):
    """
    Tests "_start_on_port" when waiting for the backend fails.
    """
    mock_get_python_exe.return_value = "/fake/conda/python"
    manager._wait_for_backend = AsyncMock(return_value=False)
    port = 8000

    result = await manager._start_on_port(port)

    assert result['success'] is False
    assert "non accessible" in result['error']
    mock_popen.return_value.terminate.assert_called_once()


@pytest.mark.asyncio
async def test_wait_for_backend_process_dies(manager, mock_popen):
    """
    Tests that _wait_for_backend returns False if the process dies.
    """
    mock_popen.return_value.poll.return_value = 1
    mock_popen.return_value.returncode = 1 
    
    manager.process = mock_popen.return_value

    result = await manager._wait_for_backend(8000)

    assert result is False
    manager.logger.error.assert_called_with("Processus backend terminé prématurément (code: 1)")

@pytest.mark.asyncio
@patch('aiohttp.ClientSession.get')
async def test_wait_for_backend_health_check_ok(mock_get, manager, mock_popen):
    """
    Tests _wait_for_backend with a successful health check.
    """
    manager.process = mock_popen.return_value
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_get.return_value.__aenter__.return_value = mock_response

    with patch('asyncio.sleep', new_callable=AsyncMock):
        result = await manager._wait_for_backend(8000)

    assert result is True

@pytest.mark.asyncio
async def test_stop_process(manager, mock_popen):
    """
    Tests the stop method.
    """
    manager.process = mock_popen.return_value
    manager.pid = 1234

    await manager.stop()

    mock_popen.return_value.terminate.assert_called_once()
    assert manager.process is None
    assert manager.pid is None