"""
Interfaces standardisées pour le système Oracle Enhanced
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

class OracleAgentInterface(ABC):
    """Interface standard pour tous les agents Oracle"""
    
    @abstractmethod
    async def process_oracle_request(self, requesting_agent: str, query_type: str, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """Traite une requête Oracle"""
        pass
        
    @abstractmethod
    def get_oracle_statistics(self) -> Dict[str, Any]:
        """Retourne les statistiques Oracle"""
        pass
        
    @abstractmethod
    def reset_oracle_state(self) -> None:
        """Remet à zéro l'état Oracle"""
        pass

class DatasetManagerInterface(ABC):
    """Interface standard pour les gestionnaires de dataset"""
    
    @abstractmethod
    def execute_query(self, agent_name: str, query_type: str, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """Exécute une requête sur le dataset"""
        pass
        
    @abstractmethod
    def check_permission(self, agent_name: str, query_type: str) -> bool:
        """Vérifie les permissions"""
        pass

@dataclass
class StandardOracleResponse:
    """Réponse Oracle standardisée"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: str = ""
    error_code: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire"""
        return {
            "success": self.success,
            "data": self.data,
            "message": self.message,
            "error_code": self.error_code,
            "metadata": self.metadata
        }

class OracleResponseStatus(Enum):
    """Statuts de réponse Oracle"""
    SUCCESS = "success"
    ERROR = "error"
    PERMISSION_DENIED = "permission_denied"
    INVALID_QUERY = "invalid_query"
    DATASET_ERROR = "dataset_error"
