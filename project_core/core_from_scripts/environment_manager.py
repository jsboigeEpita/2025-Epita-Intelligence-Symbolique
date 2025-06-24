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
import json
import logging
import subprocess
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Union

# Configuration de base du logger pour ce module
logging.basicConfig(level=logging.INFO, format='[ENV_MGR] [%(asctime)s] - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PrintLogger:
    """Fallback Logger pour la compatibilité de l'API et l'usage simple en script."""
    def debug(self, msg): logger.debug(msg)
    def info(self, msg): logger.info(msg)
    def warning(self, msg): logger.warning(msg)
    def error(self, msg): logger.error(msg)
    def success(self, msg): logger.info(f"✅ SUCCESS: {msg}")

class EnvironmentManager:
    """
    Gestionnaire d'environnement partiel.
    Fournit des fonctionnalités de base pour les scripts d'activation.
    """
    def __init__(self, logger_instance: PrintLogger = None):
        self.logger = logger_instance or PrintLogger()
        self.project_root = Path(__file__).resolve().parent.parent.parent
        self._conda_env_path_cache: Optional[Path] = None

    def _get_conda_env_path(self, env_name: str) -> Optional[Path]:
        """Trouve le chemin d'un environnement Conda via 'conda info'."""
        if self._conda_env_path_cache:
            return self._conda_env_path_cache
        try:
            result = subprocess.run(
                ["conda", "info", "--envs", "--json"],
                capture_output=True, text=True, check=True
            )
            data = json.loads(result.stdout)
            for env_path_str in data.get("envs", []):
                env_path = Path(env_path_str)
                if env_path.name == env_name:
                    self.logger.info(f"Chemin trouvé pour l'environnement '{env_name}': {env_path}")
                    self._conda_env_path_cache = env_path
                    return env_path
            self.logger.error(f"Environnement Conda '{env_name}' non trouvé.")
            return None
        except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError) as e:
            self.logger.error(f"Erreur lors de la recherche de l'environnement Conda: {e}")
            return None

    def get_python_executable(self, env_name: str = 'projet-is') -> Optional[str]:
        """Retourne le chemin absolu de l'exécutable Python pour un environnement Conda."""
        env_path = self._get_conda_env_path(env_name)
        if not env_path:
            return None
        
        python_executable = env_path / ('python.exe' if sys.platform == "win32" else 'bin/python')
        if not python_executable.is_file():
            self.logger.error(f"Exécutable Python non trouvé à: {python_executable}")
            return None
            
        return str(python_executable)

    def run_command(self, command: List[str]) -> int:
        """Exécute une commande en tant que sous-processus."""
        # ... (le reste de la méthode est inchangé) ...
        if not command:
            self.logger.error("Aucune commande à exécuter.")
            return 1

        command_str = ' '.join(command)
        self.logger.info(f"Exécution de la commande: {command_str}")
        
        env = os.environ.copy()
        env['CONDA_VERBOSITY'] = '3'
        env['PYTHONUNBUFFERED'] = '1'

        try:
            result = subprocess.run(command, check=False)
            self.logger.info(f"La commande s'est terminée avec le code de sortie: {result.returncode}")
            return result.returncode
        except FileNotFoundError:
            self.logger.error(f"Commande non trouvée: '{command[0]}'. Vérifiez que l'exécutable est dans le PATH.")
            return 1
        except Exception as e:
            self.logger.error(f"Une erreur est survenue lors de l'exécution de la commande: {e}")
            return 1
        
        return returncode


def main():
    """Point d'entrée CLI pour la gestion de l'environnement."""
    parser = argparse.ArgumentParser(description="Outil de gestion d'environnement.")
    parser.add_argument('--get-python-path', action='store_true', help="Affiche le chemin de l'exécutable Python de l'environnement.")
    parser.add_argument('--env-name', type=str, default='projet-is', help="Nom de l'environnement Conda à utiliser.")
    
    args = parser.parse_args()
    
    manager = EnvironmentManager()
    
    if args.get_python_path:
        python_path = manager.get_python_executable(args.env_name)
        if python_path:
            print(python_path)
            sys.exit(0)
        else:
            sys.exit(1)
    
    parser.print_help()

if __name__ == "__main__":
    # --- BOOTSTRAP MINIMAL ---
    # Cette section est critique pour que l'orchestrateur puisse
    # obtenir le chemin python de l'environnement sans l'activer entièrement
    if any(arg == '--get-python-path' for arg in sys.argv):
         main()
         sys.exit(0) # Quitter après avoir récupéré le chemin

    # --- PARTIE OBSOLETE (Conservée pour compatibilité) ---
    warnings.warn(
        "L'utilisation de environment_manager.py comme script principal est obsolète.",
        DeprecationWarning,
        stacklevel=2
    )

    # L'ancien code de 'main' est ici pour la compatibilité, mais ne devrait plus être appelé directement.
    if os.getenv("RUNNING_VIA_ENV_MANAGER") == "true":
        logger.info("Détecté --RUNNING_VIA_ENV_MANAGER--, validation de l'environnement court-circuitée.")
        sys.exit(0)
    
    try:
        from argumentation_analysis.core.bootstrap import bootstrap_project
        bootstrap_project(force_setup=False, verbose=True)
        logger.info("--- environment_manager.py chargé et logger configuré ---")
    except ImportError as e:
        logger.error(f"Erreur de bootstrap : {e}. Assurez-vous que PYTHONPATH est correct.")
        sys.exit(1)