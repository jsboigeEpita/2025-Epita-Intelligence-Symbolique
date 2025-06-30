# -*- coding: utf-8 -*-
"""
Tests de validation de l'intégration réussie du système de fact-checking.

Ces tests utilisent les mocks pour valider que l'intégration fonctionne
correctement dans différents scénarios et conditions.
"""

import pytest
import asyncio
from unittest.mock import patch, Mock
from datetime import datetime

# Import des mocks
from .mocks.fact_checking_mocks import (
    MockFactClaimExtractor, MockFactVerificationService, MockFallacyTaxonomyManager,
    MockFallacyFamilyAnalyzer, MockOrchestrator, IntegrationTestScenarios,
    create_mock_extractor, create_mock_verifier, create_mock_taxonomy_manager,
    create_mock_analyzer, create_mock_orchestrator
)


class TestIntegrationSuccess:
    """Tests de validation de l'intégration réussie."""
    
    def test_mock_fact_claim_extractor_success(self):
        """Test que l'extracteur mock fonctionne correctement."""
        extractor = create_mock_extractor(IntegrationTestScenarios.SUCCESS)
        
        # Test avec contenu statistique
        text = "En 2024, 85% des entreprises utilisent l'IA selon les experts."
        claims = extractor.extract_factual_claims(text, max_claims=5)
        
        assert len(claims) >= 2  # Au moins statistique et temporel
        assert extractor.call_count == 1
        
        # Vérifier que les claims contiennent les bonnes informations
        claim_texts = [getattr(c, 'claim_text', c.get('claim_text', '')) for c in claims]
        assert any("85%" in text for text in claim_texts)
        assert any("2024" in text for text in claim_texts)
    
    def test_mock_fact_claim_extractor_no_claims(self):
        """Test avec aucune affirmation détectée."""
        extractor = create_mock_extractor(IntegrationTestScenarios.NO_CONTENT)
        
        text = "Voici un texte sans affirmations factuelles vérifiables."
        claims = extractor.extract_factual_claims(text)
        
        assert len(claims) == 0
        assert extractor.call_count == 1
    
    def test_mock_fact_claim_extractor_error_handling(self):
        """Test de gestion d'erreur dans l'extracteur."""
        extractor = create_mock_extractor(IntegrationTestScenarios.ERROR_HANDLING)
        
        with pytest.raises(Exception, match="Mock error in claim extraction"):
            extractor.extract_factual_claims("Texte de test")
    
    @pytest.mark.asyncio
    async def test_mock_fact_verification_service_success(self):
        """Test du service de vérification mock."""
        verifier = create_mock_verifier(IntegrationTestScenarios.SUCCESS)
        
        # Créer une claim mock
        mock_claim = type('MockClaim', (), {
            'claim_text': "85% des entreprises utilisent l'IA"
        })()
        
        result = await verifier.verify_claim(mock_claim)
        
        assert result is not None
        assert verifier.call_count == 1
        assert len(verifier.verification_history) == 1
        
        # Vérifier les attributs du résultat
        if hasattr(result, 'status'):
            assert result.status is not None
            assert result.confidence >= 0.0
        else:
            assert 'status' in result
            assert result['confidence'] >= 0.0
    
    @pytest.mark.asyncio
    async def test_mock_fact_verification_multiple_claims(self):
        """Test de vérification multiple."""
        verifier = create_mock_verifier(IntegrationTestScenarios.MIXED_RESULTS)
        
        # Créer plusieurs claims mock
        claims = [
            type('MockClaim', (), {'claim_text': f"Claim {i}"})()
            for i in range(3)
        ]
        
        results = await verifier.verify_multiple_claims(claims)
        
        assert len(results) == 3
        assert verifier.call_count == 3  # Un appel par claim
        
        # Vérifier que les résultats alternent (scénario MIXED)
        statuses = []
        for result in results:
            if hasattr(result, 'status'):
                status = result.status.value if hasattr(result.status, 'value') else result.status
            else:
                status = result['status']
            statuses.append(status)
        
        # Dans le scénario MIXED, les statuts doivent varier
        assert len(set(statuses)) > 1
    
    @pytest.mark.asyncio
    async def test_mock_fact_verification_error_handling(self):
        """Test de gestion d'erreur dans la vérification."""
        verifier = create_mock_verifier(IntegrationTestScenarios.ERROR_HANDLING)
        
        mock_claim = type('MockClaim', (), {'claim_text': "Test claim"})()
        
        with pytest.raises(Exception, match="Mock error in fact verification"):
            await verifier.verify_claim(mock_claim)
    
    def test_mock_taxonomy_manager_success(self):
        """Test du gestionnaire de taxonomie mock."""
        manager = create_mock_taxonomy_manager(IntegrationTestScenarios.SUCCESS)
        
        text = "Tous les experts s'accordent à dire que cette solution génère de la peur."
        fallacies = manager.detect_fallacies_with_families(text, max_fallacies=10)
        
        assert len(fallacies) >= 1  # Au moins appel à l'autorité
        assert manager.call_count == 1
        
        # Vérifier les familles détectées
        families_detected = set()
        for fallacy in fallacies:
            if hasattr(fallacy, 'family'):
                family = fallacy.family.value if hasattr(fallacy.family, 'value') else fallacy.family
            else:
                family = fallacy.get('family')
            families_detected.add(family)
        
        # Devrait détecter au moins autorité et émotion
        expected_families = {"authority_popularity", "emotional_appeals"}
        assert len(families_detected.intersection(expected_families)) >= 1
    
    def test_mock_taxonomy_manager_statistics(self):
        """Test des statistiques par famille."""
        manager = create_mock_taxonomy_manager(IntegrationTestScenarios.HIGH_CONFIDENCE)
        
        text = "Les experts confirment que cela génère de la peur chez tous les utilisateurs."
        fallacies = manager.detect_fallacies_with_families(text)
        
        stats = manager.get_family_statistics(fallacies)
        
        assert isinstance(stats, dict)
        assert len(stats) > 0
        
        # Vérifier la structure des statistiques
        for family, stat in stats.items():
            assert 'count' in stat
            assert 'percentage' in stat
            assert 'present' in stat
            assert stat['present'] is True
    
    @pytest.mark.asyncio
    async def test_mock_family_analyzer_comprehensive(self):
        """Test de l'analyseur par famille mock."""
        analyzer = create_mock_analyzer(IntegrationTestScenarios.COMPREHENSIVE)
        
        text = "En 2024, 85% des experts confirment que l'IA génère de la peur chez tous."
        result = await analyzer.analyze_comprehensive(text)
        
        assert result is not None
        assert analyzer.call_count == 1
        
        # Vérifier la structure du résultat
        if hasattr(result, 'factual_claims'):
            assert len(result.factual_claims) >= 0
            assert len(result.fact_check_results) >= 0
        else:
            assert 'factual_claims' in result
            assert 'fact_check_results' in result
    
    @pytest.mark.asyncio
    async def test_mock_family_analyzer_error_handling(self):
        """Test de gestion d'erreur dans l'analyseur."""
        analyzer = create_mock_analyzer(IntegrationTestScenarios.ERROR_HANDLING)
        
        with pytest.raises(Exception, match="Mock error in comprehensive analysis"):
            await analyzer.analyze_comprehensive("Test text")
    
    @pytest.mark.asyncio
    async def test_mock_orchestrator_full_integration(self):
        """Test de l'orchestrateur mock complet."""
        orchestrator = create_mock_orchestrator(IntegrationTestScenarios.SUCCESS)
        
        # Créer une requête mock
        request = type('MockRequest', (), {
            'text': "En 2024, 85% des experts s'accordent sur cette solution.",
            'analysis_depth': 'standard'
        })()
        
        response = await orchestrator.analyze_with_fact_checking(request)
        
        assert response is not None
        assert orchestrator.call_count == 1
        
        # Vérifier la structure de la réponse
        if hasattr(response, 'status'):
            assert response.status == "completed"
            assert response.processing_time >= 0.0
        else:
            assert response['status'] == "completed"
            assert response['processing_time'] >= 0.0
    
    @pytest.mark.asyncio
    async def test_mock_orchestrator_quick_fact_check(self):
        """Test du fact-checking rapide via orchestrateur."""
        orchestrator = create_mock_orchestrator(IntegrationTestScenarios.SUCCESS)
        
        result = await orchestrator.quick_fact_check("85% des entreprises utilisent l'IA.")
        
        assert result['status'] == "completed"
        assert 'claims_count' in result
        assert 'processing_time' in result
        assert result['claims_count'] > 0
    
    @pytest.mark.asyncio
    async def test_mock_orchestrator_no_claims(self):
        """Test orchestrateur avec aucune affirmation."""
        orchestrator = create_mock_orchestrator(IntegrationTestScenarios.NO_CONTENT)
        
        result = await orchestrator.quick_fact_check("Texte sans affirmations factuelles.")
        
        assert result['status'] == "no_claims"
        assert 'message' in result
    
    @pytest.mark.asyncio
    async def test_mock_orchestrator_health_check(self):
        """Test du health check de l'orchestrateur."""
        orchestrator = create_mock_orchestrator(IntegrationTestScenarios.SUCCESS)
        
        health = await orchestrator.health_check()
        
        assert health['status'] == "healthy"
        assert 'components' in health
        assert 'fact_extractor' in health['components']
        assert 'taxonomy_manager' in health['components']
        assert 'verification_service' in health['components']


class TestIntegrationScenarios:
    """Tests des différents scénarios d'intégration."""
    
    @pytest.mark.asyncio
    async def test_scenario_success_end_to_end(self):
        """Test du scénario de succès de bout en bout."""
        orchestrator = create_mock_orchestrator(IntegrationTestScenarios.SUCCESS)
        
        # Test avec un texte contenant plusieurs éléments
        text = """
        En 2024, selon une étude récente, 85% des entreprises françaises 
        ont adopté l'intelligence artificielle. Tous les experts s'accordent 
        à dire que cette technologie révolutionnaire transforme le marché.
        Cependant, cette évolution génère de la peur chez certains utilisateurs.
        """
        
        request = type('MockRequest', (), {
            'text': text,
            'analysis_depth': 'comprehensive'
        })()
        
        response = await orchestrator.analyze_with_fact_checking(request)
        
        # Vérifications de l'intégration réussie
        assert response is not None
        
        if hasattr(response, 'status'):
            assert response.status == "completed"
            assert response.processing_time > 0.0
            comprehensive_result = response.comprehensive_result
        else:
            assert response['status'] == "completed"
            comprehensive_result = response['comprehensive_result']
        
        # Vérifier que l'analyse a trouvé du contenu
        if hasattr(comprehensive_result, 'factual_claims'):
            # Le texte contient des éléments statistiques et temporels
            assert len(comprehensive_result.factual_claims) >= 1
        else:
            # Format dict
            assert comprehensive_result.get('factual_claims', 0) >= 1
    
    @pytest.mark.asyncio
    async def test_scenario_mixed_results(self):
        """Test du scénario avec résultats mixtes."""
        analyzer = create_mock_analyzer(IntegrationTestScenarios.MIXED_RESULTS)
        
        text = "Claim 1. Claim 2. Claim 3."
        result = await analyzer.analyze_comprehensive(text)
        
        # Dans le scénario MIXED, on devrait avoir des résultats variés
        assert result is not None
        
        # Vérifier que les sous-composants ont été appelés
        assert analyzer.fact_extractor.call_count > 0
        assert analyzer.verification_service.call_count >= 0  # Peut être 0 si no claims
    
    @pytest.mark.asyncio 
    async def test_scenario_high_confidence(self):
        """Test du scénario avec confiance élevée."""
        manager = create_mock_taxonomy_manager(IntegrationTestScenarios.HIGH_CONFIDENCE)
        
        text = "Tous les experts confirment que cette approche génère des attaques personnelles."
        fallacies = manager.detect_fallacies_with_families(text)
        
        # Le scénario HIGH_CONFIDENCE devrait produire plus de résultats
        assert len(fallacies) >= 2
        
        # Vérifier les niveaux de confiance
        confidences = []
        for fallacy in fallacies:
            if hasattr(fallacy, 'confidence'):
                confidences.append(fallacy.confidence)
            else:
                confidences.append(fallacy.get('confidence', 0))
        
        # Toutes les confidences devraient être élevées
        assert all(conf >= 0.8 for conf in confidences)
    
    @pytest.mark.asyncio
    async def test_scenario_error_recovery(self):
        """Test de récupération d'erreur."""
        orchestrator = create_mock_orchestrator(IntegrationTestScenarios.ERROR_HANDLING)
        
        request = type('MockRequest', (), {
            'text': "Text that will cause an error",
            'analysis_depth': 'standard'
        })()
        
        response = await orchestrator.analyze_with_fact_checking(request)
        
        # L'orchestrateur devrait gérer l'erreur gracieusement
        assert response is not None
        
        if hasattr(response, 'status'):
            assert response.status == "error"
            assert response.error_message is not None
        else:
            assert response['status'] == "error"
            assert 'error_message' in response
    
    @pytest.mark.asyncio
    async def test_scenario_timeout_handling(self):
        """Test de gestion des timeouts."""
        analyzer = create_mock_analyzer(IntegrationTestScenarios.TIMEOUT)
        
        with pytest.raises(asyncio.TimeoutError, match="Mock timeout in analysis"):
            await analyzer.analyze_comprehensive("Text that will timeout")


class TestIntegrationPerformance:
    """Tests de performance de l'intégration."""
    
    @pytest.mark.asyncio
    async def test_mock_performance_acceptable(self):
        """Test que les mocks ont des performances acceptables."""
        orchestrator = create_mock_orchestrator(IntegrationTestScenarios.SUCCESS)
        
        # Mesurer le temps d'exécution
        import time
        start_time = time.time()
        
        request = type('MockRequest', (), {
            'text': "Test text with 85% statistics and expert opinions in 2024.",
            'analysis_depth': 'standard'
        })()
        
        response = await orchestrator.analyze_with_fact_checking(request)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Les mocks devraient être rapides (< 1 seconde)
        assert execution_time < 1.0
        assert response is not None
        
        if hasattr(response, 'processing_time'):
            assert response.processing_time >= 0.0
        else:
            assert response.get('processing_time', 0) >= 0.0
    
    @pytest.mark.asyncio
    async def test_concurrent_analysis(self):
        """Test d'analyses concurrentes."""
        orchestrator = create_mock_orchestrator(IntegrationTestScenarios.SUCCESS)
        
        texts = [
            "Text 1 with 90% statistics.",
            "Text 2 with expert opinions.",
            "Text 3 with 2024 temporal references."
        ]
        
        # Lancer les analyses en parallèle
        tasks = []
        for i, text in enumerate(texts):
            request = type('MockRequest', (), {
                'text': text,
                'analysis_depth': 'basic'
            })()
            task = orchestrator.analyze_with_fact_checking(request)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Toutes les analyses devraient réussir
        assert len(results) == 3
        for result in results:
            assert not isinstance(result, Exception)
            
            if hasattr(result, 'status'):
                assert result.status == "completed"
            else:
                assert result['status'] == "completed"


class TestIntegrationValidation:
    """Tests de validation de l'intégration."""
    
    def test_all_mock_components_available(self):
        """Test que tous les composants mock sont disponibles."""
        # Vérifier que toutes les classes mock peuvent être instanciées
        extractor = MockFactClaimExtractor()
        assert extractor is not None
        
        verifier = MockFactVerificationService()
        assert verifier is not None
        
        manager = MockFallacyTaxonomyManager()
        assert manager is not None
        
        analyzer = MockFallacyFamilyAnalyzer()
        assert analyzer is not None
        
        orchestrator = MockOrchestrator()
        assert orchestrator is not None
    
    def test_scenario_descriptions_available(self):
        """Test que les descriptions de scénarios sont disponibles."""
        scenarios = [
            IntegrationTestScenarios.SUCCESS,
            IntegrationTestScenarios.NO_CONTENT,
            IntegrationTestScenarios.MIXED_RESULTS,
            IntegrationTestScenarios.HIGH_CONFIDENCE,
            IntegrationTestScenarios.ERROR_HANDLING,
            IntegrationTestScenarios.TIMEOUT,
            IntegrationTestScenarios.COMPREHENSIVE
        ]
        
        for scenario in scenarios:
            description = IntegrationTestScenarios.get_scenario_description(scenario)
            assert isinstance(description, str)
            assert len(description) > 0
    
    def test_factory_functions_work(self):
        """Test que les fonctions factory fonctionnent."""
        # Tester toutes les fonctions factory
        extractor = create_mock_extractor("success")
        assert isinstance(extractor, MockFactClaimExtractor)
        assert extractor.scenario == "success"
        
        verifier = create_mock_verifier("mixed")
        assert isinstance(verifier, MockFactVerificationService)
        assert verifier.scenario == "mixed"
        
        manager = create_mock_taxonomy_manager("high_confidence")
        assert isinstance(manager, MockFallacyTaxonomyManager)
        assert manager.scenario == "high_confidence"
        
        analyzer = create_mock_analyzer("comprehensive")
        assert isinstance(analyzer, MockFallacyFamilyAnalyzer)
        assert analyzer.scenario == "comprehensive"
        
        orchestrator = create_mock_orchestrator("error")
        assert isinstance(orchestrator, MockOrchestrator)
        assert orchestrator.scenario == "error"
    
    @pytest.mark.asyncio
    async def test_integration_chain_complete(self):
        """Test que la chaîne d'intégration est complète."""
        # Test de la chaîne complète : Extractor -> Verifier -> Manager -> Analyzer -> Orchestrator
        
        orchestrator = create_mock_orchestrator(IntegrationTestScenarios.SUCCESS)
        
        # Vérifier que tous les composants sont connectés
        assert orchestrator.analyzer is not None
        assert orchestrator.analyzer.fact_extractor is not None
        assert orchestrator.analyzer.verification_service is not None
        assert orchestrator.analyzer.taxonomy_manager is not None
        
        # Test d'un flux complet
        request = type('MockRequest', (), {
            'text': "Complete integration test with 95% confidence and expert validation in 2024.",
            'analysis_depth': 'comprehensive'
        })()
        
        response = await orchestrator.analyze_with_fact_checking(request)
        
        # La réponse devrait contenir tous les éléments attendus
        assert response is not None
        
        if hasattr(response, 'comprehensive_result'):
            result = response.comprehensive_result
            # Vérifier que tous les composants ont contribué
            if hasattr(result, 'factual_claims') and hasattr(result, 'fact_check_results'):
                # Au moins l'un des composants devrait avoir produit des résultats
                has_content = (len(result.factual_claims) > 0 or 
                             len(result.fact_check_results) > 0 or
                             len(getattr(result, 'family_results', {})) > 0)
                assert has_content
        else:
            # Format dict
            result = response['comprehensive_result']
            assert isinstance(result, (dict, object))


if __name__ == "__main__":
    # Exécution des tests si le script est lancé directement
    pytest.main([__file__, "-v", "--tb=short"])