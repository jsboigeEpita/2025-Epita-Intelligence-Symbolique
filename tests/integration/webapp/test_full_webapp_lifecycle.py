import pytest
import sys
import psutil
import asyncio

sys.path.insert(0, '.')

from argumentation_analysis.webapp.orchestrator import UnifiedWebOrchestrator, WebAppStatus

@pytest.fixture
def integration_config(webapp_config, tmp_path):
    """Override the config for integration tests to use the real backend."""
    config = webapp_config
    
    # The command_list is now inherited from the orchestrator's default config,
    # which launches the real uvicorn backend.
    
    # config['backend']['command_list'] = fake_backend_command_list
    # config['backend']['command'] = None # Ensure list is used
    config['backend']['health_endpoint'] = '/api/health'
    config['backend']['start_port'] = 9020  # Use a higher port to be safer
    config['backend']['fallback_ports'] = [9021, 9022]
    config['backend']['timeout_seconds'] = 20 # > 15s initial wait
    # config['backend']['module'] = None # Let the orchestrator use the default real module
    
    config['frontend']['enabled'] = False
    config['playwright']['enabled'] = False
    
    return config

@pytest.fixture
def orchestrator(integration_config, test_config_path, mocker):
    """Fixture to get an orchestrator instance for integration tests."""
    import argparse
    import yaml
    
    mocker.patch('argumentation_analysis.webapp.orchestrator.UnifiedWebOrchestrator._setup_signal_handlers')

    with open(test_config_path, 'w') as f:
        yaml.dump(integration_config, f)

    # Create a mock args object that mirrors the one from command line parsing
    mock_args = argparse.Namespace(
        config=str(test_config_path),
        log_level='DEBUG',
        headless=True,
        visible=False,
        timeout=5, # 5 minutes for integration tests
        no_trace=True # Disable trace generation for speed
    )
        
    return UnifiedWebOrchestrator(args=mock_args)

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
        # Check for 'uvicorn' which indicates the real backend is running
        assert 'uvicorn' in ' '.join(proc.cmdline())
        
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