# core/jvm_setup.py
import jpype
try:
    import jpype.imports
except (ImportError, ModuleNotFoundError):
    # Si jpype est un mock ou si jpype.imports n'est pas disponible,
    # cela sera géré par le mock de jpype dans conftest.py qui fournira 
    # un attribut jpype.imports mocké au module jpype mocké.
    # Si le vrai jpype est utilisé mais que .imports n'est pas là (improbable pour les versions récentes),
    # alors le code qui l'utilise pourrait échouer plus tard si le mock de conftest n'est pas actif.
    pass
import os
import pathlib
import platform
import logging
from typing import Optional
import requests # Ajout pour téléchargement
import urllib.request # Ajout pour téléchargement
from tqdm.auto import tqdm # Ajout pour barre de progression
import stat # Ajout pour chmod (Linux/Mac)
import shutil # Ajout pour shutil.which

from argumentation_analysis.paths import LIBS_DIR


logger = logging.getLogger("Orchestration.JPype")
# Assurer logger configuré
if not logger.handlers and not logger.propagate:
    handler = logging.StreamHandler(); formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S'); handler.setFormatter(formatter); logger.addHandler(handler); logger.setLevel(logging.INFO)

MIN_JAVA_VERSION = 11
TWEETY_VERSION = "1.28" # Version de Tweety à télécharger

# --- Classe Tqdm pour barre de progression ---
class TqdmUpTo(tqdm):
    """Provides `update_to(block_num, block_size, total_size)`."""
    def update_to(self, b=1, bsize=1, tsize=None):
         if tsize is not None: self.total = tsize
         self.update(b * bsize - self.n)


# --- Fonction de téléchargement unitaire ---
def _download_file_with_progress(file_url: str, target_path: pathlib.Path, description: str):
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

# --- Fonction Principale de Téléchargement Tweety ---
def download_tweety_jars(
    version: str = TWEETY_VERSION,
    target_dir: str = LIBS_DIR,
    native_subdir: str = "native"
    ) -> bool:
    """
    Vérifie et télécharge les JARs Tweety (Core + Modules) et les binaires natifs nécessaires.
    """
    logger.info(f"\n--- Vérification/Téléchargement des JARs Tweety v{version} ---")
    BASE_URL = f"https://tweetyproject.org/builds/{version}/"
    LIB_DIR = pathlib.Path(target_dir)
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


# --- Fonction de détection JAVA_HOME (inchangée) ---
def find_valid_java_home() -> Optional[str]:
    logger.debug("Début recherche répertoire Java Home valide...")
    found_home_path = None
    java_home_env = os.getenv("JAVA_HOME")
    if java_home_env:
        logger.info(f"ℹ️ Variable JAVA_HOME trouvée: '{java_home_env}'")
        java_home_path = pathlib.Path(java_home_env)
        if java_home_path.is_dir():
            exe_suffix = ".exe" if platform.system() == "Windows" else ""
            java_exe = java_home_path / "bin" / f"java{exe_suffix}"
            if java_exe.is_file():
                logger.info(f"✔️ JAVA_HOME ('{java_home_env}') semble valide.")
                return str(java_home_path)
            else:
                logger.warning(f"⚠️ JAVA_HOME trouvé mais 'bin/java' non trouvé ou n'est pas un fichier dans: {java_home_path}")
        else:
            logger.warning(f"⚠️ JAVA_HOME ('{java_home_env}') n'est pas un dossier valide.")
    else:
        logger.info("ℹ️ Variable d'environnement JAVA_HOME non définie.")
    logger.info("ℹ️ Tentative de détection via heuristiques spécifiques à l'OS...")
    system = platform.system()
    potential_homes_dirs = []
    if system == "Windows":
        logger.debug("-> Recherche Windows...")
        program_files_paths = [os.getenv("ProgramFiles", "C:/Program Files"),
                               os.getenv("ProgramFiles(x86)", "C:/Program Files (x86)")]
        vendors = ["Java", "OpenJDK", "Eclipse Adoptium", "Amazon Corretto", "Microsoft", "Semeru"]
        for pf_path in filter(None, program_files_paths):
            for vendor in vendors:
                vendor_dir = pathlib.Path(pf_path) / vendor
                if vendor_dir.is_dir():
                    logger.debug(f"  Scan du dossier: {vendor_dir}")
                    potential_homes_dirs.extend(list(vendor_dir.glob("jdk*")))
                    potential_homes_dirs.extend(list(vendor_dir.glob("jre*")))
    elif system == "Darwin": 
        logger.debug("-> Recherche macOS...")
        mac_paths = ["/Library/Java/JavaVirtualMachines", "/System/Library/Frameworks/JavaVM.framework/Versions", os.path.expanduser("~/Library/Java/JavaVirtualMachines")]
        if os.path.exists("/opt/homebrew/opt"): mac_paths.append("/opt/homebrew/opt")
        for base_path in mac_paths:
            base_path_p = pathlib.Path(base_path)
            if base_path_p.is_dir():
                 potential_homes_dirs.extend(list(base_path_p.glob("*.jdk"))) 
                 potential_homes_dirs.extend([p / "Contents" / "Home" for p in base_path_p.glob("*/Contents/Home") if (p / "Contents" / "Home").is_dir()])
    elif system == "Linux":
        logger.debug("-> Recherche Linux...")
        linux_paths = ["/usr/lib/jvm", "/usr/java", "/opt/java"]
        for base_path in linux_paths:
            base_path_p = pathlib.Path(base_path)
            if base_path_p.is_dir():
                potential_homes_dirs.extend(list(base_path_p.glob("java-*")))
                potential_homes_dirs.extend(list(base_path_p.glob("jdk*")))
                potential_homes_dirs.extend(list(base_path_p.glob("jre*")))
    if potential_homes_dirs:
        logger.info(f"  {len(potential_homes_dirs)} installations Java potentielles trouvées par heuristique.")
        potential_homes_dirs.sort(key=lambda x: x.name, reverse=True) 
        for home in potential_homes_dirs:
            actual_home = home
            if system == "Darwin" and str(home).endswith("/Contents/Home"):
                 pass 
            elif system == "Darwin" and (home / "Contents" / "Home").is_dir():
                 actual_home = home / "Contents" / "Home" 
            logger.debug(f"  Vérification home potentiel: {actual_home}")
            exe_suffix = ".exe" if system == "Windows" else ""
            java_exe = actual_home / "bin" / f"java{exe_suffix}"
            if java_exe.is_file():
                logger.info(f"✔️ Répertoire Java Home valide trouvé via heuristique: {actual_home}")
                return str(actual_home) 
            else:
                logger.debug(f"    -> 'bin/java' non trouvé dans {actual_home}")
        logger.warning("⚠️ Heuristique a trouvé des dossiers Java mais aucun avec 'bin/java' valide.")
    else:
        logger.info("  Aucune installation Java trouvée via heuristiques OS standard.")
    logger.error("❌ Recherche finale: Aucun répertoire Java Home valide n'a pu être localisé.")
    return None


# --- Fonction d'Initialisation JVM (modifiée pour appeler download_tweety_jars) ---
def initialize_jvm(
    lib_dir_path: str = LIBS_DIR,
    native_lib_subdir: str = "native",
    tweety_version: str = TWEETY_VERSION 
    ) -> bool:
    logger.info("\n--- Préparation et Initialisation de la JVM via JPype ---")
    libs_ok = download_tweety_jars(version=tweety_version, target_dir=lib_dir_path, native_subdir=native_lib_subdir)
    if not libs_ok:
        logger.error("❌ Problème avec les fichiers Tweety (Core manquant?). Démarrage JVM annulé.")
        return False
    LIB_DIR = pathlib.Path(lib_dir_path)
    NATIVE_LIBS_DIR = LIB_DIR / native_lib_subdir
    jvm_ready = False
    if jpype.isJVMStarted():
        logger.warning("ℹ️ JVM déjà démarrée. Utilisation existante.")
        jvm_ready = True
        try: 
            if hasattr(jpype, 'imports') and jpype.imports is not None:
                 jpype.imports.registerDomain("org", alias="org")
                 jpype.imports.registerDomain("java", alias="java")
                 jpype.imports.registerDomain("net", alias="net")
                 logger.info("   Domaines JPype (org, java, net) enregistrés (ou déjà présents).")
            else:
                logger.warning("   jpype.imports non disponible pour enregistrer les domaines (possible si mock partiel).")
        except Exception: pass
        return True 
    java_home_to_set = find_valid_java_home()
    if java_home_to_set and not os.getenv("JAVA_HOME"):
        try:
            os.environ['JAVA_HOME'] = java_home_to_set
            logger.info(f"✅ JAVA_HOME défini dynamiquement à '{java_home_to_set}' pour cette session.")
        except Exception as e_setenv:
            logger.error(f"❌ Impossible de définir JAVA_HOME dynamiquement: {e_setenv}")
    elif not java_home_to_set:
         logger.error("❌ JAVA_HOME non trouvé. Démarrage JVM impossible.")
         return False 
    jvm_path_final = None
    jvm_args = [] # Définir jvm_args ici pour qu'il soit toujours disponible pour le log d'erreur
    try:
        logger.info(f"⏳ Tentative de démarrage JVM...")
        try:
            jvm_path_final = jpype.getDefaultJVMPath()
            logger.info(f"   (Chemin JVM par défaut détecté par JPype: {jvm_path_final})")
        except jpype.JVMNotFoundException:
            logger.warning("   (JPype n'a pas trouvé de JVM par défaut - dépendra de JAVA_HOME)")
            jvm_path_final = None
        classpath_separator = os.pathsep
        jar_list = sorted([str(p.resolve()) for p in LIB_DIR.glob("*.jar")])
        if not jar_list: 
             logger.error("❌ Aucun JAR trouvé dans le classpath après téléchargement/vérification ! Démarrage annulé.")
             return False
        classpath = classpath_separator.join(jar_list)
        logger.info(f"   Classpath construit ({len(jar_list)} JARs depuis '{LIB_DIR}').")
        jvm_args = [f"-Djava.class.path={classpath}"]
        if NATIVE_LIBS_DIR.exists() and any(NATIVE_LIBS_DIR.iterdir()):
            native_path_arg = f"-Djava.library.path={NATIVE_LIBS_DIR.resolve()}"
            jvm_args.append(native_path_arg)
            logger.info(f"   Argument JVM natif ajouté: {native_path_arg}")
        else:
            logger.info(f"   (Pas de bibliothèques natives trouvées dans '{NATIVE_LIBS_DIR.resolve()}', -Djava.library.path non ajouté)")
        jpype.startJVM(*jvm_args, convertStrings=False, ignoreUnrecognized=True)
        if hasattr(jpype, 'imports') and jpype.imports is not None:
            jpype.imports.registerDomain("org", alias="org")
            jpype.imports.registerDomain("java", alias="java")
            jpype.imports.registerDomain("net", alias="net")
            logger.info("✅ JVM démarrée avec succès et domaines enregistrés.")
        else:
            logger.warning("✅ JVM démarrée mais jpype.imports non disponible pour enregistrer les domaines (possible si mock partiel).")
        jvm_ready = True
    except Exception as e:
        logger.critical(f"\n❌❌❌ Erreur Démarrage JVM: {e} ❌❌❌", exc_info=True)
        logger.critical(f"   Vérifiez chemin JVM, classpath, versions JDK/JARs.")
        logger.info(f"   JAVA_HOME (défini ou trouvé): {os.getenv('JAVA_HOME', 'Non défini')}")
        if jvm_path_final: logger.info(f"   Chemin JVM Défaut JPype: {jvm_path_final}")
        logger.info(f"   Arguments JVM tentés: {jvm_args}")
        jvm_ready = False
    if not jvm_ready:
        logger.warning(f"\n‼️‼️ JVM NON PRÊTE après tentative. L'agent PL échouera probablement. ‼️‼️")
    else:
        logger.info("\n✅ JVM prête pour utilisation.")
    logger.info("--- Fin Initialisation JVM ---")
    return jvm_ready

module_logger = logging.getLogger(__name__)
module_logger.debug("Module core.jvm_setup chargé et modifié pour inclure téléchargement JARs.")