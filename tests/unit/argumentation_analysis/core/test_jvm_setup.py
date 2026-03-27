# -*- coding: utf-8 -*-
"""
Tests unitaires pour le module jvm_setup.py.
Issue #253: JVM startup timeout and asyncio.Lock for TweetyBridge
"""

import pytest
from unittest.mock import patch, MagicMock
from concurrent.futures import TimeoutError as FuturesTimeoutError


class TestJVMStartupTimeout:
    """Tests pour le mécanisme de timeout au démarrage de la JVM."""

    def test_default_timeout_value(self):
        """Vérifie que le timeout par défaut est de 60 secondes."""
        from argumentation_analysis.core.jvm_setup import DEFAULT_JVM_STARTUP_TIMEOUT_SECONDS
        assert DEFAULT_JVM_STARTUP_TIMEOUT_SECONDS == 60

    def test_timeout_exception_is_timeout_error_subclass(self):
        """Vérifie que JVMStartupTimeoutError est une sous-classe de TimeoutError."""
        from argumentation_analysis.core.jvm_setup import JVMStartupTimeoutError
        assert issubclass(JVMStartupTimeoutError, TimeoutError)

    def test_timeout_exception_message(self):
        """Vérifie que l'exception contient le message attendu."""
        from argumentation_analysis.core.jvm_setup import JVMStartupTimeoutError
        msg = "JVM startup exceeded timeout of 30 seconds"
        exc = JVMStartupTimeoutError(msg)
        assert msg in str(exc)

    def test_timeout_exception_can_be_caught_as_timeout_error(self):
        """Vérifie que JVMStartupTimeoutError peut être attrapée comme TimeoutError."""
        from argumentation_analysis.core.jvm_setup import JVMStartupTimeoutError

        try:
            raise JVMStartupTimeoutError("Test timeout")
        except TimeoutError as e:
            # Devrait attraper l'exception car c'est une sous-classe
            assert "Test timeout" in str(e)
        else:
            pytest.fail("JVMStartupTimeoutError should be catchable as TimeoutError")
