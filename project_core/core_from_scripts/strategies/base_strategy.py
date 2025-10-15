import abc
import logging
from typing import Dict, Any, Optional
from argumentation_analysis.core.utils.shell_utils import run_shell_command
from pathlib import Path


class BaseStrategy(abc.ABC):
    """
    Classe de base abstraite pour toutes les stratégies de réparation.
    """

    def __init__(self, manager_env, logger: Optional[logging.Logger] = None):
        """
        Initialise la stratégie.

        Args:
            manager_env: Une instance du EnvironmentManager pour accéder aux chemins et utilitaires.
            logger: L'instance du logger à utiliser.
        """
        self.manager_env = manager_env
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Retourne le nom de la stratégie."""
        pass

    @abc.abstractmethod
    def execute(self, package: str, options: Optional[Dict[str, Any]] = None) -> bool:
        """
        Exécute la logique de la stratégie pour un paquet donné.

        Args:
            package: Le nom du paquet à traiter.
            options: Un dictionnaire d'options supplémentaires.

        Returns:
            True si l'exécution a réussi, False sinon.
        """
        pass
