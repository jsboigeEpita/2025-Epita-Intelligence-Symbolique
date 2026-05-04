"""Conftest for minimal_jpype_tweety tests.

All tests in this directory import jpype at module level.
Skip collection entirely when jpype is mocked by --disable-jvm-session
to avoid ModuleNotFoundError on 'jpype.types'.
"""

import sys
from unittest.mock import MagicMock

# Block collection when jpype is mocked (prevents import errors)
if isinstance(sys.modules.get("jpype"), MagicMock):
    collect_ignore_glob = ["test_*.py"]
