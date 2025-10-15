# -*- coding: utf-8 -*-
"""
Tests unitaires pour l'intégration du système de fact-checking et taxonomie des sophismes.

Ces tests valident le bon fonctionnement des nouveaux composants développés :
- FallacyTaxonomyManager
- FactClaimExtractor
- FactVerificationService
- FallacyFamilyAnalyzer
- FactCheckingOrchestrator
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from typing import List, Dict, Any

# Imports des composants à tester
try:
    from argumentation_analysis.services.fallacy_taxonomy_service import (
        FallacyTaxonomyManager,
        FallacyFamily,
        ClassifiedFallacy,
        get_taxonomy_manager,
    )
    from argumentation_analysis.agents.tools.analysis.fact_claim_extractor import (
        FactClaimExtractor,
        FactualClaim,
        ClaimType,
        ClaimVerifiability,
    )
    from argumentation_analysis.services.fact_verification_service import (
        FactVerificationService,
        VerificationStatus,
        SourceReliability,
    )
    from argumentation_analysis.agents.tools.analysis.fallacy_family_analyzer import (
        FallacyFamilyAnalyzer,
        AnalysisDepth,
        get_family_analyzer,
    )
    from argumentation_analysis.orchestration.fact_checking_orchestrator import (
        FactCheckingOrchestrator,
        FactCheckingRequest,
        get_fact_checking_orchestrator,
    )

    COMPONENTS_AVAILABLE = True
except ImportError as e:
    COMPONENTS_AVAILABLE = False
    IMPORT_ERROR = str(e)


class TestFallacyTaxonomyService:
    """Tests pour le service de taxonomie des sophismes."""

    @pytest.mark.skipif(
        not COMPONENTS_AVAILABLE,
        reason=f"Composants non disponibles: {IMPORT_ERROR if not COMPONENTS_AVAILABLE else ''}",
    )
    def test_fallacy_taxonomy_manager_initialization(self):
        """Test l'initialisation du gestionnaire de taxonomie."""
        with patch(
            "argumentation_analysis.services.fallacy_taxonomy_service.get_global_detector"
        ) as mock_detector:
            mock_detector.return_value = Mock()

            manager = FallacyTaxonomyManager()

            assert manager is not None
            assert len(manager.families) == 8  # 8 familles selon le PRD
            assert FallacyFamily.AUTHORITY_POPULARITY in manager.families
            assert FallacyFamily.EMOTIONAL_APPEALS in manager.families

    @pytest.mark.skipif(
        not COMPONENTS_AVAILABLE,
        reason=f"Composants non disponibles: {IMPORT_ERROR if not COMPONENTS_AVAILABLE else ''}",
    )
    def test_fallacy_family_enumeration(self):
        """Test l'énumération des familles de sophismes."""
        families = list(FallacyFamily)

        assert len(families) == 8
        expected_families = [
            "authority_popularity",
            "emotional_appeals",
            "generalization_causality",
            "diversion_attack",
            "false_dilemma_simplification",
            "language_ambiguity",
            "statistical_probabilistic",
            "audio_oral_context",
        ]

        family_values = [f.value for f in families]
        for expected in expected_families:
            assert expected in family_values

    @pytest.mark.skipif(
        not COMPONENTS_AVAILABLE,
        reason=f"Composants non disponibles: {IMPORT_ERROR if not COMPONENTS_AVAILABLE else ''}",
    )
    def test_classified_fallacy_creation(self):
        """Test la création d'un sophisme classifié."""
        fallacy = ClassifiedFallacy(
            taxonomy_key=123,
            name="Test Fallacy",
            nom_vulgarise="Sophisme de test",
            family=FallacyFamily.EMOTIONAL_APPEALS,
            confidence=0.8,
            description="Description de test",
            severity="Haute",
            context_relevance=0.7,
            family_pattern_score=0.6,
            detection_method="test",
        )

        assert fallacy.taxonomy_key == 123
        assert fallacy.family == FallacyFamily.EMOTIONAL_APPEALS
        assert fallacy.confidence == 0.8

        # Test de sérialisation
        fallacy_dict = fallacy.to_dict()
        assert fallacy_dict["family"] == "emotional_appeals"
        assert fallacy_dict["confidence"] == 0.8


class TestFactClaimExtractor:
    """Tests pour l'extracteur d'affirmations factuelles."""

    @pytest.mark.skipif(
        not COMPONENTS_AVAILABLE,
        reason=f"Composants non disponibles: {IMPORT_ERROR if not COMPONENTS_AVAILABLE else ''}",
    )
    def test_fact_claim_extractor_initialization(self):
        """Test l'initialisation de l'extracteur."""
        extractor = FactClaimExtractor()

        assert extractor is not None
        assert extractor.language == "fr"
        assert len(extractor.claim_patterns) > 0

    @pytest.mark.skipif(
        not COMPONENTS_AVAILABLE,
        reason=f"Composants non disponibles: {IMPORT_ERROR if not COMPONENTS_AVAILABLE else ''}",
    )
    def test_claim_type_enumeration(self):
        """Test l'énumération des types d'affirmations."""
        claim_types = list(ClaimType)

        expected_types = [
            "statistical",
            "historical",
            "scientific",
            "geographical",
            "biographical",
            "numerical",
            "temporal",
            "causal",
            "definitional",
            "quote",
        ]

        claim_type_values = [ct.value for ct in claim_types]
        for expected in expected_types:
            assert expected in claim_type_values

    @pytest.mark.skipif(
        not COMPONENTS_AVAILABLE,
        reason=f"Composants non disponibles: {IMPORT_ERROR if not COMPONENTS_AVAILABLE else ''}",
    )
    def test_factual_claim_creation(self):
        """Test la création d'une affirmation factuelle."""
        claim = FactualClaim(
            claim_text="En 2023, 75% des français utilisent internet.",
            claim_type=ClaimType.STATISTICAL,
            verifiability=ClaimVerifiability.HIGHLY_VERIFIABLE,
            confidence=0.9,
            context="Contexte de test",
            start_pos=0,
            end_pos=42,
            entities=[],
            keywords=["statistique", "internet"],
            temporal_references=["2023"],
            numerical_values=[{"value": 75.0, "unit": "%"}],
            sources_mentioned=[],
            extraction_method="test",
        )

        assert claim.claim_text.startswith("En 2023")
        assert claim.claim_type == ClaimType.STATISTICAL
        assert claim.verifiability == ClaimVerifiability.HIGHLY_VERIFIABLE
        assert "2023" in claim.temporal_references

        # Test de sérialisation
        claim_dict = claim.to_dict()
        assert claim_dict["claim_type"] == "statistical"
        assert claim_dict["confidence"] == 0.9

    @pytest.mark.skipif(
        not COMPONENTS_AVAILABLE,
        reason=f"Composants non disponibles: {IMPORT_ERROR if not COMPONENTS_AVAILABLE else ''}",
    )
    def test_extract_factual_claims_basic(self):
        """Test d'extraction basique d'affirmations."""
        extractor = FactClaimExtractor()
        text = "En 2024, 80% des entreprises utilisent l'IA. Paris est la capitale de la France."

        claims = extractor.extract_factual_claims(text, max_claims=5)

        assert isinstance(claims, list)
        # Nous ne pouvons pas garantir le nombre exact sans le vrai système NLP
        # mais nous pouvons vérifier que la méthode fonctionne
        for claim in claims:
            assert isinstance(claim, FactualClaim)
            assert claim.claim_text
            assert claim.confidence >= 0.0


class TestFactVerificationService:
    """Tests pour le service de vérification factuelle."""

    @pytest.mark.skipif(
        not COMPONENTS_AVAILABLE,
        reason=f"Composants non disponibles: {IMPORT_ERROR if not COMPONENTS_AVAILABLE else ''}",
    )
    def test_fact_verification_service_initialization(self):
        """Test l'initialisation du service de vérification."""
        service = FactVerificationService()

        assert service is not None
        assert hasattr(service, "source_reliability_map")
        assert len(service.source_reliability_map) > 0

    @pytest.mark.skipif(
        not COMPONENTS_AVAILABLE,
        reason=f"Composants non disponibles: {IMPORT_ERROR if not COMPONENTS_AVAILABLE else ''}",
    )
    def test_verification_status_enumeration(self):
        """Test l'énumération des statuts de vérification."""
        statuses = list(VerificationStatus)

        expected_statuses = [
            "verified_true",
            "verified_false",
            "partially_true",
            "disputed",
            "unverifiable",
            "insufficient_info",
            "error",
        ]

        status_values = [s.value for s in statuses]
        for expected in expected_statuses:
            assert expected in status_values

    @pytest.mark.skipif(
        not COMPONENTS_AVAILABLE,
        reason=f"Composants non disponibles: {IMPORT_ERROR if not COMPONENTS_AVAILABLE else ''}",
    )
    def test_source_reliability_assessment(self):
        """Test l'évaluation de la fiabilité des sources."""
        service = FactVerificationService()

        # Test source hautement fiable
        reliability = service._assess_source_reliability("wikipedia.org")
        assert reliability == SourceReliability.HIGHLY_RELIABLE

        # Test source modérément fiable
        reliability = service._assess_source_reliability("lefigaro.fr")
        assert reliability == SourceReliability.MODERATELY_RELIABLE

        # Test source inconnue
        reliability = service._assess_source_reliability("unknown-domain.com")
        assert reliability == SourceReliability.UNKNOWN

    @pytest.mark.skipif(
        not COMPONENTS_AVAILABLE,
        reason=f"Composants non disponibles: {IMPORT_ERROR if not COMPONENTS_AVAILABLE else ''}",
    )
    @pytest.mark.asyncio
    async def test_verify_claim_simulation(self):
        """Test de vérification d'affirmation (mode simulation)."""
        service = FactVerificationService()

        # Créer une affirmation test
        claim = FactualClaim(
            claim_text="Test claim",
            claim_type=ClaimType.SCIENTIFIC,
            verifiability=ClaimVerifiability.MODERATELY_VERIFIABLE,
            confidence=0.7,
            context="Test context",
            start_pos=0,
            end_pos=10,
            entities=[],
            keywords=[],
            temporal_references=[],
            numerical_values=[],
            sources_mentioned=[],
            extraction_method="test",
        )

        # Vérifier (utilisera la simulation)
        result = await service.verify_claim(claim)

        assert result is not None
        assert result.claim == claim
        assert isinstance(result.status, VerificationStatus)
        assert result.confidence >= 0.0
        assert result.verification_date is not None


class TestFallacyFamilyAnalyzer:
    """Tests pour l'analyseur par famille de sophismes."""

    @pytest.mark.skipif(
        not COMPONENTS_AVAILABLE,
        reason=f"Composants non disponibles: {IMPORT_ERROR if not COMPONENTS_AVAILABLE else ''}",
    )
    def test_fallacy_family_analyzer_initialization(self):
        """Test l'initialisation de l'analyseur."""
        with patch(
            "argumentation_analysis.agents.tools.analysis.fallacy_family_analyzer.get_taxonomy_manager"
        ) as mock_manager, patch(
            "argumentation_analysis.agents.tools.analysis.fallacy_family_analyzer.FactClaimExtractor"
        ) as mock_extractor, patch(
            "argumentation_analysis.agents.tools.analysis.fallacy_family_analyzer.get_verification_service"
        ) as mock_verifier:
            mock_manager.return_value = Mock()
            mock_extractor.return_value = Mock()
            mock_verifier.return_value = Mock()

            analyzer = FallacyFamilyAnalyzer()

            assert analyzer is not None
            assert analyzer.taxonomy_manager is not None
            assert analyzer.fact_extractor is not None
            assert analyzer.fact_verifier is not None

    @pytest.mark.skipif(
        not COMPONENTS_AVAILABLE,
        reason=f"Composants non disponibles: {IMPORT_ERROR if not COMPONENTS_AVAILABLE else ''}",
    )
    def test_analysis_depth_enumeration(self):
        """Test l'énumération des profondeurs d'analyse."""
        depths = list(AnalysisDepth)

        expected_depths = ["basic", "standard", "comprehensive", "expert"]
        depth_values = [d.value for d in depths]

        for expected in expected_depths:
            assert expected in depth_values


class TestFactCheckingOrchestrator:
    """Tests pour l'orchestrateur de fact-checking."""

    @pytest.mark.skipif(
        not COMPONENTS_AVAILABLE,
        reason=f"Composants non disponibles: {IMPORT_ERROR if not COMPONENTS_AVAILABLE else ''}",
    )
    def test_fact_checking_orchestrator_initialization(self):
        """Test l'initialisation de l'orchestrateur."""
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

            assert orchestrator is not None
            assert orchestrator.fact_extractor is not None
            assert orchestrator.verification_service is not None
            assert orchestrator.taxonomy_manager is not None
            assert orchestrator.family_analyzer is not None

    @pytest.mark.skipif(
        not COMPONENTS_AVAILABLE,
        reason=f"Composants non disponibles: {IMPORT_ERROR if not COMPONENTS_AVAILABLE else ''}",
    )
    def test_fact_checking_request_creation(self):
        """Test la création d'une requête de fact-checking."""
        request = FactCheckingRequest(
            text="Texte de test",
            analysis_depth=AnalysisDepth.STANDARD,
            enable_fact_checking=True,
            max_claims=10,
        )

        assert request.text == "Texte de test"
        assert request.analysis_depth == AnalysisDepth.STANDARD
        assert request.enable_fact_checking is True
        assert request.max_claims == 10

    @pytest.mark.skipif(
        not COMPONENTS_AVAILABLE,
        reason=f"Composants non disponibles: {IMPORT_ERROR if not COMPONENTS_AVAILABLE else ''}",
    )
    @pytest.mark.asyncio
    async def test_quick_fact_check(self):
        """Test de fact-checking rapide."""
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
            mock_extractor_instance.extract_factual_claims.return_value = []

            mock_verifier.return_value = Mock()
            mock_manager.return_value = Mock()
            mock_analyzer.return_value = Mock()

            orchestrator = FactCheckingOrchestrator()

            result = await orchestrator.quick_fact_check(
                "Texte sans affirmations factuelles", max_claims=5
            )

            assert result is not None
            assert result["status"] == "no_claims"
            assert "processing_time" in result

    @pytest.mark.skipif(
        not COMPONENTS_AVAILABLE,
        reason=f"Composants non disponibles: {IMPORT_ERROR if not COMPONENTS_AVAILABLE else ''}",
    )
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test du contrôle de santé de l'orchestrateur."""
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
            mock_extractor_instance.extract_factual_claims.return_value = []

            mock_manager_instance = Mock()
            mock_manager.return_value = mock_manager_instance
            mock_manager_instance.detect_fallacies_with_families.return_value = []

            mock_verifier.return_value = Mock()
            mock_analyzer.return_value = Mock()

            orchestrator = FactCheckingOrchestrator()

            health = await orchestrator.health_check()

            assert health is not None
            assert "status" in health
            assert "components" in health
            assert "fact_extractor" in health["components"]
            assert "taxonomy_manager" in health["components"]


class TestIntegrationFunctionality:
    """Tests d'intégration des fonctionnalités."""

    @pytest.mark.skipif(
        not COMPONENTS_AVAILABLE,
        reason=f"Composants non disponibles: {IMPORT_ERROR if not COMPONENTS_AVAILABLE else ''}",
    )
    def test_singleton_pattern_taxonomy_manager(self):
        """Test du pattern singleton pour le gestionnaire de taxonomie."""
        with patch(
            "argumentation_analysis.services.fallacy_taxonomy_service.get_global_detector"
        ) as mock_detector:
            mock_detector.return_value = Mock()

            manager1 = get_taxonomy_manager()
            manager2 = get_taxonomy_manager()

            # Devrait retourner la même instance
            assert manager1 is manager2

    @pytest.mark.skipif(
        not COMPONENTS_AVAILABLE,
        reason=f"Composants non disponibles: {IMPORT_ERROR if not COMPONENTS_AVAILABLE else ''}",
    )
    def test_singleton_pattern_family_analyzer(self):
        """Test du pattern singleton pour l'analyseur par famille."""
        with patch(
            "argumentation_analysis.agents.tools.analysis.fallacy_family_analyzer.get_taxonomy_manager"
        ) as mock_manager, patch(
            "argumentation_analysis.agents.tools.analysis.fallacy_family_analyzer.FactClaimExtractor"
        ) as mock_extractor, patch(
            "argumentation_analysis.agents.tools.analysis.fallacy_family_analyzer.get_verification_service"
        ) as mock_verifier:
            mock_manager.return_value = Mock()
            mock_extractor.return_value = Mock()
            mock_verifier.return_value = Mock()

            analyzer1 = get_family_analyzer()
            analyzer2 = get_family_analyzer()

            # Devrait retourner la même instance
            assert analyzer1 is analyzer2

    @pytest.mark.skipif(
        not COMPONENTS_AVAILABLE,
        reason=f"Composants non disponibles: {IMPORT_ERROR if not COMPONENTS_AVAILABLE else ''}",
    )
    def test_singleton_pattern_fact_checking_orchestrator(self):
        """Test du pattern singleton pour l'orchestrateur de fact-checking."""
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

            orchestrator1 = get_fact_checking_orchestrator()
            orchestrator2 = get_fact_checking_orchestrator()

            # Devrait retourner la même instance
            assert orchestrator1 is orchestrator2


# Tests de performance (optionnels)
class TestPerformance:
    """Tests de performance pour les nouveaux composants."""

    @pytest.mark.skipif(
        not COMPONENTS_AVAILABLE,
        reason=f"Composants non disponibles: {IMPORT_ERROR if not COMPONENTS_AVAILABLE else ''}",
    )
    def test_fact_extraction_performance(self):
        """Test de performance de l'extraction d'affirmations."""
        extractor = FactClaimExtractor()

        # Texte de test relativement long
        long_text = "En 2024, 80% des entreprises utilisent l'IA. " * 100

        import time

        start_time = time.time()
        claims = extractor.extract_factual_claims(long_text, max_claims=10)
        end_time = time.time()

        processing_time = end_time - start_time

        # L'extraction devrait prendre moins de 10 secondes
        assert processing_time < 10.0
        assert isinstance(claims, list)

    @pytest.mark.skipif(
        not COMPONENTS_AVAILABLE,
        reason=f"Composants non disponibles: {IMPORT_ERROR if not COMPONENTS_AVAILABLE else ''}",
    )
    def test_taxonomy_manager_performance(self):
        """Test de performance du gestionnaire de taxonomie."""
        with patch(
            "argumentation_analysis.services.fallacy_taxonomy_service.get_global_detector"
        ) as mock_detector:
            mock_detector.return_value = Mock()
            mock_detector.return_value.detect_sophisms_from_taxonomy.return_value = []

            manager = FallacyTaxonomyManager()

            # Test de classification multiple
            test_text = "Ceci est un argument fallacieux avec appel à l'autorité. " * 50

            import time

            start_time = time.time()
            fallacies = manager.detect_fallacies_with_families(
                test_text, max_fallacies=10
            )
            end_time = time.time()

            processing_time = end_time - start_time

            # La classification devrait prendre moins de 5 secondes
            assert processing_time < 5.0
            assert isinstance(fallacies, list)


if __name__ == "__main__":
    # Exécution des tests si le script est lancé directement
    pytest.main([__file__, "-v"])
