"""FB-35 #1121 — global cost-based circuit breaker on the agentic fallacy descent.

Target: ``fallacy_workflow_plugin._BranchSupersessionTracker.try_consume_descent_call``
+ the descent-loop check in ``_explore_single_branch``.

Context: FB-30 (#1107) restored agentic navigation by **subtracting** the depth
cap (``MAX_DEPTH_PER_BRANCH``) + the mechanical beam. The per-branch
``MAX_NAVIGATION_LLM_CALLS`` bounds a SINGLE branch and the fan-out spawn budget
bounds sub-branch SPAWNING — but their product (~wide-net candidates × per-branch
calls × fan-out) is uncapped, which is what explodes on a large/entity-dense
corpus (the doc_A >2h runaway). FB-35 adds a **global cost-based breaker**: a
total-LLM-call budget across ALL branches + sub-branches of one
``run_guided_analysis`` that fails loud (partial results + a flag) when exceeded.

Anti-pendule HARD (coordinator arbitration, no ACK needed):
- This is a COST cap (one descent iteration == one LLM call), NOT a depth cap.
  The taxonomy leaves remain the only structural depth bound.
- It fails LOUD (``descent_budget_exceeded`` surfaced in the JSON → ``degraded``
  + ``last_error`` on the phase output), never a silent truncation.

Tests are LOAD-BEARING (#1097 lesson): the tracker unit test exercises the real
``_BranchSupersessionTracker``; the wiring test exercises the REAL
``_explore_single_branch`` loop with the LLM dependency mocked.
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


# ---------------------------------------------------------------------------
# Helpers (mirrors test_fb30_agentic_navigation.py — kept local to avoid
# cross-test imports).
# ---------------------------------------------------------------------------


def _msg_with_items(*items):
    return [SimpleNamespace(items=list(items))]


def _slave_kernel_stub():
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


def _make_tracker(plugin, descent_call_budget, fanout_budget=0):
    return plugin._BranchSupersessionTracker(
        plugin.taxonomy_navigator,
        fanout_budget=fanout_budget,
        descent_call_budget=descent_call_budget,
    )


# ---------------------------------------------------------------------------
# Contract (regression-detectable surface)
# ---------------------------------------------------------------------------


class TestDescentBreakerContract:
    """The FB-35 breaker must be detectable in the plugin's surface AND must
    NOT re-introduce the depth cap FB-30 subtracted (anti-pendule HARD)."""

    def test_global_call_budget_constant_exists(self):
        assert hasattr(FallacyWorkflowPlugin, "DESCENT_TOTAL_CALL_BUDGET"), (
            "FB-35: DESCENT_TOTAL_CALL_BUDGET global call budget missing."
        )
        assert FallacyWorkflowPlugin.DESCENT_TOTAL_CALL_BUDGET >= 1

    def test_depth_cap_still_absent(self):
        """Anti-pendule: FB-35 must NOT re-add the depth cap FB-30 removed."""
        assert not hasattr(FallacyWorkflowPlugin, "MAX_DEPTH_PER_BRANCH"), (
            "FB-35 anti-pendule: MAX_DEPTH_PER_BRANCH re-introduced — the "
            "breaker must be cost-based, never a depth cap."
        )

    def test_per_branch_budget_preserved(self):
        """The FB-30 per-branch guard is unchanged (the global budget is
        ADDITIVE on the call-count dimension, not a replacement)."""
        assert hasattr(FallacyWorkflowPlugin, "MAX_NAVIGATION_LLM_CALLS")

    def test_beam_constants_still_absent(self):
        """The new constant is NOT named BEAM_* (would trip the FB-30
        regression test test_beam_constants_removed)."""
        for dead in ("BEAM_WIDTH", "BEAM_MAX_LLM_CALLS", "BEAM_MIN_DEPTH"):
            assert not hasattr(FallacyWorkflowPlugin, dead)

    def test_tracker_has_descent_call_api(self):
        tracker = FallacyWorkflowPlugin._BranchSupersessionTracker(
            MagicMock(), descent_call_budget=5
        )
        assert hasattr(tracker, "try_consume_descent_call")
        assert hasattr(tracker, "descent_budget_exceeded")
        assert hasattr(tracker, "descent_calls_made")
        assert tracker.descent_budget_exceeded is False

    def test_no_silent_truncation_added(self):
        """Anti-pendule: no heuristic/regex shortcut masking a producer
        weakness instead of bounding it."""
        src = inspect.getsource(FallacyWorkflowPlugin).lower()
        # The breaker must RAISE/BREAK, not silently rewrite output.
        assert "re.sub" not in src or "scrub" not in src


# ---------------------------------------------------------------------------
# Unit — the tracker mechanics (pure, deterministic, no LLM)
# ---------------------------------------------------------------------------


class TestDescentBreakerUnit:
    def test_budget_consumed_then_exceeded(self):
        """budget=3 → 3 consumes return True, the 4th returns False and sets
        the fail-loud flag."""
        plugin = _make_plugin()
        tracker = _make_tracker(plugin, descent_call_budget=3)

        assert tracker.try_consume_descent_call() is True  # remaining 3→2
        assert tracker.descent_calls_made == 1
        assert tracker.try_consume_descent_call() is True  # remaining 2→1
        assert tracker.descent_calls_made == 2
        assert tracker.try_consume_descent_call() is True  # remaining 1→0
        assert tracker.descent_calls_made == 3
        assert tracker.descent_budget_exceeded is False

        # 4th consume: budget exhausted.
        assert tracker.try_consume_descent_call() is False
        assert tracker.descent_budget_exceeded is True
        # calls_made does NOT advance past the budget (the refusing call is
        # not made — fail-loud, the loop breaks BEFORE the LLM call).
        assert tracker.descent_calls_made == 3

    def test_disabled_budget_always_allows(self):
        """budget=0 ⇒ breaker disabled (legacy unbounded-within-branch behavior).
        Never trips."""
        plugin = _make_plugin()
        tracker = _make_tracker(plugin, descent_call_budget=0)

        for _ in range(50):
            assert tracker.try_consume_descent_call() is True
        assert tracker.descent_budget_exceeded is False
        # When disabled, calls_made is not counted (the breaker is a no-op).
        assert tracker.descent_calls_made == 0

    def test_exhaustion_is_sticky(self):
        """Once exceeded, every further consume keeps returning False."""
        plugin = _make_plugin()
        tracker = _make_tracker(plugin, descent_call_budget=1)
        assert tracker.try_consume_descent_call() is True
        for _ in range(5):
            assert tracker.try_consume_descent_call() is False
        assert tracker.descent_budget_exceeded is True


# ---------------------------------------------------------------------------
# Wiring — the REAL descent loop with the LLM mocked to over-fan-out
# ---------------------------------------------------------------------------


class TestDescentBreakerWiring:
    @pytest.mark.asyncio
    async def test_global_budget_breaks_bouncing_loop_before_per_branch_cap(self):
        """DoD #1121 item 4: with the global budget set BELOW the per-branch
        cap, an over-fanning (bouncing) descent must stop at the GLOBAL budget
        and surface the fail-loud flag — NOT at MAX_NAVIGATION_LLM_CALLS.

        This is the doc_A pathology in miniature: the loop would otherwise run
        to the per-branch cap (18); the global breaker trips first (budget=2).
        """
        plugin = _make_plugin()
        slave_kernel = _slave_kernel_stub()
        tracker = _make_tracker(plugin, descent_call_budget=2)
        assert tracker.descent_budget_exceeded is False

        call_count = {"n": 0}

        async def bouncing_response(*args, **kwargs):
            call_count["n"] += 1
            pk = "11" if call_count["n"] % 2 == 1 else "1"
            return _msg_with_items(_explore_call(pk))

        plugin.llm_service.get_chat_message_contents = bouncing_response

        result = await plugin._explore_single_branch(
            argument_text="Dense text that fans out indefinitely.",
            start_pk="1",
            slave_kernel=slave_kernel,
            slave_settings=MagicMock(),
            supersession_tracker=tracker,
        )

        # The descent was cost-capped — no confirmation reached.
        assert result is None
        # The global budget (2) tripped BEFORE the per-branch cap (18).
        assert call_count["n"] == 2, (
            f"FB-35: global breaker should stop descent at 2 LLM calls, made "
            f"{call_count['n']}."
        )
        assert tracker.descent_calls_made == 2
        assert tracker.descent_budget_exceeded is True, (
            "FB-35: descent_budget_exceeded flag must be set when the global "
            "call budget is exceeded (fail-loud)."
        )

    @pytest.mark.asyncio
    async def test_generous_budget_does_not_interfere_with_normal_descent(self):
        """DoD #1121 item 3 (richness unchanged): a generous global budget lets
        a normal depth-10 level-jump descent complete UNCHANGED — the breaker
        is invisible unless the pathological fan-out trips it. A confirmed
        fallacy is returned and the flag stays False."""
        plugin = _make_plugin()
        slave_kernel = _slave_kernel_stub()
        # Generous budget — must not trip on a normal 2-call descent.
        tracker = _make_tracker(plugin, descent_call_budget=240)
        deep_leaf_pk = "1" * 10

        plugin.llm_service.get_chat_message_contents = AsyncMock(
            side_effect=[
                _msg_with_items(_explore_call(deep_leaf_pk)),
                _msg_with_items(_confirm_call(deep_leaf_pk)),
            ]
        )

        result = await plugin._explore_single_branch(
            argument_text="Genuinely fallacious text.",
            start_pk="1",
            slave_kernel=slave_kernel,
            slave_settings=MagicMock(),
            supersession_tracker=tracker,
        )

        assert result is not None
        assert result.taxonomy_pk == deep_leaf_pk
        assert tracker.descent_budget_exceeded is False
        assert tracker.descent_calls_made == 2

    @pytest.mark.asyncio
    async def test_no_tracker_no_global_check(self):
        """When no tracker is passed (legacy/standalone call), the global
        breaker is skipped — only the per-branch MAX_NAVIGATION_LLM_CALLS
        bounds the loop. Preserves backward compatibility."""
        plugin = _make_plugin()
        slave_kernel = _slave_kernel_stub()
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
            # NOTE: no supersession_tracker — global breaker is a no-op.
        )

        assert result is None
        # Bounded only by the per-branch cap, NOT by any global budget.
        assert call_count["n"] == FallacyWorkflowPlugin.MAX_NAVIGATION_LLM_CALLS


def _confirm_call(node_pk, justification="matches the pattern"):
    return FunctionCallContent(
        name="confirm_fallacy",
        arguments=json.dumps(
            {"node_pk": node_pk, "justification": justification, "confidence": "high"}
        ),
    )
