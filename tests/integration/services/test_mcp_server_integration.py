# Integration tests for the MCP server service (#2757).
#
# A real MCPService is built on a real MCPServer. Only the external boundary
# is doubled: the project bootstrap (JVM) and AppServices (LLM keys). The one
# legitimate skip is the third-party ``mcp`` package being absent; a failure
# inside our own constructor is a failure, never a skip.
# Full stdio transport tests require a running subprocess and are better
# suited for e2e tests.
from unittest.mock import MagicMock

import pytest

pytest.importorskip(
    "mcp", reason="mcp>=2.0 is not installed (declared in environment.yml)"
)

from mcp.client.session import ClientSession  # noqa: E402
from mcp.client.stdio import stdio_client  # noqa: E402
from mcp.server import MCPServer  # noqa: E402

from argumentation_analysis.services.mcp_server import main as mcp_main  # noqa: E402

SERVICE_NAME = "argumentation_analysis_mcp"


@pytest.fixture
def controlled_boundary(monkeypatch):
    """Double what needs keys or a JVM; keep the server and its tools real."""
    app_services = MagicMock(name="AppServices")
    monkeypatch.setattr(
        mcp_main, "initialize_project_environment", lambda **kwargs: None
    )
    monkeypatch.setattr(mcp_main, "AppServices", app_services)
    return app_services


class TestMCPServiceInstantiation:
    """A real MCPService builds, and serves the tools it advertises."""

    def test_service_builds_on_a_real_server(self, controlled_boundary):
        service = mcp_main.MCPService(service_name=SERVICE_NAME)

        assert isinstance(service.mcp, MCPServer)
        assert service.services is controlled_boundary.return_value
        assert service._initialized is True

    async def test_served_tools_are_the_advertised_tools(self, controlled_boundary):
        """The v2 registration swallows its errors; the served set tells."""
        service = mcp_main.MCPService(service_name=SERVICE_NAME)

        served = {tool.name for tool in await service.mcp.list_tools()}
        advertised = await service.list_available_tools()

        assert served == set(advertised["tools"])
        assert advertised["total_tools"] == len(served)

    def test_missing_environment_is_a_declared_refusal(self, monkeypatch):
        """Without keys or a JVM the constructor refuses with its own error."""

        def _no_environment(**kwargs):
            raise OSError("no LLM key configured")

        monkeypatch.setattr(mcp_main, "initialize_project_environment", _no_environment)
        with pytest.raises(RuntimeError, match="MCP service initialization failed"):
            mcp_main.MCPService(service_name=SERVICE_NAME)


class TestMCPClientImports:
    """Tests that the MCP client SDK is properly available."""

    def test_client_session_import(self):
        """ClientSession can be imported from mcp.client.session."""
        assert ClientSession is not None

    def test_stdio_client_import(self):
        """stdio_client can be imported from mcp.client.stdio."""
        assert stdio_client is not None

    def test_client_session_is_class(self):
        """ClientSession is a callable class."""
        assert callable(ClientSession)
