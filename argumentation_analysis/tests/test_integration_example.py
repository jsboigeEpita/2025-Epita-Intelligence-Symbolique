#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Exemple de test d'intégration pour le projet d'analyse d'argumentation.

Ce module contient un exemple de test d'intégration qui démontre l'utilisation
des mocks et fixtures pour tester l'interaction entre les différents composants.
"""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ajouter le répertoire parent au chemin de recherche des modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Importer les modules à tester
from argumentation_analysis.utils.extract_repair.marker_verification_logic import verify_all_extracts as verify_extracts, generate_verification_report as generate_report
from argumentation_analysis.models.extract_definition import ExtractDefinitions, Extract, SourceDefinition
from argumentation_analysis.services.extract_service import ExtractService
from argumentation_analysis.services.fetch_service import FetchService
from argumentation_analysis.tests.async_test_case import AsyncTestCase


class TestIntegrationVerifyExtracts:
    """Tests d'intégration pour le script verify_extracts."""

    def test_verify_extracts_integration(self, mock_fetch_service, mock_extract_service, integration_sample_definitions, temp_dir):
        """Test d'intégration pour la fonction verify_extracts."""
        # Exécuter la fonction verify_extracts
        results = verify_extracts(
            integration_sample_definitions,
            mock_fetch_service,
            mock_extract_service
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
        report_path = temp_dir / "test_report.html"
        generate_report(results, str(report_path))
        
        # Vérifier que le rapport a été généré
        assert report_path.exists()
        
        # Vérifier le contenu du rapport
        report_content = report_path.read_text(encoding='utf-8')
        assert "Source d'intégration" in report_content
        assert "Extrait d'intégration 1" in report_content
        assert "Extrait d'intégration 2" in report_content
        assert "valid" in report_content
        assert "invalid" in report_content


class TestIntegrationExtractService:
    """Tests d'intégration pour le service d'extraction."""

    # Utiliser autouse=True pour configurer les mocks automatiquement
    @pytest.fixture(autouse=True)
    def setup_mocks(self, request):
        """Configure les mocks nécessaires pour le test."""
        # Créer des mocks pour les services
        self.mock_fetch_service = MagicMock(spec=FetchService)
        
        # Configurer le mock pour fetch_text
        sample_text = """
        Ceci est un exemple de texte source.
        Il contient plusieurs paragraphes.
        
        Voici un marqueur de début: DEBUT_EXTRAIT
        Ceci est le contenu de l'extrait.
        Il peut contenir plusieurs lignes.
        Voici un marqueur de fin: FIN_EXTRAIT
        
        Et voici la suite du texte après l'extrait.
        """
        self.mock_fetch_service.fetch_text.return_value = (sample_text, "https://example.com/test")
        
        # Créer un échantillon de définitions d'extraits
        source = SourceDefinition(
            source_name="Source d'intégration",
            source_type="url",
            schema="https",
            host_parts=["example", "com"],
            path="/test",
            extracts=[
                Extract(
                    extract_name="Extrait d'intégration 1",
                    start_marker="DEBUT_EXTRAIT",
                    end_marker="FIN_EXTRAIT"
                )
            ]
        )
        self.integration_sample_definitions = ExtractDefinitions(sources=[source])

    def test_extract_service_with_fetch_service(self):
        """Test d'intégration entre ExtractService et FetchService."""
        # Créer un vrai service d'extraction (pas un mock)
        extract_service = ExtractService()
        
        # Récupérer la source et l'extrait de test
        source = self.integration_sample_definitions.sources[0]
        extract = source.extracts[0]
        
        # Récupérer le texte source via le service de récupération mocké
        source_text, url = self.mock_fetch_service.fetch_text(source.to_dict())
        
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


class TestIntegrationRepairExtractMarkers(AsyncTestCase):
    """Tests d'intégration pour le script repair_extract_markers."""

    # Utiliser autouse=True pour configurer les mocks automatiquement
    @pytest.fixture(autouse=True)
    def setup_mocks(self, request):
        """Configure les mocks nécessaires pour le test."""
        # Créer des mocks pour les services
        self.mock_fetch_service = MagicMock(spec=FetchService)
        self.mock_extract_service = MagicMock(spec=ExtractService)
        self.mock_llm_service = MagicMock()
        self.mock_llm_service.service_id = "mock_llm_service"
        
        # Configurer le mock pour fetch_text
        sample_text = """
        Ceci est un exemple de texte source.
        Il contient plusieurs paragraphes.
        
        Voici un marqueur de début: DEBUT_EXTRAIT
        Ceci est le contenu de l'extrait.
        Il peut contenir plusieurs lignes.
        Voici un marqueur de fin: FIN_EXTRAIT
        
        Et voici la suite du texte après l'extrait.
        """
        self.mock_fetch_service.fetch_text.return_value = (sample_text, "https://example.com/test")
        
        # Créer un échantillon de définitions d'extraits
        source = SourceDefinition(
            source_name="Source d'intégration",
            source_type="url",
            schema="https",
            host_parts=["example", "com"],
            path="/test",
            extracts=[
                Extract(
                    extract_name="Extrait d'intégration 1",
                    start_marker="DEBUT_EXTRAIT",
                    end_marker="FIN_EXTRAIT"
                ),
                Extract(
                    extract_name="Extrait d'intégration 2",
                    start_marker="MARQUEUR_INEXISTANT",
                    end_marker="FIN_EXTRAIT"
                )
            ]
        )
        self.integration_sample_definitions = ExtractDefinitions(sources=[source])

    @patch('scripts.repair_extract_markers.setup_agents')
    async def test_repair_extract_markers_integration(self, mock_setup_agents):
        """Test d'intégration pour la fonction repair_extract_markers."""
        from scripts.repair_extract_markers import repair_extract_markers
        
        # Configurer le mock pour setup_agents
        kernel_mock = self.mock_llm_service
        repair_agent_mock = self.mock_llm_service
        validation_agent_mock = self.mock_llm_service
        mock_setup_agents.return_value = (kernel_mock, repair_agent_mock, validation_agent_mock)
        
        # Exécuter la fonction repair_extract_markers
        updated_definitions, results = await repair_extract_markers(
            self.integration_sample_definitions,
            self.mock_llm_service,
            self.mock_fetch_service,
            self.mock_extract_service
        )
        
        # Vérifier les résultats
        assert len(results) == 2
        
        # Vérifier que les définitions ont été mises à jour
        assert updated_definitions is not None
        assert len(updated_definitions.sources) == 1
        assert len(updated_definitions.sources[0].extracts) == 2


if __name__ == '__main__':
    pytest.main(['-xvs', __file__])