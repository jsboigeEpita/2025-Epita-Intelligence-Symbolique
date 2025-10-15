from typing import List, Optional
from pydantic import BaseModel, Field


class ToulminComponent(BaseModel):
    """Représente un composant identifié du modèle de Toulmin."""

    text: str = Field(
        description="Le fragment de texte exact identifié comme composant."
    )
    confidence_score: float = Field(
        description="Score de confiance (entre 0 et 1) que le texte correspond bien au composant."
    )
    source_sentences: List[int] = Field(
        description="Liste des indices des phrases d'origine."
    )


class ToulminAnalysisResult(BaseModel):
    """Structure de données pour le résultat de l'analyse de Toulmin."""

    claim: Optional[ToulminComponent] = Field(
        None, description="La thèse principale de l'argument."
    )
    data: List[ToulminComponent] = Field(
        default_factory=list,
        description="Les données, faits ou preuves soutenant la thèse.",
    )
    warrant: Optional[ToulminComponent] = Field(
        None,
        description="Le lien logique ou la garantie qui connecte les données à la thèse.",
    )
    backing: Optional[ToulminComponent] = Field(
        None, description="Le fondement ou le support pour la garantie."
    )
    qualifier: Optional[ToulminComponent] = Field(
        None,
        description="Le modalisateur qui nuance la force de la thèse (ex: 'probablement', 'certainement').",
    )
    rebuttal: Optional[ToulminComponent] = Field(
        None, description="La réfutation ou les conditions d'exception à la thèse."
    )
