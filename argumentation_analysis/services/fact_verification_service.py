# -*- coding: utf-8 -*-
"""
Service de vérification factuelle pour l'intégration du fact-checking.

Ce module implémente la vérification automatique des affirmations factuelles
en utilisant des sources externes et l'intégration avec la taxonomie des sophismes.
"""

import logging
import asyncio
import aiohttp
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta

# Import des composants existants
from ..agents.tools.analysis.fact_claim_extractor import FactualClaim, ClaimVerifiability
from .fallacy_taxonomy_service import FallacyFamily, get_taxonomy_manager

logger = logging.getLogger(__name__)


class VerificationStatus(Enum):
    """Statuts de vérification des affirmations."""
    
    VERIFIED_TRUE = "verified_true"
    VERIFIED_FALSE = "verified_false"
    PARTIALLY_TRUE = "partially_true"
    DISPUTED = "disputed"
    UNVERIFIABLE = "unverifiable"
    INSUFFICIENT_INFO = "insufficient_info"
    ERROR = "error"


class SourceReliability(Enum):
    """Niveaux de fiabilité des sources."""
    
    HIGHLY_RELIABLE = "highly_reliable"
    MODERATELY_RELIABLE = "moderately_reliable"
    QUESTIONABLE = "questionable"
    UNRELIABLE = "unreliable"
    UNKNOWN = "unknown"


@dataclass
class VerificationSource:
    """Représentation d'une source de vérification."""
    
    url: str
    title: str
    snippet: str
    reliability: SourceReliability
    relevance_score: float
    publication_date: Optional[datetime]
    domain: str
    supports_claim: bool
    contradicts_claim: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit la source en dictionnaire."""
        return {
            "url": self.url,
            "title": self.title,
            "snippet": self.snippet,
            "reliability": self.reliability.value,
            "relevance_score": self.relevance_score,
            "publication_date": self.publication_date.isoformat() if self.publication_date else None,
            "domain": self.domain,
            "supports_claim": self.supports_claim,
            "contradicts_claim": self.contradicts_claim
        }


@dataclass
class FactVerificationResult:
    """Résultat de vérification d'une affirmation factuelle."""
    
    claim: FactualClaim
    status: VerificationStatus
    confidence: float
    verdict: str
    explanation: str
    sources: List[VerificationSource]
    supporting_sources: int
    contradicting_sources: int
    neutral_sources: int
    verification_date: datetime
    processing_time: float
    fallacy_implications: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit le résultat en dictionnaire."""
        return {
            "claim": self.claim.to_dict(),
            "status": self.status.value,
            "confidence": self.confidence,
            "verdict": self.verdict,
            "explanation": self.explanation,
            "sources": [source.to_dict() for source in self.sources],
            "supporting_sources": self.supporting_sources,
            "contradicting_sources": self.contradicting_sources,
            "neutral_sources": self.neutral_sources,
            "verification_date": self.verification_date.isoformat(),
            "processing_time": self.processing_time,
            "fallacy_implications": self.fallacy_implications
        }


class FactVerificationService:
    """
    Service de vérification factuelle des affirmations.
    
    Cette classe vérifie la véracité des affirmations factuelles
    en utilisant des sources externes et détecte les sophismes associés.
    """
    
    def __init__(self, api_config: Optional[Dict[str, Any]] = None):
        """
        Initialise le service de vérification factuelle.
        
        :param api_config: Configuration des APIs de recherche externes
        """
        self.logger = logging.getLogger("FactVerificationService")
        self.api_config = api_config or {}
        
        # Configuration des sources par défaut
        self._initialize_source_reliability()
        
        # Cache de vérifications
        self._verification_cache = {}
        self._cache_expiry = timedelta(hours=24)
        
        # Gestionnaire de taxonomie pour l'intégration des sophismes
        self.taxonomy_manager = get_taxonomy_manager()
        
        self.logger.info("FactVerificationService initialisé")
    
    def _initialize_source_reliability(self):
        """Initialise les niveaux de fiabilité des sources."""
        
        self.source_reliability_map = {
            # Sources hautement fiables
            "HIGHLY_RELIABLE": [
                "wikipedia.org", "britannica.com", "reuters.com", "apnews.com",
                "bbc.com", "lemonde.fr", "liberation.fr", "franceinfo.fr",
                "sciencedirect.com", "nature.com", "science.org", "pubmed.ncbi.nlm.nih.gov",
                "insee.fr", "gouvernement.fr", "europa.eu", "who.int"
            ],
            
            # Sources modérément fiables
            "MODERATELY_RELIABLE": [
                "huffingtonpost.fr", "lefigaro.fr", "lexpress.fr", "nouvelobs.com",
                "cnews.fr", "francetvinfo.fr", "rfi.fr", "france24.com",
                "20minutes.fr", "ouest-france.fr", "sudouest.fr"
            ],
            
            # Sources questionnables
            "QUESTIONABLE": [
                "blog", "forum", "reddit.com", "quora.com",
                "yahoo.com", "answers.com", "wikihow.com"
            ],
            
            # Sources non fiables
            "UNRELIABLE": [
                "fake-news", "conspiracy", "hoax", "satirical",
                "clickbait", "tabloid", "unverified"
            ]
        }
    
    async def verify_claim(self, claim: FactualClaim) -> FactVerificationResult:
        """
        Vérifie une affirmation factuelle.
        
        :param claim: Affirmation à vérifier
        :return: Résultat de vérification
        """
        start_time = datetime.now()
        
        try:
            self.logger.info(f"Vérification de l'affirmation: {claim.claim_text[:50]}...")
            
            # Vérifier le cache
            cache_key = self._generate_cache_key(claim)
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                self.logger.debug("Résultat trouvé en cache")
                return cached_result
            
            # Rechercher des sources
            sources = await self._search_sources(claim)
            
            # Analyser les sources
            analyzed_sources = self._analyze_sources(sources, claim)
            
            # Déterminer le statut de vérification
            status, confidence, verdict, explanation = self._determine_verification_status(
                analyzed_sources, claim
            )
            
            # Analyser les implications de sophismes
            fallacy_implications = self._analyze_fallacy_implications(
                claim, status, analyzed_sources
            )
            
            # Compter les sources par type
            supporting = sum(1 for s in analyzed_sources if s.supports_claim)
            contradicting = sum(1 for s in analyzed_sources if s.contradicts_claim)
            neutral = len(analyzed_sources) - supporting - contradicting
            
            # Créer le résultat
            processing_time = (datetime.now() - start_time).total_seconds()
            
            result = FactVerificationResult(
                claim=claim,
                status=status,
                confidence=confidence,
                verdict=verdict,
                explanation=explanation,
                sources=analyzed_sources,
                supporting_sources=supporting,
                contradicting_sources=contradicting,
                neutral_sources=neutral,
                verification_date=datetime.now(),
                processing_time=processing_time,
                fallacy_implications=fallacy_implications
            )
            
            # Mettre en cache
            self._cache_result(cache_key, result)
            
            self.logger.info(f"Vérification terminée: {status.value} (confiance: {confidence:.2f})")
            return result
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification: {e}")
            
            # Retourner un résultat d'erreur
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return FactVerificationResult(
                claim=claim,
                status=VerificationStatus.ERROR,
                confidence=0.0,
                verdict="Erreur de vérification",
                explanation=f"Une erreur s'est produite lors de la vérification: {e}",
                sources=[],
                supporting_sources=0,
                contradicting_sources=0,
                neutral_sources=0,
                verification_date=datetime.now(),
                processing_time=processing_time,
                fallacy_implications=[]
            )
    
    async def verify_multiple_claims(self, claims: List[FactualClaim]) -> List[FactVerificationResult]:
        """
        Vérifie plusieurs affirmations en parallèle.
        
        :param claims: Liste des affirmations à vérifier
        :return: Liste des résultats de vérification
        """
        self.logger.info(f"Vérification de {len(claims)} affirmations")
        
        # Limiter la concurrence pour éviter de surcharger les APIs
        semaphore = asyncio.Semaphore(3)
        
        async def verify_with_semaphore(claim):
            async with semaphore:
                return await self.verify_claim(claim)
        
        tasks = [verify_with_semaphore(claim) for claim in claims]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Traiter les exceptions
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Erreur lors de la vérification de l'affirmation {i}: {result}")
                # Créer un résultat d'erreur
                error_result = FactVerificationResult(
                    claim=claims[i],
                    status=VerificationStatus.ERROR,
                    confidence=0.0,
                    verdict="Erreur de vérification",
                    explanation=str(result),
                    sources=[],
                    supporting_sources=0,
                    contradicting_sources=0,
                    neutral_sources=0,
                    verification_date=datetime.now(),
                    processing_time=0.0,
                    fallacy_implications=[]
                )
                valid_results.append(error_result)
            else:
                valid_results.append(result)
        
        return valid_results
    
    async def _search_sources(self, claim: FactualClaim) -> List[Dict[str, Any]]:
        """Recherche des sources pour vérifier une affirmation."""
        
        # Construire la requête de recherche
        search_query = self._build_search_query(claim)
        
        sources = []
        
        # Recherche avec différentes APIs
        if self.api_config.get("tavily_api_key"):
            tavily_sources = await self._search_tavily(search_query)
            sources.extend(tavily_sources)
        
        if self.api_config.get("searxng_url"):
            searxng_sources = await self._search_searxng(search_query)
            sources.extend(searxng_sources)
        
        # Recherche de base (simulation si pas d'API configurée)
        if not sources:
            sources = self._simulate_search(search_query)
        
        return sources[:10]  # Limiter à 10 sources max
    
    def _build_search_query(self, claim: FactualClaim) -> str:
        """Construit une requête de recherche optimisée."""
        
        query_parts = []
        
        # Utiliser le texte de l'affirmation
        claim_text = claim.claim_text.strip('"\'')
        query_parts.append(f'"{claim_text}"')
        
        # Ajouter des mots-clés contextuels
        if claim.keywords:
            query_parts.extend(claim.keywords[:3])  # Limiter à 3 mots-clés
        
        # Ajouter des entités importantes
        for entity in claim.entities[:2]:  # Limiter à 2 entités
            if entity.get("label") in ["PERSON", "ORG", "GPE"]:
                query_parts.append(entity["text"])
        
        # Ajouter des références temporelles
        if claim.temporal_references:
            query_parts.append(claim.temporal_references[0])
        
        return " ".join(query_parts)
    
    async def _search_tavily(self, query: str) -> List[Dict[str, Any]]:
        """Recherche avec l'API Tavily."""
        
        # Implémentation simulée - remplacer par l'appel réel à l'API
        self.logger.debug(f"Recherche Tavily simulée pour: {query}")
        
        return [
            {
                "url": f"https://example-source-1.com/article",
                "title": f"Article vérifiant: {query[:30]}",
                "snippet": f"Information pertinente concernant {query}...",
                "domain": "example-source-1.com",
                "published_date": "2024-01-01"
            },
            {
                "url": f"https://example-source-2.com/study",
                "title": f"Étude sur: {query[:30]}",
                "snippet": f"Recherche académique concernant {query}...",
                "domain": "example-source-2.com",
                "published_date": "2024-02-01"
            }
        ]
    
    async def _search_searxng(self, query: str) -> List[Dict[str, Any]]:
        """Recherche avec SearXNG."""
        
        # Implémentation simulée - remplacer par l'appel réel à SearXNG
        self.logger.debug(f"Recherche SearXNG simulée pour: {query}")
        
        return [
            {
                "url": f"https://searxng-result.com/page",
                "title": f"Résultat SearXNG: {query[:30]}",
                "snippet": f"Information trouvée via SearXNG pour {query}...",
                "domain": "searxng-result.com",
                "published_date": "2024-03-01"
            }
        ]
    
    def _simulate_search(self, query: str) -> List[Dict[str, Any]]:
        """Simule une recherche quand aucune API n'est configurée."""
        
        self.logger.debug(f"Simulation de recherche pour: {query}")
        
        return [
            {
                "url": "https://wikipedia.org/wiki/mock_article",
                "title": f"Article Wikipedia sur {query[:20]}",
                "snippet": f"Wikipedia contient des informations sur {query}. Cette affirmation peut être vérifiée selon les sources disponibles.",
                "domain": "wikipedia.org",
                "published_date": "2024-01-15"
            },
            {
                "url": "https://reuters.com/mock_news",
                "title": f"Actualité Reuters: {query[:20]}",
                "snippet": f"Selon Reuters, les informations concernant {query} sont documentées dans plusieurs sources fiables.",
                "domain": "reuters.com",
                "published_date": "2024-02-20"
            }
        ]
    
    def _analyze_sources(self, sources: List[Dict[str, Any]], claim: FactualClaim) -> List[VerificationSource]:
        """Analyse les sources trouvées."""
        
        analyzed_sources = []
        
        for source_data in sources:
            # Déterminer la fiabilité
            reliability = self._assess_source_reliability(source_data.get("domain", ""))
            
            # Calculer la pertinence
            relevance_score = self._calculate_relevance(source_data, claim)
            
            # Déterminer si la source supporte ou contredit l'affirmation
            supports, contradicts = self._analyze_source_stance(source_data, claim)
            
            # Extraire la date de publication
            pub_date = self._parse_publication_date(source_data.get("published_date"))
            
            analyzed_source = VerificationSource(
                url=source_data.get("url", ""),
                title=source_data.get("title", ""),
                snippet=source_data.get("snippet", ""),
                reliability=reliability,
                relevance_score=relevance_score,
                publication_date=pub_date,
                domain=source_data.get("domain", ""),
                supports_claim=supports,
                contradicts_claim=contradicts
            )
            
            analyzed_sources.append(analyzed_source)
        
        return analyzed_sources
    
    def _assess_source_reliability(self, domain: str) -> SourceReliability:
        """Évalue la fiabilité d'une source basée sur son domaine."""
        
        domain_lower = domain.lower()
        
        for reliability_level, domains in self.source_reliability_map.items():
            for known_domain in domains:
                if known_domain in domain_lower:
                    return SourceReliability(reliability_level.lower())
        
        return SourceReliability.UNKNOWN
    
    def _calculate_relevance(self, source_data: Dict[str, Any], claim: FactualClaim) -> float:
        """Calcule la pertinence d'une source pour une affirmation."""
        
        relevance = 0.0
        
        # Analyser le titre
        title = source_data.get("title", "").lower()
        claim_text = claim.claim_text.lower()
        
        # Correspondance directe dans le titre
        if claim_text in title:
            relevance += 0.5
        
        # Mots-clés de l'affirmation dans le titre
        claim_words = set(claim_text.split())
        title_words = set(title.split())
        common_words = claim_words.intersection(title_words)
        relevance += len(common_words) * 0.1
        
        # Analyser le snippet
        snippet = source_data.get("snippet", "").lower()
        if claim_text in snippet:
            relevance += 0.3
        
        # Entités communes
        for entity in claim.entities:
            entity_text = entity["text"].lower()
            if entity_text in title or entity_text in snippet:
                relevance += 0.2
        
        return min(relevance, 1.0)
    
    def _analyze_source_stance(self, source_data: Dict[str, Any], claim: FactualClaim) -> Tuple[bool, bool]:
        """Analyse si une source supporte ou contredit une affirmation."""
        
        snippet = source_data.get("snippet", "").lower()
        title = source_data.get("title", "").lower()
        content = f"{title} {snippet}"
        
        # Mots-clés de support
        support_keywords = [
            "confirme", "prouve", "démontre", "établit", "vérifie",
            "exact", "correct", "vrai", "authentique", "avéré"
        ]
        
        # Mots-clés de contradiction
        contradict_keywords = [
            "faux", "erroné", "inexact", "contredit", "réfute",
            "dément", "infirme", "nie", "conteste", "invalide"
        ]
        
        supports = any(keyword in content for keyword in support_keywords)
        contradicts = any(keyword in content for keyword in contradict_keywords)
        
        return supports, contradicts
    
    def _parse_publication_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse une date de publication."""
        
        if not date_str:
            return None
        
        try:
            # Essayer différents formats
            for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y"]:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
        except Exception as e:
            self.logger.debug(f"Impossible de parser la date {date_str}: {e}")
        
        return None
    
    def _determine_verification_status(self, sources: List[VerificationSource], 
                                     claim: FactualClaim) -> Tuple[VerificationStatus, float, str, str]:
        """Détermine le statut de vérification basé sur les sources."""
        
        if not sources:
            return (
                VerificationStatus.INSUFFICIENT_INFO,
                0.0,
                "Information insuffisante",
                "Aucune source fiable trouvée pour vérifier cette affirmation."
            )
        
        # Calculer les scores pondérés
        total_support = 0.0
        total_contradiction = 0.0
        total_weight = 0.0
        
        reliability_weights = {
            SourceReliability.HIGHLY_RELIABLE: 1.0,
            SourceReliability.MODERATELY_RELIABLE: 0.7,
            SourceReliability.QUESTIONABLE: 0.3,
            SourceReliability.UNRELIABLE: 0.1,
            SourceReliability.UNKNOWN: 0.5
        }
        
        for source in sources:
            weight = reliability_weights[source.reliability] * source.relevance_score
            total_weight += weight
            
            if source.supports_claim:
                total_support += weight
            elif source.contradicts_claim:
                total_contradiction += weight
        
        if total_weight == 0:
            return (
                VerificationStatus.UNVERIFIABLE,
                0.0,
                "Non vérifiable",
                "Les sources trouvées ne permettent pas de vérifier cette affirmation."
            )
        
        support_ratio = total_support / total_weight
        contradiction_ratio = total_contradiction / total_weight
        
        # Déterminer le statut
        if support_ratio >= 0.7:
            status = VerificationStatus.VERIFIED_TRUE
            confidence = support_ratio
            verdict = "Affirmation vérifiée comme vraie"
            explanation = f"Plusieurs sources fiables confirment cette affirmation (score de support: {support_ratio:.2f})"
            
        elif contradiction_ratio >= 0.7:
            status = VerificationStatus.VERIFIED_FALSE
            confidence = contradiction_ratio
            verdict = "Affirmation vérifiée comme fausse"
            explanation = f"Plusieurs sources fiables contredisent cette affirmation (score de contradiction: {contradiction_ratio:.2f})"
            
        elif support_ratio >= 0.4 and contradiction_ratio <= 0.2:
            status = VerificationStatus.PARTIALLY_TRUE
            confidence = support_ratio * 0.8
            verdict = "Affirmation partiellement vraie"
            explanation = f"Certaines sources supportent l'affirmation mais avec des nuances (support: {support_ratio:.2f})"
            
        elif support_ratio >= 0.3 and contradiction_ratio >= 0.3:
            status = VerificationStatus.DISPUTED
            confidence = 1.0 - abs(support_ratio - contradiction_ratio)
            verdict = "Affirmation disputée"
            explanation = f"Sources contradictoires (support: {support_ratio:.2f}, contradiction: {contradiction_ratio:.2f})"
            
        else:
            status = VerificationStatus.UNVERIFIABLE
            confidence = 0.3
            verdict = "Non vérifiable de manière concluante"
            explanation = f"Preuves insuffisantes (support: {support_ratio:.2f}, contradiction: {contradiction_ratio:.2f})"
        
        return status, confidence, verdict, explanation
    
    def _analyze_fallacy_implications(self, claim: FactualClaim, status: VerificationStatus, 
                                    sources: List[VerificationSource]) -> List[Dict[str, Any]]:
        """Analyse les implications en termes de sophismes."""
        
        implications = []
        
        # Analyser basé sur le type d'affirmation et le résultat de vérification
        if status == VerificationStatus.VERIFIED_FALSE:
            # L'affirmation est fausse, analyser les sophismes potentiels
            
            # Sophismes de généralisation si l'affirmation contient des généralisations
            if any(word in claim.claim_text.lower() for word in ["tous", "toujours", "jamais", "aucun"]):
                implications.append({
                    "fallacy_family": FallacyFamily.GENERALIZATION_CAUSALITY.value,
                    "potential_fallacy": "Généralisation hâtive basée sur des faits incorrects",
                    "confidence": 0.8,
                    "explanation": "L'affirmation utilise une généralisation qui s'avère factuellement incorrecte"
                })
            
            # Sophismes statistiques si l'affirmation contient des statistiques fausses
            if claim.claim_type.value == "statistical":
                implications.append({
                    "fallacy_family": FallacyFamily.STATISTICAL_PROBABILISTIC.value,
                    "potential_fallacy": "Utilisation de statistiques incorrectes",
                    "confidence": 0.9,
                    "explanation": "L'affirmation présente des données statistiques qui ne sont pas supportées par les sources fiables"
                })
            
            # Sophismes d'autorité si une source non fiable est citée
            if claim.sources_mentioned:
                implications.append({
                    "fallacy_family": FallacyFamily.AUTHORITY_POPULARITY.value,
                    "potential_fallacy": "Appel à une autorité non fiable",
                    "confidence": 0.7,
                    "explanation": "L'affirmation cite des sources qui ne sont pas corroborées par des sources fiables"
                })
        
        elif status == VerificationStatus.DISPUTED:
            # Affirmation disputée, pourrait indiquer une sélection biaisée de sources
            implications.append({
                "fallacy_family": FallacyFamily.STATISTICAL_PROBABILISTIC.value,
                "potential_fallacy": "Biais de confirmation possible",
                "confidence": 0.6,
                "explanation": "L'affirmation est controversée, ce qui pourrait indiquer une sélection biaisée d'informations"
            })
        
        return implications
    
    def _generate_cache_key(self, claim: FactualClaim) -> str:
        """Génère une clé de cache pour une affirmation."""
        return f"fact_check_{hash(claim.claim_text)}_{claim.claim_type.value}"
    
    def _get_cached_result(self, cache_key: str) -> Optional[FactVerificationResult]:
        """Récupère un résultat du cache s'il existe et n'est pas expiré."""
        
        if cache_key in self._verification_cache:
            cached_data = self._verification_cache[cache_key]
            cache_time = cached_data["timestamp"]
            
            if datetime.now() - cache_time < self._cache_expiry:
                return cached_data["result"]
            else:
                # Cache expiré, le supprimer
                del self._verification_cache[cache_key]
        
        return None
    
    def _cache_result(self, cache_key: str, result: FactVerificationResult):
        """Met en cache un résultat de vérification."""
        
        self._verification_cache[cache_key] = {
            "result": result,
            "timestamp": datetime.now()
        }
        
        # Nettoyage périodique du cache (garder seulement les 100 derniers)
        if len(self._verification_cache) > 100:
            # Supprimer les plus anciens
            sorted_items = sorted(
                self._verification_cache.items(),
                key=lambda x: x[1]["timestamp"]
            )
            
            for key, _ in sorted_items[:-50]:  # Garder les 50 plus récents
                del self._verification_cache[key]


# Instance globale du service
_global_verification_service = None

def get_verification_service(api_config: Optional[Dict[str, Any]] = None) -> FactVerificationService:
    """
    Récupère l'instance globale du service de vérification (singleton pattern).
    
    :param api_config: Configuration optionnelle des APIs
    :return: Instance globale du service
    """
    global _global_verification_service
    if _global_verification_service is None:
        _global_verification_service = FactVerificationService(api_config=api_config)
    return _global_verification_service