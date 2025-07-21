# Fichier de test unitaire pour le service MCP.
# TODO: Implémenter les tests unitaires décrits dans le plan de test.

import pytest
import sys
from unittest.mock import MagicMock, patch, AsyncMock

from services.mcp_server.main import MCPService, AppServices
from argumentation_analysis.services.web_api.models.response_models import AnalysisResponse, ValidationResponse, FallacyResponse, FrameworkResponse

@pytest.fixture
def mcp_service_mock():
    """Fixture améliorée pour mocker complètement l'initialisation et les services."""
    with patch('services.mcp_server.main.FastMCP') as mock_fast_mcp, \
         patch('argumentation_analysis.core.bootstrap.initialize_project_environment') as mock_init_env, \
         patch('services.mcp_server.main.AppServices') as mock_app_services:

        # Mocker l'instance de FastMCP et sa méthode 'tool'
        mock_mcp_instance = mock_fast_mcp.return_value
        mock_mcp_instance.tool.return_value = lambda f: f
        
        # Mocker l'instance des services (AppServices) et ses sous-services
        mock_services_instance = mock_app_services.return_value
        # Importer ValidationResult pour le mock ci-dessous
        from argumentation_analysis.services.web_api.models.response_models import ValidationResult

        async def mock_analyze_text(*args, **kwargs):
            return AnalysisResponse(
                success=True, text_analyzed="Sample text"
            )

        async def mock_validate_argument(*args, **kwargs):
            from argumentation_analysis.services.web_api.models.response_models import ValidationResult
            return ValidationResponse(
                success=True,
                premises=["p1"],
                conclusion="c1",
                argument_type="deductive",
                result=ValidationResult(is_valid=True, validity_score=1.0, soundness_score=1.0)
            )

        async def mock_detect_fallacies(*args, **kwargs):
            return FallacyResponse(
                success=True, text_analyzed="Sample text for fallacies", fallacies=[]
            )

        async def mock_build_framework(*args, **kwargs):
            return FrameworkResponse(
                success=True, semantics_used="complete"
            )

        mock_services_instance.analysis_service.analyze_text.side_effect = mock_analyze_text
        mock_services_instance.validation_service.validate_argument.side_effect = mock_validate_argument
        mock_services_instance.fallacy_service.detect_fallacies.side_effect = mock_detect_fallacies
        mock_services_instance.framework_service.build_framework.side_effect = mock_build_framework

        service = MCPService()
        
        # Attacher les mocks pour les assertions dans les tests
        service.mcp_instance_mock = mock_mcp_instance
        service.mock_init_env = mock_init_env
        service.mock_app_services_class = mock_app_services
        service.mock_services_instance = mock_services_instance

        # Simuler l'initialisation qui se fait normalement de manière asynchrone
        import asyncio
        asyncio.run(service._ensure_initialized())

        yield service

@pytest.mark.skip(reason="Provoque un crash systeme en l'absence de JVM")
def test_mcp_service_initialization(mcp_service_mock: MCPService):
    """Teste l'initialisation correcte du service MCP et le bon nombre d'outils."""
    assert mcp_service_mock is not None
    mcp_service_mock.mock_init_env.assert_called_once()
    mcp_service_mock.mock_app_services_class.assert_called_once()
    assert mcp_service_mock.mcp_instance_mock.tool.call_count == 10

@pytest.mark.skip(reason="Provoque un crash systeme en l'absence de JVM")
def test_analyze_text_method(mcp_service_mock: MCPService):
    """Teste la réponse de la méthode 'analyze_text'."""
    import asyncio
    response = asyncio.run(mcp_service_mock.analyze_text(text="Test text."))
    assert response['success'] is True
    assert response['text_analyzed'] == "Sample text"

@pytest.mark.skip(reason="Provoque un crash systeme en l'absence de JVM")
def test_validate_argument_method(mcp_service_mock: MCPService):
    """Teste la réponse de la méthode 'validate_argument'."""
    import asyncio
    response = asyncio.run(mcp_service_mock.validate_argument(premises=["p1"], conclusion="c1"))
    assert response['success'] is True
    assert response['result']['is_valid'] is True

@pytest.mark.skip(reason="Provoque un crash systeme en l'absence de JVM")
def test_detect_fallacies_method(mcp_service_mock: MCPService):
    """Teste la réponse de la méthode 'detect_fallacies'."""
    import asyncio
    response = asyncio.run(mcp_service_mock.detect_fallacies(text="Test fallacy."))
    assert response['success'] is True
    assert response['text_analyzed'] == "Sample text for fallacies"
    assert not response['fallacies']

@pytest.mark.skip(reason="Provoque un crash systeme en l'absence de JVM")
def test_build_framework_method(mcp_service_mock: MCPService):
    """Teste la réponse de la méthode 'build_framework' avec des données valides."""
    import asyncio
    # Le modèle `FrameworkRequest` requiert au moins un argument.
    valid_argument = [{"id": "A", "content": "Argument A"}]
    response = asyncio.run(mcp_service_mock.build_framework(arguments=valid_argument))
    assert response['success'] is True
    assert response['semantics_used'] == "complete"
