"""MCP Client Library.

A Python client library for the Model Context Protocol (MCP),
enabling communication with MCP servers via stdio transport.

Usage:
    >>> from libs.mcp.client import MCPSession, create_session
    >>> session = await create_session(command=["python", "-m", "my_server"])
    >>> tools = await session.list_tools()
    >>> result = await session.call_tool("my_tool", {"arg": "value"})
    >>> await session.close()
"""

from .session import MCPSession, MCPSessionError, create_session
from .stdio import StdioTransport, ProcessStdioTransport
from .models import (
    # Core types
    JSONRPCRequest as Request,
    JSONRPCResponse as Response,
    JSONRPCError as Error,
    # Domain types
    Tool,
    ToolCallParams,
    ToolCallResult,
    Resource,
    ResourceContents,
    Prompt,
    PromptMessage,
    # Initialization
    InitializeParams,
    InitializeResult,
    ServerCapabilities,
    # Errors
    ErrorCode,
)

__all__ = [
    # Session
    "MCPSession",
    "MCPSessionError",
    "create_session",
    # Transport
    "StdioTransport",
    "ProcessStdioTransport",
    # Models
    "Request",
    "Response",
    "Error",
    "Tool",
    "ToolCallParams",
    "ToolCallResult",
    "Resource",
    "ResourceContents",
    "Prompt",
    "PromptMessage",
    "InitializeParams",
    "InitializeResult",
    "ServerCapabilities",
    "ErrorCode",
]

__version__ = "0.1.0"
