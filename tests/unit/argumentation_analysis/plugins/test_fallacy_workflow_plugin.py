# -*- coding: utf-8 -*-
"""
Unit tests for FallacyWorkflowPlugin.
"""

import logging
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argumentation_analysis.plugins.fallacy_workflow_plugin import (
    FallacyWorkflowPlugin,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_kernel():
    kernel = MagicMock()
    kernel.add_service = MagicMock()
    return kernel


@pytest.fixture
def mock_llm_service():
    service = AsyncMock()
    service.get_chat_message_content = AsyncMock()
    return service


@pytest.fixture
def plugin(mock_kernel, mock_llm_service):
    """Create a FallacyWorkflowPlugin with no taxonomy file (empty taxonomy)."""
    return FallacyWorkflowPlugin(
        master_kernel=mock_kernel,
        llm_service=mock_llm_service,
    )


# ---------------------------------------------------------------------------
# 1. Construction
# ---------------------------------------------------------------------------

class TestConstruction:
    def test_basic_construction(self, mock_kernel, mock_llm_service):
        plugin = FallacyWorkflowPlugin(
            master_kernel=mock_kernel,
            llm_service=mock_llm_service,
        )
        assert plugin.master_kernel is mock_kernel
        assert plugin.llm_service is mock_llm_service
        assert plugin.language == "fr"
        assert plugin.taxonomy_navigator is not None

    def test_construction_with_taxonomy_file(self, mock_kernel, mock_llm_service, tmp_path):
        csv_file = tmp_path / "taxonomy.csv"
        csv_file.write_text(
            "PK,path,depth,name\n1,root,1,Root Fallacy\n",
            encoding="utf-8",
        )
        plugin = FallacyWorkflowPlugin(
            master_kernel=mock_kernel,
            llm_service=mock_llm_service,
            taxonomy_file_path=str(csv_file),
        )
        # The taxonomy navigator should have loaded the root node
        roots = plugin.taxonomy_navigator.get_root_nodes()
        assert len(roots) == 1
        assert roots[0]["name"] == "Root Fallacy"

    def test_construction_with_custom_logger(self, mock_kernel, mock_llm_service):
        custom_logger = logging.getLogger("test.custom")
        plugin = FallacyWorkflowPlugin(
            master_kernel=mock_kernel,
            llm_service=mock_llm_service,
            logger=custom_logger,
        )
        assert plugin.logger is custom_logger

    def test_construction_without_taxonomy_has_empty_navigator(self, plugin):
        roots = plugin.taxonomy_navigator.get_root_nodes()
        assert roots == []


# ---------------------------------------------------------------------------
# 2. Construction with bad taxonomy path
# ---------------------------------------------------------------------------

class TestBadTaxonomyPath:
    def test_file_not_found_logged(self, mock_kernel, mock_llm_service, caplog):
        with caplog.at_level(logging.ERROR):
            plugin = FallacyWorkflowPlugin(
                master_kernel=mock_kernel,
                llm_service=mock_llm_service,
                taxonomy_file_path="/nonexistent/path/taxonomy.csv",
            )
        # Plugin should still be created
        assert plugin.taxonomy_navigator is not None
        # Error should be logged
        assert any("not found" in r.message.lower() for r in caplog.records)

    def test_plugin_works_after_bad_path(self, mock_kernel, mock_llm_service):
        plugin = FallacyWorkflowPlugin(
            master_kernel=mock_kernel,
            llm_service=mock_llm_service,
            taxonomy_file_path="/nonexistent/taxonomy.csv",
        )
        # Should still have a working (empty) taxonomy navigator
        assert plugin.taxonomy_navigator.get_root_nodes() == []


# ---------------------------------------------------------------------------
# 3. _create_one_shot_kernel
# ---------------------------------------------------------------------------

class TestCreateOneShotKernel:
    def test_returns_kernel_and_settings(self, plugin):
        result = plugin._create_one_shot_kernel()
        assert isinstance(result, tuple)
        assert len(result) == 2

    @patch(
        "argumentation_analysis.plugins.fallacy_workflow_plugin.Kernel",
        return_value=MagicMock(),
    )
    def test_kernel_gets_llm_service_added(self, mock_kernel_cls, plugin):
        kernel, settings = plugin._create_one_shot_kernel()
        mock_kernel_cls.return_value.add_service.assert_called_once_with(
            plugin.llm_service
        )

    @patch(
        "argumentation_analysis.plugins.fallacy_workflow_plugin.Kernel",
        return_value=MagicMock(),
    )
    def test_settings_has_function_choice_none(self, mock_kernel_cls, plugin):
        from semantic_kernel.connectors.ai.open_ai import (
            OpenAIPromptExecutionSettings,
        )

        _kernel, settings = plugin._create_one_shot_kernel()
        assert isinstance(settings, OpenAIPromptExecutionSettings)
        assert settings.function_choice_behavior is not None
        # NoneInvoke sets type_ to FunctionChoiceType.NONE and max_auto_invoke=0
        assert settings.function_choice_behavior.maximum_auto_invoke_attempts == 0
        assert "none" in str(settings.function_choice_behavior.type_).lower()


# ---------------------------------------------------------------------------
# 4. run_guided_analysis success
# ---------------------------------------------------------------------------

class TestRunGuidedAnalysisSuccess:
    async def test_returns_stripped_response(self, plugin, mock_llm_service):
        mock_response = MagicMock()
        mock_response.__str__ = lambda self: "  Ad Hominem  "
        mock_llm_service.get_chat_message_content.return_value = mock_response

        result = await plugin.run_guided_analysis(
            argument_text="You are wrong because you are stupid."
        )
        assert result == "Ad Hominem"

    async def test_calls_llm_with_chat_history(self, plugin, mock_llm_service):
        mock_response = MagicMock()
        mock_response.__str__ = lambda self: "Straw Man"
        mock_llm_service.get_chat_message_content.return_value = mock_response

        await plugin.run_guided_analysis(
            argument_text="That is not what I said at all."
        )

        mock_llm_service.get_chat_message_content.assert_called_once()
        call_kwargs = mock_llm_service.get_chat_message_content.call_args
        assert "chat_history" in call_kwargs.kwargs
        assert "settings" in call_kwargs.kwargs
        assert "kernel" in call_kwargs.kwargs

    async def test_argument_text_in_prompt(self, plugin, mock_llm_service):
        mock_response = MagicMock()
        mock_response.__str__ = lambda self: "Appeal to Authority"
        mock_llm_service.get_chat_message_content.return_value = mock_response

        test_text = "Einstein said it, so it must be true."
        await plugin.run_guided_analysis(argument_text=test_text)

        call_kwargs = mock_llm_service.get_chat_message_content.call_args
        chat_history = call_kwargs.kwargs["chat_history"]
        # The user message should contain the argument text
        user_messages = [m for m in chat_history.messages if str(m.role) == "AuthorRole.USER" or "user" in str(m.role).lower()]
        assert len(user_messages) >= 1
        assert test_text in str(user_messages[0])


# ---------------------------------------------------------------------------
# 5. run_guided_analysis error handling
# ---------------------------------------------------------------------------

class TestRunGuidedAnalysisError:
    async def test_returns_error_string_on_exception(self, plugin, mock_llm_service):
        mock_llm_service.get_chat_message_content.side_effect = RuntimeError(
            "LLM service unavailable"
        )

        result = await plugin.run_guided_analysis(
            argument_text="Some argument text."
        )
        assert result.startswith("Error during analysis:")
        assert "LLM service unavailable" in result

    async def test_logs_error_on_exception(self, plugin, mock_llm_service, caplog):
        mock_llm_service.get_chat_message_content.side_effect = ValueError(
            "Bad request"
        )

        with caplog.at_level(logging.ERROR):
            await plugin.run_guided_analysis(
                argument_text="Some argument text."
            )

        assert any("one-shot analysis" in r.message.lower() for r in caplog.records)


# ---------------------------------------------------------------------------
# 6. run_guided_analysis with trace log
# ---------------------------------------------------------------------------

class TestRunGuidedAnalysisTraceLog:
    async def test_trace_log_file_created(self, plugin, mock_llm_service, tmp_path):
        mock_response = MagicMock()
        mock_response.__str__ = lambda self: "Red Herring"
        mock_llm_service.get_chat_message_content.return_value = mock_response

        log_file = tmp_path / "trace.log"

        result = await plugin.run_guided_analysis(
            argument_text="Look over there!",
            trace_log_path=str(log_file),
        )

        assert result == "Red Herring"
        # The log file should exist (created by FileHandler)
        assert log_file.exists()

    async def test_handlers_cleaned_up_after_success(self, plugin, mock_llm_service, tmp_path):
        mock_response = MagicMock()
        mock_response.__str__ = lambda self: "Fallacy"
        mock_llm_service.get_chat_message_content.return_value = mock_response

        log_file = tmp_path / "trace.log"
        logger = plugin.logger

        handlers_before = len(logger.handlers)
        await plugin.run_guided_analysis(
            argument_text="text",
            trace_log_path=str(log_file),
        )
        handlers_after = len(logger.handlers)

        # Handlers should be removed after the call
        assert handlers_after == handlers_before

    async def test_handlers_cleaned_up_after_error(self, plugin, mock_llm_service, tmp_path):
        mock_llm_service.get_chat_message_content.side_effect = RuntimeError("fail")

        log_file = tmp_path / "trace.log"
        logger = plugin.logger

        handlers_before = len(logger.handlers)
        await plugin.run_guided_analysis(
            argument_text="text",
            trace_log_path=str(log_file),
        )
        handlers_after = len(logger.handlers)

        # Handlers should be cleaned up even on error (finally block)
        assert handlers_after == handlers_before

    async def test_no_trace_log_no_file_handler(self, plugin, mock_llm_service):
        mock_response = MagicMock()
        mock_response.__str__ = lambda self: "Fallacy"
        mock_llm_service.get_chat_message_content.return_value = mock_response

        logger = plugin.logger
        handlers_before = len(logger.handlers)

        await plugin.run_guided_analysis(
            argument_text="text",
            trace_log_path=None,
        )

        # No handler should have been added or removed
        assert len(logger.handlers) == handlers_before
