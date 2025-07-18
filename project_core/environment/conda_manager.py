"""
Gestionnaire des interactions avec Conda
=========================================

Ce module centralise la logique pour interagir avec l'outil Conda,
notamment :
- La localisation de l'exécutable conda.
- La vérification de l'existence d'environnements.
- L'exécution de commandes dans un environnement Conda.
- La logique de réinstallation d'environnement.

Auteur: Intelligence Symbolique EPITA
Date: 15/06/2025
"""

import os
import subprocess
import shutil
import platform
import json
from pathlib import Path
from typing import List, Optional, Union, Dict, Any

# Supposons que Logger, ColoredOutput et safe_exit soient accessibles
# via un chemin relatif ou soient passés en paramètres.
# Pour l'instant, on les importe comme dans le fichier original.
# Cela pourrait nécessiter un ajustement en fonction de la structure finale.
try:
    from ..core_from_scripts.common_utils import Logger, ColoredOutput, safe_exit
    from ..core_from_scripts.environment_manager import ReinstallComponent # Pour les types, si nécessaire
except ImportError:
    # Fallback pour exécution directe ou si la structure change
    # Ce fallback est simplifié et pourrait ne pas fonctionner sans ajustements
    # print("Avertissement: Impossible d'importer common_utils ou ReinstallComponent directement.")
    # Définitions basiques pour que le code ne plante pas à l'import
    class Logger:
        def __init__(self, verbose=False): self.verbose = verbose
        def debug(self, msg): print(f"DEBUG: {msg}")
        def info(self, msg): print(f"INFO: {msg}")
        def warning(self, msg): print(f"WARNING: {msg}")
        def error(self, msg, exc_info=False): print(f"ERROR: {msg}")
        def success(self, msg): print(f"SUCCESS: {msg}")
        def critical(self, msg): print(f"CRITICAL: {msg}")

    class ColoredOutput:
        @staticmethod
        def print_section(msg): print(f"\n--- {msg} ---")

    def safe_exit(code, logger_instance=None):
        if logger_instance:
            logger_instance.info(f"Sortie avec code {code}")
        sys.exit(code)
    
    import sys # Nécessaire pour le fallback de safe_exit


class CondaManager:
    """
    Gère les interactions avec Conda.
    """
    def __init__(self, logger: Logger = None, project_root: Path = None):
        self.logger = logger or Logger()
        self.project_root = project_root or Path(os.getcwd()) # Fallback simple
        self.conda_executable_path: Optional[str] = None
        self.default_conda_env = "projet-is" # Peut être configuré

    def _find_conda_executable(self) -> Optional[str]:
        """
        Localise l'exécutable conda de manière robuste sur le système.
        Utilise un cache pour éviter les recherches répétées.
        """
        if self.conda_executable_path:
            return self.conda_executable_path

        # Note: La logique de _discover_and_persist_conda_path_in_env_file
        # et _update_system_path_from_conda_env_var est omise ici car elle
        # dépend fortement du contexte de EnvironmentManager et de la gestion des .env.
        # Pour un CondaManager plus autonome, cette logique devrait être adaptée ou simplifiée.
        # Pour l'instant, on se base sur shutil.which et le PATH existant.

        conda_exe_name = "conda.exe" if platform.system() == "Windows" else "conda"
        self.logger.debug(f"Recherche de '{conda_exe_name}' avec shutil.which...")
        conda_path = shutil.which(conda_exe_name)

        if conda_path:
            self.logger.info(f"Exécutable Conda trouvé via shutil.which: {conda_path}")
            self.conda_executable_path = conda_path
            return self.conda_executable_path

        self.logger.warning(f"'{conda_exe_name}' non trouvé via shutil.which. Le PATH est peut-être incomplet.")
        self.logger.debug(f"PATH actuel: {os.environ.get('PATH')}")

        # Plan B : Tenter de lire CONDA_PATH depuis .env
        self.logger.info("Tentative de localisation de Conda via le fichier .env...")
        conda_path_from_env = self._get_var_from_dotenv("CONDA_PATH")
        if conda_path_from_env:
            self.logger.info(f"Variable CONDA_PATH trouvée dans .env: {conda_path_from_env}")
            original_path = os.environ.get('PATH', '')
            # Utiliser un séparateur approprié pour le système
            separator = os.pathsep
            new_path = f"{conda_path_from_env}{separator}{original_path}"
            os.environ['PATH'] = new_path
            
            self.logger.debug(f"Nouveau PATH (temporaire): {new_path}")
            
            # Nouvelle tentative avec le PATH mis à jour
            conda_path = shutil.which(conda_exe_name)
            if conda_path:
                self.logger.info(f"Exécutable Conda trouvé via .env et shutil.which: {conda_path}")
                self.conda_executable_path = conda_path
                return self.conda_executable_path

        self.logger.error("Échec final de la localisation de l'exécutable Conda.")
        return None

    def _get_var_from_dotenv(self, var_name: str) -> Optional[str]:
        """Lit une variable spécifique depuis le fichier .env à la racine."""
        dotenv_path = self.project_root / ".env"
        if not dotenv_path.is_file():
            self.logger.warning(f"Fichier .env introuvable à : {dotenv_path}")
            return None
        
        try:
            with open(dotenv_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if line.startswith(f"{var_name}="):
                        value = line.split('=', 1)[1].strip()
                        return value.strip('\'"')
            return None
        except IOError as e:
            self.logger.error(f"Erreur de lecture du fichier .env pour la variable '{var_name}': {e}")
            return None

    def _get_conda_env_path(self, env_name: str) -> Optional[str]:
        """Récupère le chemin complet d'un environnement conda par son nom."""
        conda_exe = self._find_conda_executable()
        if not conda_exe: return None

        try:
            cmd = [conda_exe, 'env', 'list', '--json']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, encoding='utf-8')
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                json_start_index = -1
                for i, line in enumerate(lines):
                    if line.strip().startswith('{'):
                        json_start_index = i
                        break
                
                if json_start_index == -1:
                    self.logger.warning("Impossible de trouver le début du JSON dans la sortie de 'conda env list'.")
                    return None

                json_content = '\n'.join(lines[json_start_index:])
                data = json.loads(json_content)

                for env_path_str in data.get('envs', []):
                    if Path(env_path_str).name == env_name:
                        self.logger.debug(f"Chemin trouvé pour '{env_name}': {env_path_str}")
                        return env_path_str
            else:
                 self.logger.warning(f"La commande 'conda env list --json' a échoué. Stderr: {result.stderr}")

            return None
        except (subprocess.SubprocessError, json.JSONDecodeError, subprocess.TimeoutExpired) as e:
            self.logger.error(f"Erreur lors de la recherche du chemin de l'environnement '{env_name}': {e}")
            return None

    def run_in_conda_env(self, command: Union[str, List[str]], env_name: str = None,
                         cwd: Optional[Union[str, Path]] = None, capture_output: bool = False) -> subprocess.CompletedProcess:
        """
        Exécute une commande dans un environnement conda de manière robuste en utilisant `conda run`.
        """
        if env_name is None:
            env_name = self.default_conda_env
        
        effective_cwd = str(cwd) if cwd else str(self.project_root)

        conda_exe = self._find_conda_executable()
        if not conda_exe:
            self.logger.error("Exécutable Conda non trouvé.")
            raise RuntimeError("Exécutable Conda non trouvé, impossible de continuer.")

        env_path = self._get_conda_env_path(env_name)
        if not env_path:
            self.logger.error(f"Impossible de trouver le chemin pour l'environnement conda '{env_name}'.")
            raise RuntimeError(f"Environnement conda '{env_name}' non disponible ou chemin inaccessible.")

        is_complex_string_command = isinstance(command, str) and (';' in command or '&&' in command or '|' in command)

        if is_complex_string_command:
            if platform.system() == "Windows":
                final_command = [conda_exe, 'run', '--prefix', env_path, '--no-capture-output', 'cmd.exe', '/c', command]
            else:
                final_command = [conda_exe, 'run', '--prefix', env_path, '--no-capture-output', 'bash', '-c', command]
        else:
            import shlex # Import localisé car spécifique à ce bloc
            if isinstance(command, str):
                base_command = shlex.split(command, posix=(os.name != 'nt'))
            else:
                base_command = command
            
            final_command = [
                conda_exe, 'run', '--prefix', env_path,
                '--no-capture-output' # Important pour la robustesse
            ] + base_command
        
        self.logger.info(f"Commande d'exécution via 'conda run': {' '.join(final_command)}")

        try:
            # Si capture_output est True, on capture stdout/stderr. Sinon, ils vont au terminal parent.
            # Note: le --no-capture-output de 'conda run' est pour conda lui-même, pas pour subprocess.run
            process_kwargs: Dict[str, Any] = {
                "cwd": effective_cwd,
                "text": True,
                "encoding": 'utf-8',
                "errors": 'replace',
                "check": False, # On gère le code de retour nous-mêmes
                "timeout": 3600
            }
            if capture_output:
                process_kwargs["capture_output"] = True
            
            result = subprocess.run(final_command, **process_kwargs)

            if result.returncode == 0:
                self.logger.debug(f"'conda run' exécuté avec succès (code {result.returncode}).")
            else:
                self.logger.warning(f"'conda run' terminé avec le code: {result.returncode}.")
                if capture_output:
                    self.logger.debug(f"Stdout: {result.stdout}")
                    self.logger.debug(f"Stderr: {result.stderr}")
            
            return result

        except subprocess.TimeoutExpired as e:
            self.logger.error(f"La commande a dépassé le timeout de 3600 secondes : {e}")
            raise
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            self.logger.error(f"Erreur majeure lors de l'exécution de 'conda run': {e}")
            raise

    def check_conda_env_exists(self, env_name: str) -> bool:
        """Vérifie si un environnement conda existe en cherchant son chemin."""
        env_path = self._get_conda_env_path(env_name)
        if env_path:
            self.logger.debug(f"Environnement conda '{env_name}' trouvé à l'emplacement : {env_path}")
            return True
        else:
            self.logger.warning(f"Environnement conda '{env_name}' non trouvé parmi les environnements existants.")
            return False

    def reinstall_pip_dependencies(self, env_name: str, requirements_file_path: Union[str, Path]):
        """Force la réinstallation des dépendances pip depuis un fichier requirements."""
        ColoredOutput.print_section(f"Réinstallation forcée des paquets PIP pour l'env '{env_name}'")
        
        # Note: La validation de l'environnement Java est omise ici,
        # car elle est très spécifique au EnvironmentManager original.
        # Si nécessaire, elle pourrait être ajoutée comme une étape optionnelle.

        if not self.check_conda_env_exists(env_name):
            self.logger.critical(f"L'environnement '{env_name}' n'existe pas. Impossible de réinstaller les dépendances.")
            safe_exit(1, self.logger)
            
        req_path = Path(requirements_file_path)
        if not req_path.exists():
            self.logger.critical(f"Le fichier de dépendances n'a pas été trouvé: {req_path}")
            safe_exit(1, self.logger)

        self.logger.info(f"Lancement de la réinstallation depuis {req_path}...")
        pip_install_command = [
            'pip', 'install',
            '--no-cache-dir',
            '--force-reinstall',
            '-r', str(req_path)
        ]
        
        result = self.run_in_conda_env(pip_install_command, env_name=env_name)
        
        if result.returncode != 0:
            self.logger.error(f"Échec de la réinstallation des dépendances PIP. Voir logs ci-dessus.")
            safe_exit(1, self.logger)
        
        self.logger.success("Réinstallation des dépendances PIP terminée.")

    def reinstall_conda_environment(self, env_name: str, python_version: str = "3.10", requirements_file_path: Optional[Union[str, Path]] = None):
        """Supprime et recrée intégralement l'environnement conda."""
        ColoredOutput.print_section(f"Réinstallation complète de l'environnement Conda '{env_name}'")

        conda_exe = self._find_conda_executable()
        if not conda_exe:
            self.logger.critical("Impossible de trouver l'exécutable Conda. La réinstallation ne peut pas continuer.")
            safe_exit(1, self.logger)
        self.logger.info(f"Utilisation de l'exécutable Conda : {conda_exe}")

        if self.check_conda_env_exists(env_name):
            self.logger.info(f"Suppression de l'environnement existant '{env_name}'...")
            # Utiliser subprocess.run directement car run_in_conda_env n'est pas adapté pour 'conda env remove'
            remove_cmd = [conda_exe, 'env', 'remove', '-n', env_name, '--y']
            self.logger.debug(f"Exécution: {' '.join(remove_cmd)}")
            remove_result = subprocess.run(remove_cmd, check=False, capture_output=True, text=True)
            if remove_result.returncode != 0:
                self.logger.error(f"Échec de la suppression de l'environnement '{env_name}'. Stderr: {remove_result.stderr}")
                safe_exit(1, self.logger)
            self.logger.success(f"Environnement '{env_name}' supprimé.")
        else:
            self.logger.info(f"L'environnement '{env_name}' n'existe pas, pas besoin de le supprimer.")

        self.logger.info(f"Création du nouvel environnement '{env_name}' avec Python {python_version}...")
        create_cmd = [conda_exe, 'create', '-n', env_name, f'python={python_version}', '--y']
        self.logger.debug(f"Exécution: {' '.join(create_cmd)}")
        create_result = subprocess.run(create_cmd, check=False, capture_output=True, text=True)
        if create_result.returncode != 0:
            self.logger.error(f"Échec de la création de l'environnement '{env_name}'. Stderr: {create_result.stderr}")
            safe_exit(1, self.logger)
        self.logger.success(f"Environnement '{env_name}' recréé.")
        
        if requirements_file_path:
            self.reinstall_pip_dependencies(env_name, requirements_file_path)
        else:
            self.logger.info("Aucun fichier requirements fourni, les dépendances PIP ne sont pas réinstallées automatiquement.")

if __name__ == '__main__':
    # Exemple d'utilisation
    logger = Logger(verbose=True)
    # Assurez-vous que project_root est correctement défini si nécessaire pour les chemins relatifs.
    # Par exemple, pour trouver un requirements.txt à la racine du projet.
    project_root_path = Path(__file__).resolve().parent.parent.parent 
    
    manager = CondaManager(logger=logger, project_root=project_root_path)

    # Test _find_conda_executable
    conda_exe = manager._find_conda_executable()
    if conda_exe:
        logger.success(f"Conda executable found: {conda_exe}")
    else:
        logger.error("Conda executable not found.")

    # Test check_conda_env_exists
    env_to_check = "base" # ou manager.default_conda_env
    if manager.check_conda_env_exists(env_to_check):
        logger.success(f"Conda environment '{env_to_check}' exists.")
        
        # Test run_in_conda_env (exemple simple)
        try:
            logger.info(f"Tentative d'exécution de 'python --version' dans l'env '{env_to_check}'")
            result = manager.run_in_conda_env("python --version", env_name=env_to_check, capture_output=True)
            if result.returncode == 0:
                logger.success(f"Commande exécutée avec succès. Python version: {result.stdout.strip()}")
            else:
                logger.error(f"Échec de l'exécution de la commande. Stderr: {result.stderr}")
        except Exception as e:
            logger.error(f"Erreur lors du test de run_in_conda_env: {e}")
            
    else:
        logger.warning(f"Conda environment '{env_to_check}' does not exist. Certains tests seront sautés.")

    # Pour tester la réinstallation (ATTENTION: cela modifiera votre environnement)
    # test_reinstall = False
    # if test_reinstall:
    #     test_env_name = "test-conda-manager-env"
    #     req_file = project_root_path / "argumentation_analysis" / "requirements.txt" # Ajustez si nécessaire
    #     if not req_file.exists():
    #         logger.warning(f"Fichier requirements {req_file} non trouvé, la réinstallation PIP sera sautée.")
    #         req_file = None
    #     try:
    #         manager.reinstall_conda_environment(test_env_name, python_version="3.9", requirements_file_path=req_file)
    #         logger.success(f"Réinstallation de '{test_env_name}' terminée (si aucune erreur n'est survenue).")
    #     except Exception as e:
    #         logger.error(f"Erreur lors du test de réinstallation: {e}")