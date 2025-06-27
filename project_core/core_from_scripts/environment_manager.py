"""
Gestionnaire d'environnements Python/conda

Ce module fournit une logique de base pour la gestion de l'environnement Conda
et l'exécution de commandes. Il est utilisé par les scripts de premier niveau
pour assurer une abstraction indépendante de l'OS.

Bien que la configuration applicative se déplace vers `argumentation_analysis.config.settings`,
ce module reste essentiel pour le bootstrapping de l'environnement.
"""

import os
import sys
import warnings
from project_core.core_from_scripts import load_dotenv
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
    def error(self, msg, *args, **kwargs): logger.error(msg, *args, **kwargs)
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

    def run_command(self, command: List[str], env_name: str) -> int:
        """
        Exécute TOUJOURS une commande dans un sous-processus à l'intérieur de l'environnement conda spécifié.
        Ceci est la méthode la plus robuste pour éviter les conflits de path.
        """
        if not command:
            self.logger.error("Aucune commande à exécuter.")
            return 1

        # Construire la commande finale avec 'conda run'
        # C'est la manière la plus fiable de s'assurer que la commande s'exécute dans le bon environnement activé.
        final_command = ["conda", "run", "-n", env_name, "--no-capture-output"] + command
        
        command_str_for_log = ' '.join(final_command)
        self.logger.info(f"Exécution de la commande via 'conda run': {command_str_for_log}")
        
        try:
            result = subprocess.run(final_command, check=False, capture_output=True, text=True, encoding='utf-8')
            if result.stdout: self.logger.info(f"--- STDOUT ---\n{result.stdout}")
            if result.stderr: self.logger.error(f"--- STDERR ---\n{result.stderr}")
            self.logger.info(f"La commande s'est terminée avec le code de sortie: {result.returncode}")
            return result.returncode
        except Exception as e:
            self.logger.error(f"Erreur lors de l'exécution de la commande: {e}")
            return 1


def main():
    """Point d'entrée CLI pour la gestion de l'environnement."""
    parser = argparse.ArgumentParser(
        description="Outil de gestion d'environnement (avec compatibilité ascendante).",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--get-python-path', 
        action='store_true', 
        help="Affiche le chemin de l'exécutable Python de l'environnement."
    )
    parser.add_argument(
        '--env-name', 
        type=str, 
        default='projet-is-v2',
        help="Nom de l'environnement Conda à utiliser."
    )
    parser.add_argument(
        '--setup-vars', 
        action='store_true', 
        help="[OBSOLETE] Inclus pour compatibilité."
    )
    parser.add_argument(
        '--run-command',
        nargs=argparse.REMAINDER,
        help="Exécute la commande fournie et quitte. Doit être le dernier argument."
    )

    args = parser.parse_args()
    load_dotenv.ensure_dotenv_loaded(silent=False)
    manager = EnvironmentManager()

    if args.get_python_path:
        python_path = manager.get_python_executable(args.env_name)
        if python_path:
            print(python_path)
        else:
            sys.exit(1)
            
    elif args.run_command:
        # La logique de --setup-vars est maintenant obsolète et gérée par conda run.
        if args.setup_vars:
            logger.info("Argument --setup-vars ignoré.")

        # Exécuter la commande en utilisant la nouvelle méthode robuste.
        # Le nom de l'environnement est passé directement.
        return_code = manager.run_command(args.run_command, args.env_name)
        sys.exit(return_code)
    
    else:
        logger.warning("Aucune action spécifiée (ex: --get-python-path ou --run-command). Affichage de l'aide.")
        parser.print_help()


if __name__ == "__main__":
    main()