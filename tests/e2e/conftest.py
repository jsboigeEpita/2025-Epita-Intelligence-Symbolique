import pytest
import os
from typing import Generator, Tuple

# La fonction pytest_addoption est supprimée pour éviter les conflits avec les plugins
# qui définissent déjà --backend-url et --frontend-url.

@pytest.fixture(scope="session")
def backend_url() -> str:
    """Fixture to get the backend URL from the BACKEND_URL environment variable."""
    url = os.environ.get("BACKEND_URL")
    if not url:
        pytest.fail("La variable d'environnement BACKEND_URL n'est pas définie. L'orchestrateur doit la fournir.")
    return url

@pytest.fixture(scope="session")
def frontend_url() -> str:
    """Fixture to get the frontend URL from the BASE_URL or FRONTEND_URL environment variable."""
    # BASE_URL est souvent utilisé comme fallback générique pour le frontend.
    url = os.environ.get("BASE_URL") or os.environ.get("FRONTEND_URL")
    if not url:
        pytest.fail("Les variables d'environnement BASE_URL ou FRONTEND_URL ne sont pas définies. L'orchestrateur doit les fournir.")
    return url

# NOTE: The old 'webapp_service' fixture has been removed.
# The unified_web_orchestrator.py is now the single source of truth
# for starting, managing, and stopping the web application during tests.
# The orchestrator passes the correct URLs to pytest via the command line.
