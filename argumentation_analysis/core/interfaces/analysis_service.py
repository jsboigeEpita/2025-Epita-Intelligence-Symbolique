"""
Interface abstraite pour les services d'analyse.

Definit le contrat que tout service d'analyse doit implementer,
qu'il s'agisse du service authentique (LLM), du mock, ou de
futures integrations via le CapabilityRegistry.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class AbstractAnalysisService(ABC):
    """
    Interface abstraite pour les services d'analyse argumentative.

    Tout service d'analyse (mock, LLM authentique, hybride) doit
    implementer cette interface pour etre composable dans les workflows.
    """

    @abstractmethod
    async def analyze_text(self, text: str) -> Dict[str, Any]:
        """
        Analyse un texte et retourne les resultats structures.

        Args:
            text: Le texte a analyser.

        Returns:
            Dict contenant au minimum:
                - fallacies: List[Dict] — sophismes detectes
                - duration: float — duree en secondes
                - summary: str — resume de l'analyse
                - components_used: List[str] — composants utilises
        """
        raise NotImplementedError

    @abstractmethod
    def is_available(self) -> bool:
        """Verifie si le service est operationnel."""
        raise NotImplementedError

    @abstractmethod
    def get_status_details(self) -> Dict[str, Any]:
        """Retourne les details du statut du service."""
        raise NotImplementedError

    def get_service_name(self) -> str:
        """Retourne le nom du service (defaut: nom de la classe)."""
        return self.__class__.__name__
