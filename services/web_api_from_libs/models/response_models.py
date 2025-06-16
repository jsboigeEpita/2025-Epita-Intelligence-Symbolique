#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Modèles de données pour les réponses de l'API.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class FallacyDetection(BaseModel):
    """Modèle pour une détection de sophisme."""
    type: str = Field(..., description="Type de sophisme")
    name: str = Field(..., description="Nom du sophisme")
    description: str = Field(..., description="Description du sophisme")
    severity: float = Field(..., ge=0.0, le=1.0, description="Sévérité (0-1)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confiance de la détection (0-1)")
    location: Optional[Dict[str, int]] = Field(default=None, description="Position dans le texte")
    context: Optional[str] = Field(default=None, description="Contexte du sophisme")
    explanation: Optional[str] = Field(default=None, description="Explication détaillée")


class ArgumentStructure(BaseModel):
    """Modèle pour la structure d'un argument."""
    premises: List[str] = Field(default_factory=list, description="Prémisses identifiées")
    conclusion: str = Field(default="", description="Conclusion identifiée")
    argument_type: str = Field(default="unknown", description="Type d'argument")
    strength: float = Field(default=0.0, ge=0.0, le=1.0, description="Force de l'argument")
    coherence: float = Field(default=0.0, ge=0.0, le=1.0, description="Cohérence de l'argument")


class AnalysisResponse(BaseModel):
    """Réponse pour l'analyse complète d'un texte."""
    success: bool = Field(..., description="Succès de l'analyse")
    text_analyzed: str = Field(..., description="Texte analysé")
    analysis_timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp de l'analyse")
    
    # Résultats de l'analyse
    fallacies: List[FallacyDetection] = Field(default_factory=list, description="Sophismes détectés")
    argument_structure: Optional[ArgumentStructure] = Field(default=None, description="Structure argumentative")
    
    # Métriques globales
    overall_quality: float = Field(default=0.0, ge=0.0, le=1.0, description="Qualité globale")
    coherence_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Score de cohérence")
    fallacy_count: int = Field(default=0, ge=0, description="Nombre de sophismes")
    
    # Métadonnées
    processing_time: float = Field(default=0.0, ge=0.0, description="Temps de traitement (secondes)")
    analysis_options: Dict[str, Any] = Field(default_factory=dict, description="Options utilisées")


class ValidationResult(BaseModel):
    """Résultat de validation d'un argument."""
    is_valid: bool = Field(..., description="L'argument est-il valide")
    validity_score: float = Field(..., ge=0.0, le=1.0, description="Score de validité")
    soundness_score: float = Field(..., ge=0.0, le=1.0, description="Score de solidité")
    
    # Détails de la validation
    premise_analysis: List[Dict[str, Any]] = Field(default_factory=list, description="Analyse des prémisses")
    conclusion_analysis: Dict[str, Any] = Field(default_factory=dict, description="Analyse de la conclusion")
    logical_structure: Dict[str, Any] = Field(default_factory=dict, description="Structure logique")
    
    # Problèmes identifiés
    issues: List[str] = Field(default_factory=list, description="Problèmes identifiés")
    suggestions: List[str] = Field(default_factory=list, description="Suggestions d'amélioration")


class ValidationResponse(BaseModel):
    """Réponse pour la validation d'un argument."""
    success: bool = Field(..., description="Succès de la validation")
    validation_timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp de la validation")
    
    # Données de l'argument
    premises: List[str] = Field(..., description="Prémisses validées")
    conclusion: str = Field(..., description="Conclusion validée")
    argument_type: str = Field(..., description="Type d'argument")
    
    # Résultat de la validation
    result: ValidationResult = Field(..., description="Résultat de la validation")
    
    # Métadonnées
    processing_time: float = Field(default=0.0, ge=0.0, description="Temps de traitement")


class FallacyResponse(BaseModel):
    """Réponse pour la détection de sophismes."""
    success: bool = Field(..., description="Succès de la détection")
    text_analyzed: str = Field(..., description="Texte analysé")
    detection_timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp de la détection")
    
    # Sophismes détectés
    fallacies: List[FallacyDetection] = Field(default_factory=list, description="Sophismes détectés")
    fallacy_count: int = Field(default=0, ge=0, description="Nombre de sophismes")
    
    # Statistiques
    severity_distribution: Dict[str, int] = Field(default_factory=dict, description="Distribution par sévérité")
    category_distribution: Dict[str, int] = Field(default_factory=dict, description="Distribution par catégorie")
    
    # Métadonnées
    processing_time: float = Field(default=0.0, ge=0.0, description="Temps de traitement")
    detection_options: Dict[str, Any] = Field(default_factory=dict, description="Options utilisées")


class ArgumentNode(BaseModel):
    """Nœud d'argument dans un framework."""
    id: str = Field(..., description="Identifiant de l'argument")
    content: str = Field(..., description="Contenu de l'argument")
    status: str = Field(default="undecided", description="Statut dans les extensions")
    attacks: List[str] = Field(default_factory=list, description="Arguments attaqués")
    attacked_by: List[str] = Field(default_factory=list, description="Attaqué par")
    supports: List[str] = Field(default_factory=list, description="Arguments supportés")
    supported_by: List[str] = Field(default_factory=list, description="Supporté par")


class Extension(BaseModel):
    """Extension d'un framework."""
    type: str = Field(..., description="Type d'extension")
    arguments: List[str] = Field(default_factory=list, description="Arguments dans l'extension")
    is_complete: bool = Field(default=False, description="Extension complète")
    is_preferred: bool = Field(default=False, description="Extension préférée")


class FrameworkVisualization(BaseModel):
    """Données de visualisation du framework."""
    nodes: List[Dict[str, Any]] = Field(default_factory=list, description="Nœuds pour la visualisation")
    edges: List[Dict[str, Any]] = Field(default_factory=list, description="Arêtes pour la visualisation")
    layout: Dict[str, Any] = Field(default_factory=dict, description="Configuration du layout")


class FrameworkResponse(BaseModel):
    """Réponse pour la construction d'un framework."""
    success: bool = Field(..., description="Succès de la construction")
    framework_timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp de la construction")
    
    # Structure du framework
    arguments: List[ArgumentNode] = Field(default_factory=list, description="Arguments du framework")
    attack_relations: List[Dict[str, str]] = Field(default_factory=list, description="Relations d'attaque")
    support_relations: List[Dict[str, str]] = Field(default_factory=list, description="Relations de support")
    
    # Extensions calculées
    extensions: List[Extension] = Field(default_factory=list, description="Extensions calculées")
    semantics_used: str = Field(..., description="Sémantique utilisée")
    
    # Statistiques
    argument_count: int = Field(default=0, ge=0, description="Nombre d'arguments")
    attack_count: int = Field(default=0, ge=0, description="Nombre d'attaques")
    support_count: int = Field(default=0, ge=0, description="Nombre de supports")
    extension_count: int = Field(default=0, ge=0, description="Nombre d'extensions")
    
    # Visualisation
    visualization: Optional[FrameworkVisualization] = Field(default=None, description="Données de visualisation")
    
    # Métadonnées
    processing_time: float = Field(default=0.0, ge=0.0, description="Temps de traitement")
    framework_options: Dict[str, Any] = Field(default_factory=dict, description="Options utilisées")


class ErrorResponse(BaseModel):
    """Réponse d'erreur standardisée."""
    error: str = Field(..., description="Type d'erreur")
    message: str = Field(..., description="Message d'erreur")
    status_code: int = Field(..., description="Code de statut HTTP")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp de l'erreur")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Détails supplémentaires")