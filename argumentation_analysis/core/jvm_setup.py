# argumentation_analysis/core/jvm_setup.py
import jpype
import jpype.imports
import logging
import os
from pathlib import Path
from typing import Optional, List

import platform
from typing import Optional, List
import requests
from tqdm.auto import tqdm
import stat
import shutil
import zipfile

# Configuration du logger pour ce module
logger = logging.getLogger("Orchestration.JPype")

# --- Fonctions de téléchargement et de provisioning (issues du stash) ---

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
    for module in tqdm(REQUIRED_MODULES, desc="Modules JARs"):
        module_jar_name = f"org.tweetyproject.{module}-{version}-with-dependencies.jar"
        present, new_dl = _download_file_with_progress(BASE_URL + module_jar_name, LIB_DIR / module_jar_name, module_jar_name)
        if present:
            modules_present_count += 1
            if new_dl: modules_downloaded_count += 1
        elif url_accessible: 
             modules_missing.append(module)
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
                         target_path = NATIVE_LIBS_DIR / name
                         current_permissions = target_path.stat().st_mode
                         target_path.chmod(current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH) 
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

def find_valid_java_home() -> Optional[str]:
    logger.debug("Début recherche répertoire Java Home valide...")
    
    project_root = get_project_root()
    portable_jdk_parent_dir = project_root / PORTABLE_JDK_DIR_NAME
    portable_jdk_zip_path = project_root / TEMP_DIR_NAME / PORTABLE_JDK_ZIP_NAME
    PORTABLE_JDK_DOWNLOAD_URL = "https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.15%2B6/OpenJDK17U-jdk_x64_windows_hotspot_17.0.15_6.zip" # Du Stash
    
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

    # Si le portable échoue, on revient à la logique de HEAD.
    # Je vais simplement appeler `find_jdk_path` de HEAD comme fallback.
    logger.info("JDK portable non trouvé/installé. Retour à la détection standard (JAVA_HOME / chemin par défaut).")
    jdk_path_from_head = find_jdk_path()
    return str(jdk_path_from_head) if jdk_path_from_head else None

# --- Fonctions pour une initialisation paresseuse (Lazy Initialization) ---

_PROJECT_ROOT_DIR = None
_LIBS_DIR = None
_PORTABLE_JDK_PATH = None
_ENV_LOADED = False
_JVM_WAS_SHUTDOWN = False  # Indicateur pour éviter les tentatives de redémarrage
_JVM_INITIALIZED_THIS_SESSION = False  # Flag pour la session de test
_SESSION_FIXTURE_OWNS_JVM = False  # Flag pour indiquer que la fixture de session contrôle la JVM

def _ensure_env_loaded():
    """Charge les variables d'environnement une seule fois."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    try:
        from dotenv import load_dotenv, find_dotenv
        env_file = find_dotenv()
        if env_file:
            load_dotenv(env_file, override=True)
            logger.info(f"Variables d'environnement chargées depuis: {env_file}")
            _ENV_LOADED = True
        else:
            logger.warning("Fichier .env non trouvé, utilisation des variables système")
            _ENV_LOADED = True # Marquer comme chargé pour ne pas retenter
    except ImportError:
        logger.warning("python-dotenv non disponible, utilisation des variables système uniquement")
        _ENV_LOADED = True # Marquer comme chargé pour ne pas retenter

def get_project_root() -> Path:
    """Retourne le répertoire racine du projet (calculé une seule fois)."""
    global _PROJECT_ROOT_DIR
    if _PROJECT_ROOT_DIR is None:
        _PROJECT_ROOT_DIR = Path(__file__).resolve().parent.parent.parent
    return _PROJECT_ROOT_DIR

def find_libs_dir() -> Optional[Path]:
    """Trouve le répertoire des JARs de Tweety (calculé une seule fois)."""
    global _LIBS_DIR
    if _LIBS_DIR is not None:
        return _LIBS_DIR if _LIBS_DIR else None # Retourne None si la recherche précédente a échoué

    project_root = get_project_root()
    primary_dir = project_root / "libs" / "tweety"
    fallback_dir = project_root / "libs"

    if primary_dir.is_dir() and list(primary_dir.glob("*.jar")):
        _LIBS_DIR = primary_dir
        logger.info(f"LIBS_DIR défini sur (primaire): {_LIBS_DIR}")
    elif fallback_dir.is_dir() and list(fallback_dir.glob("*.jar")):
        _LIBS_DIR = fallback_dir
        logger.info(f"LIBS_DIR défini sur (fallback): {_LIBS_DIR}")
    else:
        logger.warning(
            f"Aucun JAR trouvé ni dans {primary_dir} ni dans {fallback_dir}. "
            f"LIBS_DIR n'est pas défini."
        )
        _LIBS_DIR = Path() # Marqueur pour indiquer que la recherche a échoué
        return None
    return _LIBS_DIR

def find_jdk_path() -> Optional[Path]:
    """Trouve le chemin du JDK portable ou via JAVA_HOME (calculé une seule fois)."""
    global _PORTABLE_JDK_PATH
    if _PORTABLE_JDK_PATH is not None:
         return _PORTABLE_JDK_PATH if _PORTABLE_JDK_PATH else None

    _ensure_env_loaded()
    project_root = get_project_root()

    # Priorité 1: Variable d'environnement JAVA_HOME
    java_home = os.getenv('JAVA_HOME')
    if java_home:
        potential_path = Path(java_home)
        if not potential_path.is_absolute():
            potential_path = get_project_root() / potential_path
            
        if potential_path.is_dir():
            _PORTABLE_JDK_PATH = potential_path
            logger.info(f"(OK) JDK détecté via JAVA_HOME : {_PORTABLE_JDK_PATH}")
            return _PORTABLE_JDK_PATH
        else:
            logger.warning(f"(ATTENTION) JAVA_HOME défini mais répertoire inexistant : {potential_path}")
    
    # Priorité 2: Chemin par défaut
    jdk_subdir = "libs/portable_jdk/jdk-17.0.11+9"
    potential_path = project_root / jdk_subdir
    if potential_path.is_dir():
        _PORTABLE_JDK_PATH = potential_path
        logger.info(f"(OK) JDK portable détecté via chemin par défaut : {_PORTABLE_JDK_PATH}")
        return _PORTABLE_JDK_PATH
    
    logger.warning(f"(ATTENTION) JDK portable non trouvé à l'emplacement par défaut : {potential_path}")
    _PORTABLE_JDK_PATH = Path() # Marqueur pour indiquer que la recherche a échoué
    return None

def get_jvm_options() -> List[str]:
    """Prépare les options pour le démarrage de la JVM, incluant le chemin du JDK si disponible."""
    options = [
        "-Xms64m",      # Réduit de 128m à 64m pour éviter les access violations
        "-Xmx256m",     # Réduit de 512m à 256m pour les tests
        "-Dfile.encoding=UTF-8",
        "-Djava.awt.headless=true"
    ]
    
    # Options spécifiques Windows pour contourner les access violations JPype
    if os.name == 'nt':  # Windows
        options.extend([
            "-XX:+UseG1GC",              # Garbage collector plus stable
            "-XX:+DisableExplicitGC",    # Évite les GC manuels problématiques
            "-XX:-UsePerfData",          # Désactive les données de performance
            "-Djava.awt.headless=true"   # Force mode headless
        ])
        logger.info("Options JVM Windows spécifiques ajoutées pour contourner les access violations JPype")
    
    logger.info(f"Options JVM de base définies : {options}")
    return options

def initialize_jvm(lib_dir_path: Optional[str] = None, specific_jar_path: Optional[str] = None) -> bool:
    """
    Initialise la JVM avec les JARs de TweetyProject (initialisation paresseuse).
    
    ATTENTION: JPype ne permet qu'un seul cycle de vie JVM par processus Python.
    Une fois jpype.shutdownJVM() appelé, la JVM ne peut plus être redémarrée.
    """
    global _JVM_WAS_SHUTDOWN, _JVM_INITIALIZED_THIS_SESSION, _SESSION_FIXTURE_OWNS_JVM
    
    logger.info(f"JVM_SETUP: initialize_jvm appelée. isJVMStarted au début: {jpype.isJVMStarted()}")
    logger.info(f"JVM_SETUP: _JVM_WAS_SHUTDOWN: {_JVM_WAS_SHUTDOWN}")
    logger.info(f"JVM_SETUP: _JVM_INITIALIZED_THIS_SESSION: {_JVM_INITIALIZED_THIS_SESSION}")
    logger.info(f"JVM_SETUP: _SESSION_FIXTURE_OWNS_JVM: {_SESSION_FIXTURE_OWNS_JVM}")
    
    # --- Étape de Provisioning (issue du stash) ---
    logger.info("JVM_SETUP: Lancement de l'étape de vérification/téléchargement des JARs.")
    libs_ok = download_tweety_jars()
    if not libs_ok:
        logger.error("JVM_SETUP: Échec du provisioning des bibliothèques Tweety. Démarrage de la JVM annulé.")
        return False
    logger.info("JVM_SETUP: Provisioning des bibliothèques terminé.")

    # PROTECTION 1: Vérifier si une tentative de redémarrage est en cours
    if _JVM_WAS_SHUTDOWN and not jpype.isJVMStarted():
        logger.error("JVM_SETUP: ERREUR - Tentative de redémarrage de la JVM détectée. JPype ne supporte qu'un cycle de vie JVM par processus.")
        logger.error("JVM_SETUP: Veuillez relancer le processus Python pour utiliser la JVM à nouveau.")
        return False
    
    # PROTECTION 2: Si la fixture de session contrôle la JVM, interdire les appels directs
    if _SESSION_FIXTURE_OWNS_JVM and jpype.isJVMStarted():
        logger.info("JVM_SETUP: La JVM est contrôlée par la fixture de session. Utilisation de la JVM existante.")
        _JVM_INITIALIZED_THIS_SESSION = True
        return True
    
    # PROTECTION 3: Si déjà initialisée dans cette session, ne pas refaire
    if _JVM_INITIALIZED_THIS_SESSION and jpype.isJVMStarted():
        logger.info("JVM_SETUP: JVM déjà initialisée dans cette session. Réutilisation.")
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
        jars: List[str] = []
        if specific_jar_path:
            specific_jar_file = Path(specific_jar_path)
            if specific_jar_file.is_file():
                jars = [str(specific_jar_file)]
                logger.info(f"Utilisation du JAR spécifique: {specific_jar_path}")
            else:
                logger.error(f"(ERREUR) Fichier JAR spécifique introuvable: '{specific_jar_path}'.")
                return False
        else:
            jar_directory = Path(lib_dir_path) if lib_dir_path else find_libs_dir()
            if not jar_directory or not jar_directory.is_dir():
                logger.error(f"(ERREUR) Répertoire des JARs '{jar_directory}' invalide.")
                return False
            
            jars = [str(f) for f in jar_directory.glob("*.jar")]
# --- DÉBUT DE L'INTÉGRATION DU CHANGEMENT DU STASH ---
            # Exclure le JAR problématique identifié dans le stash
            jar_to_exclude = "org.tweetyproject.lp.asp-1.28-with-dependencies.jar"
            original_jar_count = len(jars)
            jars = [jar_path for jar_path in jars if jar_to_exclude not in Path(jar_path).name]
            if len(jars) < original_jar_count:
                logger.info(f"Exclusion de débogage: '{jar_to_exclude}' retiré du classpath. Nombre de JARs réduit à {len(jars)}.")
            # --- FIN DE L'INTÉGRATION DU CHANGEMENT DU STASH ---
            logger.info(f"Classpath construit avec {len(jars)} JAR(s) depuis '{jar_directory}'.")
            logger.info(f"Classpath configuré avec {len(jars)} JARs (JPype {jpype.__version__})")

        if not jars:
            logger.error("(ERREUR) Aucun JAR trouvé pour le classpath. Démarrage annulé.")
            return False
        
        jvm_options = get_jvm_options()
        jdk_path_str = find_valid_java_home()
        jdk_path = Path(jdk_path_str) if jdk_path_str else None
        jvm_path = None

        # Stratégie de recherche de la JVM
        try:
            jvm_path = jpype.getDefaultJVMPath()
            logger.info(f"JPype a trouvé une JVM par défaut : {jvm_path}")
        except jpype.JVMNotFoundException:
            logger.warning("JPype n'a pas trouvé de JVM par défaut. Tentative avec JAVA_HOME.")
            if jdk_path:
                # Construire le chemin vers jvm.dll sur Windows
                if os.name == 'nt':
                    potential_jvm_path = jdk_path / "bin" / "server" / "jvm.dll"
                # Construire le chemin vers libjvm.so sur Linux
                else:
                    potential_jvm_path = jdk_path / "lib" / "server" / "libjvm.so"
                
                if potential_jvm_path.exists():
                    jvm_path = str(potential_jvm_path)
                    logger.info(f"Chemin JVM construit manuellement à partir de JAVA_HOME: {jvm_path}")
                else:
                    logger.error(f"Le fichier de la librairie JVM n'a pas été trouvé à l'emplacement attendu: {potential_jvm_path}")
            else:
                logger.error("JAVA_HOME n'est pas défini et la JVM par défaut n'est pas trouvable.")

        if not jvm_path:
            logger.critical("Impossible de localiser la JVM. Le démarrage est annulé.")
            return False

        logger.info(f"JVM_SETUP: Avant startJVM. isJVMStarted: {jpype.isJVMStarted()}.")

        try:
            logger.info(f"Tentative de démarrage de la JVM avec le chemin : {jvm_path}")
            jpype.startJVM(jvm_path, *jvm_options, classpath=jars)
        except Exception as e:
            logger.error(f"Échec final du démarrage de la JVM avec le chemin '{jvm_path}'. Erreur: {e}", exc_info=True)
            return False

        logger.info(f"JVM démarrée avec succès. isJVMStarted: {jpype.isJVMStarted()}.")
        
        try:
            _ = jpype.JClass("org.tweetyproject.logics.pl.syntax.PlSignature")
            logger.info("(OK) Test de chargement de classe Tweety (PlSignature) réussi.")
        except Exception as e_test:
            logger.error(f"(ERREUR) Test de chargement de classe Tweety échoué: {e_test}", exc_info=True)

        # Marquer que la JVM a été initialisée avec succès dans cette session
        _JVM_INITIALIZED_THIS_SESSION = True
        logger.info("JVM_SETUP: Flag _JVM_INITIALIZED_THIS_SESSION défini à True.")
        return True

    except Exception as e:
        logger.critical(f"(ERREUR CRITIQUE) Échec global du démarrage de la JVM: {e}", exc_info=True)
        return False

def _safe_log(logger_instance, level, message, exc_info_val=False):
    """Effectue un log de manière sécurisée, avec un fallback sur print."""
    try:
        if logger_instance.hasHandlers():
            logger_instance.log(level, message, exc_info=exc_info_val)
        else:
            print(f"FALLBACK LOG ({logging.getLevelName(level)}): {message}")
            if exc_info_val:
                import traceback
                traceback.print_exc()
    except Exception:
        print(f"FALLBACK LOG (Exception in logger) ({logging.getLevelName(level)}): {message}")

def set_session_fixture_owns_jvm(owns: bool = True):
    """
    Définit si la fixture de session contrôle la JVM.
    
    Args:
        owns: True si la fixture de session contrôle la JVM, False sinon
    """
    global _SESSION_FIXTURE_OWNS_JVM
    _SESSION_FIXTURE_OWNS_JVM = owns
    logger.info(f"JVM_SETUP: _SESSION_FIXTURE_OWNS_JVM défini à {owns}")

def is_session_fixture_owns_jvm() -> bool:
    """Retourne si la fixture de session contrôle la JVM."""
    return _SESSION_FIXTURE_OWNS_JVM

def reset_session_flags():
    """Remet à zéro les flags de session (utile pour les tests)."""
    global _JVM_INITIALIZED_THIS_SESSION, _SESSION_FIXTURE_OWNS_JVM
    _JVM_INITIALIZED_THIS_SESSION = False
    _SESSION_FIXTURE_OWNS_JVM = False
    logger.info("JVM_SETUP: Flags de session remis à zéro")

def shutdown_jvm_if_needed():
    """
    Arrête la JVM si elle est démarrée.
    
    ATTENTION: Une fois la JVM arrêtée avec jpype.shutdownJVM(),
    elle ne peut plus être redémarrée dans le même processus Python.
    """
    global _JVM_WAS_SHUTDOWN
    
    _safe_log(logger, logging.INFO, "JVM_SETUP: Appel de shutdown_jvm_if_needed.")
    _safe_log(logger, logging.INFO, f"JVM_SETUP: _SESSION_FIXTURE_OWNS_JVM: {_SESSION_FIXTURE_OWNS_JVM}")
    
    try:
        if jpype.isJVMStarted():
            _safe_log(logger, logging.INFO, f"JVM_SETUP: JVM est démarrée. Appel de jpype.shutdownJVM().")
            jpype.shutdownJVM()
            _JVM_WAS_SHUTDOWN = True
            _safe_log(logger, logging.INFO, f"JVM_SETUP: jpype.shutdownJVM() exécuté. Flag _JVM_WAS_SHUTDOWN défini à True.")
            _safe_log(logger, logging.INFO, f"JVM_SETUP: ATTENTION: La JVM ne peut plus être redémarrée dans ce processus.")
        else:
            _safe_log(logger, logging.INFO, "JVM_SETUP: JVM n'était pas démarrée.")
    except Exception as e_shutdown:
        _safe_log(logger, logging.ERROR, f"JVM_SETUP: Erreur lors de jpype.shutdownJVM(): {e_shutdown}", exc_info_val=True)

# --- Exports pour l'importation par d'autres modules ---
TWEETY_VERSION = "1.28" # Doit correspondre à la version dans libs
LIBS_DIR = find_libs_dir()

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    # Utiliser la variable exportée maintenant
    if LIBS_DIR:
        success = initialize_jvm()
        if success:
            logger.info("Test initialize_jvm: SUCCÈS")
            try:
                TestClass = jpype.JClass("org.tweetyproject.logics.pl.syntax.PropositionalSignature")
                logger.info(f"Classe de test chargée: {TestClass}")
            except Exception as e:
                logger.error(f"Erreur lors du test: {e}", exc_info=True)
            finally:
                shutdown_jvm_if_needed()
        else:
            logger.error("Test initialize_jvm: ÉCHEC")
    else:
        logger.error("Test initialize_jvm: ÉCHEC - LIBS_DIR non défini.")