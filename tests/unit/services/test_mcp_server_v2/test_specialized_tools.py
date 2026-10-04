"""Tests for MCP specialized tools."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class MockComponentType(Enum):
    AGENT = "agent"


@dataclass
class MockComponentRegistration:
    name: str
    component_type: MockComponentType
    capabilities: List[str]
    invoke: Optional[Any] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


def _make_registry(components=None):
    """Create a mock registry."""
    registry = MagicMock()
    components = components or []

    def find_for(cap):
        return [c for c in components if cap in c.capabilities]

    registry.find_for_capability.side_effect = find_for
    return registry


def _setup_tools():
    mcp_mock = MagicMock()
    tools = {}

    def fake_tool():
        def wrapper(fn):
            tools[fn.__name__] = fn
            return fn

        return wrapper

    mcp_mock.tool = fake_tool
    return mcp_mock, tools


class TestEvaluateQuality:
    """Tests for evaluate_quality tool."""

    @pytest.mark.asyncio
    async def test_success(self):
        mcp_mock, tools = _setup_tools()
        invoke_fn = AsyncMock(return_value={"overall_score": 0.82, "virtues": {}})
        registry = _make_registry(
            [
                MockComponentRegistration(
                    "quality",
                    MockComponentType.AGENT,
                    ["argument_quality"],
                    invoke=invoke_fn,
                )
            ]
        )

        from argumentation_analysis.services.mcp_server.tools.specialized_tools import (
            register_specialized_tools,
        )

        register_specialized_tools(mcp_mock, lambda: registry)

        result = await tools["evaluate_quality"](text="This is a strong argument.")
        assert result["tool"] == "evaluate_quality"
        assert result["result"]["overall_score"] == 0.82

    @pytest.mark.asyncio
    async def test_not_available(self):
        mcp_mock, tools = _setup_tools()
        registry = _make_registry([])

        from argumentation_analysis.services.mcp_server.tools.specialized_tools import (
            register_specialized_tools,
        )

        register_specialized_tools(mcp_mock, lambda: registry)

        result = await tools["evaluate_quality"](text="Test")
        assert "error" in result
        assert "not available" in result["error"]


class TestGenerateCounterArgument:
    """Tests for generate_counter_argument tool."""

    @pytest.mark.asyncio
    async def test_success(self):
        mcp_mock, tools = _setup_tools()
        invoke_fn = AsyncMock(
            return_value={
                "counter_arguments": [
                    {"strategy": "reductio", "text": "If we accept..."}
                ]
            }
        )
        registry = _make_registry(
            [
                MockComponentRegistration(
                    "counter_arg",
                    MockComponentType.AGENT,
                    ["counter_argument_generation"],
                    invoke=invoke_fn,
                )
            ]
        )

        from argumentation_analysis.services.mcp_server.tools.specialized_tools import (
            register_specialized_tools,
        )

        register_specialized_tools(mcp_mock, lambda: registry)

        result = await tools["generate_counter_argument"](
            text="Climate change is fake."
        )
        assert result["tool"] == "generate_counter_argument"
        assert "counter_arguments" in result["result"]

    @pytest.mark.asyncio
    async def test_not_available(self):
        mcp_mock, tools = _setup_tools()
        registry = _make_registry([])

        from argumentation_analysis.services.mcp_server.tools.specialized_tools import (
            register_specialized_tools,
        )

        register_specialized_tools(mcp_mock, lambda: registry)

        result = await tools["generate_counter_argument"](text="Test")
        assert "error" in result


class TestRunDebateAnalysis:
    """Tests for run_debate_analysis tool."""

    @pytest.mark.asyncio
    async def test_success(self):
        mcp_mock, tools = _setup_tools()
        invoke_fn = AsyncMock(return_value={"debate_score": 0.7})
        registry = _make_registry(
            [
                MockComponentRegistration(
                    "debate",
                    MockComponentType.AGENT,
                    ["adversarial_debate"],
                    invoke=invoke_fn,
                )
            ]
        )

        from argumentation_analysis.services.mcp_server.tools.specialized_tools import (
            register_specialized_tools,
        )

        register_specialized_tools(mcp_mock, lambda: registry)

        result = await tools["run_debate_analysis"](text="Should we ban AI?")
        assert result["tool"] == "run_debate_analysis"
        assert result["result"]["debate_score"] == 0.7

    @pytest.mark.asyncio
    async def test_no_invoke(self):
        mcp_mock, tools = _setup_tools()
        registry = _make_registry(
            [
                MockComponentRegistration(
                    "debate",
                    MockComponentType.AGENT,
                    ["adversarial_debate"],
                    invoke=None,
                )
            ]
        )

        from argumentation_analysis.services.mcp_server.tools.specialized_tools import (
            register_specialized_tools,
        )

        register_specialized_tools(mcp_mock, lambda: registry)

        result = await tools["run_debate_analysis"](text="Test")
        assert "error" in result
        assert "no invoke" in result["error"]


class TestRunGovernanceAnalysis:
    """Tests for run_governance_analysis tool."""

    @pytest.mark.asyncio
    async def test_success(self):
        mcp_mock, tools = _setup_tools()
        invoke_fn = AsyncMock(return_value={"consensus": 0.65, "method": "borda"})
        registry = _make_registry(
            [
                MockComponentRegistration(
                    "governance",
                    MockComponentType.AGENT,
                    ["governance_simulation"],
                    invoke=invoke_fn,
                )
            ]
        )

        from argumentation_analysis.services.mcp_server.tools.specialized_tools import (
            register_specialized_tools,
        )

        register_specialized_tools(mcp_mock, lambda: registry)

        result = await tools["run_governance_analysis"](
            text="Proposal: increase budget"
        )
        assert result["tool"] == "run_governance_analysis"
        assert result["result"]["consensus"] == 0.65

    @pytest.mark.asyncio
    async def test_not_available(self):
        mcp_mock, tools = _setup_tools()
        registry = _make_registry([])

        from argumentation_analysis.services.mcp_server.tools.specialized_tools import (
            register_specialized_tools,
        )

        register_specialized_tools(mcp_mock, lambda: registry)

        result = await tools["run_governance_analysis"](text="Test")
        assert "error" in result


class TestSolveSat:
    """Tests for solve_sat tool (#1604 — the sat_solving demander)."""

    @pytest.mark.asyncio
    async def test_success(self):
        mcp_mock, tools = _setup_tools()
        invoke_fn = AsyncMock(
            return_value={"mode": "solve", "satisfiable": False, "model": None}
        )
        registry = _make_registry(
            [
                MockComponentRegistration(
                    "sat_handler",
                    MockComponentType.AGENT,
                    ["sat_solving"],
                    invoke=invoke_fn,
                )
            ]
        )

        from argumentation_analysis.services.mcp_server.tools.specialized_tools import (
            register_specialized_tools,
        )

        register_specialized_tools(mcp_mock, lambda: registry)

        result = await tools["solve_sat"](text="p && !p")
        assert result["tool"] == "solve_sat"
        assert result["capability"] == "sat_solving"
        assert result["provider"] == "sat_handler"
        assert result["result"]["satisfiable"] is False

    @pytest.mark.asyncio
    async def test_not_available(self):
        mcp_mock, tools = _setup_tools()
        registry = _make_registry([])

        from argumentation_analysis.services.mcp_server.tools.specialized_tools import (
            register_specialized_tools,
        )

        register_specialized_tools(mcp_mock, lambda: registry)

        result = await tools["solve_sat"](text="p && q")
        assert "error" in result
        assert "not available" in result["error"]


class TestSolveSatRealPath:
    """The arbitration witness (#1604): through the production registry,
    solve_sat DECIDES — an unsatisfiable formula returns UNSAT (no model), a
    satisfiable one returns SAT with a model. No LLM anywhere on the route;
    PySAT is pinned in the CI env (python-sat, #1336), so a failure here is
    a real env drift, not noise."""

    @pytest.mark.asyncio
    async def test_unsat_and_sat_verdicts(self):
        from argumentation_analysis.orchestration.registry_setup import setup_registry
        from argumentation_analysis.services.mcp_server.tools.specialized_tools import (
            register_specialized_tools,
        )

        mcp_mock, tools = _setup_tools()
        registry = setup_registry(include_optional=False)
        register_specialized_tools(mcp_mock, lambda: registry)

        unsat = await tools["solve_sat"](text="p && !p")
        sat = await tools["solve_sat"](text="p && q")

        assert unsat["tool"] == "solve_sat"
        assert unsat["provider"] == "sat_handler"
        assert unsat["result"]["satisfiable"] is False
        assert unsat["result"]["model"] is None
        assert sat["result"]["satisfiable"] is True
        assert sat["result"]["model"] == {"p": True, "q": True}
