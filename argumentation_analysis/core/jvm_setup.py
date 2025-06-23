# core/jvm_setup.py
# NOTE DEV: La demande de commenter l'import de 'Agent' de 'semantic_kernel.agents' a été notée.
# Cet import n'étant pas présent dans ce fichier, aucune action n'a été nécessaire ici.
import os
import re
import sys
# import jpype  # IMPORTANT: L'import est déplacé dans les fonctions pour chargement tardif
import logging
import platform
import shutil
import subprocess
import zipfile
import requests
from pathlib import Path
from typing import Optional, List, Dict
from tqdm.auto import tqdm
import stat

from argumentation_analysis.config.settings import settings

# Configuration du logger pour ce module
logger = logging.getLogger("Orchestration.JPype")

# --- Fonctions de téléchargement et de provisioning (issues du stash de HEAD) ---

def get_project_root_robust() -> Path:
    """
    Trouve la racine du projet en remontant depuis l'emplacement de ce fichier.
    Chemin: .../racine_projet/argumentation_analysis/core/jvm_setup.py
    La racine est 2 niveaux au-dessus du dossier 'core'.
    """
    # current_path.parents[0] -> .../core
    # current_path.parents[1] -> .../argumentation_analysis
    # current_path.parents[2] -> .../racine_projet
    current_path = Path(__file__).resolve()
    # Utiliser parents[2] pour remonter de core -> argumentation_analysis -> racine
    project_root = current_path.parents[2]
    logger.debug(f"Racine du projet déterminée de manière statique à : {project_root}")
    return project_root

# --- Constantes de Configuration ---
# Répertoires (utilisant pathlib pour la robustesse multi-plateforme)
PROJ_ROOT = get_project_root_robust()

# Les constantes sont maintenant lues depuis l'objet de configuration centralisé 'settings'
LIBS_DIR = PROJ_ROOT / settings.jvm.tweety_libs_dir
TWEETY_VERSION = settings.jvm.tweety_version

# La configuration des dépendances n'est plus nécessaire ici
# car nous utilisons le JAR "full-with-dependencies"

# Configuration JDK portable lue depuis les settings
MIN_JAVA_VERSION = settings.jvm.min_java_version
JDK_VERSION = settings.jvm.jdk_version
JDK_BUILD = settings.jvm.jdk_build
JDK_URL_TEMPLATE = settings.jvm.jdk_url_template
# Windows: x64_windows, aarch64_windows | Linux: x64_linux, aarch64_linux | macOS: x64_mac, aarch64_mac

# --- Fonctions Utilitaires ---
class TqdmUpTo(tqdm):
    """Provides `update_to(block_num, block_size, total_size)`."""
    def update_to(self, b=1, bsize=1, tsize=None):
         if tsize is not None: self.total = tsize
         self.update(b * bsize - self.n)

def get_os_arch_for_jdk() -> Dict[str, str]:
    """Détermine l'OS et l'architecture pour l'URL de téléchargement du JDK."""
    system = platform.system().lower()
    arch = platform.machine().lower()

    os_map = {"windows": "windows", "linux": "linux", "darwin": "mac"}
    arch_map = {"amd64": "x64", "x86_64": "x64", "aarch64": "aarch64", "arm64": "aarch64"}

    if system not in os_map:
        raise OSError(f"Système d'exploitation non supporté pour le JDK portable : {platform.system()}")
    if arch not in arch_map:
        raise OSError(f"Architecture non supportée pour le JDK portable : {arch}")

    return {"os": os_map[system], "arch": arch_map[arch]}


def download_file(url: str, dest_path: Path, description: Optional[str] = None):
    """Télécharge un fichier depuis une URL vers un chemin cible avec une barre de progression."""
    if description is None:
        description = dest_path.name

    try:
        # S'assurer que le répertoire parent de dest_path existe
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Vérifier si le fichier existe déjà et est non vide (de HEAD)
        if dest_path.exists() and dest_path.stat().st_size > 0:
            logger.debug(f"Fichier '{dest_path.name}' déjà présent et non vide. Skip.")
            return True, False # Fichier présent, pas de nouveau téléchargement

        logger.info(f"Tentative de téléchargement: {url} vers {dest_path}")
        headers = {'User-Agent': 'Mozilla/5.0'} # De HEAD
        # Timeout de la version entrante (30s), allow_redirects de HEAD
        response = requests.get(url, stream=True, timeout=30, headers=headers, allow_redirects=True)

        if response.status_code == 404: # De HEAD
             logger.error(f"❌ Fichier non trouvé (404) à l'URL: {url}")
             return False, False

        response.raise_for_status() # De HEAD / version entrante implicitement

        total_size = int(response.headers.get('content-length', 0))

        # Utiliser logger au lieu de logging
        with TqdmUpTo(unit='B', unit_scale=True, unit_divisor=1024, total=total_size, miniters=1, desc=description[:40]) as t:
            with open(dest_path, 'wb') as f: # Utiliser dest_path
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        t.update(len(chunk))

        # Vérification après téléchargement (de HEAD)
        if dest_path.exists() and dest_path.stat().st_size > 0:
            # Ajout d'une vérification de taille si total_size était connu
            if total_size != 0 and dest_path.stat().st_size != total_size:
                 logger.warning(f"⚠️ Taille du fichier téléchargé '{dest_path.name}' ({dest_path.stat().st_size}) "
                                f"ne correspond pas à la taille attendue ({total_size}).")
            logger.info(f" -> Téléchargement de '{dest_path.name}' réussi.")
            return True, True # Fichier présent, et il a été (re)téléchargé
        else:
            logger.error(f"❓ Téléchargement de '{dest_path.name}' semblait terminé mais fichier vide ou absent.")
            if dest_path.exists(): dest_path.unlink(missing_ok=True) # Nettoyer si fichier vide
            return False, False

    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Échec connexion/téléchargement pour '{dest_path.name}': {e}")
        if dest_path.exists(): dest_path.unlink(missing_ok=True)
        return False, False
    except Exception as e_other:
        logger.error(f"❌ Erreur inattendue pendant téléchargement de '{dest_path.name}': {e_other}", exc_info=True)
        if dest_path.exists(): dest_path.unlink(missing_ok=True)
        return False, False

# Les fonctions get_project_root_for_libs et find_libs_dir sont obsolètes
# et remplacées par la nouvelle fonction get_project_root_robust.

def download_tweety_jars(
    version: str = TWEETY_VERSION,
    target_dir: Optional[Path] = None
) -> bool:
    """
    Vérifie la présence du JAR 'full-with-dependencies' de Tweety et le télécharge si manquant.
    """
    logger.info(f"--- Démarrage de la vérification/téléchargement des JARs Tweety v{version} ---")
    target_dir_path = Path(target_dir) if target_dir else LIBS_DIR
    target_dir_path.mkdir(parents=True, exist_ok=True)

    # Configuration pour le JAR "full-with-dependencies"
    jar_filename = f"org.tweetyproject.tweety-full-{version}-with-dependencies.jar"
    jar_url = f"https://tweetyproject.org/builds/{version}/{jar_filename}"
    jar_target_path = target_dir_path / jar_filename

    logger.info(f"Vérification de la présence de: {jar_target_path}")

    # Si le fichier existe et n'est pas vide, on ne fait rien
    if jar_target_path.exists() and jar_target_path.stat().st_size > 0:
        logger.info(f"JAR Core '{jar_filename}': déjà présent.")
        logger.info("--- Fin de la vérification/téléchargement des JARs Tweety ---")
        return True

    # Si le fichier n'existe pas, on le télécharge
    logger.info(f"JAR '{jar_filename}' non trouvé ou vide. Tentative de téléchargement...")
    
    # Vérifier l'accessibilité de l'URL de base avant de tenter le téléchargement
    base_url = f"https://tweetyproject.org/builds/{version}/"
    try:
        response = requests.head(base_url, timeout=10)
        response.raise_for_status()
        logger.info(f"URL de base Tweety v{version} accessible.")
    except requests.RequestException as e:
        logger.error(f"Impossible d'accéder à l'URL de base de Tweety {base_url}. Erreur: {e}")
        logger.error("Vérifiez la connexion internet ou la disponibilité du site de Tweety.")
        return False

    success, _ = download_file(jar_url, jar_target_path, description=jar_filename)

    if success:
        logger.info(f"JAR '{jar_filename}' téléchargé avec succès.")
    else:
        logger.error(f"Échec du téléchargement du JAR '{jar_filename}' depuis {jar_url}.")

    logger.info("--- Fin de la vérification/téléchargement des JARs Tweety ---")
    return success

def unzip_file(zip_path: Path, dest_dir: Path):
    """Décompresse un fichier ZIP."""
    logger.info(f"Décompression de {zip_path} vers {dest_dir}...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            # Identifie les répertoires de premier niveau dans le zip
            top_level_contents = {Path(f).parts[0] for f in file_list}

            if len(file_list) > 0 and len(top_level_contents) == 1:
                # Cas où tout le contenu est dans un seul dossier racine DANS le zip
                # ex: le zip contient "jdk-17.0.2+8/" qui contient "bin", "lib", etc.
                single_root_dir_in_zip_name = top_level_contents.pop()
                
                # Vérifier si tous les fichiers commencent par ce dossier racine
                if all(f.startswith(single_root_dir_in_zip_name + os.sep) or f == single_root_dir_in_zip_name for f in file_list if f):


                    temp_extract_dir = dest_dir.parent / (dest_dir.name + "_temp_extract_strip")
                    if temp_extract_dir.exists():
                        shutil.rmtree(temp_extract_dir)
                    temp_extract_dir.mkdir(parents=True, exist_ok=True)
                    
                    zip_ref.extractall(temp_extract_dir)
                    
                    source_dir_to_move_from = temp_extract_dir / single_root_dir_in_zip_name
                    
                    # Vider dest_dir avant de déplacer (sauf si c'est la même chose que source_dir_to_move_from)
                    if dest_dir.resolve() != source_dir_to_move_from.resolve():
                        for item in dest_dir.iterdir():
                            if item.is_dir():
                                shutil.rmtree(item)
                            else:
                                item.unlink()
                    else: # Ne devrait pas arriver avec _temp_extract_strip
                        logger.warning("Le répertoire de destination est le même que le répertoire source temporaire.")

                    for item in source_dir_to_move_from.iterdir():
                        shutil.move(str(item), str(dest_dir / item.name))
                    
                    shutil.rmtree(temp_extract_dir)
                    logger.info(f"Contenu de '{single_root_dir_in_zip_name}' extrait et déplacé vers '{dest_dir}'.")
                else:
                    # Structure de fichiers mixte, extraire normalement
                    zip_ref.extractall(dest_dir)
                    logger.info("Extraction standard effectuée (pas de strip de dossier racine).")
            else:
                 # Le contenu est déjà à la racine du zip, ou plusieurs éléments à la racine.
                 zip_ref.extractall(dest_dir)
                 logger.info("Extraction standard effectuée (contenu à la racine ou multiple).")

        if zip_path.exists():
            zip_path.unlink()
        logger.info("Décompression terminée.")
    except (zipfile.BadZipFile, IOError, shutil.Error) as e:
        logger.error(f"Erreur lors de la décompression de {zip_path}: {e}", exc_info=True)
        # Essayer de nettoyer dest_dir en cas d'erreur d'extraction pour éviter un état partiel
        if dest_dir.exists():
            shutil.rmtree(dest_dir, ignore_errors=True)
            dest_dir.mkdir(parents=True, exist_ok=True) # Recréer le dossier vide
        raise


# --- Constantes et Fonctions pour la gestion du JDK ---
PORTABLE_JDK_DIR_NAME = "portable_jdk"
TEMP_DIR_NAME = "_temp_jdk_download"
# MIN_JAVA_VERSION, JDK_VERSION, JDK_BUILD, JDK_URL_TEMPLATE sont définis plus haut

def get_project_root() -> Path:
    """Retourne la racine du projet, qui est maintenant déterminée de manière robuste."""
    return PROJ_ROOT

def is_valid_jdk(path: Path) -> bool:
    """Vérifie si un répertoire est un JDK valide et respecte la version minimale."""
    if not path.is_dir():
        return False
        
    java_exe = path / "bin" / ("java.exe" if platform.system() == "Windows" else "java")
    if not java_exe.is_file():
        logger.debug(f"Validation JDK: 'java' non trouvé ou n'est pas un fichier dans {path / 'bin'}")
        return False

    try:
        result = subprocess.run(
            [str(java_exe), "-version"],
            capture_output=True,
            text=True,
            check=False
        )
        version_output = result.stderr if result.stderr else result.stdout
        if not version_output:
            logger.warning(f"Impossible d'obtenir la sortie de version pour le JDK à {path} (commande: '{str(java_exe)} -version'). stderr: {result.stderr}, stdout: {result.stdout}")
            return False

        # Tenter de parser plusieurs formats de sortie de version
        # Format OpenJDK: openjdk version "17.0.11" 2024-04-16
        # Format Oracle: java version "1.8.0_202"
        version_pattern = r'version "(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:_(\d+))?.*"'
        
        match = None
        for line in version_output.splitlines():
            match = re.search(version_pattern, line)
            if match:
                break
        
        if not match:
            logger.warning(f"Impossible de parser la chaîne de version du JDK à '{path}'. Sortie: {version_output.strip()}")
            return False
        
        major_version_str = match.group(1)
        minor_version_str = match.group(2)

        major_version = int(major_version_str)
        if major_version == 1 and minor_version_str: # Format "1.X" (Java 8 et moins)
            major_version = int(minor_version_str)

        try:
            raw_version_detail = match.group(0).split('"')[1]
        except IndexError:
            logger.error(f"Impossible d'extraire le numéro de version de '{match.group(0)}'. Format inattendu.")
            raw_version_detail = "FORMAT_INCONNU" # Fallback
        
        version_details_str = raw_version_detail.replace('\\', '\\\\')

        if major_version >= MIN_JAVA_VERSION:
            logger.info(f"Version Java détectée à '{path}': \"{version_details_str}\" (Majeure: {major_version}) -> Valide.")
            return True
        else:
            logger.warning(f"Version Java détectée à '{path}': \"{version_details_str}\" (Majeure: {major_version}) -> INVALIDE (minimum requis: {MIN_JAVA_VERSION}).")
            return False
    except FileNotFoundError:
        logger.error(f"Exécutable Java non trouvé à {java_exe} lors de la vérification de version.")
        return False
    except Exception as e:
        logger.error(f"Erreur lors de la validation du JDK à {path}: {e}", exc_info=True)
        return False

def find_existing_jdk() -> Optional[Path]:
    """
    Tente de trouver un JDK valide.
    Note : La vérification de JAVA_HOME est désactivée pour forcer
    l'utilisation du JDK portable et garantir la consistance.
    """
    logger.debug("Recherche d'un JDK portable pré-existant valide (JAVA_HOME est ignoré).")
    
    project_r = get_project_root()
    portable_jdk_dir = project_r / PORTABLE_JDK_DIR_NAME
    
    if portable_jdk_dir.is_dir():
        if is_valid_jdk(portable_jdk_dir):
             logger.info(f"JDK portable validé directement dans : {portable_jdk_dir}")
             return portable_jdk_dir
        for item in portable_jdk_dir.iterdir():
            if item.is_dir() and item.name.startswith("jdk-"): # Typique pour les extractions Adoptium
                if is_valid_jdk(item):
                    logger.info(f"JDK portable validé dans sous-dossier : {item}")
                    return item
    
    logger.info("Aucun JDK pré-existant valide trouvé. Le téléchargement va être tenté.")
    return None

def find_valid_java_home() -> Optional[str]:
    """
    Trouve un JAVA_HOME valide. Vérifie les JDK existants, puis tente de télécharger
    et d'installer un JDK portable si nécessaire.
    """
    logger.info("Recherche d'un environnement Java valide...")
    
    existing_jdk_path = find_existing_jdk()
    if existing_jdk_path:
        logger.info(f"[SUCCESS] Utilisation du JDK existant validé: '{existing_jdk_path}'")
        return str(existing_jdk_path.resolve())

    logger.info("Aucun JDK valide existant. Tentative d'installation d'un JDK portable.")
    project_r = get_project_root()
    portable_jdk_install_dir = project_r / PORTABLE_JDK_DIR_NAME
    temp_download_dir = project_r / TEMP_DIR_NAME
    
    try:
        portable_jdk_install_dir.mkdir(parents=True, exist_ok=True)
        temp_download_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error(f"Impossible de créer les répertoires pour JDK portable ({portable_jdk_install_dir} ou {temp_download_dir}): {e}")
        return None

    os_arch_info = get_os_arch_for_jdk()
    
    # Utiliser les constantes globales JDK_VERSION, JDK_BUILD, JDK_URL_TEMPLATE
    # JDK_VERSION ex: "17.0.11", JDK_BUILD ex: "9"
    # JDK_URL_TEMPLATE ex: "https://github.com/adoptium/temurin{maj_v}-binaries/releases/download/jdk-{v}%2B{b}/OpenJDK{maj_v}U-jdk_{arch}_{os}_hotspot_{v}_{b_flat}.zip"

    jdk_major_for_url = JDK_VERSION.split('.')[0] # ex: "17"
    
    # Le nom du fichier zip peut varier légèrement, mais l'URL est la clé.
    # On va nommer le zip de manière générique pour le téléchargement.
    generic_zip_name = f"portable_jdk_{JDK_VERSION}_{JDK_BUILD}_{os_arch_info['os']}_{os_arch_info['arch']}.zip"
    jdk_zip_target_path = temp_download_dir / generic_zip_name

    jdk_url = JDK_URL_TEMPLATE.format(
        maj_v=jdk_major_for_url,
        v=JDK_VERSION,
        b=JDK_BUILD,
        arch=os_arch_info['arch'],
        os=os_arch_info['os'],
        b_flat=JDK_BUILD # Dans l'URL d'Adoptium, b_flat est souvent juste le build number
    )
    logger.info(f"URL du JDK portable construite: {jdk_url}")

    logger.info(f"Téléchargement du JDK portable depuis {jdk_url} vers {jdk_zip_target_path}...")
    downloaded_ok, _ = download_file(jdk_url, jdk_zip_target_path, description=f"JDK {JDK_VERSION}+{JDK_BUILD}")
    
    if not downloaded_ok or not jdk_zip_target_path.exists():
        logger.error(f"Échec du téléchargement du JDK portable depuis {jdk_url}.")
        return None

    logger.info(f"Décompression du JDK portable {jdk_zip_target_path} vers {portable_jdk_install_dir}...")
    try:
        # Nettoyer le répertoire d'installation avant de décompresser pour éviter les conflits
        if portable_jdk_install_dir.exists():
            for item in portable_jdk_install_dir.iterdir():
                # Ne pas supprimer le zip lui-même s'il a été téléchargé ici par erreur
                if item.resolve() == jdk_zip_target_path.resolve(): continue
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
        portable_jdk_install_dir.mkdir(parents=True, exist_ok=True) # S'assurer qu'il existe après nettoyage

        unzip_file(jdk_zip_target_path, portable_jdk_install_dir) # unzip_file supprime le zip après succès

        # Valider le JDK fraîchement décompressé
        # Le JDK peut être directement dans portable_jdk_install_dir ou dans un sous-dossier (ex: jdk-17.0.11+9)
        final_jdk_path = None
        if is_valid_jdk(portable_jdk_install_dir):
            final_jdk_path = portable_jdk_install_dir
        else:
            for item in portable_jdk_install_dir.iterdir():
                if item.is_dir() and item.name.startswith("jdk-") and is_valid_jdk(item):
                    final_jdk_path = item
                    break
        
        if final_jdk_path:
            logger.info(f"[SUCCESS] JDK portable installé et validé avec succès dans: '{final_jdk_path}'")
            return str(final_jdk_path.resolve())
        else:
            logger.error(f"L'extraction du JDK dans '{portable_jdk_install_dir}' n'a pas produit une installation valide. Contenu: {list(portable_jdk_install_dir.iterdir())}")
            return None
            
    except Exception as e_unzip:
        logger.error(f"Erreur lors de la décompression ou validation du JDK portable: {e_unzip}", exc_info=True)
        if jdk_zip_target_path.exists(): jdk_zip_target_path.unlink(missing_ok=True)
        return None

# --- Gestion du cycle de vie de la JVM ---
# (Les variables globales _JVM_INITIALIZED_THIS_SESSION etc. et les fonctions get_jvm_options, initialize_jvm, shutdown_jvm
#  seront traitées dans le prochain bloc de conflit)
# _JVM_INITIALIZED_THIS_SESSION, _JVM_WAS_SHUTDOWN, _SESSION_FIXTURE_OWNS_JVM sont définis plus haut (après la section JDK)
# ou devraient l'être. S'ils manquent, il faudra les ajouter.
# Pour l'instant, on assume qu'ils sont juste avant cette section.

_JVM_INITIALIZED_THIS_SESSION = False
_JVM_WAS_SHUTDOWN = False
_SESSION_FIXTURE_OWNS_JVM = False

def get_jvm_options() -> List[str]:
    options = [
        "-Xms64m",
        "-Xmx512m",
        "-Dfile.encoding=UTF-8",
        "-Djava.awt.headless=true"
    ]
    
    if os.name == 'nt':
        options.extend([
            "-XX:+UseG1GC",
            "-XX:+DisableExplicitGC",
            "-XX:-UsePerfData",
        ])
        # logger.warning("Options JVM Windows spécifiques temporairement désactivées pour débogage (Access Violation).")
    
    logger.info(f"Options JVM de base définies : {options}")
    return options

def initialize_jvm(
    lib_dir_path: Optional[str] = None,
    specific_jar_path: Optional[str] = None, # Conserver pour compatibilité descendante si nécessaire
    force_restart: bool = False,
    classpath: Optional[str] = None  # Nouveau paramètre pour un classpath direct
    ) -> bool:
    """
    Initialise la JVM avec le classpath configuré, si elle n'est pas déjà démarrée.
    Gère la logique de session et la possibilité de forcer un redémarrage.
    """
    import jpype
    import jpype.imports
    global _JVM_INITIALIZED_THIS_SESSION, _JVM_WAS_SHUTDOWN, _SESSION_FIXTURE_OWNS_JVM

    # --- Logging verbeux pour le débogage ---
    logger.info("="*50)
    logger.info(f"APPEL À initialize_jvm | isJVMStarted: {jpype.isJVMStarted()}, force_restart: {force_restart}")
    logger.info("="*50)

    if force_restart and jpype.isJVMStarted():
        logger.info("Forçage explicite du redémarrage de la JVM...")
        shutdown_jvm()

    if jpype.isJVMStarted():
        logger.info("La JVM est déjà démarrée. Aucune action.")
        return True

    if _JVM_WAS_SHUTDOWN:
        logger.critical("ERREUR: Tentative de redémarrage d'une JVM qui a été explicitement arrêtée. C'est une opération non supportée par JPype.")
        return False

    # --- 1. Validation de Java Home ---
    logger.info("\n--- ÉTAPE 1: RECHERCHE ET VALIDATION DE JAVA_HOME ---")
    java_home_str = find_valid_java_home()
    if not java_home_str:
        logger.critical("ÉCHEC CRITIQUE: Impossible de trouver ou d'installer un JDK valide. Démarrage JVM annulé.")
        return False
        
    os.environ['JAVA_HOME'] = java_home_str
    logger.info(f"-> JAVA_HOME positionné à : {java_home_str}")

    # --- 2. Recherche de la bibliothèque JVM (DLL/SO) ---
    logger.info("\n--- ÉTAPE 2: LOCALISATION DE LA BIBLIOTHÈQUE JVM (DLL/SO) ---")
    java_home_path = Path(java_home_str)
    
    system = platform.system()
    if system == "Windows":
        jvm_path_candidate = java_home_path / "bin" / "server" / "jvm.dll"
    elif system == "Darwin":
        jvm_pjpypeath_candidate = java_home_path / "lib" / "server" / "libjvm.dylib"
    else:
        jvm_path_candidate = java_home_path / "lib" / "server" / "libjvm.so"
    
    logger.info(f"Chemin standard candidat pour la JVM: {jvm_path_candidate}")

    if jvm_path_candidate.exists():
        jvm_path_dll_so = str(jvm_path_candidate.resolve())
        logger.info(f"-> Bibliothèque JVM trouvée et validée à l'emplacement : {jvm_path_dll_so}")
    else:
        logger.warning(f"Le chemin standard '{jvm_path_candidate}' n'existe pas. Tentative de fallback avec jpype.getDefaultJVMPath()...")
        try:
            jvm_path_dll_so = jpype.getDefaultJVMPath()
            logger.info(f"-> Succès du fallback : JPype a trouvé la JVM à '{jvm_path_dll_so}'.")
        except jpype.JVMNotFoundException:
            logger.critical(f"ÉCHEC CRITIQUE: La bibliothèque JVM est introuvable. Vérifiez l'intégrité du JDK à {java_home_str}.")
            return False

# --- 2.BIS. Nettoyage des anciens fichiers JAR verrouillés ---
    logger.info("\n--- ÉTAPE 2.BIS: NETTOYAGE DES ANCIENS JARS VERROUILLÉS (.locked) ---")
    actual_lib_dir_for_cleanup = Path(lib_dir_path) if lib_dir_path else LIBS_DIR
    locked_files = list(actual_lib_dir_for_cleanup.rglob("*.jar.locked"))
    if locked_files:
        logger.warning(f"Trouvé {len(locked_files)} fichier(s) JAR verrouillé(s) à nettoyer.")
        for f in locked_files:
            try:
                f.unlink()
                logger.info(f" -> Ancien fichier verrouillé supprimé: {f.name}")
            except OSError as e:
                logger.error(f" -> Impossible de supprimer l'ancien fichier verrouillé '{f.name}'. Il est peut-être toujours utilisé. Erreur: {e}")
    else:
        logger.info("Aucun ancien fichier .jar.locked à nettoyer.")
    # --- 3. Construction du Classpath ---
    logger.info("\n--- ÉTAPE 3: CONSTRUCTION DU CLASSPATH JAVA ---")
    jars_classpath_list: List[str] = []
    
    if classpath:
        jars_classpath_list = classpath.split(os.pathsep)
        logger.info(f"Utilisation du classpath fourni directement. Nombre d'entrées: {len(jars_classpath_list)}")
    elif specific_jar_path:
        specific_jar_file = Path(specific_jar_path)
        if specific_jar_file.is_file():
            jars_classpath_list = [str(specific_jar_file.resolve())]
            logger.info(f"Utilisation du JAR spécifique: {jars_classpath_list[0]}")
        else:
            logger.error(f"Fichier JAR spécifique fourni mais introuvable: '{specific_jar_path}'.")
            return False
    else:
        actual_lib_dir = Path(lib_dir_path) if lib_dir_path else LIBS_DIR
        logger.info(f"Recherche de JARs dans le répertoire par défaut: '{actual_lib_dir.resolve()}'")
        
        actual_lib_dir.mkdir(parents=True, exist_ok=True)

        if not _SESSION_FIXTURE_OWNS_JVM:
            logger.info("Lancement du provisioning des bibliothèques Tweety (vérification/téléchargement)...")
            if not download_tweety_jars(target_dir=actual_lib_dir):
                logger.warning("Le provisioning a signalé un problème (JARs potentiellement manquants).")
            else:
                logger.info("Provisioning terminé.")
        else:
            logger.info("Provisioning des bibliothèques géré par une fixture de session, sauté ici.")

        logger.info(f"Scan récursif (rglob) de '{actual_lib_dir.resolve()}' pour les fichiers .jar...")
        jars_classpath_list = [str(p.resolve()) for p in actual_lib_dir.rglob("*.jar")]

    if jars_classpath_list:
        logger.info(f"-> {len(jars_classpath_list)} JAR(s) trouvés pour le classpath.")
        # Afficher chaque JAR sur une nouvelle ligne pour une meilleure lisibilité
        formatted_classpath = "\n".join([f"  - {jar}" for jar in jars_classpath_list])
        logger.info(f"Classpath final à utiliser:\n{formatted_classpath}")
    else:
        logger.warning(f"-> Aucun fichier JAR trouvé. Le classpath est vide. Le démarrage de la JVM va probablement échouer.")
        return False

    # --- 4. Démarrage de la JVM ---
    logger.info("\n--- ÉTAPE 4: DÉMARRAGE DE LA JVM ---")
    jvm_options = get_jvm_options()
    logger.info(f"Options JVM: {jvm_options}")
    logger.info(f"Chemin DLL/SO: {jvm_path_dll_so}")
    logger.info(f"Classpath (brut): {os.pathsep.join(jars_classpath_list)}")
    logger.info(f"Options JVM: {jvm_options}")
    logger.info(f"Chemin DLL/SO JVM utilisé: {jvm_path_dll_so}")

    try:
        logger.info("JVM_SETUP: APPEL IMMINENT à jpype.startJVM...")
        jpype.startJVM(
            jvm_path_dll_so,
            *jvm_options,
            classpath=jars_classpath_list,
            ignoreUnrecognized=True,
            convertStrings=False
        )
        logger.info("JVM_SETUP: RETOUR de jpype.startJVM. Le blocage n'a pas eu lieu.")
        _JVM_INITIALIZED_THIS_SESSION = True
        _JVM_WAS_SHUTDOWN = False
        logger.info("[SUCCESS] JVM démarrée avec succès.")
        return True
    except Exception as e:
        logger.error(f"JVM_SETUP: EXCEPTION lors de jpype.startJVM: {e}", exc_info=True)
        logger.error(f"Erreur fatale lors du démarrage de la JVM: {e}", exc_info=True)
        _JVM_INITIALIZED_THIS_SESSION = False
        return False

def shutdown_jvm():
    global _JVM_INITIALIZED_THIS_SESSION, _JVM_WAS_SHUTDOWN, _SESSION_FIXTURE_OWNS_JVM
    
    if _SESSION_FIXTURE_OWNS_JVM and jpype.isJVMStarted():
        logger.info("Arrêt de la JVM contrôlé par la fixture de session, ne rien faire ici explicitement.")
        # La fixture devrait gérer la réinitialisation des états si nécessaire.
        return

    import jpype
    if jpype.isJVMStarted():
        logger.info("Arrêt de la JVM...")
        jpype.shutdownJVM()
        logger.info("JVM arrêtée.")
    else:
        logger.debug("La JVM n'est pas en cours d'exécution, aucun arrêt nécessaire.")
    
    _JVM_INITIALIZED_THIS_SESSION = False
    _JVM_WAS_SHUTDOWN = True

def is_jvm_owned_by_session_fixture() -> bool:
    """Retourne True si la JVM est contrôlée par une fixture de session pytest."""
    # Cette fonction permet d'éviter l'import direct d'une variable privée
    global _SESSION_FIXTURE_OWNS_JVM
    return _SESSION_FIXTURE_OWNS_JVM

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    main_logger = logging.getLogger(__name__)

    main_logger.info("--- Démonstration du module jvm_setup ---")
    try:
        main_logger.info("\n1. Première tentative de démarrage de la JVM...")
        if initialize_jvm():
            main_logger.info("\n2. Tentative de démarrage redondante (devrait être ignorée)...")
            initialize_jvm()

            try:
                import jpype
                JString = jpype.JClass("java.lang.String")
                my_string = JString("Ceci est un test depuis Python!")
                main_logger.info(f"Test Java réussi: {my_string}")
            except Exception as e_java_test:
                main_logger.error(f"Le test d'importation Java a échoué: {e_java_test}")
        else:
            main_logger.error("Échec du premier démarrage de la JVM. Démonstration interrompue.")

    except Exception as e_demo:
        main_logger.error(f"Une erreur est survenue durant la démonstration : {e_demo}", exc_info=True)

    finally:
        main_logger.info("\n3. Arrêt de la JVM...")
        shutdown_jvm()
        main_logger.info("\n--- Fin de la démonstration ---")
