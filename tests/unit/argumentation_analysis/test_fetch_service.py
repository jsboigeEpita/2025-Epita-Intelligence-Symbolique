#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour le service de récupération

Ce module contient les tests unitaires pour le service de récupération (FetchService)
qui est responsable de la récupération de texte à partir d'URLs.
"""

import pytest
import hashlib
import os
import sys
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

# Ajouter le répertoire parent au chemin de recherche des modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests

# Importer les modules à tester
from argumentation_analysis.services.fetch_service import FetchService
from argumentation_analysis.services.cache_service import CacheService


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Fixture pour un répertoire de cache temporaire."""
    cache_dir = tmp_path / "test_cache"
    cache_dir.mkdir()
    yield cache_dir
    # Nettoyage après les tests
    if cache_dir.exists():
        shutil.rmtree(cache_dir)


@pytest.fixture
def temp_download_dir(tmp_path):
    """Fixture pour un répertoire de téléchargement temporaire."""
    download_dir = tmp_path / "test_downloads"
    download_dir.mkdir()
    yield download_dir
    # Nettoyage après les tests
    if download_dir.exists():
        shutil.rmtree(download_dir)


@pytest.fixture
def cache_service(temp_cache_dir):
    """Fixture pour le service de cache."""
    return CacheService(cache_dir=temp_cache_dir)


@pytest.fixture
def fetch_service(cache_service, temp_download_dir):
    """Fixture pour le service de récupération."""
    return FetchService(
        cache_service=cache_service,
        temp_download_dir=temp_download_dir
    )


@pytest.fixture
def sample_url():
    """Fixture pour une URL d'exemple."""
    return "https://example.com/test"


@pytest.fixture
def sample_text():
    """Fixture pour un texte d'exemple."""
    return "Ceci est un exemple de texte pour tester le service de récupération."


@pytest.fixture
def sample_source_info():
    """Fixture pour des informations de source d'exemple."""
    return {
        "source_name": "Test Source",
        "source_type": "direct_download",
        "schema": "https",
        "host_parts": ["example", "com"],
        "path": "/test"
    }


class MockResponse:
    """Classe pour simuler une réponse HTTP."""
    
    def __init__(self, text, content=None, status_code=200, raise_for_status=None):
        self.text = text
        self.content = content if content is not None else text.encode('utf-8')
        self.status_code = status_code
        self.raise_for_status = raise_for_status or (lambda: None)


class TestFetchService:
    """Tests pour le service de récupération."""

    def test_init(self, cache_service, temp_download_dir):
        """Test d'initialisation du service de récupération."""
        service = FetchService(
            cache_service=cache_service,
            temp_download_dir=temp_download_dir
        )
        
        assert service.cache_service == cache_service
        assert service.temp_download_dir == temp_download_dir
        assert service.temp_download_dir.exists()

    def test_reconstruct_url(self, fetch_service):
        """Test de reconstruction d'URL."""
        # Cas valide
        schema = "https"
        host_parts = ["example", "com"]
        path = "/test"
        
        url = fetch_service.reconstruct_url(schema, host_parts, path)
        assert url == "https//example.com/test"
        
        # Cas avec chemin sans slash
        path_no_slash = "test"
        url = fetch_service.reconstruct_url(schema, host_parts, path_no_slash)
        assert url == "https//example.com/test"
        
        # Cas avec parties d'hôte vides
        host_parts_with_empty = ["example", "", "com"]
        url = fetch_service.reconstruct_url(schema, host_parts_with_empty, path)
        assert url == "https//example.com/test"
        
        # Cas invalide
        assert fetch_service.reconstruct_url("", [], "") is None
        assert fetch_service.reconstruct_url(None, None, None) is None

    @patch('requests.get')
    def test_fetch_text_from_cache(self, mock_get, fetch_service, sample_source_info, sample_text):
        """Test de récupération de texte depuis le cache."""
        # Sauvegarder dans le cache
        url = "https//example.com/test"  # URL reconstruite
        fetch_service.cache_service.save_to_cache(url, sample_text)
        
        # Récupérer le texte
        text, message = fetch_service.fetch_text(sample_source_info)
        
        # Vérifier que le texte est récupéré depuis le cache
        assert text == sample_text
        assert message == url
        
        # Vérifier que requests.get n'a pas été appelé
        mock_get.assert_not_called()

    @patch('requests.get')
    def test_fetch_text_force_refresh(self, mock_get, fetch_service, sample_source_info, sample_text):
        """Test de récupération de texte avec force_refresh."""
        # Sauvegarder dans le cache
        url = "https//example.com/test"  # URL reconstruite
        fetch_service.cache_service.save_to_cache(url, sample_text)
        
        # Simuler une réponse HTTP
        mock_get.return_value = MockResponse(sample_text + " (refreshed)")
        
        # Récupérer le texte avec force_refresh
        text, message = fetch_service.fetch_text(sample_source_info, force_refresh=True)
        
        # Vérifier que le texte est récupéré depuis l'URL
        assert text == sample_text + " (refreshed)"
        assert message == url
        
        # Vérifier que requests.get a été appelé
        mock_get.assert_called_once()

    @patch('requests.get')
    def test_fetch_text_invalid_url(self, mock_get, fetch_service):
        """Test de récupération de texte avec une URL invalide."""
        # Source avec URL invalide
        invalid_source_info = {
            "source_type": "direct_download",
            "schema": "",
            "host_parts": [],
            "path": ""
        }
        
        # Récupérer le texte
        text, message = fetch_service.fetch_text(invalid_source_info)
        
        # Vérifier que la récupération a échoué
        assert text is None
        assert "URL invalide" in message
        
        # Vérifier que requests.get n'a pas été appelé
        mock_get.assert_not_called()

    @patch('requests.get')
    def test_fetch_text_jina(self, mock_get, fetch_service, sample_source_info, sample_text):
        """Test de récupération de texte via Jina."""
        # Modifier le type de source
        jina_source_info = sample_source_info.copy()
        jina_source_info["source_type"] = "jina"
        
        # Simuler une réponse HTTP
        mock_get.return_value = MockResponse("Markdown Content:" + sample_text)
        
        # Récupérer le texte
        with patch.object(fetch_service, 'fetch_with_jina', return_value=sample_text) as mock_fetch_jina:
            text, message = fetch_service.fetch_text(jina_source_info)
        
        # Vérifier que le texte est récupéré via Jina
        assert text == sample_text
        mock_fetch_jina.assert_called_once()

    @patch('requests.get')
    def test_fetch_text_tika(self, mock_get, fetch_service, sample_source_info, sample_text):
        """Test de récupération de texte via Tika."""
        # Modifier le type de source
        tika_source_info = sample_source_info.copy()
        tika_source_info["source_type"] = "tika"
        tika_source_info["path"] = "/test.pdf"  # Extension non texte
        
        # Simuler une réponse HTTP
        mock_get.return_value = MockResponse(sample_text)
        
        # Récupérer le texte
        with patch.object(fetch_service, 'fetch_with_tika', return_value=sample_text) as mock_fetch_tika:
            text, message = fetch_service.fetch_text(tika_source_info)
        
        # Vérifier que le texte est récupéré via Tika
        assert text == sample_text
        mock_fetch_tika.assert_called_once()

    @patch('requests.get')
    def test_fetch_text_tika_plaintext(self, mock_get, fetch_service, sample_source_info, sample_text):
        """Test de récupération de texte via Tika pour un fichier texte."""
        # Modifier le type de source
        tika_source_info = sample_source_info.copy()
        tika_source_info["source_type"] = "tika"
        tika_source_info["path"] = "/test.txt"  # Extension texte
        
        # Simuler une réponse HTTP
        mock_get.return_value = MockResponse(sample_text)
        
        # Récupérer le texte
        with patch.object(fetch_service, 'fetch_direct_text', return_value=sample_text) as mock_fetch_direct:
            text, message = fetch_service.fetch_text(tika_source_info)
        
        # Vérifier que le texte est récupéré directement
        assert text == sample_text
        mock_fetch_direct.assert_called_once()

    @patch('requests.get')
    def test_fetch_text_exception(self, mock_get, fetch_service, sample_source_info):
        """Test de récupération de texte avec une exception."""
        # Simuler une exception
        mock_get.side_effect = Exception("Erreur de récupération")
        
        # Récupérer le texte
        text, message = fetch_service.fetch_text(sample_source_info)
        
        # Vérifier que la récupération a échoué
        assert text is None
        assert "Erreur" in message

    @patch('requests.get')
    def test_fetch_direct_text(self, mock_get, fetch_service, sample_url, sample_text):
        """Test de récupération directe de texte."""
        # Simuler une réponse HTTP
        mock_get.return_value = MockResponse(sample_text)
        
        # Récupérer le texte
        text = fetch_service.fetch_direct_text(sample_url)
        
        # Vérifier que le texte est récupéré
        assert text == sample_text
        
        # Vérifier que requests.get a été appelé correctement
        mock_get.assert_called_once_with(
            sample_url,
            headers={'User-Agent': 'ArgumentAnalysisApp/1.0'},
            timeout=60
        )
        
        # Vérifier que le texte est sauvegardé dans le cache
        cached_text = fetch_service.cache_service.load_from_cache(sample_url)
        assert cached_text == sample_text

    @patch('requests.get')
    def test_fetch_direct_text_error(self, mock_get, fetch_service, sample_url):
        """Test de récupération directe de texte avec une erreur."""
        # Simuler une erreur HTTP
        mock_get.side_effect = requests.exceptions.RequestException("Erreur HTTP")
        
        # Récupérer le texte
        text = fetch_service.fetch_direct_text(sample_url)
        
        # Vérifier que la récupération a échoué
        assert text is None

    @patch('requests.get')
    def test_fetch_with_jina(self, mock_get, fetch_service, sample_url, sample_text):
        """Test de récupération de texte via Jina."""
        # Simuler une réponse HTTP
        mock_get.return_value = MockResponse("Markdown Content:" + sample_text)
        
        # Récupérer le texte
        text = fetch_service.fetch_with_jina(sample_url)
        
        # Vérifier que le texte est récupéré
        assert text == sample_text
        
        # Vérifier que requests.get a été appelé correctement
        jina_url = f"{fetch_service.jina_reader_prefix}{sample_url}"
        mock_get.assert_called_once_with(
            jina_url,
            headers={'Accept': 'text/markdown', 'User-Agent': 'ArgumentAnalysisApp/1.0'},
            timeout=90
        )
        
        # Vérifier que le texte est sauvegardé dans le cache
        cached_text = fetch_service.cache_service.load_from_cache(sample_url)
        assert cached_text == sample_text

    @patch('requests.get')
    def test_fetch_with_jina_no_marker(self, mock_get, fetch_service, sample_url, sample_text):
        """Test de récupération de texte via Jina sans marqueur."""
        # Simuler une réponse HTTP sans marqueur
        mock_get.return_value = MockResponse(sample_text)
        
        # Récupérer le texte
        text = fetch_service.fetch_with_jina(sample_url)
        
        # Vérifier que le texte est récupéré
        assert text == sample_text

    @patch('requests.get')
    def test_fetch_with_jina_error(self, mock_get, fetch_service, sample_url):
        """Test de récupération de texte via Jina avec une erreur."""
        # Simuler une erreur HTTP
        mock_get.side_effect = requests.exceptions.RequestException("Erreur HTTP")
        
        # Récupérer le texte
        text = fetch_service.fetch_with_jina(sample_url)
        
        # Vérifier que la récupération a échoué
        assert text is None

    @patch('requests.put')
    @patch('requests.get')
    def test_fetch_with_tika_url(self, mock_get, mock_put, fetch_service, sample_url, sample_text):
        """Test de récupération de texte via Tika avec une URL."""
        # Simuler une réponse HTTP pour le téléchargement
        mock_get.return_value = MockResponse(
            text="binary content",
            content=b"binary content"
        )
        
        # Simuler une réponse HTTP pour Tika
        mock_put.return_value = MockResponse(sample_text)
        
        # Récupérer le texte
        text = fetch_service.fetch_with_tika(url=sample_url)
        
        # Vérifier que le texte est récupéré
        assert text == sample_text
        
        # Vérifier que requests.get a été appelé pour le téléchargement
        mock_get.assert_called_once()
        
        # Vérifier que requests.put a été appelé pour Tika
        mock_put.assert_called_once()
        
        # Vérifier que le texte est sauvegardé dans le cache
        cached_text = fetch_service.cache_service.load_from_cache(sample_url)
        assert cached_text == sample_text

    def test_fetch_with_tika_file_content(self, fetch_service, sample_text):
        """Test de récupération de texte via Tika avec un contenu de fichier."""
        # Contenu du fichier
        file_content = b"binary content"
        file_name = "test.pdf"
        
        # Simuler une réponse HTTP pour Tika
        with patch('requests.put', return_value=MockResponse(sample_text)) as mock_put:
            # Récupérer le texte
            text = fetch_service.fetch_with_tika(
                file_content=file_content,
                file_name=file_name
            )
        
        # Vérifier que le texte est récupéré
        assert text == sample_text
        
        # Vérifier que requests.put a été appelé pour Tika
        mock_put.assert_called_once()
        
        # Vérifier que le texte est sauvegardé dans le cache
        cache_key = f"file://{file_name}"
        cached_text = fetch_service.cache_service.load_from_cache(cache_key)
        assert cached_text == sample_text

    def test_fetch_with_tika_plaintext_file(self, fetch_service, sample_text):
        """Test de récupération de texte via Tika avec un fichier texte."""
        # Contenu du fichier texte
        file_content = sample_text.encode('utf-8')
        file_name = "test.txt"
        
        # Récupérer le texte
        text = fetch_service.fetch_with_tika(
            file_content=file_content,
            file_name=file_name
        )
        
        # Vérifier que le texte est récupéré directement
        assert text == sample_text

    @patch('requests.put')
    @patch('requests.get')
    def test_fetch_with_tika_timeout(self, mock_get, mock_put, fetch_service, sample_url):
        """Test de récupération de texte via Tika avec un timeout."""
        # Simuler une réponse HTTP pour le téléchargement
        mock_get.return_value = MockResponse(
            text="binary content",
            content=b"binary content"
        )
        
        # Simuler un timeout pour Tika
        mock_put.side_effect = requests.exceptions.Timeout("Timeout")
        
        # Récupérer le texte
        text = fetch_service.fetch_with_tika(url=sample_url)
        
        # Vérifier que la récupération a échoué
        assert text is None

    @patch('requests.put')
    @patch('requests.get')
    def test_fetch_with_tika_error(self, mock_get, mock_put, fetch_service, sample_url):
        """Test de récupération de texte via Tika avec une erreur."""
        # Simuler une réponse HTTP pour le téléchargement
        mock_get.return_value = MockResponse(
            text="binary content",
            content=b"binary content"
        )
        
        # Simuler une erreur pour Tika
        mock_put.side_effect = requests.exceptions.RequestException("Erreur HTTP")
        
        # Récupérer le texte
        text = fetch_service.fetch_with_tika(url=sample_url)
        
        # Vérifier que la récupération a échoué
        assert text is None

    def test_fetch_with_tika_no_content(self, fetch_service):
        """Test de récupération de texte via Tika sans contenu."""
        # Récupérer le texte sans URL ni contenu
        text = fetch_service.fetch_with_tika()
        
        # Vérifier que la récupération a échoué
        assert text is None

    @patch('requests.get')
    def test_fetch_with_tika_download_error(self, mock_get, fetch_service, sample_url):
        """Test de récupération de texte via Tika avec une erreur de téléchargement."""
        # Simuler une erreur de téléchargement
        mock_get.side_effect = requests.exceptions.RequestException("Erreur de téléchargement")
        
        # Récupérer le texte
        text = fetch_service.fetch_with_tika(url=sample_url)
        
        # Vérifier que la récupération a échoué
        assert text is None

    @patch('pathlib.Path.read_bytes')
    @patch('requests.put')
    @patch('requests.get')
    def test_fetch_with_tika_raw_cache(self, mock_get, mock_put, mock_read_bytes, fetch_service, sample_url, sample_text, temp_download_dir):
        """Test de récupération de texte via Tika avec cache brut."""
        # Créer un fichier de cache brut
        url_hash = hashlib.sha256(sample_url.encode()).hexdigest()
        raw_cache_path = temp_download_dir / f"{url_hash}.download"
        raw_cache_path.write_bytes(b"cached binary content")
        
        # Simuler la lecture du fichier de cache
        mock_read_bytes.return_value = b"cached binary content"
        
        # Simuler une réponse HTTP pour Tika
        mock_put.return_value = MockResponse(sample_text)
        
        # Récupérer le texte
        text = fetch_service.fetch_with_tika(url=sample_url)
        
        # Vérifier que le texte est récupéré
        assert text == sample_text
        
        # Vérifier que requests.get n'a pas été appelé (utilisation du cache)
        mock_get.assert_not_called()
        
        # Vérifier que requests.put a été appelé pour Tika
        mock_put.assert_called_once()

    @patch('pathlib.Path.read_bytes')
    @patch('requests.put')
    @patch('requests.get')
    def test_fetch_with_tika_raw_cache_error(self, mock_get, mock_put, mock_read_bytes, fetch_service, sample_url, sample_text, temp_download_dir):
        """Test de récupération de texte via Tika avec erreur de lecture du cache brut."""
        # Créer un fichier de cache brut
        url_hash = hashlib.sha256(sample_url.encode()).hexdigest()
        raw_cache_path = temp_download_dir / f"{url_hash}.download"
        raw_cache_path.write_bytes(b"cached binary content")
        
        # Simuler une erreur de lecture du fichier de cache
        mock_read_bytes.side_effect = Exception("Erreur de lecture")
        
        # Simuler une réponse HTTP pour le téléchargement
        mock_get.return_value = MockResponse(
            text="binary content",
            content=b"binary content"
        )
        
        # Simuler une réponse HTTP pour Tika
        mock_put.return_value = MockResponse(sample_text)
        
        # Récupérer le texte
        text = fetch_service.fetch_with_tika(url=sample_url)
        
        # Vérifier que le texte est récupéré
        assert text == sample_text
        
        # Vérifier que requests.get a été appelé pour le téléchargement
        mock_get.assert_called_once()