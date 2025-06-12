#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests d'Intégration pour l'Orchestration Unifiée
===============================================

Tests d'intégration pour valider le fonctionnement global du système d'orchestration :
- Intégration pipeline unifié avec composants hiérarchiques
- Intégration avec les orchestrateurs spécialisés
- Flux de bout en bout
- Performance et robustesse
- Compatibilité avec l'API existante

Auteur: Intelligence Symbolique EPITA
Date: 10/06/2025
"""

import pytest
import asyncio
import logging
import time
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, Any, List

# Configuration du logging pour les tests
logging.basicConfig(level=logging.WARNING)

# Imports à tester
try:
    from argumentation_analysis.pipelines.unified_orchestration_pipeline import (
        UnifiedOrchestrationPipeline,
        ExtendedOrchestrationConfig,
        OrchestrationMode,
        AnalysisType,
        run_unified_orchestration_pipeline
    )
    from argumentation_analysis.pipelines.unified_pipeline import run_unified_text_analysis
    ORCHESTRATION_INTEGRATION_AVAILABLE = True
except ImportError as e:
    ORCHESTRATION_INTEGRATION_AVAILABLE = False
    pytestmark = pytest.mark.skip(f"Intégration orchestration non disponible: {e}")


class TestEndToEndOrchestration:
    """Tests de bout en bout du système d'orchestration."""
    
    @pytest.fixture
    def sample_texts(self):
        """Textes d'exemple pour différents scénarios."""
        return {
            "simple_argument": "L'éducation améliore la société car elle forme des citoyens éclairés.",
            "complex_debate": (
                "L'intelligence artificielle transformera l'éducation en personnalisant l'apprentissage. "
                "Cependant, certains craignent une déshumanisation. D'une part, l'IA peut adapter "
                "le contenu à chaque élève. D'autre part, elle pourrait remplacer les enseignants. "
                "Il faut donc trouver un équilibre entre innovation et valeurs humaines."
            ),
            "investigation_case": (
                "Le témoin principal affirme avoir vu l'accusé sur les lieux à 21h. "
                "Cependant, les relevés de téléphone montrent qu'il était ailleurs. "
                "Un second témoin confirme sa présence ailleurs. Qui dit la vérité ?"
            ),
            "dialogue_argument": (
                "Alice: L'enseignement à distance est l'avenir de l'éducation.\n"
                "Bob: Je ne suis pas d'accord, rien ne remplace le contact humain.\n"
                "Alice: Mais pensez à l'accessibilité pour les zones rurales.\n"
                "Bob: C'est vrai, mais quid de la sociabilisation des enfants ?"
            ),
            "logical_complex": (
                "Si tous les experts sont fiables, et si tous les fiables donnent des conseils justes, "
                "alors tous les experts donnent des conseils justes. Or, certains experts se trompent. "
                "Par conséquent, soit certains experts ne sont pas fiables, soit notre raisonnement est faux."
            )
        }
    
    @pytest.mark.asyncio
    async def test_pipeline_mode_end_to_end(self, sample_texts):
        """Test de bout en bout en mode pipeline standard."""
        config = ExtendedOrchestrationConfig(
            orchestration_mode=OrchestrationMode.PIPELINE,
            analysis_type=AnalysisType.COMPREHENSIVE,
            use_mocks=True,
            save_orchestration_trace=True
        )
        
        # Mock du pipeline de fallback
        with patch('argumentation_analysis.pipelines.unified_orchestration_pipeline.create_llm_service'):
            with patch('argumentation_analysis.pipelines.unified_text_analysis.run_unified_text_analysis') as mock_fallback:
                mock_fallback.return_value = {
                    "informal_analysis": {"fallacies": [], "summary": {"total_fallacies": 0}},
                    "formal_analysis": {"status": "success", "logical_structure": "valid"},
                    "unified_analysis": {"status": "success", "coherence_score": 0.85},
                    "status": "success"
                }
                
                results = await run_unified_orchestration_pipeline(
                    sample_texts["simple_argument"], 
                    config
                )
                
                assert results["status"] == "success"
                assert "execution_time" in results
                assert "metadata" in results
                assert results["metadata"]["pipeline_version"] == "unified_orchestration_2.0"
                assert "orchestration_trace" in results
                assert len(results["orchestration_trace"]) > 0
    
    @pytest.mark.asyncio
    async def test_hierarchical_mode_end_to_end(self, sample_texts):
        """Test de bout en bout en mode hiérarchique."""
        config = ExtendedOrchestrationConfig(
            orchestration_mode=OrchestrationMode.HIERARCHICAL_FULL,
            analysis_type=AnalysisType.COMPREHENSIVE,
            enable_hierarchical=True,
            use_mocks=True,
            save_orchestration_trace=True
        )
        
        with patch('argumentation_analysis.pipelines.unified_orchestration_pipeline.create_llm_service'):
            with patch('argumentation_analysis.pipelines.unified_orchestration_pipeline.StrategicManager') as mock_strategic:
                with patch('argumentation_analysis.pipelines.unified_orchestration_pipeline.TaskCoordinator') as mock_tactical:
                    with patch('argumentation_analysis.pipelines.unified_orchestration_pipeline.OperationalManager') as mock_operational:
                        
                        # Configuration des mocks hiérarchiques
                        mock_strategic_instance = MagicMock()
                        mock_strategic_instance.initialize_analysis = AsyncMock(return_value={
                            "objectives": [{"id": "obj1", "description": "Test objective"}],
                            "strategic_plan": {"phases": [{"id": "phase1", "name": "Test phase"}]}
                        })
                        mock_strategic.return_value = mock_strategic_instance
                        
                        mock_tactical_instance = MagicMock()
                        mock_tactical_instance.process_strategic_objectives = AsyncMock(return_value={"tasks_created": 3})
                        mock_tactical.return_value = mock_tactical_instance
                        
                        mock_operational_instance = MagicMock()
                        mock_operational_instance.execute_tactical_tasks = AsyncMock(return_value={
                            "execution_summary": {"completed": 3, "failed": 0},
                            "task_results": {"task1": {"result": "success"}}
                        })
                        mock_operational.return_value = mock_operational_instance
                        
                        results = await run_unified_orchestration_pipeline(
                            sample_texts["complex_debate"], 
                            config
                        )
                        
                        assert results["status"] == "success"
                        assert "strategic_analysis" in results
                        assert "tactical_coordination" in results
                        assert "hierarchical_coordination" in results
    
    @pytest.mark.asyncio
    async def test_specialized_orchestrator_end_to_end(self, sample_texts):
        """Test de bout en bout avec orchestrateurs spécialisés."""
        config = ExtendedOrchestrationConfig(
            orchestration_mode=OrchestrationMode.CLUEDO_INVESTIGATION,
            analysis_type=AnalysisType.INVESTIGATIVE,
            enable_specialized_orchestrators=True,
            use_mocks=True
        )
        
        with patch('argumentation_analysis.pipelines.unified_orchestration_pipeline.create_llm_service'):
            with patch('argumentation_analysis.pipelines.unified_orchestration_pipeline.CluedoOrchestrator') as mock_cluedo:
                
                mock_cluedo_instance = MagicMock()
                mock_cluedo_instance.orchestrate_investigation_analysis = AsyncMock(return_value={
                    "evidence_analysis": {"physical": [], "testimonial": ["témoin principal", "second témoin"]},
                    "credibility_assessment": {"témoin principal": 0.7, "second témoin": 0.8},
                    "investigation_conclusion": {"verdict": "second témoin plus crédible", "confidence": 0.8}
                })
                mock_cluedo.return_value = mock_cluedo_instance
                
                results = await run_unified_orchestration_pipeline(
                    sample_texts["investigation_case"], 
                    config
                )
                
                assert results["status"] == "success"
                assert "specialized_orchestration" in results
                assert "investigation_conclusion" in results["specialized_orchestration"]
                assert results["specialized_orchestration"]["investigation_conclusion"]["confidence"] == 0.8
    
    @pytest.mark.asyncio
    async def test_auto_select_mode_end_to_end(self, sample_texts):
        """Test de bout en bout avec sélection automatique."""
        config = ExtendedOrchestrationConfig(
            orchestration_mode=OrchestrationMode.AUTO_SELECT,
            analysis_type=AnalysisType.COMPREHENSIVE,
            auto_select_orchestrator=True,
            use_mocks=True
        )
        
        test_cases = [
            (sample_texts["investigation_case"], "cluedo"),
            (sample_texts["dialogue_argument"], "conversation"),
            (sample_texts["logical_complex"], "logic_complex"),
            (sample_texts["simple_argument"], "pipeline")
        ]
        
        for text, expected_strategy in test_cases:
            with patch('argumentation_analysis.pipelines.unified_orchestration_pipeline.create_llm_service'):
                # Mock de la sélection automatique
                with patch('argumentation_analysis.pipelines.unified_text_analysis.run_unified_text_analysis') as mock_fallback:
                    mock_fallback.return_value = {"status": "success"}
                    
                    results = await run_unified_orchestration_pipeline(text, config)
                    
                    assert results["status"] == "success"
                    assert "metadata" in results
                    # La stratégie sélectionnée devrait être dans les métadonnées
                    if "orchestration_strategy" in results["metadata"]:
                        # Vérifier que la stratégie est cohérente avec le contenu
                        assert results["metadata"]["orchestration_strategy"] in [
                            expected_strategy, "fallback", "hybrid"
                        ]


class TestCompatibilityWithExistingAPI:
    """Tests de compatibilité avec l'API existante."""
    
    @pytest.mark.asyncio
    async def test_unified_pipeline_compatibility(self):
        """Test de compatibilité avec le pipeline unifié existant."""
        text = "Test de compatibilité avec l'API existante."
        
        # Test avec le nouveau pipeline via l'ancien point d'entrée
        with patch('argumentation_analysis.pipelines.unified_pipeline.detect_orchestration_capabilities') as mock_detect:
            mock_detect.return_value = True  # Orchestration disponible
            
            with patch('argumentation_analysis.pipelines.unified_pipeline.run_unified_orchestration_pipeline') as mock_run_orchestration:
                mock_run_orchestration.return_value = {
                    "status": "success",
                    "mode": "orchestrated",
                    "informal_analysis": {"fallacies": []},
                    "formal_analysis": {"status": "success"},
                    "unified_analysis": {"coherence_score": 0.8}
                }
                
                # Appel via l'ancien point d'entrée
                results = await run_unified_text_analysis(
                    text=text,
                    modes=["informal", "formal", "unified"],
                    use_orchestration=True
                )
                
                assert results["status"] == "success"
                assert results["mode"] == "orchestrated"
                assert "informal_analysis" in results
                assert "formal_analysis" in results
                assert "unified_analysis" in results
    
    @pytest.mark.asyncio
    async def test_fallback_to_original_pipeline(self):
        """Test de fallback vers le pipeline original."""
        text = "Test de fallback vers le pipeline original."
        
        # Simuler l'indisponibilité de l'orchestration
        with patch('argumentation_analysis.pipelines.unified_pipeline.detect_orchestration_capabilities') as mock_detect:
            mock_detect.return_value = False  # Orchestration non disponible
            
            with patch('argumentation_analysis.pipelines.unified_text_analysis.run_unified_text_analysis') as mock_run_original:
                mock_run_original.return_value = {
                    "status": "success",
                    "mode": "original",
                    "informal_analysis": {"fallacies": []},
                    "formal_analysis": {"status": "success"}
                }
                
                results = await run_unified_text_analysis(
                    text=text,
                    modes=["informal", "formal"],
                    use_orchestration=True  # Demandé mais non disponible
                )
                
                assert results["status"] == "success"
                assert results["mode"] == "original"
                mock_run_original.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_parameter_mapping_compatibility(self):
        """Test de mapping des paramètres pour la compatibilité."""
        text = "Test de mapping des paramètres."
        
        # Test avec différents paramètres de l'ancienne API
        compatibility_cases = [
            {
                "modes": ["informal"],
                "expected_analysis_type": AnalysisType.RHETORICAL
            },
            {
                "modes": ["formal"],
                "expected_analysis_type": AnalysisType.LOGICAL
            },
            {
                "modes": ["informal", "formal", "unified"],
                "expected_analysis_type": AnalysisType.COMPREHENSIVE
            }
        ]
        
        for case in compatibility_cases:
            with patch('argumentation_analysis.pipelines.unified_pipeline.detect_orchestration_capabilities') as mock_detect:
                mock_detect.return_value = True
                
                with patch('argumentation_analysis.pipelines.unified_pipeline.run_unified_orchestration_pipeline') as mock_run:
                    mock_run.return_value = {"status": "success"}
                    
                    await run_unified_text_analysis(
                        text=text,
                        modes=case["modes"],
                        use_orchestration=True
                    )
                    
                    # Vérifier que la configuration passée correspond aux attentes
                    call_args = mock_run.call_args
                    config = call_args[0][1]  # Deuxième argument = config
                    assert config.analysis_type == case["expected_analysis_type"]


class TestPerformanceAndRobustness:
    """Tests de performance et robustesse."""
    
    @pytest.mark.asyncio
    async def test_concurrent_orchestration_requests(self):
        """Test de gestion de requêtes d'orchestration concurrentes."""
        texts = [f"Texte de test concurrent {i}" for i in range(5)]
        
        config = ExtendedOrchestrationConfig(
            orchestration_mode=OrchestrationMode.PIPELINE,
            use_mocks=True,
            max_concurrent_analyses=3
        )
        
        async def single_orchestration(text):
            with patch('argumentation_analysis.pipelines.unified_orchestration_pipeline.create_llm_service'):
                with patch('argumentation_analysis.pipelines.unified_text_analysis.run_unified_text_analysis') as mock_fallback:
                    mock_fallback.return_value = {"status": "success"}
                    return await run_unified_orchestration_pipeline(text, config)
        
        # Lancer les orchestrations en parallèle
        start_time = time.time()
        tasks = [single_orchestration(text) for text in texts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        # Vérifier que toutes les orchestrations réussissent
        for result in results:
            assert not isinstance(result, Exception)
            assert result["status"] == "success"
        
        # Vérifier que l'exécution parallèle est efficace
        assert execution_time < 10.0  # Temps raisonnable pour 5 analyses
    
    @pytest.mark.asyncio
    async def test_error_handling_robustness(self):
        """Test de robustesse de la gestion d'erreurs."""
        error_scenarios = [
            {
                "description": "Service LLM indisponible",
                "patch_target": "argumentation_analysis.pipelines.unified_orchestration_pipeline.create_llm_service",
                "side_effect": Exception("Service LLM indisponible")
            },
            {
                "description": "Timeout d'initialisation",
                "patch_target": "argumentation_analysis.pipelines.unified_orchestration_pipeline.initialize_jvm",
                "side_effect": Exception("Timeout JVM")
            }
        ]
        
        config = ExtendedOrchestrationConfig(use_mocks=True)
        text = "Texte de test pour robustesse"
        
        for scenario in error_scenarios:
            with patch(scenario["patch_target"]) as mock_component:
                mock_component.side_effect = scenario["side_effect"]
                
                # Le pipeline doit gérer l'erreur gracieusement
                results = await run_unified_orchestration_pipeline(text, config)
                
                # Même en cas d'erreur, le système doit retourner un résultat
                assert "status" in results
                # Le status peut être "success" (via fallback) ou "failed" avec détails
                assert results["status"] in ["success", "failed"]
                
                if results["status"] == "failed":
                    assert "error" in results
                    assert scenario["description"].lower() in results["error"].lower()
    
    @pytest.mark.asyncio
    async def test_memory_usage_optimization(self):
        """Test d'optimisation de l'usage mémoire."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        config = ExtendedOrchestrationConfig(
            use_mocks=True,
            save_orchestration_trace=False  # Désactiver pour économiser la mémoire
        )
        
        # Analyser plusieurs textes volumineux
        large_texts = [f"Texte volumineux d'analyse {i}. " * 1000 for i in range(3)]
        
        for text in large_texts:
            with patch('argumentation_analysis.pipelines.unified_orchestration_pipeline.create_llm_service'):
                with patch('argumentation_analysis.pipelines.unified_text_analysis.run_unified_text_analysis') as mock_fallback:
                    mock_fallback.return_value = {"status": "success"}
                    
                    results = await run_unified_orchestration_pipeline(text, config)
                    assert results["status"] == "success"
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Vérifier que l'augmentation mémoire reste raisonnable (< 50MB)
        assert memory_increase < 50 * 1024 * 1024  # 50MB
    
    @pytest.mark.asyncio
    async def test_orchestration_trace_functionality(self):
        """Test de fonctionnalité des traces d'orchestration."""
        config = ExtendedOrchestrationConfig(
            orchestration_mode=OrchestrationMode.PIPELINE,
            save_orchestration_trace=True,
            use_mocks=True
        )
        
        text = "Texte pour test de trace d'orchestration"
        
        with patch('argumentation_analysis.pipelines.unified_orchestration_pipeline.create_llm_service'):
            with patch('argumentation_analysis.pipelines.unified_text_analysis.run_unified_text_analysis') as mock_fallback:
                mock_fallback.return_value = {"status": "success"}
                
                results = await run_unified_orchestration_pipeline(text, config)
                
                assert results["status"] == "success"
                assert "orchestration_trace" in results
                assert len(results["orchestration_trace"]) > 0
                
                # Vérifier la structure des traces
                for trace_entry in results["orchestration_trace"]:
                    assert "timestamp" in trace_entry
                    assert "event_type" in trace_entry
                    assert "data" in trace_entry
                    assert trace_entry["timestamp"]  # Non vide
                    assert trace_entry["event_type"]  # Non vide


class TestSpecializedIntegrationScenarios:
    """Tests de scénarios d'intégration spécialisés."""
    
    @pytest.mark.asyncio
    async def test_multi_orchestrator_coordination(self):
        """Test de coordination entre plusieurs orchestrateurs."""
        # Texte complexe nécessitant plusieurs orchestrateurs
        complex_text = (
            "Dans cette enquête criminelle, l'inspecteur interroge le suspect : "
            "'Si vous étiez innocent, pourquoi fuir ?' Le suspect répond : "
            "'Fuir ne prouve pas la culpabilité. D'ailleurs, tout innocent "
            "craindrait une erreur judiciaire.' Qui a raison logiquement ?"
        )
        
        config = ExtendedOrchestrationConfig(
            orchestration_mode=OrchestrationMode.HYBRID,
            analysis_type=AnalysisType.COMPREHENSIVE,
            enable_hierarchical=True,
            enable_specialized_orchestrators=True,
            use_mocks=True
        )
        
        with patch('argumentation_analysis.pipelines.unified_orchestration_pipeline.create_llm_service'):
            # Mock de coordination multi-orchestrateurs
            with patch('argumentation_analysis.pipelines.unified_orchestration_pipeline.CluedoOrchestrator') as mock_cluedo:
                with patch('argumentation_analysis.pipelines.unified_orchestration_pipeline.ConversationOrchestrator') as mock_conversation:
                    with patch('argumentation_analysis.pipelines.unified_orchestration_pipeline.LogiqueComplexeOrchestrator') as mock_logic:
                        
                        # Configuration des mocks
                        mock_cluedo.return_value.orchestrate_investigation_analysis = AsyncMock(return_value={
                            "investigation_findings": "Dialogue suspect-inspecteur"
                        })
                        
                        mock_conversation.return_value.orchestrate_dialogue_analysis = AsyncMock(return_value={
                            "dialogue_structure": "Question-réponse argumentée"
                        })
                        
                        mock_logic.return_value.orchestrate_complex_logical_analysis = AsyncMock(return_value={
                            "logical_assessment": "Raisonnement valide sur l'innocence"
                        })
                        
                        results = await run_unified_orchestration_pipeline(complex_text, config)
                        
                        assert results["status"] == "success"
                        # En mode hybride, plusieurs orchestrateurs peuvent être utilisés
                        assert "metadata" in results
    
    @pytest.mark.asyncio
    async def test_escalation_and_fallback_chain(self):
        """Test de chaîne d'escalade et de fallback."""
        config = ExtendedOrchestrationConfig(
            orchestration_mode=OrchestrationMode.HIERARCHICAL_FULL,
            enable_hierarchical=True,
            use_mocks=True
        )
        
        text = "Texte pour test d'escalade et fallback"
        
        # Simuler des échecs en cascade
        with patch('argumentation_analysis.pipelines.unified_orchestration_pipeline.create_llm_service'):
            with patch('argumentation_analysis.pipelines.unified_orchestration_pipeline.StrategicManager') as mock_strategic:
                # Simuler échec du gestionnaire stratégique
                mock_strategic.side_effect = Exception("Gestionnaire stratégique indisponible")
                
                with patch('argumentation_analysis.pipelines.unified_text_analysis.run_unified_text_analysis') as mock_fallback:
                    mock_fallback.return_value = {"status": "success", "mode": "fallback"}
                    
                    results = await run_unified_orchestration_pipeline(text, config)
                    
                    # Le système doit fallback vers le pipeline original
                    assert results["status"] == "success"
                    assert "error_handled" in results or results.get("mode") == "fallback"


if __name__ == "__main__":
    # Exécution des tests si le script est lancé directement
    pytest.main([__file__, "-v", "--tb=short"])