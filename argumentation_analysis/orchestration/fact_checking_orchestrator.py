# -*- coding: utf-8 -*-
"""
Orchestrateur de fact-checking intégré avec l'analyse des sophismes par familles.

Ce module intègre les nouveaux composants de fact-checking et d'analyse
par famille dans l'architecture d'orchestration existante.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

# Imports des nouveaux composants
# Correction des imports pour utiliser des chemins absolus et éviter les ambiguïtés
from argumentation_analysis.agents.tools.analysis.fact_claim_extractor import FactClaimExtractor, FactualClaim
from argumentation_analysis.agents.tools.analysis.fallacy_family_analyzer import (
    FallacyFamilyAnalyzer, get_family_analyzer, AnalysisDepth, ComprehensiveAnalysisResult
)
from argumentation_analysis.services.fact_verification_service import get_verification_service
from argumentation_analysis.services.fallacy_taxonomy_service import get_taxonomy_manager

logger = logging.getLogger(__name__)


@dataclass
class FactCheckingRequest:
    """Requête d'analyse avec fact-checking intégré."""
    
    text: str
    analysis_depth: AnalysisDepth = AnalysisDepth.STANDARD
    enable_fact_checking: bool = True
    max_claims: int = 10
    max_fallacies: int = 15
    api_config: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None


@dataclass
class FactCheckingResponse:
    """Réponse d'analyse avec fact-checking intégré."""
    
    request_id: str
    text_analyzed: str
    analysis_timestamp: datetime
    comprehensive_result: ComprehensiveAnalysisResult
    processing_time: float
    status: str
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit la réponse en dictionnaire."""
        return {
            "request_id": self.request_id,
            "text_analyzed": self.text_analyzed[:200] + "..." if len(self.text_analyzed) > 200 else self.text_analyzed,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
            "comprehensive_result": self.comprehensive_result.to_dict(),
            "processing_time": self.processing_time,
            "status": self.status,
            "error_message": self.error_message
        }


class FactCheckingOrchestrator:
    """
    Orchestrateur principal pour l'analyse intégrée fact-checking + sophismes.
    
    Cette classe coordonne l'ensemble du processus d'analyse en intégrant :
    - Extraction d'affirmations factuelles
    - Vérification factuelle multi-source
    - Détection et classification des sophismes par familles
    - Analyse des corrélations entre fact-checking et sophismes
    """
    
    def __init__(self, api_config: Optional[Dict[str, Any]] = None):
        """
        Initialise l'orchestrateur de fact-checking.
        
        :param api_config: Configuration des APIs externes (Tavily, SearXNG, etc.)
        """
        self.logger = logging.getLogger("FactCheckingOrchestrator")
        self.api_config = api_config or {}
        
        # Initialiser les composants
        self.fact_extractor = FactClaimExtractor()
        self.verification_service = get_verification_service(api_config)
        self.taxonomy_manager = get_taxonomy_manager()
        self.family_analyzer = get_family_analyzer(api_config)
        
        # Métriques de performance
        self.analysis_count = 0
        self.total_processing_time = 0.0
        self.error_count = 0
        
        self.logger.info("FactCheckingOrchestrator initialisé")
    
    async def analyze_with_fact_checking(self, request: FactCheckingRequest) -> FactCheckingResponse:
        """
        Lance une analyse complète avec fact-checking intégré.
        
        :param request: Requête d'analyse
        :return: Réponse complète de l'analyse
        """
        import uuid
        
        request_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        try:
            self.logger.info(f"Début d'analyse fact-checking {request_id}")
            
            # Analyse complète avec l'analyseur par famille
            comprehensive_result = await self.family_analyzer.analyze_comprehensive(
                text=request.text,
                depth=request.analysis_depth
            )
            
            # Calculer le temps de traitement
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Mettre à jour les métriques
            self.analysis_count += 1
            self.total_processing_time += processing_time
            
            # Créer la réponse
            response = FactCheckingResponse(
                request_id=request_id,
                text_analyzed=request.text,
                analysis_timestamp=start_time,
                comprehensive_result=comprehensive_result,
                processing_time=processing_time,
                status="completed"
            )
            
            self.logger.info(f"Analyse {request_id} terminée en {processing_time:.2f}s")
            return response
            
        except Exception as e:
            self.error_count += 1
            processing_time = (datetime.now() - start_time).total_seconds()
            
            self.logger.error(f"Erreur lors de l'analyse {request_id}: {e}")
            
            return FactCheckingResponse(
                request_id=request_id,
                text_analyzed=request.text,
                analysis_timestamp=start_time,
                comprehensive_result=ComprehensiveAnalysisResult(
                    text_analyzed=request.text,
                    analysis_timestamp=start_time,
                    analysis_depth=request.analysis_depth,
                    family_results={},
                    factual_claims=[],
                    fact_check_results=[],
                    overall_assessment={"error": str(e)},
                    strategic_insights={},
                    recommendations=[]
                ),
                processing_time=processing_time,
                status="error",
                error_message=str(e)
            )
    
    async def quick_fact_check(self, text: str, max_claims: int = 5) -> Dict[str, Any]:
        """
        Effectue un fact-checking rapide sans analyse complète des sophismes.
        
        :param text: Texte à vérifier
        :param max_claims: Nombre maximum d'affirmations à vérifier
        :return: Résultats de fact-checking
        """
        start_time = datetime.now()
        
        try:
            self.logger.info(f"Fact-checking rapide pour un texte de {len(text)} caractères")
            
            # Extraction des affirmations
            factual_claims = self.fact_extractor.extract_factual_claims(text, max_claims)
            
            if not factual_claims:
                return {
                    "status": "no_claims",
                    "message": "Aucune affirmation factuelle trouvée",
                    "processing_time": (datetime.now() - start_time).total_seconds()
                }
            
            # Vérification factuelle
            verification_results = await self.verification_service.verify_multiple_claims(factual_claims)
            
            # Compilation des résultats
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "status": "completed",
                "claims_count": len(factual_claims),
                "verifications": [result.to_dict() for result in verification_results],
                "summary": self._generate_quick_summary(verification_results),
                "processing_time": processing_time
            }
            
        except Exception as e:
            self.logger.error(f"Erreur lors du fact-checking rapide: {e}")
            return {
                "status": "error",
                "error": str(e),
                "processing_time": (datetime.now() - start_time).total_seconds()
            }
    
    async def analyze_fallacy_families_only(self, text: str, depth: AnalysisDepth = AnalysisDepth.STANDARD) -> Dict[str, Any]:
        """
        Analyse uniquement les familles de sophismes sans fact-checking.
        
        :param text: Texte à analyser
        :param depth: Profondeur d'analyse
        :return: Résultats d'analyse des familles
        """
        start_time = datetime.now()
        
        try:
            self.logger.info(f"Analyse des familles de sophismes uniquement")
            
            # Détection et classification par famille
            classified_fallacies = self.taxonomy_manager.detect_fallacies_with_families(text)
            
            # Statistiques par famille
            family_stats = self.taxonomy_manager.get_family_statistics(classified_fallacies)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "status": "completed",
                "fallacies_detected": [f.to_dict() for f in classified_fallacies],
                "family_statistics": family_stats,
                "analysis_depth": depth.value,
                "processing_time": processing_time
            }
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'analyse des familles: {e}")
            return {
                "status": "error",
                "error": str(e),
                "processing_time": (datetime.now() - start_time).total_seconds()
            }
    
    def _generate_quick_summary(self, verification_results: List[Any]) -> Dict[str, Any]:
        """Génère un résumé rapide des résultats de fact-checking."""
        
        summary = {
            "total_claims": len(verification_results),
            "verified_true": 0,
            "verified_false": 0,
            "disputed": 0,
            "unverifiable": 0,
            "average_confidence": 0.0,
            "credibility_score": 0.0
        }
        
        if not verification_results:
            return summary
        
        total_confidence = 0.0
        
        for result in verification_results:
            status = result.status.value
            
            if status == "verified_true":
                summary["verified_true"] += 1
            elif status == "verified_false":
                summary["verified_false"] += 1
            elif status == "disputed":
                summary["disputed"] += 1
            else:
                summary["unverifiable"] += 1
            
            total_confidence += result.confidence
        
        summary["average_confidence"] = total_confidence / len(verification_results)
        
        # Calculer le score de crédibilité
        false_ratio = summary["verified_false"] / summary["total_claims"]
        disputed_ratio = summary["disputed"] / summary["total_claims"]
        summary["credibility_score"] = max(0.0, 1.0 - (false_ratio * 0.8) - (disputed_ratio * 0.4))
        
        return summary
    
    async def batch_analyze(self, texts: List[str], 
                          analysis_depth: AnalysisDepth = AnalysisDepth.STANDARD) -> List[FactCheckingResponse]:
        """
        Analyse en lot de plusieurs textes.
        
        :param texts: Liste des textes à analyser
        :param analysis_depth: Profondeur d'analyse
        :return: Liste des réponses d'analyse
        """
        self.logger.info(f"Analyse en lot de {len(texts)} textes")
        
        # Créer les requêtes
        requests = [
            FactCheckingRequest(
                text=text,
                analysis_depth=analysis_depth,
                api_config=self.api_config
            )
            for text in texts
        ]
        
        # Traitement en parallèle avec limitation de concurrence
        semaphore = asyncio.Semaphore(3)  # Max 3 analyses simultanées
        
        async def analyze_with_semaphore(request):
            async with semaphore:
                return await self.analyze_with_fact_checking(request)
        
        tasks = [analyze_with_semaphore(req) for req in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Traiter les exceptions
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Erreur pour le texte {i}: {result}")
                # Créer une réponse d'erreur
                error_response = FactCheckingResponse(
                    request_id=f"batch_error_{i}",
                    text_analyzed=texts[i][:100] + "..." if len(texts[i]) > 100 else texts[i],
                    analysis_timestamp=datetime.now(),
                    comprehensive_result=ComprehensiveAnalysisResult(
                        text_analyzed=texts[i],
                        analysis_timestamp=datetime.now(),
                        analysis_depth=analysis_depth,
                        family_results={},
                        factual_claims=[],
                        fact_check_results=[],
                        overall_assessment={"error": str(result)},
                        strategic_insights={},
                        recommendations=[]
                    ),
                    processing_time=0.0,
                    status="error",
                    error_message=str(result)
                )
                valid_results.append(error_response)
            else:
                valid_results.append(result)
        
        return valid_results
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Retourne les métriques de performance de l'orchestrateur."""
        
        avg_processing_time = (
            self.total_processing_time / self.analysis_count 
            if self.analysis_count > 0 else 0.0
        )
        
        error_rate = (
            self.error_count / self.analysis_count 
            if self.analysis_count > 0 else 0.0
        )
        
        return {
            "total_analyses": self.analysis_count,
            "total_processing_time": self.total_processing_time,
            "average_processing_time": avg_processing_time,
            "error_count": self.error_count,
            "error_rate": error_rate,
            "success_rate": 1.0 - error_rate
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Effectue un contrôle de santé de l'orchestrateur."""
        
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {}
        }
        
        try:
            # Test de l'extracteur d'affirmations
            test_text = "En 2023, 50% des français utilisent internet quotidiennement."
            test_claims = self.fact_extractor.extract_factual_claims(test_text, max_claims=1)
            health_status["components"]["fact_extractor"] = {
                "status": "ok" if test_claims else "warning",
                "claims_extracted": len(test_claims)
            }
            
            # Test du gestionnaire de taxonomie
            test_fallacies = self.taxonomy_manager.detect_fallacies_with_families(test_text, max_fallacies=1)
            health_status["components"]["taxonomy_manager"] = {
                "status": "ok",
                "fallacies_detected": len(test_fallacies)
            }
            
            # Test de l'analyseur par famille (test léger)
            health_status["components"]["family_analyzer"] = {
                "status": "ok",
                "note": "Interface disponible"
            }
            
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["error"] = str(e)
        
        return health_status
    
    def get_api_config(self) -> Dict[str, Any]:
        """Retourne la configuration API actuelle."""
        return self.api_config.copy()
    
    def update_api_config(self, new_config: Dict[str, Any]):
        """Met à jour la configuration API."""
        self.api_config.update(new_config)
        self.logger.info("Configuration API mise à jour")


# Instance globale de l'orchestrateur
_global_fact_checking_orchestrator = None

def get_fact_checking_orchestrator(api_config: Optional[Dict[str, Any]] = None) -> FactCheckingOrchestrator:
    """
    Récupère l'instance globale de l'orchestrateur fact-checking (singleton pattern).
    
    :param api_config: Configuration optionnelle des APIs
    :return: Instance globale de l'orchestrateur
    """
    global _global_fact_checking_orchestrator
    if _global_fact_checking_orchestrator is None:
        _global_fact_checking_orchestrator = FactCheckingOrchestrator(api_config=api_config)
    return _global_fact_checking_orchestrator


# Fonctions de commodité pour l'intégration
async def quick_analyze_text(text: str, api_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Fonction de commodité pour une analyse rapide.
    
    :param text: Texte à analyser
    :param api_config: Configuration API optionnelle
    :return: Résultats d'analyse
    """
    orchestrator = get_fact_checking_orchestrator(api_config)
    
    request = FactCheckingRequest(
        text=text,
        analysis_depth=AnalysisDepth.STANDARD,
        api_config=api_config
    )
    
    response = await orchestrator.analyze_with_fact_checking(request)
    return response.to_dict()


async def quick_fact_check_only(text: str, api_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Fonction de commodité pour un fact-checking rapide uniquement.
    
    :param text: Texte à vérifier
    :param api_config: Configuration API optionnelle
    :return: Résultats de fact-checking
    """
    orchestrator = get_fact_checking_orchestrator(api_config)
    return await orchestrator.quick_fact_check(text)


async def quick_fallacy_analysis_only(text: str) -> Dict[str, Any]:
    """
    Fonction de commodité pour une analyse des sophismes uniquement.
    
    :param text: Texte à analyser
    :return: Résultats d'analyse des sophismes
    """
    orchestrator = get_fact_checking_orchestrator()
    return await orchestrator.analyze_fallacy_families_only(text)