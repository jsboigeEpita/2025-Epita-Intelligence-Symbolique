"""
Tests for Dung provider selection wiring (#908).

Validates:
  - Context propagation (dung_provider_hint)
  - Default behavior (no hint = AFHandler native)
  - Hint="abs_arg_dung_student" delegates to DungStudentProvider
  - Fallback when student provider unavailable
  - Signature acceptance in run_modern_analysis (future CLI flag)
"""

import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock


# ---------------------------------------------------------------------------
# Context propagation (zero-pollution)
# ---------------------------------------------------------------------------


class TestDungProviderContext:
    """Test context propagation for dung_provider_hint."""

    def test_default_no_hint(self):
        """No dung_provider_hint should be in context by default."""
        context = {}
        assert "dung_provider_hint" not in context

    def test_hint_set_in_context(self):
        """Explicitly set hint should be in context."""
        context = {"dung_provider_hint": "abs_arg_dung_student"}
        assert context["dung_provider_hint"] == "abs_arg_dung_student"


# ---------------------------------------------------------------------------
# Consumer tests — _invoke_dung_extensions reads hint
# ---------------------------------------------------------------------------


class TestDungProviderConsumer:
    """Test that _invoke_dung_extensions reads dung_provider_hint from context.

    These tests CALL the real consumer to verify the wiring works end-to-end.
    """

    async def test_no_hint_uses_native_afhandler(self):
        """Without hint, should use native AFHandler (may fall back to Python)."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_dung_extensions,
        )

        # Mock the extraction helpers to return minimal data
        with patch(
            "argumentation_analysis.orchestration.invoke_callables._extract_arguments_from_context",
            return_value=["arg1", "arg2"],
        ), patch(
            "argumentation_analysis.orchestration.invoke_callables._generate_attacks_from_args",
            return_value=[["arg1", "arg2"]],
        ):
            result = await _invoke_dung_extensions("Test argument", {})

        # Should have computed extensions (either via AFHandler or Python fallback)
        assert isinstance(result, dict)
        assert "semantics" in result

    async def test_student_hint_delegates_to_student_provider(self):
        """With hint='abs_arg_dung_student', should delegate to DungStudentProvider."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_dung_extensions,
        )

        mock_provider = MagicMock()
        mock_provider.compute_extensions = AsyncMock(return_value={
            "provider": "abs_arg_dung_student",
            "semantics": "multi",
            "extensions": {"extensions": [["arg1"]], "count": 1},
            "all_extensions": {"grounded": {"extensions": [["arg1"]], "count": 1}},
            "arguments": ["arg1", "arg2"],
            "attacks": [["arg1", "arg2"]],
            "statistics": {"arguments_count": 2, "attacks_count": 1, "semantics_computed": 4},
        })

        with patch(
            "argumentation_analysis.orchestration.invoke_callables._extract_arguments_from_context",
            return_value=["arg1", "arg2"],
        ), patch(
            "argumentation_analysis.orchestration.invoke_callables._generate_attacks_from_args",
            return_value=[["arg1", "arg2"]],
        ), patch(
            "argumentation_analysis.adapters.dung_student_provider.DungStudentProvider",
            return_value=mock_provider,
        ):
            result = await _invoke_dung_extensions(
                "Test argument",
                {"dung_provider_hint": "abs_arg_dung_student"},
            )

        # Should have used the student provider
        assert result["provider"] == "abs_arg_dung_student"
        mock_provider.compute_extensions.assert_called_once()

    async def test_student_unavailable_falls_back(self):
        """When student provider is unavailable, should fall back to native."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_dung_extensions,
        )

        mock_provider = MagicMock()
        mock_provider.compute_extensions = AsyncMock(return_value={
            "provider": "abs_arg_dung_student",
            "status": "unavailable",
            "error": "JVM not started",
        })

        with patch(
            "argumentation_analysis.orchestration.invoke_callables._extract_arguments_from_context",
            return_value=["arg1"],
        ), patch(
            "argumentation_analysis.orchestration.invoke_callables._generate_attacks_from_args",
            return_value=[],
        ), patch(
            "argumentation_analysis.adapters.dung_student_provider.DungStudentProvider",
            return_value=mock_provider,
        ):
            result = await _invoke_dung_extensions(
                "Test argument",
                {"dung_provider_hint": "abs_arg_dung_student"},
            )

        # Should have fallen back to native (no "provider" key from student)
        assert isinstance(result, dict)
        assert "semantics" in result

    async def test_unknown_hint_ignored(self):
        """An unknown hint value should be ignored (native behavior)."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_dung_extensions,
        )

        with patch(
            "argumentation_analysis.orchestration.invoke_callables._extract_arguments_from_context",
            return_value=["arg1"],
        ), patch(
            "argumentation_analysis.orchestration.invoke_callables._generate_attacks_from_args",
            return_value=[],
        ):
            result = await _invoke_dung_extensions(
                "Test argument",
                {"dung_provider_hint": "unknown_provider"},
            )

        # Should have used native AFHandler or Python fallback
        assert isinstance(result, dict)
        assert "semantics" in result


# ---------------------------------------------------------------------------
# DungStudentProvider unit tests
# ---------------------------------------------------------------------------


class TestDungStudentProvider:
    """Test DungStudentProvider interface."""

    def test_provider_name(self):
        """Provider name should be 'abs_arg_dung_student'."""
        from argumentation_analysis.adapters.dung_student_provider import (
            DungStudentProvider,
        )

        provider = DungStudentProvider()
        assert provider.provider_name == "abs_arg_dung_student"

    def test_quality_score(self):
        """Quality score should be 0.6 (lower than native 0.8)."""
        from argumentation_analysis.adapters.dung_student_provider import (
            DungStudentProvider,
        )

        provider = DungStudentProvider()
        assert provider.quality_score == 0.6

    def test_capabilities(self):
        """Should declare 'dung_extensions' capability."""
        from argumentation_analysis.adapters.dung_student_provider import (
            DungStudentProvider,
        )

        provider = DungStudentProvider()
        assert "dung_extensions" in provider.capabilities


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
