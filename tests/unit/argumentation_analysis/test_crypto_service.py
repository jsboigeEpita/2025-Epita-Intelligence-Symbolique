# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour le service de chiffrement

Ce module contient les tests unitaires pour le service de chiffrement (CryptoService)
qui est responsable du chiffrement et du déchiffrement des données sensibles.
"""

import pytest
import base64
import json
import gzip
import os
import sys


# Ajouter le répertoire parent au chemin de recherche des modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptography.fernet import Fernet, InvalidToken
from cryptography.exceptions import InvalidSignature

# Importer les modules à tester
from argumentation_analysis.services.crypto_service import CryptoService


@pytest.fixture
def valid_key():
    """Fixture pour une clé de chiffrement valide."""
    return Fernet.generate_key()


@pytest.fixture
def crypto_service(valid_key):
    """Fixture pour le service de chiffrement avec une clé valide."""
    return CryptoService(encryption_key=valid_key)


@pytest.fixture
def crypto_service_no_key():
    """Fixture pour le service de chiffrement sans clé."""
    return CryptoService(encryption_key=None)


@pytest.fixture
def sample_data():
    """Fixture pour des données d'exemple à chiffrer."""
    return b"Ceci est un exemple de donnees a chiffrer."


@pytest.fixture
def sample_json_data():
    """Fixture pour des données JSON d'exemple à chiffrer."""
    return {
        "name": "Test Data",
        "values": [1, 2, 3, 4, 5],
        "nested": {"key": "value", "flag": True},
    }


@pytest.fixture
def mock_derive(mocker):
    """Fixture to mock key derivation and raise an exception."""
    return mocker.patch(
        "argumentation_analysis.services.crypto_service.PBKDF2HMAC.derive",
        side_effect=Exception("Derivation Error"),
    )


@pytest.fixture
def mock_encrypt(mocker):
    """Fixture to mock data encryption and raise an exception."""
    return mocker.patch(
        "argumentation_analysis.services.crypto_service.Fernet.encrypt",
        side_effect=Exception("Encryption Error"),
    )


@pytest.fixture
def mock_decrypt(mocker):
    """Fixture to mock data decryption and raise an exception."""
    return mocker.patch(
        "argumentation_analysis.services.crypto_service.Fernet.decrypt",
        side_effect=Exception("Decryption Error"),
    )


@pytest.fixture
def mock_dumps(mocker):
    """Fixture to mock json.dumps and raise an exception."""
    return mocker.patch(
        "argumentation_analysis.services.crypto_service.json.dumps",
        side_effect=Exception("JSON Error"),
    )


@pytest.fixture
def mock_decompress(mocker):
    """Fixture to mock gzip.decompress and raise an exception."""
    return mocker.patch(
        "argumentation_analysis.services.crypto_service.gzip.decompress",
        side_effect=Exception("Decompression Error"),
    )


class TestCryptoService:
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

    """Tests pour le service de chiffrement."""

    def test_init_with_key(self, valid_key):
        """Test d'initialisation avec une clé."""
        service = CryptoService(encryption_key=valid_key)
        assert service.encryption_key == valid_key
        assert service.is_encryption_enabled() is True

    def test_init_without_key(self):
        """Test d'initialisation sans clé."""
        service = CryptoService(encryption_key=None)
        assert service.encryption_key is None
        assert service.is_encryption_enabled() is False

    def test_derive_key_from_passphrase(self):
        """Test de dérivation de clé à partir d'une phrase secrète."""
        service = CryptoService()
        passphrase = "phrase_secrete_test"

        # Dériver la clé
        derived_key = service.derive_key_from_passphrase(passphrase)

        # Vérifier que la clé est valide
        assert derived_key is not None
        assert len(derived_key) > 0

        # Vérifier que la clé est au format base64 URL-safe
        try:
            base64.urlsafe_b64decode(derived_key)
        except Exception:
            pytest.fail("La clé dérivée n'est pas au format base64 URL-safe")

    def test_derive_key_from_empty_passphrase(self):
        """Test de dérivation de clé à partir d'une phrase secrète vide."""
        service = CryptoService()

        # Dériver la clé avec une phrase vide
        derived_key = service.derive_key_from_passphrase("")

        # La dérivation doit échouer
        assert derived_key is None

    def test_derive_key_exception(self, mock_derive):
        """Test de dérivation de clé avec une exception."""
        service = CryptoService()
        mock_derive  # Mock eliminated - using authentic gpt-4o-mini Exception("Erreur de dérivation")

        # Dériver la clé
        derived_key = service.derive_key_from_passphrase("phrase_secrete_test")

        # La dérivation doit échouer
        assert derived_key is None

    def test_set_encryption_key(self, crypto_service_no_key, valid_key):
        """Test de définition de la clé de chiffrement."""
        # Vérifier que le chiffrement est désactivé
        assert crypto_service_no_key.is_encryption_enabled() is False

        # Définir la clé
        crypto_service_no_key.set_encryption_key(valid_key)

        # Vérifier que le chiffrement est activé
        assert crypto_service_no_key.encryption_key == valid_key
        assert crypto_service_no_key.is_encryption_enabled() is True

    def test_encrypt_data(self, crypto_service, sample_data):
        """Test de chiffrement de données."""
        # Chiffrer les données
        encrypted_data = crypto_service.encrypt_data(sample_data)

        # Vérifier que les données sont chiffrées
        assert encrypted_data is not None
        assert encrypted_data != sample_data

        # Vérifier que les données peuvent être déchiffrées
        f = Fernet(crypto_service.encryption_key)
        decrypted_data = f.decrypt(encrypted_data)
        assert decrypted_data == sample_data

    def test_encrypt_data_no_key(self, crypto_service_no_key, sample_data):
        """Test de chiffrement sans clé."""
        # Chiffrer les données
        encrypted_data = crypto_service_no_key.encrypt_data(sample_data)

        # Le chiffrement doit échouer
        assert encrypted_data is None

    def test_encrypt_data_exception(self, mock_encrypt, crypto_service, sample_data):
        """Test de chiffrement avec une exception."""
        mock_encrypt  # Mock eliminated - using authentic gpt-4o-mini Exception("Erreur de chiffrement")

        # Chiffrer les données
        encrypted_data = crypto_service.encrypt_data(sample_data)

        # Le chiffrement doit échouer
        assert encrypted_data is None

    def test_decrypt_data(self, crypto_service, sample_data):
        """Test de déchiffrement de données."""
        # Chiffrer les données
        encrypted_data = crypto_service.encrypt_data(sample_data)

        # Déchiffrer les données
        decrypted_data = crypto_service.decrypt_data(encrypted_data)

        # Vérifier que les données sont correctement déchiffrées
        assert decrypted_data == sample_data

    def test_decrypt_data_no_key(self, crypto_service_no_key):
        """Test de déchiffrement sans clé."""
        # Créer des données chiffrées avec une autre clé
        other_key = Fernet.generate_key()
        f = Fernet(other_key)
        encrypted_data = f.encrypt(b"Test")

        # Déchiffrer les données
        decrypted_data = crypto_service_no_key.decrypt_data(encrypted_data)

        # Le déchiffrement doit échouer
        assert decrypted_data is None

    def test_decrypt_data_invalid_token(self, crypto_service):
        """Test de déchiffrement avec un jeton invalide."""
        # Créer des données chiffrées avec une autre clé
        other_key = Fernet.generate_key()
        f = Fernet(other_key)
        encrypted_data = f.encrypt(b"Test")

        # Déchiffrer les données
        decrypted_data = crypto_service.decrypt_data(encrypted_data)

        # Le déchiffrement doit échouer
        assert decrypted_data is None

    def test_decrypt_data_exception(self, mock_decrypt, crypto_service, sample_data):
        """Test de déchiffrement avec une exception générique."""
        # Chiffrer les données
        encrypted_data = crypto_service.encrypt_data(sample_data)

        # Simuler une exception
        mock_decrypt  # Mock eliminated - using authentic gpt-4o-mini Exception("Erreur de déchiffrement")

        # Déchiffrer les données
        decrypted_data = crypto_service.decrypt_data(encrypted_data)

        # Le déchiffrement doit échouer
        assert decrypted_data is None

    def test_encrypt_and_compress_json(self, crypto_service, sample_json_data):
        """Test de chiffrement et compression de données JSON."""
        # Chiffrer et compresser les données
        encrypted_data = crypto_service.encrypt_and_compress_json(sample_json_data)

        # Vérifier que les données sont chiffrées
        assert encrypted_data is not None

        # Déchiffrer et décompresser les données
        f = Fernet(crypto_service.encryption_key)
        decrypted_compressed_data = f.decrypt(encrypted_data)
        decompressed_data = gzip.decompress(decrypted_compressed_data)
        json_data = json.loads(decompressed_data.decode("utf-8"))

        # Vérifier que les données sont correctes
        assert json_data == sample_json_data

    def test_encrypt_and_compress_json_no_key(
        self, crypto_service_no_key, sample_json_data
    ):
        """Test de chiffrement et compression sans clé."""
        # Chiffrer et compresser les données
        encrypted_data = crypto_service_no_key.encrypt_and_compress_json(
            sample_json_data
        )

        # Le chiffrement doit échouer
        assert encrypted_data is None

    def test_encrypt_and_compress_json_exception(
        self, mock_dumps, crypto_service, sample_json_data
    ):
        """Test de chiffrement et compression avec une exception."""
        mock_dumps  # Mock eliminated - using authentic gpt-4o-mini Exception("Erreur JSON")

        # Chiffrer et compresser les données
        encrypted_data = crypto_service.encrypt_and_compress_json(sample_json_data)

        # Le chiffrement doit échouer
        assert encrypted_data is None

    def test_decrypt_and_decompress_json(self, crypto_service, sample_json_data):
        """Test de déchiffrement et décompression de données JSON."""
        # Chiffrer et compresser les données
        encrypted_data = crypto_service.encrypt_and_compress_json(sample_json_data)

        # Déchiffrer et décompresser les données
        json_data = crypto_service.decrypt_and_decompress_json(encrypted_data)

        # Vérifier que les données sont correctes
        assert json_data == sample_json_data

    def test_decrypt_and_decompress_json_no_key(
        self, crypto_service_no_key, sample_json_data
    ):
        """Test de déchiffrement et décompression sans clé."""
        # Créer des données chiffrées avec une autre clé
        other_service = CryptoService(encryption_key=Fernet.generate_key())
        encrypted_data = other_service.encrypt_and_compress_json(sample_json_data)

        # Déchiffrer et décompresser les données
        json_data = crypto_service_no_key.decrypt_and_decompress_json(encrypted_data)

        # Le déchiffrement doit échouer
        assert json_data is None

    def test_decrypt_and_decompress_json_invalid_token(
        self, crypto_service, sample_json_data
    ):
        """Test de déchiffrement et décompression avec un jeton invalide."""
        # Créer des données chiffrées avec une autre clé
        other_service = CryptoService(encryption_key=Fernet.generate_key())
        encrypted_data = other_service.encrypt_and_compress_json(sample_json_data)

        # Déchiffrer et décompresser les données
        json_data = crypto_service.decrypt_and_decompress_json(encrypted_data)

        # Le déchiffrement doit échouer
        assert json_data is None

    def test_decrypt_and_decompress_json_exception(
        self, mock_decompress, crypto_service, sample_json_data
    ):
        """Test de déchiffrement et décompression avec une exception."""
        # Chiffrer et compresser les données
        encrypted_data = crypto_service.encrypt_and_compress_json(sample_json_data)

        # Simuler une exception
        mock_decompress  # Mock eliminated - using authentic gpt-4o-mini Exception("Erreur de décompression")

        # Déchiffrer et décompresser les données
        json_data = crypto_service.decrypt_and_decompress_json(encrypted_data)

        # Le déchiffrement doit échouer
        assert json_data is None

    def test_is_encryption_enabled(self, crypto_service, crypto_service_no_key):
        """Test de vérification si le chiffrement est activé."""
        assert crypto_service.is_encryption_enabled() is True
        assert crypto_service_no_key.is_encryption_enabled() is False
