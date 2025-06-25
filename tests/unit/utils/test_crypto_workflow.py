#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests unitaires pour le module crypto_workflow
============================================

Tests pour :
- CryptoWorkflowManager
- Déchiffrement de corpus
- Validation d'intégrité
- Gestion des erreurs
"""

import pytest
import asyncio
import tempfile
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

import sys
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from argumentation_analysis.utils.crypto_workflow import (
    CryptoWorkflowManager,
    CorpusDecryptionResult,
    create_crypto_manager
)


class TestCryptoWorkflowManager:
    """Tests pour CryptoWorkflowManager."""
    
    def test_init_default_passphrase(self):
        """Test initialisation avec passphrase par défaut."""
        manager = CryptoWorkflowManager()
        assert manager.passphrase is not None
        assert len(manager.passphrase) > 0
    
    def test_init_custom_passphrase(self):
        """Test initialisation avec passphrase personnalisée."""
        custom_passphrase = "test_passphrase_123"
        manager = CryptoWorkflowManager(custom_passphrase)
        assert manager.passphrase == custom_passphrase
    
    def test_derive_encryption_key(self):
        """Test dérivation de clé de chiffrement."""
        manager = CryptoWorkflowManager("test_key")
        key1 = manager.derive_encryption_key()
        key2 = manager.derive_encryption_key()
        
        # La clé doit être stable (même passphrase = même clé)
        assert key1 == key2
        assert len(key1) == 44  # Base64 de 32 bytes
    
    def test_derive_encryption_key_different_passphrases(self):
        """Test que différentes passphrases donnent différentes clés."""
        manager1 = CryptoWorkflowManager("passphrase1")
        manager2 = CryptoWorkflowManager("passphrase2")
        
        key1 = manager1.derive_encryption_key()
        key2 = manager2.derive_encryption_key()
        
        assert key1 != key2
    
    @pytest.mark.asyncio
    async def test_load_encrypted_corpus_file_not_found(self):
        """Test avec fichier non existant."""
        manager = CryptoWorkflowManager("test_key")
        
        result = await manager.load_encrypted_corpus(["nonexistent.enc"])
        
        assert not result.success
        assert len(result.errors) > 0
        assert "non trouvé" in result.errors[0]
        assert result.total_definitions == 0
    
    @pytest.mark.asyncio
    async def test_load_encrypted_corpus_empty_list(self):
        """Test avec liste vide de fichiers."""
        manager = CryptoWorkflowManager("test_key")
        
        result = await manager.load_encrypted_corpus([])
        
        assert result.success  # Pas d'erreur si liste vide
        assert len(result.loaded_files) == 0
        assert result.total_definitions == 0
    
    @pytest.mark.asyncio
    @patch('argumentation_analysis.utils.crypto_workflow.load_extract_definitions')
    async def test_load_encrypted_corpus_success(self, mock_load):
        """Test déchiffrement réussi."""
        mock_definitions = [
            {"content": "Texte de test 1", "id": "def1"},
            {"content": "Texte de test 2", "id": "def2"}
        ]
        mock_load.return_value = mock_definitions

        with tempfile.NamedTemporaryFile(suffix=".enc", delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
            tmp_file.write(b"dummy_content")

        try:
            manager = CryptoWorkflowManager("test_key")
            result = await manager.load_encrypted_corpus([str(tmp_path)])

            assert result.success
            assert result.total_definitions == 2
            assert len(result.loaded_files) == 1
            assert result.loaded_files[0]["definitions_count"] == 2
            assert mock_load.call_count == 1
        finally:
            tmp_path.unlink()
    
    @pytest.mark.asyncio
    @patch('argumentation_analysis.utils.crypto_workflow.load_extract_definitions')
    async def test_load_encrypted_corpus_decryption_failure(self, mock_load):
        """Test échec de déchiffrement."""
        # Mock qui retourne None (échec)
        mock_load.return_value = None
        
        with tempfile.NamedTemporaryFile(suffix=".enc", delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
        
        try:
            manager = CryptoWorkflowManager("test_key")
            result = await manager.load_encrypted_corpus([str(tmp_path)])
            
            assert not result.success
            assert len(result.errors) > 0
            assert "Échec du déchiffrement" in result.errors[0]
            
        finally:
            tmp_path.unlink()
    
    @pytest.mark.asyncio
    async def test_load_encrypted_corpus_import_error(self):
        """Test avec modules de déchiffrement non disponibles."""
        with tempfile.NamedTemporaryFile(suffix=".enc", delete=True) as tmp_file:
            with patch('argumentation_analysis.utils.crypto_workflow.load_extract_definitions', side_effect=ImportError("Module not found")):
                manager = CryptoWorkflowManager("test_key")
                result = await manager.load_encrypted_corpus([tmp_file.name])
                
                assert not result.success
                assert len(result.errors) > 0
                assert "non disponibles" in result.errors[0]
    
    def test_validate_corpus_integrity_empty(self):
        """Test validation avec corpus vide."""
        manager = CryptoWorkflowManager("test_key")
        
        valid, errors = manager.validate_corpus_integrity({"loaded_files": []})
        
        assert not valid
        assert "Aucun fichier chargé" in errors[0]
    
    def test_validate_corpus_integrity_valid(self):
        """Test validation avec corpus valide."""
        manager = CryptoWorkflowManager("test_key")
        
        corpus_data = {
            "loaded_files": [
                {
                    "file": "test.enc",
                    "definitions": [
                        {"content": "Texte valide", "id": "def1"}
                    ]
                }
            ]
        }
        
        valid, errors = manager.validate_corpus_integrity(corpus_data)
        
        assert valid
        assert len(errors) == 0
    
    def test_validate_corpus_integrity_missing_content(self):
        """Test validation avec contenu manquant."""
        manager = CryptoWorkflowManager("test_key")
        
        corpus_data = {
            "loaded_files": [
                {
                    "file": "test.enc",
                    "definitions": [
                        {"id": "def1"}  # Pas de contenu
                    ]
                }
            ]
        }
        
        valid, errors = manager.validate_corpus_integrity(corpus_data)
        
        assert not valid
        assert len(errors) > 0
        assert "sans contenu" in errors[0]


class TestCorpusDecryptionResult:
    """Tests pour CorpusDecryptionResult."""
    
    def test_init_defaults(self):
        """Test initialisation avec valeurs par défaut."""
        result = CorpusDecryptionResult(
            success=True,
            loaded_files=[],
            errors=[],
            total_definitions=0,
            processing_time=1.5
        )
        
        assert result.success is True
        assert len(result.loaded_files) == 0
        assert len(result.errors) == 0
        assert result.total_definitions == 0
        assert result.processing_time == 1.5


class TestFactoryFunction:
    """Tests pour les fonctions factory."""
    
    def test_create_crypto_manager_default(self):
        """Test création avec paramètres par défaut."""
        manager = create_crypto_manager()
        
        assert isinstance(manager, CryptoWorkflowManager)
        assert manager.passphrase is not None
    
    def test_create_crypto_manager_custom_passphrase(self):
        """Test création avec passphrase personnalisée."""
        custom_passphrase = "custom_test_key"
        manager = create_crypto_manager(custom_passphrase)
        
        assert isinstance(manager, CryptoWorkflowManager)
        assert manager.passphrase == custom_passphrase


# Tests d'intégration (optionnels, nécessitent dépendances complètes)
class TestCryptoWorkflowIntegration:
    """Tests d'intégration pour crypto_workflow."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_workflow_simulation(self):
        """Test du workflow complet en simulation."""
        manager = CryptoWorkflowManager("integration_test_key")
        
        # Test avec fichiers simulés
        with patch('argumentation_analysis.utils.crypto_workflow.load_extract_definitions') as mock_load:
            mock_load.return_value = [
                {"content": "Texte d'intégration 1", "id": "int1"},
                {"content": "Texte d'intégration 2", "id": "int2"}
            ]
            
            with tempfile.NamedTemporaryFile(suffix=".enc") as tmp_file:
                result = await manager.load_encrypted_corpus([tmp_file.name])
                
                # Validation du résultat
                assert result.success
                assert result.total_definitions == 2
                
                # Validation de l'intégrité
                valid, errors = manager.validate_corpus_integrity({
                    "loaded_files": result.loaded_files
                })
                assert valid
                assert len(errors) == 0


if __name__ == "__main__":
    # Exécution des tests
    pytest.main([__file__, "-v"])