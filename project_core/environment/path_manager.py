"""
Module pour la gestion des chemins et des variables d'environnement.

Ce module contient la logique pour :
- Gérer le fichier .env (lecture, écriture sécurisée).
- Découvrir et persister les chemins d'installation de Conda (CONDA_PATH).
- Mettre à jour le PATH système (os.environ['PATH']) et le sys.path.
- Valider et normaliser les variables d'environnement critiques comme JAVA_HOME.
"""

import os
import sys
import platform
import shutil
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv, find_dotenv

# --- Correction dynamique du sys.path ---
# S'assure que la racine du projet est dans sys.path pour les imports relatifs.
try:
    _project_root_path_obj = Path(__file__).resolve().parent.parent.parent
    if str(_project_root_path_obj) not in sys.path:
        sys.path.insert(0, str(_project_root_path_obj))
except NameError:
    _project_root_path_obj = Path(os.getcwd()) # Fallback si __file__ n'est pas défini
    if str(_project_root_path_obj) not in sys.path:
        sys.path.insert(0, str(_project_root_path_obj))

# Importation du logger depuis common_utils.
# S'il y a une erreur d'import, cela pourrait indiquer un problème de sys.path
# ou que le module n'est pas encore au bon endroit.
try:
    from project_core.common.common_utils import Logger as ActualLogger
    Logger = ActualLogger # Alias pour que le reste du fichier fonctionne
except ImportError:
    # Fallback simple si le logger n'est pas crucial pour les fonctions de ce module
    # ou si ce module est utilisé dans un contexte où le logger n'est pas configuré.
    class PrintLogger: # Défini comme classe locale
        def debug(self, msg): print(f"DEBUG: {msg}")
        def info(self, msg): print(f"INFO: {msg}")
        def warning(self, msg): print(f"WARNING: {msg}")
        def error(self, msg): print(f"ERROR: {msg}")
        def success(self, msg): print(f"SUCCESS: {msg}")
    
    # L'instance globale 'logger' sera de type PrintLogger si l'import échoue.
    logger_fallback_instance = PrintLogger()
    logger_fallback_instance.warning("project_core.common.common_utils.Logger non trouvé, utilisation d'un logger de secours PrintLogger.")
    Logger = PrintLogger # L'alias Logger pointe maintenant vers PrintLogger si l'import échoue


class PathManager:
    """
    Gère les chemins, les variables d'environnement et la configuration associée.
    """

    # L'annotation de type doit pouvoir accepter l'un ou l'autre.
    # Puisque Logger est maintenant un alias soit pour ActualLogger soit pour PrintLogger,
    # Optional[Logger] couvre les deux cas.
    def __init__(self, project_root: Path, logger_instance: Optional[Logger] = None):
        self.project_root = project_root
        # Si logger_instance est None, on utilise le logger global (qui peut être ActualLogger ou PrintLogger)
        self.logger = logger_instance if logger_instance is not None else (Logger() if callable(Logger) and not isinstance(Logger, PrintLogger) else logger_fallback_instance if 'logger_fallback_instance' in globals() else PrintLogger())

    def get_project_root(self) -> Path:
        """Retourne le chemin racine du projet."""
        return self.project_root

    def _update_env_file_safely(self, env_file_path: Path, updates: Dict[str, str], silent: bool = True):
        """
        Met à jour un fichier .env de manière sécurisée, en préservant les lignes existantes.
        """
        lines = []
        keys_to_update = set(updates.keys())

        if env_file_path.exists():
            with open(env_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

        for i, line in enumerate(lines):
            stripped_line = line.strip()
            if not stripped_line or stripped_line.startswith('#'):
                continue

            if '=' in stripped_line:
                key = stripped_line.split('=', 1)[0].strip()
                if key in keys_to_update:
                    lines[i] = f"{key}={updates[key]}\n"
                    keys_to_update.remove(key)

        if keys_to_update:
            if lines and lines[-1].strip() != '':
                 lines.append('\n')
            for key in keys_to_update:
                lines.append(f"{key}={updates[key]}\n")

        with open(env_file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        if not silent:
            self.logger.info(f"Fichier .env mis à jour en toute sécurité : {env_file_path}")

    def _discover_and_persist_conda_path_in_env_file(self, silent: bool = True) -> bool:
        """
        Tente de découvrir les chemins d'installation de Conda et, si CONDA_PATH
        n'est pas déjà dans os.environ (via .env initial), met à jour le fichier .env.
        Recharge ensuite os.environ depuis .env.
        Retourne True si CONDA_PATH est maintenant dans os.environ.
        """
        if os.environ.get('CONDA_PATH'):
            if not silent:
                self.logger.info("[.ENV DISCOVERY] CONDA_PATH déjà présent dans l'environnement.")
            return True

        if not silent:
            self.logger.info("[.ENV DISCOVERY] CONDA_PATH non trouvé. Tentative de découverte...")

        discovered_paths_collector: List[str] = []

        conda_exe_env_var = os.environ.get('CONDA_EXE')
        if conda_exe_env_var:
            conda_exe_file_path = Path(conda_exe_env_var)
            if conda_exe_file_path.is_file():
                if not silent: self.logger.debug(f"[.ENV DISCOVERY] CONDA_EXE trouvé: {conda_exe_file_path}")
                condabin_dir_path = conda_exe_file_path.parent
                scripts_dir_path = condabin_dir_path.parent / "Scripts" # Typique pour Windows
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
                    bin_dir_path = conda_root_dir_path / "bin" # Typique pour Unix
                    if condabin_dir_path.is_dir(): discovered_paths_collector.append(str(condabin_dir_path))
                    if scripts_dir_path.is_dir(): discovered_paths_collector.append(str(scripts_dir_path))
                    if bin_dir_path.is_dir(): discovered_paths_collector.append(str(bin_dir_path))
        
        if not discovered_paths_collector:
            conda_executable_shutil = shutil.which('conda')
            if conda_executable_shutil:
                conda_exe_shutil_path = Path(conda_executable_shutil).resolve()
                if conda_exe_shutil_path.is_file():
                    if not silent: self.logger.debug(f"[.ENV DISCOVERY] 'conda' trouvé via shutil.which: {conda_exe_shutil_path}")
                    # Le parent de 'conda' est souvent 'condabin', 'Scripts', ou 'bin'
                    # La racine de l'installation de conda est alors le parent de ce répertoire.
                    conda_install_root_path = conda_exe_shutil_path.parent.parent
                    
                    paths_to_check = [
                        conda_install_root_path / "condabin",
                        conda_install_root_path / "Scripts", # Windows
                        conda_install_root_path / "bin",     # Unix
                        conda_install_root_path / "Library" / "bin" # Windows, parfois
                    ]
                    for p_to_check in paths_to_check:
                        if p_to_check.is_dir() and str(p_to_check) not in discovered_paths_collector:
                            discovered_paths_collector.append(str(p_to_check))

        if not discovered_paths_collector:
            if not silent: self.logger.debug("[.ENV DISCOVERY] Tentative de recherche dans les chemins d'installation communs...")
            potential_install_roots_list: List[Path] = []
            system_os_name = platform.system()
            home_dir = Path.home()

            if system_os_name == "Windows":
                program_data_dir = Path(os.environ.get("ProgramData", "C:/ProgramData"))
                local_app_data_env_str = os.environ.get("LOCALAPPDATA")
                local_app_data_dir = Path(local_app_data_env_str) if local_app_data_env_str else home_dir / "AppData" / "Local"
                
                potential_install_roots_list.extend([
                    Path("C:/tools/miniconda3"), Path("C:/tools/anaconda3"),
                    home_dir / "anaconda3", home_dir / "miniconda3",
                    home_dir / "Anaconda3", home_dir / "Miniconda3", # Variations de casse
                    program_data_dir / "Anaconda3", program_data_dir / "Miniconda3",
                    local_app_data_dir / "Continuum" / "anaconda3" # Ancien chemin Anaconda
                ])
            else: # Linux/macOS
                potential_install_roots_list.extend([
                    home_dir / "anaconda3", home_dir / "miniconda3",
                    home_dir / ".anaconda3", home_dir / ".miniconda3", # Parfois cachés
                    Path("/opt/anaconda3"), Path("/opt/miniconda3"),
                    Path("/usr/local/anaconda3"), Path("/usr/local/miniconda3")
                ])
            
            found_root_from_common_paths = None
            for root_candidate_path in potential_install_roots_list:
                if root_candidate_path.is_dir():
                    # Vérifier la présence de sous-répertoires clés
                    condabin_check = root_candidate_path / "condabin"
                    scripts_check_win = root_candidate_path / "Scripts"
                    bin_check_unix = root_candidate_path / "bin"
                    
                    # Un indicateur fort est la présence de 'conda.exe' ou 'conda'
                    conda_exe_found = False
                    if system_os_name == "Windows":
                        if (condabin_check / "conda.exe").exists() or \
                           (scripts_check_win / "conda.exe").exists() or \
                           (condabin_check / "conda.bat").exists(): # conda.bat est aussi un indicateur
                            conda_exe_found = True
                    else:
                        if (bin_check_unix / "conda").exists() or \
                           (condabin_check / "conda").exists():
                            conda_exe_found = True
                    
                    if conda_exe_found:
                         if not silent: self.logger.debug(f"[.ENV DISCOVERY] Racine Conda potentielle trouvée: {root_candidate_path}")
                         found_root_from_common_paths = root_candidate_path
                         break
            
            if found_root_from_common_paths:
                paths_to_add_from_common = [
                    found_root_from_common_paths / "condabin",
                    found_root_from_common_paths / "Scripts",
                    found_root_from_common_paths / "bin",
                    found_root_from_common_paths / "Library" / "bin"
                ]
                for p_add in paths_to_add_from_common:
                    if p_add.is_dir() and str(p_add) not in discovered_paths_collector:
                        discovered_paths_collector.append(str(p_add))

        ordered_unique_paths_list: List[str] = []
        seen_paths_set = set()
        for p_str_item in discovered_paths_collector:
            if p_str_item not in seen_paths_set:
                ordered_unique_paths_list.append(p_str_item)
                seen_paths_set.add(p_str_item)
        
        if ordered_unique_paths_list:
            conda_path_to_write = os.pathsep.join(ordered_unique_paths_list)
            if not silent: self.logger.debug(f"[.ENV DISCOVERY] Chemins Conda consolidés: {conda_path_to_write}")

            env_file = self.project_root / ".env"
            updates = {"CONDA_PATH": f'"{conda_path_to_write}"'} # Mettre des guillemets pour les chemins avec espaces
            
            try:
                self._update_env_file_safely(env_file, updates, silent)
                load_dotenv(env_file, override=True) # Recharger pour mettre à jour os.environ
                if not silent: self.logger.info(f"[.ENV] Variables rechargées depuis {env_file}")

                if 'CONDA_PATH' in os.environ:
                    return True
                else: # Forcer pour la session courante si le rechargement a échoué
                    if not silent: self.logger.warning("[.ENV] CONDA_PATH non chargé après mise à jour, forçage pour session courante.")
                    os.environ['CONDA_PATH'] = conda_path_to_write
                    return True
            except Exception as e_write_env:
                if not silent: self.logger.warning(f"[.ENV] Échec de la mise à jour du fichier {env_file}: {e_write_env}")
                return False
        else:
            if not silent: self.logger.info("[.ENV DISCOVERY] Impossible de découvrir automatiquement les chemins Conda.")
            return False

    def _update_system_path_from_conda_env_var(self, silent: bool = True) -> bool:
        """
        Met à jour le PATH système (os.environ['PATH']) avec les chemins de CONDA_PATH.
        """
        try:
            conda_path_value = os.environ.get('CONDA_PATH', '')
            if not conda_path_value:
                if not silent:
                    self.logger.info("CONDA_PATH non défini dans os.environ pour _update_system_path_from_conda_env_var.")
                return False
            
            # Nettoyer les guillemets potentiels autour de la valeur de CONDA_PATH
            conda_path_value = conda_path_value.strip('"').strip("'")
            conda_paths_list = [p.strip() for p in conda_path_value.split(os.pathsep) if p.strip()]
            
            current_os_path = os.environ.get('PATH', '')
            path_elements = current_os_path.split(os.pathsep)
            
            updated = False
            # Ajouter les chemins Conda au début du PATH pour leur donner la priorité
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
            elif not silent:
                 self.logger.info("[PATH] PATH système déjà configuré avec les chemins de CONDA_PATH.")
            return True # Succès si mis à jour ou déjà configuré
                
        except Exception as e_path_update:
            if not silent:
                self.logger.warning(f"[PATH] Erreur lors de la mise à jour du PATH système depuis CONDA_PATH: {e_path_update}")
            return False

    def setup_project_pythonpath(self):
        """
        Configure PYTHONPATH pour inclure la racine du projet.
        Met également à jour sys.path pour la session courante.
        """
        project_path_str = str(self.project_root.resolve())
        
        # Mise à jour de os.environ['PYTHONPATH']
        existing_pythonpath = os.environ.get('PYTHONPATH', '')
        path_components = existing_pythonpath.split(os.pathsep) if existing_pythonpath else []
        
        if project_path_str not in path_components:
            path_components.insert(0, project_path_str) # Ajouter au début
            new_pythonpath = os.pathsep.join(path_components)
            os.environ['PYTHONPATH'] = new_pythonpath
            self.logger.info(f"PYTHONPATH mis à jour : {new_pythonpath}")
        else:
            self.logger.info(f"Racine du projet déjà dans PYTHONPATH : {project_path_str}")

        # Mise à jour de sys.path pour la session courante
        if project_path_str not in sys.path:
            sys.path.insert(0, project_path_str)
            self.logger.info(f"Racine du projet ajoutée à sys.path : {project_path_str}")


    def normalize_and_validate_java_home(self, auto_install_if_missing: bool = False) -> Optional[str]:
        """
        Normalise JAVA_HOME en chemin absolu et valide son existence.
        Peut tenter une auto-installation si demandé et si la logique est disponible.
        Met à jour os.environ['JAVA_HOME'] et le PATH système si valide.

        Returns:
            Le chemin absolu vers JAVA_HOME si valide, sinon None.
        """
        java_home_value = os.environ.get('JAVA_HOME')
        if not java_home_value:
            self.logger.warning("JAVA_HOME n'est pas défini dans l'environnement.")
            # Logique d'auto-installation (si activée et disponible) irait ici
            return None

        abs_java_home = Path(java_home_value)
        if not abs_java_home.is_absolute():
            abs_java_home = (self.project_root / java_home_value).resolve()
            self.logger.info(f"JAVA_HOME relatif '{java_home_value}' converti en absolu: {abs_java_home}")

        if abs_java_home.exists() and abs_java_home.is_dir():
            os.environ['JAVA_HOME'] = str(abs_java_home)
            self.logger.success(f"JAVA_HOME validé et défini sur: {abs_java_home}")

            # Ajouter le répertoire bin de la JVM au PATH système
            java_bin_path = abs_java_home / 'bin'
            if java_bin_path.is_dir():
                current_os_path = os.environ.get('PATH', '')
                path_elements = current_os_path.split(os.pathsep)
                if str(java_bin_path) not in path_elements:
                    path_elements.insert(0, str(java_bin_path)) # Ajouter au début
                    os.environ['PATH'] = os.pathsep.join(path_elements)
                    self.logger.info(f"Répertoire bin de JAVA_HOME ajouté au PATH système: {java_bin_path}")
            else:
                self.logger.warning(f"Répertoire bin de JAVA_HOME non trouvé à: {java_bin_path}")
            return str(abs_java_home)
        else:
            self.logger.error(f"Le chemin JAVA_HOME '{abs_java_home}' est invalide (n'existe pas ou n'est pas un répertoire).")
            # Logique d'auto-installation (si activée et disponible) irait ici
            return None

    def load_environment_variables(self) -> None:
        """
        Charge les variables d'environnement depuis le fichier .env du projet.
        Cette méthode est un point d'entrée simple pour charger .env.
        """
        # Utiliser un chemin direct et fiable vers le .env basé sur la racine du projet
        dotenv_path = self.project_root / ".env"

        if dotenv_path.is_file():
            self.logger.info(f"Chargement du fichier .env depuis: {dotenv_path}")
            load_dotenv(dotenv_path, override=True)
        else:
            self.logger.info(f"Aucun fichier .env trouvé à {dotenv_path}. Ce fichier sera créé si des variables comme CONDA_PATH sont découvertes.")
            # La logique suivante (_discover_and_persist_conda_path_in_env_file)
            # créera le fichier si nécessaire, mais ne l'écrasera plus par erreur.
            pass # On laisse initialize_environment_paths gérer la découverte


    def initialize_environment_paths(self) -> None:
        """
        Séquence d'initialisation complète pour les chemins et variables d'environnement.
        1. Charge .env.
        2. Découvre/Persiste CONDA_PATH dans .env et recharge.
        3. Met à jour le PATH système depuis CONDA_PATH.
        4. Configure PYTHONPATH et sys.path.
        5. Valide JAVA_HOME.
        """
        self.logger.info("Initialisation des chemins et variables d'environnement...")

        # 1. Charger .env (s'il existe)
        self.load_environment_variables()

        # 2. S'assurer que CONDA_PATH est découvert, persisté dans .env et chargé dans os.environ
        if not self._discover_and_persist_conda_path_in_env_file(silent=False):
            self.logger.warning("CONDA_PATH n'a pas pu être résolu ou persisté. Certaines fonctionnalités Conda pourraient échouer.")
        else:
            # 3. Mettre à jour le PATH système à partir de CONDA_PATH (maintenant dans os.environ)
            self._update_system_path_from_conda_env_var(silent=False)

        # 4. Configurer PYTHONPATH pour le projet
        self.setup_project_pythonpath()
        
        # 5. Normaliser et valider JAVA_HOME (et mettre à jour le PATH avec son bin)
        self.normalize_and_validate_java_home()

        self.logger.info("Initialisation des chemins et variables d'environnement terminée.")
        self.logger.debug(f"PATH final: {os.environ.get('PATH')}")
        self.logger.debug(f"PYTHONPATH final: {os.environ.get('PYTHONPATH')}")
        self.logger.debug(f"JAVA_HOME final: {os.environ.get('JAVA_HOME')}")
        self.logger.debug(f"CONDA_PATH final: {os.environ.get('CONDA_PATH')}")


if __name__ == "__main__":
    # Exemple d'utilisation
    current_project_root = Path(__file__).resolve().parent.parent.parent
    # Utilisation du logger global défini au début du fichier
    # Si un logger plus configuré est nécessaire, il faudrait l'instancier ici.
    
    path_manager = PathManager(project_root=current_project_root, logger_instance=logger)
    
    logger.info(f"Racine du projet détectée : {path_manager.get_project_root()}")

    # Test de la séquence d'initialisation complète
    path_manager.initialize_environment_paths()

    # Test de mise à jour du .env (exemple)
    env_file_example = current_project_root / ".env.example_path_manager"
    logger.info(f"\nTest de _update_env_file_safely sur {env_file_example}...")
    if env_file_example.exists():
        env_file_example.unlink() # Supprimer pour un test propre
    
    path_manager._update_env_file_safely(env_file_example, {"TEST_VAR_1": "value1", "NEW_VAR": "new_value"}, silent=False)
    path_manager._update_env_file_safely(env_file_example, {"TEST_VAR_1": "updated_value1", "ANOTHER_NEW": "another"}, silent=False)
    
    logger.info(f"Contenu de {env_file_example} après mises à jour:")
    if env_file_example.exists():
        with open(env_file_example, "r") as f:
            print(f.read())
        # env_file_example.unlink() # Nettoyage
    else:
        logger.warning(f"{env_file_example} non créé.")

    logger.info("\nPathManager tests terminés.")