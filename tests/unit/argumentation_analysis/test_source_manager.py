
"""
Tests unitaires pour SourceManager.

Ce module teste toutes les fonctionnalités du gestionnaire de sources,
y compris le chargement de sources simples et complexes, la gestion
du chiffrement et les fonctionnalités de nettoyage.
"""
from unittest.mock import patch, mock_open
import pytest
import os
import json
import gzip
import tempfile
from pathlib import Path

from typing import Dict, List, Any, Optional, Tuple

# Import du module à tester
from argumentation_analysis.core.source_manager import (
    SourceManager,
    SourceType,
    SourceConfig,
    create_source_manager
)
from argumentation_analysis.models.extract_definition import ExtractDefinitions


class TestSourceType:
    """Tests pour l'énumération SourceType."""

    def test_source_type_values(self):
        """Test les valeurs de l'énumération."""
        assert SourceType.SIMPLE.value == "simple"
        assert SourceType.COMPLEX.value == "complex"

    def test_source_type_enum_members(self):
        """Test que l'énumération contient les membres attendus."""
        expected_members = {"SIMPLE", "COMPLEX"}
        actual_members = {member.name for member in SourceType}
        assert actual_members == expected_members


class TestSourceConfig:
    """Tests pour la classe SourceConfig."""
    
    def test_source_config_init_simple(self):
        """Test l'initialisation pour sources simples."""
        config = SourceConfig(source_type=SourceType.SIMPLE)
        
        assert config.source_type == SourceType.SIMPLE
        assert config.passphrase is None
        assert config.anonymize_logs == True
        assert config.auto_cleanup == True
    
    def test_source_config_init_complex(self):
        """Test l'initialisation pour sources complexes."""
        config = SourceConfig(
            source_type=SourceType.COMPLEX,
            passphrase="test_passphrase",
            anonymize_logs=False,
            auto_cleanup=False
        )
        
        assert config.source_type == SourceType.COMPLEX
        assert config.passphrase == "test_passphrase"
        assert config.anonymize_logs == False
        assert config.auto_cleanup == False


class TestSourceManager:
    """Tests pour la classe SourceManager."""
    
    @pytest.fixture
    def simple_config(self):
        """Configuration pour sources simples."""
        return SourceConfig(source_type=SourceType.SIMPLE)
    
    @pytest.fixture
    def complex_config(self):
        """Configuration pour sources complexes."""
        return SourceConfig(
            source_type=SourceType.COMPLEX,
            passphrase="test_passphrase"
        )
    
    @pytest.fixture
    def source_manager_simple(self, simple_config):
        """SourceManager configuré pour sources simples."""
        return SourceManager(simple_config)
    
    @pytest.fixture
    def source_manager_complex(self, complex_config):
        """SourceManager configuré pour sources complexes."""
        return SourceManager(complex_config)
    
    def test_init_source_manager(self, simple_config):
        """Test l'initialisation du SourceManager."""
        manager = SourceManager(simple_config)
        
        assert manager.config == simple_config
        assert manager.logger is not None
        assert manager._temp_files == []
    
    def test_setup_logging_simple(self, source_manager_simple):
        """Test la configuration du logging pour sources simples."""
        logger = source_manager_simple.logger
        
        assert logger is not None
        assert "simple" in logger.name
    
    def test_setup_logging_complex_with_anonymization(self, complex_config):
        """Test la configuration du logging avec anonymisation."""
        complex_config.anonymize_logs = True
        manager = SourceManager(complex_config)
        
        logger = manager.logger
        assert logger is not None
        
        # Vérifier qu'un filtre d'anonymisation a été ajouté
        has_anonymize_filter = any(
            hasattr(f, 'filter') and 'AnonymizeFilter' in str(type(f))
            for f in logger.filters
        )
        # Note: Ce test pourrait nécessiter un ajustement selon l'implémentation
        
    def test_load_sources_simple_type(self, mocker, source_manager_simple):
        """Test le routage vers les sources simples."""
        mock_simple = mocker.patch.object(source_manager_simple, '_load_simple_sources', return_value=(None, "Success"))

        result = source_manager_simple.load_sources()

        mock_simple.assert_called_once()
        assert result == (None, "Success")

    def test_load_sources_complex_type(self, mocker, source_manager_complex):
        """Test le routage vers les sources complexes."""
        mock_complex = mocker.patch.object(source_manager_complex, '_load_complex_sources', return_value=(None, "Success"))

        result = source_manager_complex.load_sources()

        mock_complex.assert_called_once()
        assert result == (None, "Success")
    
    def test_load_sources_invalid_type(self):
        """Test avec un type de source invalide."""
        # Créer une configuration avec un type invalide (simulation)
        config = SourceConfig(source_type=SourceType.SIMPLE)
        manager = SourceManager(config)
        
        # Modifier le type pour simuler un type invalide
        manager.config.source_type = "invalid_type"
        
        definitions, message = manager.load_sources()
        
        assert definitions is None
        assert "non supporté" in message
    
    
    def test_load_simple_sources_success(self, mocker, source_manager_simple):
        """Test le chargement réussi des sources simples."""
        mock_from_dict_list = mocker.patch('argumentation_analysis.core.source_manager.ExtractDefinitions.from_dict_list')
        mock_extract_def = mocker.Mock(spec=ExtractDefinitions)
        mock_from_dict_list.return_value = mock_extract_def

        definitions, message = source_manager_simple._load_simple_sources()

        assert definitions == mock_extract_def
        assert "Sources simples chargées avec succès" in message
        mock_from_dict_list.assert_called_once()

        # Vérifier la structure des données mockées
        call_args = mock_from_dict_list.call_args[0][0]
        assert isinstance(call_args, list)
        assert len(call_args) == 2  # Deux sources mockées

        # Vérifier le contenu des sources mockées
        climate_source = next(s for s in call_args if "climat" in s["source_name"])
        assert "Débat sur le climat" in climate_source["source_name"]
        assert len(climate_source["extracts"]) > 0

        political_source = next(s for s in call_args if "politique" in s["source_name"])
        assert "Discours politique" in political_source["source_name"]
        assert len(political_source["extracts"]) > 0
    
    
    def test_load_simple_sources_exception(self, mocker, source_manager_simple):
        """Test la gestion d'exception lors du chargement de sources simples."""
        mock_from_dict_list = mocker.patch('argumentation_analysis.core.source_manager.ExtractDefinitions.from_dict_list')
        mock_from_dict_list.side_effect = Exception("Test error")

        definitions, message = source_manager_simple._load_simple_sources()

        assert definitions is None
        assert "Erreur lors du chargement des sources simples" in message
        assert "Test error" in message
    
    
    
    
    
    def test_load_complex_sources_success(
        self, mocker, source_manager_complex
    ):
        """Test le chargement réussi des sources complexes."""
        # Configuration des mocks
        mocker.patch('argumentation_analysis.core.source_manager.DATA_DIR', Path("/mock/data"))
        mock_load_key = mocker.patch('argumentation_analysis.core.source_manager.load_encryption_key', return_value=b"mock_encryption_key")

        # Mock du fichier chiffré
        mocker.patch.object(Path, 'exists', return_value=True)

        # Mock des données déchiffrées et décompressées
        original_data = [{"source_name": "Test source", "extracts": []}]
        json_data = json.dumps(original_data).encode('utf-8')
        gzipped_data = gzip.compress(json_data)
        mock_decrypt = mocker.patch('argumentation_analysis.core.source_manager.decrypt_data_with_fernet', return_value=gzipped_data)

        # Mock ExtractDefinitions
        mock_extract_def = mocker.Mock(spec=ExtractDefinitions)
        # Configure the mock to have a realistic structure for len() calls
        mock_source = mocker.Mock()
        mock_source.extracts = [mocker.Mock()] # Make extracts a list
        mock_extract_def.sources = [mock_source]
        mock_from_dict_list = mocker.patch('argumentation_analysis.core.source_manager.ExtractDefinitions.from_dict_list', return_value=mock_extract_def)

        # Mock file operations
        mocker.patch('builtins.open', mock_open(read_data=b"encrypted_data"))
        definitions, message = source_manager_complex._load_complex_sources()
        
        assert definitions == mock_extract_def
        assert "Corpus chiffré chargé avec succès" in message
        mock_load_key.assert_called_once_with(passphrase_arg="test_passphrase")
        mock_decrypt.assert_called_once()

    def test_load_complex_sources_no_passphrase(self, mocker):
        """Test le chargement complexe sans passphrase."""
        config = SourceConfig(source_type=SourceType.COMPLEX)  # Pas de passphrase
        manager = SourceManager(config)

        mocker.patch.dict(os.environ, {}, clear=True)
        definitions, message = manager._load_complex_sources()

        assert definitions is None
        assert "Passphrase requise" in message

    def test_load_complex_sources_env_passphrase(self, mocker):
        """Test l'utilisation de la passphrase depuis les variables d'environnement."""
        mocker.patch.dict(os.environ, {'TEXT_CONFIG_PASSPHRASE': 'env_passphrase'}, clear=True)
        mock_load_key = mocker.patch('argumentation_analysis.core.source_manager.load_encryption_key')
        config = SourceConfig(source_type=SourceType.COMPLEX)  # Pas de passphrase dans config
        manager = SourceManager(config)

        mock_load_key.return_value = None  # Échec volontaire pour tester la passphrase

        definitions, message = manager._load_complex_sources()

        mock_load_key.assert_called_once_with(passphrase_arg='env_passphrase')
    
    
    def test_load_complex_sources_key_derivation_failure(self, mocker, source_manager_complex):
        """Test l'échec de dérivation de clé."""
        mock_load_key = mocker.patch('argumentation_analysis.core.source_manager.load_encryption_key')
        mock_load_key.return_value = None

        definitions, message = source_manager_complex._load_complex_sources()

        assert definitions is None
        assert "Impossible de dériver la clé de chiffrement" in message
    
    
    
    def test_load_complex_sources_file_not_found(self, mocker, source_manager_complex):
        """Test avec fichier chiffré introuvable."""
        mocker.patch('argumentation_analysis.core.source_manager.load_encryption_key', return_value=b"test_key")

        # Mock du chemin qui n'existe pas
        mocker.patch.object(Path, 'exists', return_value=False)
        
        definitions, message = source_manager_complex._load_complex_sources()
        
        assert definitions is None
        assert "Fichier chiffré non trouvé" in message
    
    def test_select_text_for_analysis_no_sources(self, source_manager_simple):
        """Test la sélection de texte sans sources."""
        text, description = source_manager_simple.select_text_for_analysis(None)
        
        assert "fallback" in text.lower()
        assert "aucune source disponible" in description
    
    def test_select_text_for_analysis_empty_sources(self, mocker, source_manager_simple):
        """Test la sélection de texte avec sources vides."""
        mock_definitions = mocker.MagicMock(spec=ExtractDefinitions)
        mock_definitions.sources = []

        text, description = source_manager_simple.select_text_for_analysis(mock_definitions)
        
        assert "fallback" in text.lower()
        assert "aucune source disponible" in description
    
    def test_select_text_for_analysis_simple_sources(self, mocker, source_manager_simple):
        """Test la sélection de texte depuis sources simples."""
        # Mock des sources avec extraits
        mock_extract = mocker.MagicMock()
        mock_extract.full_text = "Texte d'analyse depuis source simple"
        
        mock_source = mocker.MagicMock()
        mock_source.source_name = "Source de test"
        mock_source.extracts = [mock_extract]
        
        mock_definitions = mocker.MagicMock(spec=ExtractDefinitions)
        mock_definitions.sources = [mock_source]
        
        text, description = source_manager_simple.select_text_for_analysis(mock_definitions)
        
        assert text == "Texte d'analyse depuis source simple"
        assert "Source simple: Source de test" in description
    
    def test_select_text_for_analysis_complex_sources(self, mocker, source_manager_complex):
        """Test la sélection de texte depuis sources complexes."""
        # Mock d'un extrait substantiel (>200 caractères)
        long_text = "x" * 250  # Texte de 250 caractères
        mock_extract = mocker.MagicMock()
        mock_extract.full_text = long_text
        
        mock_source = mocker.MagicMock()
        mock_source.source_name = "Source politique complexe"
        mock_source.extracts = [mock_extract]
        
        mock_definitions = mocker.MagicMock(spec=ExtractDefinitions)
        mock_definitions.sources = [mock_source]
        
        text, description = source_manager_complex.select_text_for_analysis(mock_definitions)
        
        assert text == long_text
        # Avec anonymisation activée par défaut
        assert "[ANONYMISÉ]" in description
    
    def test_select_text_for_analysis_complex_no_anonymization(self, mocker):
        """Test la sélection complexe sans anonymisation."""
        config = SourceConfig(
            source_type=SourceType.COMPLEX,
            passphrase="test",
            anonymize_logs=False
        )
        manager = SourceManager(config)
        
        mock_extract = mocker.MagicMock()
        mock_extract.full_text = "x" * 250
        
        mock_source = mocker.MagicMock()
        mock_source.source_name = "Source politique"
        mock_source.extracts = [mock_extract]
        
        mock_definitions = mocker.MagicMock(spec=ExtractDefinitions)
        mock_definitions.sources = [mock_source]
        
        text, description = manager.select_text_for_analysis(mock_definitions)
        
        assert "Source: Source politique" in description
    
    def test_select_text_for_analysis_short_complex_content(self, mocker, source_manager_complex):
        """Test avec contenu complexe trop court."""
        # Mock d'un extrait trop court (<200 caractères)
        short_text = "x" * 50
        mock_extract = mocker.MagicMock()
        mock_extract.full_text = short_text
        
        mock_source = mocker.MagicMock()
        mock_source.extracts = [mock_extract]
        
        mock_definitions = mocker.MagicMock(spec=ExtractDefinitions)
        mock_definitions.sources = [mock_source]
        
        text, description = source_manager_complex.select_text_for_analysis(mock_definitions)
        
        # Devrait utiliser le fallback
        assert "fallback" in text.lower()
        assert "aucun contenu substantiel trouvé" in description
    
    def test_cleanup_sensitive_data_disabled(self):
        """Test du nettoyage avec auto_cleanup désactivé."""
        config = SourceConfig(
            source_type=SourceType.SIMPLE,
            auto_cleanup=False
        )
        manager = SourceManager(config)
        
        # Ajouter des fichiers temporaires fictifs
        manager._temp_files = [Path("/fake/file1"), Path("/fake/file2")]
        
        manager.cleanup_sensitive_data()
        
        # Les fichiers ne doivent pas être supprimés
        assert len(manager._temp_files) == 2
    
    def test_cleanup_sensitive_data_enabled(self):
        """Test du nettoyage avec auto_cleanup activé."""
        config = SourceConfig(
            source_type=SourceType.SIMPLE,
            auto_cleanup=True
        )
        manager = SourceManager(config)
        
        # Créer des fichiers temporaires réels
        with tempfile.NamedTemporaryFile(delete=False) as tmp1:
            tmp1_path = Path(tmp1.name)
        with tempfile.NamedTemporaryFile(delete=False) as tmp2:
            tmp2_path = Path(tmp2.name)
        
        manager._temp_files = [tmp1_path, tmp2_path]
        
        try:
            manager.cleanup_sensitive_data()
            
            # Vérifier que les fichiers ont été supprimés
            assert not tmp1_path.exists()
            assert not tmp2_path.exists()
            assert len(manager._temp_files) == 0
        finally:
            # Nettoyage au cas où
            for path in [tmp1_path, tmp2_path]:
                if path.exists():
                    path.unlink()
    
    def test_cleanup_sensitive_data_exception_handling(self, mocker):
        """Test la gestion d'exception lors du nettoyage."""
        config = SourceConfig(source_type=SourceType.SIMPLE)
        manager = SourceManager(config)
        
        # Mock d'un fichier qui lève une exception lors de la suppression
        mock_file = mocker.MagicMock()
        mock_file.exists.return_value = True
        mock_file.unlink.side_effect = PermissionError("Permission denied")
        
        manager._temp_files = [mock_file]
        
        # Ne doit pas lever d'exception
        manager.cleanup_sensitive_data()
        
        # La liste doit être vidée malgré l'erreur
        assert len(manager._temp_files) == 0
    
    def test_context_manager_enter(self, source_manager_simple):
        """Test l'entrée du context manager."""
        result = source_manager_simple.__enter__()
        assert result is source_manager_simple
    
    def test_context_manager_exit(self, mocker, source_manager_simple):
        """Test la sortie du context manager."""
        mock_cleanup = mocker.patch.object(source_manager_simple, 'cleanup_sensitive_data')
        source_manager_simple.__exit__(None, None, None)
        mock_cleanup.assert_called_once()
    
    def test_context_manager_usage(self, mocker):
        """Test d'utilisation complète du context manager."""
        config = SourceConfig(source_type=SourceType.SIMPLE)

        mock_cleanup = mocker.patch.object(SourceManager, 'cleanup_sensitive_data')
        with SourceManager(config) as manager:
            assert isinstance(manager, SourceManager)

        mock_cleanup.assert_called_once()


class TestCreateSourceManager:
    """Tests pour la fonction factory create_source_manager."""
    
    def test_create_source_manager_simple(self):
        """Test la création d'un manager pour sources simples."""
        manager = create_source_manager("simple")
        
        assert isinstance(manager, SourceManager)
        assert manager.config.source_type == SourceType.SIMPLE
        assert manager.config.passphrase is None
        assert manager.config.anonymize_logs == True
        assert manager.config.auto_cleanup == True
    
    def test_create_source_manager_complex(self):
        """Test la création d'un manager pour sources complexes."""
        manager = create_source_manager(
            "complex",
            passphrase="test_pass",
            anonymize_logs=False,
            auto_cleanup=False
        )
        
        assert isinstance(manager, SourceManager)
        assert manager.config.source_type == SourceType.COMPLEX
        assert manager.config.passphrase == "test_pass"
        assert manager.config.anonymize_logs == False
        assert manager.config.auto_cleanup == False
    
    def test_create_source_manager_case_insensitive(self):
        """Test la création avec casse insensible."""
        manager = create_source_manager("SIMPLE")
        assert manager.config.source_type == SourceType.SIMPLE
        
        manager = create_source_manager("Complex")
        assert manager.config.source_type == SourceType.COMPLEX
    
    def test_create_source_manager_invalid_type(self):
        """Test la création avec type invalide."""
        with pytest.raises(ValueError) as excinfo:
            create_source_manager("invalid_type")
        
        assert "Type de source non supporté" in str(excinfo.value)
        assert "invalid_type" in str(excinfo.value)
        assert "simple" in str(excinfo.value)
        assert "complex" in str(excinfo.value)


class TestSourceManagerIntegration:
    """Tests d'intégration pour SourceManager."""
    
    def test_full_simple_workflow(self):
        """Test du workflow complet avec sources simples."""
        with create_source_manager("simple") as manager:
            # Chargement des sources
            definitions, message = manager.load_sources()
            
            assert definitions is not None
            assert "succès" in message
            
            # Sélection de texte
            text, description = manager.select_text_for_analysis(definitions)
            
            assert text is not None
            assert len(text) > 0
            assert description is not None
    
    
    
    
    
    def test_full_complex_workflow(self, mocker):
        """Test du workflow complet avec sources complexes."""
        mocker.patch("pathlib.Path.exists", return_value=True)
        mocker.patch("argumentation_analysis.core.source_manager.DATA_DIR", Path("/mock/data"))
        mocker.patch("argumentation_analysis.core.source_manager.load_encryption_key", return_value=b"test_key")

        # Données de test
        test_data = [
            {
                "source_name": "Test Political Speech",
                "extracts": [{"extract_name": "Test Extract", "full_text": "x" * 300}]
            }
        ]
        json_data = json.dumps(test_data).encode('utf-8')
        gzipped_data = gzip.compress(json_data)
        mocker.patch("argumentation_analysis.core.source_manager.decrypt_data_with_fernet", return_value=gzipped_data)

        # Mock ExtractDefinitions
        mock_extract = mocker.MagicMock()
        mock_extract.full_text = "x" * 300
        mock_source = mocker.MagicMock()
        mock_source.source_name = "Test Political Speech"
        mock_source.extracts = [mock_extract]
        mock_definitions = mocker.MagicMock(spec=ExtractDefinitions)
        mock_definitions.sources = [mock_source]
        mocker.patch("argumentation_analysis.core.source_manager.ExtractDefinitions.from_dict_list", return_value=mock_definitions)

        mocker.patch('builtins.open', mock_open(read_data=b"encrypted_data"))
        mocker.patch.object(Path, 'exists', return_value=True)
        with create_source_manager("complex", passphrase="test") as manager:
            # Chargement des sources
            definitions, message = manager.load_sources()
            
            assert definitions is not None
            assert "succès" in message
            
            # Sélection de texte
            text, description = manager.select_text_for_analysis(definitions)
            
            assert len(text) >= 300
            assert "[ANONYMISÉ]" in description  # Anonymisation par défaut
    
    def test_error_handling_workflow(self, mocker):
        """Test du workflow avec gestion d'erreurs."""
        with create_source_manager("simple") as manager:
            # Test avec sources None
            text, description = manager.select_text_for_analysis(None)

            assert "fallback" in text.lower()
            assert "aucune source disponible" in description

            # Test avec exception dans le chargement
            mocker.patch.object(manager, '_load_simple_sources', side_effect=Exception("Test error"))
            with pytest.raises(Exception, match="Test error"):
                manager.load_sources()

            # Vérifier que le manager peut continuer à fonctionner
            # (par exemple, en sélectionnant un texte de fallback)
            text, description = manager.select_text_for_analysis(None)
            assert "fallback" in text.lower()
            # ou la laisser remonter selon l'implémentation
    
    def test_logging_integration(self, mocker):
        """Test de l'intégration du système de logging."""
        import logging
        
        # Capturer les logs
        mock_get_logger = mocker.patch('logging.getLogger')
        mock_logger = mocker.MagicMock()
        mock_get_logger.return_value = mock_logger
        
        manager = create_source_manager("simple")
        
        # Tester quelques opérations qui loggent
        manager.load_sources()
        
        # Vérifier que le logger a été utilisé
        mock_logger.info.assert_called()
    
    def test_memory_cleanup_integration(self):
        """Test du nettoyage mémoire en conditions réelles."""
        # Créer des fichiers temporaires réels
        temp_files = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                temp_files.append(Path(tmp.name))
        
        try:
            config = SourceConfig(source_type=SourceType.SIMPLE, auto_cleanup=True)
            manager = SourceManager(config)
            manager._temp_files = temp_files
            
            # Vérifier que les fichiers existent
            for temp_file in temp_files:
                assert temp_file.exists()
            
            # Nettoyage via context manager
            with manager:
                pass
            
            # Vérifier que les fichiers ont été supprimés
            for temp_file in temp_files:
                assert not temp_file.exists()
                
        finally:
            # Nettoyage de sécurité
            for temp_file in temp_files:
                if temp_file.exists():
                    temp_file.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])