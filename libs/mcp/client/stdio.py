"""MCP stdio transport implementation.

This module provides stdio-based communication with MCP servers,
as per the MCP transport specification.
"""

import asyncio
import json
import sys
from typing import Optional, Callable, Any

from .models import JSONRPCRequest, JSONRPCResponse


class StdioTransport:
    """Transport layer for MCP communication via stdin/stdout.

    This transport is used when the MCP server is a subprocess
    that communicates via JSON-RPC messages over stdio.
    """

    def __init__(
        self,
        stdin: Any = None,
        stdout: Any = None,
        read_hook: Optional[Callable[[str], None]] = None,
        write_hook: Optional[Callable[[str], None]] = None,
    ):
        """Initialize the stdio transport.

        Args:
            stdin: Input stream (default: sys.stdin.buffer)
            stdout: Output stream (default: sys.stdout.buffer)
            read_hook: Optional hook called for each incoming message
            write_hook: Optional hook called for each outgoing message
        """
        self._stdin = stdin or sys.stdin.buffer
        self._stdout = stdout or sys.stdout.buffer
        self._read_hook = read_hook
        self._write_hook = write_hook
        self._closed = False

    async def send(self, request: JSONRPCRequest) -> None:
        """Send a JSON-RPC request to the server.

        Args:
            request: The JSON-RPC request to send

        Raises:
            IOError: If the transport is closed
        """
        if self._closed:
            raise IOError("Transport is closed")

        message = json.dumps(request.to_dict())
        data = (message + "\n").encode("utf-8")

        if self._write_hook:
            self._write_hook(message)

        self._stdout.write(data)
        self._stdout.flush()

    async def receive(self) -> JSONRPCResponse:
        """Receive a JSON-RPC response from the server.

        Returns:
            The JSON-RPC response

        Raises:
            IOError: If the transport is closed or data is invalid
            json.JSONDecodeError: If the response is not valid JSON
        """
        if self._closed:
            raise IOError("Transport is closed")

        line = await self._readline()
        if not line:
            raise EOFError("Unexpected end of input")

        if self._read_hook:
            self._read_hook(line.decode("utf-8"))

        data = json.loads(line)
        return JSONRPCResponse.from_dict(data)

    async def _readline(self) -> bytes:
        """Read a line from stdin asynchronously.

        This is a workaround for Python's lack of async stdin.
        In a real implementation, this would use proper async I/O.
        """
        # For now, use blocking read - in production, use proper async
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._stdin.readline)

    def close(self) -> None:
        """Close the transport."""
        self._closed = True

    @property
    def is_closed(self) -> bool:
        """Check if the transport is closed."""
        return self._closed


class ProcessStdioTransport(StdioTransport):
    """Transport for MCP server running as a subprocess.

    This transport manages a subprocess and communicates with it
    via stdin/stdout pipes.
    """

    def __init__(
        self,
        command: list[str],
        read_hook: Optional[Callable[[str], None]] = None,
        write_hook: Optional[Callable[[str], None]] = None,
    ):
        """Initialize the process transport.

        Args:
            command: Command and arguments to start the MCP server
            read_hook: Optional hook for incoming messages
            write_hook: Optional hook for outgoing messages
        """
        self._command = command
        self._process: Optional[Any] = None

        # Process will be started in start()
        super().__init__(
            stdin=None,  # Will be set from process
            stdout=None,  # Will be set from process
            read_hook=read_hook,
            write_hook=write_hook,
        )

    async def start(self) -> None:
        """Start the MCP server subprocess.

        Raises:
            RuntimeError: If the process is already running or fails to start
        """
        if self._process is not None:
            raise RuntimeError("Process is already running")

        try:
            # Import asyncio subprocess here to avoid circular imports
            import asyncio.subprocess

            self._process = await asyncio.create_subprocess_exec(
                *self._command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Set stdin/stdout from the process
            self._stdin = self._process.stdin
            self._stdout = self._process.stdout
            self._closed = False

        except Exception as e:
            raise RuntimeError(f"Failed to start MCP server: {e}") from e

    async def stop(self) -> None:
        """Stop the MCP server subprocess."""
        if self._process is None:
            return

        try:
            self._process.terminate()
            await self._process.wait()
        except Exception:
            self._process.kill()
            await self._process.wait()
        finally:
            self._process = None
            self._closed = True

    @property
    def pid(self) -> Optional[int]:
        """Get the process ID if running."""
        return self._process.pid if self._process else None

    @property
    def is_running(self) -> bool:
        """Check if the subprocess is running."""
        return self._process is not None and self._process.returncode is None

    async def _readline(self) -> bytes:
        """Read a line from the subprocess stdout."""
        if self._process is None or self._process.stdout is None:
            raise IOError("Process is not running")

        return await self._process.stdout.readline()
