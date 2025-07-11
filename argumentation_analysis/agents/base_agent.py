from abc import ABC, abstractmethod
from typing import Dict, Any, List

# Note: L'import de KernelPlugin peut sembler introduire un couplage,
# mais il s'agit d'un type de données standardisé, pas d'une logique d'exécution.
# C'est un compromis acceptable pour un typage clair.
from semantic_kernel.functions.kernel_plugin import KernelPlugin


class BaseAgent(ABC):
    """
    Classe de base abstraite pour tous les agents métier.
    Garantit que les agents implémentent les méthodes nécessaires sans
    dépendre directement de la logique d'exécution de `semantic-kernel`.
    """

    def __init__(self, name: str, **kwargs: Any):
        self._name = name

    @property
    def name(self) -> str:
        """Retourne le nom de l'agent."""
        return self._name

    @abstractmethod
    async def invoke(self, *args: Any, **kwargs: Any) -> Any:
        """
        Méthode d'invocation principale pour l'agent.
        Doit être implémentée par toutes les sous-classes.
        """
        pass

    def get_plugins(self) -> List[KernelPlugin]:
        """
        Retourne une liste des plugins KernelPlugin requis par l'agent.
        Par défaut, ne retourne aucun plugin. Les sous-classes peuvent surcharger
        cette méthode pour déclarer leurs dépendances en plugins.
        """
        return []

    def get_agent_capabilities(self) -> Dict[str, Any]:
        """
        Retourne un dictionnaire décrivant les capacités de l'agent.
        Peut être surchargée par les sous-classes pour fournir des détails.
        """
        return {"description": f"Capacités de l'agent {self.name}"}
