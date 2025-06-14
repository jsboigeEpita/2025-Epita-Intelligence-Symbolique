
# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Exemple de test d'intégration pour le projet d'analyse d'argumentation.
"""

import pytest
from unittest.mock import MagicMock


# Importer les modules à tester
from argumentation_analysis.utils.dev_tools.verification_utils import verify_all_extracts, generate_verification_report
from argumentation_analysis.services.extract_service import ExtractService


class AuthHelper:
    async def _create_authentic_gpt4o_mini_instance(self):
        """Crée une instance authentique de gpt-4o-mini au lieu d'un mock."""
        config = UnifiedConfig()
        return config.get_kernel_with_gpt4o_mini()


def test_verify_extracts_integration(mocker, integration_services, tmp_path):
    """Test d'intégration pour la fonction verify_extracts."""
    mock_fetch_service, mock_extract_service, integration_sample_definitions = integration_services

    # Configurer le mock pour requests.get pour simuler une réponse réussie
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = """
    Ceci est un exemple de texte source.
    Il contient plusieurs paragraphes.
    
    Voici un marqueur de début: DEBUT_EXTRAIT
    Ceci est le contenu de l'extrait.
    Il peut contenir plusieurs lignes.
    Voici un marqueur de fin: FIN_EXTRAIT
    
    Et voici la suite du texte après l'extrait.
    """.encode('utf-8')
    def raise_for_status():
        pass
    mock_response.raise_for_status = raise_for_status
    
    # Utiliser mocker pour patcher requests.get
    mock_get = mocker.patch('requests.get')
    mock_get.return_value = mock_response

    # Configurer le mock pour simuler un échec d'extraction pour le deuxième extrait
    def extract_side_effect(text, start_marker, end_marker, **kwargs):
        if start_marker == "DEBUT_EXTRAIT":
            return "Ceci est le contenu de l'extrait.", "valid", True, True
        else:
            return None, "invalid", False, True

    mock_extract_service.extract_text_with_markers.side_effect = extract_side_effect
    # Exécuter la fonction verify_extracts
    # La fonction attend maintenant une liste de dictionnaires, et non l'objet plus les services.
    results = verify_all_extracts(
        integration_sample_definitions.to_dict_list()
    )
    
    # Vérifier les résultats
    assert len(results) == 2
    
    # Vérifier le premier résultat (extrait valide)
    assert results[0]["source_name"] == "Source d'intégration"
    assert results[0]["extract_name"] == "Extrait d'intégration 1"
    assert results[0]["status"] == "valid"
    
    # Vérifier le deuxième résultat (extrait invalide)
    assert results[1]["source_name"] == "Source d'intégration"
    assert results[1]["extract_name"] == "Extrait d'intégration 2"
    assert results[1]["status"] == "invalid"
    
    # Générer un rapport
    report_path = tmp_path / "test_report.html"
    generate_verification_report(results, str(report_path))
    
    # Vérifier que le rapport a été généré
    assert report_path.exists()
    
    # Vérifier le contenu du rapport
    report_content = report_path.read_text(encoding='utf-8')
    assert "Source d'intégration" in report_content
    assert "Extrait d'intégration 1" in report_content
    assert "Extrait d'intégration 2" in report_content
    assert "valid" in report_content
    assert "invalid" in report_content


def test_extract_service_with_fetch_service(integration_services):
    """Test d'intégration entre ExtractService et FetchService."""
    mock_fetch_service, _, integration_sample_definitions = integration_services
    
    # Créer un vrai service d'extraction (pas un mock)
    extract_service = ExtractService()
    
    # Récupérer la source et l'extrait de test
    source = integration_sample_definitions.sources[0]
    extract = source.extracts[0]
    
    # Récupérer le texte source via le service de récupération mocké
    source_text, url = mock_fetch_service.fetch_text(source.to_dict())
    
    # Vérifier que le texte source a été récupéré
    assert source_text is not None
    assert url == "https://example.com/test"
    
    # Extraire le texte avec les marqueurs
    extracted_text, status, start_found, end_found = extract_service.extract_text_with_markers(
        source_text, extract.start_marker, extract.end_marker
    )
    
    # Vérifier que l'extraction a réussi
    assert start_found is True
    assert end_found is True
    assert "Extraction réussie" in status
    assert "Ceci est le contenu de l'extrait" in extracted_text


@pytest.mark.skip(reason="Le module 'scripts.repair_extract_markers' n'est pas trouvé, à corriger plus tard.")

async def test_repair_extract_markers_integration(OrchestrationServiceManagers, integration_services):
    """Test d'intégration pour la fonction repair_extract_markers."""
    from scripts.repair_extract_markers import repair_extract_markers
    
    helper = AuthHelper()
    mock_fetch_service, mock_extract_service, integration_sample_definitions = integration_services
    mock_llm_service = await helper._create_authentic_gpt4o_mini_instance()
    mock_llm_service.service_id = "mock_llm_service"

    # Configurer le mock pour setup_agents
    kernel_mock = mock_llm_service
    repair_agent_mock = mock_llm_service
    validation_agent_mock = mock_llm_service
    OrchestrationServiceManagers.return_value = (kernel_mock, repair_agent_mock, validation_agent_mock)
    
    # Exécuter la fonction repair_extract_markers
    updated_definitions, results = await repair_extract_markers(
        integration_sample_definitions,
        mock_llm_service,
        mock_fetch_service,
        mock_extract_service
    )
    
    # Vérifier les résultats
    assert len(results) == 2
    
    # Vérifier que les définitions ont été mises à jour
    assert updated_definitions is not None
    assert len(updated_definitions.sources) == 1
    assert len(updated_definitions.sources[0].extracts) == 2


if __name__ == '__main__':
    pytest.main(['-xvs', __file__])