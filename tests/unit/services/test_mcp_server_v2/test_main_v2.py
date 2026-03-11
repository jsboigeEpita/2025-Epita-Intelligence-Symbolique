"""Tests for MCP Server v2 main module integration."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from argumentation_analysis.services.mcp_server.main import MCPService, AppServices
from argumentation_analysis.services.mcp_server.tools._serialization import (
    safe_serialize,
)


class TestBackwardCompatibility:
    """Ensure v1 imports and behavior are preserved."""

    def test_mcp_service_importable(self):
        """MCPService is importable from main module."""
        assert MCPService is not None

    def test_app_services_importable(self):
        """AppServices is importable from main module."""
        assert AppServices is not None

    def test_init_importable(self):
        """MCPService is importable from __init__."""
        from argumentation_analysis.services.mcp_server import MCPService as MC2
        from argumentation_analysis.services.mcp_server import AppServices as AS2

        assert MC2 is MCPService
        assert AS2 is AppServices

    def test_v1_tools_registered(self):
        """Original 10 tools are registered even when v2 fails."""
        with patch(
            "argumentation_analysis.services.mcp_server.main.FastMCP"
        ) as mock_fast_mcp, patch(
            "argumentation_analysis.services.mcp_server.main.initialize_project_environment"
        ), patch(
            "argumentation_analysis.services.mcp_server.main.AppServices"
        ):
            mock_mcp_instance = mock_fast_mcp.return_value
            mock_mcp_instance.tool.return_value = lambda f: f

            service = MCPService()
            # Original 10 tools use mcp.tool()
            assert mock_mcp_instance.tool.call_count >= 10


class TestListAvailableTools:
    """Tests for the updated list_available_tools."""

    @pytest.mark.asyncio
    async def test_list_includes_v2_tools(self):
        """list_available_tools includes both v1 and v2 tools."""
        with patch(
            "argumentation_analysis.services.mcp_server.main.FastMCP"
        ) as mock_fast_mcp, patch(
            "argumentation_analysis.services.mcp_server.main.initialize_project_environment"
        ), patch(
            "argumentation_analysis.services.mcp_server.main.AppServices"
        ):
            mock_mcp_instance = mock_fast_mcp.return_value
            mock_mcp_instance.tool.return_value = lambda f: f

            service = MCPService()
            result = await service.list_available_tools()

        assert result["version"] == "2.0.0"
        assert result["total_tools"] == 23

        # V1 tools present
        assert "health_check" in result["tools"]
        assert "analyze_text" in result["tools"]

        # V2 tools present
        assert "list_workflows" in result["tools"]
        assert "invoke_capability" in result["tools"]
        assert "evaluate_quality" in result["tools"]
        assert "start_conversation" in result["tools"]


class TestSafeSerialization:
    """Tests for the safe_serialize helper."""

    def test_primitives(self):
        assert safe_serialize(42) == 42
        assert safe_serialize("hello") == "hello"
        assert safe_serialize(3.14) == 3.14
        assert safe_serialize(True) is True
        assert safe_serialize(None) is None

    def test_dict(self):
        result = safe_serialize({"a": 1, "b": [2, 3]})
        assert result == {"a": 1, "b": [2, 3]}

    def test_list(self):
        result = safe_serialize([1, "two", {"three": 3}])
        assert result == [1, "two", {"three": 3}]

    def test_set(self):
        result = safe_serialize({3, 1, 2})
        assert result == [1, 2, 3]  # sorted

    def test_enum(self):
        from enum import Enum

        class Color(Enum):
            RED = "red"
            BLUE = "blue"

        assert safe_serialize(Color.RED) == "red"

    def test_dataclass(self):
        from dataclasses import dataclass

        @dataclass
        class Point:
            x: int
            y: int

        result = safe_serialize(Point(1, 2))
        assert result == {"x": 1, "y": 2}

    def test_unknown_type(self):
        result = safe_serialize(object())
        assert isinstance(result, str)

    def test_nested(self):
        from dataclasses import dataclass
        from enum import Enum

        class Status(Enum):
            OK = "ok"

        @dataclass
        class Inner:
            status: Status
            tags: set

        result = safe_serialize(Inner(Status.OK, {"a", "b"}))
        assert result["status"] == "ok"
        assert result["tags"] == ["a", "b"]
