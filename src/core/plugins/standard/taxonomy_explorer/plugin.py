# -*- coding: utf-8 -*-
"""
Plugin pour l'exploration de la taxonomie des sophismes.

Ce plugin centralise la logique d'accès à la taxonomie des sophismes,
y compris la gestion des familles de sophismes et la recherche d'informations détaillées.
"""

import logging
import os
from typing import Dict, List, Any, Optional

import yaml
from pydantic import BaseModel


# Les interfaces de plugins doivent être importées depuis leur emplacement standard.
# Le chemin exact pourrait varier, mais nous suivons le plan.
# from core.plugins.interfaces import BasePlugin
# En attendant la structure finale, on utilise une classe de base factice.
class BasePlugin:
    def __init__(self):
        self.name = "BasePlugin"


# L'ancien détecteur est une dépendance clé. Son chemin doit être stable.
from argumentation_analysis.agents.core.informal.taxonomy_sophism_detector import (
    get_global_detector,
    TaxonomySophismDetector,
)


# Définition des modèles de données Pydantic pour des contrats clairs
class FallacyFamily(BaseModel):
    """Modèle de données pour une famille de sophismes."""

    family: str
    name_fr: str
    name_en: str
    description: str
    keywords: List[str]
    severity_weight: float
    common_contexts: List[str]
    patterns: List[str]


class ClassifiedFallacy(BaseModel):
    """Sophisme classifié avec sa famille et métadonnées."""

    taxonomy_key: int
    name: str
    nom_vulgarise: str
    family: Optional[str] = None
    confidence: float
    description: str
    severity: str
    context_relevance: float
    family_pattern_score: float
    detection_method: str


class TaxonomyExplorerPlugin(BasePlugin):
    """
    Implémentation du plugin d'exploration de la taxonomie.
    """

    def __init__(self):
        """
        Initialise le plugin, charge les familles de sophismes et le détecteur de base.
        """
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.name = "taxonomy_explorer"

        self.families: Dict[str, FallacyFamily] = {}
        self._family_mapping_cache: Dict[int, str] = {}

        self.detector: TaxonomySophismDetector = get_global_detector()

        try:
            self._load_families()
            self._initialize_family_mappings()
            self.logger.info("TaxonomyExplorerPlugin initialisé avec succès.")
        except Exception as e:
            self.logger.critical(
                f"Échec de l'initialisation du TaxonomyExplorerPlugin: {e}",
                exc_info=True,
            )
            raise

    def _load_families(self):
        """Charge les définitions des familles depuis le fichier YAML externe."""
        families_path = os.path.join(
            os.path.dirname(__file__), "data", "fallacy_families.yaml"
        )
        self.logger.info(
            f"Chargement des familles de sophismes depuis : {families_path}"
        )

        with open(families_path, "r", encoding="utf-8") as f:
            families_data = yaml.safe_load(f)

        for family_data in families_data:
            family = FallacyFamily(**family_data)
            self.families[family.family] = family

        self.logger.info(f"{len(self.families)} familles de sophismes chargées.")

    def _initialize_family_mappings(self):
        """Construit un cache qui mappe chaque sophisme de la taxonomie principale à une famille."""
        df = self.detector._get_taxonomy_df()

        for pk, row in df.iterrows():
            best_family_id = None
            best_score = 0.0

            name = str(row.get("Name", "")).lower()
            nom_vulgarise = str(row.get("nom_vulgarisé", "")).lower()
            description = str(row.get("text_fr", "")).lower()

            for family_id, family_info in self.families.items():
                score = 0
                for pattern in family_info.patterns:
                    pattern_lower = pattern.lower()
                    if pattern_lower in name:
                        score += 0.8
                    if pattern_lower in nom_vulgarise:
                        score += 0.9
                    if pattern_lower in description:
                        score += 0.3

                if score > best_score:
                    best_score = score
                    best_family_id = family_id

            if best_score >= 0.3:
                self._family_mapping_cache[int(pk)] = best_family_id

        self.logger.info(
            f"Mappings famille initialisés : {len(self._family_mapping_cache)} sophismes classifiés."
        )

    # --- Implémentation des Capacités ---

    async def list_families(self) -> List[Dict[str, str]]:
        """Liste les familles de sophismes disponibles."""
        return [
            {"family_id": f.family, "name_fr": f.name_fr}
            for f in self.families.values()
        ]

    async def get_family_details(self, family_name: str) -> Optional[Dict[str, Any]]:
        """Retourne les détails d'une famille spécifique."""
        family = self.families.get(family_name)
        return family.model_dump() if family else None

    async def find_fallacies_by_family(self, family_name: str) -> List[Dict[str, Any]]:
        """Trouve tous les sophismes associés à une famille."""
        if family_name not in self.families:
            return []

        results = []
        for key, fam_id in self._family_mapping_cache.items():
            if fam_id == family_name:
                details = self.detector.get_sophism_details_by_key(key)
                if not details.get("error"):
                    results.append(
                        {
                            "taxonomy_key": key,
                            "name": details.get("Name", ""),
                            "nom_vulgarise": details.get("nom_vulgarisé", ""),
                        }
                    )
        return results

    async def get_fallacy_details(self, fallacy_key: int) -> Optional[Dict[str, Any]]:
        """Retourne les détails d'un sophisme par sa clé."""
        details = self.detector.get_sophism_details_by_key(fallacy_key)
        if details.get("error"):
            return None

        details["family_id"] = self._family_mapping_cache.get(fallacy_key)
        return details

    async def get_full_taxonomy(self) -> Dict[str, Any]:
        """Retourne un aperçu de la taxonomie complète."""
        df = self.detector._get_taxonomy_df()
        return {
            "total_fallacies": len(df),
            "classified_fallacies": len(self._family_mapping_cache),
            "families_count": len(self.families),
            "sample": df.head().to_dict(orient="records"),
        }

    async def detect_and_classify(
        self, text: str, max_fallacies: int = 20
    ) -> List[Dict[str, Any]]:
        """Détecte les sophismes dans un texte et les classifie par familles."""
        detected_sophisms = self.detector.detect_sophisms_from_taxonomy(
            text, max_fallacies
        )

        classified_fallacies = []
        for sophism in detected_sophisms:
            family_id = self._family_mapping_cache.get(sophism["taxonomy_key"])
            family_info = self.families.get(family_id) if family_id else None

            # Logique de calcul reprise de l'ancien service
            context_relevance = (
                self._calculate_context_relevance(text, family_info)
                if family_info
                else 0.0
            )
            family_score = (
                self._calculate_family_pattern_score(text, family_info)
                if family_info
                else 0.0
            )
            severity = (
                self._calculate_family_severity(family_info, sophism["confidence"])
                if family_info
                else "Indéterminée"
            )

            classified = ClassifiedFallacy(
                taxonomy_key=sophism["taxonomy_key"],
                name=sophism["name"],
                nom_vulgarise=sophism["nom_vulgarise"],
                family=family_id,
                confidence=sophism["confidence"],
                description=sophism["description"],
                severity=severity,
                context_relevance=context_relevance,
                family_pattern_score=family_score,
                detection_method=(
                    f"taxonomy_family_{family_id}"
                    if family_id
                    else "taxonomy_unclassified"
                ),
            )
            classified_fallacies.append(classified.model_dump())

        classified_fallacies.sort(
            key=lambda x: (x["confidence"] + x["family_pattern_score"]) / 2,
            reverse=True,
        )
        return classified_fallacies

    async def get_family_statistics(
        self, classified_fallacies: List[Dict]
    ) -> Dict[str, Any]:
        """Génère des statistiques par famille à partir d'une liste de sophismes classifiés."""
        family_stats = {}
        total_fallacies = len(classified_fallacies)
        if total_fallacies == 0:
            return {}

        family_counts = {fam.family: 0 for fam in self.families.values()}
        family_confidences = {fam.family: [] for fam in self.families.values()}

        for fallacy in classified_fallacies:
            family_id = fallacy.get("family")
            if family_id in family_counts:
                family_counts[family_id] += 1
                family_confidences[family_id].append(fallacy["confidence"])

        for family_id, family_info in self.families.items():
            count = family_counts[family_id]
            confidences = family_confidences[family_id]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            family_stats[family_id] = {
                "name_fr": family_info.name_fr,
                "count": count,
                "percentage": round((count / total_fallacies) * 100, 2),
                "average_confidence": round(avg_confidence, 3),
                "severity_weight": family_info.severity_weight,
                "present": count > 0,
            }
        return family_stats

    # --- Méthodes privées utilitaires reprises de l'ancien service ---

    def _calculate_family_pattern_score(
        self, text: str, family_info: FallacyFamily
    ) -> float:
        text_lower = text.lower()
        score = sum(
            0.1 for keyword in family_info.keywords if keyword.lower() in text_lower
        )
        return min(score, 1.0)

    def _calculate_contextual_relevance(
        self, text: str, family_info: FallacyFamily
    ) -> float:
        text_lower = text.lower()
        relevance = sum(
            0.2
            for context in family_info.common_contexts
            if context.lower() in text_lower
        )
        return min(relevance, 1.0)

    def _calculate_family_severity(
        self, family_info: FallacyFamily, base_confidence: float
    ) -> str:
        weighted_score = base_confidence * family_info.severity_weight
        if weighted_score >= 0.8:
            return "Critique"
        if weighted_score >= 0.6:
            return "Haute"
        if weighted_score >= 0.4:
            return "Moyenne"
        if weighted_score >= 0.2:
            return "Faible"
        return "Négligeable"
