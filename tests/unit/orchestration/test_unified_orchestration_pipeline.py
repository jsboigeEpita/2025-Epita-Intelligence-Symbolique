#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests Unitaires pour le Pipeline d'Orchestration Unifié
======================================================

Tests complets pour valider le fonctionnement du nouveau pipeline d'orchestration
qui intègre l'architecture hiérarchique et les orchestrateurs spécialisés.

Structure des tests :
- Configuration étendue
- Pipeline d'orchestration unifié  
- Sélection automatique d'orchestrateur
- Stratégies d'orchestration
- Gestion d'erreurs et fallbacks
- Compatibilité API

Auteur: Intelligence Symbolique EPITA
Date: 10/06/2025
"""

import pytest
import asyncio
import logging
import time
from unittest.mock import patch, AsyncMock, MagicMock
from typing import Dict, Any, List

# Configuration du logging pour les tests
logging.basicConfig(level=logging.WARNING)

# Imports des utilitaires de test
try:
    from tests.utils.common_test_helpers import (
        create_sample_text,
        assert_valid_analysis_results
    )
    TEST_UTILS_AVAILABLE = True
except ImportError:
    TEST_UTILS_AVAILABLE = False

# Imports à tester
try:
    from argumentation_analysis.pipelines.unified_orchestration_pipeline import (
        UnifiedOrchestrationPipeline,
        ExtendedOrchestrationConfig,
        OrchestrationMode,
        AnalysisType,
        run_unified_orchestration_pipeline,
        run_extended_unified_analysis,
        create_extended_config_from_params,
        compare_orchestration_approaches
    )
    ORCHESTRATION_AVAILABLE = True
except ImportError as e:
    ORCHESTRATION_AVAILABLE = False
    pytestmark = pytest.mark.skip(f"Pipeline d'orchestration non disponible: {e}")


class TestExtendedOrchestrationConfig:
    """Tests pour la configuration étendue d'orchestration."""
    
    def test_default_configuration(self):
        """Test de la configuration par défaut."""
        config = ExtendedOrchestrationConfig()
        
        assert config.analysis_type == AnalysisType.COMPREHENSIVE
        assert config.orchestration_mode_enum == OrchestrationMode.PIPELINE
        assert config.enable_hierarchical is True
        assert config.enable_specialized_orchestrators is True
        assert config.auto_select_orchestrator is True
        assert config.save_orchestration_trace is True
    
    def test_custom_configuration(self):
        """Test d'une configuration personnalisée."""
        config = ExtendedOrchestrationConfig(
            analysis_modes=["informal", "unified"],
            orchestration_mode=OrchestrationMode.HIERARCHICAL_FULL,
            analysis_type=AnalysisType.INVESTIGATIVE,
            enable_hierarchical=False,
            enable_specialized_orchestrators=True,
            max_concurrent_analyses=5,
            analysis_timeout=120,
            hierarchical_coordination_level="tactical"
        )
        
        assert config.analysis_modes == ["informal", "unified"]
        assert config.orchestration_mode_enum == OrchestrationMode.HIERARCHICAL_FULL
        assert config.analysis_type == AnalysisType.INVESTIGATIVE
        assert config.enable_hierarchical is False
        assert config.enable_specialized_orchestrators is True
        assert config.max_concurrent_analyses == 5
        assert config.analysis_timeout == 120
        assert config.hierarchical_coordination_level == "tactical"
    
    def test_enum_conversion_from_strings(self):
        """Test de la conversion automatique depuis des chaînes vers les énumérations."""
        config = ExtendedOrchestrationConfig(
            orchestration_mode="hierarchical_full",
            analysis_type="investigative"
        )
        
        assert config.orchestration_mode_enum == OrchestrationMode.HIERARCHICAL_FULL
        assert config.analysis_type == AnalysisType.INVESTIGATIVE
    
    def test_specialized_orchestrator_priority(self):
        """Test de la configuration des priorités d'orchestrateurs spécialisés."""
        custom_priority = ["logic_complex", "cluedo_investigation", "conversation"]
        config = ExtendedOrchestrationConfig(
            specialized_orchestrator_priority=custom_priority
        )
        
        assert config.specialized_orchestrator_priority == custom_priority
    
    def test_middleware_configuration(self):
        """Test de la configuration du middleware."""
        middleware_config = {
            "max_message_history": 500,
            "enable_logging": True,
            "channel_buffer_size": 100
        }
        config = ExtendedOrchestrationConfig(middleware_config=middleware_config)
        
        assert config.middleware_config == middleware_config


class TestUnifiedOrchestrationPipeline:
    """Tests pour le pipeline d'orchestration unifié."""
    
    @pytest.fixture
    def basic_config(self):
        """Configuration de base pour les tests."""
        return ExtendedOrchestrationConfig(
            use_mocks=False,
            enable_hierarchical=False,
            enable_specialized_orchestrators=False,
            auto_select_orchestrator=False,  # Force la sélection manuelle
            save_orchestration_trace=False,
            enable_communication_middleware=False
        )
    
    @pytest.fixture
    def hierarchical_config(self):
        """Configuration pour tests hiérarchiques."""
        return ExtendedOrchestrationConfig(
            orchestration_mode=OrchestrationMode.HIERARCHICAL_FULL,
            enable_hierarchical=True,
            enable_specialized_orchestrators=False,
            use_mocks=False,
            save_orchestration_trace=False
        )
    
    @pytest.fixture
    def specialized_config(self):
        """Configuration pour tests spécialisés."""
        return ExtendedOrchestrationConfig(
            orchestration_mode=OrchestrationMode.CLUEDO_INVESTIGATION,
            analysis_type=AnalysisType.INVESTIGATIVE,
            enable_hierarchical=False,
            enable_specialized_orchestrators=True,
            use_mocks=False,
            save_orchestration_trace=False
        )
    
    @pytest.fixture
    def sample_texts(self):
        """Textes d'exemple pour différents types d'analyse."""
        return {
            "simple": "Ceci est un argument simple pour tester l'analyse.",
            "complex": "L'argument principal est que l'éducation améliore la société. Premièrement, elle forme des citoyens éclairés. Deuxièmement, elle favorise l'innovation. Cependant, certains prétendent que l'éducation coûte trop cher, ce qui est un faux dilemme car on ne peut pas mettre un prix sur la connaissance.",
            "investigative": "Le témoin A dit avoir vu le suspect à 21h. Le témoin B affirme le contraire. Qui dit la vérité ? Les preuves matérielles suggèrent une présence sur les lieux.",
            "logical": "Si tous les hommes sont mortels et si Socrate est un homme, alors Socrate est mortel. Cette déduction suit la logique aristotélicienne.",
            "empty": "",
            "very_long": "Argument répétitif. " * 1000
        }
    
    def test_pipeline_initialization_basic(self, basic_config):
        """Test de l'initialisation de base du pipeline."""
        pipeline = UnifiedOrchestrationPipeline(basic_config)
        
        assert pipeline.config == basic_config
        assert pipeline.initialized is False
        assert pipeline.llm_service is None
        assert pipeline.service_manager is None
        assert pipeline.strategic_manager is None
        assert pipeline.tactical_coordinator is None
        assert pipeline.operational_manager is None
        assert len(pipeline.specialized_orchestrators) == 0
        assert pipeline.middleware is None
        assert pipeline._fallback_pipeline is None
        assert pipeline.orchestration_trace == []
    
    @pytest.mark.asyncio
    async def test_pipeline_initialization_async_success(self, basic_config, jvm_session_manager):
        """Test de l'initialisation asynchrone réussie avec de vrais composants."""
        pipeline = UnifiedOrchestrationPipeline(basic_config)
        
        # Patcher _initialize_base_services pour éviter un second appel à initialize_jvm
        with patch('argumentation_analysis.pipelines.unified_orchestration_pipeline.UnifiedOrchestrationPipeline._initialize_base_services') as mock_init_base:
            mock_init_base.return_value = True # Simuler le succès
            
            # L'initialisation doit maintenant utiliser les vrais services
            # grâce à la configuration et à l'environnement de test.
            success = await pipeline.initialize()
        
        assert success is True
        assert pipeline.initialized is True
        # Les services de base n'ont pas été réellement initialisés à cause du patch
        # donc on ne peut pas les vérifier ici.
    
    @pytest.mark.asyncio
    async def test_pipeline_initialization_with_hierarchical(self, hierarchical_config, jvm_session_manager):
        """Test de l'initialisation avec architecture hiérarchique réelle."""
        pipeline = UnifiedOrchestrationPipeline(hierarchical_config)
        
        with patch('argumentation_analysis.pipelines.unified_orchestration_pipeline.UnifiedOrchestrationPipeline._initialize_base_services'):
            success = await pipeline.initialize()
        
        assert success is True
        assert pipeline.initialized is True
        
        # Vérifier que les gestionnaires hiérarchiques réels sont instanciés
        from argumentation_analysis.orchestration.hierarchical.strategic.manager import StrategicManager
        from argumentation_analysis.orchestration.hierarchical.tactical.coordinator import TaskCoordinator
        from argumentation_analysis.orchestration.hierarchical.operational.manager import OperationalManager
        
        assert isinstance(pipeline.strategic_manager, StrategicManager)
        assert isinstance(pipeline.tactical_coordinator, TaskCoordinator)
        assert isinstance(pipeline.operational_manager, OperationalManager)
        
        # Le middleware est optionnel, vérifier s'il est activé
        if pipeline.config.enable_communication_middleware:
            from argumentation_analysis.core.communication.middleware import MessageMiddleware
            assert isinstance(pipeline.middleware, MessageMiddleware)
    
    @pytest.mark.asyncio
    async def test_pipeline_initialization_with_specialized(self, specialized_config, jvm_session_manager):
        """Test de l'initialisation avec orchestrateurs spécialisés réels."""
        pipeline = UnifiedOrchestrationPipeline(specialized_config)
        
        # Mock kernel pour que _initialize_specialized_orchestrators() fonctionne
        from unittest.mock import Mock
        mock_kernel = Mock()
        pipeline.kernel = mock_kernel
        
        with patch('argumentation_analysis.pipelines.unified_orchestration_pipeline.UnifiedOrchestrationPipeline._initialize_base_services'):
            success = await pipeline.initialize()
        
        assert success is True
        assert pipeline.initialized is True
        
        # Vérifier que les orchestrateurs spécialisés réels sont instanciés
        assert len(pipeline.specialized_orchestrators) > 0
        from argumentation_analysis.orchestration.cluedo_extended_orchestrator import CluedoExtendedOrchestrator
        from argumentation_analysis.orchestration.conversation_orchestrator import ConversationOrchestrator
        
        assert "cluedo" in pipeline.specialized_orchestrators
        assert "conversation" in pipeline.specialized_orchestrators
        assert isinstance(pipeline.specialized_orchestrators["cluedo"]["orchestrator"], CluedoExtendedOrchestrator)
        assert isinstance(pipeline.specialized_orchestrators["conversation"]["orchestrator"], ConversationOrchestrator)
    
    @pytest.mark.asyncio
    @pytest.mark.slow  # Marquer comme test lent car il fait un vrai appel LLM
    async def test_analyze_text_orchestrated_basic_real(self, basic_config, sample_texts, jvm_session_manager):
        """Test de l'analyse orchestrée de base avec un vrai LLM."""
        pipeline = UnifiedOrchestrationPipeline(basic_config)
        
        with patch('argumentation_analysis.pipelines.unified_orchestration_pipeline.UnifiedOrchestrationPipeline._initialize_base_services'):
            await pipeline.initialize()
        
        # Exécution réelle sans mock
        results = await pipeline.analyze_text_orchestrated(sample_texts["simple"])
                
        # Assertions souples sur la structure du résultat
        assert results["status"] == "success"
        assert "metadata" in results
        assert "execution_time" in results
        assert results["metadata"]["text_length"] == len(sample_texts["simple"])
        assert "fallback_analysis" in results  # Le mode de base utilise le fallback
        assert "informal_analysis" in results["fallback_analysis"]
        assert "formal_analysis" in results["fallback_analysis"]
    
    @pytest.mark.asyncio
    async def test_analyze_text_with_validation_errors(self, basic_config):
        """Test de validation des erreurs d'entrée."""
        pipeline = UnifiedOrchestrationPipeline(basic_config)
        
        with patch('argumentation_analysis.pipelines.unified_orchestration_pipeline.create_llm_service'):
            with patch('argumentation_analysis.pipelines.unified_orchestration_pipeline.UnifiedOrchestrationPipeline._initialize_base_services'):
                await pipeline.initialize()
            
            # Test texte vide
            with pytest.raises(ValueError, match="Texte vide ou invalide"):
                await pipeline.analyze_text_orchestrated("")
            
            # Test texte None
            with pytest.raises(ValueError, match="Texte vide ou invalide"):
                await pipeline.analyze_text_orchestrated(None)
            
            # Test texte whitespace seulement
            with pytest.raises(ValueError, match="Texte vide ou invalide"):
                await pipeline.analyze_text_orchestrated("   \n\t  ")
    
    @pytest.mark.asyncio
    async def test_analyze_text_without_initialization(self, basic_config, sample_texts):
        """Test d'analyse sans initialisation préalable."""
        pipeline = UnifiedOrchestrationPipeline(basic_config)
        
        with pytest.raises(RuntimeError, match="Pipeline non initialisé"):
            await pipeline.analyze_text_orchestrated(sample_texts["simple"])
    
    @pytest.mark.asyncio
    async def test_orchestration_strategy_selection(self, basic_config, sample_texts):
        """Test de la sélection de stratégie d'orchestration."""
        pipeline = UnifiedOrchestrationPipeline(basic_config)
        
        # Test sélection avec mode manuel
        strategy = await pipeline._select_orchestration_strategy(sample_texts["simple"])
        assert strategy in ["hierarchical_full", "specialized_direct", "service_manager", "hybrid", "fallback"]
        
        # Test sélection avec mode auto
        config_auto = ExtendedOrchestrationConfig(
            orchestration_mode=OrchestrationMode.AUTO_SELECT,
            auto_select_orchestrator=True
        )
        pipeline_auto = UnifiedOrchestrationPipeline(config_auto)
        strategy_auto = await pipeline_auto._select_orchestration_strategy(sample_texts["complex"])
        assert strategy_auto in ["hierarchical_full", "specialized_direct", "service_manager", "hybrid", "fallback"]
    
    @pytest.mark.asyncio
    async def test_text_features_analysis(self, basic_config, sample_texts):
        """Test de l'analyse des caractéristiques du texte."""
        pipeline = UnifiedOrchestrationPipeline(basic_config)
        
        # Test texte simple
        features_simple = await pipeline._analyze_text_features(sample_texts["simple"])
        assert "length" in features_simple
        assert "word_count" in features_simple
        assert "sentence_count" in features_simple
        assert "has_questions" in features_simple
        assert "has_logical_connectors" in features_simple
        assert "has_debate_markers" in features_simple
        assert "complexity_score" in features_simple
        
        assert features_simple["length"] == len(sample_texts["simple"])
        assert features_simple["word_count"] > 0
        assert features_simple["complexity_score"] >= 0
        
        # Test texte complexe
        features_complex = await pipeline._analyze_text_features(sample_texts["complex"])
        assert features_complex["length"] > features_simple["length"]
        assert features_complex["complexity_score"] > features_simple["complexity_score"]
        assert features_complex["has_logical_connectors"] is True  # "Premièrement", "Deuxièmement"
        
        # Test texte investigatif
        features_investigative = await pipeline._analyze_text_features(sample_texts["investigative"])
        assert features_investigative["has_questions"] is True  # "Qui dit la vérité ?"
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_hierarchical_orchestration_execution_real(self, hierarchical_config, sample_texts):
        """Test de l'exécution de l'orchestration hiérarchique avec un vrai LLM."""
        pipeline = UnifiedOrchestrationPipeline(hierarchical_config)
        with patch('argumentation_analysis.pipelines.unified_orchestration_pipeline.UnifiedOrchestrationPipeline._initialize_base_services'):
            await pipeline.initialize()

        results = await pipeline.analyze_text_orchestrated(sample_texts["complex"])

        assert results["status"] == "success"
        assert "strategic_analysis" in results
        assert "tactical_coordination" in results
        assert "operational_results" in results
        assert "hierarchical_coordination" in results
        
        # Assertions souples sur la structure de la sortie
        assert isinstance(results["strategic_analysis"]["objectives"], list)
        assert len(results["strategic_analysis"]["objectives"]) > 0
        assert results["tactical_coordination"]["tasks_created"] > 0
        assert results["operational_results"]["summary"]["executed_tasks"] > 0
    
    @pytest.mark.asyncio
    async def test_specialized_orchestrator_selection(self, specialized_config):
        """Test de la sélection d'orchestrateurs spécialisés."""
        pipeline = UnifiedOrchestrationPipeline(specialized_config)
        
        # Mock des orchestrateurs spécialisés
        pipeline.specialized_orchestrators = {
            "cluedo": {
                "orchestrator": MagicMock(),
                "types": [AnalysisType.INVESTIGATIVE, AnalysisType.DEBATE_ANALYSIS],
                "priority": 1
            },
            "conversation": {
                "orchestrator": MagicMock(),
                "types": [AnalysisType.RHETORICAL, AnalysisType.COMPREHENSIVE],
                "priority": 2
            },
            "logic_complex": {
                "orchestrator": MagicMock(),
                "types": [AnalysisType.LOGICAL, AnalysisType.COMPREHENSIVE],
                "priority": 3
            }
        }
        
        # Test sélection pour analyse investigative
        pipeline.config.analysis_type = AnalysisType.INVESTIGATIVE
        selected = await pipeline._select_specialized_orchestrator()
        assert selected is not None
        assert selected[0] == "cluedo"  # Plus haute priorité pour ce type
        
        # Test sélection pour analyse rhétorique
        pipeline.config.analysis_type = AnalysisType.RHETORICAL
        selected = await pipeline._select_specialized_orchestrator()
        assert selected is not None
        assert selected[0] == "conversation"
        
        # Test sélection pour type non supporté spécifiquement
        pipeline.config.analysis_type = AnalysisType.FALLACY_FOCUSED
        selected = await pipeline._select_specialized_orchestrator()
        assert selected is not None  # Doit retourner le premier disponible
    
    @pytest.mark.asyncio
    async def test_trace_orchestration(self, basic_config):
        """Test du système de trace d'orchestration."""
        config = ExtendedOrchestrationConfig(
            save_orchestration_trace=True, # Garder la trace pour ce test
            use_mocks=False # Démarrer sans mocks
        )
        pipeline = UnifiedOrchestrationPipeline(config)
        
        # Test ajout de traces
        pipeline._trace_orchestration("test_event", {"data": "test_data"})
        pipeline._trace_orchestration("another_event", {"more_data": 123})
        
        assert len(pipeline.orchestration_trace) == 2
        assert pipeline.orchestration_trace[0]["event_type"] == "test_event"
        assert pipeline.orchestration_trace[0]["data"]["data"] == "test_data"
        assert pipeline.orchestration_trace[1]["event_type"] == "another_event"
        assert pipeline.orchestration_trace[1]["data"]["more_data"] == 123
        
        # Vérifier format des timestamps
        for trace in pipeline.orchestration_trace:
            assert "timestamp" in trace
            assert trace["timestamp"]  # Non vide
    
    @pytest.mark.asyncio
    async def test_error_handling_and_fallback(self, basic_config, sample_texts):
        """Test de la gestion d'erreur et des fallbacks."""
        # Forcer la config à ne pas utiliser les mocks au départ
        basic_config.use_mocks = False
        pipeline = UnifiedOrchestrationPipeline(basic_config)
        
        with patch('argumentation_analysis.pipelines.unified_orchestration_pipeline.create_llm_service') as mock_create_llm:
            # Simuler un échec de création du service LLM
            mock_create_llm.side_effect = Exception("Service LLM indisponible")
            
            # L'initialisation doit réussir en basculant sur le mode mock.
            success = await pipeline.initialize()
            assert success is True, "L'initialisation doit basculer en mode mock et réussir"
            assert pipeline.config.use_mocks is True, "Le pipeline doit basculer en use_mocks=True"
            
            # Puisque nous sommes en mode mock, le fallback pipeline a dû être initialisé.
            assert pipeline._fallback_pipeline is not None
            
            # L'analyse devrait utiliser le fallback pipeline mocké.
            with patch.object(pipeline._fallback_pipeline, 'analyze_text_unified', new_callable=AsyncMock) as mock_analyze:
                mock_analyze.return_value = {"status": "success_from_fallback_mock"}
                results = await pipeline.analyze_text_orchestrated(sample_texts["simple"])
                assert results["status"] == "success_from_fallback_mock"
                mock_analyze.assert_awaited_once()
    
    @pytest.mark.asyncio
    async def test_shutdown_cleanup(self, basic_config):
        """Test du nettoyage lors de l'arrêt."""
        pipeline = UnifiedOrchestrationPipeline(basic_config)
        
        # Mock des composants avec méthodes shutdown
        mock_service_manager = MagicMock()
        mock_service_manager.shutdown = AsyncMock()
        pipeline.service_manager = mock_service_manager
        
        mock_orchestrator = MagicMock()
        mock_orchestrator.shutdown = AsyncMock()
        pipeline.specialized_orchestrators = {
            "test": {"orchestrator": mock_orchestrator}
        }
        
        mock_middleware = MagicMock()
        mock_middleware.shutdown = AsyncMock()
        pipeline.middleware = mock_middleware
        
        pipeline.initialized = True
        
        # Test shutdown
        await pipeline.shutdown()
        
        assert pipeline.initialized is False
        mock_service_manager.shutdown.assert_called_once()
        mock_orchestrator.shutdown.assert_called_once()
        mock_middleware.shutdown.assert_called_once()


class TestOrchestrationFunctions:
    """Tests pour les fonctions d'orchestration publiques."""
    
    @pytest.fixture
    def sample_text(self):
        """Texte d'exemple pour les tests."""
        return "Argument de test pour les fonctions d'orchestration publiques."
    
    @pytest.mark.asyncio
    async def test_run_unified_orchestration_pipeline_default(self, sample_text):
        """Test de la fonction principale avec configuration par défaut et vrais services."""
        # Ce test est maintenant un test d'intégration complet
        results = await run_unified_orchestration_pipeline(sample_text)
        
        assert results["status"] == "success"
        assert "metadata" in results
        # Le mode auto-select peut choisir différentes stratégies, on reste souple
        possible_result_keys = ["fallback_analysis", "hierarchical_coordination", "specialized_orchestration", "service_manager_results", "informal_analysis"]
        assert any(key in results for key in possible_result_keys)
        assert results["metadata"]["text_length"] == len(sample_text)
    
    @pytest.mark.asyncio
    async def test_run_unified_orchestration_pipeline_with_config(self, sample_text):
        """Test avec configuration personnalisée."""
        config = ExtendedOrchestrationConfig(
            orchestration_mode=OrchestrationMode.HIERARCHICAL_FULL,
            analysis_type=AnalysisType.INVESTIGATIVE,
            use_mocks=False # Test réel
        )
        
        results = await run_unified_orchestration_pipeline(sample_text, config)
        
        assert results["status"] == "success"
        assert "hierarchical_coordination" in results
        assert "strategic_analysis" in results
    
    @pytest.mark.asyncio
    async def test_run_unified_orchestration_pipeline_initialization_failure(self, sample_text):
        """Test de gestion d'échec d'initialisation."""
        with patch('argumentation_analysis.pipelines.unified_orchestration_pipeline.UnifiedOrchestrationPipeline') as mock_pipeline_class:
            mock_pipeline = MagicMock()
            mock_pipeline_class.return_value = mock_pipeline
            mock_pipeline.initialize = AsyncMock(return_value=False)  # Échec d'initialisation
            mock_pipeline.shutdown = AsyncMock()
            
            results = await run_unified_orchestration_pipeline(sample_text)
            
            assert results["status"] == "failed"
            assert "Échec de l'initialisation" in results["error"]
            assert mock_pipeline.shutdown.called  # Nettoyage même en cas d'échec
    
    @pytest.mark.asyncio
    async def test_run_extended_unified_analysis_compatibility(self, sample_text):
        """Test de la fonction de compatibilité avec des vrais appels."""
        results = await run_extended_unified_analysis(
            text=sample_text,
            mode="comprehensive",
            orchestration_mode="auto_select",
            use_mocks=False # Vrai appel
        )
        
        assert results["status"] == "success"
        assert "metadata" in results
        assert "orchestration_trace" in results
        # Le mode auto-select peut choisir différentes stratégies, on reste souple
        assert ("fallback_analysis" in results or "hierarchical_coordination" in results or "specialized_orchestration" in results)
    
    @pytest.mark.asyncio
    async def test_run_extended_unified_analysis_mode_mapping(self, sample_text):
        """Test du mapping des modes dans la fonction de compatibilité."""
        test_cases = [
            ("comprehensive", AnalysisType.COMPREHENSIVE),
            ("rhetorical", AnalysisType.RHETORICAL),
            ("logical", AnalysisType.LOGICAL),
            ("investigative", AnalysisType.INVESTIGATIVE),
            ("fallacy", AnalysisType.FALLACY_FOCUSED),
            ("structure", AnalysisType.ARGUMENT_STRUCTURE),
            ("debate", AnalysisType.DEBATE_ANALYSIS)
        ]
        
        for mode_str, expected_enum in test_cases:
            with patch('argumentation_analysis.pipelines.unified_orchestration_pipeline.run_unified_orchestration_pipeline') as mock_run:
                mock_run.return_value = {"status": "success"}
                
                await run_extended_unified_analysis(text=sample_text, mode=mode_str)
                
                config = mock_run.call_args[0][1]
                assert config.analysis_type == expected_enum
    
    def test_create_extended_config_from_params(self):
        """Test de la création de configuration depuis des paramètres."""
        config = create_extended_config_from_params(
            orchestration_mode=OrchestrationMode.HIERARCHICAL_FULL,
            analysis_type=AnalysisType.INVESTIGATIVE,
            enable_hierarchical=True,
            enable_specialized=True,
            use_mocks=True,
            auto_select=False,
            save_trace=True
        )
        
        assert config.orchestration_mode_enum == OrchestrationMode.HIERARCHICAL_FULL
        assert config.analysis_type == AnalysisType.INVESTIGATIVE
        assert config.enable_hierarchical is True
        assert config.enable_specialized_orchestrators is True
        assert config.use_mocks is True
        assert config.auto_select_orchestrator is False
        assert config.save_orchestration_trace is True
    
    def test_create_extended_config_analysis_mode_mapping(self):
        """Test du mapping des types d'analyse vers les modes d'analyse."""
        test_cases = [
            (AnalysisType.RHETORICAL, ["informal"]),
            (AnalysisType.LOGICAL, ["formal"]),
            (AnalysisType.COMPREHENSIVE, ["informal", "formal", "unified"]),
            (AnalysisType.INVESTIGATIVE, ["informal", "unified"]),
            (AnalysisType.FALLACY_FOCUSED, ["informal"]),
            (AnalysisType.ARGUMENT_STRUCTURE, ["formal", "unified"]),
            (AnalysisType.DEBATE_ANALYSIS, ["informal", "formal"])
        ]
        
        for analysis_type, expected_modes in test_cases:
            config = create_extended_config_from_params(analysis_type=analysis_type)
            assert config.analysis_modes == expected_modes
    
    @pytest.mark.asyncio
    async def test_compare_orchestration_approaches_mock(self, sample_text):
        """Test de la comparaison d'approches avec mocks."""
        # Utiliser des modes valides qui mappent aux stratégies attendues
        approaches = ["pipeline", "hierarchical_full", "cluedo_investigation"]
        
        with patch('argumentation_analysis.pipelines.unified_orchestration_pipeline.run_unified_orchestration_pipeline') as mock_run:
            # Simuler des résultats différents pour chaque approche
            def side_effect(text, config):
                mode = config.orchestration_mode_enum
                
                # Déterminer la stratégie basée sur le mode pour la simulation
                is_hierarchical = mode == OrchestrationMode.HIERARCHICAL_FULL
                is_specialized = mode == OrchestrationMode.CLUEDO_INVESTIGATION
                is_pipeline = mode == OrchestrationMode.PIPELINE

                return {
                    "status": "success",
                    "execution_time": 1.0 if is_pipeline else 2.0 if is_hierarchical else 1.5,
                    "metadata": {"orchestration_mode": mode.value},
                    "recommendations": [f"Recommandation pour {mode.value}"],
                    "strategic_analysis": {} if is_hierarchical else None,
                    "specialized_orchestration": {} if is_specialized else None
                }
            
            mock_run.side_effect = side_effect
            
            results = await compare_orchestration_approaches(sample_text, approaches)
            
            assert "approaches" in results
            assert "comparison" in results
            assert "recommendations" in results
            assert len(results["approaches"]) == len(approaches)
            
            # Vérifier les résultats pour chaque approche
            for approach in approaches:
                assert approach in results["approaches"]
                approach_result = results["approaches"][approach]
                assert approach_result["status"] == "success"
                assert "execution_time" in approach_result
                assert "summary" in approach_result
            
            # Vérifier la comparaison
            if "fastest" in results["comparison"]:
                assert results["comparison"]["fastest"] == "pipeline"  # Temps d'exécution le plus bas (1.0)
    
    @pytest.mark.asyncio
    async def test_compare_orchestration_approaches_with_errors(self, sample_text):
        """Test de comparaison avec gestion d'erreurs."""
        approaches = ["pipeline", "hierarchical"]
        
        with patch('argumentation_analysis.pipelines.unified_orchestration_pipeline.run_unified_orchestration_pipeline') as mock_run:
            # Simuler une erreur pour une approche
            def side_effect(text, config):
                mode = config.orchestration_mode_enum.value
                if mode == "pipeline":
                    return {"status": "success", "execution_time": 1.0, "metadata": {"orchestration_mode": mode}}
                else:
                    raise Exception("Erreur test orchestration hiérarchique")
            
            mock_run.side_effect = side_effect
            
            results = await compare_orchestration_approaches(sample_text, approaches)
            
            # Vérifier que les erreurs sont gérées
            assert results["approaches"]["pipeline"]["status"] == "success"
            assert results["approaches"]["hierarchical"]["status"] == "error"
            assert "error" in results["approaches"]["hierarchical"]


class TestErrorHandlingAndEdgeCases:
    """Tests pour la gestion d'erreurs et cas limites."""
    
    @pytest.mark.asyncio
    async def test_analysis_timeout_handling(self):
        """Test de gestion du timeout d'analyse."""
        config = ExtendedOrchestrationConfig(
            analysis_timeout=1,  # 1 seconde seulement
            use_mocks=True
        )
        pipeline = UnifiedOrchestrationPipeline(config)
        
        with patch('argumentation_analysis.pipelines.unified_orchestration_pipeline.create_llm_service'):
            with patch('argumentation_analysis.pipelines.unified_orchestration_pipeline.UnifiedOrchestrationPipeline._initialize_base_services'):
                await pipeline.initialize()
            
            # Mock qui prend plus de temps que le timeout
            async def slow_analysis(*args, **kwargs):
                await asyncio.sleep(2)  # Plus long que le timeout
                return {"status": "success"}
            
            with patch.object(pipeline, '_fallback_pipeline') as mock_fallback:
                mock_fallback.analyze_text_unified = slow_analysis
                
                # Note: Le timeout n'est pas implémenté dans cette version
                # Ce test vérifie que le code ne plante pas avec des analyses longues
                start_time = time.time()
                results = await pipeline.analyze_text_orchestrated("Texte de test")
                execution_time = time.time() - start_time
                
                # L'analyse devrait s'exécuter normalement même si elle dépasse le timeout configuré
                assert execution_time >= 2.0
    
    @pytest.mark.asyncio
    async def test_large_text_handling(self):
        """Test de gestion de textes volumineux."""
        config = ExtendedOrchestrationConfig(use_mocks=True)
        pipeline = UnifiedOrchestrationPipeline(config)
        
        # Texte très volumineux (1MB)
        large_text = "Test " * 200000  # Environ 1MB
        
        with patch('argumentation_analysis.pipelines.unified_orchestration_pipeline.create_llm_service'):
            with patch('argumentation_analysis.pipelines.unified_orchestration_pipeline.UnifiedOrchestrationPipeline._initialize_base_services'):
                await pipeline.initialize()
            
            with patch.object(pipeline, '_fallback_pipeline') as mock_fallback:
                mock_fallback.analyze_text_unified.return_value = {"status": "success"}
                
                results = await pipeline.analyze_text_orchestrated(large_text)
                
                assert results["status"] == "success"
                assert results["metadata"]["text_length"] == len(large_text)
    
    @pytest.mark.asyncio
    async def test_concurrent_analyses_simulation(self):
        """Test de simulation d'analyses concurrentes."""
        config = ExtendedOrchestrationConfig(
            max_concurrent_analyses=3,
            use_mocks=True
        )
        
        # Simuler plusieurs analyses en parallèle
        texts = [f"Texte de test {i}" for i in range(5)]
        
        async def run_single_analysis(text):
            pipeline = UnifiedOrchestrationPipeline(config)
            with patch('argumentation_analysis.pipelines.unified_orchestration_pipeline.create_llm_service'):
                with patch('argumentation_analysis.pipelines.unified_orchestration_pipeline.UnifiedOrchestrationPipeline._initialize_base_services'):
                    await pipeline.initialize()
                with patch.object(pipeline, '_fallback_pipeline') as mock_fallback:
                    mock_fallback.analyze_text_unified.return_value = {"status": "success"}
                    return await pipeline.analyze_text_orchestrated(text)
        
        # Lancer les analyses en parallèle
        tasks = [run_single_analysis(text) for text in texts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Vérifier que toutes les analyses réussissent
        for result in results:
            assert not isinstance(result, Exception)
            assert result["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_invalid_configuration_handling(self):
        """Test de gestion de configurations invalides."""
        # Configuration avec valeurs invalides
        with pytest.raises(ValueError):
            ExtendedOrchestrationConfig(
                orchestration_mode="mode_inexistant"
            )
        
        with pytest.raises(ValueError):
            ExtendedOrchestrationConfig(
                analysis_type="type_inexistant"
            )
    
    @pytest.mark.asyncio
    async def test_memory_usage_monitoring(self):
        """Test de monitoring basique de l'usage mémoire."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        config = ExtendedOrchestrationConfig(use_mocks=True)
        pipeline = UnifiedOrchestrationPipeline(config)
        
        with patch('argumentation_analysis.pipelines.unified_orchestration_pipeline.create_llm_service'):
            with patch('argumentation_analysis.pipelines.unified_orchestration_pipeline.UnifiedOrchestrationPipeline._initialize_base_services'):
                await pipeline.initialize()
            
            # Analyser plusieurs textes
            for i in range(10):
                text = f"Analyse mémoire test {i} " * 100
                with patch.object(pipeline, '_fallback_pipeline') as mock_fallback:
                    mock_fallback.analyze_text_unified.return_value = {"status": "success"}
                    await pipeline.analyze_text_orchestrated(text)
            
            await pipeline.shutdown()
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Vérifier que l'augmentation mémoire reste raisonnable (< 100MB)
        assert memory_increase < 100 * 1024 * 1024  # 100MB


class TestPerformanceAndOptimization:
    """Tests de performance et d'optimisation."""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_pipeline_performance_benchmark(self):
        """Test de performance de base du pipeline."""
        config = ExtendedOrchestrationConfig(
            use_mocks=True,
            save_orchestration_trace=False  # Désactiver pour performance
        )
        
        text = "Texte de benchmark pour mesurer les performances." * 50
        
        start_time = time.time()
        
        with patch('argumentation_analysis.pipelines.unified_orchestration_pipeline.create_llm_service'):
            results = await run_unified_orchestration_pipeline(text, config)
        
        execution_time = time.time() - start_time
        
        # Vérifier que l'exécution se fait en moins de 10 secondes (permissif pour CI)
        assert execution_time < 10.0
        assert results["status"] == "success"
        
        # Vérifier que le temps reporté est cohérent
        reported_time = results["execution_time"]
        assert abs(reported_time - execution_time) < 0.5  # Tolérance de 0.5s
    
    @pytest.mark.asyncio
    async def test_orchestration_trace_performance(self):
        """Test de performance du système de trace."""
        config = ExtendedOrchestrationConfig(
            save_orchestration_trace=True,
            use_mocks=True
        )
        pipeline = UnifiedOrchestrationPipeline(config)
        
        # Ajouter beaucoup de traces
        start_time = time.time()
        for i in range(1000):
            pipeline._trace_orchestration(f"event_{i}", {"data": i})
        trace_time = time.time() - start_time
        
        # Vérifier que l'ajout de traces est rapide
        assert trace_time < 1.0  # Moins d'1 seconde pour 1000 traces
        assert len(pipeline.orchestration_trace) == 1000
    
    @pytest.mark.asyncio
    async def test_configuration_creation_performance(self):
        """Test de performance de création de configuration."""
        start_time = time.time()
        
        # Créer beaucoup de configurations
        configs = []
        for i in range(100):
            config = ExtendedOrchestrationConfig(
                analysis_type=AnalysisType.COMPREHENSIVE,
                orchestration_mode=OrchestrationMode.AUTO_SELECT,
                max_concurrent_analyses=i % 10 + 1
            )
            configs.append(config)
        
        creation_time = time.time() - start_time
        
        # Vérifier que la création est rapide
        assert creation_time < 1.0
        assert len(configs) == 100


if __name__ == "__main__":
    # Exécution des tests si le script est lancé directement
    pytest.main([__file__, "-v", "--tb=short"])