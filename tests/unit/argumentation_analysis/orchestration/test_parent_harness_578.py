"""Tests for parent harness parallel per-argument fallacy detection (#578 tier 3).

Verifies that _invoke_hierarchical_fallacy_per_argument correctly:
- Extracts arguments from context/state
- Runs parallel analysis via asyncio.gather
- Deduplicates results by (taxonomy_pk, source_arg_id)
- Falls back to single-text when no arguments available
- Handles timeouts and errors per-argument
"""
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestExtractArgumentsForParallel:
    """Test argument extraction from various context sources."""

    def test_extracts_from_state_object(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _extract_arguments_for_parallel,
        )

        state = MagicMock()
        state.identified_arguments = {
            "arg_1": "First argument with sufficient length to pass threshold",
            "arg_2": "Second argument also long enough for extraction test",
        }
        context = {"_state_object": state}
        result = _extract_arguments_for_parallel("any text", context)
        assert len(result) == 2
        assert result[0] == ("arg_1", "First argument with sufficient length to pass threshold")
        assert result[1] == ("arg_2", "Second argument also long enough for extraction test")

    def test_extracts_from_extraction_output(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _extract_arguments_for_parallel,
        )

        context = {
            "phase_extraction_output": {
                "arguments": [
                    {"text": "Argument one is a substantial text for testing purposes here"},
                    {"text": "Argument two is another substantial text for testing"},
                ]
            }
        }
        result = _extract_arguments_for_parallel("any text", context)
        assert len(result) == 2
        assert result[0][0] == "arg_1"
        assert result[1][0] == "arg_2"

    def test_falls_back_to_paragraph_splitting(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _extract_arguments_for_parallel,
        )

        text = (
            "First paragraph that is long enough to be treated as an argument for testing.\n\n"
            "Second paragraph also long enough to be treated as argument for the test."
        )
        result = _extract_arguments_for_parallel(text, {})
        assert len(result) == 2
        assert result[0][0] == "paragraph_1"
        assert result[1][0] == "paragraph_2"

    def test_returns_empty_for_short_text(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _extract_arguments_for_parallel,
        )

        result = _extract_arguments_for_parallel("Short text", {})
        assert result == []

    def test_filters_short_arguments(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _extract_arguments_for_parallel,
        )

        state = MagicMock()
        state.identified_arguments = {
            "arg_1": "Too short",
            "arg_2": "This argument is long enough to pass the twenty character threshold",
        }
        context = {"_state_object": state}
        result = _extract_arguments_for_parallel("any text", context)
        assert len(result) == 1
        assert result[0][0] == "arg_2"

    def test_caps_at_10_arguments(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _extract_arguments_for_parallel,
        )

        state = MagicMock()
        state.identified_arguments = {
            f"arg_{i}": f"Argument number {i} with enough text to pass threshold check"
            for i in range(15)
        }
        context = {"_state_object": state}
        result = _extract_arguments_for_parallel("any text", context)
        assert len(result) == 10

    def test_state_takes_priority_over_paragraphs(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _extract_arguments_for_parallel,
        )

        state = MagicMock()
        state.identified_arguments = {
            "s1": "State argument one is long enough for the test threshold",
        }
        text = "Para one long enough.\n\nPara two long enough for the test."
        context = {"_state_object": state}
        result = _extract_arguments_for_parallel(text, context)
        assert len(result) == 1
        assert result[0][0] == "s1"


class TestInvokeHierarchicalFallacyPerArgument:
    """Test the parent harness parallel invocation."""

    @pytest.mark.asyncio
    async def test_skips_when_no_taxonomy(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_hierarchical_fallacy_per_argument,
        )

        with patch(
            "argumentation_analysis.orchestration.invoke_callables.os.path.isfile",
            return_value=False,
        ):
            result = await _invoke_hierarchical_fallacy_per_argument("text", {})
            assert result["exploration_method"] == "skipped"
            assert result["fallacies"] == []

    @pytest.mark.asyncio
    async def test_falls_back_to_single_when_no_args(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_hierarchical_fallacy_per_argument,
        )

        mock_single_result = {
            "fallacies": [{"fallacy_type": "ad_hominem"}],
            "exploration_method": "one_shot",
        }

        with patch(
            "argumentation_analysis.orchestration.invoke_callables.os.path.isfile",
            return_value=True,
        ), patch(
            "argumentation_analysis.orchestration.invoke_callables._extract_arguments_for_parallel",
            return_value=[],
        ), patch(
            "argumentation_analysis.orchestration.invoke_callables._invoke_hierarchical_fallacy",
            new_callable=AsyncMock,
            return_value=mock_single_result,
        ):
            result = await _invoke_hierarchical_fallacy_per_argument("short text", {})
            assert result["fallacies"][0]["fallacy_type"] == "ad_hominem"

    @pytest.mark.asyncio
    async def test_parallel_execution_with_mocked_plugin(self):
        """Simulate 3 arguments analyzed in parallel, verify aggregation."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_hierarchical_fallacy_per_argument,
        )

        arguments = [
            ("arg_1", "First argument text is long enough for the test"),
            ("arg_2", "Second argument text is long enough for the test"),
            ("arg_3", "Third argument text is long enough for the test"),
        ]

        # Each arg returns 1 fallacy — must be async coroutines
        def make_async_plugin_result(arg_id):
            result_json = json.dumps({
                "fallacies": [
                    {
                        "fallacy_type": f"fallacy_for_{arg_id}",
                        "taxonomy_pk": f"pk_{arg_id}",
                        "confidence": 0.8,
                        "explanation": f"Fallacy in {arg_id}",
                    }
                ],
                "exploration_method": "wide_net",
                "total_iterations": 3,
            })

            async def _mock_run(*args, **kwargs):
                return result_json

            return _mock_run

        mock_plugin_class = MagicMock()
        mock_instances = []

        for arg_id, arg_text in arguments:
            instance = MagicMock()
            instance.run_guided_analysis = make_async_plugin_result(arg_id)
            mock_instances.append(instance)

        mock_plugin_class.side_effect = mock_instances

        mock_llm_service = AsyncMock()
        mock_llm_service.get_chat_message_contents = AsyncMock(return_value=[])

        modules = {
            "openai": MagicMock(AsyncOpenAI=MagicMock(return_value=MagicMock())),
            "semantic_kernel.kernel": MagicMock(Kernel=MagicMock),
            "semantic_kernel.connectors.ai.open_ai": MagicMock(
                OpenAIChatCompletion=MagicMock(return_value=mock_llm_service),
            ),
            "argumentation_analysis.plugins.fallacy_workflow_plugin": MagicMock(
                FallacyWorkflowPlugin=mock_plugin_class,
            ),
        }

        with patch(
            "argumentation_analysis.orchestration.invoke_callables.os.path.isfile",
            return_value=True,
        ), patch(
            "argumentation_analysis.orchestration.invoke_callables._extract_arguments_for_parallel",
            return_value=arguments,
        ), patch.dict("sys.modules", modules), patch(
            "argumentation_analysis.orchestration.invoke_callables.os.environ",
            {"OPENAI_API_KEY": "test-key", "OPENAI_BASE_URL": "https://api.test.com/v1", "OPENAI_CHAT_MODEL_ID": "test-model"},
        ):
            result = await _invoke_hierarchical_fallacy_per_argument("full text", {})

        assert result["parallel_executed"] is True
        assert result["per_argument_count"] == 3
        assert len(result["fallacies"]) == 3
        assert result["exploration_method"] == "wide_net"

    @pytest.mark.asyncio
    async def test_dedup_same_taxonomy_different_args(self):
        """Same taxonomy_pk from different args kept; same pk+arg_id deduped."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_hierarchical_fallacy_per_argument,
        )

        arguments = [
            ("arg_1", "First argument text is long enough for the test here"),
            ("arg_2", "Second argument text is long enough for the test here"),
        ]

        # Both return same taxonomy_pk but different source_arg_id
        def make_async_plugin_result(arg_id):
            result_json = json.dumps({
                "fallacies": [
                    {
                        "fallacy_type": "ad_hominem",
                        "taxonomy_pk": "pk_ad_hominem",
                        "confidence": 0.7,
                        "explanation": f"Same fallacy in {arg_id}",
                    }
                ],
                "exploration_method": "wide_net",
                "total_iterations": 2,
            })

            async def _mock_run(*args, **kwargs):
                return result_json

            return _mock_run

        mock_plugin_class = MagicMock()
        mock_instances = []
        for arg_id, _ in arguments:
            instance = MagicMock()
            instance.run_guided_analysis = make_async_plugin_result(arg_id)
            mock_instances.append(instance)
        mock_plugin_class.side_effect = mock_instances

        mock_llm_service = AsyncMock()
        mock_llm_service.get_chat_message_contents = AsyncMock(return_value=[])

        modules = {
            "openai": MagicMock(AsyncOpenAI=MagicMock(return_value=MagicMock())),
            "semantic_kernel.kernel": MagicMock(Kernel=MagicMock),
            "semantic_kernel.connectors.ai.open_ai": MagicMock(
                OpenAIChatCompletion=MagicMock(return_value=mock_llm_service),
            ),
            "argumentation_analysis.plugins.fallacy_workflow_plugin": MagicMock(
                FallacyWorkflowPlugin=mock_plugin_class,
            ),
        }

        with patch(
            "argumentation_analysis.orchestration.invoke_callables.os.path.isfile",
            return_value=True,
        ), patch(
            "argumentation_analysis.orchestration.invoke_callables._extract_arguments_for_parallel",
            return_value=arguments,
        ), patch.dict("sys.modules", modules), patch(
            "argumentation_analysis.orchestration.invoke_callables.os.environ",
            {"OPENAI_API_KEY": "test-key", "OPENAI_BASE_URL": "https://api.test.com/v1", "OPENAI_CHAT_MODEL_ID": "test-model"},
        ):
            result = await _invoke_hierarchical_fallacy_per_argument("full text", {})

        # Same taxonomy_pk but different source_arg_id = both kept
        assert len(result["fallacies"]) == 2

    @pytest.mark.asyncio
    async def test_timeout_per_argument_doesnt_block(self):
        """A slow argument times out but others complete."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_hierarchical_fallacy_per_argument,
        )

        arguments = [
            ("arg_1", "First argument text is long enough for the test here"),
            ("arg_2", "Second argument text is long enough for the test here"),
        ]

        # arg_1 succeeds quickly
        fast_result = json.dumps({
            "fallacies": [{"fallacy_type": "ad_hominem", "taxonomy_pk": "pk_1", "confidence": 0.8}],
            "exploration_method": "wide_net",
            "total_iterations": 2,
        })

        async def fast_run(*args, **kwargs):
            return fast_result

        # arg_2 raises timeout inside wait_for
        async def timeout_run(*args, **kwargs):
            await asyncio.sleep(10)
            return json.dumps({"fallacies": [], "exploration_method": "wide_net"})

        fast_instance = MagicMock()
        fast_instance.run_guided_analysis = fast_run

        slow_instance = MagicMock()
        slow_instance.run_guided_analysis = timeout_run

        mock_plugin_class = MagicMock(side_effect=[fast_instance, slow_instance])
        mock_llm_service = AsyncMock()
        mock_llm_service.get_chat_message_contents = AsyncMock(return_value=[])

        modules = {
            "openai": MagicMock(AsyncOpenAI=MagicMock(return_value=MagicMock())),
            "semantic_kernel.kernel": MagicMock(Kernel=MagicMock),
            "semantic_kernel.connectors.ai.open_ai": MagicMock(
                OpenAIChatCompletion=MagicMock(return_value=mock_llm_service),
            ),
            "argumentation_analysis.plugins.fallacy_workflow_plugin": MagicMock(
                FallacyWorkflowPlugin=mock_plugin_class,
            ),
        }

        with patch(
            "argumentation_analysis.orchestration.invoke_callables.os.path.isfile",
            return_value=True,
        ), patch(
            "argumentation_analysis.orchestration.invoke_callables._extract_arguments_for_parallel",
            return_value=arguments,
        ), patch.dict("sys.modules", modules), patch(
            "argumentation_analysis.orchestration.invoke_callables.os.environ",
            {"OPENAI_API_KEY": "test-key", "OPENAI_BASE_URL": "https://api.test.com/v1", "OPENAI_CHAT_MODEL_ID": "test-model"},
        ):
            # Use a very short timeout for arg_2 to trigger timeout quickly
            original_wait_for = asyncio.wait_for

            async def patched_wait_for(coro, timeout=60):
                if timeout > 1:
                    return await original_wait_for(coro, timeout=0.5)
                return await original_wait_for(coro, timeout=timeout)

            with patch(
                "argumentation_analysis.orchestration.invoke_callables.asyncio.wait_for",
                side_effect=patched_wait_for,
            ):
                result = await _invoke_hierarchical_fallacy_per_argument("full text", {})

        # The fast arg completes, the slow one times out — result still valid
        assert "fallacies" in result
        assert result["parallel_executed"] is True

    @pytest.mark.asyncio
    async def test_no_api_key_returns_unavailable(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_hierarchical_fallacy_per_argument,
        )

        with patch(
            "argumentation_analysis.orchestration.invoke_callables.os.path.isfile",
            return_value=True,
        ), patch(
            "argumentation_analysis.orchestration.invoke_callables._extract_arguments_for_parallel",
            return_value=[("arg_1", "A long enough argument text for testing here")],
        ), patch(
            "argumentation_analysis.orchestration.invoke_callables.os.environ",
            {"OPENAI_API_KEY": "", "OPENAI_BASE_URL": "", "OPENAI_CHAT_MODEL_ID": ""},
        ):
            result = await _invoke_hierarchical_fallacy_per_argument("text", {})
            assert result["exploration_method"] == "unavailable"
            assert result["fallacies"] == []
