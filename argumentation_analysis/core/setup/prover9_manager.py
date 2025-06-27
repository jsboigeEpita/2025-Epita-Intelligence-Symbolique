# coding: utf-8
import os
import re
import sys
import time
import shutil
import zipfile
import logging
import platform
import subprocess
import urllib.request
import threading
from pathlib import Path

# --- Configuration du Logger ---
def _get_logger_tools(logger_instance=None):
    """Obtient un logger configuré."""
    if logger_instance:
        return logger_instance
    
    logger = logging.getLogger("Prover9Manager")
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

class Prover9Manager:
    PROVER9_CONFIG = {
        "name": "Prover9",
        "url_windows": "https://www.cs.unm.edu/~mccune/mace4/download/LADR-2009-11A.zip",
        "url_linux": "https://www.cs.unm.edu/~mccune/mace4/download/LADR-2009-11A.zip", # Note: Binaires Windows dans le zip
        "dir_name_pattern": r"LADR-2009-11A",
        "executable_path_windows": "bin/prover9.exe",
        "executable_path_linux": "bin/prover9" 
    }

    def __init__(self, logger_instance=None):
        if hasattr(self, '_initialized'):
            return
        self.logger = _get_logger_tools(logger_instance)
        self.tools_base_dir = self._get_default_tools_dir()
        self.temp_download_dir = self.tools_base_dir / "_temp_downloads"
        self._initialized = True

    def _get_default_tools_dir(self):
        # Chemin relatif depuis ce fichier vers la racine du projet, puis vers 'libs'
        # Ce fichier est dans argumentation_analysis/core/setup
        project_root = Path(__file__).parent.parent.parent.parent
        return project_root / "libs"

    def get_prover9_executable_path(self, force_reinstall=False):
        self.logger.info("--- Configuration de Prover9 ---")
        
        config = self.PROVER9_CONFIG
        tool_name = config["name"]
        dir_pattern = config["dir_name_pattern"]
        
        # Le répertoire d'installation final de Prover9
        install_dir = self.tools_base_dir / "prover9"

        # Le chemin de l'exécutable attendu
        system = platform.system().lower()
        if system == 'windows':
            executable_relative_path = config["executable_path_windows"]
        else:
            # Pour Linux/macOS, le binaire est directement dans le path après compilation
            executable_relative_path = config["executable_path_linux"]

        executable_path_base = install_dir / Path(executable_relative_path).parent / Path(executable_relative_path).stem
        
        # Noms de fichiers possibles à vérifier
        wrapper_path = executable_path_base.with_suffix('.bat')
        original_executable_path = executable_path_base.with_suffix('.exe.original')
        standard_executable_path = executable_path_base.with_suffix('.exe')

        if not force_reinstall:
            # 1. Le wrapper existe déjà (cas le plus courant après la première exécution)
            if wrapper_path.exists():
                self.logger.info(f"Wrapper Prover9 trouvé à : {wrapper_path}")
                return str(wrapper_path)
            
            # 2. L'original renommé existe, mais le wrapper a été supprimé
            if original_executable_path.exists():
                self.logger.warning(f"Prover9 original ({original_executable_path.name}) trouvé sans son wrapper. Recréation du wrapper...")
                # On doit passer le chemin de l'exécutable NON renommé pour que la logique de renommage fonctionne
                return str(self._create_prover9_wrapper(standard_executable_path))

            # 3. L'exécutable standard existe (première installation)
            if standard_executable_path.exists():
                self.logger.info(f"Exécutable Prover9 standard trouvé à : {standard_executable_path}. Création du wrapper...")
                return str(self._create_prover9_wrapper(standard_executable_path))

        if force_reinstall and install_dir.exists():
            self.logger.warning(f"Réinstallation forcée de {tool_name}, suppression de {install_dir}...")
            shutil.rmtree(install_dir)

        # Création du répertoire d'installation
        install_dir.mkdir(parents=True, exist_ok=True)

        if system == 'windows':
            return self._setup_prover9_windows(config, install_dir)
        else:
            return self._setup_prover9_unix(config, install_dir)

    def _setup_prover9_windows(self, config, install_dir):
        """ Gère le téléchargement et l'extraction pour Windows """
        url = config["url_windows"]
        file_name = Path(url).name
        zip_path = self.temp_download_dir / file_name

        if not _download_file(url, self.temp_download_dir, file_name, self.logger):
             return None

        # Décompresser le contenu de LADR-2009-11A.zip
        extracted_content_dir = self.temp_download_dir / "LADR-2009-11A"
        if not _unzip_file(str(zip_path), str(self.temp_download_dir), self.logger):
            return None
        
        # Le zip contient un dossier 'LADR-2009-11A'. Nous voulons copier son contenu.
        source_bin_dir = extracted_content_dir / "bin"
        
        # Copier le contenu du dossier 'bin' dans notre dossier d'installation 'prover9/bin'
        dest_bin_dir = install_dir / "bin"
        try:
            shutil.copytree(source_bin_dir, dest_bin_dir)
            self.logger.info(f"Fichiers de Prover9 copiés dans {dest_bin_dir}")
        except Exception as e:
            self.logger.error(f"Erreur lors de la copie des fichiers de Prover9 : {e}")
            return None
        
        executable_path = dest_bin_dir / "prover9.exe"
        if executable_path.exists():
            # --- PATCH: Mettre en place le wrapper pour Prover9 ---
            wrapper_path = self._create_prover9_wrapper(executable_path)
            return str(wrapper_path)
        else:
            self.logger.error("prover9.exe non trouvé après extraction et copie.")
            return None

    def _setup_prover9_unix(self, config, install_dir):
        """ Gère le téléchargement, la compilation et l'installation pour les systèmes Unix """
        self.logger.info("L'installation de Prover9 sur les systèmes non-Windows nécessite une compilation manuelle.")
        self.logger.info("Tentative de téléchargement et de compilation...")
        
        url = config["url_linux"]
        file_name = Path(url).name
        zip_path = self.temp_download_dir / file_name

        if not _download_file(url, self.temp_download_dir, file_name, self.logger):
            return None

        extracted_source_dir = self.temp_download_dir / "LADR-2009-11A"
        if not _unzip_file(str(zip_path), str(self.temp_download_dir), self.logger):
            return None

        # Compilation
        try:
            self.logger.info(f"Compilation de Prover9 dans {extracted_source_dir}...")
            # Le makefile est à la racine du dossier extrait
            subprocess.run(["make", "all"], cwd=str(extracted_source_dir), check=True)
            self.logger.info("Compilation réussie.")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            self.logger.error(f"Échec de la compilation de Prover9. 'make' doit être installé. Erreur : {e}")
            self.logger.error("Veuillez compiler et installer Prover9 manuellement et vous assurer qu'il est dans le PATH système.")
            return None

        # Copie des binaires compilés
        source_bin_dir = extracted_source_dir / "bin"
        dest_bin_dir = install_dir / "bin"
        try:
            shutil.copytree(source_bin_dir, dest_bin_dir)
            # Rendre les exécutables... exécutables !
            for item in dest_bin_dir.iterdir():
                item.chmod(item.stat().st_mode | 0o111) 
            self.logger.info(f"Binaires de Prover9 copiés et rendus exécutables dans {dest_bin_dir}")
        except Exception as e:
            self.logger.error(f"Erreur lors de la copie des binaires de Prover9 : {e}")
            return None

        executable_path = dest_bin_dir / "prover9"
        if executable_path.exists():
            # --- PATCH: Mettre en place le wrapper pour Prover9 ---
            wrapper_path = self._create_prover9_wrapper(executable_path)
            return str(wrapper_path)
        else:
            self.logger.error("Binaire 'prover9' non trouvé après compilation.")
            return None

    def _create_prover9_wrapper(self, original_executable_path: Path):
        """
        Crée un script wrapper (.bat) pour contourner le problème de deadlock de Prover9.
        Le wrapper appelle Prover9 avec '--help' s'il est appelé sans arguments.
        """
        
        original_executable_path = Path(original_executable_path)
        wrapper_path = original_executable_path.with_suffix('.bat')
        original_renamed_path = original_executable_path.with_suffix('.exe.original')

        # 1. Renommer prover9.exe en prover9.exe.original si ce n'est pas déjà fait
        if original_executable_path.exists() and not original_renamed_path.exists():
            self.logger.info(f"Renommage de {original_executable_path} en {original_renamed_path}")
            original_executable_path.rename(original_renamed_path)
        
        # 2. Créer le script wrapper
        wrapper_content = f"""@echo off
rem Wrapper pour prover9.exe pour gérer le cas sans arguments qui cause un deadlock.
set "PROVER9_CMD={original_renamed_path.name}"
set "PROVER9_DIR={original_renamed_path.parent.resolve()}"

rem Vérifie si des arguments ont été passés
if [%1]==[] (
    rem Aucun argument, appel avec --help pour une sortie rapide et éviter le blocage
    rem echo "Wrapper: Prover9 appelé sans arguments. Appel de --help pour éviter le blocage."
    "%PROVER9_DIR%\\%PROVER9_CMD%" --help
) else (
    rem Des arguments sont présents, les passer à l'exécutable original
    rem echo "Wrapper: Prover9 appelé avec des arguments. Transmission..."
    "%PROVER9_DIR%\\%PROVER9_CMD%" %*
)
"""
        
        self.logger.info(f"Création du script wrapper pour Prover9 à : {wrapper_path}")
        with open(wrapper_path, "w") as f:
            f.write(wrapper_content)
            
        return wrapper_path

# Il nous faut ces fonctions ici aussi, car ce module est maintenant autonome
def _download_file(url, dest_folder, file_name, logger, log_interval_seconds=5, force_download=False):
    os.makedirs(dest_folder, exist_ok=True)
    file_path = Path(dest_folder) / file_name
    if file_path.exists() and not force_download:
        logger.info(f"Le fichier {file_name} existe déjà. Téléchargement sauté.")
        return str(file_path)
    try:
        logger.info(f"Début du téléchargement de {url}...")
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response, open(file_path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        logger.info(f"Téléchargement de {file_name} terminé.")
        return str(file_path)
    except Exception as e:
        logger.error(f"Échec du téléchargement: {e}")
        if file_path.exists():
            os.remove(file_path)
        return None

def _unzip_file(zip_path, dest_dir, logger):
    logger.info(f"Décompression de {zip_path} vers {dest_dir}...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(dest_dir)
        logger.info(f"Archive décompressée avec succès.")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la décompression: {e}")
        return False