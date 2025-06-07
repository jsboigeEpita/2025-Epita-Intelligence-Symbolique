"""
Sherlock-Watson-Moriarty Oracle Enhanced System
Agent Oracle de base et système de gestion des données Cluedo
"""

# Version et métadonnées
__version__ = "2.1.0"
__author__ = "Sherlock-Watson-Moriarty Oracle Enhanced Team"

# Imports principaux
from .oracle_base_agent import OracleBaseAgent, OracleTools
from .moriarty_interrogator_agent import MoriartyInterrogatorAgent, MoriartyTools
from .cluedo_dataset import CluedoDataset, CluedoSuggestion, ValidationResult, RevelationRecord
from .dataset_access_manager import DatasetAccessManager, CluedoDatasetManager, QueryCache
from .permissions import (
    QueryType, RevealPolicy, PermissionRule, QueryResult, 
    OracleResponse, AccessLog, PermissionManager,
    validate_cluedo_method_access, get_default_cluedo_permissions
)

# Classes principales exportées
__all__ = [
    # Agents Oracle
    "OracleBaseAgent",
    "OracleTools", 
    "MoriartyInterrogatorAgent",
    "MoriartyTools",
    
    # Dataset et gestion
    "CluedoDataset",
    "CluedoSuggestion",
    "ValidationResult", 
    "RevelationRecord",
    "DatasetAccessManager",
    "CluedoDatasetManager",
    "QueryCache",
    
    # Permissions et types
    "QueryType",
    "RevealPolicy",
    "PermissionRule",
    "QueryResult",
    "OracleResponse", 
    "AccessLog",
    "PermissionManager",
    "validate_cluedo_method_access",
    "get_default_cluedo_permissions",
]

# Configuration par défaut
DEFAULT_ORACLE_CONFIG = {
    "max_revelations_per_agent": 3,
    "revelation_strategy": "strategic",
    "cache_size": 1000,
    "cache_ttl": 300,
    "enable_logging": True,
    "log_level": "INFO"
}

def get_oracle_version() -> str:
    """Retourne la version du système Oracle Enhanced"""
    return __version__

def get_oracle_info() -> Dict[str, Any]:
    """Retourne les informations du système Oracle"""
    return {
        "version": __version__,
        "author": __author__,
        "components": len(__all__),
        "config": DEFAULT_ORACLE_CONFIG
    }
