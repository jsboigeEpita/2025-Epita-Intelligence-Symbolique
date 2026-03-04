"""Tests for MCP workflow tools."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass
from enum import Enum


# --- Helpers for building mock registries and workflows ---

class MockPhaseStatus(Enum):
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class MockPhaseResult:
    phase_name: str
    status: MockPhaseStatus
    capability: str
    component_used: str = None
    output: object = None
    error: str = None
    duration_seconds: float = 0.1


@dataclass
class MockWorkflowPhase:
    name: str
    capability: str
    optional: bool = False
    depends_on: list = None
    condition: object = None
    loop_config: object = None
    timeout_seconds: float = None

    def __post_init__(self):
        if self.depends_on is None:
            self.depends_on = []


@dataclass
class MockWorkflowDefinition:
    name: str
    phases: list

    def get_required_capabilities(self):
        return [p.capability for p in self.phases]

    def get_execution_order(self):
        return [[p.name for p in self.phases]]

    def validate(self):
        return []


def _make_catalog():
    return {
        "light": MockWorkflowDefinition(
            "light",
            [MockWorkflowPhase("p1", "argument_quality")],
        ),
        "standard": MockWorkflowDefinition(
            "standard",
            [
                MockWorkflowPhase("p1", "argument_quality"),
                MockWorkflowPhase("p2", "fallacy_detection", depends_on=["p1"]),
            ],
        ),
        "full": MockWorkflowDefinition(
            "full",
            [
                MockWorkflowPhase("p1", "argument_quality"),
                MockWorkflowPhase("p2", "fallacy_detection"),
                MockWorkflowPhase("p3", "formal_logic"),
            ],
        ),
    }


class TestListWorkflows:
    """Tests for the list_workflows tool."""

    @pytest.mark.asyncio
    async def test_list_workflows_returns_catalog(self):
        mcp_mock = MagicMock()
        tools_registered = {}

        def fake_tool():
            def wrapper(fn):
                tools_registered[fn.__name__] = fn
                return fn
            return wrapper

        mcp_mock.tool = fake_tool

        from argumentation_analysis.services.mcp_server.tools.workflow_tools import (
            register_workflow_tools,
        )
        register_workflow_tools(mcp_mock, lambda: MagicMock())

        assert "list_workflows" in tools_registered

        with patch(
            "argumentation_analysis.orchestration.unified_pipeline.get_workflow_catalog",
            return_value=_make_catalog(),
        ):
            result = await tools_registered["list_workflows"]()

        assert result["total"] == 3
        assert "light" in result["workflows"]
        assert "standard" in result["workflows"]


class TestRunWorkflow:
    """Tests for the run_workflow tool."""

    @pytest.mark.asyncio
    async def test_run_workflow_success(self):
        mcp_mock = MagicMock()
        tools_registered = {}

        def fake_tool():
            def wrapper(fn):
                tools_registered[fn.__name__] = fn
                return fn
            return wrapper

        mcp_mock.tool = fake_tool
        mock_registry = MagicMock()

        from argumentation_analysis.services.mcp_server.tools.workflow_tools import (
            register_workflow_tools,
        )
        register_workflow_tools(mcp_mock, lambda: mock_registry)

        mock_result = {
            "workflow_name": "standard",
            "phases": {
                "p1": MockPhaseResult("p1", MockPhaseStatus.COMPLETED, "argument_quality"),
            },
            "summary": {"completed": 1, "failed": 0, "skipped": 0},
            "capabilities_used": ["argument_quality"],
            "capabilities_missing": [],
            "state_snapshot": None,
        }

        with patch(
            "argumentation_analysis.orchestration.unified_pipeline.run_unified_analysis",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = await tools_registered["run_workflow"](
                text="Test text", workflow_name="standard"
            )

        assert result["workflow_name"] == "standard"
        assert "phases" in result

    @pytest.mark.asyncio
    async def test_run_workflow_unknown_name(self):
        mcp_mock = MagicMock()
        tools_registered = {}

        def fake_tool():
            def wrapper(fn):
                tools_registered[fn.__name__] = fn
                return fn
            return wrapper

        mcp_mock.tool = fake_tool

        from argumentation_analysis.services.mcp_server.tools.workflow_tools import (
            register_workflow_tools,
        )
        register_workflow_tools(mcp_mock, lambda: MagicMock())

        with patch(
            "argumentation_analysis.orchestration.unified_pipeline.run_unified_analysis",
            new_callable=AsyncMock,
            side_effect=ValueError("Unknown workflow 'nonexistent'"),
        ):
            result = await tools_registered["run_workflow"](
                text="Test", workflow_name="nonexistent"
            )

        assert "error" in result


class TestGetWorkflowDetails:
    """Tests for the get_workflow_details tool."""

    @pytest.mark.asyncio
    async def test_get_details_success(self):
        mcp_mock = MagicMock()
        tools_registered = {}

        def fake_tool():
            def wrapper(fn):
                tools_registered[fn.__name__] = fn
                return fn
            return wrapper

        mcp_mock.tool = fake_tool

        from argumentation_analysis.services.mcp_server.tools.workflow_tools import (
            register_workflow_tools,
        )
        register_workflow_tools(mcp_mock, lambda: MagicMock())

        with patch(
            "argumentation_analysis.orchestration.unified_pipeline.get_workflow_catalog",
            return_value=_make_catalog(),
        ):
            result = await tools_registered["get_workflow_details"](
                workflow_name="standard"
            )

        assert result["name"] == "standard"
        assert len(result["phases"]) == 2
        assert result["validation_errors"] == []

    @pytest.mark.asyncio
    async def test_get_details_unknown(self):
        mcp_mock = MagicMock()
        tools_registered = {}

        def fake_tool():
            def wrapper(fn):
                tools_registered[fn.__name__] = fn
                return fn
            return wrapper

        mcp_mock.tool = fake_tool

        from argumentation_analysis.services.mcp_server.tools.workflow_tools import (
            register_workflow_tools,
        )
        register_workflow_tools(mcp_mock, lambda: MagicMock())

        with patch(
            "argumentation_analysis.orchestration.unified_pipeline.get_workflow_catalog",
            return_value=_make_catalog(),
        ):
            result = await tools_registered["get_workflow_details"](
                workflow_name="nonexistent"
            )

        assert "error" in result
        assert "available" in result
