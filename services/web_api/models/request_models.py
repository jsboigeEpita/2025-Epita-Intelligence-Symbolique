#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Modèles de données pour les requêtes de l'API.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field, validator


class AnalysisOptions(BaseModel):
    """Options pour l'analyse de texte."""
    detect_fallacies: bool = Field(default=True, description="Détecter les sophismes")
    analyze_structure: bool = Field(default=True, description="Analyser la structure argumentative")
    evaluate_coherence: bool = Field(default=True, description="Évaluer la cohérence")
    include_context: bool = Field(default=True, description="Inclure le contexte dans l'analyse")
    severity_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="Seuil de sévérité")


class AnalysisRequest(BaseModel):
    """Requête pour l'analyse complète d'un texte."""
    text: str = Field(..., min_length=1, description="Texte à analyser")
    options: Optional[AnalysisOptions] = Field(default_factory=AnalysisOptions, description="Options d'analyse")
    
    @validator('text')
    def validate_text(cls, v):
        if not v or not v.strip():
            raise ValueError("Le texte ne peut pas être vide")
        return v.strip()


class ValidationRequest(BaseModel):
    """Requête pour la validation d'un argument."""
    premises: List[str] = Field(..., min_items=1, description="Liste des prémisses")
    conclusion: str = Field(..., min_length=1, description="Conclusion de l'argument")
    argument_type: Optional[str] = Field(default="deductive", description="Type d'argument (deductive, inductive, abductive)")
    
    @validator('premises')
    def validate_premises(cls, v):
        if not v:
            raise ValueError("Au moins une prémisse est requise")
        cleaned = [p.strip() for p in v if p and p.strip()]
        if not cleaned:
            raise ValueError("Les prémisses ne peuvent pas être vides")
        return cleaned
    
    @validator('conclusion')
    def validate_conclusion(cls, v):
        if not v or not v.strip():
            raise ValueError("La conclusion ne peut pas être vide")
        return v.strip()
    
    @validator('argument_type')
    def validate_argument_type(cls, v):
        if v and v not in ['deductive', 'inductive', 'abductive']:
            raise ValueError("Type d'argument invalide. Utilisez: deductive, inductive, ou abductive")
        return v


class FallacyOptions(BaseModel):
    """Options pour la détection de sophismes."""
    severity_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="Seuil de sévérité")
    include_context: bool = Field(default=True, description="Inclure le contexte")
    max_fallacies: int = Field(default=10, ge=1, le=50, description="Nombre maximum de sophismes à retourner")
    categories: Optional[List[str]] = Field(default=None, description="Catégories de sophismes à rechercher")


class FallacyRequest(BaseModel):
    """Requête pour la détection de sophismes."""
    text: str = Field(..., min_length=1, description="Texte à analyser")
    options: Optional[FallacyOptions] = Field(default_factory=FallacyOptions, description="Options de détection")
    
    @validator('text')
    def validate_text(cls, v):
        if not v or not v.strip():
            raise ValueError("Le texte ne peut pas être vide")
        return v.strip()


class Argument(BaseModel):
    """Modèle pour un argument dans un framework."""
    id: str = Field(..., min_length=1, description="Identifiant unique de l'argument")
    content: str = Field(..., min_length=1, description="Contenu de l'argument")
    attacks: Optional[List[str]] = Field(default_factory=list, description="Liste des arguments attaqués")
    supports: Optional[List[str]] = Field(default_factory=list, description="Liste des arguments supportés")
    
    @validator('id')
    def validate_id(cls, v):
        if not v or not v.strip():
            raise ValueError("L'identifiant ne peut pas être vide")
        return v.strip()
    
    @validator('content')
    def validate_content(cls, v):
        if not v or not v.strip():
            raise ValueError("Le contenu ne peut pas être vide")
        return v.strip()


class FrameworkOptions(BaseModel):
    """Options pour la construction de framework."""
    compute_extensions: bool = Field(default=True, description="Calculer les extensions")
    semantics: str = Field(default="preferred", description="Sémantique à utiliser")
    include_visualization: bool = Field(default=True, description="Inclure la visualisation")
    max_arguments: int = Field(default=100, ge=1, le=1000, description="Nombre maximum d'arguments")
    
    @validator('semantics')
    def validate_semantics(cls, v):
        valid_semantics = ['grounded', 'complete', 'preferred', 'stable', 'semi-stable']
        if v not in valid_semantics:
            raise ValueError(f"Sémantique invalide. Utilisez: {', '.join(valid_semantics)}")
        return v


class FrameworkRequest(BaseModel):
    """Requête pour la construction d'un framework de Dung."""
    arguments: List[Argument] = Field(..., min_items=1, description="Liste des arguments")
    options: Optional[FrameworkOptions] = Field(default_factory=FrameworkOptions, description="Options du framework")
    
    @validator('arguments')
    def validate_arguments(cls, v):
        if not v:
            raise ValueError("Au moins un argument est requis")
        
        # Vérifier l'unicité des IDs
        ids = [arg.id for arg in v]
        if len(ids) != len(set(ids)):
            raise ValueError("Les identifiants d'arguments doivent être uniques")
        
        # Vérifier que les références d'attaque/support existent
        for arg in v:
            for attack_id in arg.attacks or []:
                if attack_id not in ids:
                    raise ValueError(f"Argument attaqué '{attack_id}' non trouvé")
            for support_id in arg.supports or []:
                if support_id not in ids:
                    raise ValueError(f"Argument supporté '{support_id}' non trouvé")
        
        return v