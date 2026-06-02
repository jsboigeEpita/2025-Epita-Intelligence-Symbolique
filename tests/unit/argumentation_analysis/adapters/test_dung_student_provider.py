"""Tests for abs_arg_dung adapter (DungStudentProvider)."""
import pytest
from unittest.mock import MagicMock, patch

from argumentation_analysis.adapters.dung_student_provider import (
    DungStudentProvider,
    SUPPORTED_SEMANTICS,
)


class TestDungStudentProvider:
    """Tests for the student Dung provider adapter."""

    def test_provider_metadata(self):
        """Verify provider name, quality score, and capabilities."""
        provider = DungStudentProvider()
        assert provider.provider_name == "abs_arg_dung_student"
        assert 0 < provider.quality_score < 1.0
        assert "dung_extensions" in provider.capabilities

    def test_supported_semantics_subset(self):
        """Student lib should support a subset of the native engine's 11 semantics."""
        assert len(SUPPORTED_SEMANTICS) == 4
        assert "grounded" in SUPPORTED_SEMANTICS
        assert "preferred" in SUPPORTED_SEMANTICS
        assert "stable" in SUPPORTED_SEMANTICS
        assert "complete" in SUPPORTED_SEMANTICS

    def test_unavailable_without_jvm(self):
        """Provider should report unavailable when JVM is not started."""
        provider = DungStudentProvider()
        # Reset cached state
        provider._available = None

        with patch("jpype.isJVMStarted", return_value=False):
            assert provider.is_available() is False

    def test_unavailable_when_import_fails(self):
        """Provider should report unavailable when abs_arg_dung is not importable."""
        provider = DungStudentProvider()
        provider._available = None

        with patch("jpype.isJVMStarted", return_value=True):
            with patch.dict("sys.modules", {"abs_arg_dung.enhanced_agent": None}):
                # Force re-check
                provider._available = None
                result = provider.is_available()
                assert result is False

    @pytest.mark.asyncio
    async def test_compute_returns_unavailable_without_jvm(self):
        """compute_extensions should return unavailable dict when JVM is off."""
        provider = DungStudentProvider()

        with patch.object(provider, "is_available", return_value=False):
            result = await provider.compute_extensions(
                arguments=["a", "b"], attacks=[("a", "b")]
            )
        assert result["provider"] == "abs_arg_dung_student"
        assert result["status"] == "unavailable"

    @pytest.mark.asyncio
    async def test_adapter_callable_signature(self):
        """invoke_dung_student should accept (input_text, context)."""
        from argumentation_analysis.adapters.dung_student_provider import (
            invoke_dung_student,
        )

        # Mock the extraction helpers to avoid needing full pipeline context
        with patch(
            "argumentation_analysis.adapters.dung_student_provider.DungStudentProvider.is_available",
            return_value=False,
        ):
            result = await invoke_dung_student("some text", {})
        assert result["provider"] == "abs_arg_dung_student"

    def test_register_only_when_available(self):
        """register_dung_student_provider should skip if unavailable."""
        registry = MagicMock()
        provider = DungStudentProvider()

        with patch.object(provider.__class__, "is_available", return_value=False):
            # Need to patch the instantiation inside register_dung_student_provider
            with patch(
                "argumentation_analysis.adapters.dung_student_provider.DungStudentProvider.is_available",
                return_value=False,
            ):
                from argumentation_analysis.adapters.dung_student_provider import (
                    register_dung_student_provider,
                )

                register_dung_student_provider(registry)
        # Registry should NOT have been called since provider is unavailable
        registry.register_service.assert_not_called()
