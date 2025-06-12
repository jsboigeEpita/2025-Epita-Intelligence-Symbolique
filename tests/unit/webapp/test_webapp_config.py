import pytest
import yaml
from unittest.mock import patch, MagicMock
from pathlib import Path

# On s'assure que le chemin est correct pour importer l'orchestrateur
import sys
sys.path.insert(0, '.')

from project_core.webapp_from_scripts.unified_web_orchestrator import UnifiedWebOrchestrator

# This patch will apply to all tests in this module
@pytest.fixture(autouse=True)
def mock_signal_handlers():
    with patch('project_core.webapp_from_scripts.unified_web_orchestrator.UnifiedWebOrchestrator._setup_signal_handlers') as mock_setup:
        yield mock_setup

def test_load_valid_config(webapp_config, test_config_path):
    """
    Tests loading a valid configuration file.
    """
    orchestrator = UnifiedWebOrchestrator(config_path=test_config_path)
    assert orchestrator.config is not None
    assert orchestrator.config['backend']['port'] == 8000
    assert orchestrator.config['frontend']['command'] == "npm start"
    assert orchestrator.config['playwright']['enabled'] is True

@patch('project_core.webapp_from_scripts.unified_web_orchestrator.CENTRAL_PORT_MANAGER_AVAILABLE', False)
def test_create_default_config_if_not_exists(tmp_path):
    """
    Tests that a default configuration is created if the file does not exist.
    The mock ensures we test the fallback mechanism.
    """
    config_path = tmp_path / "default_config.yml"
    assert not config_path.exists()

    orchestrator = UnifiedWebOrchestrator(config_path=str(config_path))
    
    assert config_path.exists()
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    assert config is not None
    assert config['webapp']['name'] == 'Argumentation Analysis Web App'
    assert config['backend']['start_port'] == 5003  # Default port without manager

@patch('project_core.webapp_from_scripts.unified_web_orchestrator.CENTRAL_PORT_MANAGER_AVAILABLE', True)
def test_create_default_config_with_port_manager(tmp_path, mocker):
    """
    Tests default config creation when the central port manager is available.
    """
    # Mock the port manager and its functions
    mock_port_manager = MagicMock()
    mock_port_manager.get_port.side_effect = lambda x: 8100 if x == 'backend' else 3100
    mock_port_manager.config = {'ports': {'backend': {'fallback': [8101, 8102]}}}

    mocker.patch('project_core.webapp_from_scripts.unified_web_orchestrator.get_port_manager', return_value=mock_port_manager)
    mocker.patch('project_core.webapp_from_scripts.unified_web_orchestrator.set_environment_variables')

    config_path = tmp_path / "default_config_with_pm.yml"
    orchestrator = UnifiedWebOrchestrator(config_path=str(config_path))
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    assert config['backend']['start_port'] == 8100
    assert config['frontend']['port'] == 3100
    assert config['backend']['fallback_ports'] == [8101, 8102]

def test_handle_invalid_yaml_config(tmp_path, capsys):
    """
    Tests that the orchestrator handles a corrupted YAML file by loading default config.
    """
    config_path = tmp_path / "invalid_config.yml"
    config_path.write_text("backend: { port: 8000\nfrontend: [") # Invalid YAML

    orchestrator = UnifiedWebOrchestrator(config_path=str(config_path))

    # Should fall back to default config without port manager
    assert orchestrator.config['backend']['start_port'] == 5003

    captured = capsys.readouterr()
    # In some CI environments, stderr might be captured instead of stdout
    assert f"Erreur chargement config {config_path}" in captured.out or f"Erreur chargement config {config_path}" in captured.err