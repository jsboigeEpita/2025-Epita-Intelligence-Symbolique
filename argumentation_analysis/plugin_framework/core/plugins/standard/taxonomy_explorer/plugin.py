# -*- coding: utf-8 -*-
"""
Plugin pour l'exploration de la taxonomie des sophismes.

Ce plugin centralise la logique d'accès à la taxonomie des sophismes,
y compris la gestion des familles de sophismes et la recherche d'informations détaillées.
"""

import logging
import os
import re
from typing import Dict, List, Any, Optional

import yaml
from pydantic import BaseModel

from argumentation_analysis.plugin_framework.core.plugins.interfaces import BasePlugin
from argumentation_analysis.utils.taxonomy_tree import taxonomy_parent_paths

# Lettres minuscules (accentuées comprises) pour la frontière de mot des
# patterns (#2602) — le texte est lower() avant le test.
_WORD_LETTERS = "a-zà-öø-ÿœæ"


def _contains_at_word_boundary(pattern_lower: str, text_lower: str) -> bool:
    """True si ``pattern_lower`` apparaît en mot entier dans ``text_lower``.

    #2602 : la frontière est une non-lettre (ou un bord) de chaque côté —
    « oral » ne matche plus à l'intérieur de « morale ». Un pattern qui n'est
    pas sous-chaîne ne peut pas être mot entier : le test rapide ``in`` filtre
    avant que la regex ne courre.
    """
    if not pattern_lower or not text_lower or pattern_lower not in text_lower:
        return False
    regex = re.compile(
        rf"(?<![{_WORD_LETTERS}]){re.escape(pattern_lower)}(?![{_WORD_LETTERS}])"
    )
    return regex.search(text_lower) is not None


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
        """Construit le cache familles : patterns à frontière de mot, puis héritage.

        #2602 : les patterns ne matchent plus à l'intérieur d'un autre mot
        (« oral » dans « morale ») ; un nœud sans hit de pattern hérite
        ensuite de son plus proche ancêtre mappé (la relation parent
        ``path``/``depth`` de la taxonomie, lue par ``taxonomy_parent_paths``).
        """
        df = self.detector._get_taxonomy_df()

        pattern_mapped = 0
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
                    if _contains_at_word_boundary(pattern_lower, name):
                        score += 0.8
                    if _contains_at_word_boundary(pattern_lower, nom_vulgarise):
                        score += 0.9
                    if _contains_at_word_boundary(pattern_lower, description):
                        score += 0.3

                if score > best_score:
                    best_score = score
                    best_family_id = family_id

            if best_score >= 0.3:
                self._family_mapping_cache[int(pk)] = best_family_id
                pattern_mapped += 1

        inherited = self._inherit_from_mapped_ancestors(df)
        self.logger.info(
            f"Mappings famille initialisés : {pattern_mapped} par pattern + "
            f"{inherited} hérités d'un ancêtre mappé = "
            f"{len(self._family_mapping_cache)} sophismes classifiés."
        )

    def _inherit_from_mapped_ancestors(self, df: Any) -> int:
        """Chaque nœud non mappé prend la famille de son plus proche ancêtre mappé.

        Retourne le nombre de nœuds ainsi hérités. Un nœud sans ancêtre mappé
        reste hors du cache : pas de famille inventée.
        """
        parent_paths = taxonomy_parent_paths(df)
        path_to_pk = {str(path): int(pk) for pk, path in df["path"].items()}

        def parent_of(pk: int) -> Optional[int]:
            parent_path = parent_paths.loc[pk]
            if parent_path is None or parent_path != parent_path:  # None or NaN
                return None
            return path_to_pk.get(str(parent_path))

        added = 0
        for pk in df.index:
            pk = int(pk)
            if pk in self._family_mapping_cache:
                continue
            seen = {pk}
            ancestor = parent_of(pk)
            while ancestor is not None and ancestor not in seen:
                if ancestor in self._family_mapping_cache:
                    self._family_mapping_cache[pk] = self._family_mapping_cache[
                        ancestor
                    ]
                    added += 1
                    break
                seen.add(ancestor)
                ancestor = parent_of(ancestor)
        return added

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
                self._calculate_contextual_relevance(text, family_info)
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
        """Génère des statistiques par famille à partir d'une liste de sophismes classifiés.

        #2602 : une détection sans famille est comptée dans l'entrée
        ``unclassified`` (nombre + clés), pas silencieusement droppée.
        """
        family_stats = {}
        total_fallacies = len(classified_fallacies)
        if total_fallacies == 0:
            return {}

        family_counts = {fam.family: 0 for fam in self.families.values()}
        family_confidences = {fam.family: [] for fam in self.families.values()}
        unclassified_names: List[str] = []
        unclassified_keys: List[Any] = []
        unclassified_confidences: List[float] = []

        for fallacy in classified_fallacies:
            family_id = fallacy.get("family")
            if family_id in family_counts:
                family_counts[family_id] += 1
                family_confidences[family_id].append(fallacy["confidence"])
            else:
                unclassified_names.append(str(fallacy.get("name", "")))
                unclassified_keys.append(fallacy.get("taxonomy_key"))
                unclassified_confidences.append(float(fallacy.get("confidence", 0.0)))

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

        n_unclassified = len(unclassified_names)
        if n_unclassified:
            family_stats["unclassified"] = {
                "name_fr": "Non classifiée (nœud sans famille)",
                "count": n_unclassified,
                "percentage": round((n_unclassified / total_fallacies) * 100, 2),
                "average_confidence": round(
                    sum(unclassified_confidences) / n_unclassified, 3
                ),
                "severity_weight": 0.0,
                "present": True,
                "names": unclassified_names,
                "taxonomy_keys": unclassified_keys,
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
