"""
Module pour la gestion des chemins et des variables d'environnement.

Ce module est OBSOLETE et conservé pour compatibilité ascendante.
La configuration est maintenant gérée de manière centralisée via pydantic-settings
dans `argumentation_analysis.config.settings`.

N'utilisez plus ce module pour de nouveaux développements.
"""

import os
import sys
import warnings
import logging
from pathlib import Path
from typing import Optional

# Configuration de base du logger pour ce module
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Tentative d'importation des nouveaux settings ---
try:
    from argumentation_analysis.config.settings import settings
except ImportError:
    # Si l'import échoue, cela signifie probablement que nous sommes dans un contexte
    # où le nouvel emplacement n'est pas disponible. On crée un objet "mock" pour éviter les crashs.
    class MockSettings:
        def __getattr__(self, name):
            warnings.warn(
                "Le module de configuration centralisé 'argumentation_analysis.config.settings' n'a pas pu être importé. "
                "PathManager fonctionne en mode dégradé et ne peut pas accéder à la configuration.",
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


class PathManager:
    """
    CLASSE OBSOLETE. Gère les chemins, les variables d'environnement et la configuration.
    La logique a été déplacée vers `argumentation_analysis.config.settings`.
    Cette classe est conservée pour compatibilité ascendante uniquement.
    """

    def __init__(self, project_root: Path, logger_instance: Optional[Logger] = None):
        warnings.warn(
            "La classe 'PathManager' est obsolète. La configuration est maintenant gérée par "
            "`argumentation_analysis.config.settings`. Veuillez migrer les appels.",
            DeprecationWarning,
            stacklevel=2
        )
        self.project_root = project_root
        self.logger = logger_instance if logger_instance is not None else PrintLogger()

    def get_project_root(self) -> Path:
        """Retourne le chemin racine du projet."""
        warnings.warn(
            "PathManager.get_project_root() est obsolète. Utilisez une méthode centralisée pour obtenir la racine du projet si nécessaire.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.project_root

    def setup_project_pythonpath(self):
        """
        Méthode obsolète. La configuration de PYTHONPATH devrait être gérée par
        l'environnement d'exécution (ex: scripts d'activation, configuration IDE).
        """
        warnings.warn(
            "PathManager.setup_project_pythonpath() est obsolète. La gestion du PYTHONPATH est maintenant implicite "
            "ou doit être configurée au niveau de l'environnement.",
            DeprecationWarning,
            stacklevel=2
        )
        project_path_str = str(self.project_root.resolve())
        # Assure la compatibilité minimale pour la session en cours


    def normalize_and_validate_java_home(self, auto_install_if_missing: bool = False) -> Optional[str]:
        """
        Méthode obsolète. La validation de JAVA_HOME est maintenant implicite via
        la configuration centralisée si nécessaire (ex: `settings.java.home`).
        """
        warnings.warn(
            "PathManager.normalize_and_validate_java_home() est obsolète. "
            "Utilisez directement `settings.java.home` ou une configuration similaire.",
            DeprecationWarning,
            stacklevel=2
        )
        # Tente de retourner la variable d'environnement si elle existe pour ne pas casser le code appelant
        java_home = os.environ.get('JAVA_HOME')
        if java_home and Path(java_home).exists():
            return java_home
        return None

    def load_environment_variables(self) -> None:
        """
        Méthode obsolète. Le chargement des variables est maintenant géré
        automatiquement par `pydantic-settings` lors de l'import de `settings`.
        """
        warnings.warn(
            "PathManager.load_environment_variables() est obsolète. "
            "Le chargement est automatique via `argumentation_analysis.config.settings`.",
            DeprecationWarning,
            stacklevel=2
        )
        # Ne fait plus rien, car pydantic-settings s'en charge.

    def initialize_environment_paths(self) -> None:
        """
        Méthode obsolète. L'initialisation est maintenant gérée par l'import
        du module `settings`.
        """
        warnings.warn(
            "PathManager.initialize_environment_paths() est obsolète. Cette initialisation est maintenant "
            "déclenchée par l'import de `argumentation_analysis.config.settings`.",
            DeprecationWarning,
            stacklevel=2
        )
        self.setup_project_pythonpath() # Conserve un comportement minimal

if __name__ == "__main__":
    logger.warning("Le script `path_manager.py` est exécuté directement.")
    logger.warning("Ce module est obsolète et ne doit plus être utilisé pour de nouveaux développements.")
    logger.warning("Veuillez migrer vers `argumentation_analysis.config.settings`.")