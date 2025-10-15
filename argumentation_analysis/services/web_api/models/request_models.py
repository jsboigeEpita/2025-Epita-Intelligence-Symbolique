#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Modèles de données pour les requêtes de l'API.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field, validator, field_validator
from argumentation_analysis.agents.core.extract.extract_definitions import (
    ExtractDefinition as Extract,
)
from argumentation_analysis.models.extract_definition import SourceDefinition
from typing import List

ExtractDefinitions = List[SourceDefinition]


class AnalysisOptions(BaseModel):
    """Options pour l'analyse de texte."""

    detect_fallacies: bool = Field(default=True, description="Détecter les sophismes")
    analyze_structure: bool = Field(
        default=True, description="Analyser la structure argumentative"
    )
    evaluate_coherence: bool = Field(default=True, description="Évaluer la cohérence")
    include_context: bool = Field(
        default=True, description="Inclure le contexte dans l'analyse"
    )
    severity_threshold: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Seuil de sévérité"
    )


class AnalysisRequest(BaseModel):
    """Requête pour l'analyse complète d'un texte."""

    text: str = Field(..., min_length=1, description="Texte à analyser")
    options: Optional[AnalysisOptions] = Field(
        default_factory=AnalysisOptions, description="Options d'analyse"
    )

    @field_validator("text")
    def validate_text(cls, v: str) -> str:
        """Valide que le texte n'est pas vide après suppression des espaces."""
        if not v or not v.strip():
            raise ValueError("Le texte ne peut pas être vide")
        return v.strip()


class ValidationRequest(BaseModel):
    """Requête pour la validation d'un argument."""

    premises: List[str] = Field(..., min_length=1, description="Liste des prémisses")
    conclusion: str = Field(..., min_length=1, description="Conclusion de l'argument")
    argument_type: Optional[str] = Field(
        default="deductive",
        description="Type d'argument (deductive, inductive, abductive)",
    )

    @field_validator("premises")
    def validate_premises(cls, v: List[str]) -> List[str]:
        """Valide que la liste des prémisses n'est pas vide et que les prémisses elles-mêmes ne sont pas vides."""
        if not v:
            raise ValueError("Au moins une prémisse est requise")
        cleaned = [p.strip() for p in v if p and p.strip()]
        if not cleaned:
            raise ValueError("Les prémisses ne peuvent pas être vides")
        return cleaned

    @field_validator("conclusion")
    def validate_conclusion(cls, v: str) -> str:
        """Valide que la conclusion n'est pas vide après suppression des espaces."""
        if not v or not v.strip():
            raise ValueError("La conclusion ne peut pas être vide")
        return v.strip()

    @field_validator("argument_type")
    def validate_argument_type(cls, v: Optional[str]) -> Optional[str]:
        """Valide que le type d'argument est l'un des types autorisés."""
        if v and v not in ["deductive", "inductive", "abductive"]:
            raise ValueError(
                "Type d'argument invalide. Utilisez: deductive, inductive, ou abductive"
            )
        return v


class FallacyOptions(BaseModel):
    """Options pour la détection de sophismes."""

    severity_threshold: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Seuil de sévérité"
    )
    include_context: bool = Field(default=True, description="Inclure le contexte")
    max_fallacies: int = Field(
        default=10, ge=1, le=50, description="Nombre maximum de sophismes à retourner"
    )
    categories: Optional[List[str]] = Field(
        default=None, description="Catégories de sophismes à rechercher"
    )
    use_enhanced: bool = Field(
        default=True, description="Utiliser l'analyseur Enhanced Contextual"
    )
    use_contextual: bool = Field(
        default=True, description="Utiliser l'analyseur Contextual"
    )
    use_patterns: bool = Field(
        default=True, description="Utiliser la détection par patterns"
    )


class FallacyRequest(BaseModel):
    """Requête pour la détection de sophismes."""

    text: str = Field(..., min_length=1, description="Texte à analyser")
    options: Optional[FallacyOptions] = Field(
        default_factory=FallacyOptions, description="Options de détection"
    )

    @field_validator("text")
    def validate_text(cls, v: str) -> str:
        """Valide que le texte n'est pas vide après suppression des espaces."""
        if not v or not v.strip():
            raise ValueError("Le texte ne peut pas être vide")
        return v.strip()


class Argument(BaseModel):
    """Modèle pour un argument dans un framework."""

    id: str = Field(..., min_length=1, description="Identifiant unique de l'argument")
    content: str = Field(..., min_length=1, description="Contenu de l'argument")
    attacks: Optional[List[str]] = Field(
        default_factory=list, description="Liste des arguments attaqués"
    )
    supports: Optional[List[str]] = Field(
        default_factory=list, description="Liste des arguments supportés"
    )

    @field_validator("id")
    def validate_id(cls, v: str) -> str:
        """Valide que l'ID de l'argument n'est pas vide."""
        if not v or not v.strip():
            raise ValueError("L'identifiant ne peut pas être vide")
        return v.strip()

    @field_validator("content")
    def validate_content(cls, v: str) -> str:
        """Valide que le contenu de l'argument n'est pas vide."""
        if not v or not v.strip():
            raise ValueError("Le contenu ne peut pas être vide")
        return v.strip()


class FrameworkOptions(BaseModel):
    """Options pour la construction de framework."""

    compute_extensions: bool = Field(
        default=True, description="Calculer les extensions"
    )
    semantics: str = Field(default="preferred", description="Sémantique à utiliser")
    include_visualization: bool = Field(
        default=True, description="Inclure la visualisation"
    )
    max_arguments: int = Field(
        default=100, ge=1, le=1000, description="Nombre maximum d'arguments"
    )

    @field_validator("semantics")
    def validate_semantics(cls, v: str) -> str:
        """Valide que la sémantique fournie est l'une des sémantiques autorisées."""
        valid_semantics = ["grounded", "complete", "preferred", "stable", "semi-stable"]
        if v not in valid_semantics:
            raise ValueError(
                f"Sémantique invalide. Utilisez: {', '.join(valid_semantics)}"
            )
        return v


class FrameworkRequest(BaseModel):
    """Requête pour la construction d'un framework de Dung."""

    arguments: List[Argument] = Field(
        ..., min_length=1, description="Liste des arguments"
    )
    options: Optional[FrameworkOptions] = Field(
        default_factory=FrameworkOptions, description="Options du framework"
    )

    @field_validator("arguments")
    def validate_arguments(cls, v: List[Argument]) -> List[Argument]:
        """Valide la liste des arguments, y compris l'unicité des IDs et la validité des références d'attaque/support."""
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


# Modèles pour les opérations logiques


class LogicOptions(BaseModel):
    """Options pour les opérations logiques."""

    include_explanation: bool = Field(
        default=True, description="Inclure une explication détaillée"
    )
    max_queries: int = Field(
        default=5, ge=1, le=20, description="Nombre maximum de requêtes à générer"
    )
    timeout: float = Field(
        default=10.0, ge=0.1, le=60.0, description="Timeout en secondes"
    )


class LogicBeliefSetRequest(BaseModel):
    """Requête pour la conversion d'un texte en ensemble de croyances logiques."""

    text: str = Field(..., min_length=1, description="Texte à convertir")
    logic_type: str = Field(
        ..., description="Type de logique (propositional, first_order, modal)"
    )
    options: Optional[dict] = Field(
        default_factory=dict, description="Options de conversion flexibles"
    )

    @field_validator("text")
    def validate_text(cls, v: str) -> str:
        """Valide que le texte n'est pas vide après suppression des espaces."""
        if not v or not v.strip():
            raise ValueError("Le texte ne peut pas être vide")
        return v.strip()

    @field_validator("logic_type")
    def validate_logic_type(cls, v: str) -> str:
        """Valide que le type de logique est l'un des types autorisés."""
        valid_types = ["propositional", "first_order", "modal"]
        if v not in valid_types:
            raise ValueError(
                f"Type de logique invalide. Utilisez: {', '.join(valid_types)}"
            )
        return v


class LogicQueryRequest(BaseModel):
    """Requête pour l'exécution d'une requête logique sur un ensemble de croyances."""

    belief_set_id: str = Field(
        ..., min_length=1, description="ID de l'ensemble de croyances"
    )
    query: str = Field(..., min_length=1, description="Requête logique à exécuter")
    logic_type: str = Field(
        ..., description="Type de logique (propositional, first_order, modal)"
    )
    options: Optional[LogicOptions] = Field(
        default_factory=LogicOptions, description="Options d'exécution"
    )

    @field_validator("belief_set_id")
    def validate_belief_set_id(cls, v: str) -> str:
        """Valide que l'ID de l'ensemble de croyances n'est pas vide."""
        if not v or not v.strip():
            raise ValueError("L'ID de l'ensemble de croyances ne peut pas être vide")
        return v.strip()

    @field_validator("query")
    def validate_query(cls, v: str) -> str:
        """Valide que la requête logique n'est pas vide."""
        if not v or not v.strip():
            raise ValueError("La requête ne peut pas être vide")
        return v.strip()

    @field_validator("logic_type")
    def validate_logic_type(cls, v: str) -> str:
        """Valide que le type de logique est l'un des types autorisés."""
        valid_types = ["propositional", "first_order", "modal"]
        if v not in valid_types:
            raise ValueError(
                f"Type de logique invalide. Utilisez: {', '.join(valid_types)}"
            )
        return v


class LogicGenerateQueriesRequest(BaseModel):
    """Requête pour la génération de requêtes logiques pertinentes."""

    belief_set_id: str = Field(
        ..., min_length=1, description="ID de l'ensemble de croyances"
    )
    text: str = Field(
        ..., min_length=1, description="Texte source pour la génération de requêtes"
    )
    logic_type: str = Field(
        ..., description="Type de logique (propositional, first_order, modal)"
    )
    options: Optional[LogicOptions] = Field(
        default_factory=LogicOptions, description="Options de génération"
    )

    @field_validator("belief_set_id")
    def validate_belief_set_id(cls, v: str) -> str:
        """Valide que l'ID de l'ensemble de croyances n'est pas vide."""
        if not v or not v.strip():
            raise ValueError("L'ID de l'ensemble de croyances ne peut pas être vide")
        return v.strip()

    @field_validator("text")
    def validate_text(cls, v: str) -> str:
        """Valide que le texte source n'est pas vide."""
        if not v or not v.strip():
            raise ValueError("Le texte ne peut pas être vide")
        return v.strip()

    @field_validator("logic_type")
    def validate_logic_type(cls, v: str) -> str:
        """Valide que le type de logique est l'un des types autorisés."""
        valid_types = ["propositional", "first_order", "modal"]
        if v not in valid_types:
            raise ValueError(
                f"Type de logique invalide. Utilisez: {', '.join(valid_types)}"
            )
        return v


class FrameworkAnalysisRequest(BaseModel):
    """Requête pour l'analyse d'un framework de Dung."""

    arguments: List[str] = Field(
        ..., min_length=1, description="Liste des IDs d'arguments"
    )
    attacks: List[List[str]] = Field(
        default_factory=list, description="Liste des attaques [source_id, target_id]"
    )
