#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Fixtures pour les tests unitaires et d'intégration.

Ce module contient des fixtures pytest qui peuvent être utilisées
dans les différents tests unitaires et d'intégration du projet.
"""

import pytest
import sys
import os
import json
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
import tempfile
import shutil

# Importer les fixtures des données de test
try:
    from .test_data.conftest import *
except ImportError:
    # Si l'import direct échoue, essayer un chemin relatif
    test_data_dir = Path(__file__).parent / "test_data"
    if test_data_dir.exists() and (test_data_dir / "conftest.py").exists():
        sys.path.insert(0, str(test_data_dir))
        from conftest import *

# Ajouter le répertoire parent au chemin de recherche des modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Créer un module factice pour les tests
import sys
import types

# Créer un module factice pour argumentation_analysis
argumentation_analysis = types.ModuleType('argumentation_analysis')
sys.modules['argumentation_analysis'] = argumentation_analysis

# Créer des sous-modules
argumentation_analysis.models = types.ModuleType('argumentation_analysis.models')
argumentation_analysis.services = types.ModuleType('argumentation_analysis.services')
sys.modules['argumentation_analysis.models'] = argumentation_analysis.models
sys.modules['argumentation_analysis.services'] = argumentation_analysis.services

# Importer les modules réels dans les modules factices
import models.extract_definition
import models.extract_result
# from argumentation_analysis.services import cache_service
from argumentation_analysis.services import crypto_service
from argumentation_analysis.services import definition_service
from argumentation_analysis.services import extract_service
from argumentation_analysis.services import fetch_service

# Assigner les modules réels aux modules factices
argumentation_analysis.models.extract_definition = models.extract_definition
argumentation_analysis.models.extract_result = models.extract_result
# argumentation_analysis.services.cache_service = services.cache_service
argumentation_analysis.services.crypto_service = crypto_service
argumentation_analysis.services.definition_service = definition_service
argumentation_analysis.services.extract_service = extract_service
argumentation_analysis.services.fetch_service = fetch_service

# Utiliser des imports directs
from models.extract_definition import Extract, SourceDefinition, ExtractDefinitions
from models.extract_result import ExtractResult
from argumentation_analysis.services.cache_service import CacheService
from argumentation_analysis.services.crypto_service import CryptoService
from argumentation_analysis.services.definition_service import DefinitionService
from argumentation_analysis.services.extract_service import ExtractService
from argumentation_analysis.services.fetch_service import FetchService

# ===== Fixtures pour les tests unitaires =====


@pytest.fixture
def sample_extract():
    """Fixture pour un extrait de test."""
    return Extract(
        extract_name="Test Extract",
        start_marker="DEBUT_EXTRAIT",
        end_marker="FIN_EXTRAIT",
        template_start="T{0}"
    )


@pytest.fixture
def sample_source(sample_extract):
    """Fixture pour une source de test avec un extrait."""
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
    """Fixture pour des définitions d'extraits de test avec une source."""
    return ExtractDefinitions(sources=[sample_source])


@pytest.fixture
def sample_extract_dict():
    """Fixture pour un dictionnaire représentant un extrait."""
    return {
        "extract_name": "Test Extract",
        "start_marker": "DEBUT_EXTRAIT",
        "end_marker": "FIN_EXTRAIT",
        "template_start": "T{0}"
    }


@pytest.fixture
def sample_source_dict(sample_extract_dict):
    """Fixture pour un dictionnaire représentant une source."""
    return {
        "source_name": "Test Source",
        "source_type": "url",
        "schema": "https",
        "host_parts": ["example", "com"],
        "path": "/test",
        "extracts": [sample_extract_dict]
    }


@pytest.fixture
def valid_extract_result():
    """Fixture pour un résultat d'extraction valide."""
    return ExtractResult(
        source_name="Test Source",
        extract_name="Test Extract",
        status="valid",
        message="Extraction réussie",
        start_marker="DEBUT_EXTRAIT",
        end_marker="FIN_EXTRAIT",
        template_start="T{0}",
        explanation="Explication de l'extraction",
        extracted_text="Texte extrait de test"
    )


@pytest.fixture
def error_extract_result():
    """Fixture pour un résultat d'extraction avec erreur."""
    return ExtractResult(
        source_name="Test Source",
        extract_name="Test Extract",
        status="error",
        message="Erreur lors de l'extraction",
        start_marker="DEBUT_EXTRAIT",
        end_marker="FIN_EXTRAIT"
    )


@pytest.fixture
def rejected_extract_result():
    """Fixture pour un résultat d'extraction rejeté."""
    return ExtractResult(
        source_name="Test Source",
        extract_name="Test Extract",
        status="rejected",
        message="Extraction rejetée",
        start_marker="DEBUT_EXTRAIT",
        end_marker="FIN_EXTRAIT"
    )


@pytest.fixture
def extract_result_dict():
    """Fixture pour un dictionnaire représentant un résultat d'extraction."""
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

# ===== Fixtures pour les tests d'intégration =====

@pytest.fixture
def temp_dir():
    """Fixture pour un répertoire temporaire."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)

@pytest.fixture
def mock_cache_service():
    """Fixture pour un service de cache mocké."""
    mock_service = MagicMock(spec=CacheService)
    
    # Simuler le comportement de load_from_cache
    cache_data = {}
    
    def mock_load_from_cache(url):
        return cache_data.get(url)
    
    def mock_save_to_cache(url, text):
        cache_data[url] = text
        return True
    
    mock_service.load_from_cache.side_effect = mock_load_from_cache
    mock_service.save_to_cache.side_effect = mock_save_to_cache
    
    return mock_service

@pytest.fixture
def mock_crypto_service():
    """Fixture pour un service de chiffrement mocké."""
    mock_service = MagicMock(spec=CryptoService)
    
    # Simuler le comportement de is_encryption_enabled
    mock_service.is_encryption_enabled.return_value = False
    
    # Simuler le comportement de encrypt_and_compress_json et decrypt_and_decompress_json
    def mock_encrypt_and_compress_json(data):
        return json.dumps(data).encode('utf-8')
    
    def mock_decrypt_and_decompress_json(encrypted_data):
        return json.loads(encrypted_data.decode('utf-8'))
    
    mock_service.encrypt_and_compress_json.side_effect = mock_encrypt_and_compress_json
    mock_service.decrypt_and_decompress_json.side_effect = mock_decrypt_and_decompress_json
    
    return mock_service

@pytest.fixture
def mock_definition_service(mock_crypto_service, sample_definitions):
    """Fixture pour un service de définition mocké."""
    mock_service = MagicMock(spec=DefinitionService)
    
    # Simuler le comportement de load_definitions
    mock_service.load_definitions.return_value = (sample_definitions, None)
    
    # Simuler le comportement de save_definitions
    mock_service.save_definitions.return_value = (True, None)
    
    return mock_service

@pytest.fixture
def mock_fetch_service(mock_cache_service):
    """Fixture pour un service de récupération mocké."""
    mock_service = MagicMock(spec=FetchService)
    
    # Simuler le comportement de fetch_text
    sample_texts = {
        "https://example.com/test": """
        Ceci est un exemple de texte source.
        Il contient plusieurs paragraphes.
        
        Voici un marqueur de début: DEBUT_EXTRAIT
        Ceci est le contenu de l'extrait.
        Il peut contenir plusieurs lignes.
        Voici un marqueur de fin: FIN_EXTRAIT
        
        Et voici la suite du texte après l'extrait.
        """
    }
    
    def mock_fetch_text(source_info, force_refresh=False):
        url = mock_service.reconstruct_url(
            source_info.get("schema"),
            source_info.get("host_parts", []),
            source_info.get("path")
        )
        
        # Vérifier d'abord dans le cache
        if not force_refresh:
            cached_text = mock_cache_service.load_from_cache(url)
            if cached_text is not None:
                return cached_text, url
        
        # Sinon, récupérer depuis les exemples
        text = sample_texts.get(url)
        if text:
            mock_cache_service.save_to_cache(url, text)
            return text, url
        
        return None, f"URL non trouvée: {url}"
    
    def mock_reconstruct_url(schema, host_parts, path):
        if not schema or not host_parts or not path:
            return None
        
        host = ".".join(part for part in host_parts if part)
        path = path if path.startswith('/') or not path else '/' + path
        
        return f"{schema}//{host}{path}"
    
    mock_service.fetch_text.side_effect = mock_fetch_text
    mock_service.reconstruct_url.side_effect = mock_reconstruct_url
    mock_service.cache_service = mock_cache_service
    
    return mock_service

@pytest.fixture
def mock_extract_service():
    """Fixture pour un service d'extraction mocké."""
    mock_service = MagicMock(spec=ExtractService)
    
    # Simuler le comportement de extract_text_with_markers
    def mock_extract_text_with_markers(text, start_marker, end_marker, template_start=None):
        if not text:
            return None, "Texte source vide", False, False
        
        start_found = start_marker in text
        end_found = end_marker in text
        
        if start_found and end_found:
            start_index = text.index(start_marker) + len(start_marker)
            end_index = text.index(end_marker, start_index)
            extracted_text = text[start_index:end_index].strip()
            status = "✅ Extraction réussie"
            return extracted_text, status, start_found, end_found
        else:
            status = ""
            if not start_found:
                status += "⚠️ Marqueur début non trouvé. "
            if not end_found:
                status += "⚠️ Marqueur fin non trouvé. "
            return None, status.strip(), start_found, end_found
    
    mock_service.extract_text_with_markers.side_effect = mock_extract_text_with_markers
    
    return mock_service

@pytest.fixture
def mock_llm_service():
    """Fixture pour un service LLM mocké."""
    mock_service = MagicMock()
    mock_service.service_id = "mock_llm_service"
    
    # Simuler le comportement d'un appel au LLM
    async def mock_complete_chat_async(messages, **kwargs):
        # Retourner une réponse simple basée sur le dernier message
        last_message = messages[-1].content if messages else "Pas de message"
        return f"Réponse du LLM à: {last_message}"
    
    mock_service.complete_chat_async = AsyncMock(side_effect=mock_complete_chat_async)
    
    return mock_service

@pytest.fixture
def mock_analysis_service():
    """Fixture pour un service d'analyse mocké."""
    mock_service = MagicMock()
    mock_service.service_id = "mock_analysis_service"

    # Simuler une méthode d'analyse typique
    async def mock_analyze_async(data, **kwargs):
        # Retourner une réponse d'analyse simple
        return {"analysis_id": "mock_id_123", "status": "completed", "result": "Mock analysis result"}

    mock_service.analyze_async = AsyncMock(side_effect=mock_analyze_async)
    # Ajouter d'autres méthodes mockées si nécessaire pour ce service
    # Par exemple: mock_service.get_analysis_status_async = AsyncMock(return_value={"status": "pending"})
    return mock_service
@pytest.fixture
def sample_analysis_request():
    """Fixture pour une requête d'analyse simple."""
    return {
        "text_to_analyze": "Ceci est un texte d'exemple pour l'analyse.",
        "options": {
            "depth": "full",
            "model_preference": "accuracy"
        }
    }
@pytest.fixture
def module_name():
    """Fixture pour un nom de module de test."""
    return "test_module_sample"

@pytest.fixture
def module_path():
    """Fixture pour un chemin de module de test."""
    return "path/to/test_module_sample.py"
def integration_sample_source():
    """Fixture pour une source de test pour l'intégration."""
    return SourceDefinition(
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

@pytest.fixture
def integration_sample_definitions(integration_sample_source):
    """Fixture pour des définitions d'extraits pour l'intégration."""
    return ExtractDefinitions(sources=[integration_sample_source])

@pytest.fixture
def integration_extract_results():
    """Fixture pour des résultats d'extraction pour l'intégration."""
    return [
        ExtractResult(
            source_name="Source d'intégration",
            extract_name="Extrait d'intégration 1",
            status="valid",
            message="Extraction réussie",
            start_marker="DEBUT_EXTRAIT",
            end_marker="FIN_EXTRAIT",
            extracted_text="Ceci est le contenu de l'extrait.\nIl peut contenir plusieurs lignes."
        ),
        ExtractResult(
            source_name="Source d'intégration",
            extract_name="Extrait d'intégration 2",
            status="error",
            message="Marqueur début non trouvé",
            start_marker="MARQUEUR_INEXISTANT",
            end_marker="FIN_EXTRAIT"
        )
    ]
