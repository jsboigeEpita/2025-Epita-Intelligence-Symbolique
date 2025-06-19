# Fichier de test unitaire pour le service MCP.
# TODO: Implémenter les tests unitaires décrits dans le plan de test.

import pytest
import sys
from unittest.mock import MagicMock, patch

# Mock du module mcp avant son importation
sys.modules['mcp.server.fastmcp'] = MagicMock()

from services.mcp_server.main import MCPService

@pytest.fixture
def mcp_service_mock():
    """Fixture pour mocker les dépendances et initialiser le service."""
    with patch('services.mcp_server.main.FastMCP') as mock_fast_mcp:
        mock_instance = mock_fast_mcp.return_value
        mock_instance.tool.return_value = lambda f: f
        
        service = MCPService()
        service.mcp_mock = mock_fast_mcp
        service.mcp_instance_mock = mock_instance
        yield service

def test_mcp_service_initialization(mcp_service_mock: MCPService):
    """Teste l'initialisation correcte du service MCP."""
    assert mcp_service_mock is not None
    # Vérifie que le constructeur de FastMCP a été appelé
    mcp_service_mock.mcp_mock.assert_called_once()
    # Vérifie que la méthode pour enregistrer les outils a été appelée
    assert mcp_service_mock.mcp_instance_mock.tool.call_count == 4


@pytest.mark.asyncio
async def test_analyze_method(mcp_service_mock: MCPService):
    """Teste la réponse de la méthode 'analyze'."""
    response = await mcp_service_mock.analyze(text="Test text.")
    assert response["message"] == "Analyse en attente d'implémentation."
    assert response["status"] == "success"


@pytest.mark.asyncio
async def test_validate_argument_method(mcp_service_mock: MCPService):
    """Teste la réponse de la méthode 'validate_argument'."""
    response = await mcp_service_mock.validate_argument(premises=["p1"], conclusion="c1")
    assert response["message"] == "Validation en attente d'implémentation."
    assert response["status"] == "success"


@pytest.mark.asyncio
async def test_detect_fallacies_method(mcp_service_mock: MCPService):
    """Teste la réponse de la méthode 'detect_fallacies'."""
    response = await mcp_service_mock.detect_fallacies(text="Test fallacy.")
    assert response["message"] == "Détection de sophismes en attente d'implémentation."
    assert response["status"] == "success"


@pytest.mark.asyncio
async def test_build_framework_method(mcp_service_mock: MCPService):
    """Teste la réponse de la méthode 'build_framework'."""
    response = await mcp_service_mock.build_framework(arguments=[])
    assert response["message"] == "Construction du framework en attente d'implémentation."
    assert response["status"] == "success"