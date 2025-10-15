import logging
from typing import Dict, Any, Optional
from .base_strategy import BaseStrategy


class NoBinaryStrategy(BaseStrategy):
    """
    Stratégie de réparation forçant la compilation depuis les sources.
    Utilise `pip install --no-binary :all:`.
    """

    @property
    def name(self) -> str:
        return "no-binary"

    def execute(self, package: str, options: Optional[Dict[str, Any]] = None) -> bool:
        """
        Exécute la stratégie d'installation sans binaire.

        Args:
            package: Le nom du paquet à installer.
            options: Options non utilisées pour cette stratégie.

        Returns:
            True si l'installation réussit, False sinon.
        """
        self.logger.info(
            f"[{package}] Exécution de la stratégie de réparation '{self.name}'..."
        )
        command = f'pip install --no-binary :all: "{package}"'

        exit_code = self.manager_env.run_command_in_conda_env(command)

        if exit_code == 0:
            self.logger.info(
                f"[{package}] Stratégie '{self.name}' terminée avec succès."
            )
            return True
        else:
            self.logger.error(f"[{package}] Échec de la stratégie '{self.name}'.")
            return False
