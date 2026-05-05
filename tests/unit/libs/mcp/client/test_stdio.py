"""Tests for MCP stdio transport.

Unit tests for the stdio transport layer defined in libs/mcp/client/stdio.py.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

from libs.mcp.client.stdio import StdioTransport, ProcessStdioTransport
from libs.mcp.client.models import JSONRPCRequest, JSONRPCResponse


class TestStdioTransport:
    """Tests for StdioTransport."""

    def test_init_default_streams(self):
        """StdioTransport initializes with sys.stdin/stdout by default."""
        mock_stdin_buf = MagicMock()
        mock_stdout_buf = MagicMock()
        with patch("libs.mcp.client.stdio.sys") as mock_sys:
            mock_sys.stdin.buffer = mock_stdin_buf
            mock_sys.stdout.buffer = mock_stdout_buf
            transport = StdioTransport()

        assert transport is not None
        assert not transport.is_closed
        assert transport._stdin is mock_stdin_buf
        assert transport._stdout is mock_stdout_buf

    def test_init_custom_streams(self):
        """StdioTransport accepts custom streams."""
        mock_stdin = MagicMock()
        mock_stdout = MagicMock()

        transport = StdioTransport(
            stdin=mock_stdin,
            stdout=mock_stdout,
        )

        assert transport._stdin is mock_stdin
        assert transport._stdout is mock_stdout

    def test_init_with_hooks(self):
        """StdioTransport accepts read/write hooks."""
        read_hook = MagicMock()
        write_hook = MagicMock()

        transport = StdioTransport(
            stdin=MagicMock(),
            stdout=MagicMock(),
            read_hook=read_hook,
            write_hook=write_hook,
        )

        assert transport._read_hook is read_hook
        assert transport._write_hook is write_hook

    @pytest.mark.asyncio
    async def test_send_calls_write_hook(self):
        """StdioTransport.send() calls write_hook if provided."""
        # Use spec=[] to prevent MagicMock from having 'drain' attribute,
        # so send() uses the flush() path (file-like behavior, not asyncio StreamWriter)
        mock_stdin = MagicMock(spec=["write", "flush"])
        write_hook = MagicMock()

        # send() writes to _stdin (the subprocess's stdin stream)
        transport = StdioTransport(
            stdin=mock_stdin, stdout=MagicMock(), write_hook=write_hook
        )

        request = JSONRPCRequest(id=1, method="test")
        await transport.send(request)

        write_hook.assert_called_once()
        args = write_hook.call_args[0]
        assert '"method": "test"' in args[0]

    @pytest.mark.asyncio
    async def test_send_writes_to_stdin(self):
        """StdioTransport.send() writes JSON to the subprocess stdin stream."""
        # Use spec=[] to prevent MagicMock from having 'drain' attribute
        mock_stdin = MagicMock(spec=["write", "flush"])

        # send() writes to _stdin (the subprocess's stdin stream)
        transport = StdioTransport(stdin=mock_stdin, stdout=MagicMock())

        request = JSONRPCRequest(id=1, method="test", params={"key": "value"})
        await transport.send(request)

        mock_stdin.write.assert_called_once()
        written_data = mock_stdin.write.call_args[0][0]
        assert b'"method": "test"' in written_data
        assert b'"key": "value"' in written_data
        mock_stdin.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_raises_when_closed(self):
        """StdioTransport.send() raises IOError when closed."""
        transport = StdioTransport(stdin=MagicMock(), stdout=MagicMock())
        transport.close()

        request = JSONRPCRequest(id=1, method="test")

        with pytest.raises(IOError, match="Transport is closed"):
            await transport.send(request)

    @pytest.mark.asyncio
    async def test_receive_calls_read_hook(self):
        """StdioTransport.receive() calls read_hook if provided."""
        mock_stdout = MagicMock()
        read_hook = MagicMock()

        # receive() reads from _stdout (the subprocess's stdout stream)
        mock_stdout.readline = MagicMock(
            return_value=b'{"jsonrpc":"2.0","id":1,"result":{}}\n'
        )

        transport = StdioTransport(
            stdin=MagicMock(), stdout=mock_stdout, read_hook=read_hook
        )

        await transport.receive()

        read_hook.assert_called_once()

    @pytest.mark.asyncio
    async def test_receive_parses_json_response(self):
        """StdioTransport.receive() parses JSON into JSONRPCResponse."""
        mock_stdout = MagicMock()
        mock_stdout.readline = MagicMock(
            return_value=b'{"jsonrpc":"2.0","id":1,"result":{"status":"ok"}}\n'
        )

        # receive() reads from _stdout (the subprocess's stdout stream)
        transport = StdioTransport(stdin=MagicMock(), stdout=mock_stdout)

        response = await transport.receive()

        assert response.id == 1
        assert response.result == {"status": "ok"}
        assert not response.is_error()

    @pytest.mark.asyncio
    async def test_receive_raises_when_closed(self):
        """StdioTransport.receive() raises IOError when closed."""
        transport = StdioTransport(stdin=MagicMock(), stdout=MagicMock())
        transport.close()

        with pytest.raises(IOError, match="Transport is closed"):
            await transport.receive()

    def test_close_sets_closed_flag(self):
        """StdioTransport.close() sets is_closed flag."""
        transport = StdioTransport(stdin=MagicMock(), stdout=MagicMock())
        transport.close()

        assert transport.is_closed


class TestProcessStdioTransport:
    """Tests for ProcessStdioTransport."""

    def test_init_requires_command(self):
        """ProcessStdioTransport requires a command."""
        transport = ProcessStdioTransport(command=["python", "-m", "server"])

        assert transport._command == ["python", "-m", "server"]
        assert transport._process is None
        assert not transport.is_running

    def test_init_accepts_hooks(self):
        """ProcessStdioTransport accepts read/write hooks."""
        read_hook = MagicMock()
        write_hook = MagicMock()

        transport = ProcessStdioTransport(
            command=["echo"],
            read_hook=read_hook,
            write_hook=write_hook,
        )

        assert transport._read_hook is read_hook
        assert transport._write_hook is write_hook

    @pytest.mark.asyncio
    async def test_start_creates_subprocess(self):
        """ProcessStdioTransport.start() creates subprocess."""
        # Use echo as a safe test command
        transport = ProcessStdioTransport(command=["echo", "test"])

        try:
            await transport.start()

            assert transport.is_running
            assert transport.pid is not None
        finally:
            await transport.stop()

    @pytest.mark.asyncio
    async def test_start_raises_when_already_running(self):
        """ProcessStdioTransport.start() raises when already running."""
        transport = ProcessStdioTransport(command=["echo", "test"])

        try:
            await transport.start()

            with pytest.raises(RuntimeError, match="already running"):
                await transport.start()
        finally:
            await transport.stop()

    @pytest.mark.asyncio
    async def test_stop_terminates_process(self):
        """ProcessStdioTransport.stop() terminates the subprocess."""
        transport = ProcessStdioTransport(command=["echo", "test"])

        await transport.start()
        assert transport.is_running

        await transport.stop()

        assert not transport.is_running
        assert transport._process is None

    @pytest.mark.asyncio
    async def test_stop_idempotent(self):
        """ProcessStdioTransport.stop() is idempotent."""
        transport = ProcessStdioTransport(command=["echo", "test"])

        await transport.start()
        await transport.stop()

        # Should not raise
        await transport.stop()

        assert not transport.is_running

    @pytest.mark.asyncio
    async def test_send_receive_with_process(self):
        """ProcessStdioTransport can send and receive to subprocess."""
        # Use Python to echo JSON-RPC responses
        transport = ProcessStdioTransport(
            command=[
                "python",
                "-c",
                'import sys; print(\'{"jsonrpc":"2.0","id":1,"result":{}}\')',
            ]
        )

        try:
            await transport.start()

            request = JSONRPCRequest(id=1, method="test")
            await transport.send(request)

            response = await transport.receive()

            assert response.id == 1
            assert not response.is_error()
        finally:
            await transport.stop()
