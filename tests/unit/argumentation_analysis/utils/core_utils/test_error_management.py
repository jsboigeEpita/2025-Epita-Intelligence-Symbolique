# tests/unit/argumentation_analysis/utils/core_utils/test_error_management.py
"""Tests for StateManager and ErrorRecoveryManager."""

import pytest

from argumentation_analysis.core.utils.error_management import (
    StateManager,
    ErrorRecoveryManager,
)

# ── StateManager ──


class TestStateManager:
    @pytest.fixture
    def sm(self):
        return StateManager()

    def test_init_state(self, sm):
        assert sm.state["tasks"] == []
        assert sm.state["errors"] == []
        assert sm.state["conclusion"] is None

    def test_add_error(self, sm):
        err = sm.add_error("network", "Connection timeout", "Agent1")
        assert err["type"] == "network"
        assert err["message"] == "Connection timeout"
        assert err["agent"] == "Agent1"
        assert err["recoverable"] is True
        assert "timestamp" in err

    def test_add_error_unrecoverable(self, sm):
        err = sm.add_error("fatal", "crash", recoverable=False)
        assert err["recoverable"] is False

    def test_add_error_no_agent(self, sm):
        err = sm.add_error("validation", "missing field")
        assert err["agent"] is None

    def test_get_errors(self, sm):
        sm.add_error("network", "err1")
        sm.add_error("service", "err2")
        assert len(sm.get_errors()) == 2

    def test_get_errors_empty(self, sm):
        assert sm.get_errors() == []

    def test_get_recoverable_errors(self, sm):
        sm.add_error("network", "err1", recoverable=True)
        sm.add_error("fatal", "err2", recoverable=False)
        recoverable = sm.get_recoverable_errors()
        assert len(recoverable) == 1
        assert recoverable[0]["type"] == "network"

    def test_get_unrecoverable_errors(self, sm):
        sm.add_error("network", "err1", recoverable=True)
        sm.add_error("fatal", "err2", recoverable=False)
        unrecoverable = sm.get_unrecoverable_errors()
        assert len(unrecoverable) == 1
        assert unrecoverable[0]["type"] == "fatal"

    def test_clear_errors(self, sm):
        sm.add_error("network", "err1")
        sm.add_error("service", "err2")
        sm.clear_errors()
        assert sm.get_errors() == []

    def test_mark_error_as_handled(self, sm):
        sm.add_error("network", "err1")
        result = sm.mark_error_as_handled(0)
        assert result is True
        assert sm.get_errors()[0]["handled"] is True

    def test_mark_error_invalid_index_negative(self, sm):
        sm.add_error("network", "err1")
        assert sm.mark_error_as_handled(-1) is False

    def test_mark_error_invalid_index_too_high(self, sm):
        sm.add_error("network", "err1")
        assert sm.mark_error_as_handled(5) is False

    def test_mark_error_empty_list(self, sm):
        assert sm.mark_error_as_handled(0) is False

    def test_multiple_errors_mark_specific(self, sm):
        sm.add_error("network", "err1")
        sm.add_error("service", "err2")
        sm.mark_error_as_handled(1)
        assert "handled" not in sm.get_errors()[0]
        assert sm.get_errors()[1]["handled"] is True


# ── ErrorRecoveryManager ──


class TestErrorRecoveryManager:
    @pytest.fixture
    def sm(self):
        return StateManager()

    @pytest.fixture
    def erm(self, sm):
        return ErrorRecoveryManager(sm)

    def test_init(self, erm, sm):
        assert erm.state_manager is sm

    # handle_error
    def test_handle_network_timeout(self, erm):
        err = {"type": "network", "message": "Connection timeout"}
        assert erm.handle_error(err) is True

    def test_handle_network_dns(self, erm):
        err = {"type": "network", "message": "DNS resolution failed"}
        assert erm.handle_error(err) is True

    def test_handle_network_unknown(self, erm):
        err = {"type": "network", "message": "unknown error"}
        assert erm.handle_error(err) is False

    def test_handle_service_rate_limit(self, erm):
        err = {"type": "service", "message": "Rate limit exceeded"}
        assert erm.handle_error(err) is True

    def test_handle_service_api_key(self, erm):
        err = {"type": "service", "message": "Invalid API key"}
        assert erm.handle_error(err) is False

    def test_handle_service_generic(self, erm):
        err = {"type": "service", "message": "Server error 500"}
        assert erm.handle_error(err) is True

    def test_handle_validation_missing(self, erm):
        err = {"type": "validation", "message": "Missing required field"}
        assert erm.handle_error(err) is True

    def test_handle_validation_invalid(self, erm):
        err = {"type": "validation", "message": "Invalid format"}
        assert erm.handle_error(err) is True

    def test_handle_validation_unknown(self, erm):
        err = {"type": "validation", "message": "schema error"}
        assert erm.handle_error(err) is False

    def test_handle_unknown_type(self, erm):
        err = {"type": "unknown_type", "message": "something"}
        assert erm.handle_error(err) is False

    def test_handle_no_type(self, erm):
        err = {"message": "no type"}
        assert erm.handle_error(err) is False

    # recover_from_errors
    def test_recover_no_errors(self, erm):
        assert erm.recover_from_errors() is True

    def test_recover_recoverable_timeout(self, erm, sm):
        sm.add_error("network", "Connection timeout")
        result = erm.recover_from_errors()
        assert result is True

    def test_recover_unrecoverable_not_processed(self, erm, sm):
        sm.add_error("fatal", "crash", recoverable=False)
        result = erm.recover_from_errors()
        assert result is True  # no recoverable errors

    def test_recover_mixed(self, erm, sm):
        sm.add_error("network", "Connection timeout", recoverable=True)
        sm.add_error("network", "unknown network error", recoverable=True)
        result = erm.recover_from_errors()
        # First one recovers, second fails
        assert result is False

    def test_recover_skips_handled(self, erm, sm):
        sm.add_error("network", "Connection timeout")
        sm.get_errors()[0]["handled"] = True
        result = erm.recover_from_errors()
        assert result is True
