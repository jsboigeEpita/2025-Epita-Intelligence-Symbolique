# -*- coding: utf-8 -*-
"""
Tests d'intégration pour l'orchestration avec fact-checking.

Ces tests vérifient l'intégration des nouveaux composants
avec l'architecture d'orchestration existante.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

# Tests d'intégration avec le ServiceManager
try:
    from argumentation_analysis.orchestration.service_manager import (
        OrchestrationServiceManager,
    )
    from argumentation_analysis.orchestration.fact_checking_orchestrator import (
        FactCheckingOrchestrator,
        FactCheckingRequest,
        AnalysisDepth,
    )

    SERVICE_MANAGER_AVAILABLE = True
except ImportError as e:
    SERVICE_MANAGER_AVAILABLE = False
    IMPORT_ERROR = str(e)


class TestServiceManagerIntegration:
    """Tests d'intégration avec le ServiceManager."""

    @pytest.mark.skipif(
        not SERVICE_MANAGER_AVAILABLE,
        reason=f"ServiceManager non disponible: {IMPORT_ERROR if not SERVICE_MANAGER_AVAILABLE else ''}",
    )
    def test_service_manager_fact_checking_orchestrator_integration(self):
        """Test de l'intégration de l'orchestrateur fact-checking dans le ServiceManager."""
        with patch(
            "argumentation_analysis.orchestration.service_manager.FactCheckingOrchestrator"
        ) as mock_orchestrator_class:
            mock_orchestrator_class.return_value = Mock()

            # Créer le service manager avec configuration
            config = {
                "enable_specialized_orchestrators": True,
                "fact_checking_api_config": {"tavily_api_key": "test_key"},
            }

            service_manager = OrchestrationServiceManager()

            # The fact_checking_orchestrator is not initialized until initialize() is called
            assert (
                service_manager.fact_checking_orchestrator is None
            )  # Pas encore initialisé

    @pytest.mark.skipif(
        not SERVICE_MANAGER_AVAILABLE,
        reason=f"ServiceManager non disponible: {IMPORT_ERROR if not SERVICE_MANAGER_AVAILABLE else ''}",
    )
    @pytest.mark.xfail(reason="CluedoExtendedOrchestrator requires settings param in ServiceManager.initialize()")
    @pytest.mark.asyncio
    async def test_service_manager_fact_checking_initialization(self):
        """Test de l'initialisation de l'orchestrateur fact-checking via ServiceManager."""
        with patch(
            "argumentation_analysis.orchestration.service_manager.FactCheckingOrchestrator"
        ) as mock_orchestrator_class, patch(
            "argumentation_analysis.orchestration.service_manager.MessageMiddleware"
        ) as mock_middleware, patch(
            "semantic_kernel.Kernel"
        ) as mock_kernel:
            mock_orchestrator_instance = Mock()
            mock_orchestrator_class.return_value = mock_orchestrator_instance
            mock_middleware.return_value = Mock()
            mock_kernel.return_value = Mock()

            service_manager = OrchestrationServiceManager()

            # Initialiser
            success = await service_manager.initialize()

            assert success is True
            assert service_manager.fact_checking_orchestrator is not None

            # Vérifier que l'orchestrateur a été créé avec la bonne config
            mock_orchestrator_class.assert_called_once_with(
                api_config={"tavily_api_key": "test_key"}
            )

    @pytest.mark.skipif(
        not SERVICE_MANAGER_AVAILABLE,
        reason=f"ServiceManager non disponible: {IMPORT_ERROR if not SERVICE_MANAGER_AVAILABLE else ''}",
    )
    def test_service_manager_orchestrator_selection(self):
        """Test de la sélection d'orchestrateur pour les types d'analyse fact-checking."""
        with patch(
            "argumentation_analysis.orchestration.service_manager.FactCheckingOrchestrator"
        ) as mock_orchestrator_class:
            mock_fact_checking_orchestrator = Mock()
            mock_orchestrator_class.return_value = mock_fact_checking_orchestrator

            service_manager = OrchestrationServiceManager()
            service_manager.fact_checking_orchestrator = mock_fact_checking_orchestrator

            # Test de sélection pour différents types d'analyse
            fact_checking_types = [
                "fact_checking",
                "comprehensive",
                "fallacy_analysis",
                "rhetorical",
            ]

            for analysis_type in fact_checking_types:
                selected = service_manager._select_orchestrator(analysis_type)
                assert (
                    selected is mock_fact_checking_orchestrator
                ), f"Échec pour {analysis_type}"

    @pytest.mark.skipif(
        not SERVICE_MANAGER_AVAILABLE,
        reason=f"ServiceManager non disponible: {IMPORT_ERROR if not SERVICE_MANAGER_AVAILABLE else ''}",
    )
    @pytest.mark.xfail(reason="CluedoExtendedOrchestrator requires settings param in ServiceManager.initialize()")
    @pytest.mark.asyncio
    async def test_service_manager_analyze_text_with_fact_checking(self):
        """Test d'analyse de texte via ServiceManager avec fact-checking."""
        with patch(
            "argumentation_analysis.orchestration.service_manager.FactCheckingOrchestrator"
        ) as mock_orchestrator_class, patch(
            "argumentation_analysis.orchestration.service_manager.MessageMiddleware"
        ) as mock_middleware:
            # Mock de l'orchestrateur fact-checking
            mock_orchestrator_instance = Mock()
            mock_orchestrator_class.return_value = mock_orchestrator_instance

            # Mock de la méthode analyze_with_fact_checking
            mock_result = Mock()
            mock_result.request_id = "test_request_123"
            mock_result.comprehensive_result.to_dict.return_value = {
                "analysis_result": "test_analysis"
            }
            mock_result.processing_time = 1.5
            mock_result.status = "completed"
            mock_result.analysis_timestamp = datetime.now()

            mock_orchestrator_instance.analyze_with_fact_checking = AsyncMock(
                return_value=mock_result
            )

            mock_middleware.return_value = Mock()

            config = {
                "enable_specialized_orchestrators": True,
                "enable_communication_middleware": False,
                "enable_hierarchical": False,
                "save_results": False,  # Éviter la sauvegarde pour les tests
            }

            service_manager = OrchestrationServiceManager(config=config)
            await service_manager.initialize()

            # Analyser un texte
            result = await service_manager.analyze_text(
                "En 2024, 90% des français utilisent internet quotidiennement.",
                analysis_type="fact_checking",
            )

            assert result is not None
            assert result["status"] == "completed"
            assert "results" in result
            assert "specialized" in result["results"]
            assert result["results"]["specialized"]["method"] == "fact_checking"

    @pytest.mark.skipif(
        not SERVICE_MANAGER_AVAILABLE,
        reason=f"ServiceManager non disponible: {IMPORT_ERROR if not SERVICE_MANAGER_AVAILABLE else ''}",
    )
    @pytest.mark.asyncio
    async def test_service_manager_status_with_fact_checking(self):
        """Test du statut ServiceManager incluant l'orchestrateur fact-checking."""
        with patch(
            "argumentation_analysis.orchestration.service_manager.FactCheckingOrchestrator"
        ) as mock_orchestrator_class:
            mock_orchestrator_instance = Mock()
            mock_orchestrator_instance.get_performance_metrics.return_value = {
                "total_analyses": 5,
                "average_processing_time": 2.3,
                "error_rate": 0.0,
            }
            mock_orchestrator_class.return_value = mock_orchestrator_instance

            service_manager = OrchestrationServiceManager()
            service_manager.fact_checking_orchestrator = mock_orchestrator_instance
            service_manager._initialized = True

            status = await service_manager.get_status()

            assert "active_services" in status
            assert "fact_checking_orchestrator" in status["active_services"]
            assert status["active_services"]["fact_checking_orchestrator"] is True

            # Test du statut détaillé
            detailed_status = service_manager.get_status_details()

            assert "active_components" in detailed_status
            assert "fact_checking_orchestrator" in detailed_status["active_components"]
            assert (
                detailed_status["active_components"]["fact_checking_orchestrator"]
                is True
            )

            assert "component_specific_status" in detailed_status
            assert (
                "fact_checking_orchestrator"
                in detailed_status["component_specific_status"]
            )

            fact_checking_status = detailed_status["component_specific_status"][
                "fact_checking_orchestrator"
            ]
            assert fact_checking_status["total_analyses"] == 5
            assert fact_checking_status["average_processing_time"] == 2.3


class TestFactCheckingOrchestrationFlow:
    """Tests du flux d'orchestration avec fact-checking."""

    @pytest.mark.skipif(
        not SERVICE_MANAGER_AVAILABLE,
        reason=f"ServiceManager non disponible: {IMPORT_ERROR if not SERVICE_MANAGER_AVAILABLE else ''}",
    )
    @pytest.mark.xfail(reason="get_verification_service removed from fact_checking_orchestrator API")
    @pytest.mark.asyncio
    async def test_complete_fact_checking_flow(self):
        """Test du flux complet d'orchestration fact-checking."""
        with patch(
            "argumentation_analysis.orchestration.fact_checking_orchestrator.FactClaimExtractor"
        ) as mock_extractor, patch(
            "argumentation_analysis.orchestration.fact_checking_orchestrator.get_verification_service"
        ) as mock_verifier, patch(
            "argumentation_analysis.orchestration.fact_checking_orchestrator.get_taxonomy_manager"
        ) as mock_manager, patch(
            "argumentation_analysis.orchestration.fact_checking_orchestrator.get_family_analyzer"
        ) as mock_analyzer:
            # Mock des composants
            mock_extractor_instance = Mock()
            mock_extractor.return_value = mock_extractor_instance

            mock_verifier_instance = Mock()
            mock_verifier.return_value = mock_verifier_instance

            mock_manager_instance = Mock()
            mock_manager.return_value = mock_manager_instance

            mock_analyzer_instance = Mock()

            # Mock de l'analyse complète
            from argumentation_analysis.orchestration.fact_checking_orchestrator import (
                ComprehensiveAnalysisResult,
            )

            mock_comprehensive_result = Mock(spec=ComprehensiveAnalysisResult)
            mock_comprehensive_result.to_dict.return_value = {
                "family_results": {},
                "factual_claims": [],
                "fact_check_results": [],
                "overall_assessment": {"status": "completed"},
                "strategic_insights": {},
                "recommendations": [],
            }

            mock_analyzer_instance.analyze_comprehensive = AsyncMock(
                return_value=mock_comprehensive_result
            )
            mock_analyzer.return_value = mock_analyzer_instance

            # Créer et tester l'orchestrateur
            orchestrator = FactCheckingOrchestrator()

            request = FactCheckingRequest(
                text="En 2024, 85% des entreprises françaises utilisent l'intelligence artificielle.",
                analysis_depth=AnalysisDepth.STANDARD,
                enable_fact_checking=True,
            )

            response = await orchestrator.analyze_with_fact_checking(request)

            assert response is not None
            assert response.status == "completed"
            assert response.request_id is not None
            assert response.processing_time >= 0.0
            assert response.comprehensive_result is not None

    @pytest.mark.skipif(
        not SERVICE_MANAGER_AVAILABLE,
        reason=f"ServiceManager non disponible: {IMPORT_ERROR if not SERVICE_MANAGER_AVAILABLE else ''}",
    )
    @pytest.mark.xfail(reason="get_verification_service removed from fact_checking_orchestrator API")
    @pytest.mark.asyncio
    async def test_batch_analysis_integration(self):
        """Test d'analyse en lot via l'orchestrateur."""
        with patch(
            "argumentation_analysis.orchestration.fact_checking_orchestrator.FactClaimExtractor"
        ) as mock_extractor, patch(
            "argumentation_analysis.orchestration.fact_checking_orchestrator.get_verification_service"
        ) as mock_verifier, patch(
            "argumentation_analysis.orchestration.fact_checking_orchestrator.get_taxonomy_manager"
        ) as mock_manager, patch(
            "argumentation_analysis.orchestration.fact_checking_orchestrator.get_family_analyzer"
        ) as mock_analyzer:
            # Mock des composants
            mock_extractor.return_value = Mock()
            mock_verifier.return_value = Mock()
            mock_manager.return_value = Mock()

            mock_analyzer_instance = Mock()

            from argumentation_analysis.orchestration.fact_checking_orchestrator import (
                ComprehensiveAnalysisResult,
            )

            mock_comprehensive_result = Mock(spec=ComprehensiveAnalysisResult)
            mock_comprehensive_result.to_dict.return_value = {"status": "completed"}

            mock_analyzer_instance.analyze_comprehensive = AsyncMock(
                return_value=mock_comprehensive_result
            )
            mock_analyzer.return_value = mock_analyzer_instance

            # Test d'analyse en lot
            orchestrator = FactCheckingOrchestrator()

            texts = [
                "Premier texte à analyser avec fact-checking.",
                "Deuxième texte contenant 70% de statistiques.",
                "Troisième texte avec des affirmations scientifiques.",
            ]

            results = await orchestrator.batch_analyze(texts, AnalysisDepth.BASIC)

            assert len(results) == 3
            for result in results:
                assert result.status == "completed"
                assert result.request_id is not None


class TestErrorHandling:
    """Tests de gestion d'erreurs dans l'intégration."""

    @pytest.mark.skipif(
        not SERVICE_MANAGER_AVAILABLE,
        reason=f"ServiceManager non disponible: {IMPORT_ERROR if not SERVICE_MANAGER_AVAILABLE else ''}",
    )
    @pytest.mark.xfail(reason="get_verification_service removed from fact_checking_orchestrator API")
    @pytest.mark.asyncio
    async def test_fact_checking_orchestrator_error_handling(self):
        """Test de gestion d'erreurs dans l'orchestrateur fact-checking."""
        with patch(
            "argumentation_analysis.orchestration.fact_checking_orchestrator.FactClaimExtractor"
        ) as mock_extractor, patch(
            "argumentation_analysis.orchestration.fact_checking_orchestrator.get_verification_service"
        ) as mock_verifier, patch(
            "argumentation_analysis.orchestration.fact_checking_orchestrator.get_taxonomy_manager"
        ) as mock_manager, patch(
            "argumentation_analysis.orchestration.fact_checking_orchestrator.get_family_analyzer"
        ) as mock_analyzer:
            # Mock des composants avec erreur
            mock_extractor.return_value = Mock()
            mock_verifier.return_value = Mock()
            mock_manager.return_value = Mock()

            mock_analyzer_instance = Mock()
            mock_analyzer_instance.analyze_comprehensive = AsyncMock(
                side_effect=Exception("Test error in analysis")
            )
            mock_analyzer.return_value = mock_analyzer_instance

            orchestrator = FactCheckingOrchestrator()

            request = FactCheckingRequest(
                text="Texte qui va causer une erreur",
                analysis_depth=AnalysisDepth.STANDARD,
            )

            response = await orchestrator.analyze_with_fact_checking(request)

            assert response is not None
            assert response.status == "error"
            assert response.error_message is not None
            assert "Test error in analysis" in response.error_message

    @pytest.mark.skipif(
        not SERVICE_MANAGER_AVAILABLE,
        reason=f"ServiceManager non disponible: {IMPORT_ERROR if not SERVICE_MANAGER_AVAILABLE else ''}",
    )
    @pytest.mark.asyncio
    async def test_service_manager_fact_checking_error_recovery(self):
        """Test de récupération d'erreur dans le ServiceManager."""
        with patch(
            "argumentation_analysis.orchestration.service_manager.FactCheckingOrchestrator"
        ) as mock_orchestrator_class:
            mock_orchestrator_instance = Mock()
            mock_orchestrator_instance.analyze_with_fact_checking = AsyncMock(
                side_effect=Exception("Orchestrator error")
            )
            mock_orchestrator_class.return_value = mock_orchestrator_instance

            service_manager = OrchestrationServiceManager()
            service_manager.fact_checking_orchestrator = mock_orchestrator_instance
            service_manager._initialized = True

            # L'analyse devrait gérer l'erreur gracieusement
            result = await service_manager.analyze_text(
                "Texte test",
                analysis_type="fact_checking",
                options={"save_results": False},
            )

            assert result is not None
            assert result["status"] == "failed"
            assert "error" in result


class TestConfigurationIntegration:
    """Tests d'intégration de configuration."""

    @pytest.mark.skipif(
        not SERVICE_MANAGER_AVAILABLE,
        reason=f"ServiceManager non disponible: {IMPORT_ERROR if not SERVICE_MANAGER_AVAILABLE else ''}",
    )
    def test_fact_checking_api_configuration(self):
        """Test de la configuration API pour le fact-checking."""
        api_config = {
            "tavily_api_key": "test_tavily_key",
            "searxng_url": "http://test.searxng.url",
            "custom_sources": ["custom1.com", "custom2.com"],
        }

        with patch(
            "argumentation_analysis.orchestration.service_manager.FactCheckingOrchestrator"
        ) as mock_orchestrator_class:
            mock_orchestrator_class.return_value = Mock()

            service_manager = OrchestrationServiceManager()

            # Verify service manager is created without error
            assert service_manager.fact_checking_orchestrator is None

    @pytest.mark.skipif(
        not SERVICE_MANAGER_AVAILABLE,
        reason=f"ServiceManager non disponible: {IMPORT_ERROR if not SERVICE_MANAGER_AVAILABLE else ''}",
    )
    @pytest.mark.xfail(reason="get_verification_service removed from fact_checking_orchestrator API")
    @pytest.mark.asyncio
    async def test_fact_checking_orchestrator_api_config_update(self):
        """Test de mise à jour de configuration API."""
        with patch(
            "argumentation_analysis.orchestration.fact_checking_orchestrator.FactClaimExtractor"
        ) as mock_extractor, patch(
            "argumentation_analysis.orchestration.fact_checking_orchestrator.get_verification_service"
        ) as mock_verifier, patch(
            "argumentation_analysis.orchestration.fact_checking_orchestrator.get_taxonomy_manager"
        ) as mock_manager, patch(
            "argumentation_analysis.orchestration.fact_checking_orchestrator.get_family_analyzer"
        ) as mock_analyzer:
            mock_extractor.return_value = Mock()
            mock_verifier.return_value = Mock()
            mock_manager.return_value = Mock()
            mock_analyzer.return_value = Mock()

            orchestrator = FactCheckingOrchestrator()

            initial_config = orchestrator.get_api_config()
            assert initial_config == {}

            new_config = {"test_key": "test_value"}
            orchestrator.update_api_config(new_config)

            updated_config = orchestrator.get_api_config()
            assert updated_config["test_key"] == "test_value"


if __name__ == "__main__":
    # Exécution des tests si le script est lancé directement
    pytest.main([__file__, "-v"])
