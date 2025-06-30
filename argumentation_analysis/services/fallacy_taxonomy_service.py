# -*- coding: utf-8 -*-
"""
Service de gestion de la taxonomie des sophismes avec classification par familles.

Ce module implémente le FallacyTaxonomyManager qui étend le système existant
pour intégrer la nouvelle taxonomie organisée en 8 familles de sophismes
selon le PRD d'intégration du fact-checking.
"""

import logging
from typing import Dict, List, Any, Optional, Set
from enum import Enum
from dataclasses import dataclass
import pandas as pd

# Import des composants existants
from ..agents.core.informal.taxonomy_sophism_detector import TaxonomySophismDetector, get_global_detector

logger = logging.getLogger(__name__)


class FallacyFamily(Enum):
    """Énumération des 8 familles de sophismes selon le PRD."""
    
    AUTHORITY_POPULARITY = "authority_popularity"
    EMOTIONAL_APPEALS = "emotional_appeals"
    GENERALIZATION_CAUSALITY = "generalization_causality"
    DIVERSION_ATTACK = "diversion_attack"
    FALSE_DILEMMA_SIMPLIFICATION = "false_dilemma_simplification"
    LANGUAGE_AMBIGUITY = "language_ambiguity"
    STATISTICAL_PROBABILISTIC = "statistical_probabilistic"
    AUDIO_ORAL_CONTEXT = "audio_oral_context"


@dataclass
class FallacyFamilyInfo:
    """Information détaillée sur une famille de sophismes."""
    
    family: FallacyFamily
    name_fr: str
    name_en: str
    description: str
    keywords: List[str]
    severity_weight: float
    common_contexts: List[str]


@dataclass
class ClassifiedFallacy:
    """Sophisme classifié avec sa famille et métadonnées."""
    
    taxonomy_key: int
    name: str
    nom_vulgarise: str
    family: FallacyFamily
    confidence: float
    description: str
    severity: str
    context_relevance: float
    family_pattern_score: float
    detection_method: str


class FallacyTaxonomyManager:
    """
    Gestionnaire de la taxonomie des sophismes avec classification par familles.
    
    Cette classe étend le TaxonomySophismDetector existant pour intégrer
    la nouvelle taxonomie organisée en 8 familles selon le PRD.
    """
    
    def __init__(self, taxonomy_file_path: Optional[str] = None):
        """
        Initialise le gestionnaire de taxonomie.
        
        :param taxonomy_file_path: Chemin optionnel vers le fichier de taxonomie
        """
        self.logger = logging.getLogger("FallacyTaxonomyManager")
        self.detector = get_global_detector(taxonomy_file_path)
        
        # Initialiser les familles de sophismes
        self.families = self._initialize_fallacy_families()
        
        # Cache pour les mappings taxonomie -> famille
        self._family_mapping_cache = {}
        self._initialize_family_mappings()
        
        self.logger.info("FallacyTaxonomyManager initialisé avec 8 familles de sophismes")
    
    def _initialize_fallacy_families(self) -> Dict[FallacyFamily, FallacyFamilyInfo]:
        """Initialise les définitions des 8 familles de sophismes."""
        
        families = {
            FallacyFamily.AUTHORITY_POPULARITY: FallacyFamilyInfo(
                family=FallacyFamily.AUTHORITY_POPULARITY,
                name_fr="Sophismes d'appel à l'autorité et à la popularité",
                name_en="Authority and Popularity Fallacies",
                description="Sophismes basés sur l'invocation d'autorités non qualifiées ou sur la popularité",
                keywords=["autorité", "expert", "tout le monde", "popularité", "tradition", "nouveauté"],
                severity_weight=0.7,
                common_contexts=["politique", "publicité", "débat public"]
            ),
            
            FallacyFamily.EMOTIONAL_APPEALS: FallacyFamilyInfo(
                family=FallacyFamily.EMOTIONAL_APPEALS,
                name_fr="Sophismes d'appel aux émotions",
                name_en="Emotional Appeal Fallacies",
                description="Sophismes utilisant les émotions pour persuader plutôt que la logique",
                keywords=["peur", "pitié", "honte", "colère", "espoir", "flatterie"],
                severity_weight=0.8,
                common_contexts=["politique", "marketing", "plaidoyer"]
            ),
            
            FallacyFamily.GENERALIZATION_CAUSALITY: FallacyFamilyInfo(
                family=FallacyFamily.GENERALIZATION_CAUSALITY,
                name_fr="Sophismes de généralisation et de causalité",
                name_en="Generalization and Causality Fallacies",
                description="Erreurs de raisonnement sur les généralisations et relations causales",
                keywords=["tous", "toujours", "jamais", "cause", "conséquence", "corrélation"],
                severity_weight=0.9,
                common_contexts=["scientifique", "statistique", "recherche"]
            ),
            
            FallacyFamily.DIVERSION_ATTACK: FallacyFamilyInfo(
                family=FallacyFamily.DIVERSION_ATTACK,
                name_fr="Sophismes de diversion et d'attaque",
                name_en="Diversion and Attack Fallacies",
                description="Tactiques pour détourner l'attention ou attaquer la personne",
                keywords=["personnellement", "attaque", "hypocrite", "diversion", "hors-sujet"],
                severity_weight=0.6,
                common_contexts=["débat", "politique", "controverse"]
            ),
            
            FallacyFamily.FALSE_DILEMMA_SIMPLIFICATION: FallacyFamilyInfo(
                family=FallacyFamily.FALSE_DILEMMA_SIMPLIFICATION,
                name_fr="Sophismes de faux dilemme et de simplification",
                name_en="False Dilemma and Simplification Fallacies",
                description="Présentation de choix artificiellement limités ou simplifications excessives",
                keywords=["soit", "ou bien", "seulement deux", "simple", "complexe"],
                severity_weight=0.7,
                common_contexts=["politique", "éthique", "choix stratégiques"]
            ),
            
            FallacyFamily.LANGUAGE_AMBIGUITY: FallacyFamilyInfo(
                family=FallacyFamily.LANGUAGE_AMBIGUITY,
                name_fr="Sophismes de langage et d'ambiguïté",
                name_en="Language and Ambiguity Fallacies",
                description="Utilisation trompeuse du langage et créations d'ambiguïtés",
                keywords=["équivoque", "ambiguïté", "double sens", "jeu de mots"],
                severity_weight=0.5,
                common_contexts=["rhétorique", "légal", "littéraire"]
            ),
            
            FallacyFamily.STATISTICAL_PROBABILISTIC: FallacyFamilyInfo(
                family=FallacyFamily.STATISTICAL_PROBABILISTIC,
                name_fr="Sophismes statistiques et probabilistes",
                name_en="Statistical and Probabilistic Fallacies",
                description="Erreurs dans l'interprétation des statistiques et probabilités",
                keywords=["statistique", "pourcentage", "probabilité", "échantillon", "corrélation"],
                severity_weight=0.9,
                common_contexts=["scientifique", "médical", "économique"]
            ),
            
            FallacyFamily.AUDIO_ORAL_CONTEXT: FallacyFamilyInfo(
                family=FallacyFamily.AUDIO_ORAL_CONTEXT,
                name_fr="Sophismes spécifiques au contexte audio/oral",
                name_en="Audio/Oral Context Fallacies",
                description="Sophismes spécifiques aux communications orales et audio",
                keywords=["interruption", "volume", "ton", "débit", "intonation"],
                severity_weight=0.4,
                common_contexts=["débat oral", "interview", "présentation"]
            )
        }
        
        return families
    
    def _initialize_family_mappings(self):
        """Initialise les mappings entre la taxonomie existante et les nouvelles familles."""
        
        # Mapping basé sur les mots-clés et patterns de noms
        family_patterns = {
            FallacyFamily.AUTHORITY_POPULARITY: [
                "ad verecundiam", "appel à l'autorité", "ad populum", "appel à la popularité",
                "argumentum ad antiquitatem", "tradition", "argumentum ad novitatem", "nouveauté"
            ],
            
            FallacyFamily.EMOTIONAL_APPEALS: [
                "ad metum", "appel à la peur", "ad misericordiam", "appel à la pitié",
                "ad captandum", "flatterie", "ad pudorem", "honte", "appel aux émotions"
            ],
            
            FallacyFamily.GENERALIZATION_CAUSALITY: [
                "généralisation hâtive", "secundum quid", "post hoc", "pente glissante",
                "composition", "division", "causalité", "corrélation"
            ],
            
            FallacyFamily.DIVERSION_ATTACK: [
                "ad hominem", "homme de paille", "straw man", "tu quoque",
                "hareng rouge", "red herring", "diversion"
            ],
            
            FallacyFamily.FALSE_DILEMMA_SIMPLIFICATION: [
                "faux dilemme", "false dilemma", "vrai écossais", "no true scotsman",
                "ad ignorantiam", "appel à l'ignorance", "petitio principii", "circulaire"
            ],
            
            FallacyFamily.LANGUAGE_AMBIGUITY: [
                "équivocation", "amphibologie", "accent", "composition lexicale",
                "ambiguïté", "double sens"
            ],
            
            FallacyFamily.STATISTICAL_PROBABILISTIC: [
                "sophisme du joueur", "gambler's fallacy", "biais de confirmation",
                "base rate fallacy", "échantillon biaisé", "statistique"
            ],
            
            FallacyFamily.AUDIO_ORAL_CONTEXT: [
                "interruption", "intimidation", "volume", "débit rapide",
                "manipulation", "intonation", "oral"
            ]
        }
        
        # Construire le cache de mapping
        try:
            df = self.detector._get_taxonomy_df()
            
            for pk, row in df.iterrows():
                name = str(row.get('Name', '')).lower()
                nom_vulgarise = str(row.get('nom_vulgarisé', '')).lower()
                description = str(row.get('text_fr', '')).lower()
                
                best_family = None
                best_score = 0.0
                
                for family, patterns in family_patterns.items():
                    score = 0.0
                    
                    for pattern in patterns:
                        pattern_lower = pattern.lower()
                        if pattern_lower in name:
                            score += 0.8
                        if pattern_lower in nom_vulgarise:
                            score += 0.9
                        if pattern_lower in description:
                            score += 0.3
                    
                    if score > best_score:
                        best_score = score
                        best_family = family
                
                # Seuil minimum pour assigner une famille
                if best_score >= 0.3:
                    self._family_mapping_cache[int(pk)] = best_family
            
            self.logger.info(f"Mappings famille initialisés: {len(self._family_mapping_cache)} sophismes classifiés")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation des mappings: {e}")
    
    def classify_fallacy_by_family(self, taxonomy_key: int) -> Optional[FallacyFamily]:
        """
        Classifie un sophisme dans une famille.
        
        :param taxonomy_key: Clé taxonomique du sophisme
        :return: Famille du sophisme ou None si non classifiable
        """
        return self._family_mapping_cache.get(taxonomy_key)
    
    def detect_fallacies_with_families(self, text: str, max_fallacies: int = 10) -> List[ClassifiedFallacy]:
        """
        Détecte les sophismes et les classifie par familles.
        
        :param text: Texte à analyser
        :param max_fallacies: Nombre maximum de sophismes à détecter
        :return: Liste des sophismes classifiés par famille
        """
        try:
            # Détecter avec le système existant
            detected_sophisms = self.detector.detect_sophisms_from_taxonomy(text, max_fallacies)
            
            classified_fallacies = []
            
            for sophism in detected_sophisms:
                taxonomy_key = sophism['taxonomy_key']
                family = self.classify_fallacy_by_family(taxonomy_key)
                
                if family:
                    # Calculer le score de pattern familial
                    family_info = self.families[family]
                    family_score = self._calculate_family_pattern_score(text, family_info)
                    
                    # Ajuster la confiance basée sur le contexte familial
                    context_relevance = self._calculate_context_relevance(text, family_info)
                    
                    classified_fallacy = ClassifiedFallacy(
                        taxonomy_key=taxonomy_key,
                        name=sophism['name'],
                        nom_vulgarise=sophism['nom_vulgarise'],
                        family=family,
                        confidence=sophism['confidence'],
                        description=sophism['description'],
                        severity=self._calculate_family_severity(family, sophism['confidence']),
                        context_relevance=context_relevance,
                        family_pattern_score=family_score,
                        detection_method=f"taxonomy_family_{family.value}"
                    )
                    
                    classified_fallacies.append(classified_fallacy)
                else:
                    # Sophisme non classifié dans les 8 familles
                    classified_fallacy = ClassifiedFallacy(
                        taxonomy_key=taxonomy_key,
                        name=sophism['name'],
                        nom_vulgarise=sophism['nom_vulgarise'],
                        family=None,
                        confidence=sophism['confidence'],
                        description=sophism['description'],
                        severity="Indéterminée",
                        context_relevance=0.5,
                        family_pattern_score=0.0,
                        detection_method="taxonomy_unclassified"
                    )
                    
                    classified_fallacies.append(classified_fallacy)
            
            # Trier par confiance et score familial
            classified_fallacies.sort(
                key=lambda x: (x.confidence + x.family_pattern_score) / 2,
                reverse=True
            )
            
            self.logger.info(f"Classification terminée: {len(classified_fallacies)} sophismes classifiés")
            return classified_fallacies
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la classification par familles: {e}")
            return []
    
    def _calculate_family_pattern_score(self, text: str, family_info: FallacyFamilyInfo) -> float:
        """Calcule le score de correspondance avec les patterns de la famille."""
        
        text_lower = text.lower()
        score = 0.0
        
        for keyword in family_info.keywords:
            if keyword.lower() in text_lower:
                score += 0.1
        
        return min(score, 1.0)
    
    def _calculate_context_relevance(self, text: str, family_info: FallacyFamilyInfo) -> float:
        """Calcule la pertinence contextuelle d'une famille dans le texte."""
        
        text_lower = text.lower()
        relevance = 0.0
        
        for context in family_info.common_contexts:
            if context.lower() in text_lower:
                relevance += 0.2
        
        return min(relevance, 1.0)
    
    def _calculate_family_severity(self, family: FallacyFamily, base_confidence: float) -> str:
        """Calcule la sévérité d'un sophisme basée sur sa famille."""
        
        family_info = self.families[family]
        weighted_score = base_confidence * family_info.severity_weight
        
        if weighted_score >= 0.8:
            return "Critique"
        elif weighted_score >= 0.6:
            return "Haute"
        elif weighted_score >= 0.4:
            return "Moyenne"
        elif weighted_score >= 0.2:
            return "Faible"
        else:
            return "Négligeable"
    
    def get_family_statistics(self, classified_fallacies: List[ClassifiedFallacy]) -> Dict[str, Any]:
        """Génère des statistiques par famille de sophismes."""
        
        family_stats = {}
        total_fallacies = len(classified_fallacies)
        
        if total_fallacies == 0:
            return family_stats
        
        # Compter par famille
        family_counts = {}
        family_confidences = {}
        
        for fallacy in classified_fallacies:
            if fallacy.family:
                family_name = fallacy.family.value
                family_counts[family_name] = family_counts.get(family_name, 0) + 1
                
                if family_name not in family_confidences:
                    family_confidences[family_name] = []
                family_confidences[family_name].append(fallacy.confidence)
        
        # Calculer les statistiques
        for family_enum in FallacyFamily:
            family_name = family_enum.value
            family_info = self.families[family_enum]
            
            count = family_counts.get(family_name, 0)
            percentage = (count / total_fallacies) * 100
            
            confidences = family_confidences.get(family_name, [])
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            family_stats[family_name] = {
                "name_fr": family_info.name_fr,
                "count": count,
                "percentage": round(percentage, 2),
                "average_confidence": round(avg_confidence, 3),
                "severity_weight": family_info.severity_weight,
                "present": count > 0
            }
        
        return family_stats
    
    def get_family_info(self, family: FallacyFamily) -> FallacyFamilyInfo:
        """Retourne les informations détaillées d'une famille."""
        return self.families[family]
    
    def list_all_families(self) -> List[Dict[str, Any]]:
        """Liste toutes les familles de sophismes disponibles."""
        
        families_list = []
        for family_enum, family_info in self.families.items():
            family_dict = {
                "family_id": family_enum.value,
                "name_fr": family_info.name_fr,
                "name_en": family_info.name_en,
                "description": family_info.description,
                "keywords": family_info.keywords,
                "severity_weight": family_info.severity_weight,
                "common_contexts": family_info.common_contexts
            }
            families_list.append(family_dict)
        
        return families_list
    
    def search_fallacies_by_family(self, family: FallacyFamily, max_results: int = 20) -> List[Dict[str, Any]]:
        """Recherche tous les sophismes d'une famille donnée."""
        
        family_fallacies = []
        
        for taxonomy_key, mapped_family in self._family_mapping_cache.items():
            if mapped_family == family:
                details = self.detector.get_sophism_details_by_key(taxonomy_key)
                if not details.get('error'):
                    family_fallacies.append({
                        'taxonomy_key': taxonomy_key,
                        'name': details.get('Name', ''),
                        'nom_vulgarise': details.get('nom_vulgarisé', ''),
                        'description': details.get('text_fr', ''),
                        'family': family.value
                    })
        
        return family_fallacies[:max_results]


# Instance globale du gestionnaire de taxonomie
_global_taxonomy_manager = None

def get_taxonomy_manager(taxonomy_file_path: Optional[str] = None) -> FallacyTaxonomyManager:
    """
    Récupère l'instance globale du gestionnaire de taxonomie (singleton pattern).
    
    :param taxonomy_file_path: Chemin optionnel vers le fichier de taxonomie
    :return: Instance globale du gestionnaire
    """
    global _global_taxonomy_manager
    if _global_taxonomy_manager is None:
        _global_taxonomy_manager = FallacyTaxonomyManager(taxonomy_file_path=taxonomy_file_path)
    return _global_taxonomy_manager