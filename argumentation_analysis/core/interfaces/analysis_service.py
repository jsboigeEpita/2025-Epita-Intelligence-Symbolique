"""
Interface abstraite pour les services d'analyse — contrat NON ADOPTE.

Mesure 2026-09-14 : `AbstractAnalysisService` n'a **aucun implementeur et
aucun importeur** dans le depot. Le service reellement servi par l'API est
`api/dependencies.AnalysisService`, qui definit sa propre classe et n'importe
pas ce module. L'integration « via le CapabilityRegistry » annoncee ici n'a
jamais eu lieu ; `adapters/` ne l'implemente pas non plus.

Ce module est conserve comme point d'extension documente, PAS comme surface
cablee : le README de `core/interfaces/` le classe « residuel », et une surface
hors depot (`.claude/skills/integrate-component/SKILL.md`) le cite encore comme
interface d'adaptation. Qui l'implemente met cette note a jour.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class AbstractAnalysisService(ABC):
    """
    Interface abstraite pour les services d'analyse argumentative.

    ATTENTION : aucun service ne l'implemente aujourd'hui (voir la docstring
    du module). La docstring d'origine affirmait que tout service « doit »
    l'implementer pour etre composable — c'est faux mesure : rien ne l'importe.
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
