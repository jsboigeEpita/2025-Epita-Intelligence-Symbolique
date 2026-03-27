"""Tests for MCP client models.

Unit tests for the MCP data models defined in libs/mcp/client/models.py.
"""

import pytest

from libs.mcp.client.models import (
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCError,
    Tool,
    ToolCallParams,
    ToolCallResult,
    Resource,
    ResourceContents,
    Prompt,
    ServerCapabilities,
    InitializeParams,
    InitializeResult,
    ErrorCode,
)


class TestJSONRPCTypes:
    """Tests for JSON-RPC base types."""

    def test_request_to_dict(self):
        """JSONRPCRequest.to_dict() produces valid dictionary."""
        request = JSONRPCRequest(id=1, method="test_method", params={"arg": "value"})
        result = request.to_dict()

        assert result["jsonrpc"] == "2.0"
        assert result["id"] == 1
        assert result["method"] == "test_method"
        assert result["params"] == {"arg": "value"}

    def test_request_to_dict_without_params(self):
        """JSONRPCRequest.to_dict() omits params when None."""
        request = JSONRPCRequest(id=2, method="no_params")
        result = request.to_dict()

        assert "params" not in result
        assert result["method"] == "no_params"

    def test_response_from_dict_success(self):
        """JSONRPCResponse.from_dict() parses success response."""
        data = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"status": "ok"},
        }
        response = JSONRPCResponse.from_dict(data)

        assert response.id == 1
        assert response.result == {"status": "ok"}
        assert response.error is None
        assert not response.is_error()

    def test_response_from_dict_error(self):
        """JSONRPCResponse.from_dict() parses error response."""
        data = {
            "jsonrpc": "2.0",
            "id": 2,
            "error": {"code": -32600, "message": "Invalid Request"},
        }
        response = JSONRPCResponse.from_dict(data)

        assert response.id == 2
        assert response.result is None
        assert response.error is not None
        assert response.error.code == -32600
        assert response.error.message == "Invalid Request"
        assert response.is_error()


class TestDomainModels:
    """Tests for MCP domain-specific models."""

    def test_tool_model(self):
        """Tool model represents tool definition."""
        tool = Tool(
            name="test_tool",
            description="A test tool",
            inputSchema={"type": "object"},
        )

        assert tool.name == "test_tool"
        assert tool.description == "A test tool"
        assert tool.inputSchema == {"type": "object"}

    def test_tool_call_params(self):
        """ToolCallParams represents tool call parameters."""
        params = ToolCallParams(name="my_tool", arguments={"x": 1})

        assert params.name == "my_tool"
        assert params.arguments == {"x": 1}

    def test_tool_call_params_without_arguments(self):
        """ToolCallParams defaults arguments to None."""
        params = ToolCallParams(name="no_args_tool")

        assert params.name == "no_args_tool"
        assert params.arguments is None

    def test_tool_call_result(self):
        """ToolCallResult represents tool execution result."""
        result = ToolCallResult(
            content=[{"type": "text", "text": "Output"}],
            isError=False,
        )

        assert len(result.content) == 1
        assert result.content[0]["text"] == "Output"
        assert not result.isError

    def test_resource_model(self):
        """Resource model represents resource reference."""
        resource = Resource(
            uri="file:///test.txt",
            name="test.txt",
            description="A test resource",
            mimeType="text/plain",
        )

        assert resource.uri == "file:///test.txt"
        assert resource.name == "test.txt"
        assert resource.description == "A test resource"
        assert resource.mimeType == "text/plain"

    def test_resource_contents(self):
        """ResourceContents represents resource data."""
        contents = ResourceContents(
            uri="file:///test.txt",
            mimeType="text/plain",
            text="Hello, world!",
        )

        assert contents.uri == "file:///test.txt"
        assert contents.text == "Hello, world!"
        assert contents.blob is None

    def test_prompt_model(self):
        """Prompt model represents prompt definition."""
        prompt = Prompt(
            name="test_prompt",
            description="A test prompt",
            arguments=[{"name": "topic", "description": "Topic to write about"}],
        )

        assert prompt.name == "test_prompt"
        assert prompt.description == "A test prompt"
        assert len(prompt.arguments) == 1


class TestInitializationModels:
    """Tests for MCP initialization models."""

    def test_initialize_params_default(self):
        """InitializeParams has sensible defaults."""
        params = InitializeParams()

        assert params.protocolVersion == "2024-11-05"
        assert params.capabilities == {}
        assert params.clientInfo is None

    def test_initialize_params_to_dict(self):
        """InitializeParams.to_dict() produces valid dictionary."""
        params = InitializeParams(
            protocolVersion="2024-11-05",
            capabilities={"tools": {}},
            clientInfo={"name": "test-client", "version": "1.0"},
        )
        result = params.to_dict()

        assert result["protocolVersion"] == "2024-11-05"
        assert result["capabilities"] == {"tools": {}}
        assert result["clientInfo"] == {"name": "test-client", "version": "1.0"}

    def test_initialize_result_from_dict(self):
        """InitializeResult.from_dict() parses server response."""
        data = {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {"listChanged": True},
                "resources": {},
            },
            "serverInfo": {"name": "test-server", "version": "1.0"},
        }
        result = InitializeResult.from_dict(data)

        assert result.protocolVersion == "2024-11-05"
        assert result.capabilities.tools is not None
        assert result.capabilities.tools["listChanged"] is True
        assert result.capabilities.resources is not None
        assert result.serverInfo["name"] == "test-server"

    def test_server_capabilities_partial(self):
        """ServerCapabilities handles partial capabilities."""
        caps = ServerCapabilities(tools={"listChanged": True})

        assert caps.tools is not None
        assert caps.resources is None
        assert caps.prompts is None


class TestErrorCode:
    """Tests for MCP error codes."""

    def test_reserved_error_codes(self):
        """ErrorCode includes JSON-RPC reserved codes."""
        assert ErrorCode.PARSE_ERROR == -32700
        assert ErrorCode.INVALID_REQUEST == -32600
        assert ErrorCode.METHOD_NOT_FOUND == -32601
        assert ErrorCode.INVALID_PARAMS == -32602
        assert ErrorCode.INTERNAL_ERROR == -32603

    def test_mcp_specific_error_codes(self):
        """ErrorCode includes MCP-specific codes."""
        assert ErrorCode.REQUEST_CANCELLED == -32800
        assert ErrorCode.METHOD_NOT_IMPLEMENTED == -32801
