import pytest
import os
import logging
import subprocess
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path

# On s'assure que le chemin est correct pour importer le manager
import sys
sys.path.insert(0, '.')

from scripts.apps.webapp.frontend_manager import FrontendManager

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
    assert manager.start_port == frontend_config['start_port']
    assert manager.process is None

@pytest.mark.asyncio
async def test_start_when_disabled(logger_mock):
    """Tests that start() returns immediately if not enabled."""
    config = {'enabled': False}
    manager = FrontendManager(config, logger_mock)
    result = await manager.start_with_failover()
    assert result['success'] is True
    assert result['error'] == 'Frontend désactivé'

@pytest.mark.asyncio
async def test_start_fails_if_path_not_found(manager, tmp_path):
    """Tests that start() fails if the frontend path does not exist."""
    manager.frontend_path = None
    result = await manager.start_with_failover()
    assert result['success'] is False
    assert "non trouvé" in result['error']

@pytest.mark.asyncio
async def test_start_fails_if_package_json_missing(manager, tmp_path):
    """Tests that start() fails if package.json is missing."""
    manager.frontend_path = tmp_path
    # La nouvelle logique vérifie les dépendances, on simule l'échec de _ensure_dependencies
    manager._ensure_dependencies = AsyncMock(return_value=False)
    result = await manager.start_with_failover()
    assert result['success'] is False
    assert "Échec de l'installation des dépendances" in result['error']

@pytest.mark.asyncio
@patch('subprocess.Popen')
async def test_ensure_dependencies_installs_if_needed(mock_popen, manager, tmp_path):
    """Vérifie que 'npm install' est exécuté si node_modules est manquant."""
    manager.frontend_path = tmp_path
    # Assurez-vous que node_modules n'existe pas
    # (tmp_path est vide par défaut)

    mock_process = MagicMock()
    mock_process.communicate.return_value = ('success', '')
    mock_process.returncode = 0
    mock_popen.return_value = mock_process

    result = await manager._ensure_dependencies()

    assert result is True
    mock_popen.assert_called_once()
    manager.logger.info.assert_any_call(f"Le dossier 'node_modules' est manquant. Lancement de 'npm install' dans {manager.frontend_path}...")


@pytest.mark.asyncio
async def test_start_success(manager):
    """Tests the full successful start sequence with the new failover logic."""
    # Mock des dépendances et des appels système
    manager._ensure_dependencies = AsyncMock(return_value=True)
    manager._is_port_occupied = AsyncMock(return_value=False)
    manager._start_on_port = AsyncMock(return_value={
        'success' : True,
        'url': f'http://localhost:{manager.start_port}',
        'port': manager.start_port,
        'pid': 1234
    })

    result = await manager.start_with_failover()

    assert result['success'] is True
    assert result['port'] == manager.start_port
    assert result['pid'] == 1234
    manager._ensure_dependencies.assert_awaited_once()
    manager._is_port_occupied.assert_awaited_once_with(manager.start_port)
    manager._start_on_port.assert_awaited_once_with(manager.start_port)


@pytest.mark.asyncio
async def test_stop_process(manager):
    """Tests that stop correctly terminates the process."""
    manager.process = MagicMock(spec=subprocess.Popen)
    manager.process.pid = 1234
    
    await manager.stop()

    manager.process.terminate.assert_called_once()