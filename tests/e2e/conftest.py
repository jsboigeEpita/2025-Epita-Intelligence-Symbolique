import pytest

# Note: The pytest_addoption function is defined in the root conftest.py
# This local conftest.py provides fixtures that correctly consume the command-line options.

@pytest.fixture(scope="session")
def backend_url(request) -> str:
    """Fixture to get the backend URL from the --backend-url pytest option."""
    url = request.config.getoption("--backend-url")
    if not url:
        pytest.fail("The --backend-url command-line option is not defined. The test runner must provide it.")
    return url

@pytest.fixture(scope="session")
def frontend_url(request) -> str:
    """Fixture to get the frontend URL from the --frontend-url pytest option."""
    url = request.config.getoption("--frontend-url")
    if not url:
        pytest.fail("The --frontend-url command-line option is not defined. The test runner must provide it.")
    return url

# NOTE: The old 'webapp_service' fixture has been removed.
# The unified_web_orchestrator.py is now the single source of truth
# for starting, managing, and stopping the web application during tests.
# The orchestrator passes the correct URLs to pytest via the command line.
