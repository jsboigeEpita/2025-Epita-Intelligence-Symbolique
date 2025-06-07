# argumentation_analysis/agents/core/oracle/permissions.py
"""
Système de permissions et structures de données pour les agents Oracle.

Ce module définit les structures de données et classes nécessaires pour le système
de permissions ACL et les réponses des agents Oracle.
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
    """Types de requêtes supportées par le système Oracle."""
    CARD_INQUIRY = "card_inquiry"
    SUGGESTION_VALIDATION = "suggestion_validation"
    CLUE_REQUEST = "clue_request"
    LOGICAL_VALIDATION = "logical_validation"
    CONSTRAINT_CHECK = "constraint_check"
    DATASET_ACCESS = "dataset_access"
    REVELATION_REQUEST = "revelation_request"
    GAME_STATE = "game_state"
    ADMIN_COMMAND = "admin_command"
    PERMISSION_CHECK = "permission_check"
    PROGRESSIVE_HINT = "progressive_hint"  # Enhanced Oracle functionality
    RAPID_TEST = "rapid_test"  # Enhanced Oracle rapid testing


class RevealPolicy(Enum):
    """Politiques de révélation pour les agents Oracle."""
    PROGRESSIVE = "progressive"  # Révélation progressive selon stratégie
    COOPERATIVE = "cooperative"  # Mode coopératif maximum
    COMPETITIVE = "competitive"  # Mode compétitif minimal
    BALANCED = "balanced"       # Équilibre entre coopération et compétition


@dataclass
class PermissionRule:
    """
    Règle de permission pour l'accès aux données Oracle.
    
    Définit les permissions qu'un agent possède pour accéder aux données
    et les conditions associées à ces accès.
    """
    agent_name: str
    allowed_query_types: List[QueryType]
    conditions: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialise les valeurs par défaut des conditions."""
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
    """Réponse standard d'un agent Oracle."""
    authorized: bool
    data: Any = None
    message: str = ""
    query_type: Optional[QueryType] = None
    revealed_information: List[str] = field(default_factory=list)
    agent_name: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    revelation_triggered: bool = False  # Enhanced Oracle functionality
    hint_content: Optional[str] = None  # Progressive hints for Enhanced Oracle
    error_code: Optional[str] = None  # Error code for failed responses
    
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
    Gestionnaire centralisé des permissions pour les agents Oracle.
    
    Gère l'autorisation des requêtes selon les règles ACL définies
    et maintient un historique d'accès pour l'auditabilité.
    """
    
    def __init__(self):
        self._permission_rules: Dict[str, PermissionRule] = {}
        self._access_log: List[AccessLog] = []
        self._daily_query_counts: Dict[str, int] = {}
        self._logger = logging.getLogger(self.__class__.__name__)
    
    def add_permission_rule(self, rule: PermissionRule) -> None:
        """Ajoute une règle de permission."""
        self._permission_rules[rule.agent_name] = rule
        self._logger.info(f"Règle de permission ajoutée pour l'agent: {rule.agent_name}")
    
    def is_authorized(self, agent_name: str, query_type: QueryType) -> bool:
        """Vérifie si un agent est autorisé pour un type de requête."""
        if agent_name not in self._permission_rules:
            self._logger.warning(f"Aucune règle de permission trouvée pour l'agent: {agent_name}")
            return False
        
        rule = self._permission_rules[agent_name]
        
        # Vérification du type de requête
        if query_type not in rule.allowed_query_types:
            self._logger.info(f"Type de requête {query_type} non autorisé pour {agent_name}")
            return False
        
        # Vérification du quota quotidien
        daily_count = self._daily_query_counts.get(agent_name, 0)
        if daily_count >= rule.max_daily_queries:
            self._logger.warning(f"Quota quotidien dépassé pour {agent_name}: {daily_count}/{rule.max_daily_queries}")
            return False
        
        return True
    
    def get_permission_rule(self, agent_name: str) -> Optional[PermissionRule]:
        """Récupère la règle de permission d'un agent."""
        return self._permission_rules.get(agent_name)
    
    def log_access(self, agent_name: str, query_type: QueryType, success: bool, details: str = "") -> None:
        """Enregistre un accès dans le log d'audit."""
        log_entry = AccessLog(
            timestamp=datetime.now(),
            agent_name=agent_name,
            query_type=query_type,
            result=success,
            details=details
        )
        self._access_log.append(log_entry)
        
        # Mise à jour du compteur quotidien
        if success:
            self._daily_query_counts[agent_name] = self._daily_query_counts.get(agent_name, 0) + 1
        
        self._logger.debug(f"Accès enregistré: {agent_name} -> {query_type} -> {success}")
    
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
            "success_rate": sum(1 for log in agent_logs if log.result) / len(agent_logs) if agent_logs else 0.0,
            "allowed_query_types": [qt.value for qt in rule.allowed_query_types],
            "reveal_policy": rule.reveal_policy
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
        "direct_card_access": "Accès direct aux cartes interdit sans révélation explicite"
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
                QueryType.CLUE_REQUEST
            ],
            conditions={
                "max_daily_queries": 30,
                "forbidden_fields": [
                    "solution_secrete",
                    "autres_joueurs_cards",  # NOUVELLE PROTECTION
                    "direct_solution_access"  # NOUVELLE PROTECTION
                ],
                "forbidden_methods": [  # NOUVELLE PROTECTION
                    "get_autres_joueurs_cards",
                    "get_solution"
                ],
                "reveal_policy": RevealPolicy.PROGRESSIVE.value,
                "integrity_enforced": True  # NOUVEAU FLAG D'INTÉGRITÉ
            }
        ),
        "WatsonLogicAssistant": PermissionRule(
            agent_name="WatsonLogicAssistant",
            allowed_query_types=[
                QueryType.LOGICAL_VALIDATION,
                QueryType.CONSTRAINT_CHECK
            ],
            conditions={
                "max_daily_queries": 100,
                "logical_queries_only": True,
                "forbidden_fields": [
                    "solution_secrete",
                    "autres_joueurs_cards",  # NOUVELLE PROTECTION
                    "direct_solution_access"  # NOUVELLE PROTECTION
                ],
                "forbidden_methods": [  # NOUVELLE PROTECTION
                    "get_autres_joueurs_cards",
                    "get_solution"
                ],
                "reveal_policy": RevealPolicy.BALANCED.value,
                "integrity_enforced": True  # NOUVEAU FLAG D'INTÉGRITÉ
            }
        ),
        "MoriartyInterrogator": PermissionRule(
            agent_name="MoriartyInterrogator",
            allowed_query_types=[
                QueryType.SUGGESTION_VALIDATION,
                QueryType.CARD_INQUIRY,
                QueryType.CLUE_REQUEST,
                QueryType.PROGRESSIVE_HINT
            ],
            conditions={
                "max_daily_queries": 50,
                "can_reveal_own_cards": True,  # Moriarty peut révéler SES cartes
                "forbidden_fields": [
                    "autres_joueurs_cards",  # PROTECTION: Ne peut voir les cartes des autres
                    "direct_solution_access"  # PROTECTION: Pas d'accès direct à la solution
                ],
                "forbidden_methods": [  # PROTECTION RENFORCÉE
                    "get_autres_joueurs_cards",
                    "get_solution"
                ],
                "reveal_policy": RevealPolicy.BALANCED.value,
                "integrity_enforced": True  # NOUVEAU FLAG D'INTÉGRITÉ
            }
        )
    }