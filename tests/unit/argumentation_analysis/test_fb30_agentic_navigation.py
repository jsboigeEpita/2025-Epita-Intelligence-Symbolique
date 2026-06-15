"""FB-30 #1107 — restored agentic taxonomy navigation (no depth cap).

Target: ``fallacy_workflow_plugin._explore_single_branch`` after the FB-30
restoration-by-subtraction. The mechanical per-level ``_beam_descent`` was
REMOVED; the agentic loop now has NO depth cap (taxonomy leaves are the only
cap, depth ≤ 10) and shows the LLM a multi-level cluster so it can jump levels
via ``explore_branch(any_pk)`` — the original summer-2025 design.

Tests are LOAD-BEARING per the #1097 lesson: they exercise the REAL plugin
with the LLM dependency mocked (``llm_service.get_chat_message_contents``
returns scripted ``FunctionCallContent``), NOT a mock of the classifier.

DoD coverage (#1107):
- ``test_deep_leaf_depth10_reachable_via_level_jump`` — a depth-10 leaf is
  reached in ONE level-jump (depths 2-9 skipped). Under the removed
  MAX_DEPTH_PER_BRANCH=8 + immediate-children-only prompt, depth 10 needed
  9 per-level iterations > the 8 cap → structurally unreachable.
- ``test_level_jump_honoured`` — an LLM-chosen mid-level jump is honoured.
- ``test_negative_control_no_fallacy_returns_none`` — no-fallacy text → None.
- ``test_call_budget_breaks_runaway_loop`` — a bouncing loop is bounded by
  MAX_NAVIGATION_LLM_CALLS (preserves #708 runaway guard).
- ``TestRestorationContract`` — the cap is gone, the budget guard exists,
  ``_beam_descent`` is removed, ``_render_subtree_cluster`` exists.
"""

import inspect
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from semantic_kernel.contents import FunctionCallContent

from argumentation_analysis.plugins.fallacy_workflow_plugin import (
    FallacyWorkflowPlugin,
)


def _msg_with_items(*items):
    """Wrap tool-call items in a fake chat message exposing ``.items``."""
    return [SimpleNamespace(items=list(items))]


def _slave_kernel_stub():
    """Slave-kernel mock whose ``plugins.get('Exploration')`` contains every
    function name, so ``_execute_tool_calls`` reaches the real
    ``self.exploration_plugin.<func>`` call and not the Unknown-function
    error branch. (Same shape as the FB-27 test helper.)"""

    class _FakePlugin:
        def __contains__(self, name):
            return True

        def __getitem__(self, name):
            return MagicMock()

    kernel = MagicMock()
    kernel.plugins.get.return_value = _FakePlugin()
    return kernel


def _explore_call(target_pk):
    return FunctionCallContent(
        name="explore_branch",
        arguments=json.dumps({"node_pk": target_pk}),
    )


def _confirm_call(node_pk, justification="matches the pattern"):
    # confidence must be a label ('high'/'medium'/'low') — see FB-27 note.
    return FunctionCallContent(
        name="confirm_fallacy",
        arguments=json.dumps(
            {"node_pk": node_pk, "justification": justification, "confidence": "high"}
        ),
    )


def _conclude_call(reason="no fallacy in this branch"):
    return FunctionCallContent(
        name="conclude_no_fallacy",
        arguments=json.dumps({"reason": reason}),
    )


# ---------------------------------------------------------------------------
# Synthetic taxonomy — a single linear chain depth 1..10 (PK = "1"*depth).
# The depth-10 leaf is structurally unreachable under the old depth-8 cap +
# immediate-children-only prompt (9 per-level iterations needed). Under the
# restored agentic nav it is reachable in one level-jump.
# ---------------------------------------------------------------------------


def _deep_chain_taxonomy(max_depth: int = 10):
    data = []
    for d in range(1, max_depth + 1):
        pk = "1" * d
        path = ".".join(["1"] * d)
        data.append(
            {
                "PK": pk,
                "path": path,
                "depth": str(d),
                "text_fr": f"Nœud profondeur {d}",
                "text_en": f"Depth-{d} node",
                "desc_fr": f"Chaîne linéaire, niveau {d}",
                "desc_en": f"Linear chain, level {d}",
                "Famille": "test",
                "Sous-Famille": f"niv{d}",
                "nom_vulgarisé": f"Nœud-{d}",
                "example_fr": "",
                "example_en": "",
            }
        )
    return data


def _make_plugin(taxonomy_data=None):
    data = taxonomy_data or _deep_chain_taxonomy()
    return FallacyWorkflowPlugin(
        master_kernel=MagicMock(),
        llm_service=MagicMock(),
        taxonomy_data=data,
    )


DEEP_LEAF_PK = "1" * 10  # depth 10


# ---------------------------------------------------------------------------
# Restoration contract (regression-detectable)
# ---------------------------------------------------------------------------


class TestRestorationContract:
    """The FB-30 subtraction must be detectable in the plugin's surface."""

    def test_depth_cap_removed(self):
        assert not hasattr(FallacyWorkflowPlugin, "MAX_DEPTH_PER_BRANCH"), (
            "FB-30: MAX_DEPTH_PER_BRANCH cap still present — the depth cap was "
            "supposed to be removed (taxonomy leaves are the only cap)."
        )

    def test_call_budget_guard_exists(self):
        assert hasattr(FallacyWorkflowPlugin, "MAX_NAVIGATION_LLM_CALLS")
        assert FallacyWorkflowPlugin.MAX_NAVIGATION_LLM_CALLS >= 1

    def test_beam_descent_removed(self):
        assert not hasattr(FallacyWorkflowPlugin, "_beam_descent"), (
            "FB-30: _beam_descent still present — the mechanical beam was "
            "removed by subtraction (anti-pendule: one scheme, not two)."
        )

    def test_beam_constants_removed(self):
        for dead in ("BEAM_WIDTH", "BEAM_MAX_LLM_CALLS", "BEAM_MIN_DEPTH"):
            assert not hasattr(
                FallacyWorkflowPlugin, dead
            ), f"FB-30: dead beam constant {dead} still present."

    def test_subtree_cluster_helper_exists(self):
        assert hasattr(FallacyWorkflowPlugin, "_render_subtree_cluster"), (
            "FB-30: _render_subtree_cluster (multi-level cluster renderer) "
            "missing — the navigation prompt needs it to show >1 level."
        )

    def test_no_heuristic_fallback_added(self):
        """Anti-pendule HARD: no regex/keyword shortcut substituting for the
        LLM's free node choice."""
        src = inspect.getsource(FallacyWorkflowPlugin).lower()
        for forbidden in ["re.match", "re.search", "if 'depth' == 9"]:
            assert forbidden.lower() not in src, (
                f"FB-30 anti-pendule: heuristic '{forbidden}' added — node "
                "choice must stay LLM-conducted."
            )


# ---------------------------------------------------------------------------
# Behaviour — the REAL navigation loop with the LLM dependency mocked
# ---------------------------------------------------------------------------


class TestLevelJumpAndDeepLeaf:
    """The LLM may jump levels (call explore_branch on a deeper PK than the
    immediate child) and the loop must honour it — reaching deep leaves."""

    @pytest.mark.asyncio
    async def test_deep_leaf_depth10_reachable_via_level_jump(self):
        """DoD: a depth-10 leaf is reachable. The LLM jumps from the root
        straight to the depth-10 leaf (skipping depths 2-9), reaches it as a
        leaf, and confirms. Under the removed depth-8 cap this was
        structurally unreachable (9 per-level iterations needed)."""
        plugin = _make_plugin()
        slave_kernel = _slave_kernel_stub()

        # Iteration 1 (root has a child → navigation branch): jump to depth 10.
        # Iteration 2 (depth-10 leaf → leaf branch): confirm.
        plugin.llm_service.get_chat_message_contents = AsyncMock(
            side_effect=[
                _msg_with_items(_explore_call(DEEP_LEAF_PK)),
                _msg_with_items(_confirm_call(DEEP_LEAF_PK)),
            ]
        )

        result = await plugin._explore_single_branch(
            argument_text="Some genuinely fallacious text.",
            start_pk="1",
            slave_kernel=slave_kernel,
            slave_settings=MagicMock(),
        )

        assert result is not None, (
            "FB-30: depth-10 leaf produced no classification — the level-jump "
            "was not honoured or the leaf was not reached."
        )
        assert result.taxonomy_pk == DEEP_LEAF_PK, (
            f"FB-30: expected depth-10 leaf PK '{DEEP_LEAF_PK}', got "
            f"'{result.taxonomy_pk}'."
        )
        # Levels 2-9 skipped — exactly one jump in the navigation trace.
        assert result.navigation_trace == ["1", DEEP_LEAF_PK], (
            f"FB-30: navigation trace should show the level-jump ['1', "
            f"'{DEEP_LEAF_PK}'], got {result.navigation_trace}. Intermediate "
            "levels must be skippable."
        )
        # Confirm the landed node really is at depth 10.
        landed = plugin.taxonomy_navigator.get_node(DEEP_LEAF_PK)
        assert int(landed["depth"]) == 10

    @pytest.mark.asyncio
    async def test_level_jump_honoured_mid_chain(self):
        """A mid-level jump (root → depth-4 grandchild) is honoured, then the
        LLM descends one more level to a depth-5 leaf and confirms. Proves the
        loop accepts ANY target PK, not just immediate children."""
        plugin = _make_plugin()
        slave_kernel = _slave_kernel_stub()
        depth4_pk = "1" * 4
        depth5_pk = "1" * 5

        plugin.llm_service.get_chat_message_contents = AsyncMock(
            side_effect=[
                _msg_with_items(_explore_call(depth4_pk)),  # jump root→depth4
                _msg_with_items(_explore_call(depth5_pk)),  # depth4→depth5 child
                _msg_with_items(_confirm_call(depth5_pk)),  # depth5 leaf confirm
            ]
        )

        result = await plugin._explore_single_branch(
            argument_text="Fallacious text.",
            start_pk="1",
            slave_kernel=slave_kernel,
            slave_settings=MagicMock(),
        )

        assert result is not None
        assert result.taxonomy_pk == depth5_pk
        assert result.navigation_trace == ["1", depth4_pk, depth5_pk]

    @pytest.mark.asyncio
    async def test_negative_control_no_fallacy_returns_none(self):
        """Anti-#1019: no-fallacy text → the LLM concludes no-fallacy → None
        (honest MISSED), never a fabricated deep confirmation."""
        plugin = _make_plugin()
        slave_kernel = _slave_kernel_stub()
        plugin.llm_service.get_chat_message_contents = AsyncMock(
            return_value=_msg_with_items(_conclude_call())
        )

        result = await plugin._explore_single_branch(
            argument_text="A neutral sentence with no fallacy.",
            start_pk="1",
            slave_kernel=slave_kernel,
            slave_settings=MagicMock(),
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_call_budget_breaks_runaway_loop(self):
        """DoD anti-runaway (#708): if the LLM bounces forever (never confirms
        nor concludes), the loop must stop at MAX_NAVIGATION_LLM_CALLS and
        return None — no unbounded descent."""
        plugin = _make_plugin()
        slave_kernel = _slave_kernel_stub()

        # Bounce "1" ↔ "11" forever: each explore target differs from current,
        # so explore_targets is never empty and the loop would run unbounded
        # without the call budget.
        call_count = {"n": 0}

        async def bouncing_response(*args, **kwargs):
            call_count["n"] += 1
            pk = "11" if call_count["n"] % 2 == 1 else "1"
            return _msg_with_items(_explore_call(pk))

        plugin.llm_service.get_chat_message_contents = bouncing_response

        result = await plugin._explore_single_branch(
            argument_text="Text.",
            start_pk="1",
            slave_kernel=slave_kernel,
            slave_settings=MagicMock(),
        )

        assert result is None, "FB-30: runaway loop should end with None."
        budget = FallacyWorkflowPlugin.MAX_NAVIGATION_LLM_CALLS
        assert call_count["n"] <= budget, (
            f"FB-30: call budget breached — made {call_count['n']} LLM calls, "
            f"budget is {budget}. Runaway guard (#708) not preserved."
        )


# ---------------------------------------------------------------------------
# Multi-level cluster rendering (the prompt shows >1 level)
# ---------------------------------------------------------------------------


class TestSubtreeCluster:
    def test_cluster_renders_multiple_levels(self):
        """The cluster helper renders children AND grandchildren (≥2 levels),
        so the LLM can pick a grandchild PK and jump a level."""
        plugin = _make_plugin()
        rendered = plugin._render_subtree_cluster("1", max_levels=2)
        # Root + depth-2 + depth-3 lines should all appear.
        assert "1" in rendered  # root line (ID: 1)
        assert "11" in rendered  # depth-2 child
        assert "111" in rendered  # depth-3 grandchild
        # The grandchild appears (multi-level), and at greater indentation.
        assert rendered.index("111") > rendered.index("11")

    def test_cluster_truncated_at_max_levels(self):
        """max_levels=1 renders only immediate children (no grandchildren)."""
        plugin = _make_plugin()
        rendered = plugin._render_subtree_cluster("1", max_levels=1)
        assert "11" in rendered  # depth-2 child present
        # depth-3 grandchild must NOT appear as its own cluster line
        # (it could appear as a substring of a deeper PK, so check the line)
        lines = [ln for ln in rendered.splitlines() if "ID: 111" in ln]
        assert lines == [], "FB-30: max_levels=1 should not render grandchildren."
