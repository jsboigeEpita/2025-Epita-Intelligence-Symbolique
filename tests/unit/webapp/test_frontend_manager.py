import pytest
import logging
import subprocess
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path

# On s'assure que le chemin est correct pour importer le manager
import sys
sys.path.insert(0, '.')

from scripts.webapp.frontend_manager import FrontendManager

@pytest.fixture
def frontend_config(webapp_config):
    """Provides a base frontend config."""
    return webapp_config['frontend']

@pytest.fixture
def logger_mock():
    """Mocks the logger."""
    return MagicMock(spec=logging.Logger)

@pytest.fixture
def manager(frontend_config, logger_mock):
    """Initializes FrontendManager with a default config."""
    # Enable the manager for most tests
    frontend_config['enabled'] = True
    return FrontendManager(frontend_config, logger_mock)

def test_initialization(manager, frontend_config):
    """Tests that the manager initializes correctly."""
    assert manager.config == frontend_config
    assert manager.enabled is True
    assert manager.port == frontend_config['port']
    assert manager.process is None

@pytest.mark.asyncio
async def test_start_when_disabled(logger_mock):
    """Tests that start() returns immediately if not enabled."""
    config = {'enabled': False}
    manager = FrontendManager(config, logger_mock)
    result = await manager.start()
    assert result['success'] is True
    assert result['error'] == 'Frontend désactivé'

@pytest.mark.asyncio
async def test_start_fails_if_path_not_found(manager, tmp_path):
    """Tests that start() fails if the frontend path does not exist."""
    manager.frontend_path = tmp_path / "non_existent_path"
    result = await manager.start()
    assert result['success'] is False
    assert "introuvable" in result['error']

@pytest.mark.asyncio
async def test_start_fails_if_package_json_missing(manager, tmp_path):
    """Tests that start() fails if package.json is missing."""
    manager.frontend_path = tmp_path
    (tmp_path / "some_other_file.txt").touch() # Create the dir but no package.json
    result = await manager.start()
    assert result['success'] is False
    assert "package.json introuvable" in result['error']

@pytest.mark.asyncio
@patch('subprocess.Popen')
async def test_ensure_dependencies_installs_if_needed(mock_popen, manager, tmp_path):
    """Tests that 'npm install' is run when node_modules is missing."""
    manager.frontend_path = tmp_path
    (tmp_path / "package.json").touch()
    
    # Mock Popen for npm install
    mock_process = MagicMock()
    mock_process.communicate.return_value = (b'success', b'')
    mock_process.returncode = 0
    mock_popen.return_value = mock_process

    await manager._ensure_dependencies()

    mock_popen.assert_called_with(
        ['npm', 'install'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=tmp_path
    )
    # Fix: Use assert_any_call because other logs might happen
    manager.logger.info.assert_any_call("Installation dépendances npm...")


@pytest.mark.asyncio
@patch('subprocess.Popen')
async def test_start_success(mock_popen, manager, tmp_path):
    """Tests the full successful start sequence."""
    manager.frontend_path = tmp_path
    (tmp_path / "package.json").touch()
    (tmp_path / "node_modules").mkdir()

    manager._wait_for_frontend = AsyncMock(return_value=True)

    # Mock Popen for npm start
    mock_popen.return_value.pid = 5678 # Set pid on the instance
    manager.process = mock_popen.return_value # Assign the mock instance here

    result = await manager.start()

    assert result['success'] is True
    assert result['pid'] == 5678
    assert result['port'] == manager.port
    mock_popen.assert_called_once()
    assert manager._wait_for_frontend.call_count == 1


@pytest.mark.asyncio
async def test_stop_process(manager, mock_popen):
    """Tests the stop method."""
    # To test closing files, we need to mock open
    mock_stdout_file = MagicMock()
    mock_stderr_file = MagicMock()
    with patch("builtins.open") as mock_open:
        # Simulate that open returns our mocks
        mock_open.side_effect = [mock_stdout_file, mock_stderr_file]
        
        manager.process = mock_popen.return_value
        manager.pid = 1234
        # Simulate that these files were opened
        manager.frontend_stdout_log_file = mock_stdout_file
        manager.frontend_stderr_log_file = mock_stderr_file

        await manager.stop()

        mock_popen.return_value.terminate.assert_called_once()
        mock_stdout_file.close.assert_called_once()
        mock_stderr_file.close.assert_called_once()
        assert manager.process is None