# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour le service de cache

Ce module contient les tests unitaires pour le service de cache (CacheService)
qui est responsable de la gestion du cache de textes.
"""

import pytest
import os
import sys
import shutil
from pathlib import Path
import logging


logger = logging.getLogger(__name__)


# Ajouter le répertoire parent au chemin de recherche des modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importer les modules à tester
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
def cache_service(temp_cache_dir):
    """Fixture pour le service de cache."""
    return CacheService(cache_dir=temp_cache_dir)


@pytest.fixture
def sample_url():
    """Fixture pour une URL d'exemple."""
    return "https://example.com/test"


@pytest.fixture
def sample_text():
    """Fixture pour un texte d'exemple."""
    return "Ceci est un exemple de texte pour tester le cache."


class TestCacheService:
    async def _create_authentic_gpt4o_mini_instance(self):
        """Crée une instance authentique de gpt-4o-mini au lieu d'un mock."""
        config = UnifiedConfig()
        return config.get_kernel_with_gpt4o_mini()

    async def _make_authentic_llm_call(self, prompt: str) -> str:
        """Fait un appel authentique à gpt-4o-mini."""
        try:
            kernel = await self._create_authentic_gpt4o_mini_instance()
            result = await kernel.invoke("chat", input=prompt)
            return str(result)
        except Exception as e:
            logger.warning(f"Appel LLM authentique échoué: {e}")
            return "Authentic LLM call failed"

    """Tests pour le service de cache."""

    def test_init(self, temp_cache_dir):
        """Test d'initialisation du service de cache."""
        service = CacheService(cache_dir=temp_cache_dir)
        assert service.cache_dir == temp_cache_dir
        assert service.cache_dir.exists()

    def test_get_cache_filepath(self, cache_service, sample_url):
        """Test de génération du chemin de fichier cache."""
        filepath = cache_service.get_cache_filepath(sample_url)

        # Vérifier que le chemin est correct
        assert filepath.parent == cache_service.cache_dir
        assert filepath.suffix == ".txt"

        # Vérifier que le nom du fichier est un hash SHA-256
        assert len(filepath.stem) == 64  # Longueur d'un hash SHA-256 en hexadécimal

    def test_save_to_cache(self, cache_service, sample_url, sample_text):
        """Test de sauvegarde dans le cache."""
        # Sauvegarder dans le cache
        result = cache_service.save_to_cache(sample_url, sample_text)

        # Vérifier que la sauvegarde a réussi
        assert result is True

        # Vérifier que le fichier existe
        filepath = cache_service.get_cache_filepath(sample_url)
        assert filepath.exists()

        # Vérifier le contenu du fichier
        content = filepath.read_text(encoding="utf-8")
        assert content == sample_text

    def test_save_to_cache_empty_text(self, cache_service, sample_url):
        """Test de sauvegarde avec un texte vide."""
        result = cache_service.save_to_cache(sample_url, "")

        # La sauvegarde doit échouer avec un texte vide
        assert result is False

        # Vérifier que le fichier n'existe pas
        filepath = cache_service.get_cache_filepath(sample_url)
        assert not filepath.exists()

    def test_load_from_cache(self, cache_service, sample_url, sample_text):
        """Test de chargement depuis le cache."""
        # Sauvegarder d'abord dans le cache
        cache_service.save_to_cache(sample_url, sample_text)

        # Charger depuis le cache
        loaded_text = cache_service.load_from_cache(sample_url)

        # Vérifier que le texte chargé est correct
        assert loaded_text == sample_text

    def test_load_from_cache_nonexistent(self, cache_service, sample_url):
        """Test de chargement d'une URL non existante dans le cache."""
        loaded_text = cache_service.load_from_cache(sample_url)

        # Le résultat doit être None
        assert loaded_text is None

    def test_load_from_cache_error(
        self, cache_service, sample_url, sample_text, mocker
    ):
        """Test de chargement avec une erreur de lecture."""
        # Sauvegarder d'abord dans le cache
        cache_service.save_to_cache(sample_url, sample_text)
        filepath = cache_service.get_cache_filepath(sample_url)
        assert filepath.exists()

        # Configurer le mock pour lever une exception lors de la lecture du fichier
        mocker.patch.object(
            Path, "read_text", side_effect=IOError("Simulated file read error")
        )

        # Espionner le logger pour vérifier qu'un avertissement est bien émis
        spy_logger = mocker.spy(cache_service.logger, "warning")

        # Tenter de charger depuis le cache
        loaded_text = cache_service.load_from_cache(sample_url)

        # Vérifier que le résultat est None et qu'un avertissement a été loggué
        assert loaded_text is None
        spy_logger.assert_called_once()
        assert "Erreur lecture cache" in spy_logger.call_args[0][0]
        assert "Simulated file read error" in spy_logger.call_args[0][0]

    def test_clear_cache_specific_url(self, cache_service, sample_url, sample_text):
        """Test d'effacement du cache pour une URL spécifique."""
        # Sauvegarder d'abord dans le cache
        cache_service.save_to_cache(sample_url, sample_text)

        # Vérifier que le fichier existe
        filepath = cache_service.get_cache_filepath(sample_url)
        assert filepath.exists()

        # Effacer le cache pour cette URL
        deleted, errors = cache_service.clear_cache(sample_url)

        # Vérifier les résultats
        assert deleted == 1
        assert errors == 0

        # Vérifier que le fichier n'existe plus
        assert not filepath.exists()

    def test_clear_cache_nonexistent_url(self, cache_service, sample_url):
        """Test d'effacement du cache pour une URL non existante."""
        # Effacer le cache pour une URL non existante
        deleted, errors = cache_service.clear_cache(sample_url)

        # Vérifier les résultats
        assert deleted == 0
        assert errors == 0

    def test_clear_cache_all(self, cache_service):
        """Test d'effacement de tout le cache."""
        # Sauvegarder plusieurs fichiers dans le cache
        urls = [
            "https://example.com/1",
            "https://example.com/2",
            "https://example.com/3",
        ]
        for url in urls:
            cache_service.save_to_cache(url, f"Contenu pour {url}")

        # Vérifier que les fichiers existent
        for url in urls:
            filepath = cache_service.get_cache_filepath(url)
            assert filepath.exists()

        # Effacer tout le cache
        deleted, errors = cache_service.clear_cache()

        # Vérifier les résultats
        assert deleted == len(urls)
        assert errors == 0

        # Vérifier que les fichiers n'existent plus
        for url in urls:
            filepath = cache_service.get_cache_filepath(url)
            assert not filepath.exists()

    def test_clear_cache_error(self, cache_service, sample_url, sample_text, mocker):
        """Test d'effacement du cache avec une erreur."""
        # Sauvegarder d'abord dans le cache
        cache_service.save_to_cache(sample_url, sample_text)
        filepath = cache_service.get_cache_filepath(sample_url)
        assert filepath.exists()

        # Configurer le mock pour lever une exception lors de la suppression du fichier
        mocker.patch.object(
            Path, "unlink", side_effect=IOError("Simulated file delete error")
        )

        # Espionner le logger pour vérifier qu'une erreur est bien émise
        spy_logger = mocker.spy(cache_service.logger, "error")

        # Tenter d'effacer le cache pour cette URL
        deleted, errors = cache_service.clear_cache(sample_url)

        # Vérifier que l'opération a échoué comme attendu
        assert deleted == 0
        assert errors == 1
        spy_logger.assert_called_once()
        assert "Erreur lors de l'effacement du cache" in spy_logger.call_args[0][0]
        assert "Simulated file delete error" in spy_logger.call_args[0][0]

    def test_get_cache_size(self, cache_service):
        """Test de récupération de la taille du cache."""
        # Sauvegarder plusieurs fichiers dans le cache
        urls = [
            "https://example.com/1",
            "https://example.com/2",
            "https://example.com/3",
        ]
        for url in urls:
            cache_service.save_to_cache(url, f"Contenu pour {url}")

        # Récupérer la taille du cache
        file_count, total_size = cache_service.get_cache_size()

        # Vérifier les résultats
        assert file_count == len(urls)
        assert total_size > 0

    def test_get_cache_info(self, cache_service):
        """Test de récupération des informations sur le cache."""
        # Sauvegarder plusieurs fichiers dans le cache
        urls = [
            "https://example.com/1",
            "https://example.com/2",
            "https://example.com/3",
        ]
        for url in urls:
            cache_service.save_to_cache(url, f"Contenu pour {url}")

        # Récupérer les informations sur le cache
        info = cache_service.get_cache_info()

        # Vérifier que les informations contiennent le nombre de fichiers
        assert f"Cache: {len(urls)} fichiers" in info

        # Vérifier que les informations contiennent la taille
        assert "B" in info  # Doit contenir une unité de taille (B, KB, MB, GB)

    def test_format_size(self, cache_service):
        """Test de formatage de la taille."""
        # Tester différentes tailles
        sizes = {
            100: "100.00 B",
            1500: "1.46 KB",
            1500000: "1.43 MB",
            1500000000: "1.40 GB",
        }

        for size_bytes, expected in sizes.items():
            formatted = cache_service._format_size(size_bytes)
            assert formatted == expected
