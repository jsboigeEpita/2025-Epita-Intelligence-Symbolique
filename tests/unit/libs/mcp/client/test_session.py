"""Tests for MCP client session.

Unit tests for the MCPSession class defined in libs/mcp/client/session.py.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from libs.mcp.client.session import MCPSession, MCPSessionError, create_session
from libs.mcp.client.stdio import StdioTransport
from libs.mcp.client.models import (
    InitializeParams,
    InitializeResult,
    ServerCapabilities,
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCError,
    Tool,
    ToolCallResult,
)


class MockTransport(StdioTransport):
    """Mock transport for testing."""

    def __init__(self, responses=None):
        super().__init__()
        self.sent = []
        self.responses = responses or []
        self.response_index = 0

    async def send(self, request):
        self.sent.append(request)

    async def receive(self):
        if self.response_index >= len(self.responses):
            raise EOFError("No more responses")
        response = self.responses[self.response_index]
        self.response_index += 1
        return response


class TestMCPSession:
    """Tests for MCPSession."""

    def test_init_creates_session(self):
        """MCPSession initializes with transport and params."""
        transport = MagicMock()
        params = InitializeParams()

        session = MCPSession(transport, params)

        assert session._transport is transport
        assert session._init_params is params
        assert not session.is_initialized
        assert session.capabilities is None

    @pytest.mark.asyncio
    async def test_initialize_sends_request(self):
        """MCPSession.initialize() sends initialize request."""
        transport = MagicMock()
        transport.send = AsyncMock()
        transport.receive = AsyncMock(
            return_value=JSONRPCResponse(
                id=1,
                result={
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "test-server"},
                },
            )
        )

        session = MCPSession(transport)
        await session.initialize()

        transport.send.assert_called_once()
        request = transport.send.call_args[0][0]
        assert request.method == "initialize"
        assert request.params["protocolVersion"] == "2024-11-05"

    @pytest.mark.asyncio
    async def test_initialize_sets_initialized_flag(self):
        """MCPSession.initialize() sets is_initialized flag."""
        transport = MagicMock()
        transport.send = AsyncMock()
        transport.receive = AsyncMock(
            return_value=JSONRPCResponse(
                id=1,
                result={
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                },
            )
        )

        session = MCPSession(transport)
        assert not session.is_initialized

        await session.initialize()

        assert session.is_initialized

    @pytest.mark.asyncio
    async def test_initialize_stores_capabilities(self):
        """MCPSession.initialize() stores server capabilities."""
        transport = MagicMock()
        transport.send = AsyncMock()
        transport.receive = AsyncMock(
            return_value=JSONRPCResponse(
                id=1,
                result={
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {"listChanged": True},
                        "resources": {},
                    },
                },
            )
        )

        session = MCPSession(transport)
        await session.initialize()

        assert session.capabilities is not None
        assert session.capabilities.tools is not None
        assert session.capabilities.tools["listChanged"] is True

    @pytest.mark.asyncio
    async def test_initialize_raises_on_error_response(self):
        """MCPSession.initialize() raises MCPSessionError on error."""
        transport = MagicMock()
        transport.send = AsyncMock()
        transport.receive = AsyncMock(
            return_value=JSONRPCResponse(
                id=1,
                error=JSONRPCError(code=-32600, message="Invalid Request"),
            )
        )

        session = MCPSession(transport)

        with pytest.raises(MCPSessionError, match="Initialization failed"):
            await session.initialize()

    @pytest.mark.asyncio
    async def test_initialize_raises_when_already_initialized(self):
        """MCPSession.initialize() raises when called twice."""
        transport = MagicMock()
        transport.send = AsyncMock()
        transport.receive = AsyncMock(
            return_value=JSONRPCResponse(
                id=1,
                result={"protocolVersion": "2024-11-05", "capabilities": {}},
            )
        )

        session = MCPSession(transport)
        await session.initialize()

        with pytest.raises(MCPSessionError, match="already initialized"):
            await session.initialize()

    @pytest.mark.asyncio
    async def test_list_tools_sends_request(self):
        """MCPSession.list_tools() sends tools/list request."""
        transport = MagicMock()
        transport.send = AsyncMock()
        transport.receive = AsyncMock(
            return_value=JSONRPCResponse(
                id=2,
                result={
                    "tools": [
                        {
                            "name": "test_tool",
                            "description": "A test tool",
                            "inputSchema": {"type": "object"},
                        }
                    ]
                },
            )
        )

        session = MCPSession(transport)
        session._initialized = True

        tools = await session.list_tools()

        transport.send.assert_called()
        request = transport.send.call_args[0][0]
        assert request.method == "tools/list"
        assert len(tools) == 1
        assert tools[0].name == "test_tool"

    @pytest.mark.asyncio
    async def test_list_tools_raises_when_not_initialized(self):
        """MCPSession.list_tools() raises when not initialized."""
        transport = MagicMock()
        session = MCPSession(transport)

        with pytest.raises(MCPSessionError, match="not initialized"):
            await session.list_tools()

    @pytest.mark.asyncio
    async def test_call_tool_sends_request(self):
        """MCPSession.call_tool() sends tools/call request."""
        transport = MagicMock()
        transport.send = AsyncMock()
        transport.receive = AsyncMock(
            return_value=JSONRPCResponse(
                id=2,
                result={
                    "content": [{"type": "text", "text": "Result"}],
                    "isError": False,
                },
            )
        )

        session = MCPSession(transport)
        session._initialized = True

        result = await session.call_tool("my_tool", {"arg": "value"})

        transport.send.assert_called()
        request = transport.send.call_args[0][0]
        assert request.method == "tools/call"
        assert request.params["name"] == "my_tool"
        assert request.params["arguments"] == {"arg": "value"}
        assert not result.isError

    @pytest.mark.asyncio
    async def test_list_resources_sends_request(self):
        """MCPSession.list_resources() sends resources/list request."""
        transport = MagicMock()
        transport.send = AsyncMock()
        transport.receive = AsyncMock(
            return_value=JSONRPCResponse(
                id=2,
                result={
                    "resources": [
                        {
                            "uri": "file:///test.txt",
                            "name": "test.txt",
                        }
                    ]
                },
            )
        )

        session = MCPSession(transport)
        session._initialized = True
        session._server_capabilities = ServerCapabilities(resources={})

        resources = await session.list_resources()

        transport.send.assert_called()
        request = transport.send.call_args[0][0]
        assert request.method == "resources/list"
        assert len(resources) == 1

    @pytest.mark.asyncio
    async def test_list_resources_raises_without_capability(self):
        """MCPSession.list_resources() raises without resources capability."""
        transport = AsyncMock()
        session = MCPSession(transport)
        session._initialized = True
        # ServerCapabilities() defaults resources=None → capability check should raise
        session._server_capabilities = ServerCapabilities()

        with pytest.raises(MCPSessionError, match="not supported"):
            await session.list_resources()

    @pytest.mark.asyncio
    async def test_close_sends_shutdown(self):
        """MCPSession.close() sends shutdown notification."""
        transport = MagicMock()
        transport.send = AsyncMock()

        session = MCPSession(transport)
        session._initialized = True

        await session.close()

        assert transport.send.call_count >= 1
        assert not session.is_initialized


class TestCreateSession:
    """Tests for create_session convenience function."""

    @pytest.mark.asyncio
    async def test_create_session_with_command(self):
        """create_session() creates ProcessStdioTransport with command."""
        # Use echo as a safe test command that outputs valid JSON
        session = await create_session(
            command=["python", "-c", "import sys; print('{\"jsonrpc\":\"2.0\",\"id\":1,\"result\":{\"protocolVersion\":\"2024-11-05\",\"capabilities\":{}}}'); sys.stdout.flush()"]
        )

        try:
            assert session.is_initialized
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_create_session_raises_without_command_or_transport(self):
        """create_session() raises ValueError without command or transport."""
        with pytest.raises(ValueError, match="Either command or transport"):
            await create_session()
