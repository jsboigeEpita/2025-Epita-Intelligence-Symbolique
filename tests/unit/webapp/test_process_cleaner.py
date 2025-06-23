import pytest
import pytest
pytest.skip("Le module 'scripts.apps.webapp.process_cleaner' a été supprimé ou refactorisé.", allow_module_level=True)

import logging
import psutil
from unittest.mock import MagicMock, patch, AsyncMock, call

# On s'assure que le chemin est correct pour importer le cleaner
import sys
sys.path.insert(0, '.')

from scripts.apps.webapp.process_cleaner import ProcessCleaner

@pytest.fixture
def logger_mock():
    """Mocks the logger."""
    return MagicMock(spec=logging.Logger)

@pytest.fixture
def cleaner(logger_mock):
    """Initializes ProcessCleaner."""
    return ProcessCleaner(logger_mock)

def create_mock_process(pid, name, cmdline, connections=None):
    """Helper function to create a mock psutil.Process."""
    proc = MagicMock(spec=psutil.Process)
    proc.pid = pid
    proc.info = {'pid': pid, 'name': name, 'cmdline': cmdline.split()}
    
    # Mock methods on the instance, not just the spec
    proc.name.return_value = name
    proc.cmdline.return_value = cmdline.split()
    
    if connections:
        mock_conns = []
        for lport in connections:
            conn = MagicMock()
            conn.laddr.port = lport
            conn.status = psutil.CONN_LISTEN
            mock_conns.append(conn)
        proc.connections.return_value = mock_conns
    else:
        proc.connections.return_value = []
        
    proc.is_running.return_value = True
    proc.terminate = MagicMock()
    proc.kill = MagicMock()
    proc.wait = MagicMock()
    
    return proc

@patch('psutil.process_iter')
def test_find_webapp_processes(mock_process_iter, cleaner):
    """
    Tests finding processes by command line and by port.
    """
    # Mock processes
    p1 = create_mock_process(101, 'python.exe', 'python scripts/app.py', connections=[5003])
    p2 = create_mock_process(102, 'node.exe', 'node node_modules/react-scripts/start.js')
    p3 = create_mock_process(103, 'explorer.exe', 'C:\\Windows\\explorer.exe') # Not a webapp process
    p4 = create_mock_process(104, 'python.exe', 'python some_other_script.py', connections=[8080]) # Not a webapp port

    mock_process_iter.return_value = [p1, p2, p3, p4]

    found_processes = cleaner._find_webapp_processes()
    found_pids = {p.pid for p in found_processes}

    assert len(found_processes) == 2
    assert {101, 102}.issubset(found_pids)
    assert 103 not in found_pids
    assert 104 not in found_pids


@pytest.mark.asyncio
async def test_terminate_processes_gracefully(cleaner):
    """
    Tests the graceful termination sequence.
    """
    p1 = create_mock_process(201, 'python.exe', 'python app.py')
    p2 = create_mock_process(202, 'node.exe', 'npm start')
    
    # After terminate is called, p1 stops, p2 keeps running
    p1.is_running.return_value = False
    p2.is_running.return_value = True 

    with patch('time.sleep'): # Avoid actual sleep
        await cleaner._terminate_processes_gracefully([p1, p2])

    p1.terminate.assert_called_once()
    p2.terminate.assert_called_once()
    cleaner.logger.warning.assert_called_with("1 processus encore actifs")

@pytest.mark.asyncio
async def test_force_kill_remaining_processes(cleaner):
    """
    Tests the force kill mechanism.
    """
    p_recalcitrant = create_mock_process(301, 'node.exe', 'npm start')
    
    # Mock find to return the stubborn process
    cleaner._find_webapp_processes = MagicMock(return_value=[p_recalcitrant])
    
    await cleaner._force_kill_remaining_processes()

    p_recalcitrant.kill.assert_called_once()
    cleaner.logger.warning.assert_called_with("KILL forcé sur PID 301")


@pytest.mark.asyncio
async def test_cleanup_temp_files(cleaner, tmp_path):
    """
    Tests the cleanup of temporary files.
    """
    # Create some dummy files to be cleaned
    (tmp_path / 'backend_info.json').touch()
    (tmp_path / 'some_other_file.txt').touch()

    # The cleaner works from the current directory, so we patch Path
    with patch('project_core.core_from_scripts.process_cleaner.Path') as mock_path:
        # Configure the mock to return paths within tmp_path
        def path_side_effect(p):
            return tmp_path / p
        mock_path.side_effect = path_side_effect
        
        await cleaner._cleanup_temp_files()

    assert not (tmp_path / 'backend_info.json').exists()
    assert (tmp_path / 'some_other_file.txt').exists() # Should not be deleted
    cleaner.logger.info.assert_any_call("Supprimé: backend_info.json")