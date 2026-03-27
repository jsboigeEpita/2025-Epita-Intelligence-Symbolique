"""MCP (Model Context Protocol) data models.

This module defines the core data structures for the MCP protocol,
which enables communication between AI applications and external tools.
Based on the MCP specification (https://modelcontextprotocol.io).

Reference: https://spec.modelcontextprotocol.io/specification/
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from enum import Enum


class ErrorCode(int, Enum):
    """MCP error codes as per specification."""

    # JSON-RPC reserved codes
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    # MCP-specific error codes
    REQUEST_CANCELLED = -32800
    METHOD_NOT_IMPLEMENTED = -32801


@dataclass
class JSONRPCRequest:
    """JSON-RPC 2.0 request."""

    jsonrpc: str = "2.0"
    id: Union[str, int] = 0
    method: str = ""
    params: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {"jsonrpc": self.jsonrpc, "id": self.id, "method": self.method}
        if self.params:
            result["params"] = self.params
        return result


@dataclass
class JSONRPCResponse:
    """JSON-RPC 2.0 response."""

    jsonrpc: str = "2.0"
    id: Union[str, int, None] = None
    result: Optional[Any] = None
    error: Optional["JSONRPCError"] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JSONRPCResponse":
        """Create from dictionary (JSON deserialization)."""
        error_data = data.get("error")
        error = JSONRPCError(**error_data) if error_data else None
        return cls(id=data.get("id"), result=data.get("result"), error=error)

    def is_error(self) -> bool:
        """Check if this response is an error."""
        return self.error is not None


@dataclass
class JSONRPCError:
    """JSON-RPC 2.0 error."""

    code: int
    message: str
    data: Optional[Any] = None


@dataclass
class Tool:
    """MCP Tool definition."""

    name: str
    description: str
    inputSchema: Dict[str, Any]


@dataclass
class ToolCallParams:
    """Parameters for calling a tool."""

    name: str
    arguments: Optional[Dict[str, Any]] = None


@dataclass
class ToolCallResult:
    """Result from a tool call."""

    content: List[Any]
    isError: bool = False


@dataclass
class Resource:
    """MCP Resource definition."""

    uri: str
    name: str
    description: Optional[str] = None
    mimeType: Optional[str] = None


@dataclass
class ResourceContents:
    """Contents of a resource."""

    uri: str
    mimeType: Optional[str] = None
    text: Optional[str] = None
    blob: Optional[bytes] = None


@dataclass
class Prompt:
    """MCP Prompt definition."""

    name: str
    description: Optional[str] = None
    arguments: Optional[List[Dict[str, Any]]] = None


@dataclass
class PromptMessage:
    """Message in a prompt."""

    role: str
    content: Dict[str, Any]


@dataclass
class ServerCapabilities:
    """Capabilities advertised by an MCP server."""

    tools: Optional[Dict[str, Any]] = None
    resources: Optional[Dict[str, Any]] = None
    prompts: Optional[Dict[str, Any]] = None


@dataclass
class InitializeParams:
    """Parameters for initializing an MCP session."""

    protocolVersion: str = "2024-11-05"
    capabilities: Dict[str, Any] = field(default_factory=dict)
    clientInfo: Optional[Dict[str, str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "protocolVersion": self.protocolVersion,
            "capabilities": self.capabilities,
        }
        if self.clientInfo:
            result["clientInfo"] = self.clientInfo
        return result


@dataclass
class InitializeResult:
    """Result from initializing an MCP server."""

    protocolVersion: str
    capabilities: ServerCapabilities
    serverInfo: Optional[Dict[str, str]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InitializeResult":
        """Create from dictionary (JSON deserialization)."""
        caps_data = data.get("capabilities", {})
        capabilities = ServerCapabilities(
            tools=caps_data.get("tools"),
            resources=caps_data.get("resources"),
            prompts=caps_data.get("prompts"),
        )
        return cls(
            protocolVersion=data.get("protocolVersion", ""),
            capabilities=capabilities,
            serverInfo=data.get("serverInfo"),
        )


# Type aliases for convenience
Request = JSONRPCRequest
Response = JSONRPCResponse
Error = JSONRPCError
