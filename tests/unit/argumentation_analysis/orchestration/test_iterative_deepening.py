"""Tests for the extracted IterativeDeepeningOrchestrator (#471).

Validates:
- Protocol compliance (TaxonomyLike, LeafConfirmer)
- Kernel creation with constrained plugin
- Tool call extraction from LLM responses
- LLM call timeout protection
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from semantic_kernel import Kernel
from semantic_kernel.contents import ChatHistory


class MockTaxonomy:
    """Minimal TaxonomyLike implementation for testing."""

    def __init__(self, nodes=None):
        self.nodes = nodes or {}
        self._roots = [
            v for v in self.nodes.values() if v.get("depth") == 0
        ]

    def get_root_nodes(self):
        return self._roots

    def get_children(self, pk: str):
        return [
            v for v in self.nodes.values()
            if v.get("parent_pk") == pk
        ]

    def get_node(self, pk: str):
        return self.nodes.get(pk)


SAMPLE_TAXONOMY = MockTaxonomy({
    "root1": {"PK": "root1", "depth": 0, "text_fr": "Ad hominem", "parent_pk": None},
    "root1.1": {"PK": "root1.1", "depth": 1, "text_fr": "Abus personnel", "parent_pk": "root1"},
    "root1.1.1": {"PK": "root1.1.1", "depth": 2, "text_fr": "Empoisonnement du puits", "parent_pk": "root1.1"},
    "root2": {"PK": "root2", "depth": 0, "text_fr": "Appel à l'autorité", "parent_pk": None},
})


class TestProtocols:
    """Test that protocols are correctly implemented."""

    def test_mock_taxonomy_satisfies_protocol(self):
        from argumentation_analysis.orchestration.iterative_deepening import TaxonomyLike

        assert isinstance(SAMPLE_TAXONOMY, TaxonomyLike)

    def test_kernel_creation(self):
        from argumentation_analysis.orchestration.iterative_deepening import (
            IterativeDeepeningOrchestrator,
        )
        from argumentation_analysis.plugins.exploration_plugin import ExplorationPlugin
        from argumentation_analysis.agents.utils.taxonomy_navigator import TaxonomyNavigator

        mock_llm = MagicMock()
        orch = IterativeDeepeningOrchestrator(
            taxonomy=SAMPLE_TAXONOMY,
            llm_service=mock_llm,
            max_depth_per_branch=5,
            max_branches=3,
        )

        nav = TaxonomyNavigator(taxonomy_data=[])
        plugin = ExplorationPlugin(nav)
        kernel, settings = orch._create_constrained_kernel(plugin, "Exploration")

        assert isinstance(kernel, Kernel)
        assert settings is not None
        functions = kernel.get_full_list_of_function_metadata()
        assert len(functions) >= 3  # explore_branch, confirm_fallacy, conclude_no_fallacy


class TestToolCallExtraction:
    """Test tool call extraction from LLM responses."""

    def test_extract_from_none_response(self):
        from argumentation_analysis.orchestration.iterative_deepening import (
            IterativeDeepeningOrchestrator,
        )

        mock_llm = MagicMock()
        orch = IterativeDeepeningOrchestrator(
            taxonomy=SAMPLE_TAXONOMY,
            llm_service=mock_llm,
        )

        result = orch._extract_tool_calls(None)
        assert result == []

    def test_extract_from_empty_response(self):
        from argumentation_analysis.orchestration.iterative_deepening import (
            IterativeDeepeningOrchestrator,
        )

        mock_llm = MagicMock()
        orch = IterativeDeepeningOrchestrator(
            taxonomy=SAMPLE_TAXONOMY,
            llm_service=mock_llm,
        )

        result = orch._extract_tool_calls([])
        assert result == []


class TestTimeoutProtection:
    """Test LLM call timeout handling."""

    @pytest.mark.asyncio
    async def test_timeout_returns_none(self):
        from argumentation_analysis.orchestration.iterative_deepening import (
            IterativeDeepeningOrchestrator,
        )

        mock_llm = MagicMock()
        # Make get_chat_message_contents sleep longer than timeout
        mock_llm.get_chat_message_contents = AsyncMock(side_effect=asyncio.TimeoutError())

        orch = IterativeDeepeningOrchestrator(
            taxonomy=SAMPLE_TAXONOMY,
            llm_service=mock_llm,
            timeout_seconds=0.1,
        )

        kernel = Kernel()
        kernel.add_service(mock_llm)
        history = ChatHistory()
        history.add_user_message("test")

        result = await orch._llm_call_with_timeout(
            history, MagicMock(), kernel
        )
        assert result is None


class TestConfiguration:
    """Test orchestrator configuration."""

    def test_custom_configuration(self):
        from argumentation_analysis.orchestration.iterative_deepening import (
            IterativeDeepeningOrchestrator,
        )

        mock_llm = MagicMock()
        orch = IterativeDeepeningOrchestrator(
            taxonomy=SAMPLE_TAXONOMY,
            llm_service=mock_llm,
            max_depth_per_branch=12,
            max_branches=6,
            min_confirm_depth=3,
            timeout_seconds=60.0,
            language="en",
        )

        assert orch.max_depth_per_branch == 12
        assert orch.max_branches == 6
        assert orch.min_confirm_depth == 3
        assert orch.timeout_seconds == 60.0
        assert orch.language == "en"

    def test_defaults(self):
        from argumentation_analysis.orchestration.iterative_deepening import (
            IterativeDeepeningOrchestrator,
        )

        mock_llm = MagicMock()
        orch = IterativeDeepeningOrchestrator(
            taxonomy=SAMPLE_TAXONOMY,
            llm_service=mock_llm,
        )

        assert orch.max_depth_per_branch == 8
        assert orch.max_branches == 4
        assert orch.min_confirm_depth == 2
        assert orch.timeout_seconds == 30.0
        assert orch.language == "fr"
