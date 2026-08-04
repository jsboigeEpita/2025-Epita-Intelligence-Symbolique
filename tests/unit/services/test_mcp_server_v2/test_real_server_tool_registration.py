"""#1576 — exercise tool registration against a REAL MCPServer (not a mock).

Context
-------
The mcp 2.x migration (#1559, PR #1575) registers our 10 tools in the
**called-form on a bound method**::

    self.mcp.tool()(self.health_check)   # self.mcp is a real MCPServer

No test exercised that against a real ``MCPServer``. The existing
``test_v1_tools_registered`` / ``test_list_includes_v2_tools`` assertions
counted *our* call sites against a ``MagicMock`` (``patch("...main.MCPServer")``
+ ``tool.return_value = lambda f: f``), which would pass even if
``MCPServer.tool()`` rejected a bound method or had changed signature —
same shape as the guard retired in #1571. A mock does not testify about
what it replaces.

This module is ADDITIVE (anti-pendule): the mock-based suites stay — they
test ``MCPService`` logic and should keep their isolation/speed. Here we
test the external contract that was previously asserted only by source
inspection: does a real ``MCPServer`` register a bound method via the
called-form, and is that method actually invokable through ``Tool.run``?

Why a probe class, not ``MCPService``
------------------------------------
``MCPService.__init__`` boots the JVM + project environment (heavy, out of
scope for the registration contract). A bound async method returning a dict
has the same *form* as ``MCPService.health_check`` (both are
``<bound method ...>``), which is what the called-form contract is about.
"""

import inspect
from typing import Any

import pytest
from mcp.server import MCPServer
from mcp.server.mcpserver.tools import Tool, ToolManager


class _Probe:
    """Stand-in for MCPService: a tool is a bound async method returning a dict."""

    async def my_tool(self) -> dict[str, Any]:
        """A probe tool. Returns ok."""
        return {"ok": True}


@pytest.fixture
def real_server_with_tool() -> tuple[MCPServer, _Probe, str, Any]:
    """A REAL MCPServer with one bound method registered via the called-form.

    This is the exact registration shape MCPService uses (``self.mcp`` is a
    real MCPServer, not a mock). If this fixture raises, the 2.x API moved.
    """
    probe = _Probe()
    server = MCPServer("probe-registration")
    returned = server.tool()(probe.my_tool)
    return server, probe, "my_tool", returned


class TestRealServerRegistration:
    """P1 — a real MCPServer registers a bound method via the called-form."""

    def test_server_exposes_tool_decorator(self) -> None:
        """Guard: if ``tool`` disappears/renames, the called-form is dead."""
        assert hasattr(MCPServer, "tool"), (
            "MCPServer no longer exposes a `tool` attribute; the called-form "
            "registration shape our code depends on has moved in this mcp version."
        )

    def test_called_form_registers_bound_method(
        self, real_server_with_tool: tuple[MCPServer, _Probe, str, Any]
    ) -> None:
        """The bound method lands in the server's tool registry by its name."""
        server, probe, name, _ = real_server_with_tool
        registry = server._tool_manager._tools
        assert name in registry, (
            f"{name!r} not in the tool registry. registry keys={sorted(registry)}. "
            "If this fails, MCPServer.tool() either rejected the bound method, "
            "deduced a different name, or the registry moved (_tool_manager._tools)."
        )
        tool = registry[name]
        assert isinstance(tool, Tool)

    def test_registered_tool_keeps_the_bound_callable(
        self, real_server_with_tool: tuple[MCPServer, _Probe, str, Any]
    ) -> None:
        """The wrapper preserves the bound method as the invokable ``fn``.

        This is what makes later invocation possible: ``tool.fn`` must be our
        bound method (same ``__name__``), not a bare reference or a no-op.
        """
        server, probe, name, _ = real_server_with_tool
        tool = server._tool_manager._tools[name]
        assert tool.fn is probe.my_tool or tool.fn.__name__ == name, (
            f"tool.fn is {tool.fn!r}; expected the bound method {name!r}. "
            "The wrapper dropped the callable — the tool would not invoke our code."
        )

    @pytest.mark.asyncio
    async def test_bound_method_is_invokable_with_positional_context(
        self, real_server_with_tool: tuple[MCPServer, _Probe, str, Any]
    ) -> None:
        """P2 — 2.x passes a positional ``context`` to ``Tool.run``/``call_tool``.

        No network: ``context`` is a stub. This is the point flagged in #1576
        where 2.x "can bite": ``ToolManager.call_tool`` and ``Tool.run`` take a
        positional ``context`` provided by the framework. We assert the contract
        on the signature AND that the bound method actually runs through it.
        """
        server, probe, name, _ = real_server_with_tool
        tool = server._tool_manager._tools[name]

        # Signature guard: if a future mcp removes/renames the positional
        # `context`, the invocation contract has shifted — fail loudly here,
        # not as an opaque TypeError inside the framework.
        run_params = inspect.signature(Tool.run).parameters
        call_params = inspect.signature(ToolManager.call_tool).parameters
        assert (
            "context" in run_params
        ), f"Tool.run no longer takes `context`; signature={dict(run_params)}."
        assert "context" in call_params, (
            f"ToolManager.call_tool no longer takes `context`; "
            f"signature={dict(call_params)}."
        )

        from unittest.mock import MagicMock

        result = await tool.run({}, context=MagicMock())
        # convert_result defaults to False -> raw return from the bound method.
        assert result == {"ok": True}, (
            f"tool.run did not return the bound method's result; got {result!r}. "
            "The bound method was not actually invoked."
        )

    @pytest.mark.asyncio
    async def test_call_tool_requires_positional_context(
        self, real_server_with_tool: tuple[MCPServer, _Probe, str, Any]
    ) -> None:
        """P2 — confirms ``context`` is required (not optional) in 2.x.

        Calling ``call_tool`` without it raises TypeError, proving the
        positional-context contract observed in the mcp 2.x source.
        """
        server, probe, name, _ = real_server_with_tool
        # INTENTIONAL: this call omits `context` to prove it is required.
        # mypy strict correctly flags it; the runtime TypeError is the assertion.
        with pytest.raises(TypeError, match="context"):
            await server._tool_manager.call_tool(name, {})  # type: ignore[call-arg]
