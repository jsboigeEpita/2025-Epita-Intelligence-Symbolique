import pytest
import os
import logging
import subprocess
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path

# On s'assure que le chemin est correct pour importer le manager
import sys
sys.path.insert(0, '.')

from project_core.webapp_from_scripts.frontend_manager import FrontendManager

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
    """Vérifie que 'npm install' est toujours exécuté."""
    manager.frontend_path = tmp_path
    (tmp_path / "package.json").touch()
    
    mock_process = MagicMock()
    mock_process.communicate.return_value = ('success', '') # text=True now returns strings
    mock_process.returncode = 0
    mock_popen.return_value = mock_process

    mock_env = {"PATH": os.environ.get("PATH", "")}
    await manager._ensure_dependencies(env=mock_env)

    is_windows = sys.platform == "win32"
    expected_cmd = 'npm install' if is_windows else ['npm', 'install']

    mock_popen.assert_called_with(
        expected_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=tmp_path,
        env=mock_env,
        shell=is_windows,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    manager.logger.info.assert_any_call("Lancement de 'npm install' pour garantir la fraîcheur des dépendances...")


@pytest.mark.asyncio
async def test_start_success(manager, tmp_path):
    """Tests the full successful start sequence with the new build logic."""
    manager.frontend_path = tmp_path
    build_path = tmp_path / "build"
    build_path.mkdir()
    (tmp_path / "package.json").touch()

    # Mock dependencies
    manager._ensure_dependencies = AsyncMock()
    manager._build_react_app = AsyncMock()  # On mocke l'étape de build
    manager._start_static_server = AsyncMock()
    # Le pid sera celui du thread, simulons-le
    manager.static_server_thread = MagicMock()
    manager.static_server_thread.ident = 5678
    manager._wait_for_health_check = AsyncMock(return_value=True)

    # Mock backend_manager for env setup
    manager.backend_manager = MagicMock()
    manager.backend_manager.host = 'localhost'
    manager.backend_manager.port = 5000
    
    manager.env = manager._get_frontend_env()

    result = await manager.start()

    assert result['success'] is True, f"start() a échoué, retour: {result.get('error', 'N/A')}"
    assert result['pid'] == 5678
    assert result['port'] == manager.port # Le port est maintenant géré directement par le manager
    
    manager._ensure_dependencies.assert_awaited_once()
    manager._build_react_app.assert_awaited_once() # On vérifie l'appel de la méthode de build
    manager._start_static_server.assert_awaited_once()
    manager._wait_for_health_check.assert_awaited_once()


@pytest.mark.asyncio
async def test_stop_process(manager):
    """Tests that stop correctly calls the static server shutdown."""
    manager._stop_static_server = AsyncMock()
    
    await manager.stop()

    manager._stop_static_server.assert_awaited_once()