# -*- coding: utf-8 -*-
"""
Service de taxonomie des sophismes — module de compatibilité.

Ce module fournit une interface de service pour la taxonomie des sophismes,
déléguant au plugin TaxonomyExplorerPlugin et au TaxonomySophismDetector.

Historique: Le module original (PR #8, Candy Nguyen) a été refactoré en plugin
(commit 80008c43, 2025-07-31). Ce shim restaure l'API de service attendue par
les tests et les modules dépendants (fallacy_family_definitions.py, etc.).
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

# Re-export FallacyFamily Enum from the canonical definition in the analyzer module
from argumentation_analysis.agents.tools.analysis.fallacy_family_analyzer import (
    FallacyFamily,
)

# Import du détecteur — also exposed as module-level name for unittest.mock.patch
from argumentation_analysis.agents.core.informal.taxonomy_sophism_detector import (
    get_global_detector,
    TaxonomySophismDetector,
)

logger = logging.getLogger(__name__)


@dataclass
class ClassifiedFallacy:
    """Sophisme classifié avec sa famille et métadonnées."""

    taxonomy_key: int
    name: str
    nom_vulgarise: str
    family: Any  # FallacyFamily enum or str
    confidence: float
    description: str
    severity: str
    context_relevance: float
    family_pattern_score: float
    detection_method: str

    def to_dict(self) -> Dict[str, Any]:
        """Convertit le sophisme classifié en dictionnaire."""
        family_value = self.family
        if hasattr(family_value, "value"):
            family_value = family_value.value
        return {
            "taxonomy_key": self.taxonomy_key,
            "name": self.name,
            "nom_vulgarise": self.nom_vulgarise,
            "family": family_value,
            "confidence": self.confidence,
            "description": self.description,
            "severity": self.severity,
            "context_relevance": self.context_relevance,
            "family_pattern_score": self.family_pattern_score,
            "detection_method": self.detection_method,
        }


class FallacyTaxonomyManager:
    """
    Gestionnaire de taxonomie des sophismes.

    Fournit l'accès aux 8 familles de sophismes et à la détection
    via le TaxonomySophismDetector sous-jacent.
    """

    def __init__(self):
        self.logger = logging.getLogger("FallacyTaxonomyManager")
        self.families = set(FallacyFamily)
        self.detector = get_global_detector()
        self.logger.info(
            f"FallacyTaxonomyManager initialisé avec {len(self.families)} familles"
        )

    def detect_fallacies_with_families(
        self, text: str, max_fallacies: int = 20
    ) -> List[ClassifiedFallacy]:
        """Détecte les sophismes dans un texte et les classifie par familles."""
        detected = self.detector.detect_sophisms_from_taxonomy(text, max_fallacies)
        classified = []
        for sophism in detected:
            classified.append(
                ClassifiedFallacy(
                    taxonomy_key=sophism.get("taxonomy_key", 0),
                    name=sophism.get("name", ""),
                    nom_vulgarise=sophism.get("nom_vulgarise", ""),
                    family=FallacyFamily.LANGUAGE_AMBIGUITY,  # Default family
                    confidence=sophism.get("confidence", 0.0),
                    description=sophism.get("description", ""),
                    severity="Moyenne",
                    context_relevance=0.5,
                    family_pattern_score=0.5,
                    detection_method="taxonomy_service",
                )
            )
        return classified


# Singleton instance
_global_taxonomy_manager = None


def get_taxonomy_manager() -> FallacyTaxonomyManager:
    """Récupère l'instance globale du gestionnaire de taxonomie (singleton)."""
    global _global_taxonomy_manager
    if _global_taxonomy_manager is None:
        _global_taxonomy_manager = FallacyTaxonomyManager()
    return _global_taxonomy_manager
