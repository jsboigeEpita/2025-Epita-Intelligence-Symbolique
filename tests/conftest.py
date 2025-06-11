import pytest
import yaml
import os
from unittest.mock import MagicMock

@pytest.fixture(scope="session")
def test_config_path(tmp_path_factory):
    """Creates a temporary config file for the session."""
    config_content = """
backend:
  path: "path/to/backend"
  command: "python backend.py"
  start_port: 8000
  port: 8000 
  max_retries: 3
  retry_delay: 5
  fallback_ports: [8001, 8002, 8003] # Fix: Key was 'ports_failover'

frontend:
  path: "path/to/frontend"
  command: "npm start"
  port: 3000
  enabled: true
  env:
    BROWSER: "none"

playwright:
  enabled: true
  command: "pytest --headed"
  path: "path/to/playwright_tests"
  port_retries: 5
  port_retry_delay: 2
  browser: 'chromium'

process_cleaner:
  enabled: true
  ports: [8000, 3000, 9222]
  processes: ["node", "python"]
"""
    config_file = tmp_path_factory.mktemp("config") / "test_config.yml"
    config_file.write_text(config_content)
    return str(config_file)

@pytest.fixture(scope="session")
def webapp_config(test_config_path):
    """Loads a test webapp configuration from the temporary YAML file."""
    with open(test_config_path, "r") as f:
        config = yaml.safe_load(f)
    return config

@pytest.fixture
def mock_popen(mocker):
    """Mock subprocess.Popen to prevent actual process creation."""
    mock = mocker.patch("subprocess.Popen")
    popen_instance = MagicMock()
    popen_instance.pid = 1234
    popen_instance.poll.return_value = None  # Process is running
    popen_instance.returncode = None
    popen_instance.terminate.return_value = None
    popen_instance.kill.return_value = None
    popen_instance.wait.return_value = None
    mock.return_value = popen_instance
    return mock