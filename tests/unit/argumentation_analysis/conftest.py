# conftest.py pour les tests unitaires de argumentation_analysis

import pytest
from unittest.mock import patch
from argumentation_analysis.models.extract_result import ExtractResult

@pytest.fixture(autouse=True)
def force_mock_llm():
    """
    Fixture 'autouse' qui force l'activation du mock LLM pour tous les tests
    dans ce répertoire et ses sous-répertoires.

    Ceci assure que les tests unitaires n'effectuent jamais d'appels réels
    au LLM, conformément aux bonnes pratiques d'isolation.
    """
    with patch('argumentation_analysis.config.settings.settings.use_mock_llm', True):
        yield

@pytest.fixture
def extract_result_dict():
    """Dictionnaire de données pour un résultat d'extraction."""
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
    """Fixture pour un résultat d'extraction valide."""
    return ExtractResult.from_dict(extract_result_dict)

@pytest.fixture
def error_extract_result():
    """Fixture pour un résultat d'extraction en erreur."""
    return ExtractResult(
        source_name="Error Source",
        extract_name="Error Extract",
        status="error",
        message="Erreur lors de l'extraction",
    )

@pytest.fixture
def rejected_extract_result():
    """Fixture pour un résultat d'extraction rejeté."""
    return ExtractResult(
        source_name="Rejected Source",
        extract_name="Rejected Extract",
        status="rejected",
        message="Extraction rejetée",
    )

@pytest.fixture
def sample_definitions():
    """Fixture pour des définitions d'extraits simples."""
    from argumentation_analysis.models.extract_definition import Extract, SourceDefinition, ExtractDefinitions
    
    extract = Extract(
        extract_name="Test Extract",
        start_marker="DEBUT_EXTRAIT",
        end_marker="FIN_EXTRAIT",
        template_start="T{0}"
    )
    
    source = SourceDefinition(
        source_name="Test Source",
        source_type="url",
        schema="https",
        host_parts=["example", "com"],
        path="/test",
        extracts=[extract]
    )
    
    return ExtractDefinitions(sources=[source])

@pytest.fixture
def mock_parse_args():
    """Fixture pour mocker la fonction `parse_args` d'argparse."""
    with patch('argparse.ArgumentParser.parse_args') as mock:
        yield mock