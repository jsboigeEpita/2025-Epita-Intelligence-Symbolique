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
    
    logger = logging.getLogger("PortableToolsManager")
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

# --- Configurations des Outils ---
JDK_CONFIG = {
    "name": "JDK",
    "url_windows": "https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.11%2B9/OpenJDK17U-jdk_x64_windows_hotspot_17.0.11_9.zip",
    "url_linux": "https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.11%2B9/OpenJDK17U-jdk_x64_linux_hotspot_17.0.11_9.tar.gz",
    "url_darwin": "https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.11%2B9/OpenJDK17U-x64_mac_hotspot_17.0.11_9.tar.gz",
    "dir_name_pattern": r"jdk-17.*",
    "home_env_var": "JAVA_HOME"
}

OCTAVE_CONFIG = {
    "name": "Octave",
    "url_windows": "https://ftp.gnu.org/gnu/octave/windows/octave-8.4.0-w64.zip",
    "dir_name_pattern": r"octave-8.4.0-w64.*",
    "home_env_var": "OCTAVE_HOME"
}

NODE_CONFIG = {
   "name": "Node.js",
   "url_windows": "https://nodejs.org/dist/v20.14.0/node-v20.14.0-win-x64.zip",
   "dir_name_pattern": r"node-v20\.14\.0-win-x64",
   "home_env_var": "NODE_HOME"
}

TOOLS_TO_MANAGE = [JDK_CONFIG, OCTAVE_CONFIG, NODE_CONFIG]

# --- Fonctions Utilitaires ---

def _download_file(url, dest_folder, file_name, logger_instance=None, log_interval_seconds=5, force_download=False):
    """
    Télécharge un fichier depuis une URL vers un dossier de destination.
    Affiche une barre de progression simple dans le terminal.
    NOTE: Cette fonction est bloquante.
    """
    logger = _get_logger_tools(logger_instance)
    os.makedirs(dest_folder, exist_ok=True)
    file_path = os.path.join(dest_folder, file_name)

    if os.path.exists(file_path) and not force_download:
        logger.info(f"Le fichier {file_name} existe déjà. Téléchargement sauté.")
        return file_path

    try:
        logger.info(f"Début du téléchargement de {url}...")
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        
        with urllib.request.urlopen(req) as response, open(file_path, 'wb') as out_file:
            total_size = int(response.info().get('Content-Length', 0))
            bytes_so_far = 0
            start_time = time.time()
            last_log_time = start_time

            while True:
                chunk = response.read(8192)
                if not chunk:
                    break
                
                bytes_so_far += len(chunk)
                out_file.write(chunk)

                current_time = time.time()
                if current_time - last_log_time > log_interval_seconds:
                    elapsed = current_time - start_time
                    speed = (bytes_so_far / 1024**2) / elapsed if elapsed > 0 else 0
                    progress = (bytes_so_far / total_size) * 100 if total_size else 0
                    
                    sys.stdout.write(
                        f"\r -> Téléchargement en cours... {bytes_so_far / 1024**2:.2f}/{total_size / 1024**2:.2f} Mo "
                        f"({progress:.1f}%) à {speed:.2f} Mo/s"
                    )
                    sys.stdout.flush()
                    last_log_time = current_time

        sys.stdout.write("\n")
        logger.info(f"Téléchargement de {file_name} terminé.")
        return file_path
    
    except Exception as e:
        logger.error(f"Échec du téléchargement: {e}")
        if os.path.exists(file_path):
            os.remove(file_path) # Nettoyage en cas d'échec partiel
        return None

def _unzip_file(zip_path, dest_dir, logger_instance=None):
    """Décompresse une archive ZIP."""
    logger = _get_logger_tools(logger_instance)
    logger.info(f"Décompression de {zip_path} vers {dest_dir}...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(dest_dir)
        logger.info(f"Archive décompressée avec succès.")
        return True
    except zipfile.BadZipFile:
        logger.error("Le fichier téléchargé n'est pas une archive ZIP valide.")
        return False
    except Exception as e:
        logger.error(f"Erreur lors de la décompression: {e}")
        return False

def _find_extracted_directory(base_dir, dir_pattern, logger_instance=None):
    """
    Trouve le nom du répertoire qui a été créé après l'extraction du zip.
    """
    logger = _get_logger_tools(logger_instance)
    pattern = re.compile(dir_pattern)
    for item in os.listdir(base_dir):
        if os.path.isdir(os.path.join(base_dir, item)) and pattern.match(item):
            logger.info(f"Répertoire de l'outil trouvé : {item}")
            return os.path.join(base_dir, item)
    logger.warning(f"Aucun répertoire correspondant au motif '{dir_pattern}' trouvé dans {base_dir}")
    return None

def _is_tool_installed(env_var_name, expected_home_path=None, logger_instance=None):
    """
    Vérifie si un outil est déjà installé et configuré_
    - via sa variable d'environnement (ex: JAVA_HOME)
    - ou en vérifiant la présence du répertoire attendu.
    """
    logger = _get_logger_tools(logger_instance)
    env_var_value = os.environ.get(env_var_name)
    
    if env_var_value and os.path.isdir(env_var_value):
        logger.info(f"L'outil est déjà configuré via la variable d'environnement {env_var_name}={env_var_value}")
        return env_var_value
    
    if expected_home_path and os.path.isdir(expected_home_path):
        logger.info(f"L'outil est déjà présent dans le répertoire attendu : {expected_home_path}")
        return expected_home_path
        
    return None

def setup_single_tool(tool_config, tools_base_dir, temp_download_dir, logger_instance=None, force_reinstall=False, interactive=False):
    """Met en place un seul outil portable (téléchargement, extraction, configuration)."""
    logger = _get_logger_tools(logger_instance)
    
    tool_name = tool_config["name"]
    url = tool_config.get(f"url_{platform.system().lower()}")
    file_name = os.path.basename(url) if url else None
    dir_pattern = tool_config["dir_name_pattern"]
    env_var = tool_config["home_env_var"]
    
    logger.info(f"--- Configuration de {tool_name} ---")

    if not url or not file_name:
        logger.warning(f"URL de téléchargement non définie pour {tool_name} sur {platform.system().lower()}. Installation sautée.")
        return None

    expected_tool_path = _find_extracted_directory(tools_base_dir, dir_pattern, logger_instance=logger)
    
    # Vérification si l'outil est déjà installé
    installed_path = _is_tool_installed(env_var, expected_home_path=expected_tool_path, logger_instance=logger)
    if installed_path and not force_reinstall:
        logger.info(f"{tool_name} déjà configuré. Pour réinstaller, utilisez --force-reinstall.")
        return installed_path

    if force_reinstall and installed_path:
        logger.warning(f"Réinstallation forcée de {tool_name} demandée. Suppression de {installed_path}...")
        try:
            shutil.rmtree(installed_path)
            logger.info("Ancien répertoire supprimé.")
        except Exception as e:
            logger.error(f"Impossible de supprimer l'ancien répertoire : {e}")
            return None
    
    zip_path = _download_file(url, temp_download_dir, file_name, logger_instance=logger, force_download=force_reinstall)
    if not zip_path:
        return None
    
    if not _unzip_file(zip_path, tools_base_dir, logger_instance=logger):
        return None
    
    # Nettoyage du fichier zip après extraction
    try:
        os.remove(zip_path)
        logger.info(f"Archive {zip_path} supprimée.")
    except OSError as e:
        logger.warning(f"Impossible de supprimer l'archive {zip_path}: {e}")

    # Retrouver le chemin exact de l'outil après extraction
    expected_tool_path = _find_extracted_directory(tools_base_dir, dir_pattern, logger_instance=logger)
    if not expected_tool_path:
        logger.error(f"Impossible de trouver le répertoire de {tool_name} après extraction.")
        return None
    
    logger.success(f"{tool_name} a été installé avec succès dans : {expected_tool_path}")
    return expected_tool_path

def setup_tools(tools_dir_base_path, logger_instance=None, force_reinstall=False, interactive=False, skip_jdk=False, skip_octave=False, skip_node=False):
    """Configure les outils portables (JDK, Octave, Node.js)."""
    logger = _get_logger_tools(logger_instance)
    logger.debug(f"setup_tools called with: tools_dir_base_path={tools_dir_base_path}, force_reinstall={force_reinstall}, interactive={interactive}, skip_jdk={skip_jdk}, skip_octave={skip_octave}, skip_node={skip_node}")
    os.makedirs(tools_dir_base_path, exist_ok=True)
    temp_download_dir = os.path.join(tools_dir_base_path, "_temp_downloads")

    installed_tool_paths = {}

    if not skip_jdk:
        jdk_home = setup_single_tool(JDK_CONFIG, tools_dir_base_path, temp_download_dir, logger_instance=logger, force_reinstall=force_reinstall, interactive=interactive)
        if jdk_home:
            installed_tool_paths[JDK_CONFIG["home_env_var"]] = jdk_home
    else:
        logger.info("Skipping JDK setup as per request.")

    if not skip_octave:
        octave_home = setup_single_tool(OCTAVE_CONFIG, tools_dir_base_path, temp_download_dir, logger_instance=logger, force_reinstall=force_reinstall, interactive=interactive)
        if octave_home:
            installed_tool_paths[OCTAVE_CONFIG["home_env_var"]] = octave_home
    else:
        logger.info("Skipping Octave setup as per request.")

    if not skip_node:
        node_home = setup_single_tool(NODE_CONFIG, tools_dir_base_path, temp_download_dir, logger_instance=logger, force_reinstall=force_reinstall, interactive=interactive)
        if node_home:
            installed_tool_paths[NODE_CONFIG["home_env_var"]] = node_home
    else:
        logger.info("Skipping Node.js setup as per request.")
        
    if os.path.isdir(temp_download_dir):
        logger.info(f"Temporary download directory {temp_download_dir} can be cleaned up manually for now.")
    
    logger.info("Configuration des outils portables terminée.")
    return installed_tool_paths

if __name__ == "__main__":
    # --- Point d'entrée pour exécution directe ---
    import argparse
    parser = argparse.ArgumentParser(description="Gestionnaire d'installation d'outils portables (JDK, Octave, Node.js).")
    parser.add_argument("--tools-dir", default=os.path.join(os.getcwd(), "libs"), help="Répertoire de base pour les outils portables.")
    parser.add_argument("--force-reinstall", action="store_true", help="Force le re-téléchargement et la réinstallation même si l'outil est déjà présent.")
    parser.add_argument("--skip-jdk", action="store_true", help="Saute l'installation du JDK.")
    parser.add_argument("--skip-octave", action="store_true", help="Saute l'installation d'Octave.")
    parser.add_argument("--skip-node", action="store_true", help="Saute l'installation de Node.js.")
    
    args = parser.parse_args()
    
    main_logger = _get_logger_tools()
    main_logger.info("--- DÉBUT de la configuration des outils portables via le script principal ---")
    
    installed_paths = setup_tools(
        tools_dir_base_path=args.tools_dir,
        logger_instance=main_logger,
        force_reinstall=args.force_reinstall,
        skip_jdk=args.skip_jdk,
        skip_octave=args.skip_octave,
        skip_node=args.skip_node
    )
    
    main_logger.info("--- FIN de la configuration ---")
    if installed_paths:
        main_logger.info("Chemins des outils installés :")
        for env_var, path in installed_paths.items():
            main_logger.info(f"  {env_var}: {path}")
            # Suggestion pour l'utilisateur
            print(f"\nPour utiliser {env_var}, vous pouvez exporter cette variable:")
            if platform.system() == "Windows":
                 print(f'  setx {env_var} "{path}"')
            else:
                 print(f'  export {env_var}="{path}"')
    else:
        main_logger.warning("Aucun outil n'a été installé ou configuré.")