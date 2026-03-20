"""Tests for MCP capability tools."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class MockComponentType(Enum):
    AGENT = "agent"
    SERVICE = "service"
    PLUGIN = "plugin"


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


@dataclass
class MockSlotDeclaration:
    name: str
    description: str


def _make_registry(components=None, slots=None):
    """Create a mock registry with given components and slots."""
    registry = MagicMock()
    components = components or []
    slots = slots or {}

    caps_index = {}
    for comp in components:
        for cap in comp.capabilities:
            caps_index.setdefault(cap, []).append(comp.name)

    registry.get_all_capabilities.return_value = caps_index
    registry.get_all_slots.return_value = slots
    registry.summary.return_value = {
        "agents": sum(
            1 for c in components if c.component_type == MockComponentType.AGENT
        ),
        "services": sum(
            1 for c in components if c.component_type == MockComponentType.SERVICE
        ),
        "plugins": sum(
            1 for c in components if c.component_type == MockComponentType.PLUGIN
        ),
        "total_registrations": len(components),
        "slots_unfilled": len(slots),
    }
    registry.get_all_registrations.return_value = components

    def find_for(cap):
        return [c for c in components if cap in c.capabilities]

    registry.find_for_capability.side_effect = find_for
    return registry


def _setup_tools():
    """Helper to register tools and capture them."""
    mcp_mock = MagicMock()
    tools = {}

    def fake_tool():
        def wrapper(fn):
            tools[fn.__name__] = fn
            return fn

        return wrapper

    mcp_mock.tool = fake_tool
    return mcp_mock, tools


class TestListCapabilities:
    """Tests for list_capabilities tool."""

    @pytest.mark.asyncio
    async def test_list_with_components(self):
        mcp_mock, tools = _setup_tools()
        registry = _make_registry(
            components=[
                MockComponentRegistration(
                    "quality", MockComponentType.AGENT, ["argument_quality"]
                ),
                MockComponentRegistration(
                    "debate", MockComponentType.AGENT, ["adversarial_debate"]
                ),
            ],
            slots={"ranking": MockSlotDeclaration("ranking", "Ranking semantics")},
        )

        from argumentation_analysis.services.mcp_server.tools.capability_tools import (
            register_capability_tools,
        )

        register_capability_tools(mcp_mock, lambda: registry)

        result = await tools["list_capabilities"]()
        assert "argument_quality" in result["capabilities"]
        assert "ranking" in result["unfilled_slots"]
        assert result["summary"]["total_registrations"] == 2

    @pytest.mark.asyncio
    async def test_list_empty_registry(self):
        mcp_mock, tools = _setup_tools()
        registry = _make_registry()

        from argumentation_analysis.services.mcp_server.tools.capability_tools import (
            register_capability_tools,
        )

        register_capability_tools(mcp_mock, lambda: registry)

        result = await tools["list_capabilities"]()
        assert result["capabilities"] == {}
        assert result["summary"]["total_registrations"] == 0


class TestInvokeCapability:
    """Tests for invoke_capability tool."""

    @pytest.mark.asyncio
    async def test_invoke_success(self):
        mcp_mock, tools = _setup_tools()
        invoke_fn = AsyncMock(return_value={"score": 0.85})
        registry = _make_registry(
            components=[
                MockComponentRegistration(
                    "quality",
                    MockComponentType.AGENT,
                    ["argument_quality"],
                    invoke=invoke_fn,
                ),
            ]
        )

        from argumentation_analysis.services.mcp_server.tools.capability_tools import (
            register_capability_tools,
        )

        register_capability_tools(mcp_mock, lambda: registry)

        result = await tools["invoke_capability"](
            capability_name="argument_quality", text="Test argument"
        )
        assert result["provider"] == "quality"
        assert result["result"]["score"] == 0.85
        invoke_fn.assert_called_once_with("Test argument", {})

    @pytest.mark.asyncio
    async def test_invoke_not_found(self):
        mcp_mock, tools = _setup_tools()
        registry = _make_registry()

        from argumentation_analysis.services.mcp_server.tools.capability_tools import (
            register_capability_tools,
        )

        register_capability_tools(mcp_mock, lambda: registry)

        result = await tools["invoke_capability"](
            capability_name="nonexistent", text="Test"
        )
        assert "error" in result
        assert "No provider" in result["error"]

    @pytest.mark.asyncio
    async def test_invoke_no_callable(self):
        mcp_mock, tools = _setup_tools()
        registry = _make_registry(
            components=[
                MockComponentRegistration(
                    "quality",
                    MockComponentType.AGENT,
                    ["argument_quality"],
                    invoke=None,
                ),
            ]
        )

        from argumentation_analysis.services.mcp_server.tools.capability_tools import (
            register_capability_tools,
        )

        register_capability_tools(mcp_mock, lambda: registry)

        result = await tools["invoke_capability"](
            capability_name="argument_quality", text="Test"
        )
        assert "error" in result
        assert "no invoke" in result["error"]

    @pytest.mark.asyncio
    async def test_invoke_with_context(self):
        mcp_mock, tools = _setup_tools()
        invoke_fn = AsyncMock(return_value={"ok": True})
        registry = _make_registry(
            components=[
                MockComponentRegistration(
                    "quality",
                    MockComponentType.AGENT,
                    ["argument_quality"],
                    invoke=invoke_fn,
                ),
            ]
        )

        from argumentation_analysis.services.mcp_server.tools.capability_tools import (
            register_capability_tools,
        )

        register_capability_tools(mcp_mock, lambda: registry)

        ctx = {"key": "value"}
        result = await tools["invoke_capability"](
            capability_name="argument_quality", text="Test", context=ctx
        )
        invoke_fn.assert_called_once_with("Test", ctx)


class TestGetRegistrySummary:
    """Tests for get_registry_summary tool."""

    @pytest.mark.asyncio
    async def test_summary_with_components(self):
        mcp_mock, tools = _setup_tools()
        registry = _make_registry(
            components=[
                MockComponentRegistration(
                    "quality",
                    MockComponentType.AGENT,
                    ["argument_quality"],
                    invoke=AsyncMock(),
                ),
                MockComponentRegistration(
                    "jtms",
                    MockComponentType.SERVICE,
                    ["belief_maintenance"],
                ),
            ]
        )

        from argumentation_analysis.services.mcp_server.tools.capability_tools import (
            register_capability_tools,
        )

        register_capability_tools(mcp_mock, lambda: registry)

        result = await tools["get_registry_summary"]()
        assert result["summary"]["total_registrations"] == 2
        assert len(result["registrations"]) == 2

        quality_reg = next(r for r in result["registrations"] if r["name"] == "quality")
        assert quality_reg["has_invoke"] is True
        assert quality_reg["type"] == "agent"

        jtms_reg = next(r for r in result["registrations"] if r["name"] == "jtms")
        assert jtms_reg["has_invoke"] is False
        assert jtms_reg["type"] == "service"
