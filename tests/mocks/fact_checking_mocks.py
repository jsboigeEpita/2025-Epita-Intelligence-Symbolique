# -*- coding: utf-8 -*-
"""
Mocks pour tester l'intégration du système de fact-checking.

Ces mocks permettent de tester l'intégration sans dépendance aux APIs externes
et avec des données contrôlées pour valider le bon fonctionnement du système.
"""

import asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import random

# Import des types nécessaires pour les mocks
try:
    from argumentation_analysis.agents.tools.analysis.fact_claim_extractor import (
        FactualClaim,
        ClaimType,
        ClaimVerifiability,
    )
    from argumentation_analysis.services.fact_verification_service import (
        FactVerificationResult,
        VerificationStatus,
        VerificationSource,
        SourceReliability,
    )
    from argumentation_analysis.services.fallacy_taxonomy_service import (
        FallacyFamily,
        ClassifiedFallacy,
    )
    from argumentation_analysis.agents.tools.analysis.fallacy_family_analyzer import (
        ComprehensiveAnalysisResult,
        FamilyAnalysisResult,
        AnalysisDepth,
    )

    TYPES_AVAILABLE = True
except ImportError:
    TYPES_AVAILABLE = False


class MockFactClaimExtractor:
    """Mock de l'extracteur d'affirmations factuelles."""

    def __init__(self, scenario: str = "success"):
        """
        Initialise le mock avec différents scénarios.

        :param scenario: Type de scénario ("success", "no_claims", "error", "mixed")
        """
        self.scenario = scenario
        self.call_count = 0

    def extract_factual_claims(self, text: str, max_claims: int = 20) -> List[Any]:
        """Mock d'extraction d'affirmations factuelles."""
        self.call_count += 1

        if self.scenario == "error":
            raise Exception("Mock error in claim extraction")

        if self.scenario == "no_claims":
            return []

        # Données de test basées sur le contenu du texte
        claims = []

        if "85%" in text or "pourcentage" in text.lower():
            if TYPES_AVAILABLE:
                claims.append(
                    FactualClaim(
                        claim_text="85% des entreprises utilisent l'IA",
                        claim_type=ClaimType.STATISTICAL,
                        verifiability=ClaimVerifiability.HIGHLY_VERIFIABLE,
                        confidence=0.9,
                        context=text[:100],
                        start_pos=text.find("85%") if "85%" in text else 0,
                        end_pos=(text.find("85%") + 20) if "85%" in text else 20,
                        entities=[{"text": "85%", "label": "PERCENT"}],
                        keywords=["statistique", "entreprises", "IA"],
                        temporal_references=["2024"],
                        numerical_values=[{"value": 85.0, "unit": "%"}],
                        sources_mentioned=[],
                        extraction_method="mock_statistical",
                    )
                )
            else:
                claims.append(
                    {
                        "claim_text": "85% des entreprises utilisent l'IA",
                        "claim_type": "statistical",
                        "confidence": 0.9,
                        "extraction_method": "mock_statistical",
                    }
                )

        if "2024" in text:
            if TYPES_AVAILABLE:
                claims.append(
                    FactualClaim(
                        claim_text="En 2024",
                        claim_type=ClaimType.TEMPORAL,
                        verifiability=ClaimVerifiability.MODERATELY_VERIFIABLE,
                        confidence=0.8,
                        context=text[:100],
                        start_pos=text.find("2024") if "2024" in text else 0,
                        end_pos=(text.find("2024") + 10) if "2024" in text else 10,
                        entities=[{"text": "2024", "label": "DATE"}],
                        keywords=["année", "temporel"],
                        temporal_references=["2024"],
                        numerical_values=[{"value": 2024.0, "unit": "année"}],
                        sources_mentioned=[],
                        extraction_method="mock_temporal",
                    )
                )
            else:
                claims.append(
                    {
                        "claim_text": "En 2024",
                        "claim_type": "temporal",
                        "confidence": 0.8,
                        "extraction_method": "mock_temporal",
                    }
                )

        if "expert" in text.lower() or "étude" in text.lower():
            if TYPES_AVAILABLE:
                claims.append(
                    FactualClaim(
                        claim_text="selon les experts",
                        claim_type=ClaimType.SCIENTIFIC,
                        verifiability=ClaimVerifiability.PARTIALLY_VERIFIABLE,
                        confidence=0.6,
                        context=text[:100],
                        start_pos=0,
                        end_pos=20,
                        entities=[{"text": "experts", "label": "PERSON"}],
                        keywords=["expert", "autorité"],
                        temporal_references=[],
                        numerical_values=[],
                        sources_mentioned=["experts"],
                        extraction_method="mock_scientific",
                    )
                )
            else:
                claims.append(
                    {
                        "claim_text": "selon les experts",
                        "claim_type": "scientific",
                        "confidence": 0.6,
                        "extraction_method": "mock_scientific",
                    }
                )

        if self.scenario == "mixed" and len(claims) == 0:
            # Générer des claims aléatoires pour tester
            claims = self._generate_random_claims(text, 2)

        return claims[:max_claims]

    def _generate_random_claims(self, text: str, count: int) -> List[Any]:
        """Génère des claims aléatoires pour les tests."""
        claims = []
        claim_types = ["statistical", "historical", "scientific", "numerical"]

        for i in range(count):
            if TYPES_AVAILABLE:
                claims.append(
                    FactualClaim(
                        claim_text=f"Mock claim {i+1}",
                        claim_type=ClaimType(random.choice(claim_types)),
                        verifiability=ClaimVerifiability.MODERATELY_VERIFIABLE,
                        confidence=random.uniform(0.5, 0.9),
                        context=text[:50] + "...",
                        start_pos=i * 10,
                        end_pos=(i * 10) + 15,
                        entities=[],
                        keywords=[f"keyword{i}"],
                        temporal_references=[],
                        numerical_values=[],
                        sources_mentioned=[],
                        extraction_method="mock_random",
                    )
                )
            else:
                claims.append(
                    {
                        "claim_text": f"Mock claim {i+1}",
                        "claim_type": random.choice(claim_types),
                        "confidence": random.uniform(0.5, 0.9),
                        "extraction_method": "mock_random",
                    }
                )

        return claims


class MockFactVerificationService:
    """Mock du service de vérification factuelle."""

    def __init__(self, scenario: str = "success"):
        """
        Initialise le mock avec différents scénarios.

        :param scenario: Type de scénario ("success", "all_false", "mixed", "error", "timeout")
        """
        self.scenario = scenario
        self.call_count = 0
        self.verification_history = []

    async def verify_claim(self, claim: Any) -> Any:
        """Mock de vérification d'une affirmation."""
        self.call_count += 1
        claim_text = getattr(claim, "claim_text", str(claim))

        self.verification_history.append(
            {
                "claim": claim_text,
                "timestamp": datetime.now(),
                "scenario": self.scenario,
            }
        )

        if self.scenario == "error":
            raise Exception("Mock error in fact verification")

        if self.scenario == "timeout":
            await asyncio.sleep(0.1)  # Simuler un timeout rapide
            raise asyncio.TimeoutError("Mock timeout in verification")

        # Simuler un délai de traitement
        await asyncio.sleep(0.05)

        # Déterminer le statut basé sur le scénario et le contenu
        status = self._determine_mock_status(claim_text)
        confidence = self._calculate_mock_confidence(claim_text, status)

        # Créer des sources mockées
        sources = self._create_mock_sources(claim_text, status)

        if TYPES_AVAILABLE:
            return FactVerificationResult(
                claim=claim,
                status=status,
                confidence=confidence,
                verdict=self._generate_verdict(status, confidence),
                explanation=self._generate_explanation(status, claim_text),
                sources=sources,
                supporting_sources=len([s for s in sources if s.supports_claim]),
                contradicting_sources=len([s for s in sources if s.contradicts_claim]),
                neutral_sources=len(
                    [
                        s
                        for s in sources
                        if not s.supports_claim and not s.contradicts_claim
                    ]
                ),
                verification_date=datetime.now(),
                processing_time=random.uniform(0.5, 2.0),
                fallacy_implications=self._generate_fallacy_implications(
                    claim_text, status
                ),
            )
        else:
            return {
                "status": status.value if hasattr(status, "value") else status,
                "confidence": confidence,
                "verdict": self._generate_verdict(status, confidence),
                "sources_count": len(sources),
                "processing_time": random.uniform(0.5, 2.0),
            }

    async def verify_multiple_claims(self, claims: List[Any]) -> List[Any]:
        """Mock de vérification multiple."""
        results = []
        for claim in claims:
            try:
                result = await self.verify_claim(claim)
                results.append(result)
            except Exception as e:
                # Créer un résultat d'erreur
                if TYPES_AVAILABLE:
                    error_result = FactVerificationResult(
                        claim=claim,
                        status=VerificationStatus.ERROR,
                        confidence=0.0,
                        verdict="Erreur de vérification",
                        explanation=str(e),
                        sources=[],
                        supporting_sources=0,
                        contradicting_sources=0,
                        neutral_sources=0,
                        verification_date=datetime.now(),
                        processing_time=0.0,
                        fallacy_implications=[],
                    )
                    results.append(error_result)
                else:
                    results.append(
                        {"status": "error", "confidence": 0.0, "error": str(e)}
                    )

        return results

    def _determine_mock_status(self, claim_text: str):
        """Détermine le statut mock basé sur le contenu."""
        if self.scenario == "all_false":
            return (
                VerificationStatus.VERIFIED_FALSE
                if TYPES_AVAILABLE
                else "verified_false"
            )

        if self.scenario == "mixed":
            # Alterner les statuts
            statuses = ["verified_true", "verified_false", "disputed", "partially_true"]
            status_str = statuses[self.call_count % len(statuses)]
            return VerificationStatus(status_str) if TYPES_AVAILABLE else status_str

        # Logique basée sur le contenu pour le scénario "success"
        if "85%" in claim_text:
            return (
                VerificationStatus.VERIFIED_TRUE if TYPES_AVAILABLE else "verified_true"
            )
        elif "expert" in claim_text.lower():
            return (
                VerificationStatus.PARTIALLY_TRUE
                if TYPES_AVAILABLE
                else "partially_true"
            )
        elif "2024" in claim_text:
            return (
                VerificationStatus.VERIFIED_TRUE if TYPES_AVAILABLE else "verified_true"
            )
        else:
            return VerificationStatus.DISPUTED if TYPES_AVAILABLE else "disputed"

    def _calculate_mock_confidence(self, claim_text: str, status) -> float:
        """Calcule la confiance mock."""
        status_str = status.value if hasattr(status, "value") else status

        base_confidence = {
            "verified_true": 0.9,
            "verified_false": 0.8,
            "partially_true": 0.6,
            "disputed": 0.4,
            "unverifiable": 0.2,
        }.get(status_str, 0.5)

        # Ajuster basé sur le contenu
        if "%" in claim_text:
            base_confidence += 0.1
        if len(claim_text) > 50:
            base_confidence -= 0.1

        return max(0.0, min(1.0, base_confidence))

    def _create_mock_sources(self, claim_text: str, status) -> List[Any]:
        """Crée des sources mockées."""
        sources = []
        status_str = status.value if hasattr(status, "value") else status

        # Sources fiables qui supportent
        if status_str in ["verified_true", "partially_true"]:
            if TYPES_AVAILABLE:
                sources.append(
                    VerificationSource(
                        url="https://mock-reliable-source.com/article",
                        title=f"Étude confirme: {claim_text[:30]}...",
                        snippet=f"Nos recherches confirment que {claim_text}",
                        reliability=SourceReliability.HIGHLY_RELIABLE,
                        relevance_score=0.9,
                        publication_date=datetime.now() - timedelta(days=30),
                        domain="mock-reliable-source.com",
                        supports_claim=True,
                        contradicts_claim=False,
                    )
                )
            else:
                sources.append(
                    {
                        "url": "https://mock-reliable-source.com/article",
                        "title": f"Étude confirme: {claim_text[:30]}...",
                        "reliability": "highly_reliable",
                        "supports_claim": True,
                    }
                )

        # Sources qui contredisent
        if status_str in ["verified_false", "disputed"]:
            if TYPES_AVAILABLE:
                sources.append(
                    VerificationSource(
                        url="https://mock-counter-source.com/analysis",
                        title=f"Analyse critique: {claim_text[:30]}...",
                        snippet=f"Nos données montrent que {claim_text} est inexact",
                        reliability=SourceReliability.MODERATELY_RELIABLE,
                        relevance_score=0.8,
                        publication_date=datetime.now() - timedelta(days=15),
                        domain="mock-counter-source.com",
                        supports_claim=False,
                        contradicts_claim=True,
                    )
                )
            else:
                sources.append(
                    {
                        "url": "https://mock-counter-source.com/analysis",
                        "title": f"Analyse critique: {claim_text[:30]}...",
                        "reliability": "moderately_reliable",
                        "contradicts_claim": True,
                    }
                )

        return sources

    def _generate_verdict(self, status, confidence: float) -> str:
        """Génère un verdict mock."""
        status_str = status.value if hasattr(status, "value") else status

        verdicts = {
            "verified_true": f"Affirmation confirmée (confiance: {confidence:.2f})",
            "verified_false": f"Affirmation réfutée (confiance: {confidence:.2f})",
            "partially_true": f"Affirmation partiellement vraie (confiance: {confidence:.2f})",
            "disputed": f"Affirmation controversée (confiance: {confidence:.2f})",
            "unverifiable": "Impossible à vérifier avec les sources disponibles",
        }

        return verdicts.get(status_str, "Statut de vérification indéterminé")

    def _generate_explanation(self, status, claim_text: str) -> str:
        """Génère une explication mock."""
        status_str = status.value if hasattr(status, "value") else status

        if status_str == "verified_true":
            return (
                f"Plusieurs sources fiables confirment que '{claim_text}' est exacte."
            )
        elif status_str == "verified_false":
            return (
                f"Les sources consultées indiquent que '{claim_text}' est incorrecte."
            )
        elif status_str == "disputed":
            return (
                f"Les sources présentent des avis contradictoires sur '{claim_text}'."
            )
        else:
            return f"Statut de vérification: {status_str} pour '{claim_text}'"

    def _generate_fallacy_implications(
        self, claim_text: str, status
    ) -> List[Dict[str, Any]]:
        """Génère des implications de sophismes mock."""
        status_str = status.value if hasattr(status, "value") else status
        implications = []

        if status_str == "verified_false":
            if "expert" in claim_text.lower():
                implications.append(
                    {
                        "fallacy_family": "authority_popularity",
                        "potential_fallacy": "Appel à une autorité non fiable",
                        "confidence": 0.8,
                        "explanation": "L'affirmation cite des experts mais s'avère factuellement incorrecte",
                    }
                )

            if "%" in claim_text:
                implications.append(
                    {
                        "fallacy_family": "statistical_probabilistic",
                        "potential_fallacy": "Utilisation de statistiques incorrectes",
                        "confidence": 0.9,
                        "explanation": "Les données statistiques présentées ne sont pas supportées par des sources fiables",
                    }
                )

        return implications


class MockFallacyTaxonomyManager:
    """Mock du gestionnaire de taxonomie des sophismes."""

    def __init__(self, scenario: str = "success"):
        """
        Initialise le mock avec différents scénarios.

        :param scenario: Type de scénario ("success", "no_fallacies", "high_confidence", "error")
        """
        self.scenario = scenario
        self.call_count = 0

    def detect_fallacies_with_families(
        self, text: str, max_fallacies: int = 20
    ) -> List[Any]:
        """Mock de détection de sophismes avec familles."""
        self.call_count += 1

        if self.scenario == "error":
            raise Exception("Mock error in fallacy detection")

        if self.scenario == "no_fallacies":
            return []

        fallacies = []

        # Détection basée sur le contenu
        if "expert" in text.lower() or "autorité" in text.lower():
            if TYPES_AVAILABLE:
                fallacies.append(
                    ClassifiedFallacy(
                        taxonomy_key=101,
                        name="Argumentum ad Verecundiam",
                        nom_vulgarise="Appel à l'autorité",
                        family=FallacyFamily.AUTHORITY_POPULARITY,
                        confidence=0.8 if self.scenario != "high_confidence" else 0.95,
                        description="Invocation d'une autorité pour soutenir un argument",
                        severity="Moyenne",
                        context_relevance=0.7,
                        family_pattern_score=0.8,
                        detection_method="mock_authority",
                    )
                )
            else:
                fallacies.append(
                    {
                        "name": "Appel à l'autorité",
                        "family": "authority_popularity",
                        "confidence": 0.8,
                        "detection_method": "mock_authority",
                    }
                )

        if "peur" in text.lower() or "danger" in text.lower():
            if TYPES_AVAILABLE:
                fallacies.append(
                    ClassifiedFallacy(
                        taxonomy_key=201,
                        name="Argumentum ad Metum",
                        nom_vulgarise="Appel à la peur",
                        family=FallacyFamily.EMOTIONAL_APPEALS,
                        confidence=0.7 if self.scenario != "high_confidence" else 0.9,
                        description="Utilisation de la peur pour persuader",
                        severity="Haute",
                        context_relevance=0.8,
                        family_pattern_score=0.7,
                        detection_method="mock_emotional",
                    )
                )
            else:
                fallacies.append(
                    {
                        "name": "Appel à la peur",
                        "family": "emotional_appeals",
                        "confidence": 0.7,
                        "detection_method": "mock_emotional",
                    }
                )

        if "tous" in text.lower() and (
            "sont" in text.lower() or "font" in text.lower()
        ):
            if TYPES_AVAILABLE:
                fallacies.append(
                    ClassifiedFallacy(
                        taxonomy_key=301,
                        name="Généralisation hâtive",
                        nom_vulgarise="Généralisation abusive",
                        family=FallacyFamily.GENERALIZATION_CAUSALITY,
                        confidence=0.6 if self.scenario != "high_confidence" else 0.85,
                        description="Généralisation basée sur un échantillon insuffisant",
                        severity="Moyenne",
                        context_relevance=0.6,
                        family_pattern_score=0.6,
                        detection_method="mock_generalization",
                    )
                )
            else:
                fallacies.append(
                    {
                        "name": "Généralisation hâtive",
                        "family": "generalization_causality",
                        "confidence": 0.6,
                        "detection_method": "mock_generalization",
                    }
                )

        # Pour le scénario high_confidence, ajouter plus de sophismes
        if self.scenario == "high_confidence" and len(fallacies) < 2:
            if TYPES_AVAILABLE:
                fallacies.append(
                    ClassifiedFallacy(
                        taxonomy_key=401,
                        name="Argumentum ad Hominem",
                        nom_vulgarise="Attaque personnelle",
                        family=FallacyFamily.DIVERSION_ATTACK,
                        confidence=0.9,
                        description="Attaque de la personne plutôt que de l'argument",
                        severity="Moyenne",
                        context_relevance=0.8,
                        family_pattern_score=0.9,
                        detection_method="mock_attack",
                    )
                )
            else:
                fallacies.append(
                    {
                        "name": "Attaque personnelle",
                        "family": "diversion_attack",
                        "confidence": 0.9,
                        "detection_method": "mock_attack",
                    }
                )

        return fallacies[:max_fallacies]

    def get_family_statistics(self, classified_fallacies: List[Any]) -> Dict[str, Any]:
        """Mock des statistiques par famille."""
        if not classified_fallacies:
            return {}

        stats = {}
        families_present = set()

        for fallacy in classified_fallacies:
            if hasattr(fallacy, "family"):
                family = (
                    fallacy.family.value
                    if hasattr(fallacy.family, "value")
                    else fallacy.family
                )
            else:
                family = fallacy.get("family", "unknown")

            families_present.add(family)

        for family in families_present:
            count = len(
                [
                    f
                    for f in classified_fallacies
                    if (hasattr(f, "family") and f.family.value == family)
                    or (isinstance(f, dict) and f.get("family") == family)
                ]
            )

            stats[family] = {
                "count": count,
                "percentage": (count / len(classified_fallacies)) * 100,
                "present": True,
                "average_confidence": 0.7 + (count * 0.1),  # Mock calculation
            }

        return stats


class MockFallacyFamilyAnalyzer:
    """Mock de l'analyseur par famille de sophismes."""

    def __init__(self, scenario: str = "success"):
        """
        Initialise le mock avec différents scénarios.

        :param scenario: Type de scénario ("success", "comprehensive", "error", "timeout")
        """
        self.scenario = scenario
        self.call_count = 0

        # Initialiser les mocks des composants
        self.fact_extractor = MockFactClaimExtractor(scenario)
        self.verification_service = MockFactVerificationService(scenario)
        self.taxonomy_manager = MockFallacyTaxonomyManager(scenario)

    async def analyze_comprehensive(self, text: str, depth=None) -> Any:
        """Mock d'analyse complète."""
        self.call_count += 1

        if self.scenario == "error":
            raise Exception("Mock error in comprehensive analysis")

        if self.scenario == "timeout":
            await asyncio.sleep(0.1)
            raise asyncio.TimeoutError("Mock timeout in analysis")

        # Simuler le processus d'analyse
        start_time = datetime.now()

        # 1. Extraction des claims
        factual_claims = self.fact_extractor.extract_factual_claims(text, max_claims=10)

        # 2. Vérification factuelle
        fact_check_results = []
        if factual_claims:
            fact_check_results = await self.verification_service.verify_multiple_claims(
                factual_claims
            )

        # 3. Détection des sophismes
        classified_fallacies = self.taxonomy_manager.detect_fallacies_with_families(
            text, max_fallacies=10
        )

        # 4. Génération du résultat
        if TYPES_AVAILABLE:
            # Simuler les résultats par famille
            family_results = {}
            if classified_fallacies:
                for fallacy in classified_fallacies:
                    family = fallacy.family
                    if family not in family_results:
                        family_results[family] = FamilyAnalysisResult(
                            family=family,
                            fallacies_detected=[fallacy],
                            family_score=0.7,
                            severity_assessment="Moyenne",
                            fact_check_integration={"relevant_fact_checks": 1},
                            contextual_relevance=0.8,
                            strategic_patterns=[],
                            recommendations=[f"Attention aux {family.value}"],
                        )

            result = ComprehensiveAnalysisResult(
                text_analyzed=text,
                analysis_timestamp=start_time,
                analysis_depth=depth or AnalysisDepth.STANDARD,
                family_results=family_results,
                factual_claims=factual_claims,
                fact_check_results=[
                    r.to_dict() if hasattr(r, "to_dict") else r
                    for r in fact_check_results
                ],
                overall_assessment={
                    "total_families_detected": len(family_results),
                    "total_fallacies": len(classified_fallacies),
                    "overall_severity": "Moyenne",
                    "credibility_score": 0.7,
                },
                strategic_insights={
                    "argumentation_strategy": "Mock strategy",
                    "sophistication_level": "Standard",
                },
                recommendations=[
                    "Vérifier les sources",
                    "Analyser la logique des arguments",
                ],
            )
        else:
            result = {
                "text_analyzed": text[:100] + "...",
                "analysis_timestamp": start_time.isoformat(),
                "factual_claims": len(factual_claims),
                "fact_check_results": len(fact_check_results),
                "fallacies_detected": len(classified_fallacies),
                "overall_assessment": {
                    "total_fallacies": len(classified_fallacies),
                    "credibility_score": 0.7,
                },
            }

        # Simuler un délai de traitement
        if self.scenario == "comprehensive":
            await asyncio.sleep(0.2)
        else:
            await asyncio.sleep(0.05)

        return result


class IntegrationTestScenarios:
    """Scénarios de test pour valider l'intégration."""

    SUCCESS = "success"
    NO_CONTENT = "no_content"
    MIXED_RESULTS = "mixed"
    HIGH_CONFIDENCE = "high_confidence"
    ERROR_HANDLING = "error"
    TIMEOUT = "timeout"
    COMPREHENSIVE = "comprehensive"

    @staticmethod
    def get_scenario_description(scenario: str) -> str:
        """Retourne la description d'un scénario."""
        descriptions = {
            "success": "Scénario de succès avec résultats normaux",
            "no_content": "Aucun contenu détecté (claims ou sophismes)",
            "mixed": "Résultats mixtes avec différents statuts",
            "high_confidence": "Résultats avec confiance élevée",
            "error": "Erreurs dans les composants",
            "timeout": "Timeouts dans les opérations",
            "comprehensive": "Analyse complète approfondie",
        }
        return descriptions.get(scenario, "Scénario inconnu")


class MockOrchestrator:
    """Mock de l'orchestrateur complet pour tests d'intégration."""

    def __init__(self, scenario: str = "success"):
        """Initialise l'orchestrateur mock."""
        self.scenario = scenario
        self.analyzer = MockFallacyFamilyAnalyzer(scenario)
        self.call_count = 0

    async def analyze_with_fact_checking(self, request) -> Any:
        """Mock d'analyse complète via orchestrateur."""
        self.call_count += 1

        text = getattr(request, "text", str(request))
        depth = getattr(request, "analysis_depth", None)

        try:
            comprehensive_result = await self.analyzer.analyze_comprehensive(
                text, depth
            )

            # Créer une réponse mock
            if TYPES_AVAILABLE:
                from argumentation_analysis.orchestration.fact_checking_orchestrator import (
                    FactCheckingResponse,
                )

                response = FactCheckingResponse(
                    request_id=f"mock_request_{self.call_count}",
                    text_analyzed=text,
                    analysis_timestamp=datetime.now(),
                    comprehensive_result=comprehensive_result,
                    processing_time=0.5,
                    status="completed",
                )
            else:
                response = {
                    "request_id": f"mock_request_{self.call_count}",
                    "status": "completed",
                    "processing_time": 0.5,
                    "comprehensive_result": comprehensive_result,
                }

            return response

        except Exception as e:
            if TYPES_AVAILABLE:
                from argumentation_analysis.orchestration.fact_checking_orchestrator import (
                    FactCheckingResponse,
                )

                # Créer un résultat d'erreur minimal
                error_result = type(
                    "MockResult",
                    (),
                    {
                        "to_dict": lambda: {"error": str(e)},
                        "family_results": {},
                        "factual_claims": [],
                        "fact_check_results": [],
                    },
                )()

                response = FactCheckingResponse(
                    request_id=f"mock_request_{self.call_count}",
                    text_analyzed=text,
                    analysis_timestamp=datetime.now(),
                    comprehensive_result=error_result,
                    processing_time=0.0,
                    status="error",
                    error_message=str(e),
                )
            else:
                response = {
                    "request_id": f"mock_request_{self.call_count}",
                    "status": "error",
                    "error_message": str(e),
                    "processing_time": 0.0,
                }

            return response

    async def quick_fact_check(self, text: str, max_claims: int = 5) -> Dict[str, Any]:
        """Mock de fact-checking rapide."""
        claims = self.analyzer.fact_extractor.extract_factual_claims(text, max_claims)

        if not claims:
            return {
                "status": "no_claims",
                "message": "Aucune affirmation factuelle trouvée",
                "processing_time": 0.1,
            }

        verification_results = (
            await self.analyzer.verification_service.verify_multiple_claims(claims)
        )

        return {
            "status": "completed",
            "claims_count": len(claims),
            "verifications": [
                r.to_dict() if hasattr(r, "to_dict") else r
                for r in verification_results
            ],
            "processing_time": 0.3,
        }

    async def health_check(self) -> Dict[str, Any]:
        """Mock de health check."""
        return {
            "status": "healthy" if self.scenario != "error" else "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "fact_extractor": {"status": "ok"},
                "taxonomy_manager": {"status": "ok"},
                "verification_service": {"status": "ok"},
            },
            "scenario": self.scenario,
        }


# Factory functions pour faciliter l'utilisation dans les tests
def create_mock_extractor(scenario: str = "success") -> MockFactClaimExtractor:
    """Crée un mock extractor avec le scénario spécifié."""
    return MockFactClaimExtractor(scenario)


def create_mock_verifier(scenario: str = "success") -> MockFactVerificationService:
    """Crée un mock verifier avec le scénario spécifié."""
    return MockFactVerificationService(scenario)


def create_mock_taxonomy_manager(
    scenario: str = "success",
) -> MockFallacyTaxonomyManager:
    """Crée un mock taxonomy manager avec le scénario spécifié."""
    return MockFallacyTaxonomyManager(scenario)


def create_mock_analyzer(scenario: str = "success") -> MockFallacyFamilyAnalyzer:
    """Crée un mock analyzer avec le scénario spécifié."""
    return MockFallacyFamilyAnalyzer(scenario)


def create_mock_orchestrator(scenario: str = "success") -> MockOrchestrator:
    """Crée un mock orchestrator avec le scénario spécifié."""
    return MockOrchestrator(scenario)
