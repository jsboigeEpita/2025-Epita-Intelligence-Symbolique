import pytest
import asyncio
import logging
from unittest.mock import MagicMock, patch, AsyncMock

# On s'assure que le chemin est correct pour importer le manager
import sys
sys.path.insert(0, '.')

from project_core.webapp_from_scripts.backend_manager import BackendManager

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
    """Tests the constructor and basic attribute assignments."""
    assert manager.config == backend_config
    assert manager.module == backend_config['module']

@pytest.mark.asyncio
@patch('project_core.webapp_from_scripts.backend_manager.download_tweety_jars', new_callable=AsyncMock)
@patch('subprocess.Popen')
async def test_start_success(mock_popen, mock_download_jars, manager):
    """Tests a successful start call."""
    manager._wait_for_backend = AsyncMock(return_value=True)
    manager._is_port_occupied = AsyncMock(return_value=False)
    manager._save_backend_info = AsyncMock()
    mock_download_jars.return_value = True

    mock_popen.return_value.pid = 1234
    
    result = await manager.start()

    assert result['success'] is True
    assert result['port'] == manager.start_port
    assert result['pid'] == 1234
    mock_popen.assert_called_once()
    manager._wait_for_backend.assert_called_once_with(manager.start_port)
    manager._save_backend_info.assert_called_once()

@pytest.mark.asyncio
async def test_start_port_occupied(manager):
    """Tests that start fails if the port is already occupied."""
    manager._is_port_occupied = AsyncMock(return_value=True)
    
    result = await manager.start()
    
    assert result['success'] is False
    assert "est déjà occupé" in result['error']

@pytest.mark.asyncio
@patch('subprocess.Popen')
async def test_start_fails_if_wait_fails(mock_popen, manager):
    """Tests that start fails if _wait_for_backend returns False."""
    manager._wait_for_backend = AsyncMock(return_value=False)
    manager._is_port_occupied = AsyncMock(return_value=False)
    manager._cleanup_failed_process = AsyncMock()

    result = await manager.start()

    assert result['success'] is False
    assert f"a échoué à démarrer sur le port {manager.start_port}" in result['error']
    manager._cleanup_failed_process.assert_called_once()

@pytest.mark.asyncio
async def test_wait_for_backend_process_dies(manager):
    """Tests _wait_for_backend when the process terminates prematurely."""
    manager.process = MagicMock()
    manager.process.poll.return_value = 1  # Simulate process ended with exit code 1
    manager.process.returncode = 1
    
    # We need to mock the sleep to ensure the loop doesn't timeout before checking poll()
    with patch('asyncio.sleep', new_callable=AsyncMock):
        result = await manager._wait_for_backend(8000)
    
    assert result is False
    manager.logger.error.assert_called_with("Processus backend terminé prématurément (code: 1)")

@pytest.mark.asyncio
@patch('aiohttp.ClientSession.get')
async def test_wait_for_backend_health_check_ok(mock_get, manager):
    """Tests _wait_for_backend with a successful health check."""
    manager.process = MagicMock()
    manager.process.poll.return_value = None  # Simulate running process

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_get.return_value.__aenter__.return_value = mock_response

    # Mock asyncio.sleep to avoid actual waiting
    with patch('asyncio.sleep', new_callable=AsyncMock):
        result = await manager._wait_for_backend(8000)

    assert result is True

@pytest.mark.asyncio
async def test_wait_for_backend_timeout(manager):
    """Tests _wait_for_backend when it times out."""
    manager.process = MagicMock()
    manager.process.poll.return_value = None
    
    # Make health checks fail continuously
    manager._is_port_occupied = AsyncMock(return_value=False) # Should not be called here but for safety
    with patch('aiohttp.ClientSession.get', side_effect=asyncio.TimeoutError("Test Timeout")):
        result = await manager._wait_for_backend(8000)
    
    assert result is False
    manager.logger.error.assert_called_with("Timeout dépassé - Backend inaccessible sur http://127.0.0.1:8000/api/health")

@pytest.mark.asyncio
async def test_stop_process(manager):
    """Tests the stop method."""
    mock_process = MagicMock()
    mock_process.pid = 1234
    manager.process = mock_process
    
    await manager.stop()
    
    mock_process.terminate.assert_called_once()
    assert manager.process is None
    assert manager.pid is None