"""
Gestionnaire d'environnements Python/conda
==========================================

Ce module centralise la gestion des environnements Python et conda :
- Vérification et activation d'environnements conda
- Validation des dépendances Python
- Gestion des variables d'environnement
- Exécution de commandes dans l'environnement projet

Auteur: Intelligence Symbolique EPITA
Date: 09/06/2025
"""

import os
import sys
import subprocess
import argparse
import json # Ajout de l'import json au niveau supérieur
from typing import Dict, List, Optional, Tuple, Any, Union
from pathlib import Path
import shutil # Ajout pour shutil.which
import platform # Ajout pour la détection OS-spécifique des chemins communs
from dotenv import load_dotenv, find_dotenv # Ajout pour la gestion .env

# Import relatif corrigé - gestion des erreurs d'import
try:
    from .common_utils import Logger, LogLevel, safe_exit, get_project_root
except ImportError:
    # Fallback pour execution directe
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from common_utils import Logger, LogLevel, safe_exit, get_project_root


# --- Début de l'insertion pour sys.path ---
# Déterminer la racine du projet (remonter de deux niveaux depuis scripts/core)
# __file__ est scripts/core/environment_manager.py
# .parent est scripts/core
# .parent.parent est scripts
# .parent.parent.parent est la racine du projet
_project_root_for_sys_path = Path(__file__).resolve().parent.parent.parent
if str(_project_root_for_sys_path) not in sys.path:
    sys.path.insert(0, str(_project_root_for_sys_path))
# --- Fin de l'insertion pour sys.path ---
# from scripts.core.auto_env import _load_dotenv_intelligent # MODIFIÉ ICI - Sera supprimé
class EnvironmentManager:
    """Gestionnaire centralisé des environnements Python/conda"""
    
    def __init__(self, logger: Logger = None):
        """
        Initialise le gestionnaire d'environnement
        
        Args:
            logger: Instance de logger à utiliser
        """
        self.logger = logger or Logger()
        self.project_root = Path(get_project_root())
        # Le chargement initial de .env (y compris la découverte/persistance de CONDA_PATH)
        # est maintenant géré au début de la méthode auto_activate_env.
        # L'appel à _load_dotenv_intelligent ici est donc redondant et supprimé.
        
        # Le code pour rendre JAVA_HOME absolu est déplacé vers la méthode activate_project_environment
        # pour s'assurer qu'il s'exécute APRÈS le chargement du fichier .env.
        
        self.default_conda_env = "projet-is"
        self.required_python_version = (3, 8)
        
        # Variables d'environnement importantes
        self.env_vars = {
            'PYTHONIOENCODING': 'utf-8',
            'PYTHONPATH': str(self.project_root),
            'PROJECT_ROOT': str(self.project_root)
        }
        self.conda_executable_path = None # Cache pour le chemin de l'exécutable conda

    def _find_conda_executable(self) -> Optional[str]:
        """
        Localise l'exécutable conda de manière robuste sur le système.
        Utilise un cache pour éviter les recherches répétées.
        """
        if self.conda_executable_path:
            return self.conda_executable_path
        
        # S'assurer que les variables d'environnement (.env) et le PATH sont à jour
        self._discover_and_persist_conda_path_in_env_file(self.project_root)
        self._update_system_path_from_conda_env_var()
        
        # Chercher 'conda.exe' sur Windows, 'conda' sinon
        conda_exe_name = "conda.exe" if platform.system() == "Windows" else "conda"
        
        # 1. Utiliser shutil.which qui est le moyen le plus fiable
        self.logger.debug(f"Recherche de '{conda_exe_name}' avec shutil.which...")
        conda_path = shutil.which(conda_exe_name)
        
        if conda_path:
            self.logger.info(f"Exécutable Conda trouvé via shutil.which: {conda_path}")
            self.conda_executable_path = conda_path
            return self.conda_executable_path
            
        self.logger.warning(f"'{conda_exe_name}' non trouvé via shutil.which. Le PATH est peut-être incomplet.")
        self.logger.debug(f"PATH actuel: {os.environ.get('PATH')}")
        return None

    def check_conda_available(self) -> bool:
        """Vérifie si conda est disponible en trouvant son exécutable."""
        return self._find_conda_executable() is not None
    
    def check_python_version(self, python_cmd: str = "python") -> bool:
        """Vérifie la version de Python"""
        try:
            result = subprocess.run(
                [python_cmd, '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                version_str = result.stdout.strip()
                self.logger.debug(f"Python trouvé: {version_str}")
                
                # Parser la version
                import re
                match = re.search(r'Python (\d+)\.(\d+)', version_str)
                if match:
                    major, minor = int(match.group(1)), int(match.group(2))
                    if (major, minor) >= self.required_python_version:
                        return True
                    else:
                        self.logger.warning(
                            f"Version Python {major}.{minor} < requise {self.required_python_version[0]}.{self.required_python_version[1]}"
                        )
                
        except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired):
            self.logger.warning(f"Impossible de vérifier Python avec '{python_cmd}'")
        
        return False
    
    def list_conda_environments(self) -> List[str]:
        """Liste les environnements conda disponibles"""
        conda_exe = self._find_conda_executable()
        if not conda_exe:
            self.logger.error("Impossible de lister les environnements car Conda n'est pas trouvable.")
            return []
        
        try:
            cmd = [conda_exe, 'env', 'list', '--json']
            self.logger.debug(f"Exécution de la commande pour lister les environnements: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                encoding='utf-8'
            )
            
            if result.returncode == 0:
                self.logger.debug(f"conda env list stdout: {result.stdout[:200]}...")
                self.logger.debug(f"conda env list stderr: {result.stderr[:200]}...")
                try:
                    # Extraire seulement la partie JSON (après la première ligne de config UTF-8)
                    lines = result.stdout.strip().split('\n')
                    json_start = 0
                    for i, line in enumerate(lines):
                        if line.strip().startswith('{'):
                            json_start = i
                            break
                    json_content = '\n'.join(lines[json_start:])
                    
                    # import json # Supprimé car importé au niveau supérieur
                    data = json.loads(json_content)
                    envs = []
                    for env_path in data.get('envs', []):
                        env_name = Path(env_path).name
                        envs.append(env_name)
                    self.logger.debug(f"Environnements trouvés: {envs}")
                    return envs
                except json.JSONDecodeError as e:
                    self.logger.warning(f"Erreur JSON decode: {e}")
                    self.logger.debug(f"JSON problématique: {repr(result.stdout)}")
            else:
                self.logger.warning(f"conda env list échoué. Code: {result.returncode}, Stderr: {result.stderr}")
        
        except (subprocess.SubprocessError, subprocess.TimeoutExpired) as e:
            self.logger.debug(f"Erreur subprocess lors de la liste des environnements conda: {e}")
        
        return []
    
    def check_conda_env_exists(self, env_name: str) -> bool:
        """Vérifie si un environnement conda existe"""
        environments = self.list_conda_environments()
        exists = env_name in environments
        
        if exists:
            self.logger.debug(f"Environnement conda '{env_name}' trouvé")
        else:
            self.logger.warning(f"Environnement conda '{env_name}' non trouvé")
        
        return exists
    
    def setup_environment_variables(self, additional_vars: Dict[str, str] = None):
        """Configure les variables d'environnement pour le projet"""
        env_vars = self.env_vars.copy()
        if additional_vars:
            env_vars.update(additional_vars)
        
        for key, value in env_vars.items():
            os.environ[key] = value
            self.logger.debug(f"Variable d'environnement définie: {key}={value}")
        
        # RUSTINE DE DERNIER RECOURS
        # Ajouter manuellement le `site-packages` de l'environnement au PYTHONPATH.
        conda_prefix = os.environ.get("CONDA_PREFIX")
        if conda_prefix and "projet-is" in conda_prefix:
            site_packages_path = os.path.join(conda_prefix, "lib", "site-packages")
            python_path = os.environ.get("PYTHONPATH", "")
            if site_packages_path not in python_path:
                os.environ["PYTHONPATH"] = f"{site_packages_path}{os.pathsep}{python_path}"
                self.logger.warning(f"RUSTINE: Ajout forcé de {site_packages_path} au PYTHONPATH.")
    
    def run_in_conda_env(self, command: Union[str, List[str]], env_name: str = None,
                         cwd: str = None, capture_output: bool = False) -> subprocess.CompletedProcess:
        """
        Exécute une commande dans un environnement conda de manière robuste en utilisant `conda run`.
        Cette méthode délègue l'activation de l'environnement à Conda lui-même,
        ce qui est plus fiable que la manipulation manuelle du PATH.
        """
        if env_name is None:
            env_name = self.default_conda_env
        if cwd is None:
            cwd = self.project_root
        
        conda_exe = self._find_conda_executable()
        if not conda_exe:
            self.logger.error("Exécutable Conda non trouvé.")
            raise RuntimeError("Exécutable Conda non trouvé, impossible de continuer.")

        if not self.check_conda_env_exists(env_name):
            self.logger.error(f"Environnement conda '{env_name}' non trouvé.")
            raise RuntimeError(f"Environnement conda '{env_name}' non disponible.")

        import shlex
        if isinstance(command, str):
            base_command = shlex.split(command, posix=(os.name != 'nt'))
        else:
            base_command = command

        # Construction de la commande avec 'conda run'
        # --no-capture-output et --live-stream sont essentiels pour que les processus interactifs
        # et les installations longues fonctionnent correctement et affichent leur sortie en direct.
        final_command = [
            conda_exe, 'run', '-n', env_name,
            '--no-capture-output',
            # '--live-stream', # Peut causer des pbs avec capture_output, géré manuellement
        ] + base_command
        
        self.logger.info(f"Commande d'exécution via 'conda run': {' '.join(final_command)}")

        try:
            # Utiliser Popen pour un meilleur contrôle du streaming
            process = subprocess.Popen(
                final_command,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace'
            )

            stdout_lines = []
            stderr_lines = []

            # Lire stdout et stderr en temps réel pour éviter les blocages
            while True:
                # Lire une ligne de stdout
                stdout_line = process.stdout.readline()
                if stdout_line:
                    line = stdout_line.strip()
                    self.logger.info(line) # Afficher en direct dans le log
                    stdout_lines.append(line)
                
                # Lire une ligne de stderr
                stderr_line = process.stderr.readline()
                if stderr_line:
                    line = stderr_line.strip()
                    self.logger.error(line) # Afficher en direct dans le log
                    stderr_lines.append(line)
                
                # Sortir si le processus est terminé et qu'il n'y a plus de sortie
                if process.poll() is not None and not stdout_line and not stderr_line:
                    break
            
            # Récupérer le code de sortie final
            returncode = process.wait()

            # Créer un objet CompletedProcess pour la rétrocompatibilité
            result = subprocess.CompletedProcess(
                args=final_command,
                returncode=returncode,
                stdout='\n'.join(stdout_lines),
                stderr='\n'.join(stderr_lines)
            )

            if result.returncode == 0:
                self.logger.debug(f"'conda run' exécuté avec succès (code {result.returncode}).")
            else:
                self.logger.warning(f"'conda run' terminé avec le code: {result.returncode}")
            
            return result

        except (subprocess.SubprocessError, FileNotFoundError) as e:
            self.logger.error(f"Erreur lors de l'exécution de 'conda run': {e}")
            raise
    
    def check_python_dependencies(self, requirements: List[str], env_name: str = None) -> Dict[str, bool]:
        """
        Vérifie si les dépendances Python sont installées
        
        Args:
            requirements: Liste des packages requis
            env_name: Nom de l'environnement conda
        
        Returns:
            Dictionnaire package -> installé (bool)
        """
        if env_name is None:
            env_name = self.default_conda_env
        
        results = {}
        
        for package in requirements:
            try:
                # Utiliser pip show pour vérifier l'installation
                result = self.run_in_conda_env(
                    ['pip', 'show', package],
                    env_name=env_name,
                    capture_output=True
                )
                results[package] = result.returncode == 0
                
                if result.returncode == 0:
                    self.logger.debug(f"Package '{package}' installé")
                else:
                    self.logger.warning(f"Package '{package}' non installé")
            
            except Exception as e:
                self.logger.debug(f"Erreur vérification '{package}': {e}")
                results[package] = False
        
        return results
    
    def install_python_dependencies(self, requirements: List[str], env_name: str = None) -> bool:
        """
        Installe les dépendances Python manquantes
        
        Args:
            requirements: Liste des packages à installer
            env_name: Nom de l'environnement conda
        
        Returns:
            True si installation réussie
        """
        if env_name is None:
            env_name = self.default_conda_env
        
        if not requirements:
            return True
        
        self.logger.info(f"Installation de {len(requirements)} packages...")
        
        try:
            # Installer via pip dans l'environnement conda
            pip_cmd = ['pip', 'install'] + requirements
            result = self.run_in_conda_env(pip_cmd, env_name=env_name)
            
            if result.returncode == 0:
                self.logger.success("Installation des dépendances réussie")
                return True
            else:
                self.logger.error("Échec de l'installation des dépendances")
                return False
        
        except Exception as e:
            self.logger.error(f"Erreur lors de l'installation: {e}")
            return False
    
    def activate_project_environment(self, command_to_run: str = None, env_name: str = None) -> int:
        """
        Active l'environnement projet et exécute optionnellement une commande
        
        Args:
            command_to_run: Commande à exécuter après activation
            env_name: Nom de l'environnement conda
        
        Returns:
            Code de sortie de la commande
        """
        if env_name is None:
            env_name = self.default_conda_env
        
        self.logger.info(f"Activation de l'environnement '{env_name}'...")

        # --- BLOC D'ACTIVATION UNIFIÉ ---
        self.logger.info("Début du bloc d'activation unifié...")

        # 1. Charger le fichier .env de base
        dotenv_path = find_dotenv()
        if dotenv_path:
            self.logger.info(f"Fichier .env trouvé et chargé depuis : {dotenv_path}")
            load_dotenv(dotenv_path, override=True)
        else:
            self.logger.info("Aucun fichier .env trouvé, tentative de création/mise à jour.")

        # 2. Découvrir et persister CONDA_PATH dans le .env si nécessaire
        # Cette méthode met à jour le fichier .env et recharge les variables dans os.environ
        self._discover_and_persist_conda_path_in_env_file(self.project_root, silent=False)

        # 3. Mettre à jour le PATH du processus courant à partir de CONDA_PATH (maintenant dans os.environ)
        # Ceci est crucial pour que les appels directs à `conda` ou `python` fonctionnent.
        self._update_system_path_from_conda_env_var(silent=False)

        # Assurer que JAVA_HOME est un chemin absolu APRÈS avoir chargé .env
        if 'JAVA_HOME' in os.environ:
            java_home_value = os.environ['JAVA_HOME']
            if not Path(java_home_value).is_absolute():
                absolute_java_home = (Path(self.project_root) / java_home_value).resolve()
                if absolute_java_home.exists() and absolute_java_home.is_dir():
                    os.environ['JAVA_HOME'] = str(absolute_java_home)
                    self.logger.info(f"JAVA_HOME (de .env) converti en chemin absolu: {os.environ['JAVA_HOME']}")
                else:
                    self.logger.warning(f"Le chemin JAVA_HOME (de .env) résolu vers {absolute_java_home} est invalide.")
        
        # **CORRECTION DE ROBUSTESSE POUR JPYPE**
        # S'assurer que le répertoire bin de la JVM est dans le PATH
        if 'JAVA_HOME' in os.environ:
            java_bin_path = Path(os.environ['JAVA_HOME']) / 'bin'
            if java_bin_path.is_dir():
                if str(java_bin_path) not in os.environ['PATH']:
                    os.environ['PATH'] = f"{java_bin_path}{os.pathsep}{os.environ['PATH']}"
                    self.logger.info(f"Ajouté {java_bin_path} au PATH pour la JVM.")
        
        # Vérifications préalables
        if not self.check_conda_available():
            self.logger.error("Conda non disponible")
            return 1
        
        if not self.check_conda_env_exists(env_name):
            self.logger.error(f"Environnement '{env_name}' non trouvé")
            return 1
        
        # Configuration des variables d'environnement
        self.setup_environment_variables()
        
        if command_to_run:
            self.logger.info(f"Exécution de: {command_to_run}")
            
            try:
                # La commande est maintenant passée comme une chaîne unique à run_in_conda_env
                # qui va la gérer pour l'exécution via un shell si nécessaire.
                self.logger.info(f"DEBUG: command_to_run (chaîne) avant run_in_conda_env: {command_to_run}")
                result = self.run_in_conda_env(command_to_run, env_name=env_name) # Passer la chaîne directement
                return result.returncode
            
            except Exception as e:
                self.logger.error(f"Erreur lors de l'exécution: {e}")
                return 1
        else:
            self.logger.success(f"Environnement '{env_name}' activé (via activate_project_environment)")
            return 0

    # --- Méthodes transférées et adaptées depuis auto_env.py ---

    def _update_system_path_from_conda_env_var(self, silent: bool = True) -> bool:
        """
        Met à jour le PATH système avec le chemin conda depuis la variable CONDA_PATH (os.environ).
        """
        try:
            conda_path_value = os.environ.get('CONDA_PATH', '')
            if not conda_path_value:
                if not silent:
                    self.logger.info("CONDA_PATH non défini dans os.environ pour _update_system_path_from_conda_env_var.")
                return False
            
            conda_paths_list = [p.strip() for p in conda_path_value.split(os.pathsep) if p.strip()]
            
            current_os_path = os.environ.get('PATH', '')
            path_elements = current_os_path.split(os.pathsep)
            
            updated = False
            for conda_dir_to_add in reversed(conda_paths_list): # reversed pour maintenir l'ordre d'ajout
                if conda_dir_to_add not in path_elements:
                    path_elements.insert(0, conda_dir_to_add)
                    updated = True
                    if not silent:
                        self.logger.info(f"[PATH] Ajout au PATH système: {conda_dir_to_add}")
            
            if updated:
                new_path_str = os.pathsep.join(path_elements)
                os.environ['PATH'] = new_path_str
                if not silent:
                    self.logger.info("[PATH] PATH système mis à jour avec les chemins de CONDA_PATH.")
                return True
            else:
                if not silent:
                    self.logger.info("[PATH] PATH système déjà configuré avec les chemins de CONDA_PATH.")
                return True # Déjà configuré est un succès
                
        except Exception as e_path_update:
            if not silent:
                self.logger.warning(f"[PATH] Erreur lors de la mise à jour du PATH système depuis CONDA_PATH: {e_path_update}")
            return False

    def _discover_and_persist_conda_path_in_env_file(self, project_root: Path, silent: bool = True) -> bool:
        """
        Tente de découvrir les chemins d'installation de Conda et, si CONDA_PATH
        n'est pas déjà dans os.environ (via .env initial), met à jour le fichier .env.
        Recharge ensuite os.environ depuis .env.
        Retourne True si CONDA_PATH est maintenant dans os.environ (après tentative de découverte et écriture).
        """
        if os.environ.get('CONDA_PATH'):
            if not silent:
                self.logger.info("[.ENV DISCOVERY] CONDA_PATH déjà présent dans l'environnement.")
            return True

        if not silent:
            self.logger.info("[.ENV DISCOVERY] CONDA_PATH non trouvé dans l'environnement initial. Tentative de découverte...")

        discovered_paths_collector = []
        
        conda_exe_env_var = os.environ.get('CONDA_EXE')
        if conda_exe_env_var:
            conda_exe_file_path = Path(conda_exe_env_var)
            if conda_exe_file_path.is_file():
                if not silent: self.logger.debug(f"[.ENV DISCOVERY] CONDA_EXE trouvé: {conda_exe_file_path}")
                condabin_dir_path = conda_exe_file_path.parent
                scripts_dir_path = condabin_dir_path.parent / "Scripts"
                if condabin_dir_path.is_dir(): discovered_paths_collector.append(str(condabin_dir_path))
                if scripts_dir_path.is_dir(): discovered_paths_collector.append(str(scripts_dir_path))
        
        if not discovered_paths_collector:
            conda_root_env_var = os.environ.get('CONDA_ROOT') or os.environ.get('CONDA_PREFIX')
            if conda_root_env_var:
                conda_root_dir_path = Path(conda_root_env_var)
                if conda_root_dir_path.is_dir():
                    if not silent: self.logger.debug(f"[.ENV DISCOVERY] CONDA_ROOT/PREFIX trouvé: {conda_root_dir_path}")
                    condabin_dir_path = conda_root_dir_path / "condabin"
                    scripts_dir_path = conda_root_dir_path / "Scripts"
                    if condabin_dir_path.is_dir(): discovered_paths_collector.append(str(condabin_dir_path))
                    if scripts_dir_path.is_dir(): discovered_paths_collector.append(str(scripts_dir_path))

        if not discovered_paths_collector:
            conda_executable_shutil = shutil.which('conda')
            if conda_executable_shutil:
                conda_exe_shutil_path = Path(conda_executable_shutil).resolve()
                if conda_exe_shutil_path.is_file():
                    if not silent: self.logger.debug(f"[.ENV DISCOVERY] 'conda' trouvé via shutil.which: {conda_exe_shutil_path}")
                    if conda_exe_shutil_path.parent.name.lower() in ["condabin", "scripts", "bin"]:
                        conda_install_root_path = conda_exe_shutil_path.parent.parent
                        
                        cb_dir = conda_install_root_path / "condabin"
                        s_dir_win = conda_install_root_path / "Scripts"
                        b_dir_unix = conda_install_root_path / "bin"
                        lib_bin_win = conda_install_root_path / "Library" / "bin"

                        if cb_dir.is_dir(): discovered_paths_collector.append(str(cb_dir))
                        if platform.system() == "Windows":
                            if s_dir_win.is_dir(): discovered_paths_collector.append(str(s_dir_win))
                            if lib_bin_win.is_dir(): discovered_paths_collector.append(str(lib_bin_win))
                        else:
                            if b_dir_unix.is_dir(): discovered_paths_collector.append(str(b_dir_unix))
        
        if not discovered_paths_collector:
            if not silent: self.logger.debug("[.ENV DISCOVERY] Tentative de recherche dans les chemins d'installation communs...")
            potential_install_roots_list = []
            system_os_name = platform.system()
            home_dir = Path.home()

            if system_os_name == "Windows":
                program_data_dir = Path(os.environ.get("ProgramData", "C:/ProgramData"))
                local_app_data_env_str = os.environ.get("LOCALAPPDATA")
                local_app_data_dir = Path(local_app_data_env_str) if local_app_data_env_str else home_dir / "AppData" / "Local"
                
                potential_install_roots_list.extend([
                    Path("C:/tools/miniconda3"), Path("C:/tools/anaconda3"),
                    home_dir / "anaconda3", home_dir / "miniconda3",
                    home_dir / "Anaconda3", home_dir / "Miniconda3",
                    program_data_dir / "Anaconda3", program_data_dir / "Miniconda3",
                    local_app_data_dir / "Continuum" / "anaconda3"
                ])
            else:
                potential_install_roots_list.extend([
                    home_dir / "anaconda3", home_dir / "miniconda3",
                    home_dir / ".anaconda3", home_dir / ".miniconda3",
                    Path("/opt/anaconda3"), Path("/opt/miniconda3"),
                    Path("/usr/local/anaconda3"), Path("/usr/local/miniconda3")
                ])
            
            found_root_from_common_paths = None
            for root_candidate_path in potential_install_roots_list:
                if root_candidate_path.is_dir():
                    condabin_check_path = root_candidate_path / "condabin"
                    scripts_check_win_path = root_candidate_path / "Scripts"
                    bin_check_unix_path = root_candidate_path / "bin"
                    
                    conda_exe_found_in_candidate = False
                    if system_os_name == "Windows":
                        if (condabin_check_path / "conda.bat").exists() or \
                           (condabin_check_path / "conda.exe").exists() or \
                           (scripts_check_win_path / "conda.exe").exists():
                            conda_exe_found_in_candidate = True
                    else:
                        if (bin_check_unix_path / "conda").exists() or \
                           (condabin_check_path / "conda").exists():
                            conda_exe_found_in_candidate = True

                    if conda_exe_found_in_candidate and condabin_check_path.is_dir() and \
                       ((system_os_name == "Windows" and scripts_check_win_path.is_dir()) or \
                        (system_os_name != "Windows" and bin_check_unix_path.is_dir())):
                        if not silent: self.logger.debug(f"[.ENV DISCOVERY] Racine Conda potentielle trouvée: {root_candidate_path}")
                        found_root_from_common_paths = root_candidate_path
                        break
            
            if found_root_from_common_paths:
                cb_p = found_root_from_common_paths / "condabin"
                s_p_win = found_root_from_common_paths / "Scripts"
                b_p_unix = found_root_from_common_paths / "bin"
                lb_p_win = found_root_from_common_paths / "Library" / "bin"

                def add_valid_path_to_list(path_obj_to_add, target_list):
                    if path_obj_to_add.is_dir() and str(path_obj_to_add) not in target_list:
                        target_list.append(str(path_obj_to_add))

                add_valid_path_to_list(cb_p, discovered_paths_collector)
                if system_os_name == "Windows":
                    add_valid_path_to_list(s_p_win, discovered_paths_collector)
                    add_valid_path_to_list(lb_p_win, discovered_paths_collector)
                else:
                    add_valid_path_to_list(b_p_unix, discovered_paths_collector)

        ordered_unique_paths_list = []
        seen_paths_set = set()
        for p_str_item in discovered_paths_collector:
            if p_str_item not in seen_paths_set:
                ordered_unique_paths_list.append(p_str_item)
                seen_paths_set.add(p_str_item)
        
        if ordered_unique_paths_list:
            conda_path_to_write = os.pathsep.join(ordered_unique_paths_list)
            if not silent: self.logger.debug(f"[.ENV DISCOVERY] Chemins Conda consolidés: {conda_path_to_write}")

            env_file = project_root / ".env"
            current_env_lines = []
            conda_path_line_updated_in_file = False

            if env_file.exists():
                with open(env_file, 'r', encoding='utf-8') as f_read_env:
                    current_env_lines = f_read_env.readlines()
                
                for i, line_content in enumerate(current_env_lines):
                    stripped_line_content = line_content.strip()
                    if stripped_line_content.startswith("CONDA_PATH="):
                        current_env_lines[i] = f'CONDA_PATH="{conda_path_to_write}"\n'
                        conda_path_line_updated_in_file = True
                        if not silent: self.logger.info(f"[.ENV] Ligne CONDA_PATH existante mise à jour dans {env_file}")
                        break
            
            if not conda_path_line_updated_in_file:
                if current_env_lines and not current_env_lines[-1].endswith('\n') and current_env_lines[-1].strip() != "":
                    current_env_lines.append('\n')
                current_env_lines.append(f'CONDA_PATH="{conda_path_to_write}"\n')
                if not silent: self.logger.info(f"[.ENV] Nouvelle ligne CONDA_PATH ajoutée à {env_file}")

            try:
                with open(env_file, 'w', encoding='utf-8') as f_write_env:
                    f_write_env.writelines(current_env_lines)
                if not silent: self.logger.info(f"[.ENV] Fichier {env_file} sauvegardé avec CONDA_PATH='{conda_path_to_write}'")
                
                # Recharger .env pour que os.environ soit mis à jour
                dotenv_path_for_reload_op = find_dotenv(str(env_file), usecwd=True, raise_error_if_not_found=False)
                if dotenv_path_for_reload_op:
                     load_dotenv(dotenv_path_for_reload_op, override=True) # Override pour prendre la nouvelle valeur
                     if not silent: self.logger.info(f"[.ENV] Variables rechargées depuis {dotenv_path_for_reload_op}")
                     return True # CONDA_PATH est maintenant dans os.environ
                else: # Ne devrait pas arriver
                    if not silent: self.logger.warning(f"[.ENV] Erreur: {env_file} non trouvé par find_dotenv après écriture.")
                    os.environ['CONDA_PATH'] = conda_path_to_write # Forcer au cas où
                    return True # Indiquer que CONDA_PATH est au moins dans os.environ

            except Exception as e_write_env:
                if not silent: self.logger.warning(f"[.ENV] Échec de la mise à jour du fichier {env_file}: {e_write_env}")
                return False # Échec de la persistance
        else:
            if not silent: self.logger.info("[.ENV DISCOVERY] Impossible de découvrir automatiquement les chemins Conda.")
            return False # Pas de chemins découverts, CONDA_PATH n'est pas résolu par cette fonction

    # --- Fin des méthodes transférées ---

def is_conda_env_active(env_name: str = "projet-is") -> bool:
    """Vérifie si l'environnement conda spécifié est actuellement actif"""
    current_env = os.environ.get('CONDA_DEFAULT_ENV', '')
    return current_env == env_name


def check_conda_env(env_name: str = "projet-is", logger: Logger = None) -> bool:
    """Fonction utilitaire pour vérifier un environnement conda"""
    manager = EnvironmentManager(logger)
    return manager.check_conda_env_exists(env_name)


def auto_activate_env(env_name: str = "projet-is", silent: bool = True) -> bool:
    """
    One-liner auto-activateur d'environnement intelligent.
    Cette fonction est maintenant une façade pour la logique d'activation centrale.
    """
    try:
        # Si le script d'activation principal est déjà en cours, on ne fait rien.
        if os.getenv('IS_ACTIVATION_SCRIPT_RUNNING') == 'true':
            return True

        logger = Logger(verbose=not silent)
        manager = EnvironmentManager(logger)
        
        # On appelle la méthode centrale d'activation SANS commande à exécuter.
        # Le code de sortie 0 indique le succès de l'ACTIVATION.
        exit_code = manager.activate_project_environment(env_name=env_name)
        
        is_success = (exit_code == 0)
        
        if not silent:
            if is_success:
                logger.success(f"Auto-activation de '{env_name}' réussie via le manager central.")
            else:
                logger.error(f"Échec de l'auto-activation de '{env_name}' via le manager central.")

        return is_success

    except Exception as e:
        if not silent:
            # Créer un logger temporaire si l'initialisation a échoué.
            temp_logger = Logger(verbose=True)
            temp_logger.error(f"❌ Erreur critique dans auto_activate_env: {e}", exc_info=True)
        return False


def activate_project_env(command: str = None, env_name: str = "projet-is", logger: Logger = None) -> int:
    """Fonction utilitaire pour activer l'environnement projet"""
    manager = EnvironmentManager(logger)
    return manager.activate_project_environment(command, env_name)


def main():
    """Point d'entrée principal pour utilisation en ligne de commande"""
    temp_logger = Logger(verbose=True) 
    temp_logger.info(f"DEBUG: sys.argv au début de main(): {sys.argv}")

    parser = argparse.ArgumentParser(
        description="Gestionnaire d'environnements Python/conda"
    )
    
    parser.add_argument(
        '--command', '-c',
        nargs=argparse.REMAINDER,
        help="Commande à exécuter. Doit être le dernier argument, tous les arguments suivants seront considérés comme faisant partie de la commande."
    )
    
    parser.add_argument(
        '--env-name', '-e',
        type=str,
        default='projet-is',
        help='Nom de l\'environnement conda (défaut: projet-is)'
    )
    
    parser.add_argument(
        '--check-only',
        action='store_true',
        help='Vérifier l\'environnement sans l\'activer'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Mode verbeux'
    )
    
    parser.add_argument(
        '--force-reinstall',
        action='store_true',
        help="Forcer la suppression et la recréation de l'environnement conda."
    )
    
    args = parser.parse_args() 
    
    logger = Logger(verbose=True) # FORCER VERBOSE POUR DEBUG (ou utiliser args.verbose)
    logger.info("DEBUG: Début de main() dans environment_manager.py (après parsing)")
    logger.info(f"DEBUG: Args parsés par argparse: {args}")
    
    manager = EnvironmentManager(logger)
    
    command_to_run_final = ' '.join(args.command) if args.command else None

    if args.force_reinstall:
        logger.info("FORCER LA RÉINSTALLATION DE L'ENVIRONNEMENT")
        env_name = args.env_name
        
        # 1. Trouver l'exécutable conda de manière robuste
        conda_exe = manager._find_conda_executable()
        if not conda_exe:
            logger.critical("Impossible de trouver l'exécutable Conda. La réinstallation ne peut pas continuer.")
            safe_exit(1, logger)
        logger.info(f"Utilisation de l'exécutable Conda : {conda_exe}")
        
        # 2. Supprimer l'ancien environnement
        if manager.check_conda_env_exists(env_name):
            logger.info(f"Suppression de l'environnement existant '{env_name}'...")
            subprocess.run([conda_exe, 'env', 'remove', '-n', env_name, '--y'], check=True)
            logger.success(f"Environnement '{env_name}' supprimé.")
        else:
            logger.info(f"L'environnement '{env_name}' n'existe pas, pas besoin de le supprimer.")

        # 3. Recréer l'environnement
        logger.info(f"Création du nouvel environnement '{env_name}' avec Python 3.10...")
        subprocess.run([conda_exe, 'create', '-n', env_name, 'python=3.10', '--y'], check=True)

        # 4. Installer les dépendances de base
        logger.info("Installation des dépendances depuis argumentation_analysis/requirements.txt...")
        requirements_path = manager.project_root / 'argumentation_analysis' / 'requirements.txt'
        if not requirements_path.exists():
            logger.critical(f"Le fichier de dépendances n'a pas été trouvé: {requirements_path}")
            safe_exit(1, logger)

        # Utiliser la méthode run_in_conda_env pour garantir le bon contexte
        pip_install_command = [
            'pip', 'install',
            '--no-cache-dir', # Ne pas utiliser de cache potentiellement corrompu
            '--force-reinstall', # Forcer la réécriture des paquets
            '-r', str(requirements_path)
        ]
        # On ne capture plus la sortie ici, on veut la voir en direct
        result = manager.run_in_conda_env(pip_install_command, env_name=env_name)
        
        if result.returncode != 0:
            logger.error(f"Échec de l'installation des dépendances depuis {requirements_path}. Voir logs ci-dessus.")
            # Les sorties sont déjà logguées en temps réel par run_in_conda_env
            safe_exit(1, logger)
        
        logger.success("Dépendances installées (selon pip).")
        
        # Pause de 2 secondes pour s'assurer que le système de fichiers est synchronisé
        import time
        logger.info("Pause de 2 secondes avant la vérification...")
        time.sleep(2)
        
        logger.info("Vérification de l'import de JPype1 post-installation...")
        verify_cmd = "import jpype1; print('JPype1 importé avec succès dans le manager')"
        # On ne capture plus la sortie ici non plus
        verify_result = manager.run_in_conda_env(['python', '-c', verify_cmd], env_name=env_name)

        if verify_result.returncode != 0:
            logger.critical("Échec de la vérification de l'import de JPype1. L'environnement est potentiellement corrompu.")
            logger.error(f"Trace de la vérification (stderr):\n{verify_result.stderr}")
            safe_exit(1, logger)
        
        logger.success(f"Vérification de l'import JPype1 réussie:\n{verify_result.stdout.strip()}")
        logger.success(f"Environnement '{env_name}' recréé et initialisé avec succès.")
        safe_exit(0, logger)

    elif args.check_only:
        # Mode vérification uniquement
        logger.info("Vérification de l'environnement...")
        
        if manager.check_conda_available():
            logger.success("Conda disponible")
        else:
            logger.error("Conda non disponible")
            safe_exit(1, logger)
        
        if manager.check_conda_env_exists(args.env_name):
            logger.success(f"Environnement '{args.env_name}' trouvé")
        else:
            logger.error(f"Environnement '{args.env_name}' non trouvé")
            safe_exit(1, logger)
        
        if manager.check_python_version():
            logger.success("Version Python valide")
        else:
            logger.error("Version Python invalide")
            safe_exit(1, logger)
        
        logger.success("Environnement validé")
        safe_exit(0, logger)
    
    else:
        # Mode activation et exécution
        logger.info(f"DEBUG: Valeur passée comme command_to_run: {command_to_run_final}")
        exit_code = manager.activate_project_environment(
            command_to_run=command_to_run_final,
            env_name=args.env_name
        )
        safe_exit(exit_code, logger)


if __name__ == "__main__":
    main()