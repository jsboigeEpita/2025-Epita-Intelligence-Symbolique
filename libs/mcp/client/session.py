"""MCP Client Session implementation.

This module provides a high-level client session for communicating
with MCP servers, handling initialization, tool calls, and resource access.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from .models import (
    InitializeParams,
    InitializeResult,
    JSONRPCRequest,
    JSONRPCResponse,
    ServerCapabilities,
    Tool,
    ToolCallParams,
    ToolCallResult,
    Resource,
    ResourceContents,
    Prompt,
)
from .stdio import StdioTransport, ProcessStdioTransport


logger = logging.getLogger(__name__)


class MCPSessionError(Exception):
    """Base exception for MCP session errors."""

    pass


class MCPSession:
    """Client session for communicating with an MCP server.

    This session handles the full MCP protocol lifecycle:
    1. Initialize connection with handshake
    2. List/call tools
    3. Access resources
    4. Access prompts
    5. Shutdown gracefully
    """

    def __init__(
        self,
        transport: StdioTransport,
        init_params: Optional[InitializeParams] = None,
    ):
        """Initialize the MCP session.

        Args:
            transport: The transport layer for communication
            init_params: Optional initialization parameters
        """
        self._transport = transport
        self._init_params = init_params or InitializeParams()
        self._initialized = False
        self._request_id = 0
        self._server_capabilities: Optional[ServerCapabilities] = None
        self._server_info: Optional[Dict[str, str]] = None

    async def initialize(self) -> InitializeResult:
        """Initialize the MCP session with the server.

        Returns:
            The initialization result from the server

        Raises:
            MCPSessionError: If initialization fails
        """
        if self._initialized:
            raise MCPSessionError("Session is already initialized")

        request = JSONRPCRequest(
            id=self._next_id(),
            method="initialize",
            params=self._init_params.to_dict(),
        )

        response = await self._send_request(request)

        if response.is_error():
            raise MCPSessionError(
                f"Initialization failed: {response.error.message} "
                f"(code: {response.error.code})"
            )

        self._initialized = True
        result = InitializeResult.from_dict(response.result)
        self._server_capabilities = result.capabilities
        self._server_info = result.serverInfo

        logger.info(
            f"Initialized MCP session (protocol: {result.protocolVersion}, "
            f"server: {result.serverInfo})"
        )

        return result

    async def list_tools(self) -> List[Tool]:
        """List all available tools from the server.

        Returns:
            List of available tools

        Raises:
            MCPSessionError: If not initialized or request fails
        """
        self._ensure_initialized()

        request = JSONRPCRequest(id=self._next_id(), method="tools/list")
        response = await self._send_request(request)

        if response.is_error():
            raise MCPSessionError(
                f"Failed to list tools: {response.error.message} "
                f"(code: {response.error.code})"
            )

        tools_data = response.result.get("tools", [])
        return [Tool(**tool) for tool in tools_data]

    async def call_tool(
        self, name: str, arguments: Optional[Dict[str, Any]] = None
    ) -> ToolCallResult:
        """Call a tool on the MCP server.

        Args:
            name: The name of the tool to call
            arguments: Optional arguments for the tool

        Returns:
            The result from the tool call

        Raises:
            MCPSessionError: If not initialized or call fails
        """
        self._ensure_initialized()

        params = ToolCallParams(name=name, arguments=arguments)
        request = JSONRPCRequest(
            id=self._next_id(),
            method="tools/call",
            params={"name": params.name, "arguments": params.arguments},
        )

        response = await self._send_request(request)

        if response.is_error():
            raise MCPSessionError(
                f"Tool call failed: {response.error.message} "
                f"(code: {response.error.code})"
            )

        result_data = response.result
        return ToolCallResult(
            content=result_data.get("content", []),
            isError=result_data.get("isError", False),
        )

    async def list_resources(self) -> List[Resource]:
        """List all available resources from the server.

        Returns:
            List of available resources

        Raises:
            MCPSessionError: If not supported or request fails
        """
        self._ensure_initialized()
        self._check_capability("resources")

        request = JSONRPCRequest(id=self._next_id(), method="resources/list")
        response = await self._send_request(request)

        if response.is_error():
            raise MCPSessionError(
                f"Failed to list resources: {response.error.message} "
                f"(code: {response.error.code})"
            )

        resources_data = response.result.get("resources", [])
        return [Resource(**resource) for resource in resources_data]

    async def read_resource(self, uri: str) -> ResourceContents:
        """Read a resource from the server.

        Args:
            uri: The URI of the resource to read

        Returns:
            The resource contents

        Raises:
            MCPSessionError: If not supported or read fails
        """
        self._ensure_initialized()
        self._check_capability("resources")

        request = JSONRPCRequest(
            id=self._next_id(),
            method="resources/read",
            params={"uri": uri},
        )

        response = await self._send_request(request)

        if response.is_error():
            raise MCPSessionError(
                f"Failed to read resource: {response.error.message} "
                f"(code: {response.error.code})"
            )

        return ResourceContents(**response.result)

    async def list_prompts(self) -> List[Prompt]:
        """List all available prompts from the server.

        Returns:
            List of available prompts

        Raises:
            MCPSessionError: If not supported or request fails
        """
        self._ensure_initialized()
        self._check_capability("prompts")

        request = JSONRPCRequest(id=self._next_id(), method="prompts/list")
        response = await self._send_request(request)

        if response.is_error():
            raise MCPSessionError(
                f"Failed to list prompts: {response.error.message} "
                f"(code: {response.error.code})"
            )

        prompts_data = response.result.get("prompts", [])
        return [Prompt(**prompt) for prompt in prompts_data]

    async def close(self) -> None:
        """Close the MCP session gracefully.

        Sends a shutdown notification to the server.
        """
        if not self._initialized:
            return

        try:
            # Shutdown is a notification (no response expected)
            request = JSONRPCRequest(id=self._next_id(), method="shutdown")
            await self._transport.send(request)

            # Send goodbye notification
            await self._transport.send(
                JSONRPCRequest(method="notifications/initialized")
            )

        except Exception as e:
            logger.warning(f"Error during shutdown: {e}")

        self._initialized = False

    async def _send_request(self, request: JSONRPCRequest) -> JSONRPCResponse:
        """Send a request and wait for the response.

        Args:
            request: The request to send

        Returns:
            The response from the server

        Raises:
            MCPSessionError: If communication fails
        """
        try:
            await self._transport.send(request)
            return await self._transport.receive()
        except Exception as e:
            raise MCPSessionError(f"Communication error: {e}") from e

    def _next_id(self) -> int:
        """Get the next request ID."""
        self._request_id += 1
        return self._request_id

    def _ensure_initialized(self) -> None:
        """Raise an error if the session is not initialized."""
        if not self._initialized:
            raise MCPSessionError("Session is not initialized")

    def _check_capability(self, capability: str) -> None:
        """Raise an error if the capability is not supported.

        Args:
            capability: The capability name to check

        Raises:
            MCPSessionError: If capability is not supported
        """
        if self._server_capabilities is None:
            raise MCPSessionError("Server capabilities not available")

        if getattr(self._server_capabilities, capability, None) is None:
            raise MCPSessionError(f"Capability '{capability}' is not supported")

    @property
    def capabilities(self) -> Optional[ServerCapabilities]:
        """Get the server capabilities."""
        return self._server_capabilities

    @property
    def server_info(self) -> Optional[Dict[str, str]]:
        """Get the server information."""
        return self._server_info

    @property
    def is_initialized(self) -> bool:
        """Check if the session is initialized."""
        return self._initialized


async def create_session(
    command: Optional[List[str]] = None,
    transport: Optional[StdioTransport] = None,
    init_params: Optional[InitializeParams] = None,
) -> MCPSession:
    """Create and initialize an MCP session.

    Convenience function to create a session with a subprocess transport.

    Args:
        command: Command to start the MCP server subprocess
        transport: Optional custom transport (overrides command)
        init_params: Optional initialization parameters

    Returns:
        An initialized MCP session

    Raises:
        MCPSessionError: If session creation or initialization fails

    Example:
        >>> session = await create_session(command=["python", "-m", "my_mcp_server"])
        >>> tools = await session.list_tools()
        >>> await session.close()
    """
    if transport is None:
        if command is None:
            raise ValueError("Either command or transport must be provided")

        transport = ProcessStdioTransport(command)
        if isinstance(transport, ProcessStdioTransport):
            await transport.start()

    session = MCPSession(transport, init_params)
    await session.initialize()
    return session
