# argumentation_analysis/agents/core/oracle/permissions.py
"""
Définit le système de gestion des permissions pour les agents Oracle.

Ce module contient les briques logicielles pour un système de contrôle d'accès
granulaire (ACL - Access Control List). Il définit :
-   Les types de requêtes et politiques de révélation (`QueryType`, `RevealPolicy`).
-   Les règles de permissions par agent (`PermissionRule`).
-   Le gestionnaire central (`PermissionManager`) qui applique ces règles.
-   Les structures de données standard pour les réponses (`OracleResponse`) et l'audit.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from enum import Enum


class PermissionDeniedError(Exception):
    """Exception levée lorsqu'une permission est refusée."""

    pass


class InvalidQueryError(Exception):
    """Exception levée pour une requête invalide."""

    pass


class QueryType(Enum):
    """Énumère les types de requêtes possibles qu'un agent peut faire à un Oracle."""

    CARD_INQUIRY = "card_inquiry"
    """Demander des informations sur une carte spécifique."""
    SUGGESTION_VALIDATION = "suggestion_validation"
    """Valider une suggestion (hypothèse) de jeu."""
    CLUE_REQUEST = "clue_request"
    """Demander un indice."""
    LOGICAL_VALIDATION = "logical_validation"
    """Demander une validation logique à un assistant."""
    CONSTRAINT_CHECK = "constraint_check"
    """Vérifier une contrainte logique."""
    DATASET_ACCESS = "dataset_access"
    """Accéder directement au jeu de données (généralement restreint)."""
    REVELATION_REQUEST = "revelation_request"
    """Demander une révélation d'information stratégique."""
    GAME_STATE = "game_state"
    """Demander l'état actuel du jeu."""
    ADMIN_COMMAND = "admin_command"
    """Exécuter une commande administrative (très restreint)."""
    PERMISSION_CHECK = "permission_check"
    """Vérifier une permission."""
    PROGRESSIVE_HINT = "progressive_hint"
    """Demander un indice progressif (fonctionnalité avancée)."""
    RAPID_TEST = "rapid_test"
    """Lancer un test rapide (fonctionnalité avancée)."""


class RevealPolicy(Enum):
    """Définit les différentes stratégies de révélation d'information."""

    PROGRESSIVE = "progressive"
    """Révèle l'information de manière graduelle et stratégique."""
    COOPERATIVE = "cooperative"
    """Révèle le maximum d'informations utiles pour aider les autres agents."""
    COMPETITIVE = "competitive"
    """Révèle le minimum d'informations possible pour garder un avantage."""
    BALANCED = "balanced"
    """Un équilibre entre les politiques coopérative et compétitive."""


@dataclass
class PermissionRule:
    """
    Définit une règle de permission pour un agent spécifique.

    Cette structure de données associe un nom d'agent à une liste de types de
    requêtes autorisées et à un ensemble de conditions (quota, champs interdits,
    politique de révélation).

    Attributes:
        agent_name (str): Nom de l'agent auquel la règle s'applique.
        allowed_query_types (List[QueryType]): La liste des types de requêtes
            que l'agent est autorisé à effectuer.
        conditions (Dict[str, Any]): Un dictionnaire de conditions supplémentaires,
            comme le nombre maximum de requêtes ou les champs interdits.
    """

    agent_name: str
    allowed_query_types: List[QueryType]
    conditions: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Applique les valeurs par défaut pour les conditions après l'initialisation."""
        if "max_daily_queries" not in self.conditions:
            self.conditions["max_daily_queries"] = 50
        if "forbidden_fields" not in self.conditions:
            self.conditions["forbidden_fields"] = []
        if "reveal_policy" not in self.conditions:
            self.conditions["reveal_policy"] = RevealPolicy.BALANCED.value

    @property
    def max_daily_queries(self) -> int:
        """Nombre maximum de requêtes par jour."""
        return self.conditions.get("max_daily_queries", 50)

    @property
    def forbidden_fields(self) -> List[str]:
        """Champs interdits d'accès."""
        return self.conditions.get("forbidden_fields", [])

    @property
    def reveal_policy(self) -> str:
        """Politique de révélation."""
        return self.conditions.get("reveal_policy", RevealPolicy.BALANCED.value)


@dataclass
class QueryResult:
    """Résultat d'une requête sur un dataset."""

    success: bool
    data: Any = None
    message: str = ""
    query_type: Optional[QueryType] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        status = "SUCCESS" if self.success else "FAILED"
        return f"QueryResult[{status}]: {self.message}"


@dataclass
class ValidationResult:
    """Résultat de validation d'une suggestion Cluedo."""

    can_refute: bool
    revealed_cards: List[Dict[str, str]] = field(default_factory=list)
    suggestion_valid: bool = True
    authorized: bool = True
    reason: str = ""
    refuting_agent: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def __str__(self) -> str:
        refute_status = "CAN_REFUTE" if self.can_refute else "CANNOT_REFUTE"
        auth_status = "AUTHORIZED" if self.authorized else "DENIED"
        return f"ValidationResult[{refute_status}, {auth_status}]: {self.reason}"


@dataclass
class OracleResponse:
    """
    Structure de données standard pour les réponses émises par le système Oracle.

    Elle encapsule si une requête a été autorisée, les données résultantes,
    les informations révélées et divers messages et métadonnées.
    """

    authorized: bool
    """`True` si la requête a été autorisée et exécutée, `False` sinon."""
    data: Any = None
    """Les données utiles retournées par la requête si elle a réussi."""
    message: str = ""
    """Un message lisible décrivant le résultat."""
    query_type: Optional[QueryType] = None
    """Le type de la requête qui a généré cette réponse."""
    revealed_information: List[str] = field(default_factory=list)
    """Liste des informations spécifiques qui ont été révélées lors de cette transaction."""
    agent_name: str = ""
    """Le nom de l'agent qui a fait la requête."""
    timestamp: datetime = field(default_factory=datetime.now)
    """L'horodatage de la réponse."""
    metadata: Dict[str, Any] = field(default_factory=dict)
    """Métadonnées additionnelles."""
    revelation_triggered: bool = False
    """Indique si une révélation d'information a été déclenchée."""
    hint_content: Optional[str] = None
    """Contenu d'un indice progressif, le cas échéant."""
    error_code: Optional[str] = None
    """Code d'erreur standardisé en cas d'échec."""

    @property
    def success(self) -> bool:
        """Compatibilité avec les tests : retourne authorized."""
        return self.authorized

    def __str__(self) -> str:
        status = "AUTHORIZED" if self.authorized else "DENIED"
        return f"OracleResponse[{status}]: {self.message}"


@dataclass
class AccessLog:
    """Log d'accès pour auditabilité."""

    timestamp: datetime
    agent_name: str
    query_type: QueryType
    result: bool
    details: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class PermissionManager:
    """
    Gestionnaire centralisé des permissions et de l'audit pour le système Oracle.

    Cette classe est le cœur du système de contrôle d'accès. Elle :
    -   Stocke toutes les règles de permission (`PermissionRule`).
    -   Vérifie si une requête d'un agent est autorisée (`is_authorized`).
    -   Tient un journal d'audit de toutes les requêtes (`_access_log`).
    -   Gère les quotas (ex: nombre de requêtes par jour).
    """

    def __init__(self):
        """Initialise le gestionnaire de permissions."""
        self._permission_rules: Dict[str, PermissionRule] = {}
        self._access_log: List[AccessLog] = []
        self._daily_query_counts: Dict[str, int] = {}
        self._logger = logging.getLogger(self.__class__.__name__)

    def add_permission_rule(self, rule: PermissionRule) -> None:
        """
        Enregistre ou met à jour une règle de permission pour un agent.

        Args:
            rule (PermissionRule): L'objet règle à ajouter.
        """
        self._permission_rules[rule.agent_name] = rule
        self._logger.info(
            f"Règle de permission ajoutée pour l'agent: {rule.agent_name}"
        )

    def add_permission(self, agent_name: str, query_type: QueryType):
        """Ajoute dynamiquement une permission à une règle existante."""
        if agent_name not in self._permission_rules:
            # Si l'agent n'a pas de règle, on en crée une nouvelle.
            # C'est un comportement de convenance, mais peut nécessiter une logique plus fine
            # dans un cas réel (par ex. lever une erreur).
            self._permission_rules[agent_name] = PermissionRule(
                agent_name=agent_name, allowed_query_types=[query_type]
            )
            self._logger.info(
                f"Nouvelle règle de permission créée pour l'agent {agent_name} avec la permission {query_type.value}."
            )
        else:
            # Ajoute la permission si elle n'existe pas déjà pour éviter les doublons
            rule = self._permission_rules[agent_name]
            if query_type not in rule.allowed_query_types:
                rule.allowed_query_types.append(query_type)
                self._logger.info(
                    f"Permission {query_type.value} ajoutée à la règle existante pour l'agent {agent_name}."
                )

    def is_authorized(self, agent_name: str, query_type: QueryType) -> bool:
        """Vérifie si un agent est autorisé pour un type de requête."""
        if agent_name not in self._permission_rules:
            self._logger.warning(
                f"Aucune règle de permission trouvée pour l'agent: {agent_name}"
            )
            return False

        rule = self._permission_rules[agent_name]

        # Vérification du type de requête
        if query_type not in rule.allowed_query_types:
            self._logger.info(
                f"Type de requête {query_type} non autorisé pour {agent_name}"
            )
            return False

        # Vérification du quota quotidien
        daily_count = self._daily_query_counts.get(agent_name, 0)
        if daily_count >= rule.max_daily_queries:
            self._logger.warning(
                f"Quota quotidien dépassé pour {agent_name}: {daily_count}/{rule.max_daily_queries}"
            )
            return False

        return True

    def get_permission_rule(self, agent_name: str) -> Optional[PermissionRule]:
        """Récupère la règle de permission d'un agent."""
        return self._permission_rules.get(agent_name)

    def log_access(
        self, agent_name: str, query_type: QueryType, success: bool, details: str = ""
    ) -> None:
        """Enregistre un accès dans le log d'audit."""
        log_entry = AccessLog(
            timestamp=datetime.now(),
            agent_name=agent_name,
            query_type=query_type,
            result=success,
            details=details,
        )
        self._access_log.append(log_entry)

        # Mise à jour du compteur quotidien
        if success:
            self._daily_query_counts[agent_name] = (
                self._daily_query_counts.get(agent_name, 0) + 1
            )

        self._logger.debug(
            f"Accès enregistré: {agent_name} -> {query_type} -> {success}"
        )

    def get_access_log(self, agent_name: Optional[str] = None) -> List[AccessLog]:
        """Récupère l'historique d'accès, optionnellement filtré par agent."""
        if agent_name:
            return [log for log in self._access_log if log.agent_name == agent_name]
        return self._access_log.copy()

    def reset_daily_counts(self) -> None:
        """Remet à zéro les compteurs quotidiens."""
        self._daily_query_counts.clear()
        self._logger.info("Compteurs quotidiens remis à zéro")

    def get_query_stats(self, agent_name: str) -> Dict[str, Any]:
        """Récupère les statistiques d'usage d'un agent."""
        rule = self.get_permission_rule(agent_name)
        if not rule:
            return {}

        daily_count = self._daily_query_counts.get(agent_name, 0)
        agent_logs = self.get_access_log(agent_name)

        return {
            "agent_name": agent_name,
            "daily_queries_used": daily_count,
            "daily_queries_limit": rule.max_daily_queries,
            "total_queries": len(agent_logs),
            "success_rate": sum(1 for log in agent_logs if log.result) / len(agent_logs)
            if agent_logs
            else 0.0,
            "allowed_query_types": [qt.value for qt in rule.allowed_query_types],
            "reveal_policy": rule.reveal_policy,
        }


class CluedoIntegrityError(Exception):
    """Exception levée lors de violation des règles d'intégrité du Cluedo."""

    pass


def validate_cluedo_method_access(method_name: str, agent_name: str) -> None:
    """
    Valide l'accès aux méthodes selon les règles d'intégrité du Cluedo.

    Args:
        method_name: Nom de la méthode appelée
        agent_name: Nom de l'agent demandeur

    Raises:
        CluedoIntegrityError: Si la méthode viole les règles du Cluedo
    """
    # Méthodes interdites qui violent les règles du Cluedo
    FORBIDDEN_METHODS = {
        "get_autres_joueurs_cards": "Violation règle fondamentale : un joueur ne peut voir les cartes des autres",
        "get_solution": "Violation règle fondamentale : la solution ne peut être révélée qu'à la fin",
        "direct_card_access": "Accès direct aux cartes interdit sans révélation explicite",
    }

    if method_name in FORBIDDEN_METHODS:
        raise CluedoIntegrityError(
            f"INTÉGRITÉ CLUEDO VIOLÉE par {agent_name}: {FORBIDDEN_METHODS[method_name]}"
        )


# Configuration par défaut pour les permissions Cluedo RENFORCÉES
def get_default_cluedo_permissions() -> Dict[str, PermissionRule]:
    """Retourne les règles de permission par défaut pour Cluedo AVEC INTÉGRITÉ RENFORCÉE."""
    return {
        "SherlockEnqueteAgent": PermissionRule(
            agent_name="SherlockEnqueteAgent",
            allowed_query_types=[
                QueryType.CARD_INQUIRY,
                QueryType.SUGGESTION_VALIDATION,
                QueryType.CLUE_REQUEST,
            ],
            conditions={
                "max_daily_queries": 30,
                "forbidden_fields": [
                    "solution_secrete",
                    "autres_joueurs_cards",  # NOUVELLE PROTECTION
                    "direct_solution_access",  # NOUVELLE PROTECTION
                ],
                "forbidden_methods": [  # NOUVELLE PROTECTION
                    "get_autres_joueurs_cards",
                    "get_solution",
                ],
                "reveal_policy": RevealPolicy.PROGRESSIVE.value,
                "integrity_enforced": True,  # NOUVEAU FLAG D'INTÉGRITÉ
            },
        ),
        "WatsonLogicAssistant": PermissionRule(
            agent_name="WatsonLogicAssistant",
            allowed_query_types=[
                QueryType.LOGICAL_VALIDATION,
                QueryType.CONSTRAINT_CHECK,
                QueryType.SUGGESTION_VALIDATION,
            ],
            conditions={
                "max_daily_queries": 100,
                "logical_queries_only": True,
                "forbidden_fields": [
                    "solution_secrete",
                    "autres_joueurs_cards",  # NOUVELLE PROTECTION
                    "direct_solution_access",  # NOUVELLE PROTECTION
                ],
                "forbidden_methods": [  # NOUVELLE PROTECTION
                    "get_autres_joueurs_cards",
                    "get_solution",
                ],
                "reveal_policy": RevealPolicy.BALANCED.value,
                "integrity_enforced": True,  # NOUVEAU FLAG D'INTÉGRITÉ
            },
        ),
        "MoriartyInterrogator": PermissionRule(
            agent_name="MoriartyInterrogator",
            allowed_query_types=[
                QueryType.SUGGESTION_VALIDATION,
                QueryType.CARD_INQUIRY,
                QueryType.CLUE_REQUEST,
                QueryType.PROGRESSIVE_HINT,
            ],
            conditions={
                "max_daily_queries": 50,
                "can_reveal_own_cards": True,  # Moriarty peut révéler SES cartes
                "forbidden_fields": [
                    "autres_joueurs_cards",  # PROTECTION: Ne peut voir les cartes des autres
                    "direct_solution_access",  # PROTECTION: Pas d'accès direct à la solution
                ],
                "forbidden_methods": [  # PROTECTION RENFORCÉE
                    "get_autres_joueurs_cards",
                    "get_solution",
                ],
                "reveal_policy": RevealPolicy.BALANCED.value,
                "integrity_enforced": True,  # NOUVEAU FLAG D'INTÉGRITÉ
            },
        ),
    }
