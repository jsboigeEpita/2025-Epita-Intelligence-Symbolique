# project_core/setup_core_from_scripts/manage_tweety_libs.py
"""
Ce module contient la logique restaurée pour télécharger les bibliothèques JAR
de TweetyProject. Cette fonctionnalité a été retirée de jvm_setup.py et est
réintégrée ici pour être appelée par le gestionnaire d'environnement.
"""

import os
import pathlib
import platform
import logging
import requests
from tqdm.auto import tqdm
import stat
from typing import Optional

# Configuration du logger
logger = logging.getLogger("Orchestration.Setup.Tweety")
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Constantes
TWEETY_VERSION = "1.28"

class TqdmUpTo(tqdm):
    """Provides `update_to(block_num, block_size, total_size)`."""
    def update_to(self, b=1, bsize=1, tsize=None):
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n)

def _download_file_with_progress(file_url: str, target_path: pathlib.Path, description: str):
    """Télécharge un fichier depuis une URL vers un chemin cible avec une barre de progression."""
    try:
        if target_path.exists() and target_path.stat().st_size > 0:
            logger.debug(f"Fichier '{target_path.name}' déjà présent et non vide. Skip.")
            return True, False
        
        logger.info(f"Tentative de téléchargement: {file_url} vers {target_path}")
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(file_url, stream=True, timeout=30, headers=headers, allow_redirects=True)
        
        if response.status_code == 404:
            logger.error(f"Fichier non trouvé (404) à l'URL: {file_url}")
            return False, False
            
        response.raise_for_status()
        total_size = int(response.headers.get('content-length', 0))
        
        with TqdmUpTo(unit='B', unit_scale=True, unit_divisor=1024, total=total_size, miniters=1, desc=description[:40]) as t:
            with open(target_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        t.update(len(chunk))
                        
        if target_path.exists() and target_path.stat().st_size > 0:
            logger.info(f" -> Téléchargement de '{target_path.name}' réussi.")
            return True, True
        else:
            logger.error(f"Téléchargement de '{target_path.name}' semblait terminé mais fichier vide ou absent.")
            if target_path.exists():
                target_path.unlink(missing_ok=True)
            return False, False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Échec connexion/téléchargement pour '{target_path.name}': {e}")
        if target_path.exists():
            target_path.unlink(missing_ok=True)
        return False, False
    except Exception as e_other:
        logger.error(f"Erreur inattendue pour '{target_path.name}': {e_other}", exc_info=True)
        if target_path.exists():
            target_path.unlink(missing_ok=True)
        return False, False

def download_tweety_jars(
    target_dir: str,
    version: str = TWEETY_VERSION,
    native_subdir: str = "native"
) -> bool:
    """
    Vérifie et télécharge les JARs Tweety (Core + Modules) et les binaires natifs nécessaires.
    """
    logger.info(f"--- Démarrage de la vérification/téléchargement des JARs Tweety v{version} ---")
    BASE_URL = f"https://tweetyproject.org/builds/{version}/"
    LIB_DIR = pathlib.Path(target_dir)
    NATIVE_LIBS_DIR = LIB_DIR / native_subdir
    LIB_DIR.mkdir(exist_ok=True)
    NATIVE_LIBS_DIR.mkdir(exist_ok=True)

    CORE_JAR_NAME = f"org.tweetyproject.tweety-full-{version}-with-dependencies.jar"
    
    # --- Contournement du verrou en renommant le fichier JAR existant ---
    jar_to_rename_path = LIB_DIR / CORE_JAR_NAME
    if jar_to_rename_path.exists():
        locked_file_path = jar_to_rename_path.with_suffix(jar_to_rename_path.suffix + '.locked')
        logger.warning(f"Tentative de renommage du JAR potentiellement verrouillé: {jar_to_rename_path} -> {locked_file_path}")
        try:
            # S'assurer qu'un ancien fichier .locked ne bloque pas le renommage
            if locked_file_path.exists():
                try:
                    locked_file_path.unlink()
                except OSError as e_unlink:
                    logger.error(f"Impossible de supprimer l'ancien fichier .locked '{locked_file_path}': {e_unlink}")
                    # Ne pas bloquer, le renommage va probablement échouer mais on loggue le problème.

            jar_to_rename_path.rename(locked_file_path)
            logger.info(f"Renommage réussi. Le chemin est libre pour un nouveau téléchargement.")
        except OSError as e:
            logger.error(f"Impossible de renommer le JAR existant. Le verrou est probablement très fort. Erreur: {e}")
            # L'échec ici est grave, car le téléchargement échouera probablement aussi.
            # On continue quand même pour voir les logs du downloader.
    # --- Fin du contournement ---
    
    logger.info(f"Vérification de l'accès à {BASE_URL}...")
    try:
        response = requests.head(BASE_URL, timeout=10)
        response.raise_for_status()
        logger.info(f"URL de base Tweety v{version} accessible.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Impossible d'accéder à l'URL de base {BASE_URL}. Erreur : {e}")
        logger.warning("Le téléchargement des JARs manquants échouera.")
        return False

    logger.info(f"--- Vérification/Téléchargement JAR Core ---")
    core_present, core_new = _download_file_with_progress(BASE_URL + CORE_JAR_NAME, LIB_DIR / CORE_JAR_NAME, CORE_JAR_NAME)
    status_core = "téléchargé" if core_new else ("déjà présent" if core_present else "MANQUANT")
    logger.info(f"JAR Core '{CORE_JAR_NAME}': {status_core}.")
    
    if not core_present:
        logger.critical("Le JAR core est manquant et n'a pas pu être téléchargé. Opération annulée.")
        return False

    logger.info("--- Fin de la vérification/téléchargement des JARs Tweety ---")
    return True