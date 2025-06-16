# This file is intentionally left (almost) empty.
#
# The primary E2E test setup, including starting and stopping the web server,
# is handled by the `webapp_service` fixture in the parent `tests/e2e/conftest.py`.
#
# Previously, this file contained a conflicting `e2e_session_setup` fixture
# that attempted to manage its own web orchestrator and JVM instance, leading
# to fatal crashes (e.g., Windows access violation).
#
# By centralizing the service management in the parent conftest, we ensure that
# a single, clean instance of the backend is launched in a separate process,
# which is the correct approach for black-box E2E testing.
#
# Specific fixtures for Python E2E tests can be added here if needed,
# but they must not interfere with the server lifecycle.

import pytest

# Aucune fixture spécifique n'est définie ici pour le moment.
# Les tests utilisent la fixture 'webapp_service' du conftest.py parent.
