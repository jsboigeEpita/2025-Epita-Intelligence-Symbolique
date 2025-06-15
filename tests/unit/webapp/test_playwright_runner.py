import pytest
import logging
import subprocess
import json
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path

# On s'assure que le chemin est correct pour importer le runner
import sys
sys.path.insert(0, '.')

from project_core.webapp_from_scripts.playwright_runner import PlaywrightRunner

@pytest.fixture
def playwright_config(webapp_config):
    """Provides a base playwright config."""
    return webapp_config['playwright']

@pytest.fixture
def logger_mock():
    """Mocks the logger."""
    return MagicMock(spec=logging.Logger)

@pytest.fixture
def runner(playwright_config, logger_mock, tmp_path):
    """Initializes PlaywrightRunner with a default config."""
    # Ensure artifact dirs are using a temporary path
    playwright_config['screenshots_dir'] = str(tmp_path / 'screenshots')
    playwright_config['traces_dir'] = str(tmp_path / 'traces')
    return PlaywrightRunner(playwright_config, logger_mock)

def test_initialization(runner, playwright_config):
    """Tests that the runner initializes correctly."""
    assert runner.enabled is True
    assert runner.browser == 'chromium'
    assert Path(runner.screenshots_dir).exists()
    assert Path(runner.traces_dir).exists()

@pytest.mark.asyncio
async def test_run_tests_when_disabled(logger_mock):
    """Tests that run_tests returns True if disabled."""
    config = {'enabled': False}
    runner = PlaywrightRunner(config, logger_mock)
    result = await runner.run_tests()
    assert result is True
    runner.logger.info.assert_called_with("Tests Playwright désactivés")

@pytest.mark.asyncio
async def test_prepare_test_environment(runner):
    """Tests that the environment variables are set correctly."""
    config = {
        'backend_url': 'http://backend:1234',
        'frontend_url': 'http://frontend:5678',
        'headless': False,
        'browser': 'firefox'
    }
    
    with patch('os.environ', {}) as mock_environ:
        await runner._prepare_test_environment(config)
        assert mock_environ['BACKEND_URL'] == 'http://backend:1234'
        assert mock_environ['FRONTEND_URL'] == 'http://frontend:5678'
        assert mock_environ['PLAYWRIGHT_BASE_URL'] == 'http://frontend:5678'
        assert mock_environ['HEADLESS'] == 'false'
        assert mock_environ['BROWSER'] == 'firefox'

@patch('sys.platform', 'win32')
@patch('os.getenv')
def test_build_pytest_command_windows(mock_getenv, runner):
    """Tests command building on Windows."""
    mock_getenv.return_value = 'C:/fake/node/home'
    with patch('pathlib.Path.is_file', return_value=True):
        cmd = runner._build_playwright_command_string(['tests/'], {'headless': True, 'browser': 'chromium'})
        assert 'npx.cmd' in cmd[0]
        assert '--headed' not in cmd
        assert '--project=chromium' in cmd
        assert 'tests/' in cmd

@patch('sys.platform', 'linux')
@patch('os.getenv')
def test_build_pytest_command_linux(mock_getenv, runner):
    """Tests command building on Linux."""
    mock_getenv.return_value = '/fake/node/home'
    with patch('pathlib.Path.is_file', return_value=True):
        cmd = runner._build_playwright_command_string(['tests/'], {'headless': False, 'browser': 'webkit'})
        assert 'npx' in cmd[0]
        assert '--headed' in cmd
        assert '--project=webkit' in cmd
        assert 'tests/' in cmd


@patch('subprocess.run')
async def test_run_tests_execution_flow(mock_subprocess_run, runner):
    """Tests the main execution flow of run_tests."""
    # Mock the subprocess call
    mock_result = MagicMock(spec=subprocess.CompletedProcess)
    mock_result.returncode = 0
    mock_result.stdout = "================= 1 passed in 5.00s =================="
    mock_result.stderr = ""
    mock_subprocess_run.return_value = mock_result

    # Mock internal methods to isolate run_tests
    runner._build_playwright_command_string = MagicMock(return_value=['fake_command'])
    runner._prepare_test_environment = AsyncMock()

    success = await runner.run_tests()

    assert success is True
    runner._prepare_test_environment.assert_called_once()
    runner._build_playwright_command_string.assert_called_once()
    mock_subprocess_run.assert_called_once_with(
        ['fake_command'], capture_output=True, text=True, encoding='utf-8',
        errors='replace', timeout=300, cwd=Path.cwd()
    )

    # Check if report was created
    report_file = Path(runner.traces_dir) / 'test_report.json'
    assert report_file.exists()
    with open(report_file, 'r') as f:
        report_data = json.load(f)
        assert report_data['success'] is True
        assert report_data['stats']['passed'] == 1