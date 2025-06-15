"""
Modèles de données pour l'Agent de Synthèse Unifié.

Ce module définit les structures de données utilisées par le SynthesisAgent
pour représenter les résultats d'analyses logiques, informelles et le rapport unifié.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import json


@dataclass
class LogicAnalysisResult:
    """
    Résultat d'une analyse logique (formelle) d'un texte.
    
    Contient les résultats des trois types de logique :
    - Logique propositionnelle
    - Logique de premier ordre  
    - Logique modale
    """
    
    # Résultats par type de logique
    propositional_result: Optional[str] = None
    first_order_result: Optional[str] = None
    modal_result: Optional[str] = None
    
    # Métriques logiques
    logical_validity: Optional[bool] = None
    consistency_check: Optional[bool] = None
    satisfiability: Optional[bool] = None
    
    # Détails techniques
    formulas_extracted: List[str] = field(default_factory=list)
    queries_executed: List[str] = field(default_factory=list)
    
    # Métadonnées
    analysis_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    processing_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit le résultat en dictionnaire."""
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
    Résultat d'une analyse informelle (rhétorique) d'un texte.
    
    Contient les résultats des analyses de sophismes, arguments
    et structures rhétoriques.
    """
    
    # Analyses rhétoriques
    fallacies_detected: List[Dict[str, Any]] = field(default_factory=list)
    arguments_structure: Optional[str] = None
    rhetorical_devices: List[str] = field(default_factory=list)
    
    # Métriques informelles
    argument_strength: Optional[float] = None
    persuasion_level: Optional[str] = None
    credibility_score: Optional[float] = None
    
    # Détails d'analyse
    text_segments_analyzed: List[str] = field(default_factory=list)
    context_factors: Dict[str, Any] = field(default_factory=dict)
    
    # Métadonnées
    analysis_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    processing_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit le résultat en dictionnaire."""
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
    Rapport unifié combinant analyses formelles et informelles.
    
    Ce rapport présente une synthèse cohérente des résultats
    des deux types d'analyses avec une évaluation globale.
    """
    
    # Texte analysé
    original_text: str
    
    # Résultats des analyses
    logic_analysis: LogicAnalysisResult
    informal_analysis: InformalAnalysisResult
    
    # Synthèse unifiée
    executive_summary: str = ""
    coherence_assessment: Optional[str] = None
    contradictions_identified: List[str] = field(default_factory=list)
    
    # Évaluation globale
    overall_validity: Optional[bool] = None
    confidence_level: Optional[float] = None
    recommendations: List[str] = field(default_factory=list)
    
    # Métriques combinées
    logic_informal_alignment: Optional[float] = None
    analysis_completeness: Optional[float] = None
    
    # Métadonnées du rapport
    synthesis_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    total_processing_time_ms: float = 0.0
    synthesis_version: str = "1.0.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit le rapport en dictionnaire."""
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
        """Convertit le rapport en JSON formaté."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    def get_summary_statistics(self) -> Dict[str, Any]:
        """Retourne un résumé statistique du rapport."""
        return {
            'text_length': len(self.original_text),
            'formulas_count': len(self.logic_analysis.formulas_extracted),
            'fallacies_count': len(self.informal_analysis.fallacies_detected),
            'contradictions_count': len(self.contradictions_identified),
            'recommendations_count': len(self.recommendations),
            'overall_validity': self.overall_validity,
            'confidence_level': self.confidence_level
        }