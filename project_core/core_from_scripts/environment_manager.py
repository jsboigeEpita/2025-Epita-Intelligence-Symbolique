"""
Gestionnaire de fichiers d'environnement (.env)

Ce module centralise la logique pour la gestion des fichiers de configuration
d'environnement, permettant de basculer, créer et valider des configurations
stockées dans des fichiers .env.
"""
import os
import sys
import warnings
from project_core.core_from_scripts import load_dotenv
import json
import logging
from pathlib import Path
from typing import Optional, List
import subprocess
import argparse

# Assumant l'existence de cet utilitaire comme défini dans la roadmap
from argumentation_analysis.core.utils.shell_utils import execute_command

# Configuration du logger
logging.basicConfig(level=logging.INFO, format='[ENV_MGR] [%(asctime)s] - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnvironmentManager:
    """Gère la création, la validation et le changement de fichiers .env."""

    def __init__(self, project_root: Optional[Path] = None, logger: Optional[logging.Logger] = None):
        """
        Initialise le gestionnaire.
        """
        if project_root and isinstance(project_root, Path):
            self.project_root = project_root
        else:
            self.project_root = Path(__file__).resolve().parent.parent.parent
        
        self.logger = logger or logging.getLogger(__name__)

    def _get_conda_env_path(self, env_name: str) -> Optional[Path]:
        """Tente de trouver le chemin d'un environnement Conda."""
        # On essaie d'abord de deviner via les chemins standards
        conda_base_command = shutil.which("conda")
        if not conda_base_command:
            self.logger.warning("Commande 'conda' non trouvée dans le PATH.")
            return None
        
        try:
            # Exécute `conda info --json` pour obtenir des infos sur l'installation
            result = subprocess.run(['conda', 'info', '--json'], capture_output=True, text=True, check=True)
            conda_info = json.loads(result.stdout)
            env_dirs = conda_info.get('envs_dirs', [])
            
            for env_dir in env_dirs:
                env_path = Path(env_dir) / env_name
                if env_path.is_dir():
                    self.logger.info(f"Environnement '{env_name}' trouvé à: {env_path}")
                    return env_path
        except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError) as e:
            self.logger.error(f"Erreur en cherchant l'environnement Conda: {e}")

        self.logger.error(f"Environnement conda '{env_name}' non trouvé.")
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