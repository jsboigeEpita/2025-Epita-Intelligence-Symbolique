#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stabilization conftest for tests/validation_sherlock_watson/

This conftest addresses several sources of flakiness in the Sherlock-Watson
validation test suite:

1. API rate limiting: LLM API calls (OpenAI) can hit rate limits when tests
   run back-to-back without pauses. The `rate_limit` fixture adds a cooldown.

2. Missing timeouts: Async workflow tests can hang indefinitely when the LLM
   is slow or unresponsive. The `workflow_timeout` fixture wraps coroutines
   with asyncio.wait_for.

3. Silent skips: Some tests use `skipif` at the module level without an
   explicit pytest marker, making them invisible in test reports. The
   `api_key_required` fixture surfaces this clearly at session scope.

4. JSON serialization: Semantic Kernel ChatMessageContent objects are not
   JSON-serializable. The `safe_json_serialize` fixture provides a recursive
   cleaner that handles SK types gracefully.

5. State leakage: CluedoOracleState can carry state between tests via module-
   level imports or singleton patterns. The `clean_oracle_state` fixture
   provides a factory that produces fresh instances.
"""

import asyncio
import logging
import os
import time
from typing import Any, Coroutine, Optional

import pytest

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. Rate limiting between LLM API calls
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True, scope="function")
def rate_limit():
    """
    Adds a 2-second cooldown AFTER each test function to avoid hitting
    OpenAI/OpenRouter rate limits when tests run in sequence.

    This is autouse so every test in this directory benefits automatically.
    The sleep happens in the teardown phase (after yield), so it does not
    inflate the measured test duration reported by pytest.
    """
    # Setup: nothing to do
    yield
    # Teardown: pause before the next test starts
    time.sleep(2)


# ---------------------------------------------------------------------------
# 2. Session-level API key check
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True, scope="session")
def api_key_required():
    """
    At session start, checks whether OPENAI_API_KEY is set in the environment.

    If the key is missing, the entire validation_sherlock_watson module is
    skipped with a clear, explicit message. This avoids silent skipif decorators
    scattered across individual test files and makes the skip reason visible
    in CI logs.

    NOTE: Tests that genuinely work without an API key (pure unit tests on
    data structures like CluedoDataset, OracleResponse, etc.) should override
    this by NOT depending on LLM calls. Those tests will still be collected
    but the non-LLM ones will pass even when this fixture triggers a skip,
    because this fixture only emits a WARNING -- the actual skip decision is
    left to individual tests that import LLM-dependent code.

    UPDATE: After review, the tests in this directory are a mix of pure-unit
    and LLM-dependent tests. We therefore only log a warning rather than
    skipping the entire session. Individual tests that need the key should
    use the pytestmark pattern or the `require_openai_api_key` fixture below.
    """
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        logger.warning(
            "[validation_sherlock_watson] OPENAI_API_KEY is not set. "
            "Tests requiring LLM calls will be skipped individually. "
            "Set OPENAI_API_KEY in your environment or .env file to run "
            "the full validation suite."
        )
    else:
        logger.info(
            "[validation_sherlock_watson] OPENAI_API_KEY is available. "
            "LLM-dependent validation tests will run."
        )
    yield


@pytest.fixture(scope="function")
def require_openai_api_key():
    """
    Explicit opt-in fixture for tests that REQUIRE a real OpenAI API key.

    Usage in a test:
        def test_something(require_openai_api_key):
            ...

    If the key is not set, the test is skipped with a clear reason.
    """
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not set -- skipping LLM-dependent validation test")


# ---------------------------------------------------------------------------
# 3. Async workflow timeout wrapper
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def workflow_timeout():
    """
    Provides an async wrapper that applies asyncio.wait_for with a default
    timeout of 120 seconds to any coroutine.

    Usage in a test:
        async def test_my_workflow(workflow_timeout):
            result = await workflow_timeout(some_async_function(), timeout=60)
            assert result is not None

    If the coroutine does not complete within the timeout, asyncio.TimeoutError
    is raised, which pytest captures as a clear test failure rather than an
    indefinite hang.

    Args (of the returned callable):
        coro: The coroutine to execute.
        timeout: Timeout in seconds (default: 120).

    Returns:
        The result of the coroutine.

    Raises:
        asyncio.TimeoutError: If the coroutine exceeds the timeout.
    """

    async def _run_with_timeout(
        coro: Coroutine,
        timeout: float = 120.0,
    ) -> Any:
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            logger.error(
                f"[workflow_timeout] Coroutine exceeded {timeout}s timeout. "
                f"This typically indicates an LLM call that is hanging or "
                f"a workflow that entered an infinite loop."
            )
            raise

    return _run_with_timeout


# ---------------------------------------------------------------------------
# 4. Clean CluedoOracleState factory
# ---------------------------------------------------------------------------

# Default Cluedo game elements used across the validation tests.
_DEFAULT_ELEMENTS_JEU = {
    "suspects": [
        "Colonel Moutarde",
        "Professeur Violet",
        "Mademoiselle Rose",
        "Madame Pervenche",
        "Monsieur Olive",
        "Madame Leblanc",
    ],
    "armes": [
        "Poignard",
        "Chandelier",
        "Revolver",
        "Corde",
        "Clef Anglaise",
        "Matraque",
    ],
    "lieux": [
        "Cuisine",
        "Salon",
        "Bureau",
        "Bibliotheque",
        "Salle de Billard",
        "Jardin d'Hiver",
        "Hall",
        "Salle a Manger",
        "Veranda",
    ],
}


@pytest.fixture(scope="function")
def clean_oracle_state():
    """
    Factory fixture that produces a fresh CluedoOracleState for each test.

    This ensures no state leaks between tests -- each invocation creates a
    brand new instance with default game elements. The factory pattern allows
    tests to customize parameters while still getting a clean baseline.

    Usage in a test:
        def test_oracle(clean_oracle_state):
            state = clean_oracle_state()
            assert state is not None

        def test_custom(clean_oracle_state):
            state = clean_oracle_state(
                nom_enquete="Custom",
                oracle_strategy="cooperative",
            )
    """

    def _factory(
        nom_enquete: str = "TestEnquete",
        elements_jeu: Optional[dict] = None,
        description_cas: str = "Test case description",
        initial_context: Optional[Any] = None,
        oracle_strategy: str = "balanced",
        **kwargs,
    ):
        try:
            from argumentation_analysis.core.cluedo_oracle_state import (
                CluedoOracleState,
            )
        except ImportError:
            pytest.skip(
                "Cannot import CluedoOracleState -- "
                "argumentation_analysis package not available"
            )

        return CluedoOracleState(
            nom_enquete_cluedo=nom_enquete,
            elements_jeu_cluedo=elements_jeu or _DEFAULT_ELEMENTS_JEU.copy(),
            description_cas=description_cas,
            initial_context=initial_context or {"context": "test"},
            oracle_strategy=oracle_strategy,
            **kwargs,
        )

    return _factory


# ---------------------------------------------------------------------------
# 5. Safe JSON serializer for SK objects
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def safe_json_serialize():
    """
    Provides a helper function that recursively cleans Semantic Kernel objects
    (and other non-serializable types) so that json.dumps succeeds.

    This addresses a common flakiness source: tests that build reports from
    workflow results containing ChatMessageContent, AuthorRole, or other SK
    types that are not natively JSON-serializable.

    Usage in a test:
        def test_report(safe_json_serialize):
            data = run_workflow()  # may contain SK objects
            clean = safe_json_serialize(data)
            json_str = json.dumps(clean)  # guaranteed to work
            assert isinstance(json_str, str)

    The function handles:
    - ChatMessageContent -> {"role": str, "content": str, "name": str|None}
    - AuthorRole / enum types -> str(value)
    - ChatHistory -> list of cleaned messages
    - property objects -> str representation
    - datetime objects -> ISO format string
    - Arbitrary objects with __dict__ -> "<ClassName object>"
    - Deque / set / frozenset -> list
    - bytes -> base64 or repr
    """

    def _clean(obj: Any) -> Any:
        """Recursively convert obj into a JSON-serializable structure."""
        if obj is None:
            return None

        if isinstance(obj, (str, int, float, bool)):
            return obj

        # Handle enum types (AuthorRole, QueryType, etc.)
        try:
            import enum

            if isinstance(obj, enum.Enum):
                return obj.value
        except Exception:
            pass

        # Handle SK ChatMessageContent
        try:
            from semantic_kernel.contents import ChatMessageContent

            if isinstance(obj, ChatMessageContent):
                return {
                    "role": (
                        str(obj.role.value)
                        if hasattr(obj.role, "value")
                        else str(obj.role)
                    ),
                    "content": str(obj.content) if obj.content else "",
                    "name": (
                        str(obj.name) if hasattr(obj, "name") and obj.name else None
                    ),
                }
        except ImportError:
            pass

        # Handle SK ChatHistory
        try:
            from semantic_kernel.contents import ChatHistory

            if isinstance(obj, ChatHistory):
                return [_clean(msg) for msg in obj.messages]
        except (ImportError, AttributeError):
            pass

        # Handle property objects (surprisingly common in SK results)
        if isinstance(obj, property):
            return "<property>"

        # Handle datetime
        try:
            from datetime import datetime, date

            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
        except Exception:
            pass

        # Handle dict
        if isinstance(obj, dict):
            cleaned = {}
            for k, v in obj.items():
                # Clean keys too -- SK sometimes uses non-string keys
                clean_key = str(k) if not isinstance(k, (str, int, float, bool)) else k
                cleaned[clean_key] = _clean(v)
            return cleaned

        # Handle list, tuple, deque, set, frozenset
        if isinstance(obj, (list, tuple)):
            return [_clean(item) for item in obj]

        try:
            from collections import deque

            if isinstance(obj, deque):
                return [_clean(item) for item in obj]
        except ImportError:
            pass

        if isinstance(obj, (set, frozenset)):
            return [_clean(item) for item in sorted(obj, key=str)]

        # Handle bytes
        if isinstance(obj, bytes):
            try:
                return obj.decode("utf-8")
            except UnicodeDecodeError:
                return repr(obj)

        # Fallback: objects with __dict__ get a placeholder
        if hasattr(obj, "__dict__") and not isinstance(obj, type):
            return f"<{obj.__class__.__name__} object>"

        # Last resort: str()
        try:
            return str(obj)
        except Exception:
            return "<unserializable>"

    return _clean
