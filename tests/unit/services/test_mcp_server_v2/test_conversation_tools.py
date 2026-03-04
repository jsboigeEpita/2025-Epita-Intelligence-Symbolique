"""Tests for MCP conversation tools."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from argumentation_analysis.services.mcp_server.session_manager import (
    SessionManager,
    SessionState,
)


@dataclass
class MockTurnResult:
    turn_number: int = 1
    phase_results: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.75
    needs_refinement: bool = False
    questions_for_user: List[str] = field(default_factory=list)
    duration_seconds: float = 0.5


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


def _make_conversation_patches(catalog, mock_strategy):
    """Create the standard patch set for conversation tool tests."""
    return [
        patch(
            "argumentation_analysis.orchestration.unified_pipeline.get_workflow_catalog",
            return_value=catalog,
        ),
        patch(
            "argumentation_analysis.orchestration.unified_pipeline.CAPABILITY_STATE_WRITERS",
            {},
            create=True,
        ),
        patch(
            "argumentation_analysis.orchestration.conversational_executor.WorkflowTurnStrategy",
            return_value=mock_strategy,
        ),
    ]


class TestStartConversation:
    """Tests for start_conversation tool."""

    @pytest.mark.asyncio
    async def test_start_creates_session(self):
        mcp_mock, tools = _setup_tools()
        sm = SessionManager()
        mock_registry = MagicMock()

        catalog = {
            "standard": MockWorkflowDefinition(
                "standard", [MockWorkflowPhase("p1", "quality")]
            )
        }

        mock_strategy = MagicMock()
        mock_strategy.execute_turn = AsyncMock(return_value=MockTurnResult())

        from argumentation_analysis.services.mcp_server.tools.conversation_tools import (
            register_conversation_tools,
        )
        register_conversation_tools(mcp_mock, lambda: mock_registry, lambda: sm)

        patches = _make_conversation_patches(catalog, mock_strategy)
        with patches[0], patches[1], patches[2]:
            result = await tools["start_conversation"](
                text="Analyze this", workflow_name="standard"
            )

        assert "session_id" in result
        assert result["status"] == "active"
        assert result["round"] == 1

    @pytest.mark.asyncio
    async def test_start_with_custom_config(self):
        mcp_mock, tools = _setup_tools()
        sm = SessionManager()
        mock_registry = MagicMock()

        catalog = {
            "full": MockWorkflowDefinition(
                "full", [MockWorkflowPhase("p1", "quality")]
            )
        }

        mock_strategy = MagicMock()
        mock_strategy.execute_turn = AsyncMock(return_value=MockTurnResult())

        from argumentation_analysis.services.mcp_server.tools.conversation_tools import (
            register_conversation_tools,
        )
        register_conversation_tools(mcp_mock, lambda: mock_registry, lambda: sm)

        patches = _make_conversation_patches(catalog, mock_strategy)
        with patches[0], patches[1], patches[2]:
            result = await tools["start_conversation"](
                text="Test", workflow_name="full", max_rounds=5
            )

        assert result["max_rounds"] == 5


class TestContinueConversation:
    """Tests for continue_conversation tool."""

    @pytest.mark.asyncio
    async def test_continue_existing_session(self):
        mcp_mock, tools = _setup_tools()
        sm = SessionManager()
        session = sm.create_session("Test")
        sm.update_session(session.session_id, {"round": 1, "status": "completed"})

        mock_registry = MagicMock()
        catalog = {
            "standard": MockWorkflowDefinition(
                "standard", [MockWorkflowPhase("p1", "quality")]
            )
        }

        mock_strategy = MagicMock()
        mock_strategy.execute_turn = AsyncMock(
            return_value=MockTurnResult(turn_number=2)
        )

        from argumentation_analysis.services.mcp_server.tools.conversation_tools import (
            register_conversation_tools,
        )
        register_conversation_tools(mcp_mock, lambda: mock_registry, lambda: sm)

        patches = _make_conversation_patches(catalog, mock_strategy)
        with patches[0], patches[1], patches[2]:
            result = await tools["continue_conversation"](
                session_id=session.session_id
            )

        assert result["status"] == "active"
        assert result["round"] == 2

    @pytest.mark.asyncio
    async def test_continue_nonexistent_session(self):
        mcp_mock, tools = _setup_tools()
        sm = SessionManager()

        from argumentation_analysis.services.mcp_server.tools.conversation_tools import (
            register_conversation_tools,
        )
        register_conversation_tools(mcp_mock, lambda: MagicMock(), lambda: sm)

        result = await tools["continue_conversation"](session_id="nonexistent")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_continue_max_rounds_reached(self):
        mcp_mock, tools = _setup_tools()
        sm = SessionManager()
        session = sm.create_session("Test", config={"max_rounds": 2})
        sm.update_session(session.session_id, {"round": 1})
        sm.update_session(session.session_id, {"round": 2})

        from argumentation_analysis.services.mcp_server.tools.conversation_tools import (
            register_conversation_tools,
        )
        register_conversation_tools(mcp_mock, lambda: MagicMock(), lambda: sm)

        result = await tools["continue_conversation"](
            session_id=session.session_id
        )
        assert result["status"] == "max_rounds_reached"


class TestGetConversationStatus:
    """Tests for get_conversation_status tool."""

    @pytest.mark.asyncio
    async def test_get_status_existing(self):
        mcp_mock, tools = _setup_tools()
        sm = SessionManager()
        session = sm.create_session("Test", workflow_name="full")
        sm.update_session(session.session_id, {"status": "completed", "confidence": 0.8})

        from argumentation_analysis.services.mcp_server.tools.conversation_tools import (
            register_conversation_tools,
        )
        register_conversation_tools(mcp_mock, lambda: MagicMock(), lambda: sm)

        result = await tools["get_conversation_status"](
            session_id=session.session_id
        )
        assert result["workflow"] == "full"
        assert result["rounds_completed"] == 1

    @pytest.mark.asyncio
    async def test_get_status_nonexistent(self):
        mcp_mock, tools = _setup_tools()
        sm = SessionManager()

        from argumentation_analysis.services.mcp_server.tools.conversation_tools import (
            register_conversation_tools,
        )
        register_conversation_tools(mcp_mock, lambda: MagicMock(), lambda: sm)

        result = await tools["get_conversation_status"](session_id="missing")
        assert "error" in result
