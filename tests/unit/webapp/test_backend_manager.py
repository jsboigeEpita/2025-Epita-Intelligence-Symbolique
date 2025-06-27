import pytest
import asyncio
import logging
import time
import subprocess
import aiohttp
from unittest.mock import MagicMock, patch, AsyncMock

# Correction du chemin pour inclure la racine du projet, nécessaire pour les tests
import sys
sys.path.insert(0, '.')

from scripts.apps.webapp.backend_manager import BackendManager

# Fixtures existantes (non modifiées)
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
    # Le chemin du script d'activation est maintenant forcé, on peut le mocker si nécessaire
    # ou laisser la valeur par défaut du manager. Pour ce test, pas besoin de le mocker.
    return BackendManager(backend_config, logger_mock)

def test_initialization(manager, backend_config):
    """Tests the constructor and basic attribute assignments."""
    assert manager.config == backend_config
    assert manager.module == backend_config['module']

# --- Tests de la logique de démarrage (`start_with_failover` et `_start_on_port`) ---

@pytest.mark.asyncio
@patch('subprocess.Popen')
async def test_start_success(mock_popen, manager):
    """Tests a successful start call, mocking the internal _wait_for_backend."""
    # `_wait_for_backend` retourne maintenant un simple booléen.
    manager._get_conda_env_python_executable = MagicMock(return_value="/fake/python") # Isoler du système
    manager._wait_for_backend = AsyncMock(return_value=True)
    manager._is_port_occupied = AsyncMock(return_value=False)
    manager._save_backend_info = AsyncMock()

    # Le PID vient de l'instance Popen mockée.
    mock_process = MagicMock()
    mock_process.pid = 1234
    mock_popen.return_value = mock_process
    
    # Le port est passé ici pour simplifier le test.
    result = await manager.start_with_failover(port_override=5003)

    assert result['success'] is True
    assert result['port'] == 5003
    assert result['pid'] == 1234
    assert result['url'] == "http://127.0.0.1:5003"
    
    mock_popen.assert_called_once()
    manager._wait_for_backend.assert_awaited_once_with(5003)
    manager._save_backend_info.assert_called_once()

@pytest.mark.asyncio
async def test_start_all_ports_occupied(manager):
    """Tests that start_with_failover fails if all attempted ports are occupied."""
    manager._is_port_occupied = AsyncMock(return_value=True)
    
    result = await manager.start_with_failover()
    
    assert result['success'] is False
    assert "Impossible de démarrer le backend après" in result['error']
    # Vérifie que tous les ports ont été testés
    assert manager._is_port_occupied.call_count == manager.max_attempts

@pytest.mark.asyncio
@patch('subprocess.Popen')
async def test_start_fails_if_wait_fails(mock_popen, manager):
    """Tests that start fails if the internal _wait_for_backend returns False."""
    manager._wait_for_backend = AsyncMock(return_value=False)
    manager._is_port_occupied = AsyncMock(return_value=False)

    # Note: _cleanup_failed_process n'existe plus, la logique est dans _wait_for_backend
    mock_popen.return_value = MagicMock(pid=1235)

    result = await manager.start_with_failover()

    assert result['success'] is False
    # L'erreur est maintenant plus générique, venant de la boucle de failover.
    assert "Impossible de démarrer le backend après" in result['error']

# --- Tests de la logique d'attente (`_wait_for_backend`) ---

@pytest.mark.asyncio
async def test_wait_for_backend_process_dies(manager):
    """Tests _wait_for_backend returns False when the process terminates prematurely."""
    manager.process = MagicMock()
    manager.process.poll.return_value = 1  # Simule la fin du processus
    manager.process.returncode = 1
    
    result = await manager._wait_for_backend(port=manager.start_port)
    
    assert result is False
    manager.logger.error.assert_called_with(f"Processus backend terminé prématurément (code: {manager.process.returncode}). Voir logs pour détails.")

@pytest.mark.asyncio
@patch('aiohttp.ClientSession.get')
async def test_wait_for_backend_health_check_ok(mock_get, manager):
    """Tests _wait_for_backend returns True with a successful health check."""
    manager.process = MagicMock()
    manager.process.poll.return_value = None  # Processus en cours

    # Simule une réponse HTTP 200 OK.
    mock_response = AsyncMock()
    mock_response.status = 200
    # aenter pour le contexte `async with`
    mock_get.return_value.__aenter__.return_value = mock_response

    result = await manager._wait_for_backend(port=8000)

    assert result is True
    mock_get.assert_called_once()

@pytest.mark.asyncio
@patch('scripts.apps.webapp.backend_manager.time.time')
async def test_wait_for_backend_global_timeout(mock_time, manager):
    """Tests that _wait_for_backend returns False when the global timeout is reached."""
    manager.process = MagicMock()
    manager.process.poll.return_value = None  # Processus en cours

    # Simuler l'écoulement du temps pour dépasser le timeout global.
    # time.time() sera appelé une fois pour start_time, puis à chaque itération de la boucle.
    # Nous simulons l'écoulement du temps en fournissant une fonction comme side_effect pour
    # rendre le mock robuste contre un nombre d'appels variable.
    time_sequence = [
        1000.0,  # 1. Appel pour initialiser start_time
        1001.0,  # 2. Appel dans la boucle while (continue)
        1000.0 + manager.timeout_seconds + 1.0  # 3. Appel qui termine la boucle
    ]
    def time_gen():
        yield from time_sequence
        while True: # Pour tous les appels suivants, retourner la dernière valeur
            yield time_sequence[-1]
    
    time_iterator = time_gen()
    mock_time.side_effect = lambda: next(time_iterator)
    
    # Faire échouer les health checks
    with patch('aiohttp.ClientSession.get', side_effect=aiohttp.ClientConnectorError(None, MagicMock())):
        with patch('asyncio.sleep', new_callable=AsyncMock): # Empêche l'attente réelle
            result = await manager._wait_for_backend(port=8000)

    assert result is False
    manager.logger.error.assert_any_call(f"Timeout global atteint ({manager.timeout_seconds}s) - Backend non accessible sur http://127.0.0.1:8000/api/health")

# --- Test de la logique d'arrêt (`stop`) ---

@pytest.mark.asyncio
async def test_stop_process_terminates_gracefully(manager):
    """Tests that stop() correctly tries to terminate and then waits for the process."""
    mock_process = MagicMock()
    manager.process = mock_process
    manager.pid = 1234
    
    # Simuler que wait() réussit sans Timeout
    mock_process.wait.return_value = 0

    await manager.stop()
    
    mock_process.terminate.assert_called_once()
    mock_process.wait.assert_called_once_with(timeout=5)
    mock_process.kill.assert_not_called() # Ne doit pas être appelé si wait réussit
    
    assert manager.process is None
    assert manager.pid is None

@pytest.mark.asyncio
async def test_stop_process_forces_kill_on_timeout(manager):
    """Tests that stop() kills the process if terminate + wait fails."""
    mock_process = MagicMock()
    manager.process = mock_process
    manager.pid = 1234
    
    # Simuler que wait() lève une exception de timeout
    mock_process.wait.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=5)

    await manager.stop()
    
    mock_process.terminate.assert_called_once()
    # Vérifier les deux appels à wait()
    assert mock_process.wait.call_count == 2
    # Le premier appel est avec un timeout
    mock_process.wait.assert_any_call(timeout=5)
    # Le second appel (après kill) est sans argument
    mock_process.wait.assert_any_call()
    
    mock_process.kill.assert_called_once() # Doit être appelé après le timeout de wait
    
    assert manager.process is None
    assert manager.pid is None