"""Configuration for the MCP server."""

from dataclasses import dataclass


@dataclass
class MCPServerConfig:
    """Configuration for the argumentation analysis MCP server."""

    service_name: str = "argumentation_analysis_mcp"
    host: str = "0.0.0.0"
    port: int = 8000
    transport: str = "streamable-http"
    session_ttl_seconds: int = 1800  # 30 minutes
    max_sessions: int = 100
