#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Modèles de données pour les réponses logiques de l'API.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class LogicQueryResult(BaseModel):
    """Résultat d'une requête logique."""
    query: str = Field(..., description="Requête exécutée")
    result: Optional[bool] = Field(..., description="Résultat de la requête (True, False ou None)")
    formatted_result: str = Field(..., description="Résultat formaté")
    explanation: Optional[str] = Field(default=None, description="Explication du résultat")


class LogicBeliefSet(BaseModel):
    """Ensemble de croyances logiques."""
    id: str = Field(..., description="Identifiant unique de l'ensemble de croyances")
    logic_type: str = Field(..., description="Type de logique (propositional, first_order, modal)")
    content: str = Field(..., description="Contenu de l'ensemble de croyances")
    source_text: str = Field(..., description="Texte source")
    creation_timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp de création")


class LogicBeliefSetResponse(BaseModel):
    """Réponse pour la conversion d'un texte en ensemble de croyances logiques."""
    success: bool = Field(..., description="Succès de la conversion")
    conversion_timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp de la conversion")
    
    # Ensemble de croyances
    belief_set: LogicBeliefSet = Field(..., description="Ensemble de croyances créé")
    
    # Métadonnées
    processing_time: float = Field(default=0.0, ge=0.0, description="Temps de traitement")
    conversion_options: Dict[str, Any] = Field(default_factory=dict, description="Options utilisées")


class LogicQueryResponse(BaseModel):
    """Réponse pour l'exécution d'une requête logique."""
    success: bool = Field(..., description="Succès de l'exécution")
    query_timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp de l'exécution")
    
    # Résultat de la requête
    belief_set_id: str = Field(..., description="ID de l'ensemble de croyances")
    logic_type: str = Field(..., description="Type de logique")
    result: LogicQueryResult = Field(..., description="Résultat de la requête")
    
    # Métadonnées
    processing_time: float = Field(default=0.0, ge=0.0, description="Temps de traitement")
    query_options: Dict[str, Any] = Field(default_factory=dict, description="Options utilisées")


class LogicGenerateQueriesResponse(BaseModel):
    """Réponse pour la génération de requêtes logiques."""
    success: bool = Field(..., description="Succès de la génération")
    generation_timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp de la génération")
    
    # Requêtes générées
    belief_set_id: str = Field(..., description="ID de l'ensemble de croyances")
    logic_type: str = Field(..., description="Type de logique")
    queries: List[str] = Field(default_factory=list, description="Requêtes générées")
    
    # Métadonnées
    processing_time: float = Field(default=0.0, ge=0.0, description="Temps de traitement")
    generation_options: Dict[str, Any] = Field(default_factory=dict, description="Options utilisées")


class LogicInterpretationResponse(BaseModel):
    """Réponse pour l'interprétation des résultats de requêtes logiques."""
    success: bool = Field(..., description="Succès de l'interprétation")
    interpretation_timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp de l'interprétation")
    
    # Interprétation
    belief_set_id: str = Field(..., description="ID de l'ensemble de croyances")
    logic_type: str = Field(..., description="Type de logique")
    queries: List[str] = Field(default_factory=list, description="Requêtes exécutées")
    results: List[LogicQueryResult] = Field(default_factory=list, description="Résultats des requêtes")
    interpretation: str = Field(..., description="Interprétation textuelle des résultats")
    
    # Métadonnées
    processing_time: float = Field(default=0.0, ge=0.0, description="Temps de traitement")
    interpretation_options: Dict[str, Any] = Field(default_factory=dict, description="Options utilisées")