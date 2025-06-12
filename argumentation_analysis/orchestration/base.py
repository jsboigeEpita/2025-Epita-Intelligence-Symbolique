# argumentation_analysis/orchestration/base.py
"""
Ce module contient les concepts de base pour l'orchestration,
y compris l'agent de base de semantic-kernel et les stratégies
personnalisées pour éviter les dépendances circulaires.
"""
import logging
from typing import List, Any, Optional

# Importation de la classe Agent officielle de semantic-kernel.
# Cela suppose que la version de semantic-kernel utilisée inclut ce module.
try:
    from semantic_kernel.agents import Agent
except ImportError:
    # Fallback pour les versions plus anciennes ou si le module agents n'est pas où on pense
    class Agent:
        def __init__(self, name: str, kernel=None, **kwargs):
            self.name = name
            self.kernel = kernel
            self._logger = logging.getLogger(f"Agent.{self.name}")
            self._logger.warning(f"Fallback: Classe Agent mockée pour {self.name}.")

# Définitions des stratégies de base, déplacées depuis cluedo_extended_orchestrator
class SelectionStrategy:
    def __init__(self, **kwargs):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._logger.info("SelectionStrategy initialisée.")

    async def next(self, agents: List[Agent], history: List[Any]) -> Optional[Agent]:
        """Méthode de sélection du prochain agent."""
        self._logger.debug(f"Sélection du prochain agent depuis la liste: {[a.name for a in agents]}")
        if not agents:
            self._logger.warning("Aucun agent disponible pour la sélection.")
            return None
        # Comportement par défaut simple : le premier agent de la liste.
        return agents[0]

class TerminationStrategy:
    def __init__(self, **kwargs):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._logger.info("TerminationStrategy initialisée.")

    async def should_terminate(self, agent: Optional[Agent], history: List[Any]) -> bool:
        """Méthode de vérification des conditions de terminaison."""
        self._logger.debug(f"Vérification des conditions de terminaison pour {len(history)} messages. Agent actuel: {agent.name if agent else 'None'}")
        # Par défaut, ne jamais terminer pour permettre un contrôle externe.
        return False