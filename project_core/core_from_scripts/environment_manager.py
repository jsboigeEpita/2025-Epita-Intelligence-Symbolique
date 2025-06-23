"""
Gestionnaire d'environnements Python/conda

Ce module est OBSOLETE et conservé pour compatibilité ascendante.
La configuration est maintenant gérée de manière centralisée via pydantic-settings
dans `argumentation_analysis.config.settings`.
L'activation de l'environnement et l'exécution de commandes doivent être gérées
par des scripts de premier niveau (ex: `activate_project_env.ps1`).

N'utilisez plus ce module pour de nouveaux développements.
"""

import os
import sys
import warnings
import logging
import subprocess
from pathlib import Path
from enum import Enum, auto
from typing import Dict, List, Optional, Union

# Configuration de base du logger pour ce module
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

warnings.warn(
    "Le module 'environment_manager.py' est obsolète. "
    "Veuillez utiliser `argumentation_analysis.config.settings` pour la configuration "
    "et les scripts d'activation dédiés.",
    DeprecationWarning,
    stacklevel=2
)

# --- Tentative d'importation des nouveaux settings ---
try:
    from argumentation_analysis.config.settings import settings
except ImportError:
    class MockSettings:
        def __getattr__(self, name):
            warnings.warn(
                "Le module de configuration centralisé 'argumentation_analysis.config.settings' n'a pas pu être importé. "
                "EnvironmentManager fonctionne en mode dégradé.",
                ImportWarning
            )
            return None
    settings = MockSettings()

# --- Fallback Logger pour la compatibilité de l'API ---
class PrintLogger:
    def debug(self, msg): logger.debug(msg)
    def info(self, msg): logger.info(msg)
    def warning(self, msg): logger.warning(msg)
    def error(self, msg): logger.error(msg)
    def success(self, msg): logger.info(f"SUCCESS: {msg}")

Logger = PrintLogger

class ReinstallComponent(Enum):
    """Énumération OBSOLETE des composants pouvant être réinstallés."""
    def _generate_next_value_(name, start, count, last_values):
        return name.lower()
    ALL = auto()
    CONDA = auto()
    JAVA = auto()
    def __str__(self):
        return self.value

class EnvironmentManager:
    """
    CLASSE OBSOLETE. La logique a été déplacée vers `argumentation_analysis.config.settings`
    et des scripts d'activation.
    """
    def __init__(self, logger: Logger = None):
        warnings.warn("La classe 'EnvironmentManager' est obsolète.", DeprecationWarning, stacklevel=2)
        self.logger = logger or PrintLogger()
        try:
            from project_core.common.common_utils import get_project_root
            self.project_root = Path(get_project_root())
        except ImportError:
            self.project_root = Path(os.getcwd())
        self.default_conda_env = os.environ.get('CONDA_ENV_NAME', "projet-is")
        self.env_vars = {}

    def _warn_obsolete(self, method_name: str):
        warnings.warn(
            f"EnvironmentManager.{method_name}() est obsolète et ne doit plus être utilisé. "
            "Sa fonctionnalité a été supprimée ou remplacée.",
            DeprecationWarning,
            stacklevel=3
        )

    def check_conda_available(self) -> bool:
        self._warn_obsolete("check_conda_available")
        return False

    def check_python_version(self, python_cmd: str = "python") -> bool:
        self._warn_obsolete("check_python_version")
        return False

    def list_conda_environments(self) -> List[str]:
        self._warn_obsolete("list_conda_environments")
        return []

    def check_conda_env_exists(self, env_name: str) -> bool:
        self._warn_obsolete("check_conda_env_exists")
        return False

    def setup_environment_variables(self, additional_vars: Dict[str, str] = None):
        self._warn_obsolete("setup_environment_variables")
        pass

    def build_final_command(self, command: Union[str, List[str]], env_name: str = None) -> List[str]:
        self._warn_obsolete("build_final_command")
        if isinstance(command, str):
            import shlex
            return shlex.split(command)
        return command

    def run_in_conda_env(self, command: Union[str, List[str]], **kwargs) -> subprocess.CompletedProcess:
        self._warn_obsolete("run_in_conda_env")
        cmd_list = self.build_final_command(command)
        self.logger.warning(f"Exécution de la commande via un appel système direct car EnvironmentManager est obsolète: {' '.join(cmd_list)}")
        return subprocess.run(cmd_list, check=False)

    def check_python_dependencies(self, requirements: List[str], env_name: str = None) -> Dict[str, bool]:
        self._warn_obsolete("check_python_dependencies")
        return {req: False for req in requirements}

    def install_python_dependencies(self, requirements: List[str], env_name: str = None) -> bool:
        self._warn_obsolete("install_python_dependencies")
        return False

    def activate_project_environment(self, command_to_run: str = None, env_name: str = None) -> int:
        self._warn_obsolete("activate_project_environment")
        if command_to_run:
            self.run_in_conda_env(command_to_run)
            return 1 # Return non-zero to indicate potential issues
        return 0

# --- Fonctions autonomes obsolètes ---

def _warn_obsolete_func(func_name: str):
    warnings.warn(
        f"La fonction '{func_name}' est obsolète et ne doit plus être utilisée. "
        "Elle est conservée pour compatibilité uniquement.",
        DeprecationWarning,
        stacklevel=3
    )

def is_conda_env_active(env_name: str = None) -> bool:
    _warn_obsolete_func("is_conda_env_active")
    return False

def check_conda_env(env_name: str = None, logger: Logger = None) -> bool:
    _warn_obsolete_func("check_conda_env")
    return False

def auto_activate_env(env_name: str = None, silent: bool = True) -> bool:
    _warn_obsolete_func("auto_activate_env")
    return False

def activate_project_env(command: str = None, env_name: str = None, logger: Logger = None) -> int:
    _warn_obsolete_func("activate_project_env")
    if command:
        return 1 # Simulate failure
    return 0

def reinstall_conda_environment(manager, env_name: str, verbose_level: int = 0):
    _warn_obsolete_func("reinstall_conda_environment")
    pass

def recheck_java_environment(manager):
    _warn_obsolete_func("recheck_java_environment")
    pass

def main():
    """Point d'entrée principal OBSOLETE."""
    warnings.warn(
        "Le script 'environment_manager.py' est obsolète et ne doit plus être exécuté directement. "
        "Utilisez les scripts d'activation de projet (ex: activate_project_env.ps1). "
        "Cet appel direct est maintenant une opération sans effet (no-op) pour la compatibilité.",
        DeprecationWarning,
        stacklevel=2
    )
    # Ne plus quitter avec une erreur pour maintenir la compatibilité des anciens scripts.
    # On se contente d'afficher l'avertissement.
    pass

if __name__ == "__main__":
    main()