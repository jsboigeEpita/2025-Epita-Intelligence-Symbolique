import pytest
import sys
import psutil
import asyncio

sys.path.insert(0, '.')

from project_core.webapp_from_scripts.unified_web_orchestrator import UnifiedWebOrchestrator, WebAppStatus

@pytest.fixture
def integration_config(webapp_config, tmp_path):
    """Override the config for integration tests to use the fake backend."""
    config = webapp_config
    
    # Use a command list for robustness
    fake_backend_command_list = [sys.executable, 'tests/integration/webapp/fake_backend.py']
    
    config['backend']['command_list'] = fake_backend_command_list
    config['backend']['command'] = None # Ensure list is used
    config['backend']['health_endpoint'] = '/api/health'
    config['backend']['start_port'] = 9020  # Use a higher port to be safer
    config['backend']['fallback_ports'] = [9021, 9022]
    config['backend']['module'] = None
    
    config['frontend']['enabled'] = False
    config['playwright']['enabled'] = False
    
    return config

@pytest.fixture
def orchestrator(integration_config, test_config_path, mocker):
    """Fixture to get an orchestrator instance for integration tests."""
    mocker.patch('project_core.webapp_from_scripts.unified_web_orchestrator.UnifiedWebOrchestrator._setup_signal_handlers')
    
    import yaml
    with open(test_config_path, 'w') as f:
        yaml.dump(integration_config, f)
        
    return UnifiedWebOrchestrator(config_path=test_config_path)

@pytest.mark.asyncio
async def test_backend_lifecycle(orchestrator):
    """
    Tests the full start and stop lifecycle of the backend through the orchestrator.
    """
    pid_before_stop = None
    try:
        # Start the webapp (only backend enabled)
        success = await orchestrator.start_webapp()
        
        assert success is True
        assert orchestrator.app_info.status == WebAppStatus.RUNNING
        assert orchestrator.app_info.backend_pid is not None
        pid_before_stop = orchestrator.app_info.backend_pid
        
        # Check if the process actually exists
        assert psutil.pid_exists(pid_before_stop)
        proc = psutil.Process(pid_before_stop)
        assert 'fake_backend.py' in ' '.join(proc.cmdline())
        
        # Check that the port is in use
        assert orchestrator.app_info.backend_port in [9020, 9021, 9022]
        
    finally:
        # Ensure cleanup
        await orchestrator.stop_webapp()
        
        assert orchestrator.app_info.status == WebAppStatus.STOPPED
        assert orchestrator.app_info.backend_pid is None
        
        # Check that the process is actually gone
        if pid_before_stop:
            await asyncio.sleep(1) 
            assert not psutil.pid_exists(pid_before_stop)