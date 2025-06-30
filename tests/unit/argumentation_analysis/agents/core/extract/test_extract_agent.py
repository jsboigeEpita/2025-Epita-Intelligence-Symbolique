
# -*- coding: utf-8 -*-
"""
Tests unitaires pour le module extract_agent.

Ce module contient les tests unitaires pour les classes et fonctions définies dans le module
agents.core.extract.extract_agent. Ces tests n'utilisent PAS de connexion réseau
et mockent les appels au LLM.
"""

import pytest
import pytest_asyncio
from unittest.mock import MagicMock, AsyncMock

from argumentation_analysis.agents.core.extract.extract_agent import ExtractAgent
from argumentation_analysis.agents.core.extract.extract_definitions import ExtractAgentPlugin
from semantic_kernel import Kernel
from semantic_kernel.functions.function_result import FunctionResult

@pytest.fixture
def mock_load_source_text(mocker):
    """
    Fixture pour mocker la fonction `load_source_text` utilisée par l'agent.
    Cela isole le test de la lecture réelle des fichiers/URL.
    """
    mock_func = mocker.patch(
        'argumentation_analysis.agents.core.extract.extract_agent.load_source_text',
        autospec=True
    )
    return mock_func

@pytest_asyncio.fixture
async def agent_with_mocked_invoke():
    """Crée un agent avec un kernel dont la méthode 'invoke' est mockée."""
    mock_kernel = MagicMock(spec=Kernel)
    mock_response = MagicMock(spec=FunctionResult)
    mock_response.__str__.return_value = "Je suis une réponse intentionnellement non-JSON."
    mock_kernel.invoke = AsyncMock(return_value=mock_response)
    agent = ExtractAgent(kernel=mock_kernel)
    return agent

@pytest.mark.asyncio
async def test_extract_from_name_json_error(agent_with_mocked_invoke, mock_load_source_text):
    """
    Teste le cas où la réponse du LLM (simulée ici) n'est pas un JSON valide.
    """
    agent = agent_with_mocked_invoke

    source_info = {
        "source_name": "Texte de test",
        "source_text": "Du texte sans importance car l'appel est mocké."
    }
    extract_name = "Un extrait quelconque"
    mock_load_source_text.return_value = (source_info["source_text"], "http://example.com")

    result = await agent.extract_from_name(source_info, extract_name)

    # On vérifie que la logique de parsing d'erreur est bien déclenchée
    assert result.status == "error"
    assert "Réponse non-JSON de l'agent LLM." in result.message
    print(f"\n--- Test de réponse non-JSON réussi ---")
    print(f"  Statut reçu: {result.status}")
    print(f"  Message: {result.message}")
    print(f"------------------------------------")

@pytest.fixture
def basic_agent():
    """
    Crée une instance simple de ExtractAgent pour les tests non-LLM.
    Le plugin natif est initialisé manuellement pour éviter l'appel à setup_agent_components
    qui requiert un service LLM dans le kernel.
    """
    agent = ExtractAgent(kernel=Kernel())
    agent._native_extract_plugin = ExtractAgentPlugin()
    return agent


if __name__ == "__main__":
    pytest.main([__file__])