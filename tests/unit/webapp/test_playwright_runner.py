import pytest
import logging
import subprocess
from unittest.mock import MagicMock, patch, AsyncMock, ANY
from pathlib import Path

import sys
sys.path.insert(0, '.')

from project_core.webapp_from_scripts.playwright_runner import PlaywrightRunner

@pytest.fixture
def playwright_config(webapp_config, tmp_path):
    """Provides a base playwright config, ensuring temp dirs are used."""
    config = webapp_config['playwright']
    # Force 'enabled' for most tests and use temp paths
    config['enabled'] = True
    config['screenshots_dir'] = str(tmp_path / 'screenshots')
    config['traces_dir'] = str(tmp_path / 'traces')
    return config

@pytest.fixture
def logger_mock():
    """Mocks the logger."""
    return MagicMock(spec=logging.Logger)

@pytest.fixture
def runner(playwright_config, logger_mock):
    """Initializes PlaywrightRunner with a test-safe config."""
    return PlaywrightRunner(playwright_config, logger_mock)

def test_initialization(runner, playwright_config):
    """Tests that the runner initializes correctly."""
    assert runner.enabled is True
    assert runner.browser == 'chromium' # Default from the mock config
    assert Path(runner.screenshots_dir).exists()
    assert Path(runner.traces_dir).exists()

@pytest.mark.asyncio
async def test_run_tests_when_disabled(logger_mock):
    """Tests that run_tests returns True if the runner is disabled."""
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
        # HEADLESS et BROWSER sont passés en ligne de commande, pas en variable d'environnement
        # On vérifie juste qu'elles ne sont PAS dans l'environnement
        assert 'HEADLESS' not in mock_environ
        assert 'BROWSER' not in mock_environ

def test_build_command_for_python(runner):
    """Tests the command building logic for Python tests."""
    cmd = runner._build_command(
        'python',
        ['tests/my_test.py'],
        {'browser': 'chromium', 'headless': True},
        ['-k', 'my_keyword'],
        None
    )
    
    assert sys.executable in cmd
    assert '-m' in cmd
    assert 'pytest' in cmd
    assert 'tests/my_test.py' in cmd
    assert '--browser=chromium' in cmd
    assert '--headed' not in cmd
    assert '-k' in cmd
    assert 'my_keyword' in cmd

@patch('sys.platform', 'win32')
def test_build_command_for_js(runner):
    """Tests the command building logic for JavaScript tests."""
    with patch('os.getenv', return_value='C:/fake_node_home'):
        cmd = runner._build_command(
            'javascript',
            ['tests/js/my_test.spec.js'],
            {'browser': 'firefox', 'headless': False, 'timeout_ms': 5000},
            [],
            'my.config.js'
        )
        
        assert str(cmd[0]).endswith('npx.cmd')
        assert 'playwright' in cmd
        assert 'test' in cmd
        assert 'tests/js/my_test.spec.js' in cmd
        assert '--config=my.config.js' in cmd
        assert '--project=firefox' in cmd
        assert '--headed' in cmd
        assert '--timeout=5000' in cmd

@pytest.mark.asyncio
async def test_run_tests_happy_path(runner):
    """Tests the main execution flow of run_tests on a successful run."""
    runner._prepare_test_environment = AsyncMock()
    runner._build_command = MagicMock(return_value=['fake_command'])
    runner._execute_tests = AsyncMock(return_value=MagicMock(returncode=0))
    runner._analyze_results = AsyncMock(return_value=True)

    success = await runner.run_tests()

    assert success is True
    runner._prepare_test_environment.assert_called_once()
    runner._build_command.assert_called_once()
    runner._execute_tests.assert_called_once_with(['fake_command'], ANY)
    runner._analyze_results.assert_called_once()

@pytest.mark.asyncio
async def test_run_tests_execution_fails(runner):
    """Tests the main execution flow when the test subprocess fails."""
    runner._prepare_test_environment = AsyncMock()
    runner._build_command = MagicMock(return_value=['fake_command'])
    # Simulate a non-zero return code
    runner._execute_tests = AsyncMock(return_value=MagicMock(returncode=1))
    # _analyze_results should still be called to log the failure
    runner._analyze_results = AsyncMock(return_value=False) 

    success = await runner.run_tests()

    assert success is False
    runner._execute_tests.assert_called_once()
    runner._analyze_results.assert_called_once()