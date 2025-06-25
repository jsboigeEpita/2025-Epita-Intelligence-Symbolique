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
import threading

from argumentation_analysis.config.settings import settings

# Configuration du logger pour ce module
logger = logging.getLogger("Orchestration.JPype")

# Verrou global pour rendre l'initialisation de la JVM thread-safe
_jvm_lock = threading.Lock()

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
    """
    Construit une liste d'options JVM standard pour la stabilité et la performance.
    """
    options = [
        "-Xmx4096m",              # Augmentation de la mémoire maximale à 4 Go
        "-Xms512m",               # Mémoire initiale
        "-XX:+UseG1GC",             # Utilisation du G1 Garbage Collector
        "-XX:MaxGCPauseMillis=200", # Objectif de pause pour le GC
        "-Dfile.encoding=UTF-8",    # Encodage des fichiers
        "-Djava.awt.headless=true"  # Mode Headless pour les environnements sans UI
    ]
    logger.info(f"Options JVM configurées: {options}")
    return options

def initialize_jvm(force_redownload_jars=False, session_fixture_owns_jvm=False) -> bool:
    """
    Initialise et démarre la JVM avec les JARs et la configuration nécessaires.
    """
    global _JVM_INITIALIZED_THIS_SESSION, _SESSION_FIXTURE_OWNS_JVM
    import jpype
    import jpype.imports

    _SESSION_FIXTURE_OWNS_JVM = session_fixture_owns_jvm
    logger.info("=" * 50)
    logger.info("APPEL À initialize_jvm")
    logger.info(f"Propriétaire de la session JVM: {_SESSION_FIXTURE_OWNS_JVM}")

    if jpype.isJVMStarted():
        logger.info("La JVM est déjà démarrée. Aucune action n'est requise.")
        return True

    if _JVM_WAS_SHUTDOWN and not _SESSION_FIXTURE_OWNS_JVM:
        logger.warning(
            "La JVM a déjà été démarrée et arrêtée dans cette session."
            "Le redémarrage n'est pas supporté et peut entraîner une instabilité."
        )

    # ... (Le reste de la logique reste le même)
    if not download_tweety_jars():
        logger.critical("Échec du provisionnement des JARs Tweety.")
        return False

    java_home = find_valid_java_home()
    if not java_home:
        logger.critical("Impossible de trouver un JDK valide.")
        return False
    os.environ['JAVA_HOME'] = java_home

    # Déterminer le chemin de la JVM de manière déterministe au lieu de se fier à la magie.
    # C'est la correction la plus critique pour éviter les "access violation".
    system = platform.system()
    if system == "Windows":
        jvm_path = Path(java_home) / "bin" / "server" / "jvm.dll"
    elif system == "Linux":
        jvm_path = Path(java_home) / "lib" / "server" / "libjvm.so"
    elif system == "Darwin": # macOS
        jvm_path = Path(java_home) / "lib" / "server" / "libjvm.dylib"
    else:
        logger.critical(f"Système d'exploitation non supporté pour la construction du chemin JVM: {system}")
        return False

    if not jvm_path.exists():
        logger.critical(f"Le chemin de la librairie JVM construit n'existe pas : {jvm_path}")
        return False
        
    logger.info(f"Utilisation du chemin de la librairie JVM explicite : {jvm_path}")
    
    all_jars = [str(p.resolve()) for p in LIBS_DIR.glob("*.jar")]
    if not all_jars:
        logger.critical(f"Aucun fichier .jar trouvé dans {LIBS_DIR}.")
        return False
        
    jvm_options = get_jvm_options()
    
    try:
        logger.info("Tentative de démarrage de la JVM...")
        # Vérification explicite de l'existence et des permissions des JARs
        all_jars_paths = [p.resolve() for p in LIBS_DIR.glob("*.jar")]
        if not all_jars_paths:
            logger.critical(f"Aucun fichier .jar trouvé dans {LIBS_DIR}.")
            return False

        classpath_list = []
        for jar_path in all_jars_paths:
            if not jar_path.exists():
                logger.error(f"Erreur Classpath: Le fichier JAR '{jar_path}' n'existe pas.")
                return False
            try:
                # Vérifier si on peut au moins lire le fichier
                with open(jar_path, 'rb') as f:
                    f.read(1)
                classpath_list.append(str(jar_path))
            except IOError as e:
                logger.error(f"Erreur Classpath: Impossible de lire le fichier JAR '{jar_path}'. Erreur: {e}")
                return False
        
        logger.info(f"Classpath final validé: {classpath_list}")
        
        jpype.startJVM(
            str(jvm_path), # Conversion explicite en string pour compatibilité maximale
            *jvm_options,
            classpath=classpath_list, # Utiliser la liste de strings validée
            ignoreUnrecognized=True,
            convertStrings=False
        )
        logger.info("[SUCCESS] JVM démarrée avec succès.")
        _JVM_INITIALIZED_THIS_SESSION = True
        return True
    except Exception as e:
        logger.critical(f"Échec du démarrage de la JVM: {e}", exc_info=True)
        return False

def shutdown_jvm():
    """Arrête la JVM si elle a été démarrée par ce processus."""
    global _JVM_INITIALIZED_THIS_SESSION, _JVM_WAS_SHUTDOWN
    import jpype
    if jpype.isJVMStarted():
        # Seul le thread qui a démarré la JVM peut l'arrêter.
        # On ne vérifie pas `_JVM_INITIALIZED_THIS_SESSION` car si la fixture
        # de session possède la JVM, cette variable sera False mais l'arrêt
        # doit quand même se faire à la fin de la session.
        logger.info("Arrêt de la JVM...")
        jpype.shutdownJVM()
        logger.info("JVM arrêtée.")
        _JVM_WAS_SHUTDOWN = True
        _JVM_INITIALIZED_THIS_SESSION = False
    else:
        logger.debug("La JVM n'est pas en cours d'exécution, aucun arrêt nécessaire.")


def is_jvm_started() -> bool:
    """
    Vérifie si la JVM est actuellement démarrée, en gérant l'import de jpype.
    """
    try:
        import jpype
        return jpype.isJVMStarted()
    except ImportError:
        # Si jpype n'est pas installé ou trouvable, la JVM ne peut pas être démarrée.
        return False
    except Exception as e:
        logger.error(f"Erreur inattendue lors de la vérification du statut de la JVM: {e}")
        return False


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
