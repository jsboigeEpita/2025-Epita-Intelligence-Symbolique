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

# --- Début du bloc d'auto-amorçage ---
# Ce bloc vérifie les dépendances minimales requises pour que ce script fonctionne
# et les installe si elles sont manquantes. C'est crucial car ce script peut
# être appelé par un interpréteur Python qui n'est pas encore dans un environnement conda.
try:
    import pip
except ImportError:
    print("ERREUR CRITIQUE: pip n'est pas disponible. Impossible de continuer.", file=sys.stderr)
    sys.exit(1)

def _bootstrap_dependency(package_name, import_name=None):
    if import_name is None:
        import_name = package_name
    try:
        __import__(import_name)
    except ImportError:
        print(f"INFO: Le module '{import_name}' est manquant. Tentative d'installation via pip...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package_name])
            print(f"INFO: Le paquet '{package_name}' a été installé avec succès.")
        except subprocess.CalledProcessError as e:
            print(f"ERREUR: Impossible d'installer '{package_name}'. Code de sortie: {e.returncode}", file=sys.stderr)
            sys.exit(1)

_bootstrap_dependency('python-dotenv', 'dotenv')
_bootstrap_dependency('PyYAML', 'yaml')
_bootstrap_dependency('requests')
_bootstrap_dependency('psutil')
# --- Fin du bloc d'auto-amorçage ---

from enum import Enum, auto
from typing import Dict, List, Optional, Tuple, Any, Union
from pathlib import Path
import shutil # Ajout pour shutil.which
import platform # Ajout pour la détection OS-spécifique des chemins communs
import tempfile # Ajout pour le script de diagnostic
from dotenv import load_dotenv, find_dotenv # Ajout pour la gestion .env

# --- Correction dynamique du sys.path pour l'exécution directe ---
# Permet au script de trouver le module 'project_core' même lorsqu'il est appelé directement.
# Cela est crucial car le script s'auto-invoque depuis des contextes où la racine du projet n'est pas dans PYTHONPATH.
try:
    _project_root = Path(__file__).resolve().parent.parent.parent
    if str(_project_root) not in sys.path:
        sys.path.insert(0, str(_project_root))
except NameError:
    # __file__ n'est pas défini dans certains contextes (ex: interpréteur interactif), gestion simple.
    _project_root = Path(os.getcwd())
    if str(_project_root) not in sys.path:
         sys.path.insert(0, str(_project_root))


class ReinstallComponent(Enum):
    """Énumération des composants pouvant être réinstallés."""
    # Utilise str pour que argparse puisse directement utiliser les noms
    def _generate_next_value_(name, start, count, last_values):
        return name.lower()

    ALL = auto()
    CONDA = auto()
    JAVA = auto()
    # OCTAVE = auto() # Placeholder pour le futur
    # TWEETY = auto() # Placeholder pour le futur

    def __str__(self):
        return self.value

# Import relatif corrigé - gestion des erreurs d'import
try:
    from .common_utils import Logger, LogLevel, safe_exit, get_project_root, ColoredOutput
except ImportError:
    # Fallback pour execution directe
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from common_utils import Logger, LogLevel, safe_exit, get_project_root, ColoredOutput


# Déclaration d'un logger global pour le module, en particulier pour les erreurs d'import au niveau du module
_module_logger = Logger(log_file_path="logs/environment_manager.log")

try:
    from argumentation_analysis.core.jvm_setup import download_tweety_jars
except ImportError:
    # Fallback pour execution directe
    _module_logger.warning("Could not import download_tweety_jars from argumentation_analysis.core.jvm_setup, Tweety JARs might not be downloaded if missing.")
    def download_tweety_jars(*args, **kwargs):
        _module_logger.error("download_tweety_jars is not available due to a critical import issue.")
        return False
# --- Début de l'insertion pour sys.path ---
# Déterminer la racine du projet (remonter de deux niveaux depuis scripts/core)
# __file__ est scripts/core/auto_env.py
# .parent est scripts/core
# .parent.parent est scripts
# .parent.parent.parent est la racine du projet
# _project_root_for_sys_path = Path(__file__).resolve().parent.parent.parent
# if str(_project_root_for_sys_path) not in sys.path:
#     sys.path.insert(0, str(_project_root_for_sys_path))
# --- Fin de l'insertion pour sys.path ---
# from argumentation_analysis.core.environment import _load_dotenv_intelligent # MODIFIÉ ICI - Sera supprimé
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

        # Chargement prioritaire du .env pour récupérer le nom de l'environnement
        dotenv_path = self.project_root / ".env"
        if dotenv_path.is_file():
            self.logger.debug(f"Chargement initial du .env depuis : {dotenv_path}")
            load_dotenv(dotenv_path, override=True)
        
        # Le code pour rendre JAVA_HOME absolu est déplacé vers la méthode activate_project_environment
        # pour s'assurer qu'il s'exécute APRÈS le chargement du fichier .env.
        
        # Priorité : Variable d'environnement > 'projet-is' par défaut
        self.default_conda_env = os.environ.get('CONDA_ENV_NAME', "projet-is")
        self.logger.info(f"Nom de l'environnement Conda par défaut utilisé : '{self.default_conda_env}'")

        self.required_python_version = (3, 8)
        
        # Variables d'environnement importantes
        # On construit le PYTHONPATH en ajoutant la racine du projet au PYTHONPATH existant
        # pour ne pas écraser les chemins qui pourraient être nécessaires (ex: par VSCode pour les tests)
        project_path_str = str(self.project_root)
        existing_pythonpath = os.environ.get('PYTHONPATH', '')
        
        path_components = existing_pythonpath.split(os.pathsep) if existing_pythonpath else []
        if project_path_str not in path_components:
            # On insère la racine du projet au début pour prioriser les modules locaux
            path_components.insert(0, project_path_str)
        
        new_pythonpath = os.pathsep.join(path_components)

        self.env_vars = {
            'PYTHONIOENCODING': 'utf-8',
            'PYTHONPATH': new_pythonpath,
            'PROJECT_ROOT': project_path_str
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
        """Vérifie si un environnement conda existe en cherchant son chemin."""
        env_path = self._get_conda_env_path(env_name)
        if env_path:
            self.logger.debug(f"Environnement conda '{env_name}' trouvé à l'emplacement : {env_path}")
            return True
        else:
            self.logger.warning(f"Environnement conda '{env_name}' non trouvé parmi les environnements existants.")
            return False
    
    def setup_environment_variables(self, additional_vars: Dict[str, str] = None):
        """Configure les variables d'environnement pour le projet"""
        env_vars = self.env_vars.copy()
        if additional_vars:
            env_vars.update(additional_vars)
        
        for key, value in env_vars.items():
            os.environ[key] = value
            self.logger.debug(f"Variable d'environnement définie: {key}={value}")
        
        # RUSTINE DE DERNIER RECOURS - Commenté car c'est une mauvaise pratique
        # # Ajouter manuellement le `site-packages` de l'environnement au PYTHONPATH.
        # conda_prefix = os.environ.get("CONDA_PREFIX")
        # if conda_prefix and "projet-is" in conda_prefix:
        #     site_packages_path = os.path.join(conda_prefix, "lib", "site-packages")
        #     python_path = os.environ.get("PYTHONPATH", "")
        #     if site_packages_path not in python_path:
        #         os.environ["PYTHONPATH"] = f"{site_packages_path}{os.pathsep}{python_path}"
        #         self.logger.warning(f"RUSTINE: Ajout forcé de {site_packages_path} au PYTHONPATH.")
    
    def _get_conda_env_path(self, env_name: str) -> Optional[str]:
        """Récupère le chemin complet d'un environnement conda par son nom."""
        conda_exe = self._find_conda_executable()
        if not conda_exe: return None
        
        try:
            cmd = [conda_exe, 'env', 'list', '--json']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, encoding='utf-8')
            if result.returncode == 0:
                # Nettoyage de la sortie pour ne garder que le JSON
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

                for env_path in data.get('envs', []):
                    if Path(env_path).name == env_name:
                        self.logger.debug(f"Chemin trouvé pour '{env_name}': {env_path}")
                        return env_path
            else:
                 self.logger.warning(f"La commande 'conda env list --json' a échoué. Stderr: {result.stderr}")

            return None
        except (subprocess.SubprocessError, json.JSONDecodeError, subprocess.TimeoutExpired) as e:
            self.logger.error(f"Erreur lors de la recherche du chemin de l'environnement '{env_name}': {e}")
            return None

    def build_final_command(self, command: Union[str, List[str]], env_name: str = None) -> List[str]:
        """
        Construit la liste de commande finale à exécuter, sans l'exécuter.
        Contient la logique pour choisir entre l'exécution directe de Python et 'conda run'.
        """
        if env_name is None:
            env_name = self.default_conda_env

        conda_exe = self._find_conda_executable()
        if not conda_exe:
            raise RuntimeError("Exécutable Conda non trouvé pour construire la commande.")

        env_path = self._get_conda_env_path(env_name)
        if not env_path:
            raise RuntimeError(f"Chemin pour l'environnement conda '{env_name}' introuvable.")

        import shlex
        is_complex = isinstance(command, str) and any(op in command for op in [';', '&&', '|'])
        
        cmd_list = shlex.split(command, posix=(os.name != 'nt')) if isinstance(command, str) else command
        is_python_direct = cmd_list and cmd_list[0].lower() == 'python'

        if is_python_direct:
            python_exe_path = Path(env_path) / ('python.exe' if platform.system() == "Windows" else 'bin/python')
            if not python_exe_path.is_file():
                # Fallback for windows store python or other weird installs
                python_exe_path = Path(env_path) / 'Scripts' / 'python.exe' if platform.system() == "Windows" else python_exe_path
            
            if not python_exe_path.is_file():
                 raise RuntimeError(f"Exécutable Python introuvable dans '{env_path}'.")
            
            return [str(python_exe_path)] + cmd_list[1:]

        if is_complex:
            shell_cmd = ['cmd.exe', '/c'] if platform.system() == "Windows" else ['bash', '-c']
            return [conda_exe, 'run', '--prefix', env_path, '--no-capture-output'] + shell_cmd + [command]
        
        # Standard command
        return [conda_exe, 'run', '--prefix', env_path, '--no-capture-output'] + cmd_list

    def run_in_conda_env(self, command: Union[str, List[str]], env_name: str = None,
                         cwd: str = None, capture_output: bool = False) -> subprocess.CompletedProcess:
        """Exécute une commande dans un environnement conda de manière robuste."""
        if env_name is None: env_name = self.default_conda_env
        if cwd is None: cwd = str(self.project_root)

        final_command = self.build_final_command(command, env_name)
        self.logger.info(f"Commande finale à exécuter: {' '.join(final_command)}")

        # Préparation de l'environnement
        env_path = self._get_conda_env_path(env_name)
        sub_process_env = os.environ.copy()
        sub_process_env['CONDA_DEFAULT_ENV'] = env_name
        sub_process_env['CONDA_PREFIX'] = env_path
        # S'assurer que le PATH de l'environnement cible est prioritaire
        sub_process_env['PATH'] = f"{env_scripts_dir}{os.pathsep}{os.environ.get('PATH', '')}"
        
        # --- CORRECTIF : Propagation du PYTHONPATH ---
        # Le PYTHONPATH a été défini dans self.env_vars mais n'était pas propagé
        # au sous-processus. On le récupère depuis self.env_vars (qui a la bonne valeur)
        # et on le force dans l'environnement du sous-processus.
        if 'PYTHONPATH' in self.env_vars:
            sub_process_env['PYTHONPATH'] = self.env_vars['PYTHONPATH']
            self.logger.info(f"Propagation du PYTHONPATH au sous-processus: {sub_process_env['PYTHONPATH']}")
        
        # --- CORRECTIF CRUCIAL : Propagation de JAVA_HOME ---
        # S'assure que la variable JAVA_HOME, validée par activate_project_environment,
        # est bien transmise au sous-processus final qui exécute les tests.
        if 'JAVA_HOME' in os.environ:
            sub_process_env['JAVA_HOME'] = os.environ['JAVA_HOME']
            self.logger.info(f"Propagation de JAVA_HOME au sous-processus: {sub_process_env['JAVA_HOME']}")

        # --- CORRECTIF OMP: Error #15 ---
        # Force la variable d'environnement pour éviter les conflits de librairies OpenMP
        # (souvent entre la version de PyTorch et celle de scikit-learn/numpy).
        # sub_process_env['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
        # self.logger.info("Injection de KMP_DUPLICATE_LIB_OK=TRUE pour éviter les erreurs OMP.")

        self.logger.info(f"Variables d'environnement préparées pour le sous-processus (extrait): "
                         f"CONDA_DEFAULT_ENV={sub_process_env.get('CONDA_DEFAULT_ENV')}, "
                         f"CONDA_PREFIX={sub_process_env.get('CONDA_PREFIX')}, "
                         f"PATH starts with: {sub_process_env.get('PATH', '')[:100]}...")
       
        # --- INJECTION DE LA VARIABLE DE COURT-CIRCUIT ---
        # Indique aux sous-processus (comme auto_env.py) que l'environnement est déjà géré.
        sub_process_env['RUNNING_VIA_ENV_MANAGER'] = 'true'
        self.logger.info("Injection de RUNNING_VIA_ENV_MANAGER=true pour court-circuiter la double activation.")
        
        # Cette logique de `is_complex_string_command` a été déplacée plus haut,
        # dans la méthode `build_final_command`. Ici, on ne devrait plus avoir à
        # la gérer. `final_command` est déjà la liste d'arguments prête à l'emploi.
        # On peut simplifier cette section.

        # La variable "is_complex_string_command" n'est plus disponible dans ce scope.
        # La logique a été déplacée et centralisée dans `build_final_command`.
        # Par conséquent, je supprime tout le bloc `if is_complex_string_command / else`.
        # `final_command` est déjà correctement formatée par `build_final_command`.

        try:
            return subprocess.run(
                final_command, cwd=cwd, capture_output=capture_output, text=True,
                encoding='utf-8', errors='replace', check=False, timeout=3600,
                env=sub_process_env
            )
        except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
            self.logger.error(f"Erreur majeure lors de l'exécution de la commande: {e}")
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
        
        self.logger.info(f"Activation de l'environnement '{env_name}' (déterminé par .env ou défaut)...")

        # --- BLOC D'ACTIVATION UNIFIÉ ---
        self.logger.info("Début du bloc d'activation unifié...")

        # 1. Charger le fichier .env de base (depuis le bon répertoire de projet) de manière robuste
        dotenv_path = self.project_root / ".env"
        if dotenv_path.is_file():
            self.logger.info(f"Fichier .env trouvé et chargé depuis : {dotenv_path}")
            load_dotenv(dotenv_path, override=True)
        else:
            self.logger.info(f"Aucun fichier .env trouvé à {dotenv_path}, il sera créé si nécessaire.")

        # 2. Découvrir et persister CONDA_PATH dans le .env si nécessaire
        # Cette méthode met à jour le fichier .env et recharge les variables dans os.environ
        # Elle ne sera plus destructive car elle est appelée après un chargement fiable.
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
                    self.logger.warning(f"Le chemin JAVA_HOME '{absolute_java_home}' est invalide. Tentative d'auto-installation...")
                    try:
                        from project_core.environment.tool_installer import ensure_tools_are_installed
                        ensure_tools_are_installed(tools_to_ensure=['jdk'], logger_instance=self.logger)
                    except ImportError as ie:
                        self.logger.error(f"Échec de l'import de 'tool_installer' pour l'auto-installation de JAVA: {ie}")
                    except Exception as e:
                        self.logger.error(f"Une erreur est survenue durant l'auto-installation du JDK: {e}")
        
        # **CORRECTION DE ROBUSTESSE POUR JPYPE**
        # S'assurer que le répertoire bin de la JVM est dans le PATH
        if 'JAVA_HOME' in os.environ:
            java_bin_path = Path(os.environ['JAVA_HOME']) / 'bin'
            if java_bin_path.is_dir():
                if str(java_bin_path) not in os.environ['PATH']:
                    os.environ['PATH'] = f"{java_bin_path}{os.pathsep}{os.environ['PATH']}"
                    self.logger.info(f"Ajouté {java_bin_path} au PATH pour la JVM.")
        
        # --- BLOC D'AUTO-INSTALLATION NODE.JS ---
        if 'NODE_HOME' not in os.environ or not Path(os.environ.get('NODE_HOME', '')).is_dir():
             self.logger.warning("NODE_HOME non défini ou invalide. Tentative d'auto-installation...")
             try:
                 from project_core.environment.tool_installer import ensure_tools_are_installed
                 ensure_tools_are_installed(tools_to_ensure=['node'], logger_instance=self.logger)
             except ImportError as ie:
                 self.logger.error(f"Échec de l'import de 'tool_installer' pour l'auto-installation de Node.js: {ie}")
             except Exception as e:
                 self.logger.error(f"Une erreur est survenue durant l'auto-installation de Node.js: {e}")


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
                result = self.run_in_conda_env(command_to_run, env_name=env_name)
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
            updates = {"CONDA_PATH": f'"{conda_path_to_write}"'}
            
            try:
                self._update_env_file_safely(env_file, updates, silent)
                
                # Recharger .env pour que os.environ soit mis à jour
                load_dotenv(env_file, override=True)
                if not silent: self.logger.info(f"[.ENV] Variables rechargées depuis {env_file}")

                # Valider que la variable est bien dans l'environnement
                if 'CONDA_PATH' in os.environ:
                    return True
                else:
                    if not silent: self.logger.warning("[.ENV] CONDA_PATH n'a pas pu être chargé dans l'environnement après la mise à jour.")
                    # Forcer au cas où, pour la session courante
                    os.environ['CONDA_PATH'] = conda_path_to_write
                    return True

            except Exception as e_write_env:
                if not silent: self.logger.warning(f"[.ENV] Échec de la mise à jour du fichier {env_file}: {e_write_env}")
                return False # Échec de la persistance
        else:
            if not silent: self.logger.info("[.ENV DISCOVERY] Impossible de découvrir automatiquement les chemins Conda.")
            return False # Pas de chemins découverts, CONDA_PATH n'est pas résolu par cette fonction

    # --- Fin des méthodes transférées ---

    def _update_env_file_safely(self, env_file_path: Path, updates: Dict[str, str], silent: bool = True):
        """
        Met à jour un fichier .env de manière sécurisée, en préservant les lignes existantes.
        
        Args:
            env_file_path: Chemin vers le fichier .env.
            updates: Dictionnaire des clés/valeurs à mettre à jour.
            silent: Si True, n'affiche pas les logs de succès.
        """
        lines = []
        keys_to_update = set(updates.keys())
        
        if env_file_path.exists():
            with open(env_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

        # Parcourir les lignes existantes pour mettre à jour les clés
        for i, line in enumerate(lines):
            stripped_line = line.strip()
            if not stripped_line or stripped_line.startswith('#'):
                continue
            
            if '=' in stripped_line:
                key = stripped_line.split('=', 1)[0].strip()
                if key in keys_to_update:
                    lines[i] = f"{key}={updates[key]}\n"
                    keys_to_update.remove(key) # Marquer comme traitée

        # Ajouter les nouvelles clés à la fin si elles n'existaient pas
        if keys_to_update:
            if lines and lines[-1].strip() != '':
                 lines.append('\n') # Assurer un retour à la ligne avant d'ajouter
            for key in keys_to_update:
                lines.append(f"{key}={updates[key]}\n")

        # Écrire le fichier mis à jour
        with open(env_file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        if not silent:
            self.logger.info(f"Fichier .env mis à jour en toute sécurité : {env_file_path}")


def is_conda_env_active(env_name: str = None) -> bool:
    """Vérifie si l'environnement conda spécifié est actuellement actif"""
    # Utilise le nom d'env du .env par défaut si `env_name` non fourni
    if env_name is None:
        load_dotenv(find_dotenv())
        env_name = os.environ.get('CONDA_ENV_NAME', 'projet-is')
    current_env = os.environ.get('CONDA_DEFAULT_ENV', '')
    return current_env == env_name


def check_conda_env(env_name: str = None, logger: Logger = None) -> bool:
    """Fonction utilitaire pour vérifier un environnement conda"""
    manager = EnvironmentManager(logger)
    # Si env_name est None, le manager utilisera la valeur par défaut chargée depuis .env
    return manager.check_conda_env_exists(env_name or manager.default_conda_env)


def auto_activate_env(env_name: str = None, silent: bool = True) -> bool:
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
                # Le nom de l'env est géré par le manager, on le récupère pour un log correct
                logger.success(f"Auto-activation de '{manager.default_conda_env}' réussie via le manager central.")
            else:
                logger.error(f"Échec de l'auto-activation de '{manager.default_conda_env}' via le manager central.")

        return is_success

    except Exception as e:
        if not silent:
            # Créer un logger temporaire si l'initialisation a échoué.
            temp_logger = Logger(verbose=True)
            temp_logger.error(f"❌ Erreur critique dans auto_activate_env: {e}")
        return False


def activate_project_env(command: str = None, env_name: str = None, logger: Logger = None) -> int:
    """Fonction utilitaire pour activer l'environnement projet"""
    manager = EnvironmentManager(logger)
    # Laisser `activate_project_environment` gérer la valeur par défaut si env_name est None
    return manager.activate_project_environment(command, env_name)



def reinstall_conda_environment(manager: 'EnvironmentManager', env_name: str, verbose_level: int = 0):
    """Supprime et recrée intégralement l'environnement conda à partir de environment.yml."""
    logger = manager.logger
    ColoredOutput.print_section(f"Réinstallation complète de l'environnement '{env_name}' à partir de environment.yml")

    # --- Stratégie d'utilisation de Mamba ---
    # 1. Tenter de trouver mamba. C'est le choix préféré pour sa vitesse.
    # 2. Si mamba n'est pas trouvé, se rabattre sur conda.
    installer_exe = shutil.which("mamba.exe") or shutil.which("mamba")
    installer_name = "mamba"

    if installer_exe:
        logger.info(f"🚀 Utilisation de Mamba pour une installation rapide : {installer_exe}")
    else:
        logger.info("Mamba non trouvé. Utilisation de l'exécutable Conda standard.")
        installer_exe = manager._find_conda_executable()
        installer_name = "conda"

    if not installer_exe:
        logger.critical(f"Impossible de trouver un exécutable ({installer_name} ou conda). La réinstallation ne peut pas continuer.")
        safe_exit(1, logger)

    env_file_path = manager.project_root / 'environment.yml'
    if not env_file_path.exists():
        logger.critical(f"Fichier d'environnement non trouvé : {env_file_path}")
        safe_exit(1, logger)

    logger.info(f"Lancement de la réinstallation depuis {env_file_path} avec {installer_name}...")
    
    # La commande est la même pour `conda env create` et `mamba env create`
    create_command = [
        installer_exe, 'env', 'create',
        '--file', str(env_file_path),
        '--name', env_name,
        '--yes' # Accepter automatiquement toutes les confirmations
    ]

    if installer_name == 'conda':
        create_command.append('--force')

    if verbose_level > 0 and installer_name == 'conda': # Mamba gère différemment la verbosité
        create_command.append(f"-{'v' * verbose_level}")
        logger.info(f"Niveau de verbosité Conda activé : {verbose_level}")

    try:
        # La sortie est directement affichée sur la console pour un retour en temps réel.
        result = subprocess.run(
            create_command,
            text=True,
            encoding='utf-8',
            errors='replace',
            check=False  # On gère le code de retour nous-mêmes
        )
        
        if result.returncode != 0:
            logger.error(f"Échec de la création de l'environnement avec {installer_name}. Le log ci-dessus devrait contenir les détails.")
            if installer_name == "conda":
                logger.warning("Conda peut être très lent. L'installation de 'mamba' (`conda install mamba -n base -c conda-forge`) est fortement recommandée.")
            safe_exit(1, logger)

    except (subprocess.SubprocessError, FileNotFoundError) as e:
        logger.critical(f"Une erreur majeure est survenue lors de l'exécution de la commande {installer_name} : {e}")
        safe_exit(1, logger)
    
    logger.success(f"Environnement '{env_name}' recréé avec succès depuis {env_file_path} en utilisant {installer_name}.")

    # S'assurer que les JARs de Tweety sont présents après la réinstallation
    tweety_libs_dir = manager.project_root / "libs" / "tweety"
    logger.info(f"Vérification des JARs Tweety dans : {tweety_libs_dir}")
    if not download_tweety_jars(target_dir=str(tweety_libs_dir)):
        logger.warning("Échec du téléchargement ou de la vérification des JARs Tweety. JPype pourrait échouer.")
    else:
        logger.success("Les JARs de Tweety sont présents ou ont été téléchargés.")

def recheck_java_environment(manager: 'EnvironmentManager'):
    """Revalide la configuration de l'environnement Java."""
    logger = manager.logger
    ColoredOutput.print_section("Validation de l'environnement JAVA")
    
    # Recharge .env pour être sûr d'avoir la dernière version (depuis le bon répertoire)
    dotenv_path = find_dotenv()
    if dotenv_path: load_dotenv(dotenv_path, override=True)

    # Cette logique est tirée de `activate_project_environment`
    if 'JAVA_HOME' in os.environ:
        logger.info(f"JAVA_HOME trouvé dans l'environnement: {os.environ['JAVA_HOME']}")
        java_home_value = os.environ['JAVA_HOME']
        abs_java_home = Path(os.environ['JAVA_HOME'])
        if not abs_java_home.is_absolute():
            abs_java_home = (manager.project_root / java_home_value).resolve()
        
        if abs_java_home.exists() and abs_java_home.is_dir():
            os.environ['JAVA_HOME'] = str(abs_java_home)
            logger.success(f"JAVA_HOME est valide et absolu: {abs_java_home}")

            java_bin_path = abs_java_home / 'bin'
            if java_bin_path.is_dir():
                logger.success(f"Répertoire bin de la JVM trouvé: {java_bin_path}")
                if str(java_bin_path) not in os.environ['PATH']:
                    os.environ['PATH'] = f"{java_bin_path}{os.pathsep}{os.environ['PATH']}"
                    logger.info(f"Ajouté {java_bin_path} au PATH.")
                else:
                    logger.info("Le répertoire bin de la JVM est déjà dans le PATH.")
            else:
                logger.warning(f"Le répertoire bin '{java_bin_path}' n'a pas été trouvé.")
        else:
            logger.error(f"Le chemin JAVA_HOME '{abs_java_home}' est invalide.")
    else:
        logger.error("La variable d'environnement JAVA_HOME n'est pas définie.")


def main():
    """Point d'entrée principal pour utilisation en ligne de commande"""
    temp_logger = Logger(verbose=True)
    temp_logger.info(f"DEBUG: sys.argv au début de main(): {sys.argv}")

    parser = argparse.ArgumentParser(
        description="Gestionnaire d'environnements Python/conda"
    )
    
    parser.add_argument(
        '--command', '-c',
        type=str,
        help="Commande à exécuter, passée comme une chaîne unique."
    )
    
    parser.add_argument(
        '--env-name', '-e',
        type=str,
        default=None, # Le défaut sera géré par l'instance du manager
        help='Nom de l\'environnement conda (par défaut, utilise la valeur de CONDA_ENV_NAME dans .env)'
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
        '--reinstall',
        choices=[item.value for item in ReinstallComponent],
        nargs='+', # Accepte un ou plusieurs arguments
        help=f"Force la réinstallation de composants spécifiques. "
             f"Options: {[item.value for item in ReinstallComponent]}. "
             f"'all' réinstalle tout (équivaut à l'ancien --force-reinstall)."
    )
    
    parser.add_argument(
        '--conda-verbose-level',
        type=int,
        choices=[1, 2, 3],
        default=0,
        help="Niveau de verbosité pour les commandes conda (1 pour -v, 2 pour -vv, 3 pour -vvv)."
    )

    parser.add_argument(
        '--get-python-path',
        action='store_true',
        help="Affiche le chemin de l'exécutable Python de l'environnement Conda cible et quitte."
    )
    
    parser.add_argument(
        '--get-command-only',
        action='store_true',
        help="Construit la commande finale et l'affiche sur stdout sans l'exécuter."
    )
    
    parser.add_argument(
        '--output-command-file',
        type=str,
        help="Fichier où écrire la commande finale (au lieu de stdout)."
    )

    args = parser.parse_args()
    
    log_file = "logs/environment_manager.log"
    logger = Logger(verbose=args.verbose, log_file_path=log_file)
    logger.info("DEBUG: Début de main() dans auto_env.py (après parsing)")
    logger.info(f"DEBUG: Args parsés par argparse: {args}")
    
    manager = EnvironmentManager(logger)
    
    # --- NOUVELLE LOGIQUE D'EXÉCUTION ---

    # 0. Gérer --get-python-path (action prioritaire et terminale)
    if args.get_python_path:
        env_name_for_path = args.env_name or manager.default_conda_env
        env_path = manager._get_conda_env_path(env_name_for_path)
        if not env_path:
            logger.error(f"Impossible de trouver le chemin pour l'environnement '{env_name_for_path}'.")
            safe_exit(1, logger)
        
        python_exe_in_env = Path(env_path) / ('python.exe' if platform.system() == "Windows" else 'bin/python')
        if not python_exe_in_env.is_file():
            logger.error(f"Exécutable Python non trouvé à l'emplacement attendu: {python_exe_in_env}")
            safe_exit(1, logger)
        
        # Imprimer le chemin sur stdout pour que le script appelant puisse le récupérer
        print(str(python_exe_in_env))
        safe_exit(0, logger) # Terminer proprement


    # 1. Gérer la réinstallation si demandée.
    if args.reinstall:
        reinstall_choices = set(args.reinstall)
        # Priorité : argument CLI > .env/défaut du manager
        env_name = args.env_name or manager.default_conda_env
        
        # Si 'all' ou 'conda' est demandé, on réinstalle l'environnement Conda, ce qui inclut les paquets pip.
        if ReinstallComponent.ALL.value in reinstall_choices or ReinstallComponent.CONDA.value in reinstall_choices:
            reinstall_conda_environment(manager, env_name, verbose_level=args.conda_verbose_level)
        # Si seulement 'pip' est demandé, c'est maintenant géré par la reinstall de conda, mais on peut imaginer
        # une simple mise à jour dans le futur. Pour l'instant on ne fait rien de plus.
        # la logique ci-dessus suffit.
        
        # On vérifie si une autre action est nécessaire, comme la vérification Java
        if ReinstallComponent.JAVA.value in reinstall_choices:
             recheck_java_environment(manager)
                
        ColoredOutput.print_section("Vérification finale post-réinstallation")
        logger.info("Lancement du script de diagnostic complet via un fichier temporaire...")

        diagnostic_script_content = (
            "import sys, os, site, traceback\n"
            "print('--- Diagnostic Info from Conda Env ---')\n"
            "print(f'Python Executable: {sys.executable}')\n"
            "print(f'sys.path: {sys.path}')\n"
            "try:\n"
            "    site_packages_paths = site.getsitepackages()\n"
            "except AttributeError:\n"
            "    site_packages_paths = [p for p in sys.path if 'site-packages' in p]\n"
            "print(f'Site Packages Paths: {site_packages_paths}')\n"
            "found_jpype = False\n"
            "if site_packages_paths:\n"
            "    for sp_path in site_packages_paths:\n"
            "        jpype_dir = os.path.join(sp_path, 'jpype')\n"
            "        if os.path.isdir(jpype_dir):\n"
            "            print(f'  [SUCCESS] Found jpype directory: {jpype_dir}')\n"
            "            found_jpype = True\n"
            "            break\n"
            "if not found_jpype:\n"
            "    print('[FAILURE] jpype directory not found in any site-packages.')\n"
            "print('--- Attempting import ---')\n"
            "try:\n"
            "    import jpype\n"
            "    print('[SUCCESS] JPype1 (jpype) importé avec succès.')\n"
            "    sys.exit(0)\n"
            "except Exception as e:\n"
            "    traceback.print_exc()\n"
            "    print(f'[FAILURE] Échec de l\\'import JPype1 (jpype): {e}')\n"
            "    sys.exit(1)\n"
        )
        
        # Utiliser un fichier temporaire pour éviter les problèmes de ligne de commande et d'échappement
        temp_diag_file = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py', encoding='utf-8') as fp:
                temp_diag_file = fp.name
                fp.write(diagnostic_script_content)
            
            logger.debug(f"Script de diagnostic écrit dans {temp_diag_file}")
            verify_result = manager.run_in_conda_env(['python', temp_diag_file], env_name=env_name)

            if verify_result.returncode != 0:
                logger.critical("Échec du script de diagnostic. La sortie ci-dessus devrait indiquer la cause.")
                safe_exit(1, logger)

        finally:
            if temp_diag_file and os.path.exists(temp_diag_file):
                os.remove(temp_diag_file)
                logger.debug(f"Fichier de diagnostic temporaire {temp_diag_file} supprimé.")
        
        logger.success("Toutes les opérations de réinstallation et de vérification se sont terminées avec succès.")
        logger.success("Toutes les opérations de réinstallation et de vérification se sont terminées avec succès.")
        # Après une réinstallation, il est plus sûr de terminer ici.
        # Le script appelant (ex: setup_project_env.ps1) peut alors le ré-exécuter pour l'activation.
        safe_exit(0, logger)

    # 2. Gérer --check-only, qui est une action terminale.
    if args.check_only:
        logger.info("Vérification de l'environnement (mode --check-only)...")
        if not manager.check_conda_available():
            logger.error("Conda non disponible"); safe_exit(1, logger)
        logger.success("Conda disponible")
        if not manager.check_conda_env_exists(args.env_name or manager.default_conda_env):
            logger.error(f"Environnement '{args.env_name or manager.default_conda_env}' non trouvé"); safe_exit(1, logger)
        logger.success(f"Environnement '{args.env_name or manager.default_conda_env}' trouvé")
        logger.success("Environnement validé.")
        safe_exit(0, logger)

    # 3. Exécuter la commande (ou juste activer si aucune commande n'est fournie).
    command_to_run_final = args.command
        
    # --- AJOUT: TENTATIVE DE CRÉATION AUTOMATIQUE SI MANQUANT ---
    env_name_for_check = args.env_name or manager.default_conda_env
    if not manager.check_conda_env_exists(env_name_for_check):
        logger.warning(f"L'environnement '{env_name_for_check}' n'existe pas. Tentative de création automatique...")
        reinstall_conda_environment(manager, env_name_for_check, verbose_level=args.conda_verbose_level)
        logger.info("La création est terminée (succès ou échec). Le script va maintenant procéder à l'activation.")
    # --- FIN DE L'AJOUT ---

    # 4. Gérer --get-command-only si présent
    if args.get_command_only:
        if not command_to_run_final:
            logger.error("--get-command-only nécessite un --command.")
            safe_exit(1, logger)
        try:
            # S'assurer que les variables d'environnement sont à jour pour la session
            load_dotenv(find_dotenv(), override=True)
            manager._discover_and_persist_conda_path_in_env_file(manager.project_root, silent=True)
            manager._update_system_path_from_conda_env_var(silent=True)

            final_cmd_list = manager.build_final_command(command_to_run_final, env_name=env_name_for_check)
            # Important: Échapper correctement pour PowerShell/Invoke-Expression
            import shlex
            # Ne pas utiliser shlex.quote ici, car Invoke-Expression gère les arguments.
            # On retourne la liste d'arguments comme une chaîne, c'est PowerShell qui reconstruira.
            final_cmd_str = ' '.join(final_cmd_list)
            if args.output_command_file:
                try:
                    with open(args.output_command_file, 'w', encoding='utf-8') as f:
                        f.write(final_cmd_str)
                except IOError as e:
                    logger.error(f"Impossible d'écrire la commande dans le fichier {args.output_command_file}: {e}")
                    safe_exit(1, logger)
            else:
                print(final_cmd_str) # Écrit la commande sur stdout pour compatibilité
            
            safe_exit(0, logger)
        except Exception as e:
            logger.error(f"Erreur lors de la construction de la commande : {e}")
            safe_exit(1, logger)

    logger.info("Phase d'activation/exécution de commande...")
    exit_code = manager.activate_project_environment(
        command_to_run=command_to_run_final,
        env_name=args.env_name or manager.default_conda_env # Utiliser le nom CLI ou fallback sur .env
    )
    
    if command_to_run_final:
        logger.info(f"La commande a été exécutée avec le code de sortie: {exit_code}")
    else:
        logger.info("Activation de l'environnement terminée.")
        
    safe_exit(exit_code, logger)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Catch-all pour s'assurer que toute exception non gérée est loggée avant de quitter.
        import traceback
        import sys
        # Recréer un logger au cas où l'initialisation aurait échoué.
        logger = Logger(verbose=True)
        logger.critical(f"Exception non gérée interceptée au plus haut niveau : {e}")
        logger.critical(traceback.format_exc())
        sys.exit(99) # Quitter avec un code unique pour l'identification