"""Conftest for jpype_tweety integration tests.

All tests in this directory require a real JVM.
Skip the entire directory when jpype is mocked by --disable-jvm-session.
"""

import sys
import pytest
from unittest.mock import MagicMock

_jpype_is_mocked = isinstance(sys.modules.get("jpype"), MagicMock)


def pytest_collection_modifyitems(config, items):
    """Skip all jpype_tweety tests when JVM is mocked."""
    if _jpype_is_mocked:
        skip_marker = pytest.mark.skip(
            reason="jpype is mocked by --disable-jvm-session"
        )
        for item in items:
            if "jpype_tweety" in str(item.fspath):
                item.add_marker(skip_marker)
