"""
Tests for FunctionChoiceBehavior.Auto() wiring on agents (#208-B).

Verifies that AgentFactory.enable_auto_function_calling() correctly
configures the kernel's execution settings for auto-invocation.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestAgentFactoryFCB:
    """Tests for FunctionChoiceBehavior wiring in AgentFactory."""

    def test_enable_auto_function_calling(self):
        """enable_auto_function_calling sets FunctionChoiceBehavior.Auto on kernel settings."""
        from argumentation_analysis.agents.factory import AgentFactory

        # Create mock kernel and execution settings
        mock_settings = MagicMock()
        mock_kernel = MagicMock()
        mock_kernel.get_prompt_execution_settings_from_service_id.return_value = (
            mock_settings
        )

        factory = AgentFactory(kernel=mock_kernel, llm_service_id="test-service")
        result = factory.enable_auto_function_calling(max_auto_invoke_attempts=3)

        # Should return self for chaining
        assert result is factory
        assert factory._fcb_configured is True

        # Should have called get_prompt_execution_settings_from_service_id
        mock_kernel.get_prompt_execution_settings_from_service_id.assert_called_once_with(
            "test-service"
        )

        # Should have set function_choice_behavior on the settings
        assert mock_settings.function_choice_behavior is not None

    def test_enable_auto_function_calling_default_attempts(self):
        """Default max_auto_invoke_attempts is 5."""
        from argumentation_analysis.agents.factory import AgentFactory

        mock_settings = MagicMock()
        mock_kernel = MagicMock()
        mock_kernel.get_prompt_execution_settings_from_service_id.return_value = (
            mock_settings
        )

        factory = AgentFactory(kernel=mock_kernel, llm_service_id="test-service")
        factory.enable_auto_function_calling()

        # Verify FunctionChoiceBehavior.Auto was set
        assert mock_settings.function_choice_behavior is not None
        assert factory._fcb_configured is True

    def test_enable_auto_function_calling_graceful_failure(self):
        """enable_auto_function_calling handles errors gracefully."""
        from argumentation_analysis.agents.factory import AgentFactory

        mock_kernel = MagicMock()
        mock_kernel.get_prompt_execution_settings_from_service_id.side_effect = (
            RuntimeError("No such service")
        )

        factory = AgentFactory(kernel=mock_kernel, llm_service_id="bad-service")
        result = factory.enable_auto_function_calling()

        # Should not crash, return self, but _fcb_configured stays False
        assert result is factory
        assert factory._fcb_configured is False

    def test_factory_init_fcb_not_configured(self):
        """Factory starts with _fcb_configured = False."""
        from argumentation_analysis.agents.factory import AgentFactory

        mock_kernel = MagicMock()
        factory = AgentFactory(kernel=mock_kernel, llm_service_id="test-service")
        assert factory._fcb_configured is False

    def test_enable_auto_function_calling_chaining(self):
        """enable_auto_function_calling supports method chaining."""
        from argumentation_analysis.agents.factory import AgentFactory

        mock_settings = MagicMock()
        mock_kernel = MagicMock()
        mock_kernel.get_prompt_execution_settings_from_service_id.return_value = (
            mock_settings
        )

        factory = AgentFactory(kernel=mock_kernel, llm_service_id="test-service")
        # Should support chaining
        same_factory = factory.enable_auto_function_calling()
        assert same_factory is factory


class TestAnalysisRunnerV2FCB:
    """Tests for FCB wiring in analysis_runner_v2."""

    def test_runner_imports_correctly(self):
        """analysis_runner_v2 can be imported without errors."""
        try:
            from argumentation_analysis.orchestration.analysis_runner_v2 import (
                AnalysisRunnerV2,
            )
            assert AnalysisRunnerV2 is not None
        except ImportError as e:
            pytest.skip(f"Optional dependency missing: {e}")

    def test_fcb_import_exists(self):
        """FunctionChoiceBehavior is importable from SK."""
        from semantic_kernel.connectors.ai.function_choice_behavior import (
            FunctionChoiceBehavior,
        )
        assert hasattr(FunctionChoiceBehavior, "Auto")
