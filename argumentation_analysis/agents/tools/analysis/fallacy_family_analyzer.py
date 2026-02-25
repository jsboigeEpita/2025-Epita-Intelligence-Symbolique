# -*- coding: utf-8 -*-
"""
Analyseur par famille de sophismes avec intégration du fact-checking.

Ce module implémente l'analyse complète des sophismes par famille,
intégrant la détection, la classification et la vérification factuelle.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

# Import des composants développés
from .fact_claim_extractor import FactClaimExtractor, FactualClaim

# Importations nettoyées
from argumentation_analysis.plugin_framework.core.plugins.standard.taxonomy_explorer.plugin import (
    TaxonomyExplorerPlugin,
    ClassifiedFallacy,
)
from argumentation_analysis.plugin_framework.core.plugins.standard.external_verification.plugin import (
    ExternalVerificationPlugin,
)

logger = logging.getLogger(__name__)


class AnalysisDepth(Enum):
    """Niveaux de profondeur d'analyse."""

    BASIC = "basic"
    STANDARD = "standard"
    COMPREHENSIVE = "comprehensive"
    EXPERT = "expert"


# L'Enum FallacyFamily est maintenant définie ici car elle est sémantiquement liée
# à la logique de cet analyseur.
class FallacyFamily(Enum):
    """Énumération des 8 familles de sophismes."""

    AUTHORITY_POPULARITY = "authority_popularity"
    EMOTIONAL_APPEALS = "emotional_appeals"
    GENERALIZATION_CAUSALITY = "generalization_causality"
    DIVERSION_ATTACK = "diversion_attack"
    FALSE_DILEMMA_SIMPLIFICATION = "false_dilemma_simplification"
    LANGUAGE_AMBIGUITY = "language_ambiguity"
    STATISTICAL_PROBABILISTIC = "statistical_probabilistic"
    AUDIO_ORAL_CONTEXT = "audio_oral_context"


@dataclass
class FamilyAnalysisResult:
    """Résultat d'analyse pour une famille de sophismes."""

    family: FallacyFamily
    fallacies_detected: List[ClassifiedFallacy]
    family_score: float
    severity_assessment: str
    fact_check_integration: Dict[str, Any]
    contextual_relevance: float
    strategic_patterns: List[Dict[str, Any]]
    recommendations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convertit le résultat en dictionnaire."""
        return {
            "family": self.family.value,
            "fallacies_detected": [f.to_dict() for f in self.fallacies_detected],
            "family_score": self.family_score,
            "severity_assessment": self.severity_assessment,
            "fact_check_integration": self.fact_check_integration,
            "contextual_relevance": self.contextual_relevance,
            "strategic_patterns": self.strategic_patterns,
            "recommendations": self.recommendations,
        }


@dataclass
class ComprehensiveAnalysisResult:
    """Résultat d'analyse complète intégrant toutes les familles."""

    text_analyzed: str
    analysis_timestamp: datetime
    analysis_depth: AnalysisDepth
    family_results: Dict[FallacyFamily, FamilyAnalysisResult]
    factual_claims: List[FactualClaim]
    fact_check_results: List[Dict[str, Any]]
    overall_assessment: Dict[str, Any]
    strategic_insights: Dict[str, Any]
    recommendations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convertit le résultat en dictionnaire."""
        return {
            "text_analyzed": (
                self.text_analyzed[:200] + "..."
                if len(self.text_analyzed) > 200
                else self.text_analyzed
            ),
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
            "analysis_depth": self.analysis_depth.value,
            "family_results": {
                family.value: result.to_dict()
                for family, result in self.family_results.items()
            },
            "factual_claims": [claim.to_dict() for claim in self.factual_claims],
            "fact_check_results": self.fact_check_results,
            "overall_assessment": self.overall_assessment,
            "strategic_insights": self.strategic_insights,
            "recommendations": self.recommendations,
        }


class FallacyFamilyAnalyzer:
    """
    Analyseur par famille de sophismes avec intégration fact-checking.

    Cette classe unifie l'analyse des sophismes par famille avec la vérification
    factuelle pour fournir une analyse complète et contextuelle.
    """

    def __init__(
        self,
        taxonomy_plugin: Optional[TaxonomyExplorerPlugin] = None,
        verification_plugin: Optional[ExternalVerificationPlugin] = None,
        api_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialise l'analyseur par famille.

        :param taxonomy_plugin: Instance du plugin de taxonomie (ou None pour singleton).
        :param verification_plugin: Instance du plugin de vérification (ou None pour singleton).
        :param api_config: Configuration des APIs pour le fact-checking.
        """
        self.logger = logging.getLogger("FallacyFamilyAnalyzer")

        # Resolve via singletons if not injected directly
        if taxonomy_plugin is None:
            taxonomy_plugin = get_taxonomy_manager()
        if verification_plugin is None:
            verification_plugin = get_verification_service()

        # Initialiser les composants via injection de dépendances
        self.taxonomy_plugin = taxonomy_plugin
        self.taxonomy_manager = taxonomy_plugin  # backward compat alias
        self.fact_extractor = FactClaimExtractor()
        self.fact_verifier = verification_plugin

        self.logger.info("FallacyFamilyAnalyzer initialisé avec fact-checking intégré")

    async def analyze_comprehensive(
        self, text: str, depth: AnalysisDepth = AnalysisDepth.STANDARD
    ) -> ComprehensiveAnalysisResult:
        """
        Effectue une analyse complète d'un texte par familles de sophismes.

        :param text: Texte à analyser
        :param depth: Profondeur d'analyse
        :return: Résultat d'analyse complète
        """
        start_time = datetime.now()

        try:
            self.logger.info(
                f"Début d'analyse complète (profondeur: {depth.value}) pour un texte de {len(text)} caractères"
            )

            # 1. Extraction des affirmations factuelles
            factual_claims = self.fact_extractor.extract_factual_claims(
                text, max_claims=15
            )
            self.logger.info(
                f"Affirmations factuelles extraites: {len(factual_claims)}"
            )

            # 2. Vérification factuelle en parallèle
            fact_check_results = []
            if factual_claims:
                verification_results = await self.fact_verifier.verify_claims(
                    claims=factual_claims
                )
                fact_check_results = [
                    result.to_dict() for result in verification_results
                ]

            # 3. Détection et classification des sophismes par famille
            classified_fallacies = await self.taxonomy_plugin.detect_and_classify(
                text, max_fallacies=20
            )
            self.logger.info(f"Sophismes classifiés: {len(classified_fallacies)}")

            # 4. Analyse par famille
            family_results = {}
            for family in FallacyFamily:
                family_result = await self._analyze_family(
                    text, family, classified_fallacies, fact_check_results, depth
                )
                if family_result.fallacies_detected or family_result.family_score > 0.2:
                    family_results[family] = family_result

            # 5. Analyse stratégique globale
            overall_assessment = self._compute_overall_assessment(
                family_results, fact_check_results
            )
            strategic_insights = self._extract_strategic_insights(
                family_results, classified_fallacies
            )
            recommendations = self._generate_recommendations(
                family_results, fact_check_results
            )

            # 6. Compilation du résultat
            result = ComprehensiveAnalysisResult(
                text_analyzed=text,
                analysis_timestamp=start_time,
                analysis_depth=depth,
                family_results=family_results,
                factual_claims=factual_claims,
                fact_check_results=fact_check_results,
                overall_assessment=overall_assessment,
                strategic_insights=strategic_insights,
                recommendations=recommendations,
            )

            processing_time = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"Analyse complète terminée en {processing_time:.2f}s")

            return result

        except Exception as e:
            self.logger.error(f"Erreur lors de l'analyse complète: {e}")

            # Retourner un résultat d'erreur minimal
            return ComprehensiveAnalysisResult(
                text_analyzed=text[:100] + "..." if len(text) > 100 else text,
                analysis_timestamp=start_time,
                analysis_depth=depth,
                family_results={},
                factual_claims=[],
                fact_check_results=[],
                overall_assessment={"error": str(e)},
                strategic_insights={},
                recommendations=["Erreur lors de l'analyse, veuillez réessayer"],
            )

    async def _analyze_family(
        self,
        text: str,
        family: FallacyFamily,
        classified_fallacies: List[ClassifiedFallacy],
        fact_check_results: List[Dict[str, Any]],
        depth: AnalysisDepth,
    ) -> FamilyAnalysisResult:
        """Analyse une famille spécifique de sophismes."""

        # Filtrer les sophismes de cette famille
        family_fallacies = [
            fallacy
            for fallacy in classified_fallacies
            if fallacy["family"] == family.value
        ]

        # Calculer le score de famille
        family_score = self._calculate_family_score(text, family, family_fallacies)

        # Évaluer la sévérité
        severity_assessment = self._assess_family_severity(
            family, family_fallacies, family_score
        )

        # Intégrer les résultats de fact-checking
        fact_check_integration = self._integrate_fact_checking(
            family, fact_check_results
        )

        # Calculer la pertinence contextuelle
        contextual_relevance = self._calculate_contextual_relevance(text, family)

        # Analyser les patterns stratégiques
        strategic_patterns = self._analyze_strategic_patterns(
            family, family_fallacies, depth
        )

        # Générer des recommandations spécifiques
        recommendations = self._generate_family_recommendations(
            family, family_fallacies, fact_check_integration
        )

        return FamilyAnalysisResult(
            family=family,
            fallacies_detected=family_fallacies,
            family_score=family_score,
            severity_assessment=severity_assessment,
            fact_check_integration=fact_check_integration,
            contextual_relevance=contextual_relevance,
            strategic_patterns=strategic_patterns,
            recommendations=recommendations,
        )

    def _calculate_family_score(
        self, text: str, family: FallacyFamily, fallacies: List[ClassifiedFallacy]
    ) -> float:
        """Calcule le score global d'une famille dans le texte."""

        if not fallacies:
            # Vérifier quand même la présence de patterns de la famille
            family_info = self.taxonomy_plugin.families.get(family.value)
            if not family_info:
                return 0.0

            text_lower = text.lower()

            keyword_score = 0.0
            for keyword in family_info.keywords:
                if keyword.lower() in text_lower:
                    keyword_score += 0.05

            return min(keyword_score, 0.5)  # Maximum 0.5 sans sophismes détectés

        # Calculer basé sur les sophismes détectés
        total_score = 0.0
        for fallacy in fallacies:
            # Score basé sur la confiance et le score familial
            base_score = (fallacy["confidence"] + fallacy["family_pattern_score"]) / 2

            # Pondération par pertinence contextuelle
            weighted_score = base_score * fallacy["context_relevance"]

            total_score += weighted_score

        # Normaliser par le nombre de sophismes (éviter l'accumulation artificielle)
        normalized_score = total_score / len(fallacies) if fallacies else 0.0

        # Bonus pour la diversité des sophismes dans la famille
        unique_types = len(set(f["name"] for f in fallacies))
        diversity_bonus = min(unique_types * 0.1, 0.3)

        return min(normalized_score + diversity_bonus, 1.0)

    def _assess_family_severity(
        self,
        family: FallacyFamily,
        fallacies: List[ClassifiedFallacy],
        family_score: float,
    ) -> str:
        """Évalue la sévérité d'une famille de sophismes."""

        family_info = self.taxonomy_plugin.families.get(family.value)
        base_severity = family_info.severity_weight if family_info else 0.5

        # Calculer la sévérité pondérée
        weighted_severity = family_score * base_severity

        # Ajuster basé sur le contexte
        context_multiplier = 1.0
        # TODO: Détecter automatiquement le contexte du texte

        final_severity = weighted_severity * context_multiplier

        if final_severity >= 0.8:
            return "Critique"
        elif final_severity >= 0.6:
            return "Haute"
        elif final_severity >= 0.4:
            return "Moyenne"
        elif final_severity >= 0.2:
            return "Faible"
        else:
            return "Négligeable"

    def _integrate_fact_checking(
        self, family: FallacyFamily, fact_check_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Intègre les résultats de fact-checking avec l'analyse des familles."""

        integration = {
            "relevant_fact_checks": 0,
            "verified_false_claims": 0,
            "disputed_claims": 0,
            "fallacy_implications": [],
            "credibility_impact": 0.0,
        }

        for fact_result in fact_check_results:
            # Analyser les implications de sophismes
            fallacy_implications = fact_result.get("fallacy_implications", [])

            for implication in fallacy_implications:
                if implication.get("fallacy_family") == family.value:
                    integration["relevant_fact_checks"] += 1
                    integration["fallacy_implications"].append(implication)

                    # Compter les types de problèmes
                    if fact_result.get("status") == "verified_false":
                        integration["verified_false_claims"] += 1
                    elif fact_result.get("status") == "disputed":
                        integration["disputed_claims"] += 1

        # Calculer l'impact sur la crédibilité
        if integration["relevant_fact_checks"] > 0:
            false_ratio = (
                integration["verified_false_claims"]
                / integration["relevant_fact_checks"]
            )
            disputed_ratio = (
                integration["disputed_claims"] / integration["relevant_fact_checks"]
            )

            integration["credibility_impact"] = (false_ratio * 0.8) + (
                disputed_ratio * 0.4
            )

        return integration

    def _calculate_contextual_relevance(
        self, text: str, family: FallacyFamily
    ) -> float:
        """Calcule la pertinence contextuelle d'une famille."""

        family_info = self.taxonomy_plugin.families.get(family.value)
        if not family_info:
            return 0.0

        text_lower = text.lower()

        relevance = 0.0
        for context in family_info.common_contexts:
            if context.lower() in text_lower:
                relevance += 0.2

        # Analyser les indicateurs contextuels additionnels
        context_indicators = {
            "politique": ["élection", "candidat", "vote", "parti", "gouvernement"],
            "scientifique": ["étude", "recherche", "données", "expérience", "analyse"],
            "commercial": ["produit", "vente", "client", "marque", "publicité"],
            "débat": ["argument", "position", "opinion", "discussion", "point de vue"],
        }

        for context_type, indicators in context_indicators.items():
            if context_type in family_contexts:
                for indicator in indicators:
                    if indicator in text_lower:
                        relevance += 0.1
                        break  # Éviter le double comptage

        return min(relevance, 1.0)

    def _analyze_strategic_patterns(
        self,
        family: FallacyFamily,
        fallacies: List[ClassifiedFallacy],
        depth: AnalysisDepth,
    ) -> List[Dict[str, Any]]:
        """Analyse les patterns stratégiques d'utilisation des sophismes."""

        patterns = []

        if not fallacies:
            return patterns

        # Pattern 1: Concentration de sophismes
        if len(fallacies) >= 3:
            patterns.append(
                {
                    "type": "concentration",
                    "description": f"Utilisation concentrée de {len(fallacies)} sophismes de la famille {family.value}",
                    "severity": "high" if len(fallacies) >= 5 else "medium",
                    "tactical_purpose": "Saturation argumentative pour masquer la faiblesse logique",
                }
            )

        # Pattern 2: Progression de confiance
        if len(fallacies) >= 2:
            confidences = [f["confidence"] for f in fallacies]
            if max(confidences) - min(confidences) > 0.4:
                patterns.append(
                    {
                        "type": "confidence_variation",
                        "description": "Variation significative dans la confiance des détections",
                        "severity": "medium",
                        "tactical_purpose": "Mélange de sophismes évidents et subtils",
                    }
                )

        # Pattern 3: Analyse de profondeur expert
        if depth == AnalysisDepth.EXPERT:
            # Analyser les combinaisons spécifiques
            fallacy_names = [f["name"] for f in fallacies]
            unique_names = set(fallacy_names)

            if len(unique_names) < len(fallacy_names):
                patterns.append(
                    {
                        "type": "repetition",
                        "description": "Répétition de sophismes similaires",
                        "severity": "medium",
                        "tactical_purpose": "Renforcement par répétition",
                    }
                )

        return patterns

    def _generate_family_recommendations(
        self,
        family: FallacyFamily,
        fallacies: List[ClassifiedFallacy],
        fact_check_integration: Dict[str, Any],
    ) -> List[str]:
        """Génère des recommandations spécifiques à une famille."""

        recommendations = []

        if not fallacies and fact_check_integration.get("relevant_fact_checks", 0) == 0:
            return recommendations

        # Recommandations basées sur la famille
        family_specific_recommendations = {
            FallacyFamily.AUTHORITY_POPULARITY: [
                "Vérifier la qualification des autorités citées",
                "Demander des sources primaires",
                "Questionner la représentativité des opinions populaires",
            ],
            FallacyFamily.EMOTIONAL_APPEALS: [
                "Séparer les émotions des faits",
                "Analyser la pertinence émotionnelle",
                "Rechercher des arguments rationnels complémentaires",
            ],
            FallacyFamily.GENERALIZATION_CAUSALITY: [
                "Examiner la taille et représentativité des échantillons",
                "Vérifier les relations causales",
                "Rechercher des variables confondantes",
            ],
            FallacyFamily.STATISTICAL_PROBABILISTIC: [
                "Vérifier les sources des statistiques",
                "Analyser la méthodologie des études",
                "Comparer avec d'autres sources de données",
            ],
        }

        base_recommendations = family_specific_recommendations.get(family, [])
        recommendations.extend(
            base_recommendations[:2]
        )  # Limiter à 2 recommandations de base

        # Recommandations basées sur le fact-checking
        if fact_check_integration.get("verified_false_claims", 0) > 0:
            recommendations.append(
                "Attention: certaines affirmations factuelles sont incorrectes"
            )

        if fact_check_integration.get("credibility_impact", 0) > 0.5:
            recommendations.append(
                "La crédibilité générale est compromise par des erreurs factuelles"
            )

        return recommendations

    def _compute_overall_assessment(
        self,
        family_results: Dict[FallacyFamily, FamilyAnalysisResult],
        fact_check_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Calcule l'évaluation globale de l'analyse."""

        assessment = {
            "total_families_detected": len(family_results),
            "total_fallacies": sum(
                len(result.fallacies_detected) for result in family_results.values()
            ),
            "average_family_score": 0.0,
            "dominant_families": [],
            "overall_severity": "Négligeable",
            "fact_check_summary": {},
            "credibility_score": 1.0,
        }

        if family_results:
            # Calculer le score moyen
            total_score = sum(result.family_score for result in family_results.values())
            assessment["average_family_score"] = total_score / len(family_results)

            # Identifier les familles dominantes
            sorted_families = sorted(
                family_results.items(), key=lambda x: x[1].family_score, reverse=True
            )

            assessment["dominant_families"] = [
                {
                    "family": family.value,
                    "score": result.family_score,
                    "severity": result.severity_assessment,
                }
                for family, result in sorted_families[:3]
                if result.family_score > 0.3
            ]

            # Déterminer la sévérité globale
            max_severity = max(
                result.family_score for result in family_results.values()
            )
            if max_severity >= 0.8:
                assessment["overall_severity"] = "Critique"
            elif max_severity >= 0.6:
                assessment["overall_severity"] = "Haute"
            elif max_severity >= 0.4:
                assessment["overall_severity"] = "Moyenne"
            elif max_severity >= 0.2:
                assessment["overall_severity"] = "Faible"

        # Résumé du fact-checking
        if fact_check_results:
            fact_summary = {
                "total_claims": len(fact_check_results),
                "verified_true": 0,
                "verified_false": 0,
                "disputed": 0,
                "unverifiable": 0,
            }

            for result in fact_check_results:
                status = result.get("status", "unverifiable")
                if status in fact_summary:
                    fact_summary[status] += 1
                else:
                    fact_summary["unverifiable"] += 1

            assessment["fact_check_summary"] = fact_summary

            # Calculer le score de crédibilité
            if fact_summary["total_claims"] > 0:
                false_ratio = (
                    fact_summary["verified_false"] / fact_summary["total_claims"]
                )
                disputed_ratio = fact_summary["disputed"] / fact_summary["total_claims"]

                assessment["credibility_score"] = max(
                    0.0, 1.0 - (false_ratio * 0.8) - (disputed_ratio * 0.4)
                )

        return assessment

    def _extract_strategic_insights(
        self,
        family_results: Dict[FallacyFamily, FamilyAnalysisResult],
        classified_fallacies: List[ClassifiedFallacy],
    ) -> Dict[str, Any]:
        """Extrait des insights stratégiques de l'analyse."""

        insights = {
            "argumentation_strategy": "Non déterminée",
            "sophistication_level": "Basique",
            "target_audience": "Général",
            "rhetorical_goals": [],
            "weakness_indicators": [],
            "manipulation_tactics": [],
        }

        if not family_results:
            return insights

        # Analyser la stratégie argumentative
        dominant_families = [
            family
            for family, result in family_results.items()
            if result.family_score > 0.4
        ]

        if FallacyFamily.EMOTIONAL_APPEALS in dominant_families:
            insights["argumentation_strategy"] = "Persuasion émotionnelle"
            insights["rhetorical_goals"].append("Influence émotionnelle")

        if FallacyFamily.AUTHORITY_POPULARITY in dominant_families:
            insights["argumentation_strategy"] = "Appel à l'autorité"
            insights["rhetorical_goals"].append("Légitimation par l'autorité")

        if FallacyFamily.STATISTICAL_PROBABILISTIC in dominant_families:
            insights["sophistication_level"] = "Avancé"
            insights["rhetorical_goals"].append("Persuasion par les données")

        # Analyser les indicateurs de faiblesse
        total_fallacies = sum(
            len(result.fallacies_detected) for result in family_results.values()
        )
        if total_fallacies > 5:
            insights["weakness_indicators"].append("Forte dépendance aux sophismes")

        # Analyser les tactiques de manipulation
        family_diversity = len(dominant_families)
        if family_diversity >= 3:
            insights["manipulation_tactics"].append("Diversification des sophismes")

        return insights

    def _generate_recommendations(
        self,
        family_results: Dict[FallacyFamily, FamilyAnalysisResult],
        fact_check_results: List[Dict[str, Any]],
    ) -> List[str]:
        """Génère des recommandations globales."""

        recommendations = []

        # Recommandations basées sur les familles détectées
        high_score_families = [
            family
            for family, result in family_results.items()
            if result.family_score > 0.5
        ]

        if high_score_families:
            recommendations.append(
                f"Attention aux sophismes détectés dans {len(high_score_families)} familles principales"
            )

        # Recommandations basées sur le fact-checking
        false_claims = sum(
            1
            for result in fact_check_results
            if result.get("status") == "verified_false"
        )

        if false_claims > 0:
            recommendations.append(
                f"Vérifier {false_claims} affirmation(s) identifiée(s) comme fausse(s)"
            )

        # Recommandations générales
        if len(family_results) >= 3:
            recommendations.append(
                "Analyse critique recommandée : multiples types de sophismes détectés"
            )

        return recommendations[:5]  # Limiter à 5 recommandations max


# Backward compatibility functions for service-layer access.
# These exist as module-level names to support unittest.mock.patch() in tests.
def get_taxonomy_manager():
    """Get the taxonomy manager singleton (compat shim)."""
    from argumentation_analysis.services.fallacy_taxonomy_service import (
        get_taxonomy_manager as _get_tm,
    )

    return _get_tm()


def get_verification_service():
    """Get the fact verification service singleton (compat shim)."""
    from argumentation_analysis.services.fact_verification_service import (
        get_verification_service as _get_vs,
    )

    return _get_vs()


# Instance globale de l'analyseur
_global_family_analyzer = None


def get_family_analyzer(
    taxonomy_plugin: Optional["TaxonomyExplorerPlugin"] = None,
    api_config: Optional[Dict[str, Any]] = None,
) -> FallacyFamilyAnalyzer:
    """
    Récupère ou crée une instance de l'analyseur par famille.

    :param taxonomy_plugin: Instance du plugin de taxonomie à injecter. Si None, utilise singleton.
    :param api_config: Configuration optionnelle des APIs
    :return: Instance de l'analyseur
    """
    global _global_family_analyzer
    if taxonomy_plugin is not None:
        # Explicit plugin injection — create directly (no singleton)
        return FallacyFamilyAnalyzer(
            taxonomy_plugin=taxonomy_plugin, api_config=api_config
        )
    # Singleton mode
    if _global_family_analyzer is None:
        _global_family_analyzer = FallacyFamilyAnalyzer(api_config=api_config)
    return _global_family_analyzer
