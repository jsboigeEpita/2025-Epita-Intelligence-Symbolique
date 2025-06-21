"""
Modèles de données pour la synthèse des analyses d'arguments.

Ce module définit un ensemble de `dataclasses` Pydantic qui structurent les
résultats produits par les différents agents d'analyse. Ces modèles permettent
de créer un `UnifiedReport` qui combine les analyses logiques et informelles
d'un texte donné, fournissant une vue d'ensemble cohérente.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import json


@dataclass
class LogicAnalysisResult:
    """
    Structure de données pour les résultats de l'analyse logique formelle.

    Cette dataclass recueille les informations issues des agents spécialisés
    en logique propositionnelle, en logique du premier ordre, etc.
    """

    # --- Résultats par type de logique ---
    propositional_result: Optional[str] = None
    """Conclusion ou résultat de l'analyse en logique propositionnelle."""
    first_order_result: Optional[str] = None
    """Conclusion ou résultat de l'analyse en logique du premier ordre."""
    modal_result: Optional[str] = None
    """Conclusion ou résultat de l'analyse en logique modale."""

    # --- Métriques logiques ---
    logical_validity: Optional[bool] = None
    """Indique si l'argument est jugé logiquement valide."""
    consistency_check: Optional[bool] = None
    """Indique si l'ensemble des formules est cohérent."""
    satisfiability: Optional[bool] = None
    """Indique si les formules sont satisfiables."""

    # --- Détails techniques ---
    formulas_extracted: List[str] = field(default_factory=list)
    """Liste des formules logiques extraites du texte."""
    queries_executed: List[str] = field(default_factory=list)
    """Liste des requêtes exécutées contre la base de connaissances logique."""

    # --- Métadonnées ---
    analysis_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    """Horodatage de la fin de l'analyse."""
    processing_time_ms: float = 0.0
    """Temps de traitement total pour l'analyse logique en millisecondes."""

    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet en un dictionnaire sérialisable."""
        return {
            'propositional_result': self.propositional_result,
            'first_order_result': self.first_order_result,
            'modal_result': self.modal_result,
            'logical_validity': self.logical_validity,
            'consistency_check': self.consistency_check,
            'satisfiability': self.satisfiability,
            'formulas_extracted': self.formulas_extracted,
            'queries_executed': self.queries_executed,
            'analysis_timestamp': self.analysis_timestamp,
            'processing_time_ms': self.processing_time_ms
        }


@dataclass
class InformalAnalysisResult:
    """
    Structure de données pour les résultats de l'analyse rhétorique et informelle.

    Cette dataclass agrège les informations relatives à la détection de sophismes,
    à la structure argumentative et à d'autres aspects rhétoriques.
    """

    # --- Analyses rhétoriques ---
    fallacies_detected: List[Dict[str, Any]] = field(default_factory=list)
    """Liste des sophismes détectés, chaque sophisme étant un dictionnaire."""
    arguments_structure: Optional[str] = None
    """Description textuelle de la structure des arguments (ex: Toulmin model)."""
    rhetorical_devices: List[str] = field(default_factory=list)
    """Liste des procédés rhétoriques identifiés (ex: hyperbole, métaphore)."""

    # --- Métriques informelles ---
    argument_strength: Optional[float] = None
    """Score numérique évaluant la force perçue de l'argumentation (0.0 à 1.0)."""
    persuasion_level: Optional[str] = None
    """Évaluation qualitative du niveau de persuasion (ex: 'Faible', 'Moyen', 'Élevé')."""
    credibility_score: Optional[float] = None
    """Score numérique évaluant la crédibilité de la source ou de l'argument."""

    # --- Détails d'analyse ---
    text_segments_analyzed: List[str] = field(default_factory=list)
    """Liste des segments de texte spécifiques qui ont été soumis à l'analyse."""
    context_factors: Dict[str, Any] = field(default_factory=dict)
    """Facteurs contextuels pris en compte (ex: audience, objectif de l'auteur)."""

    # --- Métadonnées ---
    analysis_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    """Horodatage de la fin de l'analyse."""
    processing_time_ms: float = 0.0
    """Temps de traitement total pour l'analyse informelle en millisecondes."""

    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet en un dictionnaire sérialisable."""
        return {
            'fallacies_detected': self.fallacies_detected,
            'arguments_structure': self.arguments_structure,
            'rhetorical_devices': self.rhetorical_devices,
            'argument_strength': self.argument_strength,
            'persuasion_level': self.persuasion_level,
            'credibility_score': self.credibility_score,
            'text_segments_analyzed': self.text_segments_analyzed,
            'context_factors': self.context_factors,
            'analysis_timestamp': self.analysis_timestamp,
            'processing_time_ms': self.processing_time_ms
        }


@dataclass
class UnifiedReport:
    """
    Rapport de synthèse final combinant analyses formelles et informelles.

    C'est le produit final de la chaîne d'analyse. Il intègre les résultats
    logiques et rhétoriques et fournit une évaluation globale et une synthèse.
    """

    # --- Données de base ---
    original_text: str
    """Le texte source original qui a été analysé."""
    logic_analysis: LogicAnalysisResult
    """Objet contenant tous les résultats de l'analyse logique."""
    informal_analysis: InformalAnalysisResult
    """Objet contenant tous les résultats de l'analyse informelle."""

    # --- Synthèse Unifiée ---
    executive_summary: str = ""
    """Résumé exécutif lisible qui synthétise les points clés des deux analyses."""
    coherence_assessment: Optional[str] = None
    """Évaluation de la cohérence entre les arguments logiques et rhétoriques."""
    contradictions_identified: List[str] = field(default_factory=list)
    """Liste des contradictions détectées entre les différentes parties de l'analyse."""

    # --- Évaluation Globale ---
    overall_validity: Optional[bool] = None
    """Conclusion globale sur la validité de l'argumentation, tenant compte de tout."""
    confidence_level: Optional[float] = None
    """Niveau de confiance de l'agent dans sa propre analyse (0.0 à 1.0)."""
    recommendations: List[str] = field(default_factory=list)
    """Suggestions pour améliorer ou réfuter l'argumentation."""

    # --- Métriques Combinées ---
    logic_informal_alignment: Optional[float] = None
    """Score mesurant l'alignement entre la validité logique et la force persuasive."""
    analysis_completeness: Optional[float] = None
    """Score évaluant la complétude de l'analyse (ex: toutes les branches ont-elles été explorées?)."""

    # --- Métadonnées du rapport ---
    synthesis_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    """Horodatage de la création du rapport."""
    total_processing_time_ms: float = 0.0
    """Temps de traitement total pour l'ensemble de la chaîne d'analyse."""
    synthesis_version: str = "1.0.0"
    """Version du schéma du rapport."""

    def to_dict(self) -> Dict[str, Any]:
        """Convertit le rapport complet en un dictionnaire sérialisable."""
        return {
            'original_text': self.original_text,
            'logic_analysis': self.logic_analysis.to_dict(),
            'informal_analysis': self.informal_analysis.to_dict(),
            'executive_summary': self.executive_summary,
            'coherence_assessment': self.coherence_assessment,
            'contradictions_identified': self.contradictions_identified,
            'overall_validity': self.overall_validity,
            'confidence_level': self.confidence_level,
            'recommendations': self.recommendations,
            'logic_informal_alignment': self.logic_informal_alignment,
            'analysis_completeness': self.analysis_completeness,
            'synthesis_timestamp': self.synthesis_timestamp,
            'total_processing_time_ms': self.total_processing_time_ms,
            'synthesis_version': self.synthesis_version
        }
    
    def to_json(self, indent: int = 2) -> str:
        """
        Convertit le rapport complet en une chaîne de caractères JSON.

        Args:
            indent (int): Le nombre d'espaces à utiliser pour l'indentation JSON.

        Returns:
            str: Une représentation JSON formatée du rapport.
        """
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def get_summary_statistics(self) -> Dict[str, Any]:
        """
        Calcule et retourne des statistiques clés issues du rapport.

        Returns:
            Dict[str, Any]: Un dictionnaire contenant des métriques de haut niveau
            sur l'analyse (nombre de sophismes, validité, etc.).
        """
        return {
            'text_length': len(self.original_text),
            'formulas_count': len(self.logic_analysis.formulas_extracted),
            'fallacies_count': len(self.informal_analysis.fallacies_detected),
            'contradictions_count': len(self.contradictions_identified),
            'recommendations_count': len(self.recommendations),
            'overall_validity': self.overall_validity,
            'confidence_level': self.confidence_level
        }