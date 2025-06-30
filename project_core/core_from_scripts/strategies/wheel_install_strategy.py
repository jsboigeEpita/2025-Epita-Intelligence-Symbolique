import sys
import platform
from typing import Dict, Any, Optional
from .base_strategy import BaseStrategy

class WheelInstallStrategy(BaseStrategy):
    """
    Stratégie de réparation qui tente d'installer un wheel précompilé.
    """

    @property
    def name(self) -> str:
        return "wheel-install"

    def execute(self, package: str, options: Optional[Dict[str, Any]] = None) -> bool:
        """
        Tente de deviner et d'installer un wheel précompilé.
        """
        self.logger.info(f"[{package}] Exécution de la stratégie de réparation '{self.name}'...")
        if not sys.platform == 'win32':
            self.logger.warning(f"[{package}] La stratégie '{self.name}' n'est applicable que sur Windows.")
            return False

        python_version = self._get_python_version_for_wheel()
        architecture = 'win_amd64' if platform.architecture()[0] == '64bit' else 'win32'
        
        # Heuristique pour JPype1, qui est le cas d'usage principal
        if package.lower() == 'jpype1':
            versions_to_try = ["1.5.0", "1.4.1", "1.4.0"]
            for version in versions_to_try:
                wheel_name = f"{package}-{version}-{python_version}-{python_version}-{architecture}.whl"
                wheel_url = f"https://files.pythonhosted.org/packages/source/J/JPype1/{wheel_name}"
                
                self.logger.info(f"Tentative de téléchargement et installation du wheel: {wheel_url}")
                command = f'pip install "{wheel_url}"'
                if self.manager_env.run_command_in_conda_env(command) == 0:
                    self.logger.info(f"[{package}] Succès de l'installation via le wheel précompilé '{wheel_name}'.")
                    return True
        
        self.logger.warning(f"[{package}] Impossible de deviner un wheel pour le paquet '{package}'.")
        return False

    def _get_python_version_for_wheel(self) -> str:
        """Retourne la version de Python formatée pour les noms de wheels (ex: cp312)."""
        return f"cp{sys.version_info.major}{sys.version_info.minor}"