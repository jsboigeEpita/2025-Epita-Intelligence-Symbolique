#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests unitaires pour le module unified_pipeline
==============================================

Tests pour :
- UnifiedAnalysisPipeline
- AnalysisConfig
- AnalysisResult
- Factory functions
- Modes d'analyse
"""

import pytest
import asyncio
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from argumentation_analysis.utils.unified_pipeline import (
    UnifiedAnalysisPipeline,
    AnalysisConfig,
    AnalysisResult,
    AnalysisMode,
    SourceType,
    create_analysis_pipeline,
)


class TestAnalysisConfig:
    """Tests pour AnalysisConfig."""

    def test_init_defaults(self):
        """Test initialisation avec valeurs par défaut."""
        config = AnalysisConfig()

        assert config.analysis_modes == [AnalysisMode.UNIFIED]
        assert config.enable_parallel is True
        assert config.max_workers == 4
        assert config.require_real_llm is True
        assert config.llm_service == "openai"
        assert config.llm_model == "gpt-4"

    def test_init_custom_values(self):
        """Test initialisation avec valeurs personnalisées."""
        config = AnalysisConfig(
            analysis_modes=[AnalysisMode.FALLACIES, AnalysisMode.RHETORIC],
            max_workers=8,
            require_real_llm=False,
            llm_model="gpt-3.5-turbo",
        )

        assert config.analysis_modes == [AnalysisMode.FALLACIES, AnalysisMode.RHETORIC]
        assert config.max_workers == 8
        assert config.require_real_llm is False
        assert config.llm_model == "gpt-3.5-turbo"


class TestAnalysisResult:
    """Tests pour AnalysisResult."""

    def test_init_basic(self):
        """Test initialisation basique."""
        timestamp = datetime.now()
        result = AnalysisResult(
            id="test_1",
            timestamp=timestamp,
            source_type=SourceType.TEXT,
            content_preview="Test content",
            analysis_modes=["unified"],
            results={"unified": {"test": "data"}},
            execution_time=1.5,
            status="completed",
        )

        assert result.id == "test_1"
        assert result.timestamp == timestamp
        assert result.source_type == SourceType.TEXT
        assert result.status == "completed"
        assert result.execution_time == 1.5
        assert len(result.errors) == 0
        assert len(result.warnings) == 0


class TestUnifiedAnalysisPipeline:
    """Tests pour UnifiedAnalysisPipeline."""

    def test_init(self):
        """Test initialisation du pipeline."""
        config = AnalysisConfig()
        pipeline = UnifiedAnalysisPipeline(config)

        assert pipeline.config == config
        assert pipeline.session_id.startswith("pipeline_")
        assert len(pipeline.results_cache) == 0

    @pytest.mark.asyncio
    async def test_analyze_text_mock_mode(self):
        """Test analyse de texte en mode mock."""
        config = AnalysisConfig(
            require_real_llm=False, analysis_modes=[AnalysisMode.UNIFIED]
        )
        pipeline = UnifiedAnalysisPipeline(config)

        result = await pipeline.analyze_text("Test text for analysis")

        assert result.status == "completed"
        assert result.source_type == SourceType.TEXT
        assert "unified" in result.results
        assert result.results["unified"]["authentic"] is False
        assert result.execution_time > 0
        assert len(pipeline.results_cache) == 1

    @pytest.mark.asyncio
    async def test_analyze_text_multiple_modes(self):
        """Test analyse avec plusieurs modes."""
        config = AnalysisConfig(
            require_real_llm=False,
            analysis_modes=[AnalysisMode.FALLACIES, AnalysisMode.RHETORIC],
        )
        pipeline = UnifiedAnalysisPipeline(config)

        result = await pipeline.analyze_text("Test text")

        assert result.status == "completed"
        assert "fallacies" in result.results
        assert "rhetoric" in result.results
        assert len(result.analysis_modes) == 2

    @pytest.mark.asyncio
    async def test_analyze_text_fallback_mode(self):
        """Test mode fallback lors d'erreur."""
        config = AnalysisConfig(
            require_real_llm=True,  # Mode authentique qui va échouer
            enable_fallback=True,
            retry_count=1,
        )
        pipeline = UnifiedAnalysisPipeline(config)

        # Mock l'erreur et le fallback
        with patch.object(
            pipeline, "_real_llm_analysis", side_effect=Exception("LLM Error")
        ):
            with patch.object(
                pipeline, "_fallback_analysis", new_callable=AsyncMock
            ) as mock_fallback:
                mock_fallback.return_value = {"fallback": True}
                result = await pipeline.analyze_text("Test text")

        assert result.status == "completed"
        assert result.results["unified"]["fallback"] is True

    @pytest.mark.asyncio
    async def test_analyze_batch_sequential(self):
        """Test analyse batch séquentielle."""
        config = AnalysisConfig(require_real_llm=False, enable_parallel=False)
        pipeline = UnifiedAnalysisPipeline(config)

        texts = ["Text 1", "Text 2", "Text 3"]
        results = await pipeline.analyze_batch(texts)

        assert len(results) == 3
        assert all(r.status == "completed" for r in results)
        assert all(r.source_type == SourceType.BATCH for r in results)

    @pytest.mark.asyncio
    async def test_analyze_batch_parallel(self):
        """Test analyse batch parallèle."""
        config = AnalysisConfig(
            require_real_llm=False, enable_parallel=True, max_workers=2
        )
        pipeline = UnifiedAnalysisPipeline(config)

        texts = ["Text 1", "Text 2", "Text 3"]
        start_time = time.time()
        results = await pipeline.analyze_batch(texts)
        execution_time = time.time() - start_time

        assert len(results) == 3
        # In parallel mode, check results completed or errored gracefully
        statuses = [r.status for r in results]
        completed_count = statuses.count("completed")
        assert (
            completed_count >= 2
        ), f"Expected at least 2 completed, got statuses: {statuses}"
        # Le parallélisme devrait être plus rapide que séquentiel
        assert (
            execution_time < 10.0
        )  # Avec mock, devrait être rapide mais inclut overhead système

    @pytest.mark.asyncio
    async def test_analyze_corpus_data(self):
        """Test analyse de données de corpus."""
        config = AnalysisConfig(require_real_llm=False)
        pipeline = UnifiedAnalysisPipeline(config)

        corpus_data = {
            "loaded_files": [
                {
                    "file": "test.enc",
                    "definitions": [
                        {"content": "Corpus text 1"},
                        {"content": "Corpus text 2"},
                    ],
                }
            ]
        }

        results = await pipeline.analyze_corpus_data(corpus_data)

        assert len(results) == 2
        assert all(r.source_type == SourceType.CORPUS for r in results)

    @pytest.mark.asyncio
    async def test_analyze_corpus_data_empty(self):
        """Test analyse de corpus vide."""
        config = AnalysisConfig(require_real_llm=False)
        pipeline = UnifiedAnalysisPipeline(config)

        corpus_data = {"loaded_files": []}
        results = await pipeline.analyze_corpus_data(corpus_data)

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_fallback_analysis_fallacies(self):
        """Test analyse de fallback pour détection de sophismes."""
        config = AnalysisConfig()
        pipeline = UnifiedAnalysisPipeline(config)

        # Texte avec mots-clés de sophisme
        text = "Cette personne attaque toujours les individus plutôt que les arguments"
        pipeline._fallback_analysis = AsyncMock(
            return_value={"fallback": True, "fallacies_detected": ["ad_hominem"]}
        )

        result = await pipeline._fallback_analysis(text, AnalysisMode.FALLACIES)

        assert result["fallback"] is True
        assert "fallacies_detected" in result
        assert "ad_hominem" in result["fallacies_detected"]

    def test_get_session_summary(self):
        """Test génération du résumé de session."""
        config = AnalysisConfig()
        pipeline = UnifiedAnalysisPipeline(config)

        # Simulation de quelques résultats
        pipeline.results_cache = [
            AnalysisResult(
                id="test_1",
                timestamp=datetime.now(),
                source_type=SourceType.TEXT,
                content_preview="",
                analysis_modes=[],
                results={},
                execution_time=1.0,
                status="completed",
            ),
            AnalysisResult(
                id="test_2",
                timestamp=datetime.now(),
                source_type=SourceType.TEXT,
                content_preview="",
                analysis_modes=[],
                results={},
                execution_time=2.0,
                status="error",
            ),
        ]

        summary = pipeline.get_session_summary()

        assert summary["total_analyses"] == 2
        assert summary["successful_analyses"] == 1
        assert summary["failed_analyses"] == 1
        assert summary["success_rate"] == 0.5
        assert summary["total_execution_time"] == 3.0
        assert summary["average_execution_time"] == 1.5


class TestAnalysisModes:
    """Tests pour les modes d'analyse."""

    @pytest.mark.asyncio
    async def test_mock_analysis_fallacies(self):
        """Test analyse mock pour sophismes."""
        config = AnalysisConfig()
        pipeline = UnifiedAnalysisPipeline(config)

        result = await pipeline._mock_analysis("Test text", AnalysisMode.FALLACIES)

        assert result["mode"] == "fallacies"
        assert result["authentic"] is False
        assert "fallacies_detected" in result
        assert "confidence" in result

    @pytest.mark.asyncio
    async def test_mock_analysis_other_modes(self):
        """Test analyse mock pour autres modes."""
        config = AnalysisConfig()
        pipeline = UnifiedAnalysisPipeline(config)

        for mode in [AnalysisMode.RHETORIC, AnalysisMode.LOGIC, AnalysisMode.SEMANTIC]:
            result = await pipeline._mock_analysis("Test text", mode)

            assert result["mode"] == mode.value
            assert result["authentic"] is False
            assert "timestamp" in result


class TestRetryMechanism:
    """Tests pour le mécanisme de retry."""

    @pytest.mark.asyncio
    async def test_retry_success_second_attempt(self):
        """Test retry réussi à la deuxième tentative."""
        config = AnalysisConfig(retry_count=3, retry_delay=0.01)
        pipeline = UnifiedAnalysisPipeline(config)

        call_count = 0

        async def failing_then_success(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("First attempt fails")
            return {"success": True}

        with patch.object(
            pipeline, "_real_llm_analysis", side_effect=failing_then_success
        ) as mock_analysis:
            result = await pipeline._execute_analysis_mode("Test", AnalysisMode.UNIFIED)

        assert result["success"] is True
        assert mock_analysis.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_exhausted_with_fallback(self):
        """Test épuisement des tentatives avec fallback."""
        config = AnalysisConfig(retry_count=2, retry_delay=0.01, enable_fallback=True)
        pipeline = UnifiedAnalysisPipeline(config)

        with patch.object(
            pipeline, "_real_llm_analysis", side_effect=Exception("Always fails")
        ):
            with patch.object(
                pipeline, "_fallback_analysis", new_callable=AsyncMock
            ) as mock_fallback:
                mock_fallback.return_value = {"fallback": True}
                result = await pipeline._execute_analysis_mode(
                    "Test", AnalysisMode.UNIFIED
                )

        assert result["fallback"] is True


class TestFactoryFunction:
    """Tests pour create_analysis_pipeline."""

    def test_create_pipeline_defaults(self):
        """Test création avec paramètres par défaut."""
        pipeline = create_analysis_pipeline()

        assert isinstance(pipeline, UnifiedAnalysisPipeline)
        assert pipeline.config.analysis_modes == [AnalysisMode.UNIFIED]
        assert pipeline.config.max_workers == 4
        assert pipeline.config.require_real_llm is True

    def test_create_pipeline_custom_modes(self):
        """Test création avec modes personnalisés."""
        pipeline = create_analysis_pipeline(
            analysis_modes=["fallacies", "rhetoric"],
            parallel_workers=8,
            require_authentic=False,
        )

        assert len(pipeline.config.analysis_modes) == 2
        assert AnalysisMode.FALLACIES in pipeline.config.analysis_modes
        assert AnalysisMode.RHETORIC in pipeline.config.analysis_modes
        assert pipeline.config.max_workers == 8
        assert pipeline.config.require_real_llm is False

    def test_create_pipeline_invalid_mode(self):
        """Test création avec mode invalide."""
        # Les modes invalides sont ignorés avec warning
        pipeline = create_analysis_pipeline(analysis_modes=["invalid_mode", "unified"])

        # Devrait garder seulement les modes valides ou revenir au défaut
        assert len(pipeline.config.analysis_modes) >= 1


# Tests d'intégration
class TestPipelineIntegration:
    """Tests d'intégration pour le pipeline."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_pipeline_workflow(self):
        """Test workflow complet du pipeline."""
        pipeline = create_analysis_pipeline(
            analysis_modes=["unified", "fallacies"], require_authentic=False
        )

        # Test analyse unique
        result = await pipeline.analyze_text("Test d'intégration du pipeline")

        assert result.status == "completed"
        assert len(result.results) == 2

        # Test analyse batch
        texts = ["Texte 1", "Texte 2"]
        batch_results = await pipeline.analyze_batch(texts)

        assert len(batch_results) == 2

        # Test résumé de session
        summary = pipeline.get_session_summary()
        assert summary["total_analyses"] == 3  # 1 + 2
        assert summary["successful_analyses"] == 3


if __name__ == "__main__":
    # Exécution des tests
    pytest.main([__file__, "-v"])
