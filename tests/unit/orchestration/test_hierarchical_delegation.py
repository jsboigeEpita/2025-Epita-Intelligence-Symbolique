#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for the M3 true 3-tier delegation orchestrator (RA-10 #1069 / ORC-2).
===========================================================================

Covers the DoD of #1069:
- 3-tier path runnable + selectable (DelegationOrchestrator + mode routing).
- Strategic NL objective flows S→T→O — a write→read chain test asserting a
  unique strategic-intent marker reaches the operational command/provider.
- No heuristic fallback — a degraded delegation fails loud (#1019):
    * empty strategic objectives → DelegationError
    * absent operational tier → DelegationError
    * missing capability provider → honest status="failed" (not fabrication)

Async note: this directory's local ``pytest.ini`` uses STRICT asyncio mode
(not the repo root's ``asyncio_mode = auto``), so the module-level
``pytestmark = pytest.mark.asyncio`` below is required for the ``async def``
tests to run.
"""

from unittest.mock import MagicMock

import pytest

from argumentation_analysis.orchestration.hierarchical.delegation_orchestrator import (
    DelegationError,
    DelegationOrchestrator,
    make_registry_operational_executor,
    run_delegation_analysis,
)
from argumentation_analysis.orchestration.hierarchical.orchestrator import (
    run_hierarchical_analysis,
)

# This dir's local pytest.ini uses strict asyncio mode — mark every (async) test.
pytestmark = pytest.mark.asyncio


# A deliberately unique, keyword-free marker. Keyword-free so the tactical
# decomposition falls through to its generic branch (it must NOT match the
# "identifier"+"arguments" or "détecter"+"sophisme" heuristics), which proves
# the NL intent is threaded explicitly rather than via the keyword router.
STRATEGIC_MARKER = "UNIQUE_STRATEGIC_INTENT_zeta42_opaque"


class _FakeStrategicManager:
    """Strategic-tier seam: returns canned objectives, records eval input.

    Replacing the real ``StrategicManager`` keeps the test free of LLM/middleware
    while still exercising the REAL tactical decomposition + T→O translation.
    """

    def __init__(self, objectives):
        self._objectives = objectives
        self.eval_calls = []

    def initialize_analysis(self, text):
        return {"objectives": self._objectives, "strategic_plan": {}}

    def evaluate_final_results(self, results):
        self.eval_calls.append(results)
        return {
            "conclusion": "stub-conclusion",
            "evaluation": {"overall_success_rate": 1.0},
        }


class _FakeProvider:
    def __init__(self, name, invoke):
        self.name = name
        self.invoke = invoke


class _FakeRegistry:
    """Minimal CapabilityRegistry surface used by RegistryBackedOperationalRegistry."""

    def __init__(self, providers_by_cap=None):
        self._providers_by_cap = providers_by_cap or {}

    def find_for_capability(self, capability):
        return self._providers_by_cap.get(capability, [])


# ---------------------------------------------------------------------------
# S→T→O write→read chain
# ---------------------------------------------------------------------------


async def test_strategic_objective_flows_s_to_t_to_o():
    """The strategic NL objective (write) reaches the operational command (read).

    This is the core #1069 chain test: a unique strategic-intent marker, set at
    the strategic tier, must surface verbatim on the operational command after
    crossing the real tactical decomposition + translation tiers.
    """
    objectives = [{"id": "obj-1", "description": STRATEGIC_MARKER, "priority": "high"}]
    captured = []

    async def stub_executor(command):
        captured.append(command)
        return {
            "task_id": command.get("tactical_task_id"),
            "objective_id": command.get("objective_id"),
            "status": "completed",
            "outputs": {"ok": True},
        }

    orchestrator = DelegationOrchestrator(
        strategic_manager=_FakeStrategicManager(objectives),
        operational_executor=stub_executor,
        middleware=MagicMock(),
    )

    result = await orchestrator.analyze("some source text")

    assert result["mode"] == "delegation"
    assert result["tasks_created"] >= 1
    assert len(captured) >= 1
    # write→read: the NL intent crossed S→T→O intact.
    assert captured[0]["strategic_objective_description"] == STRATEGIC_MARKER
    assert captured[0]["objective_id"] == "obj-1"
    # The strategic tier received an aggregated per-objective success_rate.
    assert orchestrator.strategic_manager.eval_calls
    assert "obj-1" in orchestrator.strategic_manager.eval_calls[0]


async def test_multiple_objectives_each_thread_their_intent():
    """Each objective's NL intent reaches its own task's command (no cross-talk)."""
    objectives = [
        {"id": "obj-1", "description": "ALPHA_intent_opaque", "priority": "high"},
        {"id": "obj-2", "description": "BETA_intent_opaque", "priority": "medium"},
    ]
    captured = {}

    async def stub_executor(command):
        captured[command["objective_id"]] = command["strategic_objective_description"]
        return {
            "task_id": command.get("tactical_task_id"),
            "objective_id": command.get("objective_id"),
            "status": "completed",
        }

    orchestrator = DelegationOrchestrator(
        strategic_manager=_FakeStrategicManager(objectives),
        operational_executor=stub_executor,
        middleware=MagicMock(),
    )
    await orchestrator.analyze("text")

    assert captured["obj-1"] == "ALPHA_intent_opaque"
    assert captured["obj-2"] == "BETA_intent_opaque"


# ---------------------------------------------------------------------------
# Fail-loud — no heuristic fallback (#1019)
# ---------------------------------------------------------------------------


async def test_empty_objectives_fails_loud():
    """Zero strategic objectives must raise, not silently inject defaults."""
    orchestrator = DelegationOrchestrator(
        strategic_manager=_FakeStrategicManager([]),
        operational_executor=lambda cmd: None,  # never reached
        middleware=MagicMock(),
    )
    with pytest.raises(DelegationError):
        await orchestrator.analyze("text")


async def test_absent_operational_tier_fails_loud():
    """No executor and no registry → the chain has no operational tier → raise."""
    objectives = [
        {"id": "obj-1", "description": "generic_opaque_task", "priority": "high"}
    ]
    orchestrator = DelegationOrchestrator(
        strategic_manager=_FakeStrategicManager(objectives),
        middleware=MagicMock(),
    )  # no operational_executor, no capability_registry
    with pytest.raises(DelegationError):
        await orchestrator.analyze("text")


async def test_run_delegation_analysis_routes_to_chain():
    """The convenience fn builds + runs the chain (and fails loud on empty tier)."""
    objectives = [
        {"id": "obj-1", "description": "generic_opaque_task", "priority": "high"}
    ]
    with pytest.raises(DelegationError):
        await run_delegation_analysis(
            "text",
            strategic_manager=_FakeStrategicManager(objectives),
            middleware=MagicMock(),
        )


# ---------------------------------------------------------------------------
# Default registry-backed executor — honest failure vs real routing
# ---------------------------------------------------------------------------


async def test_registry_executor_missing_provider_is_honest_failure():
    """A required capability with no provider yields status=failed, not a raise
    and not a fabricated success."""
    executor = make_registry_operational_executor(_FakeRegistry())
    result = await executor(
        {
            "tactical_task_id": "t1",
            "objective_id": "obj-1",
            "required_capabilities": ["fallacy_detection"],
        }
    )
    assert result["status"] == "failed"
    assert result["reason"] == "no_provider_for_required_capabilities"


async def test_registry_executor_invokes_real_provider_with_intent():
    """The default executor routes the strategic NL intent to the provider."""

    async def fake_invoke(input_data, context):
        return {"echo": input_data.get("strategic_objective_description")}

    registry = _FakeRegistry(
        {"fallacy_detection": [_FakeProvider("informal_v1", fake_invoke)]}
    )
    executor = make_registry_operational_executor(registry)
    result = await executor(
        {
            "tactical_task_id": "t1",
            "objective_id": "obj-2",
            "required_capabilities": ["fallacy_detection"],
            "strategic_objective_description": "INTENT_MARK_opaque",
        }
    )
    assert result["status"] == "completed"
    assert result["capability"] == "fallacy_detection"
    assert result["outputs"]["echo"] == "INTENT_MARK_opaque"


# ---------------------------------------------------------------------------
# Mode routing on the shared hierarchical entry point
# ---------------------------------------------------------------------------


async def test_run_hierarchical_analysis_unknown_mode_raises():
    with pytest.raises(ValueError):
        await run_hierarchical_analysis("text", mode="nonsense")


async def test_run_hierarchical_analysis_delegation_mode_dispatches():
    """mode='delegation' routes to the M3 chain (proven by its fail-loud on an
    absent operational tier, which the M2 bridge would not raise).

    The fake strategic_manager + MagicMock middleware are threaded through
    ``**kwargs`` so no real LLM/MessageMiddleware is constructed in the test.
    """
    objectives = [
        {"id": "obj-1", "description": "generic_opaque_task", "priority": "high"}
    ]
    with pytest.raises(DelegationError):
        await run_hierarchical_analysis(
            "text",
            mode="delegation",
            strategic_manager=_FakeStrategicManager(objectives),
            middleware=MagicMock(),
        )
