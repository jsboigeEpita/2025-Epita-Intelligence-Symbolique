
# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

# -*- coding: utf-8 -*-
"""
Tests unitaires pour le module extract_agent.

Ce module contient les tests unitaires pour les classes et fonctions définies dans le module
agents.core.extract.extract_agent.
"""

import pytest
import pytest_asyncio
import asyncio
import json
import re

from argumentation_analysis.agents.core.extract.extract_agent import ExtractAgent
from argumentation_analysis.agents.core.extract.extract_definitions import ExtractAgentPlugin, ExtractResult
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel import Kernel
from semantic_kernel.functions.function_result import FunctionResult
from argumentation_analysis.core.llm_service import create_llm_service

# Suppression des mocks inutiles, on garde juste ce qui est nécessaire pour des tests unitaires purs.
from unittest.mock import MagicMock, AsyncMock

@pytest_asyncio.fixture
async def authentic_extract_agent():
    """Fixture pour configurer un agent d'extraction avec un vrai kernel LLM."""
    try:
        service_id = "test_llm_service"
        # On passe l'ID de service directement à la création
        llm_service = create_llm_service(service_id=service_id)
        kernel = Kernel()
        # add_service n'a pas de paramètre service_id, l'ID est dans l'objet service
        kernel.add_service(llm_service)
        agent = ExtractAgent(kernel=kernel)
        
        # La méthode setup_agent_components est essentielle et requiert l'ID du service
        agent.setup_agent_components(llm_service_id=service_id)

        return agent
    except Exception as e:
        pytest.fail(f"Échec de la configuration de l'agent d'extraction authentique: {e}")

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

@pytest.mark.asyncio
async def test_extract_from_name_success_authentic(authentic_extract_agent, mock_load_source_text):
    """Teste le flux d'extraction de bout en bout avec un vrai LLM."""
    # La fixture est déjà 'awaited' par pytest-asyncio
    agent = authentic_extract_agent

    source_info = {
        "source_name": "Discours sur l'état de l'Union 2023",
        "source_url": "https://example.com/sotu2023",
        "source_text": "Le chômage a atteint son niveau le plus bas en 50 ans. Nous avons créé plus d'emplois en deux ans que n'importe quelle administration en quatre. C'est un progrès économique réel."
    }
    extract_name = "Déclaration sur la création d'emplois"

    mock_load_source_text.return_value = (source_info["source_text"], source_info["source_url"])

    result = await agent.extract_from_name(source_info, extract_name)

    assert result.status == "valid", f"Le statut devrait être 'valid', mais est '{result.status}' avec le message '{result.message}'"
    assert result.start_marker is not None and isinstance(result.start_marker, str) and len(result.start_marker) > 0
    assert result.end_marker is not None and isinstance(result.end_marker, str) and len(result.end_marker) > 0
    assert result.extracted_text is not None and isinstance(result.extracted_text, str)
    assert "emplois" in result.extracted_text.lower()

    print(f"\n--- Résultat d'extraction authentique ---")
    print(f"  Statut: {result.status}")
    print(f"  Marqueur début: '{result.start_marker}'")
    print(f"  Marqueur fin: '{result.end_marker}'")
    print(f"  Texte extrait: '{result.extracted_text}'")
    print(f"  Explication: {result.explanation}")
    print(f"----------------------------------------")

    mock_load_source_text.assert_called_once_with(source_info)

# --- Les anciens tests sont désactivés pour se concentrer sur l'appel authentique ---

@pytest.mark.asyncio
async def test_extract_from_name_large_text(authentic_extract_agent, mock_load_source_text):
    """
    Teste le flux d'extraction de bout en bout avec un vrai LLM sur un texte volumineux,
    forçant l'agent à utiliser sa logique de découpage en blocs.
    """
    agent = authentic_extract_agent

    # Créer un texte très long avec une phrase cible unique au milieu
    lorem_ipsum = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed non risus. Suspendisse lectus tortor, dignissim sit amet, adipiscing nec, ultricies sed, dolor. "
    long_text = lorem_ipsum * 200  # Assez long pour déclencher le mode "large_text"
    target_sentence = "La déclaration cruciale sur l'économie verte est enfouie ici."
    text_with_target = long_text[:len(long_text)//2] + target_sentence + long_text[len(long_text)//2:]

    source_info = {
        "source_name": "Rapport Annuel Extensif",
        "source_text": text_with_target
    }
    extract_name = "Le point sur l'économie verte"

    mock_load_source_text.return_value = (source_info["source_text"], "http://example.com/long_report")

    result = await agent.extract_from_name(source_info, extract_name)

    assert result.status == "valid", f"Le statut devrait être 'valid', mais est '{result.status}' avec le message '{result.message}'"
    assert target_sentence in result.extracted_text, f"Le texte extrait devrait contenir la phrase cible."
    print(f"\n--- Test sur texte volumineux réussi ---")
    print(f"  Statut reçu: {result.status}")
    print(f"  Texte extrait (extrait): '{result.extracted_text[:100]}...'")
    print(f"------------------------------------")

@pytest_asyncio.fixture
async def agent_with_mocked_invoke():
    """Crée un agent avec un kernel dont la méthode 'invoke' est mockée."""
    # Créer un mock pour le Kernel
    mock_kernel = MagicMock(spec=Kernel)
    
    # Créer un mock pour la réponse de la fonction sémantique
    mock_response = MagicMock(spec=FunctionResult)
    mock_response.__str__.return_value = "Je suis une réponse intentionnellement non-JSON."
    
    # Configurer la méthode invoke du mock_kernel
    mock_kernel.invoke = AsyncMock(return_value=mock_response)
    
    # Créer l'agent avec ce kernel mocké
    agent = ExtractAgent(kernel=mock_kernel)
    # Pas besoin de setup_agent_components car le kernel est un mock.
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
    assert "Bornes invalides ou manquantes proposées par l'agent" in result.message
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

@pytest.mark.asyncio
async def test_update_extract_markers(basic_agent):
    """Teste la mise à jour des marqueurs avec un résultat valide."""
    agent = basic_agent
    extract_definitions = [{"source_name": "Source", "extracts": [{"extract_name": "Extrait 1", "start_marker": "vieux début", "end_marker": "vieille fin"}]}]
    valid_result = ExtractResult(source_name="Source", extract_name="Extrait 1", status="valid", message="OK", start_marker="nouveau début", end_marker="nouvelle fin")
    
    success = await agent.update_extract_markers(extract_definitions, 0, 0, valid_result)
    
    assert success
    assert extract_definitions[0]["extracts"][0]["start_marker"] == "nouveau début"
    assert extract_definitions[0]["extracts"][0]["end_marker"] == "nouvelle fin"

@pytest.mark.asyncio
async def test_update_extract_markers_invalid(basic_agent):
    """Teste que la mise à jour échoue avec un résultat invalide ou des index incorrects."""
    agent = basic_agent
    extract_definitions = [{"source_name": "Source", "extracts": [{"extract_name": "Extrait 1", "start_marker": "original", "end_marker": "original"}]}]
    invalid_result = ExtractResult(source_name="Source", extract_name="Extrait 1", status="error", message="Erreur")
    valid_result = ExtractResult(source_name="Source", extract_name="Extrait 1", status="valid", message="OK", start_marker="nouveau", end_marker="nouveau")

    # Cas 1: Résultat non valide
    success = await agent.update_extract_markers(extract_definitions, 0, 0, invalid_result)
    assert not success
    assert extract_definitions[0]["extracts"][0]["start_marker"] == "original" # Doit rester inchangé

    # Cas 2: Index de source invalide
    success = await agent.update_extract_markers(extract_definitions, 1, 0, valid_result)
    assert not success

    # Cas 3: Index d'extrait invalide
    success = await agent.update_extract_markers(extract_definitions, 0, 1, valid_result)
    assert not success

@pytest.mark.asyncio
async def test_add_new_extract(basic_agent):
    """Teste l'ajout d'un nouvel extrait avec un résultat valide."""
    agent = basic_agent
    extract_definitions = [{"source_name": "Source", "extracts": []}]
    valid_result = ExtractResult(source_name="Source", extract_name="Nouvel Extrait", status="valid", message="OK", start_marker="début", end_marker="fin", template_start="template")

    success, new_index = await agent.add_new_extract(extract_definitions, 0, "Nouvel Extrait", valid_result)

    assert success
    assert new_index == 0
    assert len(extract_definitions[0]["extracts"]) == 1
    assert extract_definitions[0]["extracts"][0]["extract_name"] == "Nouvel Extrait"
    assert extract_definitions[0]["extracts"][0]["start_marker"] == "début"

@pytest.mark.asyncio
async def test_add_new_extract_invalid(basic_agent):
    """Teste que l'ajout échoue avec un résultat invalide ou un index de source incorrect."""
    agent = basic_agent
    extract_definitions = [{"source_name": "Source", "extracts": []}]
    invalid_result = ExtractResult(source_name="Source", extract_name="Test", status="rejected", message="Rejeté")
    valid_result = ExtractResult(source_name="Source", extract_name="Test", status="valid", message="OK", start_marker="début", end_marker="fin")

    # Cas 1: Résultat non valide
    success, idx = await agent.add_new_extract(extract_definitions, 0, "Test", invalid_result)
    assert not success
    assert idx == -1
    assert len(extract_definitions[0]["extracts"]) == 0 # Doit rester vide

    # Cas 2: Index de source invalide
    success, idx = await agent.add_new_extract(extract_definitions, 1, "Test", valid_result)
    assert not success
    assert idx == -1

if __name__ == "__main__":
    pytest.main([__file__])