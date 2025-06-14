import project_core.core_from_scripts.auto_env

# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

import pytest
from unittest.mock import MagicMock
from argumentation_analysis.models.extract_definition import (
    ExtractDefinitions, SourceDefinition, Extract
)
from argumentation_analysis.models.extract_result import ExtractResult
from argumentation_analysis.services.fetch_service import FetchService
from argumentation_analysis.services.extract_service import ExtractService


@pytest.fixture
def sample_extract_dict():
    """Retourne un dictionnaire représentant un extrait simple."""
    return {
        "extract_name": "Test Extract",
        "start_marker": "DEBUT_EXTRAIT",
        "end_marker": "FIN_EXTRAIT",
        "template_start": "T{0}"
    }

@pytest.fixture
def sample_extract(sample_extract_dict):
    """Retourne une instance de Extract basée sur la fixture de dictionnaire."""
    return Extract.from_dict(sample_extract_dict)

@pytest.fixture
def sample_source(sample_extract):
    """Retourne une instance de SourceDefinition contenant un extrait."""
    return SourceDefinition(
        source_name="Test Source",
        source_type="url",
        schema="https",
        host_parts=["example", "com"],
        path="/test",
        extracts=[sample_extract]
    )

@pytest.fixture
def sample_definitions(sample_source):
    """Retourne une instance de ExtractDefinitions contenant une source."""
    return ExtractDefinitions(sources=[sample_source])
@pytest.fixture
def extract_result_dict():
    """Retourne un dictionnaire représentant un résultat d'extraction valide."""
    return {
        "source_name": "Test Source",
        "extract_name": "Test Extract",
        "status": "valid",
        "message": "Extraction réussie",
        "start_marker": "DEBUT_EXTRAIT",
        "end_marker": "FIN_EXTRAIT",
        "template_start": "T{0}",
        "explanation": "Explication de l'extraction",
        "extracted_text": "Texte extrait de test"
    }

@pytest.fixture
def valid_extract_result(extract_result_dict):
    """Retourne une instance de ExtractResult valide."""
    return ExtractResult.from_dict(extract_result_dict)

@pytest.fixture
def error_extract_result(extract_result_dict):
    """Retourne une instance de ExtractResult avec un statut d'erreur."""
    error_dict = extract_result_dict.copy()
    error_dict["status"] = "error"
    error_dict["message"] = "Erreur lors de l'extraction"
    return ExtractResult.from_dict(error_dict)

@pytest.fixture
def rejected_extract_result(extract_result_dict):
    """Retourne une instance de ExtractResult avec un statut rejeté."""
    rejected_dict = extract_result_dict.copy()
    rejected_dict["status"] = "rejected"
    rejected_dict["message"] = "Extraction rejetée"
    return ExtractResult.from_dict(rejected_dict)


@pytest.fixture
def integration_services():
    """
    Fournit des services mockés et des données de test pour les tests d'intégration.
    """
    mock_fetch_service = MagicMock(spec=FetchService)
    mock_extract_service = MagicMock(spec=ExtractService)
    
    sample_text = """
    Ceci est un exemple de texte source.
    Il contient plusieurs paragraphes.
    
    Voici un marqueur de début: DEBUT_EXTRAIT
    Ceci est le contenu de l'extrait.
    Il peut contenir plusieurs lignes.
    Voici un marqueur de fin: FIN_EXTRAIT
    
    Et voici la suite du texte après l'extrait.
    """
    # Mock eliminated - using authentic gpt-4o-mini
    mock_fetch_service.fetch_text(sample_text, "https://example.com/test")
    
    # Mock eliminated - using authentic gpt-4o-mini
    mock_extract_service.extract_text_with_markers(
        "Ceci est le contenu de l'extrait.\nIl peut contenir plusieurs lignes.",
        "✅ Extraction réussie",
        True,
        True
    )
    
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
    integration_sample_definitions = ExtractDefinitions(sources=[source])
    
    return mock_fetch_service, mock_extract_service, integration_sample_definitions