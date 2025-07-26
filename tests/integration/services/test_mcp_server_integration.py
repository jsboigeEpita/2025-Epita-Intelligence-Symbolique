# Fichier de test d'intégration pour le service MCP.
import pytest
import multiprocessing
import time
import asyncio

from mcp import ClientSession as Client

from services.mcp_server.main import MCPService

SERVICE_NAME = "argumentation_analysis_mcp"

def run_mcp_service():
    """Fonction cible pour le processus du service MCP."""
    service = MCPService(service_name=SERVICE_NAME)
    service.run(transport='stdio')


@pytest.fixture(scope="module")
async def mcp_client():
    """Fixture pour créer un client MCP connecté au service."""
    from mcp.client.stdio import stdio_client
    from mcp import StdioServerParameters

    import os
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"

    server_params = StdioServerParameters(
        command="python",
        args=["-m", "services.mcp_server.main"],
        env=env,
    )

    async with stdio_client(server_params) as (read, write):
        async with Client(read, write) as session:
            await session.initialize()
            yield session

async def test_service_lifecycle(mcp_client: Client):
    """Teste que le service peut être démarré et que le client peut s'y connecter."""
    tools = await mcp_client.list_tools()
    assert len(tools.tools) > 0

async def test_analyze_interaction(mcp_client: Client):
    """Teste l'appel de l'outil 'analyze'."""
    result = await mcp_client.call_tool("analyze", arguments={"text": "Ceci est un test."})
    assert result.isError is False
    assert "implémentation" in result.content[0].text

async def test_validate_argument_interaction(mcp_client: Client):
    """Teste l'appel de l'outil 'validate_argument'."""
    result = await mcp_client.call_tool("validate_argument", arguments={"premises": ["p1"], "conclusion": "c1"})
    assert result.isError is False
    assert "implémentation" in result.content[0].text

async def test_detect_fallacies_interaction(mcp_client: Client):
    """Teste l'appel de l'outil 'detect_fallacies'."""
    result = await mcp_client.call_tool("detect_fallacies", arguments={"text": "Ceci est un sophisme."})
    assert result.isError is False
    assert "implémentation" in result.content[0].text

async def test_build_framework_interaction(mcp_client: Client):
    """Teste l'appel de l'outil 'build_framework'."""
    result = await mcp_client.call_tool("build_framework", arguments={"arguments": []})
    assert result.isError is False
    assert "implémentation" in result.content[0].text