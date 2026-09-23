"""
Définit les contrats (interfaces) et les modèles de données partagés
pour le système Oracle.

Ce module contient les Classes de Base Abstraites (ABC), les Dataclasses,
et les Enums qui garantissent une interaction cohérente et standardisée
entre les différents composants du système Oracle (Agents, Gestionnaires
de Données, etc.).

Verdict #2358 — ceci est un CONTRAT, pas une documentation de forme :
- les implémentations de production en héritent (`OracleBaseAgent` implémente
  `OracleAgentInterface`, `DatasetAccessManager` implémente
  `DatasetManagerInterface`) ;
- une garde de conformité compare chaque membre déclaré à l'implémentation
  réelle (signatures + async-ité) et ROUGIT à la première divergence
  (`tests/unit/argumentation_analysis/agents/core/oracle/test_interface_contract_2358.py`).

L'historique : ce contrat divergeait de la réalité sur trois membres et avait
« licencié » le défaut de #2340 — un appel sync vers un `check_permission`
async, exactement ce que la déclaration affirmait. Un contrat sans exécutant
endosse les bugs au lieu de les attraper ; c'est réparé.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from argumentation_analysis.agents.core.oracle.permissions import (
    OracleResponse,
    QueryResult,
    QueryType,
)


class OracleAgentInterface(ABC):
    """
    Définit le contrat qu'un agent doit respecter pour agir comme un Oracle.

    Tout agent implémentant cette interface peut recevoir, traiter et répondre
    à des requêtes standardisées provenant d'autres agents.
    """

    @abstractmethod
    async def process_oracle_request(
        self, requesting_agent: str, query_type: QueryType, query_params: Dict[str, Any]
    ) -> OracleResponse:
        """
        Traite une requête entrante adressée à l'Oracle.

        Args:
            requesting_agent (str): Le nom de l'agent qui soumet la requête.
            query_type (QueryType): Le type de requête (enum `permissions.QueryType`).
            query_params (Dict[str, Any]): Les paramètres spécifiques à la requête.

        Returns:
            OracleResponse: Un objet structuré contenant le résultat de l'opération.
        """
        pass

    @abstractmethod
    def get_oracle_statistics(self) -> Dict[str, Any]:
        """
        Retourne des statistiques sur l'état et l'utilisation de l'Oracle.

        Returns:
            Dict[str, Any]: Un dictionnaire de métriques (ex: nombre de requêtes,
            erreurs, etc.).
        """
        pass

    @abstractmethod
    def reset_oracle_state(self) -> None:
        """Réinitialise l'état interne de l'Oracle."""
        pass


class DatasetManagerInterface(ABC):
    """
    Définit le contrat pour un gestionnaire d'accès à un jeu de données.

    Ce composant est responsable de l'exécution des requêtes sur la source de
    données sous-jacente et de la vérification des permissions.
    """

    @abstractmethod
    async def execute_query(
        self, agent_name: str, query_type: QueryType, query_params: Dict[str, Any]
    ) -> QueryResult:
        """
        Exécute une requête sur le jeu de données après vérification des permissions.

        Args:
            agent_name (str): Le nom de l'agent effectuant la requête.
            query_type (QueryType): Le type de requête à exécuter (enum).
            query_params (Dict[str, Any]): Les paramètres de la requête.

        Returns:
            QueryResult: Le résultat de la requête.
        """
        pass

    @abstractmethod
    async def check_permission(self, agent_name: str, query_type: QueryType) -> bool:
        """
        Vérifie si un agent a la permission d'exécuter un certain type de requête.

        ⚠ Async (#2340/#2358) : un appel sync à cette méthode rend une coroutine
        truthy — le contrôle répond « autorisé » sur tout refus.

        Args:
            agent_name (str): Le nom de l'agent demandeur.
            query_type (QueryType): Le type de requête pour lequel la permission
                est demandée.

        Returns:
            bool: `True` si l'agent a la permission, `False` sinon.
        """
        pass


@dataclass
class StandardOracleResponse:
    """
    Structure de données standard pour toutes les réponses de l'Oracle.
    """

    success: bool
    """Indique si la requête a été traitée avec succès."""
    data: Optional[Dict[str, Any]] = None
    """Les données retournées en cas de succès."""
    message: str = ""
    """Un message lisible décrivant le résultat ou l'erreur."""
    error_code: Optional[str] = None
    """Un code d'erreur standardisé (voir `OracleResponseStatus`)."""
    metadata: Optional[Dict[str, Any]] = None
    """Métadonnées additionnelles (ex: coût de la requête, temps d'exécution)."""

    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet en un dictionnaire sérialisable."""
        return {
            "success": self.success,
            "data": self.data,
            "message": self.message,
            "error_code": self.error_code,
            "metadata": self.metadata,
        }


class OracleResponseStatus(Enum):
    """Codes de statut standardisés pour les réponses de l'Oracle."""

    SUCCESS = "success"
    """La requête a été traitée avec succès."""
    ERROR = "error"
    """Une erreur générique et non spécifiée est survenue."""
    PERMISSION_DENIED = "permission_denied"
    """L'agent demandeur n'a pas les permissions nécessaires."""
    INVALID_QUERY = "invalid_query"
    """La requête ou ses paramètres sont mal formés."""
    DATASET_ERROR = "dataset_error"
    """Une erreur est survenue lors de l'accès à la source de données."""
