"""
Définitions des structures de données utilisées par l'agent étudiant.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class AgentInput:
    """
    Structure de données pour les entrées de l'agent.
    
    Attributes:
        text: Le texte à analyser
        context: Contexte supplémentaire pour l'analyse
        parameters: Paramètres optionnels pour configurer l'analyse
    """
    text: str
    context: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


@dataclass
class AgentOutput:
    """
    Structure de données pour les sorties de l'agent.
    
    Attributes:
        result: Le résultat principal de l'analyse
        confidence: Niveau de confiance dans le résultat (0.0 à 1.0)
        metadata: Métadonnées supplémentaires sur le traitement
        details: Détails optionnels sur le résultat
    """
    result: Any
    confidence: float
    metadata: Dict[str, Any]
    details: Optional[Dict[str, Any]] = None


# Vous pouvez définir d'autres structures de données spécifiques à votre agent ici

@dataclass
class AnalysisStep:
    """
    Représente une étape dans le processus d'analyse.
    
    Attributes:
        name: Nom de l'étape
        input: Données d'entrée pour cette étape
        output: Résultat de cette étape
        duration: Durée de l'étape en secondes
    """
    name: str
    input: Any
    output: Any
    duration: float


@dataclass
class AnalysisReport:
    """
    Rapport complet d'une analyse.
    
    Attributes:
        input: Données d'entrée initiales
        output: Résultat final
        steps: Liste des étapes intermédiaires
        total_duration: Durée totale de l'analyse
    """
    input: AgentInput
    output: AgentOutput
    steps: List[AnalysisStep]
    total_duration: float