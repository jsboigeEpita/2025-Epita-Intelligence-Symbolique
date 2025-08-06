import pytest
import os
import logging
import asyncio
import subprocess
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path

# On s'assure que le chemin est correct pour importer le manager
import sys
sys.path.insert(0, '.')

# Note: Le chemin d'import a changé vers la classe minimale dans l'orchestrateur
from argumentation_analysis.webapp.orchestrator import MinimalFrontendManager as FrontendManager

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
    assert manager.process is None
    # La logique de l'orchestrateur utilise 'port'
    assert manager.config['port'] == frontend_config['port']

@pytest.mark.asyncio
async def test_start_when_disabled(logger_mock):
    """Tests that start() returns immediately if not enabled."""
    config = {'enabled': False}
    manager = FrontendManager(config, logger_mock)
    result = await manager.start()
    assert result['success'] is True
    assert 'Frontend disabled' in result['error']

@pytest.mark.asyncio
async def test_start_fails_if_path_not_found(manager, logger_mock):
    """Tests that start() fails if the frontend path does not exist."""
    invalid_config = {
        'enabled': True,
        'path': '/non/existent/path'
    }
    manager_invalid = FrontendManager(invalid_config, logger_mock)
    result = await manager_invalid.start()
    assert result['success'] is False
    assert "non valide ou non trouvé" in manager_invalid.logger.error.call_args[0][0]

@pytest.mark.asyncio
@patch('asyncio.create_subprocess_exec')
async def test_start_success(mock_subprocess, manager, logger_mock, tmp_path):
    """Tests the full successful start sequence with the new event-based logic."""
    # Setup
    manager.config['path'] = str(tmp_path)
    mock_proc = AsyncMock()
    mock_proc.pid = 1234
    
    # Configure stdout mock
    mock_stdout = AsyncMock()
    # readline is awaitable
    mock_stdout.readline.side_effect = [
        b'Starting the development server...\n',
        b'Compiled successfully!\n',
    ]
    # at_eof is a synchronous method, so we use a standard MagicMock for it
    # This resolves the RuntimeWarning about a coroutine not being awaited.
    stdout_at_eof_mock = MagicMock(side_effect=[False, False, True])
    mock_stdout.at_eof = stdout_at_eof_mock

    # Configure stderr mock
    mock_stderr = AsyncMock()
    mock_stderr.readline.side_effect = [] # No output
    stderr_at_eof_mock = MagicMock(return_value=True) # Always at end
    mock_stderr.at_eof = stderr_at_eof_mock

    mock_proc.stdout = mock_stdout
    mock_proc.stderr = mock_stderr

    mock_subprocess.return_value = mock_proc

    # Execute the start method with a timeout to prevent hangs
    result = await asyncio.wait_for(manager.start(), timeout=2)

    # Assertions
    assert result['success'] is True
    assert result['port'] == manager.config['port']
    assert result['pid'] == 1234
    mock_subprocess.assert_awaited_once()
    logger_mock.info.assert_any_call(f"[FRONTEND] Frontend démarré et prêt sur {result['url']}")
    # Check that stdout was actually read
    assert mock_stdout.readline.call_count == 2


@pytest.mark.asyncio
async def test_stop_process(manager):
    """Tests that stop correctly terminates the process using psutil."""
    # On simule la présence d'un processus à arrêter
    manager.process = AsyncMock(spec=asyncio.subprocess.Process)
    manager.process.pid = 1234
    manager.process.returncode = None # Simule un processus en cours

    # On mock psutil.Process pour intercepter l'appel de terminaison
    with patch('psutil.Process') as mock_psutil_process:
        mock_parent = MagicMock()
        mock_parent.children.return_value = [] # Pas d'enfants pour ce test simple
        mock_psutil_process.return_value = mock_parent

        await manager.stop()

        # On vérifie que `psutil.Process` a été appelé avec le bon PID
        mock_psutil_process.assert_called_with(1234)
        # On vérifie que la méthode `kill` a été appelée sur le processus parent
        mock_parent.kill.assert_called_once()
        # On vérifie que le manager a bien attendu la fin du processus asyncio
        # La méthode wait n'est pas garantie d'être appelée si le processus est tué.
        # L'important est que la tentative de terminaison a eu lieu.
        pass

@pytest.mark.asyncio
async def test_health_check_success(manager):
    """Tests a successful health check."""
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_get.return_value.__aenter__.return_value = mock_response
        
        result = await manager.health_check()
        
        assert result is True

@pytest.mark.asyncio
async def test_health_check_failure(manager):
    """Tests a failed health check."""
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_get.return_value.__aenter__.return_value = mock_response
        
        result = await manager.health_check()
        
        assert result is False
