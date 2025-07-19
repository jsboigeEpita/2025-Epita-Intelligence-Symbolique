# core/jvm_setup.py
import os
import jpype
import jpype.imports
import logging
import threading
from pathlib import Path
from typing import List, Optional

from argumentation_analysis.config.settings import settings

# Configuration du logger pour ce module
logger = logging.getLogger("Orchestration.JPype")

# Verrou global pour rendre l'initialisation de la JVM thread-safe
_jvm_lock = threading.Lock()

# core/jvm_setup.py
import os
import jpype
import jpype.imports
import logging
import threading
import platform
import re
import requests
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import List, Optional, Dict
from tqdm.auto import tqdm

from argumentation_analysis.config.settings import settings

# Configuration du logger pour ce module
logger = logging.getLogger("Orchestration.JPype")

# Verrou global pour rendre l'initialisation de la JVM thread-safe
_jvm_lock = threading.Lock()

# --- Gestion d'état de la JVM (depuis la branche feature) ---
_JVM_INITIALIZED_THIS_SESSION = False
_JVM_WAS_SHUTDOWN = False
_SESSION_FIXTURE_OWNS_JVM = False


def get_project_root_robust() -> Path:
    """
    Trouve la racine du projet en remontant depuis l'emplacement de ce fichier.
    """
    current_path = Path(__file__).resolve()
    project_root = current_path.parents[2]
    logger.debug(f"Racine du projet déterminée de manière statique à : {project_root}")
    return project_root

PROJ_ROOT = get_project_root_robust()
LIBS_DIR = PROJ_ROOT / settings.jvm.tweety_libs_dir
TWEETY_VERSION = settings.jvm.tweety_version
MIN_JAVA_VERSION = settings.jvm.min_java_version
JDK_VERSION = settings.jvm.jdk_version
JDK_BUILD = settings.jvm.jdk_build
JDK_URL_TEMPLATE = settings.jvm.jdk_url_template


class TqdmUpTo(tqdm):
    """Provides `update_to(block_num, block_size, total_size)`."""
    def update_to(self, b=1, bsize=1, tsize=None):
         if tsize is not None: self.total = tsize
         self.update(b * bsize - self.n)

def get_os_arch_for_jdk() -> Dict[str, str]:
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
    if description is None:
        description = dest_path.name
    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        if dest_path.exists() and dest_path.stat().st_size > 0:
            logger.debug(f"Fichier '{dest_path.name}' déjà présent et non vide. Skip.")
            return True, False
        logger.info(f"Tentative de téléchargement: {url} vers {dest_path}")
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, stream=True, timeout=30, headers=headers, allow_redirects=True)
        if response.status_code == 404:
             logger.error(f"❌ Fichier non trouvé (404) à l'URL: {url}")
             return False, False
        response.raise_for_status()
        total_size = int(response.headers.get('content-length', 0))
        with TqdmUpTo(unit='B', unit_scale=True, unit_divisor=1024, total=total_size, miniters=1, desc=description[:40]) as t:
            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        t.update(len(chunk))
        if dest_path.exists() and dest_path.stat().st_size > 0:
            if total_size != 0 and dest_path.stat().st_size != total_size:
                 logger.warning(f"⚠️ Taille du fichier téléchargé '{dest_path.name}' ({dest_path.stat().st_size}) "
                                f"ne correspond pas à la taille attendue ({total_size}).")
            logger.info(f" -> Téléchargement de '{dest_path.name}' réussi.")
            return True, True
        else:
            logger.error(f"❓ Téléchargement de '{dest_path.name}' semblait terminé mais fichier vide ou absent.")
            if dest_path.exists(): dest_path.unlink(missing_ok=True)
            return False, False
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Échec connexion/téléchargement pour '{dest_path.name}': {e}")
        if dest_path.exists(): dest_path.unlink(missing_ok=True)
        return False, False
    except Exception as e_other:
        logger.error(f"❌ Erreur inattendue pendant téléchargement de '{dest_path.name}': {e_other}", exc_info=True)
        if dest_path.exists(): dest_path.unlink(missing_ok=True)
        return False, False

def download_tweety_jars(version: str = TWEETY_VERSION, target_dir: Optional[Path] = None) -> bool:
    logger.info(f"--- Démarrage de la vérification/téléchargement des JARs Tweety v{version} ---")
    target_dir_path = Path(target_dir) if target_dir else LIBS_DIR
    target_dir_path.mkdir(parents=True, exist_ok=True)
    jar_filename = f"org.tweetyproject.tweety-full-{version}-with-dependencies.jar"
    jar_url = f"https://tweetyproject.org/builds/{version}/{jar_filename}"
    jar_target_path = target_dir_path / jar_filename
    logger.info(f"Vérification de la présence de: {jar_target_path}")
    if jar_target_path.exists() and jar_target_path.stat().st_size > 0:
        logger.info(f"JAR Core '{jar_filename}': déjà présent.")
        logger.info("--- Fin de la vérification/téléchargement des JARs Tweety ---")
        return True
    logger.info(f"JAR '{jar_filename}' non trouvé ou vide. Tentative de téléchargement...")
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
    logger.info(f"Décompression de {zip_path} vers {dest_dir}...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            top_level_contents = {Path(f).parts[0] for f in file_list}
            if len(file_list) > 0 and len(top_level_contents) == 1:
                single_root_dir_in_zip_name = top_level_contents.pop()
                if all(f.startswith(single_root_dir_in_zip_name + os.sep) or f == single_root_dir_in_zip_name for f in file_list if f):
                    temp_extract_dir = dest_dir.parent / (dest_dir.name + "_temp_extract_strip")
                    if temp_extract_dir.exists():
                        shutil.rmtree(temp_extract_dir)
                    temp_extract_dir.mkdir(parents=True, exist_ok=True)
                    zip_ref.extractall(temp_extract_dir)
                    source_dir_to_move_from = temp_extract_dir / single_root_dir_in_zip_name
                    if dest_dir.resolve() != source_dir_to_move_from.resolve():
                        for item in dest_dir.iterdir():
                            if item.is_dir():
                                shutil.rmtree(item)
                            else:
                                item.unlink()
                    else:
                        logger.warning("Le répertoire de destination est le même que le répertoire source temporaire.")
                    for item in source_dir_to_move_from.iterdir():
                        shutil.move(str(item), str(dest_dir / item.name))
                    shutil.rmtree(temp_extract_dir)
                    logger.info(f"Contenu de '{single_root_dir_in_zip_name}' extrait et déplacé vers '{dest_dir}'.")
                else:
                    zip_ref.extractall(dest_dir)
                    logger.info("Extraction standard effectuée (pas de strip de dossier racine).")
            else:
                 zip_ref.extractall(dest_dir)
                 logger.info("Extraction standard effectuée (contenu à la racine ou multiple).")
        if zip_path.exists():
            zip_path.unlink()
        logger.info("Décompression terminée.")
    except (zipfile.BadZipFile, IOError, shutil.Error) as e:
        logger.error(f"Erreur lors de la décompression de {zip_path}: {e}", exc_info=True)
        if dest_dir.exists():
            shutil.rmtree(dest_dir, ignore_errors=True)
            dest_dir.mkdir(parents=True, exist_ok=True)
        raise

PORTABLE_JDK_DIR_NAME = "portable_jdk"
TEMP_DIR_NAME = "_temp_jdk_download"

def get_project_root() -> Path:
    return PROJ_ROOT

def is_valid_jdk(path: Path) -> bool:
    if not path.is_dir():
        return False
    java_exe = path / "bin" / ("java.exe" if platform.system() == "Windows" else "java")
    if not java_exe.is_file():
        logger.debug(f"Validation JDK: 'java' non trouvé ou n'est pas un fichier dans {path / 'bin'}")
        return False
    try:
        result = subprocess.run([str(java_exe), "-version"], capture_output=True, text=True, check=False)
        version_output = result.stderr if result.stderr else result.stdout
        if not version_output:
            logger.warning(f"Impossible d'obtenir la sortie de version pour le JDK à {path}. stderr: {result.stderr}, stdout: {result.stdout}")
            return False
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
        if major_version == 1 and minor_version_str:
            major_version = int(minor_version_str)
        try:
            raw_version_detail = match.group(0).split('"')[1]
        except IndexError:
            logger.error(f"Impossible d'extraire le numéro de version de '{match.group(0)}'.")
            raw_version_detail = "FORMAT_INCONNU"
        version_details_str = raw_version_detail.replace('\\', '\\\\')
        if major_version >= MIN_JAVA_VERSION:
            logger.info(f"Version Java détectée à '{path}': \"{version_details_str}\" (Majeure: {major_version}) -> Valide.")
            return True
        else:
            logger.warning(f"Version Java détectée à '{path}': \"{version_details_str}\" (Majeure: {major_version}) -> INVALIDE (minimum requis: {MIN_JAVA_VERSION}).")
            return False
    except FileNotFoundError:
        logger.error(f"Exécutable Java non trouvé à {java_exe}.")
        return False
    except Exception as e:
        logger.error(f"Erreur lors de la validation du JDK à {path}: {e}", exc_info=True)
        return False

def find_existing_jdk() -> Optional[Path]:
    logger.debug("Recherche d'un JDK portable pré-existant valide (JAVA_HOME est ignoré).")
    project_r = get_project_root()
    portable_jdk_dir = project_r / PORTABLE_JDK_DIR_NAME
    if portable_jdk_dir.is_dir():
        if is_valid_jdk(portable_jdk_dir):
             logger.info(f"JDK portable validé directement dans : {portable_jdk_dir}")
             return portable_jdk_dir
        for item in portable_jdk_dir.iterdir():
            if item.is_dir() and item.name.startswith("jdk-"):
                if is_valid_jdk(item):
                    logger.info(f"JDK portable validé dans sous-dossier : {item}")
                    return item
    logger.info("Aucun JDK pré-existant valide trouvé. Le téléchargement va être tenté.")
    return None

def find_valid_java_home() -> Optional[str]:
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
        logger.error(f"Impossible de créer les répertoires pour JDK portable: {e}")
        return None
    os_arch_info = get_os_arch_for_jdk()
    jdk_major_for_url = JDK_VERSION.split('.')[0]
    generic_zip_name = f"portable_jdk_{JDK_VERSION}_{JDK_BUILD}_{os_arch_info['os']}_{os_arch_info['arch']}.zip"
    jdk_zip_target_path = temp_download_dir / generic_zip_name
    jdk_url = JDK_URL_TEMPLATE.format(
        maj_v=jdk_major_for_url, v=JDK_VERSION, b=JDK_BUILD, arch=os_arch_info['arch'],
        os=os_arch_info['os'], b_flat=JDK_BUILD
    )
    logger.info(f"URL du JDK portable construite: {jdk_url}")
    logger.info(f"Téléchargement du JDK portable depuis {jdk_url} vers {jdk_zip_target_path}...")
    downloaded_ok, _ = download_file(jdk_url, jdk_zip_target_path, description=f"JDK {JDK_VERSION}+{JDK_BUILD}")
    if not downloaded_ok or not jdk_zip_target_path.exists():
        logger.error(f"Échec du téléchargement du JDK portable.")
        return None
    logger.info(f"Décompression du JDK portable...")
    try:
        unzip_file(jdk_zip_target_path, portable_jdk_install_dir)
        final_jdk_path = None
        if is_valid_jdk(portable_jdk_install_dir):
            final_jdk_path = portable_jdk_install_dir
        else:
            for item in portable_jdk_install_dir.iterdir():
                if item.is_dir() and item.name.startswith("jdk-") and is_valid_jdk(item):
                    final_jdk_path = item
                    break
        if final_jdk_path:
            logger.info(f"[SUCCESS] JDK portable installé et validé: '{final_jdk_path}'")
            return str(final_jdk_path.resolve())
        else:
            logger.error(f"L'extraction du JDK dans '{portable_jdk_install_dir}' n'a pas produit une installation valide.")
            return None
    except Exception as e_unzip:
        logger.error(f"Erreur lors de la décompression ou validation du JDK portable: {e_unzip}", exc_info=True)
        if jdk_zip_target_path.exists(): jdk_zip_target_path.unlink(missing_ok=True)
        return None

def get_jvm_options() -> List[str]:
    """
    Retourne une liste d'options JVM optimisées.
    """
    options = [
        f"-Xms{settings.jvm.min_heap_size}",
        f"-Xmx{settings.jvm.max_heap_size}",
        "-Dfile.encoding=UTF-8",
        # "-Djava.awt.headless=true" # Cette option cause un "Windows fatal exception: access violation"
                                     # sur certaines configurations Windows. Elle est désactivée.
    ]
    # Les options "-XX:+UseG1GC", "-Xrs" sur Windows provoquaient un "fatal exception: access violation".
    # Elles sont désactivées de manière permanente.

    # --- DIAGNOSTIC PROVER9 (Temporarily disabled for debugging JVM crash) ---
    logger.warning("Le diagnostic Prover9 et le chargement de la librairie native sont temporairement désactivés.")
    logger.info(f"Options JVM utilisées : {options}")
    return options

def initialize_jvm(session_fixture_owns_jvm=False) -> bool:
    global _JVM_INITIALIZED_THIS_SESSION, _SESSION_FIXTURE_OWNS_JVM
    with _jvm_lock:
        _SESSION_FIXTURE_OWNS_JVM = session_fixture_owns_jvm
        logger.info("=" * 50)
        logger.info(f"APPEL À initialize_jvm (Propriétaire de session: {_SESSION_FIXTURE_OWNS_JVM})")
        if jpype.isJVMStarted():
            logger.info("La JVM est déjà démarrée.")
            return True
        if _JVM_WAS_SHUTDOWN:
            logger.critical("La JVM a déjà été arrêtée. Le redémarrage n'est pas supporté.")
            return False
        
        # Provisioning des dépendances
        if not download_tweety_jars():
            return False
        
        java_home = find_valid_java_home()
        if not java_home:
            return False
        os.environ['JAVA_HOME'] = java_home


        # Construction du Classpath
        tweety_libs_dir = PROJ_ROOT / settings.jvm.tweety_libs_dir
        uber_jars = [jar for jar in tweety_libs_dir.glob("*.jar") if "full" in jar.name.lower()]
        if uber_jars:
            classpath = [str(uber_jars[0].resolve())]
        else:
            logger.warning(f"Aucun uber-jar trouvé, chargement de tous les JARs.")
            classpath = [str(jar.resolve()) for jar in tweety_libs_dir.glob("*.jar")]
            if not classpath:
                logger.critical(f"Aucun JAR trouvé dans {tweety_libs_dir}.")
                return False
        
        # Démarrage de la JVM
        try:
            jvm_path = jpype.getDefaultJVMPath()
            jvm_options = get_jvm_options()
            
            # --- AJOUT DE LOGS DE DÉBOGAGE CRITIQUES ---
            logger.info("="*20 + " DIAGNOSTIC DÉMARRAGE JVM " + "="*20)
            logger.info(f"Chemin JVM (jpype.getDefaultJVMPath): {jvm_path}")
            logger.info(f"Options JVM finales: {jvm_options}")
            logger.info(f"Classpath final: {classpath}")
            logger.info("="*71)
            # --- FIN DES LOGS ---

            logger.info("Tentative de démarrage de la JVM...")
            jpype.startJVM(
                jvm_path,
                *jvm_options,
                classpath=classpath,
                ignoreUnrecognized=True,
                convertStrings=False
            )
            logger.info("[SUCCESS] JVM démarrée.")
            _JVM_INITIALIZED_THIS_SESSION = True
            return True
        except Exception as e:
            logger.critical(f"Échec critique du démarrage de la JVM: {e}", exc_info=True)
            return False

def shutdown_jvm(called_by_session_fixture=False):
    global _JVM_WAS_SHUTDOWN
    with _jvm_lock:
        if not jpype.isJVMStarted():
            return
        if _SESSION_FIXTURE_OWNS_JVM and not called_by_session_fixture:
            logger.warning("Arrêt de la JVM demandé, mais elle est gérée par une fixture de session.")
            return
        logger.info("Tentative d'arrêt de la JVM...")
        try:
            jpype.shutdownJVM()
            logger.info("[SUCCESS] JVM arrêtée.")
            _JVM_WAS_SHUTDOWN = True
        except Exception as e:
            logger.error(f"Erreur lors de l'arrêt de la JVM: {e}", exc_info=True)
            _JVM_WAS_SHUTDOWN = True

def is_jvm_started() -> bool:
    try:
        return jpype.isJVMStarted()
    except Exception:
        return False

def is_jvm_owned_by_session_fixture() -> bool:
    return _SESSION_FIXTURE_OWNS_JVM

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    print("Ce script n'est pas conçu pour être exécuté directement.")
