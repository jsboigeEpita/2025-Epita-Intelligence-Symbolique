#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Modèles de données pour les requêtes logiques de l'API.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field


class LogicOptions(BaseModel):
    """Options pour les opérations logiques."""

    reasoner: str = Field(
        default="default", description="Moteur de raisonnement à utiliser"
    )
    max_steps: Optional[int] = Field(
        default=None, description="Nombre maximum d'étapes de raisonnement"
    )


class LogicBeliefSetRequest(BaseModel):
    """Requête pour créer ou mettre à jour un ensemble de croyances."""

    text: str = Field(
        ..., description="Le texte source à convertir en ensemble de croyances."
    )
    logic_type: str = Field(
        default="propositional",
        description="Le type de logique à utiliser (ex: propositional, first_order).",
    )
    options: Optional[LogicOptions] = Field(
        default_factory=LogicOptions, description="Options de conversion."
    )


class LogicQueryRequest(BaseModel):
    """Requête pour interroger un ensemble de croyances."""

    belief_set_id: str = Field(
        ..., description="L'ID de l'ensemble de croyances à interroger."
    )
    query: str = Field(..., description="La requête logique à exécuter.")
    logic_type: str = Field(
        default="propositional", description="Le type de logique à utiliser."
    )


class LogicGenerateQueriesRequest(BaseModel):
    """Requête pour générer des requêtes pertinentes à partir d'un ensemble de croyances."""

    belief_set_id: str = Field(..., description="L'ID de l'ensemble de croyances.")
    logic_type: str = Field(
        default="propositional", description="Le type de logique à utiliser."
    )
    limit: int = Field(
        default=5, ge=1, le=20, description="Le nombre de requêtes à générer."
    )
