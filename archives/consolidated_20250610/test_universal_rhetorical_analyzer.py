#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests pour Universal Rhetorical Analyzer
========================================

Tests d'intégration pour le script unifié qui combine :
- unified_production_analyzer.py
- comprehensive_workflow_processor.py

Tests couvrant tous les modes et types de sources.
"""

import pytest
import asyncio
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

import sys
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.consolidated.universal_rhetorical_analyzer import (
    UniversalRhetoricalAnalyzer,
    UniversalConfig,
    SourceType,
    WorkflowMode,
    create_config_from_args,
    create_cli_parser
)


class TestUniversalConfig:
    """Tests pour UniversalConfig."""
    
    def test_init_defaults(self):
        """Test initialisation avec valeurs par défaut."""
        config = UniversalConfig()
        
        assert config.source_type == SourceType.TEXT
        assert config.workflow_mode == WorkflowMode.ANALYSIS
        assert config.analysis_modes == ["unified"]
        assert config.require_authentic is True
        assert config.parallel_workers == 4
    
    def test_post_init_performance_mode(self):
        """Test configuration automatique en mode performance."""
        config = UniversalConfig(workflow_mode=WorkflowMode.PERFORMANCE)
        
        assert config.require_authentic is False
        assert config.mock_level == "minimal"
    
    def test_corpus_files_normalization(self):
        """Test normalisation des fichiers de corpus."""
        config = UniversalConfig(corpus_files=None)
        assert config.corpus_files == []
        
        config = UniversalConfig(corpus_files=["file1.enc", "file2.enc"])
        assert len(config.corpus_files) == 2


class TestUniversalRhetoricalAnalyzer:
    """Tests pour UniversalRhetoricalAnalyzer."""
    
    def test_init(self):
        """Test initialisation de l'analyseur."""
        config = UniversalConfig()
        analyzer = UniversalRhetoricalAnalyzer(config)
        
        assert analyzer.config == config
        assert analyzer.session_id.startswith("universal_")
        assert len(analyzer.results) == 0
    
    @pytest.mark.asyncio
    async def test_analyze_text_direct(self):
        """Test analyse de texte direct."""
        config = UniversalConfig(
            source_type=SourceType.TEXT,
            require_authentic=False  # Mode test
        )
        analyzer = UniversalRhetoricalAnalyzer(config)
        
        result = await analyzer.analyze("Texte de test pour analyse directe")
        
        assert result["status"] == "completed"
        assert "session_id" in result
        assert "results" in result
        assert result["config"]["source_type"] == "text"
    
    @pytest.mark.asyncio
    async def test_analyze_file_source(self):
        """Test analyse depuis fichier."""
        config = UniversalConfig(
            source_type=SourceType.FILE,
            require_authentic=False
        )
        analyzer = UniversalRhetoricalAnalyzer(config)
        
        # Création d'un fichier temporaire
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Contenu du fichier de test pour analyse")
            test_file = f.name
        
        try:
            result = await analyzer.analyze(test_file)
            
            assert result["status"] == "completed"
            assert result["config"]["source_type"] == "file"
            
        finally:
            Path(test_file).unlink()  # Nettoyage
    
    @pytest.mark.asyncio
    async def test_analyze_file_not_found(self):
        """Test avec fichier inexistant."""
        config = UniversalConfig(source_type=SourceType.FILE)
        analyzer = UniversalRhetoricalAnalyzer(config)
        
        result = await analyzer.analyze("fichier_inexistant.txt")
        
        assert result["status"] == "error"
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_analyze_batch_directory(self):
        """Test analyse batch d'un répertoire."""
        config = UniversalConfig(
            source_type=SourceType.BATCH,
            require_authentic=False
        )
        analyzer = UniversalRhetoricalAnalyzer(config)
        
        # Création d'un répertoire temporaire avec fichiers
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Création de fichiers de test
            (temp_path / "test1.txt").write_text("Contenu fichier 1")
            (temp_path / "test2.md").write_text("Contenu fichier 2")
            
            result = await analyzer.analyze(str(temp_path))
            
            assert result["status"] == "completed"
            assert result["config"]["source_type"] == "batch"
    
    @pytest.mark.asyncio
    async def test_workflow_mode_full(self):
        """Test mode workflow complet."""
        config = UniversalConfig(
            workflow_mode=WorkflowMode.FULL,
            require_authentic=False
        )
        analyzer = UniversalRhetoricalAnalyzer(config)
        
        result = await analyzer.analyze("Texte pour workflow complet")
        
        assert result["status"] == "completed"
        assert "analysis" in result["results"]
        assert "validation" in result["results"]
    
    @pytest.mark.asyncio
    async def test_workflow_mode_validation(self):
        """Test mode validation uniquement."""
        config = UniversalConfig(
            workflow_mode=WorkflowMode.VALIDATION,
            require_authentic=False
        )
        analyzer = UniversalRhetoricalAnalyzer(config)
        
        result = await analyzer.analyze("Texte pour validation")
        
        assert result["status"] == "completed"
        assert "validation" in result["results"]
        assert result["results"]["workflow_type"] == "validation_only"
    
    @pytest.mark.asyncio
    async def test_workflow_mode_performance(self):
        """Test mode performance."""
        config = UniversalConfig(
            workflow_mode=WorkflowMode.PERFORMANCE,
            # Mode performance configure automatiquement require_authentic=False
        )
        analyzer = UniversalRhetoricalAnalyzer(config)
        
        result = await analyzer.analyze("Texte pour test performance")
        
        assert result["status"] == "completed"
        assert "performance_tests" in result["results"]
        assert "average_duration" in result["results"]
    
    @pytest.mark.asyncio
    @patch('argumentation_analysis.utils.crypto_workflow.create_crypto_manager')
    async def test_analyze_encrypted_source(self, mock_crypto):
        """Test analyse de source chiffrée."""
        # Mock du gestionnaire crypto
        mock_manager = Mock()
        mock_manager.load_encrypted_corpus = AsyncMock(return_value=Mock(
            success=True,
            loaded_files=[{
                "definitions": [{"content": "Texte déchiffré"}]
            }]
        ))
        mock_crypto.return_value = mock_manager
        
        config = UniversalConfig(
            source_type=SourceType.ENCRYPTED,
            require_authentic=False
        )
        analyzer = UniversalRhetoricalAnalyzer(config)
        
        result = await analyzer.analyze("fichier_chiffre.enc")
        
        assert result["status"] == "completed"
        assert result["config"]["source_type"] == "encrypted"
    
    @pytest.mark.asyncio
    async def test_save_results(self):
        """Test sauvegarde des résultats."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_results.json"
            
            config = UniversalConfig(
                output_file=output_file,
                require_authentic=False
            )
            analyzer = UniversalRhetoricalAnalyzer(config)
            
            result = await analyzer.analyze("Texte pour test sauvegarde")
            
            assert output_file.exists()
            
            # Vérification du contenu
            with open(output_file, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
            
            assert saved_data["session_id"] == result["session_id"]
            assert saved_data["status"] == "completed"


class TestCLIParser:
    """Tests pour le parser CLI."""
    
    def test_create_cli_parser(self):
        """Test création du parser CLI."""
        parser = create_cli_parser()
        
        assert parser.prog is not None
        assert "universal" in parser.description.lower()
    
    def test_parse_basic_arguments(self):
        """Test parsing d'arguments basiques."""
        parser = create_cli_parser()
        
        args = parser.parse_args([
            "texte de test",
            "--source-type", "text",
            "--workflow-mode", "analysis"
        ])
        
        assert args.input == "texte de test"
        assert args.source_type == "text"
        assert args.workflow_mode == "analysis"
    
    def test_parse_corpus_arguments(self):
        """Test parsing d'arguments pour corpus."""
        parser = create_cli_parser()
        
        args = parser.parse_args([
            "--source-type", "corpus",
            "--corpus", "file1.enc", "file2.enc",
            "--passphrase", "test_key"
        ])
        
        assert args.source_type == "corpus"
        assert args.corpus == ["file1.enc", "file2.enc"]
        assert args.passphrase == "test_key"
    
    def test_parse_parallel_arguments(self):
        """Test parsing d'arguments de parallélisme."""
        parser = create_cli_parser()
        
        args = parser.parse_args([
            "test",
            "--parallel-workers", "8",
            "--analysis-modes", "fallacies", "rhetoric"
        ])
        
        assert args.parallel_workers == 8
        assert args.analysis_modes == ["fallacies", "rhetoric"]


class TestConfigFromArgs:
    """Tests pour create_config_from_args."""
    
    def test_create_config_basic(self):
        """Test création de config basique."""
        parser = create_cli_parser()
        args = parser.parse_args(["test_text"])
        
        config = create_config_from_args(args)
        
        assert isinstance(config, UniversalConfig)
        assert config.source_type == SourceType.TEXT
        assert config.workflow_mode == WorkflowMode.ANALYSIS
    
    def test_create_config_corpus_mode(self):
        """Test création de config pour mode corpus."""
        parser = create_cli_parser()
        args = parser.parse_args([
            "--source-type", "corpus",
            "--corpus", "test.enc",
            "--passphrase", "test_key"
        ])
        
        config = create_config_from_args(args)
        
        assert config.source_type == SourceType.CORPUS
        assert config.corpus_files == ["test.enc"]
        assert config.passphrase == "test_key"
    
    def test_create_config_with_output_file(self):
        """Test création de config avec fichier de sortie."""
        parser = create_cli_parser()
        args = parser.parse_args([
            "test",
            "--output-file", "results.json"
        ])
        
        config = create_config_from_args(args)
        
        assert config.output_file == Path("results.json")
    
    def test_create_config_auto_output_file(self):
        """Test génération automatique du fichier de sortie."""
        parser = create_cli_parser()
        args = parser.parse_args([
            "test",
            "--workflow-mode", "full"  # Mode qui génère auto le fichier
        ])
        
        config = create_config_from_args(args)
        
        assert config.output_file is not None
        assert "universal_analysis_" in str(config.output_file)


# Tests d'intégration
class TestIntegrationWorkflows:
    """Tests d'intégration pour les workflows complets."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_text_to_analysis_workflow(self):
        """Test workflow complet texte → analyse."""
        config = UniversalConfig(
            source_type=SourceType.TEXT,
            workflow_mode=WorkflowMode.ANALYSIS,
            analysis_modes=["unified", "fallacies"],
            require_authentic=False
        )
        
        analyzer = UniversalRhetoricalAnalyzer(config)
        result = await analyzer.analyze("Si nous autorisons cela, bientôt tout sera permis.")
        
        assert result["status"] == "completed"
        assert "analysis_results" in result["results"]
        # Devrait détecter une pente glissante
        analysis_results = result["results"]["analysis_results"]
        assert len(analysis_results) > 0
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_batch_workflow_simulation(self):
        """Test workflow batch avec fichiers simulés."""
        config = UniversalConfig(
            source_type=SourceType.BATCH,
            workflow_mode=WorkflowMode.FULL,
            require_authentic=False
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Création de plusieurs fichiers de test
            texts = [
                "Texte avec argument fallacieux ad hominem.",
                "Analyse rhétorique normale sans sophisme.",
                "Exemple de pente glissante évidente."
            ]
            
            for i, text in enumerate(texts):
                (temp_path / f"test_{i}.txt").write_text(text)
            
            analyzer = UniversalRhetoricalAnalyzer(config)
            result = await analyzer.analyze(str(temp_path))
            
            assert result["status"] == "completed"
            assert "analysis" in result["results"]
            assert "validation" in result["results"]
            
            # Vérification que les 3 fichiers ont été traités
            analysis_results = result["results"]["analysis"]["analysis_results"]
            assert len(analysis_results) == 3


# Tests de performance
class TestPerformance:
    """Tests de performance pour l'analyseur universel."""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_performance_single_text(self):
        """Test performance analyse de texte unique."""
        config = UniversalConfig(
            workflow_mode=WorkflowMode.PERFORMANCE,
            require_authentic=False
        )
        
        analyzer = UniversalRhetoricalAnalyzer(config)
        
        import time
        start_time = time.time()
        result = await analyzer.analyze("Texte de test pour performance")
        duration = time.time() - start_time
        
        assert result["status"] == "completed"
        assert duration < 5.0  # Doit être rapide en mode mock
        assert "average_duration" in result["results"]
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_performance_parallel_batch(self):
        """Test performance en mode parallèle."""
        config = UniversalConfig(
            source_type=SourceType.TEXT,
            workflow_mode=WorkflowMode.ANALYSIS,
            parallel_workers=4,
            require_authentic=False
        )
        
        analyzer = UniversalRhetoricalAnalyzer(config)
        
        # Simulation d'un batch via préparation manuelle
        prepared_data = {
            "texts": [f"Texte de test {i}" for i in range(10)],
            "source": "performance_test"
        }
        
        import time
        start_time = time.time()
        result = await analyzer._run_analysis_workflow(prepared_data)
        duration = time.time() - start_time
        
        assert len(result["analysis_results"]) == 10
        assert duration < 2.0  # Le parallélisme doit être efficace


if __name__ == "__main__":
    # Exécution des tests
    pytest.main([__file__, "-v", "--tb=short"])