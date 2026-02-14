# -*- coding: utf-8 -*-
"""
Plugin pour la vérification factuelle externe.
"""

import logging
import asyncio
import aiohttp
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta

# Import des composants de base des plugins
from src.core.plugins.interfaces import BasePlugin

# Import des composants de l'ancien service
from argumentation_analysis.agents.tools.analysis.fact_claim_extractor import (
    FactualClaim,
    ClaimVerifiability,
)
from src.core.plugins.standard.taxonomy_explorer.plugin import TaxonomyExplorerPlugin

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
            "publication_date": (
                self.publication_date.isoformat() if self.publication_date else None
            ),
            "domain": self.domain,
            "supports_claim": self.supports_claim,
            "contradicts_claim": self.contradicts_claim,
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
            "fallacy_implications": self.fallacy_implications,
        }


class ExternalVerificationPlugin(BasePlugin):
    """
    Plugin de vérification factuelle des affirmations.
    """

    def __init__(
        self,
        taxonomy_plugin: TaxonomyExplorerPlugin,
        api_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialise le plugin de vérification factuelle.
        :param taxonomy_plugin: Instance du plugin de taxonomie.
        :param api_config: Configuration des APIs de recherche externes
        """
        super().__init__()
        self.logger = logging.getLogger("ExternalVerificationPlugin")
        self.api_config = api_config or {}

        self._initialize_source_reliability()

        self._verification_cache = {}
        self._cache_expiry = timedelta(hours=24)

        self.taxonomy_plugin = taxonomy_plugin

        self.logger.info("ExternalVerificationPlugin initialisé")

    def _initialize_source_reliability(self):
        """Initialise les niveaux de fiabilité des sources."""
        self.source_reliability_map = {
            "HIGHLY_RELIABLE": [
                "wikipedia.org",
                "britannica.com",
                "reuters.com",
                "apnews.com",
                "bbc.com",
                "lemonde.fr",
                "liberation.fr",
                "franceinfo.fr",
                "sciencedirect.com",
                "nature.com",
                "science.org",
                "pubmed.ncbi.nlm.nih.gov",
                "insee.fr",
                "gouvernement.fr",
                "europa.eu",
                "who.int",
            ],
            "MODERATELY_RELIABLE": [
                "huffingtonpost.fr",
                "lefigaro.fr",
                "lexpress.fr",
                "nouvelobs.com",
                "cnews.fr",
                "francetvinfo.fr",
                "rfi.fr",
                "france24.com",
                "20minutes.fr",
                "ouest-france.fr",
                "sudouest.fr",
            ],
            "QUESTIONABLE": [
                "blog",
                "forum",
                "reddit.com",
                "quora.com",
                "yahoo.com",
                "answers.com",
                "wikihow.com",
            ],
            "UNRELIABLE": [
                "fake-news",
                "conspiracy",
                "hoax",
                "satirical",
                "clickbait",
                "tabloid",
                "unverified",
            ],
        }

    async def verify_claims(
        self, claims: List[FactualClaim]
    ) -> List[FactVerificationResult]:
        """
        Vérifie plusieurs affirmations en parallèle.
        C'est la capacité principale exposée par le plugin.
        """
        self.logger.info(f"Vérification de {len(claims)} affirmations via le plugin")

        semaphore = asyncio.Semaphore(
            self.api_config.get("max_concurrent_verifications", 3)
        )

        async def verify_with_semaphore(claim):
            async with semaphore:
                return await self._verify_one_claim(claim)

        tasks = [verify_with_semaphore(claim) for claim in claims]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(
                    f"Erreur lors de la vérification de l'affirmation {i}: {result}"
                )
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
                    fallacy_implications=[],
                )
                valid_results.append(error_result)
            else:
                valid_results.append(result)

        return valid_results

    async def _verify_one_claim(self, claim: FactualClaim) -> FactVerificationResult:
        """
        Logique de vérification pour une seule affirmation.
        """
        start_time = datetime.now()

        try:
            self.logger.info(
                f"Vérification de l'affirmation: {claim.claim_text[:50]}..."
            )

            cache_key = self._generate_cache_key(claim)
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                self.logger.debug("Résultat trouvé en cache")
                return cached_result

            sources = await self._search_sources(claim)
            analyzed_sources = self._analyze_sources(sources, claim)

            (
                status,
                confidence,
                verdict,
                explanation,
            ) = self._determine_verification_status(analyzed_sources, claim)

            fallacy_implications = self._analyze_fallacy_implications(
                claim, status, analyzed_sources
            )

            supporting = sum(1 for s in analyzed_sources if s.supports_claim)
            contradicting = sum(1 for s in analyzed_sources if s.contradicts_claim)
            neutral = len(analyzed_sources) - supporting - contradicting

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
                fallacy_implications=fallacy_implications,
            )

            self._cache_result(cache_key, result)

            self.logger.info(
                f"Vérification terminée: {status.value} (confiance: {confidence:.2f})"
            )
            return result

        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification: {e}", exc_info=True)
            processing_time = (datetime.now() - start_time).total_seconds()
            return FactVerificationResult(
                claim=claim,
                status=VerificationStatus.ERROR,
                confidence=0.0,
                verdict="Erreur de vérification",
                explanation=f"Une erreur s'est produite: {e}",
                sources=[],
                supporting_sources=0,
                contradicting_sources=0,
                neutral_sources=0,
                verification_date=datetime.now(),
                processing_time=processing_time,
                fallacy_implications=[],
            )

    async def _search_sources(self, claim: FactualClaim) -> List[Dict[str, Any]]:
        # ... (le reste des méthodes privées _search_sources, _build_search_query, etc. reste identique)
        """Recherche des sources pour vérifier une affirmation."""

        search_query = self._build_search_query(claim)
        sources = []

        if self.api_config.get("tavily_api_key"):
            tavily_sources = await self._search_tavily(search_query)
            sources.extend(tavily_sources)

        if self.api_config.get("searxng_url"):
            searxng_sources = await self._search_searxng(search_query)
            sources.extend(searxng_sources)

        if not sources:
            sources = self._simulate_search(search_query)

        return sources[:10]

    def _build_search_query(self, claim: FactualClaim) -> str:
        query_parts = []
        claim_text = claim.claim_text.strip("\"'")
        query_parts.append(f'"{claim_text}"')
        if claim.keywords:
            query_parts.extend(claim.keywords[:3])
        for entity in claim.entities[:2]:
            if entity.get("label") in ["PERSON", "ORG", "GPE"]:
                query_parts.append(entity["text"])
        if claim.temporal_references:
            query_parts.append(claim.temporal_references[0])
        return " ".join(query_parts)

    async def _search_tavily(self, query: str) -> List[Dict[str, Any]]:
        self.logger.debug(f"Recherche Tavily simulée pour: {query}")
        return [
            {
                "url": f"https://example-tavily.com/{query[:10]}",
                "title": f"Tavily: {query[:30]}",
                "snippet": "...",
                "domain": "example-tavily.com",
                "published_date": "2024-01-01",
            }
        ]

    async def _search_searxng(self, query: str) -> List[Dict[str, Any]]:
        self.logger.debug(f"Recherche SearXNG simulée pour: {query}")
        return [
            {
                "url": f"https://example-searxng.com/{query[:10]}",
                "title": f"SearXNG: {query[:30]}",
                "snippet": "...",
                "domain": "example-searxng.com",
                "published_date": "2024-03-01",
            }
        ]

    def _simulate_search(self, query: str) -> List[Dict[str, Any]]:
        self.logger.debug(f"Simulation de recherche pour: {query}")
        return [
            {
                "url": "https://wikipedia.org/wiki/mock_article",
                "title": f"Wikipedia sur {query[:20]}",
                "snippet": "...",
                "domain": "wikipedia.org",
                "published_date": "2024-01-15",
            },
            {
                "url": "https://reuters.com/mock_news",
                "title": f"Reuters: {query[:20]}",
                "snippet": "...",
                "domain": "reuters.com",
                "published_date": "2024-02-20",
            },
        ]

    def _analyze_sources(
        self, sources: List[Dict[str, Any]], claim: FactualClaim
    ) -> List[VerificationSource]:
        analyzed_sources = []
        for source_data in sources:
            reliability = self._assess_source_reliability(source_data.get("domain", ""))
            relevance_score = self._calculate_relevance(source_data, claim)
            supports, contradicts = self._analyze_source_stance(source_data, claim)
            pub_date = self._parse_publication_date(source_data.get("published_date"))
            analyzed_sources.append(
                VerificationSource(
                    url=source_data.get("url", ""),
                    title=source_data.get("title", ""),
                    snippet=source_data.get("snippet", ""),
                    reliability=reliability,
                    relevance_score=relevance_score,
                    publication_date=pub_date,
                    domain=source_data.get("domain", ""),
                    supports_claim=supports,
                    contradicts_claim=contradicts,
                )
            )
        return analyzed_sources

    def _assess_source_reliability(self, domain: str) -> SourceReliability:
        domain_lower = domain.lower()
        for reliability_level, domains in self.source_reliability_map.items():
            if any(known_domain in domain_lower for known_domain in domains):
                return SourceReliability(reliability_level.lower())
        return SourceReliability.UNKNOWN

    def _calculate_relevance(
        self, source_data: Dict[str, Any], claim: FactualClaim
    ) -> float:
        relevance = 0.0
        title = source_data.get("title", "").lower()
        claim_text = claim.claim_text.lower()
        if claim_text in title:
            relevance += 0.5
        claim_words = set(claim_text.split())
        title_words = set(title.split())
        common_words = claim_words.intersection(title_words)
        relevance += len(common_words) * 0.1
        snippet = source_data.get("snippet", "").lower()
        if claim_text in snippet:
            relevance += 0.3
        for entity in claim.entities:
            entity_text = entity["text"].lower()
            if entity_text in title or entity_text in snippet:
                relevance += 0.2
        return min(relevance, 1.0)

    def _analyze_source_stance(
        self, source_data: Dict[str, Any], claim: FactualClaim
    ) -> Tuple[bool, bool]:
        content = f"{source_data.get('title', '').lower()} {source_data.get('snippet', '').lower()}"
        support_keywords = [
            "confirme",
            "prouve",
            "démontre",
            "établit",
            "vérifie",
            "exact",
            "correct",
            "vrai",
        ]
        contradict_keywords = [
            "faux",
            "erroné",
            "inexact",
            "contredit",
            "réfute",
            "dément",
            "infirme",
            "nie",
        ]
        supports = any(keyword in content for keyword in support_keywords)
        contradicts = any(keyword in content for keyword in contradict_keywords)
        return supports, contradicts

    def _parse_publication_date(self, date_str: Optional[str]) -> Optional[datetime]:
        if not date_str:
            return None
        for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y"]:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None

    def _determine_verification_status(
        self, sources: List[VerificationSource], claim: FactualClaim
    ) -> Tuple[VerificationStatus, float, str, str]:
        if not sources:
            return (
                VerificationStatus.INSUFFICIENT_INFO,
                0.0,
                "Information insuffisante",
                "Aucune source fiable trouvée.",
            )

        total_support, total_contradiction, total_weight = 0.0, 0.0, 0.0
        reliability_weights = {
            SourceReliability.HIGHLY_RELIABLE: 1.0,
            SourceReliability.MODERATELY_RELIABLE: 0.7,
            SourceReliability.QUESTIONABLE: 0.3,
            SourceReliability.UNRELIABLE: 0.1,
            SourceReliability.UNKNOWN: 0.5,
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
                "Sources non pertinentes.",
            )

        support_ratio = total_support / total_weight
        contradiction_ratio = total_contradiction / total_weight

        if support_ratio >= 0.7:
            return (
                VerificationStatus.VERIFIED_TRUE,
                support_ratio,
                "Vérifiée vraie",
                f"Support: {support_ratio:.2f}",
            )
        elif contradiction_ratio >= 0.7:
            return (
                VerificationStatus.VERIFIED_FALSE,
                contradiction_ratio,
                "Vérifiée fausse",
                f"Contradiction: {contradiction_ratio:.2f}",
            )
        elif support_ratio >= 0.4 and contradiction_ratio <= 0.2:
            return (
                VerificationStatus.PARTIALLY_TRUE,
                support_ratio,
                "Partiellement vraie",
                f"Support partiel: {support_ratio:.2f}",
            )
        elif support_ratio >= 0.3 and contradiction_ratio >= 0.3:
            return (
                VerificationStatus.DISPUTED,
                1.0 - abs(support_ratio - contradiction_ratio),
                "Disputée",
                f"Sources contradictoires.",
            )
        else:
            return (
                VerificationStatus.UNVERIFIABLE,
                0.3,
                "Non vérifiable",
                "Preuves insuffisantes.",
            )

    def _analyze_fallacy_implications(
        self,
        claim: FactualClaim,
        status: VerificationStatus,
        sources: List[VerificationSource],
    ) -> List[Dict[str, Any]]:
        implications = []
        if status == VerificationStatus.VERIFIED_FALSE:
            if any(w in claim.claim_text.lower() for w in ["tous", "jamais", "aucun"]):
                implications.append(
                    {"potential_fallacy": "Généralisation hâtive", "confidence": 0.8}
                )
            if claim.claim_type.value == "statistical":
                implications.append(
                    {"potential_fallacy": "Statistiques incorrectes", "confidence": 0.9}
                )
        return implications

    def _generate_cache_key(self, claim: FactualClaim) -> str:
        return f"fact_check_{hash(claim.claim_text)}_{claim.claim_type.value}"

    def _get_cached_result(self, cache_key: str) -> Optional[FactVerificationResult]:
        if cache_key in self._verification_cache:
            cached_data = self._verification_cache[cache_key]
            if datetime.now() - cached_data["timestamp"] < self._cache_expiry:
                return cached_data["result"]
            else:
                del self._verification_cache[cache_key]
        return None

    def _cache_result(self, cache_key: str, result: FactVerificationResult):
        self._verification_cache[cache_key] = {
            "result": result,
            "timestamp": datetime.now(),
        }
        if len(self._verification_cache) > 100:
            oldest_key = min(
                self._verification_cache,
                key=lambda k: self._verification_cache[k]["timestamp"],
            )
            del self._verification_cache[oldest_key]
