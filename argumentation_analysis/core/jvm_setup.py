# core/jvm_setup.py
import os
import sys
import jpype
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

# Configuration du logger pour ce module
logger = logging.getLogger("Orchestration.JPype")

# --- Fonctions de téléchargement et de provisioning (issues du stash de HEAD) ---

class TqdmUpTo(tqdm):
    """Provides `update_to(block_num, block_size, total_size)`."""
    def update_to(self, b=1, bsize=1, tsize=None):
         if tsize is not None: self.total = tsize
         self.update(b * bsize - self.n)

def _download_file_with_progress(file_url: str, target_path: Path, description: str):
    """Télécharge un fichier depuis une URL vers un chemin cible avec une barre de progression."""
    try:
        if target_path.exists() and target_path.stat().st_size > 0:
            logger.debug(f"Fichier '{target_path.name}' déjà présent et non vide. Skip.")
            return True, False
        logger.info(f"Tentative de téléchargement: {file_url} vers {target_path}")
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(file_url, stream=True, timeout=15, headers=headers, allow_redirects=True)
        if response.status_code == 404:
             logger.error(f"❌ Fichier non trouvé (404) à l'URL: {file_url}")
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
            logger.error(f"❓ Téléchargement de '{target_path.name}' semblait terminé mais fichier vide ou absent.")
            if target_path.exists(): target_path.unlink(missing_ok=True)
            return False, False
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Échec connexion/téléchargement pour '{target_path.name}': {e}")
        if target_path.exists(): target_path.unlink(missing_ok=True)
        return False, False
    except Exception as e_other:
        logger.error(f"❌ Erreur inattendue pour '{target_path.name}': {e_other}", exc_info=True)
        if target_path.exists(): target_path.unlink(missing_ok=True)
        return False, False

def get_project_root_for_libs() -> Path: # Renamed to avoid conflict if get_project_root is defined elsewhere
    return Path(__file__).resolve().parents[3]

def find_libs_dir() -> Optional[Path]:
    proj_root_temp = get_project_root_for_libs()
    libs_dir_temp = proj_root_temp / "libs"
    libs_dir_temp.mkdir(parents=True, exist_ok=True)
    return libs_dir_temp

def download_tweety_jars(
    version: str = "1.28",
    target_dir: str = None,
    native_subdir: str = "native"
    ) -> bool:
    """
    Vérifie et télécharge les JARs Tweety (Core + Modules) et les binaires natifs nécessaires.
    """
    if target_dir is None:
        target_dir_path = find_libs_dir()
        if not target_dir_path:
            logger.critical("Impossible de trouver le répertoire des bibliothèques pour y télécharger les JARs.")
            return False
    else:
        target_dir_path = Path(target_dir)

    logger.info(f"\n--- Vérification/Téléchargement des JARs Tweety v{version} ---")
    BASE_URL = f"https://tweetyproject.org/builds/{version}/"
    LIB_DIR = target_dir_path
    NATIVE_LIBS_DIR = LIB_DIR / native_subdir
    LIB_DIR.mkdir(exist_ok=True)
    NATIVE_LIBS_DIR.mkdir(exist_ok=True)

    CORE_JAR_NAME = f"org.tweetyproject.tweety-full-{version}-with-dependencies.jar"
    REQUIRED_MODULES = sorted([
        "arg.adf", "arg.aba", "arg.bipolar", "arg.aspic", "arg.dung", "arg.weighted",
        "arg.social", "arg.setaf", "arg.rankings", "arg.prob", "arg.extended",
        "arg.delp", "arg.deductive", "arg.caf",
        "beliefdynamics", "agents.dialogues", "action",
        "logics.pl", "logics.fol", "logics.ml", "logics.dl", "logics.cl",
        "logics.qbf", "logics.pcl", "logics.rcl", "logics.rpcl", "logics.mln", "logics.bpm",
        "lp.asp",
        "math", "commons", "agents"
    ])
    system = platform.system()
    native_binaries_repo_path = "https://raw.githubusercontent.com/TweetyProjectTeam/TweetyProject/main/org-tweetyproject-arg-adf/src/main/resources/"
    native_binaries = {
        "Windows": ["picosat.dll", "lingeling.dll", "minisat.dll"],
        "Linux":   ["picosat.so", "lingeling.so", "minisat.so"],
        "Darwin":  ["picosat.dylib", "lingeling.dylib", "minisat.dylib"]
    }.get(system, [])

    logger.info(f"Vérification de l'accès à {BASE_URL}...")
    url_accessible = False
    try:
        response = requests.head(BASE_URL, timeout=10)
        response.raise_for_status()
        logger.info(f"✔️ URL de base Tweety v{version} accessible.")
        url_accessible = True
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Impossible d'accéder à l'URL de base {BASE_URL}. Erreur : {e}")
        logger.warning("   Le téléchargement des JARs/binaires manquants échouera. Seuls les fichiers locaux seront utilisables.")

    logger.info(f"\n--- Vérification/Téléchargement JAR Core ---")
    core_present, core_new = _download_file_with_progress(BASE_URL + CORE_JAR_NAME, LIB_DIR / CORE_JAR_NAME, CORE_JAR_NAME)
    status_core = "téléchargé" if core_new else ("déjà présent" if core_present else "MANQUANT")
    logger.info(f"✔️ JAR Core '{CORE_JAR_NAME}': {status_core}.")
    if not core_present:
        logger.critical(f"❌ ERREUR CRITIQUE : Le JAR core est manquant et n'a pas pu être téléchargé.")
        return False

    logger.info(f"\n--- Vérification/Téléchargement des {len(REQUIRED_MODULES)} JARs de modules ---")
    modules_present_count = 0
    modules_downloaded_count = 0
    modules_missing = []
    for module_name in tqdm(REQUIRED_MODULES, desc="Modules JARs"):
        module_jar_name = f"org.tweetyproject.{module_name}-{version}-with-dependencies.jar"
        present, new_dl = _download_file_with_progress(BASE_URL + module_jar_name, LIB_DIR / module_jar_name, module_jar_name)
        if present:
            modules_present_count += 1
            if new_dl: modules_downloaded_count += 1
        elif url_accessible:
             modules_missing.append(module_name)
    logger.info(f"-> Modules: {modules_downloaded_count} téléchargés, {modules_present_count}/{len(REQUIRED_MODULES)} présents.")
    if modules_missing:
        logger.warning(f"   Modules potentiellement manquants (non trouvés ou erreur DL): {', '.join(modules_missing)}")

    logger.info(f"\n--- Vérification/Téléchargement des {len(native_binaries)} binaires natifs ({system}) ---")
    native_present_count = 0
    native_downloaded_count = 0
    native_missing = []
    if not native_binaries:
         logger.info(f"   (Aucun binaire natif connu pour {system})")
    else:
        for name in tqdm(native_binaries, desc="Binaires Natifs"):
             present, new_dl = _download_file_with_progress(native_binaries_repo_path + name, NATIVE_LIBS_DIR / name, name)
             if present:
                 native_present_count += 1
                 if new_dl: native_downloaded_count += 1
                 if new_dl and system != "Windows":
                     try:
                         target_path_native = NATIVE_LIBS_DIR / name
                         current_permissions = target_path_native.stat().st_mode
                         target_path_native.chmod(current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                         logger.debug(f"      Permissions d'exécution ajoutées à {name}")
                     except Exception as e_chmod:
                         logger.warning(f"      Impossible d'ajouter les permissions d'exécution à {name}: {e_chmod}")
             elif url_accessible:
                  native_missing.append(name)
        logger.info(f"-> Binaires natifs: {native_downloaded_count} téléchargés, {native_present_count}/{len(native_binaries)} présents.")
        if native_missing:
            logger.warning(f"   Binaires natifs potentiellement manquants: {', '.join(native_missing)}")
        if native_present_count > 0:
             logger.info(f"   Note: S'assurer que le chemin '{NATIVE_LIBS_DIR.resolve()}' est inclus dans java.library.path lors du démarrage JVM.")
    logger.info("--- Fin Vérification/Téléchargement Tweety ---")
    return core_present and modules_present_count > 0


PORTABLE_JDK_DIR_NAME = "portable_jdk"
PORTABLE_JDK_ZIP_NAME = "OpenJDK17U-jdk_x64_windows_hotspot_17.0.15_6_new.zip"
TEMP_DIR_NAME = "_temp"

def get_project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _extract_portable_jdk(project_root: Path, portable_jdk_parent_dir: Path, portable_jdk_zip_path: Path) -> Optional[Path]:
    logger.info(f"Tentative d'extraction du JDK portable depuis '{portable_jdk_zip_path}' vers '{portable_jdk_parent_dir}'...")
    try:
        with zipfile.ZipFile(portable_jdk_zip_path, 'r') as zip_ref:
            zip_ref.extractall(portable_jdk_parent_dir)
        logger.info(f"JDK portable extrait avec succès dans '{portable_jdk_parent_dir}'.")
        for item in portable_jdk_parent_dir.iterdir():
            if item.is_dir() and item.name.startswith("jdk-"):
                logger.info(f"Dossier racine du JDK portable détecté : '{item}'")
                return item
        logger.warning(f"Impossible de déterminer le dossier racine du JDK dans '{portable_jdk_parent_dir}' après extraction.")
        extracted_items = [d for d in portable_jdk_parent_dir.iterdir() if d.is_dir()]
        if len(extracted_items) == 1:
            logger.info(f"Un seul dossier trouvé après extraction: '{extracted_items[0]}', en supposant que c'est le JDK.")
            return extracted_items[0]
        return None
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction du JDK portable: {e}", exc_info=True)
        return None

def find_jdk_path() -> Optional[Path]:
    project_root = get_project_root()
    _PORTABLE_JDK_PATH: Optional[Path] = None

    java_home_env = os.environ.get("JAVA_HOME")
    if java_home_env:
        logger.info(f"Variable JAVA_HOME trouvée : {java_home_env}")
        potential_path = Path(java_home_env)
        if potential_path.is_dir():
            java_exe_in_java_home = potential_path / "bin" / f"java{'.exe' if os.name == 'nt' else ''}"
            if java_exe_in_java_home.is_file():
                logger.info(f"(OK) JDK détecté via JAVA_HOME et validé : {potential_path}")
                return potential_path
            else:
                logger.warning(f"(ATTENTION) JAVA_HOME pointe vers un répertoire sans java exécutable valide: {potential_path}")
        else:
            logger.warning(f"(ATTENTION) JAVA_HOME défini mais répertoire inexistant : {potential_path}")

    portable_jdk_root_dir_check = project_root / PORTABLE_JDK_DIR_NAME
    if portable_jdk_root_dir_check.is_dir():
        for item in portable_jdk_root_dir_check.iterdir():
            if item.is_dir() and item.name.startswith("jdk-"):
                java_exe_portable = item / "bin" / f"java{'.exe' if os.name == 'nt' else ''}"
                if java_exe_portable.is_file():
                    logger.info(f"(OK) JDK portable détecté via chemin par défaut : {item}")
                    return item
    
    logger.warning(f"(ATTENTION) JDK portable non trouvé à l'emplacement par défaut : {portable_jdk_root_dir_check}")
    return None


def find_valid_java_home() -> Optional[str]:
    logger.debug("Début recherche répertoire Java Home valide...")
    
    project_root = get_project_root()
    portable_jdk_parent_dir = project_root / PORTABLE_JDK_DIR_NAME
    portable_jdk_zip_path = project_root / TEMP_DIR_NAME / PORTABLE_JDK_ZIP_NAME
    PORTABLE_JDK_DOWNLOAD_URL = "https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.15%2B6/OpenJDK17U-jdk_x64_windows_hotspot_17.0.15_6.zip"
    
    potential_jdk_root_dir = None
    if portable_jdk_parent_dir.is_dir():
        for item in portable_jdk_parent_dir.iterdir():
            if item.is_dir() and item.name.startswith("jdk-"):
                java_exe_portable = item / "bin" / f"java{'.exe' if os.name == 'nt' else ''}"
                if java_exe_portable.is_file():
                    logger.info(f"JDK portable trouvé et valide dans: '{item}'")
                    potential_jdk_root_dir = item
                    break
    
    if potential_jdk_root_dir:
        logger.info(f"🎉 Utilisation du JDK portable intégré: '{potential_jdk_root_dir}'")
        return str(potential_jdk_root_dir.resolve())

    if portable_jdk_zip_path.is_file():
        extracted_jdk_root = _extract_portable_jdk(project_root, portable_jdk_parent_dir, portable_jdk_zip_path)
        if extracted_jdk_root and (extracted_jdk_root / "bin" / f"java{'.exe' if os.name == 'nt' else ''}").is_file():
            return str(extracted_jdk_root.resolve())
    else:
        logger.info(f"Archive ZIP du JDK portable non trouvée. Tentative de téléchargement...")
        temp_dir = project_root / TEMP_DIR_NAME
        temp_dir.mkdir(parents=True, exist_ok=True)
        jdk_downloaded, _ = _download_file_with_progress(PORTABLE_JDK_DOWNLOAD_URL, portable_jdk_zip_path, "JDK Portable")
        if jdk_downloaded:
            extracted_jdk_root = _extract_portable_jdk(project_root, portable_jdk_parent_dir, portable_jdk_zip_path)
            if extracted_jdk_root and (extracted_jdk_root / "bin" / f"java{'.exe' if os.name == 'nt' else ''}").is_file():
                return str(extracted_jdk_root.resolve())

    logger.info("JDK portable non trouvé/installé. Retour à la détection standard (JAVA_HOME / chemin par défaut).")
    jdk_path_from_standard_detection = find_jdk_path()
    return str(jdk_path_from_standard_detection.resolve()) if jdk_path_from_standard_detection else None


_JVM_INITIALIZED_THIS_SESSION = False
_JVM_WAS_SHUTDOWN = False
_SESSION_FIXTURE_OWNS_JVM = False


def get_jvm_options() -> List[str]:
    options = [
        "-Xms64m",
        "-Xmx256m",
        "-Dfile.encoding=UTF-8",
        "-Djava.awt.headless=true"
    ]
    
    if os.name == 'nt':
        options.extend([
            "-XX:+UseG1GC",
            "-XX:+DisableExplicitGC",
            "-XX:-UsePerfData",
        ])
        logger.info("Options JVM Windows spécifiques ajoutées pour contourner les access violations JPype")
    
    logger.info(f"Options JVM de base définies : {options}")
    return options

def initialize_jvm(lib_dir_path: Optional[str] = None, specific_jar_path: Optional[str] = None) -> bool:
    global _JVM_WAS_SHUTDOWN, _JVM_INITIALIZED_THIS_SESSION, _SESSION_FIXTURE_OWNS_JVM
    
    logger.info(f"JVM_SETUP: initialize_jvm appelée. isJVMStarted au début: {jpype.isJVMStarted()}")
    logger.info(f"JVM_SETUP: _JVM_WAS_SHUTDOWN: {_JVM_WAS_SHUTDOWN}")
    logger.info(f"JVM_SETUP: _JVM_INITIALIZED_THIS_SESSION: {_JVM_INITIALIZED_THIS_SESSION}")
    logger.info(f"JVM_SETUP: _SESSION_FIXTURE_OWNS_JVM: {_SESSION_FIXTURE_OWNS_JVM}")
    
    logger.info("JVM_SETUP: Lancement de l'étape de vérification/téléchargement des JARs Tweety.")
    libs_ok = download_tweety_jars()
    if not libs_ok:
        logger.error("JVM_SETUP: Échec du provisioning des bibliothèques Tweety. Démarrage de la JVM annulé.")
        return False
    logger.info("JVM_SETUP: Provisioning des bibliothèques Tweety terminé.")

    if _JVM_WAS_SHUTDOWN and not jpype.isJVMStarted():
        logger.error("JVM_SETUP: ERREUR - Tentative de redémarrage de la JVM détectée.")
        return False
    
    if _SESSION_FIXTURE_OWNS_JVM and jpype.isJVMStarted():
        logger.info("JVM_SETUP: La JVM est contrôlée par la fixture de session.")
        _JVM_INITIALIZED_THIS_SESSION = True
        return True
    
    if _JVM_INITIALIZED_THIS_SESSION and jpype.isJVMStarted():
        logger.info("JVM_SETUP: JVM déjà initialisée dans cette session.")
        return True
    
    if jpype.isJVMStarted():
        logger.info("JVM_SETUP: JVM déjà démarrée (sans contrôle de session).")
        _JVM_INITIALIZED_THIS_SESSION = True
        return True

    try:
        logger.info(f"JVM_SETUP: Version de JPype: {jpype.__version__}")
    except (ImportError, AttributeError):
        logger.warning("JVM_SETUP: Impossible d'obtenir la version de JPype.")

    try:
        jars_classpath: List[str] = []
        if specific_jar_path:
            specific_jar_file = Path(specific_jar_path)
            if specific_jar_file.is_file():
                jars_classpath = [str(specific_jar_file)]
                logger.info(f"Utilisation du JAR spécifique: {specific_jar_path}")
            else:
                logger.error(f"(ERREUR) Fichier JAR spécifique introuvable: '{specific_jar_path}'.")
                return False
        else:
            jar_directory_path = Path(lib_dir_path) if lib_dir_path else find_libs_dir()
            if not jar_directory_path or not jar_directory_path.is_dir():
                logger.error(f"(ERREUR) Répertoire des JARs '{jar_directory_path}' invalide.")
                return False
            
            all_jars_in_dir = [str(f) for f in jar_directory_path.glob("*.jar")]
            jar_to_exclude = "org.tweetyproject.lp.asp-1.28-with-dependencies.jar"
            original_jar_count = len(all_jars_in_dir)
            jars_classpath = [jp for jp in all_jars_in_dir if jar_to_exclude not in Path(jp).name]
            if len(jars_classpath) < original_jar_count:
                logger.info(f"Exclusion de débogage: '{jar_to_exclude}' retiré du classpath. Nombre de JARs réduit à {len(jars_classpath)}.")
            logger.info(f"Classpath construit avec {len(jars_classpath)} JAR(s) depuis '{jar_directory_path}'.")

        if not jars_classpath:
            logger.error("(ERREUR) Aucun JAR trouvé pour le classpath. Démarrage annulé.")
            return False
        
        jvm_options_list = get_jvm_options()
        
        java_home_path_str = find_valid_java_home()
        if not java_home_path_str:
            logger.error("Impossible de trouver un JDK valide. JAVA_HOME n'est pas défini ou le JDK portable a échoué.")
        else:
            logger.info(f"Utilisation de JAVA_HOME (ou équivalent portable) : {java_home_path_str}")

        logger.info(f"Tentative de démarrage de la JVM avec classpath: {os.pathsep.join(jars_classpath)}")
        logger.info(f"Options JVM: {jvm_options_list}")
        
        jvm_dll_path = jpype.getDefaultJVMPath()
        logger.info(f"Chemin JVM par défaut détecté par JPype: {jvm_dll_path}")

        jpype.startJVM(
            jvm_dll_path,
            *jvm_options_list,
            classpath=jars_classpath,
            ignoreUnrecognized=True,
            convertStrings=False
        )
        _JVM_INITIALIZED_THIS_SESSION = True
        logger.info("JVM démarrée avec succès.")
        return True

    except Exception as e:
        logger.error(f"Erreur fatale lors du démarrage de la JVM: {e}", exc_info=True)
        if " RuntimeError: No matching overloads found." in str(e) or "No matching overloads found" in str(e):
             logger.error("Astuce: Cette erreur peut survenir si le classpath est incorrect, si une dépendance manque, ou incompatibilité de version JAR/JVM.")
        elif sys.platform == "win32" and ("java.lang.UnsatisfiedLinkError" in str(e) or "Can't load IA 32-bit .dll on a AMD 64-bit platform" in str(e)):
             logger.error("Astuce Windows: Vérifiez la cohérence 32/64 bits entre Python, JPype et le JDK. Assurez-vous que Microsoft Visual C++ Redistributable est installé.")
        return False


def shutdown_jvm():
    global _JVM_INITIALIZED_THIS_SESSION, _JVM_WAS_SHUTDOWN
    if jpype.isJVMStarted():
        logger.info("Arrêt de la JVM...")
        jpype.shutdownJVM()
        _JVM_INITIALIZED_THIS_SESSION = False
        _JVM_WAS_SHUTDOWN = True
        logger.info("JVM arrêtée.")
    else:
        logger.debug("La JVM n'est pas en cours d'exécution.")

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
