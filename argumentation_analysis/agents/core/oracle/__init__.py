# argumentation_analysis/agents/core/oracle/__init__.py
"""
Module Oracle - Gestion des agents Oracle avec système ACL et datasets.

Ce module implémente le pattern Oracle pour l'extension du workflow Sherlock/Watson,
permettant la gestion de datasets avec contrôle d'accès granulaire et révélations progressives.

Classes principales:
- OracleBaseAgent: Agent de base avec système ACL
- MoriartyInterrogatorAgent: Agent Oracle spécialisé pour Cluedo
- DatasetAccessManager: Gestionnaire d'accès aux datasets
- PermissionManager: Gestionnaire des permissions ACL
"""

from .oracle_base_agent import OracleBaseAgent
from .moriarty_interrogator_agent import MoriartyInterrogatorAgent
from .dataset_access_manager import DatasetAccessManager, PermissionManager
from .cluedo_dataset import CluedoDataset
from .permissions import PermissionRule, QueryResult, ValidationResult, OracleResponse

__all__ = [
    "OracleBaseAgent",
    "MoriartyInterrogatorAgent", 
    "DatasetAccessManager",
    "PermissionManager",
    "CluedoDataset",
    "PermissionRule",
    "QueryResult",
    "ValidationResult",
    "OracleResponse"
]

__version__ = "1.0.0"
__author__ = "Équipe Projet Sherlock/Watson"