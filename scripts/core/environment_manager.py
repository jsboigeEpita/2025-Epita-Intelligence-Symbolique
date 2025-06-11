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
from typing import Dict, List, Optional, Tuple, Any
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
        self.project_root = get_project_root()
        # Le chargement initial de .env (y compris la découverte/persistance de CONDA_PATH)
        # est maintenant géré au début de la méthode auto_activate_env.
        # L'appel à _load_dotenv_intelligent ici est donc redondant et supprimé.
        
        # Assurer que JAVA_HOME est absolu s'il vient du .env
        # Cette logique reste pertinente si JAVA_HOME est défini par un .env chargé par auto_activate_env.
        if 'JAVA_HOME' in os.environ: # Vérifier si JAVA_HOME a été chargé
            java_home_value = os.environ['JAVA_HOME']
            java_home_path = Path(java_home_value)
            if not java_home_path.is_absolute():
                # Le chemin dans .env est relatif à la racine du projet
                absolute_java_home = (Path(self.project_root) / java_home_path).resolve()
                if absolute_java_home.exists() and absolute_java_home.is_dir():
                    os.environ['JAVA_HOME'] = str(absolute_java_home)
                    self.logger.info(f"JAVA_HOME (de .env) mis à jour en chemin absolu: {os.environ['JAVA_HOME']}")
                else:
                    self.logger.warning(f"Le chemin JAVA_HOME (de .env) résolu {absolute_java_home} n'existe pas ou n'est pas un répertoire.")
            # else: JAVA_HOME est déjà absolu ou n'a pas besoin d'être modifié par ce bloc
        
        self.default_conda_env = "projet-is"
        self.required_python_version = (3, 8)
        
        # Variables d'environnement importantes
        self.env_vars = {
            'PYTHONIOENCODING': 'utf-8',
            'PYTHONPATH': self.project_root,
            'PROJECT_ROOT': self.project_root
        }
    
    def check_conda_available(self) -> bool:
        """Vérifie si conda est disponible"""
        try:
            # Nouvelle tentative : utiliser shell=True pour que le shell résolve conda via le PATH mis à jour.
            # C'est pour 'conda --version' uniquement, donc le risque de sécurité est minime.
            self.logger.debug("Tentative de vérification de Conda avec shell=True...")
            result = subprocess.run(
                'conda --version', # Commande en chaîne de caractères pour shell=True
                shell=True,
                capture_output=True,
                text=True,
                timeout=10,
                executable=shutil.which('powershell') if platform.system() == "Windows" else None # Spécifier le shell si Windows
            )
            if result.returncode == 0 and "conda" in result.stdout.lower():
                self.logger.debug(f"Conda trouvé (via shell=True): {result.stdout.strip()}")
                return True
            else:
                self.logger.warning(f"Commande 'conda --version' (shell=True) a échoué ou n'a pas retourné 'conda'. Code: {result.returncode}. Output: {result.stdout.strip()} Stderr: {result.stderr.strip()}")

        except (subprocess.SubprocessError, subprocess.TimeoutExpired) as e:
            self.logger.warning(f"Erreur lors de la vérification de Conda (shell=True): {e}")
            pass # L'échec est géré ci-dessous
        
        self.logger.warning("Conda non disponible (après tentative avec shell=True)")
        return False
    
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
        if not self.check_conda_available():
            return []
        
        try:
            # CORRECTION: Utiliser shell=True comme dans check_conda_available()
            result = subprocess.run(
                'conda env list --json',
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                executable=shutil.which('powershell') if platform.system() == "Windows" else None
            )
            
            if result.returncode == 0:
                # import json # Supprimé car importé au niveau supérieur
                data = json.loads(result.stdout)
                envs = []
                for env_path in data.get('envs', []):
                    env_name = Path(env_path).name
                    envs.append(env_name)
                return envs
        
        except (subprocess.SubprocessError, json.JSONDecodeError, subprocess.TimeoutExpired):
            self.logger.debug("Erreur lors de la liste des environnements conda")
        
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
    
    def run_in_conda_env(self, command: List[str], env_name: str = None, 
                        cwd: str = None, capture_output: bool = False) -> subprocess.CompletedProcess:
        """
        Exécute une commande dans un environnement conda
        
        Args:
            command: Commande à exécuter (liste de strings)
            env_name: Nom de l'environnement conda (défaut: projet-is)
            cwd: Répertoire de travail (défaut: project_root)
            capture_output: Capturer la sortie au lieu de l'afficher
        
        Returns:
            Résultat de l'exécution
        """
        if env_name is None:
            env_name = self.default_conda_env
        
        if cwd is None:
            cwd = self.project_root
        
        # Vérifier que l'environnement existe
        if not self.check_conda_env_exists(env_name):
            self.logger.error(f"Environnement conda '{env_name}' non trouvé")
            raise RuntimeError(f"Environnement conda '{env_name}' non disponible")

        # Si 'command' est une liste, la joindre. Si c'est une chaîne, la garder.
        # Cela est pour préparer l'exécution via un shell si nécessaire.
        if isinstance(command, list):
            command_str_for_shell = ' '.join(command)
        else: # Devrait déjà être une chaîne si on passe par activate_project_environment avec une chaîne de commandes
            command_str_for_shell = command

        # Construire la commande conda run pour exécuter la chaîne de commandes via le shell par défaut de l'OS
        # Sur Windows, cmd.exe est souvent le shell par défaut pour conda run, qui gère les ';'
        # Pour forcer PowerShell (plus robuste pour les scripts complexes) :
        # conda_cmd = ['conda', 'run', '-n', env_name, '--no-capture-output', 'powershell', '-Command', command_str_for_shell]
        # Pour l'instant, on laisse conda run utiliser son shell par défaut, qui devrait gérer les ';' sur Windows.
        # Si la commande est simple (une seule commande logique), on peut l'exécuter directement.
        # Si elle contient ';', elle est probablement destinée à un shell.
        if ';' in command_str_for_shell or '&' in command_str_for_shell or '|' in command_str_for_shell:
             # Sur Windows, cmd.exe est souvent le shell par défaut pour conda run.
             # Pour s'assurer que les commandes multiples fonctionnent, on peut les passer à 'cmd /c'
             # ou 'powershell -Command'. 'cmd /c' est plus simple pour les points-virgules.
            if os.name == 'nt':
                conda_cmd = ['conda', 'run', '-n', env_name, '--no-capture-output', 'cmd', '/c', command_str_for_shell]
                self.logger.info(f"DEBUG: Commande conda (via cmd /c) construite: {' '.join(conda_cmd)}")
            else: # Pour Unix, bash est typique
                conda_cmd = ['conda', 'run', '-n', env_name, '--no-capture-output', 'bash', '-c', command_str_for_shell]
                self.logger.info(f"DEBUG: Commande conda (via bash -c) construite: {' '.join(conda_cmd)}")
        else:
            # Si c'est une commande simple (pas de ';', '&', '|'), on la passe comme avant (liste d'arguments)
            # `command` doit être une liste ici. Si c'était une chaîne simple, elle devient une liste d'un élément.
            final_command_parts = command_str_for_shell.split()
            conda_cmd = ['conda', 'run', '-n', env_name, '--no-capture-output'] + final_command_parts
            self.logger.info(f"DEBUG: Commande conda (directe) construite: {' '.join(conda_cmd)}")
        
        self.logger.debug(f"Exécution dans conda '{env_name}': {command_str_for_shell}")
        
        try:
            if capture_output:
                result = subprocess.run(
                    conda_cmd,
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minutes par défaut
                )
            else:
                result = subprocess.run(
                    conda_cmd,
                    cwd=cwd,
                    timeout=300
                )
            
            if result.returncode == 0:
                self.logger.debug("Commande exécutée avec succès")
            else:
                self.logger.warning(f"Commande terminée avec code: {result.returncode}")
            
            return result
        
        except subprocess.TimeoutExpired:
            self.logger.error("Timeout lors de l'exécution de la commande")
            raise
        except subprocess.SubprocessError as e:
            self.logger.error(f"Erreur lors de l'exécution: {e}")
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
    One-liner auto-activateur d'environnement intelligent
    
    Active véritablement l'environnement conda en modifiant le PATH et les variables.
    
    Args:
        env_name: Nom de l'environnement conda
        silent: Mode silencieux (pas de logs verbeux)
    
    Returns:
        True si environnement actif/activé, False sinon
    """
    try:
        # Logger minimal pour auto-activation
        # Note: La création d'une nouvelle instance de EnvironmentManager ici peut être problématique
        # si auto_activate_env est appelée sur une instance existante.
        # Pour l'instant, on garde la logique originale de auto_env.py qui crée son propre manager.
        logger = Logger(verbose=not silent)
        manager = EnvironmentManager(logger) # Crée une instance, __init__ sera appelé.

        # --- Début des modifications pour la refactorisation ---
        # 1. S'assurer que CONDA_PATH est dans .env et chargé dans os.environ, et que le PATH système de base est correct
        # self.project_root est disponible via manager.project_root
        # Note: manager._discover_and_persist_conda_path_in_env_file va appeler load_dotenv si .env est modifié.
        manager._discover_and_persist_conda_path_in_env_file(Path(manager.project_root), silent)
        
        # 2. Mettre à jour le PATH système à partir de CONDA_PATH (qui devrait être dans os.environ maintenant)
        manager._update_system_path_from_conda_env_var(silent)
        # --- Fin des modifications pour la refactorisation ---
        
        # Vérifier si conda et l'environnement existent
        # manager.check_conda_available() devrait maintenant mieux fonctionner car le PATH a été mis à jour.
        if not manager.check_conda_available():
            if not silent:
                print(f"[ERROR] Conda non disponible - impossible d'activer '{env_name}'")
            return False
        
        if not manager.check_conda_env_exists(env_name):
            if not silent:
                print(f"[ERROR] Environnement '{env_name}' non trouve")
            return False
        
        # Obtenir le chemin de l'environnement conda
        try:
            # Utiliser la méthode corrigée avec shell=True + PowerShell comme dans list_conda_environments
            cmd_env_path = f'$env:PATH = "{os.environ.get("CONDA_PATH", "")};$env:PATH"; conda info --envs --json'
            if not silent:
                print(f"[DEBUG] Exécution: {cmd_env_path}")
            
            result = subprocess.run(
                f'powershell -c "{cmd_env_path}"',
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # import json # Supprimé car importé au niveau supérieur
                env_data = json.loads(result.stdout)
                env_path = None
                
                for env_dir in env_data.get('envs', []):
                    if Path(env_dir).name == env_name:
                        env_path = env_dir
                        break
                
                if env_path:
                    # Activer vraiment l'environnement en modifiant le PATH
                    env_bin_path = os.path.join(env_path, 'Scripts')  # Windows
                    if not os.path.exists(env_bin_path):
                        env_bin_path = os.path.join(env_path, 'bin')  # Unix
                    
                    if os.path.exists(env_bin_path):
                        # Mettre le chemin de l'environnement en premier dans le PATH
                        current_path = os.environ.get('PATH', '')
                        path_parts = current_path.split(os.pathsep)
                        
                        # Retirer les anciens chemins conda s'ils existent
                        path_parts = [p for p in path_parts if not ('conda' in p.lower() and 'envs' in p.lower())]
                        
                        # Ajouter le nouveau chemin en premier
                        path_parts.insert(0, env_bin_path)
                        os.environ['PATH'] = os.pathsep.join(path_parts)
                        
                        # Configurer les variables d'environnement conda
                        os.environ['CONDA_DEFAULT_ENV'] = env_name
                        os.environ['CONDA_PREFIX'] = env_path
                        
                        if not silent:
                            print(f"[INFO] Auto-activation de l'environnement '{env_name}'...")
                            print(f"[CONDA] PATH mis à jour: {env_bin_path}")
                        
                        # Configurer les variables d'environnement du projet
                        manager.setup_environment_variables()
                        
                        if not silent:
                            print(f"[OK] Environnement '{env_name}' auto-actif")
                        
                        return True
                    else:
                        if not silent:
                            print(f"[ERROR] Répertoire bin/Scripts non trouvé: {env_bin_path}")
                        return False
                else:
                    if not silent:
                        print(f"[ERROR] Chemin de l'environnement '{env_name}' non trouvé")
                    return False
            else:
                if not silent:
                    print(f"[ERROR] Impossible d'obtenir les infos conda: {result.stderr}")
                return False
                
        except Exception as e:
            if not silent:
                print(f"[ERROR] Erreur lors de l'obtention du chemin conda: {e}")
            return False
        
    except Exception as e:
        if not silent:
            print(f"❌ Erreur auto-activation: {e}")
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
        '--command', '-c', # Option nommée, attendue par activate_project_env.ps1 (version lue)
        type=str,
        default=None,
        help='Commande à exécuter dans l\'environnement (optionnel)'
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
    
    args = parser.parse_args() 
    
    logger = Logger(verbose=True) # FORCER VERBOSE POUR DEBUG (ou utiliser args.verbose)
    logger.info("DEBUG: Début de main() dans environment_manager.py (après parsing)")
    logger.info(f"DEBUG: Args parsés par argparse: {args}")
    
    manager = EnvironmentManager(logger)
    
    command_to_run_final = args.command 

    if args.check_only:
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