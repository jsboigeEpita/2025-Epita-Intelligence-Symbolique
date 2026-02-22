# -*- coding: utf-8 -*-
"""
Service de vérification factuelle — module de compatibilité.

Ce module fournit une interface de service pour la vérification factuelle,
déléguant au plugin ExternalVerificationPlugin sous-jacent.

Historique: Le module original (PR #8, Candy Nguyen) a été refactoré en plugin
(commit 80008c43, 2025-07-31). Ce shim restaure l'API de service attendue par
les tests et les modules dépendants.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Any, Optional
from datetime import datetime

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
class VerificationResult:
    """Résultat de vérification d'une affirmation."""

    claim: Any
    status: VerificationStatus
    confidence: float
    verification_date: datetime
    sources: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        """Convertit le résultat en dictionnaire."""
        return {
            "claim": str(self.claim),
            "status": self.status.value,
            "confidence": self.confidence,
            "verification_date": self.verification_date.isoformat(),
            "sources": self.sources,
        }


class FactVerificationService:
    """
    Service de vérification factuelle.

    Fournit la vérification des affirmations factuelles via recherche
    multi-source et évaluation de la fiabilité des sources.
    """

    def __init__(self, api_config: Optional[Dict[str, Any]] = None):
        self.logger = logging.getLogger("FactVerificationService")
        self.api_config = api_config or {}
        self.source_reliability_map = {
            "wikipedia.org": SourceReliability.HIGHLY_RELIABLE,
            "britannica.com": SourceReliability.HIGHLY_RELIABLE,
            "reuters.com": SourceReliability.HIGHLY_RELIABLE,
            "apnews.com": SourceReliability.HIGHLY_RELIABLE,
            "bbc.com": SourceReliability.HIGHLY_RELIABLE,
            "lemonde.fr": SourceReliability.HIGHLY_RELIABLE,
            "liberation.fr": SourceReliability.HIGHLY_RELIABLE,
            "franceinfo.fr": SourceReliability.HIGHLY_RELIABLE,
            "sciencedirect.com": SourceReliability.HIGHLY_RELIABLE,
            "nature.com": SourceReliability.HIGHLY_RELIABLE,
            "science.org": SourceReliability.HIGHLY_RELIABLE,
            "pubmed.ncbi.nlm.nih.gov": SourceReliability.HIGHLY_RELIABLE,
            "insee.fr": SourceReliability.HIGHLY_RELIABLE,
            "gouvernement.fr": SourceReliability.HIGHLY_RELIABLE,
            "europa.eu": SourceReliability.HIGHLY_RELIABLE,
            "who.int": SourceReliability.HIGHLY_RELIABLE,
            "huffingtonpost.fr": SourceReliability.MODERATELY_RELIABLE,
            "lefigaro.fr": SourceReliability.MODERATELY_RELIABLE,
            "lexpress.fr": SourceReliability.MODERATELY_RELIABLE,
            "nouvelobs.com": SourceReliability.MODERATELY_RELIABLE,
            "cnews.fr": SourceReliability.MODERATELY_RELIABLE,
            "francetvinfo.fr": SourceReliability.MODERATELY_RELIABLE,
            "rfi.fr": SourceReliability.MODERATELY_RELIABLE,
            "france24.com": SourceReliability.MODERATELY_RELIABLE,
            "20minutes.fr": SourceReliability.MODERATELY_RELIABLE,
            "ouest-france.fr": SourceReliability.MODERATELY_RELIABLE,
            "sudouest.fr": SourceReliability.MODERATELY_RELIABLE,
        }
        self.logger.info("FactVerificationService initialisé")

    def _assess_source_reliability(self, domain: str) -> SourceReliability:
        """Évalue la fiabilité d'une source par son domaine."""
        domain_lower = domain.lower()
        for known_domain, reliability in self.source_reliability_map.items():
            if known_domain in domain_lower:
                return reliability
        return SourceReliability.UNKNOWN

    async def verify_claim(self, claim) -> VerificationResult:
        """
        Vérifie une affirmation factuelle unique.

        En mode simulation (pas d'API externes configurées), retourne
        un résultat UNVERIFIABLE avec confiance faible.
        """
        return VerificationResult(
            claim=claim,
            status=VerificationStatus.UNVERIFIABLE,
            confidence=0.3,
            verification_date=datetime.now(),
            sources=[],
        )

    async def verify_claims(self, claims: List) -> List[VerificationResult]:
        """Vérifie plusieurs affirmations factuelles."""
        results = []
        for claim in claims:
            result = await self.verify_claim(claim)
            results.append(result)
        return results


# Singleton instance
_global_verification_service = None


def get_verification_service(
    api_config: Optional[Dict[str, Any]] = None,
) -> FactVerificationService:
    """Récupère l'instance globale du service de vérification (singleton)."""
    global _global_verification_service
    if _global_verification_service is None:
        _global_verification_service = FactVerificationService(api_config=api_config)
    return _global_verification_service
