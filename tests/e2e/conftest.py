import pytest
from typing import Generator, Tuple

# La fonction pytest_addoption est supprimée pour éviter les conflits avec les plugins
# qui définissent déjà --backend-url et --frontend-url.

@pytest.fixture(scope="session")
def backend_url(request: pytest.FixtureRequest) -> str:
    """Fixture to get the backend URL from command-line options."""
    return request.config.getoption("--backend-url")

@pytest.fixture(scope="session")
def frontend_url(request: pytest.FixtureRequest) -> str:
    """Fixture to get the frontend URL from command-line options."""
    return request.config.getoption("--frontend-url")

# NOTE: The old 'webapp_service' fixture has been removed.
# The unified_web_orchestrator.py is now the single source of truth
# for starting, managing, and stopping the web application during tests.
# The orchestrator passes the correct URLs to pytest via the command line.
