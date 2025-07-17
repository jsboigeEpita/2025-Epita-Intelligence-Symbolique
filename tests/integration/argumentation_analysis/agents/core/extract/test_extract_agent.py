# -*- coding: utf-8 -*-
"""
Tests d'intégration pour le module extract_agent.

Ces tests valident le fonctionnement de l'agent d'extraction avec une
connexion réelle à un service LLM. Ils nécessitent une configuration
d'environnement valide avec une clé API.
"""

import pytest
from semantic_kernel import Kernel
import asyncio

from argumentation_analysis.agents.core.extract.extract_agent import ExtractAgent
from argumentation_analysis.core.llm_service import create_llm_service

@pytest.fixture
def authentic_extract_agent():
    """Fixture pour configurer un agent d'extraction avec un vrai kernel LLM."""
    try:
        service_id = "test_llm_service"
        llm_service = create_llm_service(service_id=service_id, model_id="gpt-4o-mini")
        kernel = Kernel()
        kernel.add_service(llm_service)
        agent = ExtractAgent(kernel=kernel)
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

def test_extract_from_name_success_authentic(authentic_extract_agent, mock_load_source_text):
    """Teste le flux d'extraction de bout en bout avec un vrai LLM."""
    async def run_test():
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

        mock_load_source_text.assert_called_once_with(source_info)
    asyncio.run(run_test())

def test_extract_from_name_large_text(authentic_extract_agent, mock_load_source_text):
    """
    Teste le flux d'extraction de bout en bout avec un vrai LLM sur un texte volumineux,
    forçant l'agent à utiliser sa logique de découpage en blocs.
    """
    async def run_test():
        agent = authentic_extract_agent

        lorem_ipsum = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed non risus. Suspendisse lectus tortor, dignissim sit amet, adipiscing nec, ultricies sed, dolor. "
        long_text = lorem_ipsum * 200
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
        assert target_sentence in result.extracted_text, "Le texte extrait devrait contenir la phrase cible."
    asyncio.run(run_test())