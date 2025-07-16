# Fichier de test d'intégration pour le service MCP.
import pytest
import multiprocessing
import time
import asyncio

try:
    from mcp.client import Client
except ImportError:
    Client = None  # Définir Client à None pour éviter les erreurs de syntaxe plus bas
    pytest.skip("mcp.client.Client non trouvé, skip des tests d'intégration MCP", allow_module_level=True)

from services.mcp_server.main import MCPService

SERVICE_NAME = "argumentation_analysis_mcp"

def run_mcp_service():
    """Fonction cible pour le processus du service MCP."""
    service = MCPService(service_name=SERVICE_NAME)
    service.run(transport='stdio')

@pytest.fixture(scope="module")
def mcp_server_process():
    """Fixture pour démarrer et arrêter le service MCP dans un processus séparé."""
    process = multiprocessing.Process(target=run_mcp_service)
    process.start()
    time.sleep(1) # Laisser le temps au serveur de démarrer
    yield
    process.terminate()
    process.join(timeout=1)

@pytest.fixture(scope="module")
async def mcp_client():
    """Fixture pour créer un client MCP connecté au service."""
    client = Client(SERVICE_NAME)
    await client.start(transport='stdio')
    yield client
    await client.stop()

def test_service_lifecycle(mcp_server_process):
    """Teste que le service peut être démarré et arrêté."""
    # Le simple fait d'utiliser la fixture mcp_server_process
    # exécute le test de cycle de vie (démarrage/arrêt).
    # Si la fixture se termine sans erreur, le test est réussi.
    pass

async def test_analyze_interaction(mcp_server_process, mcp_client: Client):
    """Teste l'appel de l'outil 'analyze'."""
    result = await mcp_client.analyze(text="Ceci est un test.")
    assert result['status'] == 'success'
    assert "implémentation" in result['message']

async def test_validate_argument_interaction(mcp_server_process, mcp_client: Client):
    """Teste l'appel de l'outil 'validate_argument'."""
    result = await mcp_client.validate_argument(premises=["p1"], conclusion="c1")
    assert result['status'] == 'success'
    assert "implémentation" in result['message']

async def test_detect_fallacies_interaction(mcp_server_process, mcp_client: Client):
    """Teste l'appel de l'outil 'detect_fallacies'."""
    result = await mcp_client.detect_fallacies(text="Ceci est un sophisme.")
    assert result['status'] == 'success'
    assert "implémentation" in result['message']

async def test_build_framework_interaction(mcp_server_process, mcp_client: Client):
    """Teste l'appel de l'outil 'build_framework'."""
    result = await mcp_client.build_framework(arguments=[])
    assert result['status'] == 'success'
    assert "implémentation" in result['message']