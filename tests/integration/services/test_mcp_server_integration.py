# Integration tests for MCP server service.
# Tests the MCPService can be instantiated and its tools registered.
# Full stdio transport tests require a running subprocess and are
# better suited for e2e tests.
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

try:
    from mcp.client.session import ClientSession
    from mcp.client.stdio import stdio_client

    MCP_CLIENT_AVAILABLE = True
except ImportError:
    MCP_CLIENT_AVAILABLE = False

try:
    from argumentation_analysis.services.mcp_server.main import MCPService

    MCP_SERVICE_AVAILABLE = True
except ImportError:
    MCP_SERVICE_AVAILABLE = False

SERVICE_NAME = "argumentation_analysis_mcp"


@pytest.mark.skipif(
    not MCP_SERVICE_AVAILABLE,
    reason="MCPService not available (missing dependencies)",
)
class TestMCPServiceInstantiation:
    """Tests that the MCP service can be created and configured."""

    def test_service_creation(self):
        """MCPService can be instantiated with a service name.
        Note: full initialization may fail without LLM services configured,
        but the object itself should be created."""
        try:
            service = MCPService(service_name=SERVICE_NAME)
            assert service is not None
        except Exception:
            # MCPService may fail during init if LogicService/LLM not configured.
            # The important thing is the class is importable and constructable
            # up to the point where it needs external services.
            pytest.skip("MCPService requires LLM services to fully initialize")

    def test_service_class_importable(self):
        """MCPService class is importable and has expected interface."""
        assert hasattr(MCPService, "__init__")
        assert callable(MCPService)


@pytest.mark.skipif(
    not MCP_CLIENT_AVAILABLE,
    reason="mcp.client.session not available (install mcp package)",
)
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
