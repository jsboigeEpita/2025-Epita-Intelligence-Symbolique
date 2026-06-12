"""Tests for RA-3 #1048 item 2 — bounded recursive sub-branch fan-out.

When the slave LLM flags more than one promising child at a fork, the engine
used to keep the first and silently drop the rest (recall loss). The fan-out
explores the top child as the primary path AND the next few (bounded) as
concurrent recursive sub-branches whose results land in a shared sink.

These tests drive ``_explore_single_branch`` directly with a tiny path-based
taxonomy and a context-aware $0 mock LLM (no API, no corpus). They prove:
  - a fork with two explore targets explores BOTH children (recall structure);
  - the primary single-path is preserved when fan-out is disabled (additive);
  - a zero budget hard-disables fan-out (anti-pendule #1019 bound).
"""

import asyncio
import re
from unittest.mock import MagicMock

import pytest

from semantic_kernel.kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from semantic_kernel.contents import ChatMessageContent, FunctionCallContent

from argumentation_analysis.plugins.fallacy_workflow_plugin import FallacyWorkflowPlugin
from argumentation_analysis.plugins.identification_models import IdentifiedFallacy


def _make_fork_taxonomy():
    """Root → Branch A (depth 1) → two leaf children (depth 2).

    ``get_children`` resolves parentage via the dotted ``path`` + ``depth``
    (NOT ``parent_PK``), so every node carries an explicit ``path``.
    """
    return [
        {"PK": "0", "depth": "0", "path": "0", "text_fr": "Racine", "desc_fr": "root"},
        {
            "PK": "10",
            "depth": "1",
            "path": "0.10",
            "text_fr": "Branche A",
            "desc_fr": "fork node",
            "Famille": "FamA",
        },
        {
            "PK": "20",
            "depth": "2",
            "path": "0.10.20",
            "text_fr": "Sophisme X",
            "desc_fr": "leaf x",
        },
        {
            "PK": "21",
            "depth": "2",
            "path": "0.10.21",
            "text_fr": "Sophisme Y",
            "desc_fr": "leaf y",
        },
    ]


def _make_plugin():
    kernel = Kernel()
    mock_service = MagicMock(spec=OpenAIChatCompletion)
    mock_service.service_id = "test-service"
    return FallacyWorkflowPlugin(
        master_kernel=kernel,
        llm_service=mock_service,
        taxonomy_data=_make_fork_taxonomy(),
    )


def _explore_call(pk):
    call = MagicMock(spec=FunctionCallContent)
    call.name = "Exploration-explore_branch"
    call.arguments = {"node_pk": pk}
    call.id = f"explore_{pk}"
    return call


def _confirm_call(pk):
    call = MagicMock(spec=FunctionCallContent)
    call.name = "Exploration-confirm_fallacy"
    call.arguments = {
        "node_pk": pk,
        "confidence": "high",
        "justification": f"matches leaf {pk}",
    }
    call.id = f"confirm_{pk}"
    return call


def _msg(items):
    msg = MagicMock(spec=ChatMessageContent)
    msg.items = items
    return msg


def _install_fork_mock(plugin):
    """Mock get_chat_message_contents.

    At the single fork (Branche A) it returns TWO explore targets (the two
    leaves). At each leaf it confirms that leaf. This makes the LLM
    deterministically request multi-child exploration.
    """

    async def mock_contents(chat_history, settings, kernel, **kwargs):
        prompt = "\n".join(
            str(getattr(m, "content", "") or "") for m in chat_history.messages
        )
        # "You reached a LEAF node" is unique to the leaf prompt. The fork's
        # *system* message also mentions "LEAF node" in passing ("confirm ...
        # if you are at a LEAF node"), so a bare "LEAF node" check misfires.
        if "You reached a LEAF node" in prompt:
            match = re.search(r"PK:\s*(\w+)", prompt)
            leaf_pk = match.group(1) if match else ""
            return [_msg([_confirm_call(leaf_pk)])]
        # Fork prompt: request both children.
        return [_msg([_explore_call("20"), _explore_call("21")])]

    plugin.llm_service.get_chat_message_contents = mock_contents


class TestSubbranchFanout:
    def test_fork_fans_out_extra_child_into_sink(self):
        """Both children of a 2-way fork get explored — recall is preserved."""
        plugin = _make_plugin()
        _install_fork_mock(plugin)
        slave_kernel, slave_settings = plugin._create_slave_kernel()
        tracker = plugin._BranchSupersessionTracker(
            plugin.taxonomy_navigator,
            fanout_budget=plugin.SUBBRANCH_FANOUT_BUDGET,
        )
        sink = []

        primary = asyncio.get_event_loop().run_until_complete(
            plugin._explore_single_branch(
                "some argument text",
                "10",
                slave_kernel,
                slave_settings,
                supersession_tracker=tracker,
                results_sink=sink,
            )
        )

        # Primary path followed the top child (PK 20).
        assert isinstance(primary, IdentifiedFallacy)
        assert primary.taxonomy_pk == "20"
        assert primary.fallacy_type == "Sophisme X"

        # The extra child (PK 21) was fanned out, not dropped.
        assert tracker.fanout_spawned == 1
        assert len(sink) == 1
        assert sink[0].taxonomy_pk == "21"
        assert sink[0].fallacy_type == "Sophisme Y"

        # Both confirmations were high-confidence leaves.
        assert primary.confidence > 0.8
        assert sink[0].confidence > 0.8

    def test_no_sink_preserves_single_path(self):
        """With no sink, behaviour is the legacy single-path descent (additive)."""
        plugin = _make_plugin()
        _install_fork_mock(plugin)
        slave_kernel, slave_settings = plugin._create_slave_kernel()
        tracker = plugin._BranchSupersessionTracker(
            plugin.taxonomy_navigator,
            fanout_budget=plugin.SUBBRANCH_FANOUT_BUDGET,
        )

        primary = asyncio.get_event_loop().run_until_complete(
            plugin._explore_single_branch(
                "some argument text",
                "10",
                slave_kernel,
                slave_settings,
                supersession_tracker=tracker,
                results_sink=None,  # no sink → no fan-out
            )
        )

        assert isinstance(primary, IdentifiedFallacy)
        assert primary.taxonomy_pk == "20"  # top child only
        assert tracker.fanout_spawned == 0

    def test_zero_budget_disables_fanout(self):
        """A zero fan-out budget hard-disables fan-out (anti-pendule bound)."""
        plugin = _make_plugin()
        _install_fork_mock(plugin)
        slave_kernel, slave_settings = plugin._create_slave_kernel()
        tracker = plugin._BranchSupersessionTracker(
            plugin.taxonomy_navigator,
            fanout_budget=0,  # exhausted from the start
        )
        sink = []

        primary = asyncio.get_event_loop().run_until_complete(
            plugin._explore_single_branch(
                "some argument text",
                "10",
                slave_kernel,
                slave_settings,
                supersession_tracker=tracker,
                results_sink=sink,
            )
        )

        assert isinstance(primary, IdentifiedFallacy)
        assert primary.taxonomy_pk == "20"
        assert tracker.fanout_spawned == 0
        assert sink == []

    def test_try_consume_fanout_respects_budget(self):
        """The shared budget decrements and stops at zero."""
        plugin = _make_plugin()
        tracker = plugin._BranchSupersessionTracker(
            plugin.taxonomy_navigator, fanout_budget=2
        )
        assert tracker.try_consume_fanout() is True
        assert tracker.try_consume_fanout() is True
        assert tracker.try_consume_fanout() is False  # exhausted
        assert tracker.fanout_spawned == 2

    def test_default_budget_is_zero(self):
        """Default tracker (no budget arg) cannot fan out — backward compatible."""
        plugin = _make_plugin()
        tracker = plugin._BranchSupersessionTracker(plugin.taxonomy_navigator)
        assert tracker.try_consume_fanout() is False
        assert tracker.fanout_spawned == 0
