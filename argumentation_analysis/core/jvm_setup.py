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

MIN_JAVA_VERSION = 15
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


# --- Fonction de détection JAVA_HOME (modifiée pour prioriser Java >= MIN_JAVA_VERSION) ---
def find_valid_java_home() -> Optional[str]:
    logger.debug(f"Début recherche répertoire Java Home valide (priorité Java >= {MIN_JAVA_VERSION})...")

    system = platform.system()
    exe_suffix = ".exe" if system == "Windows" else ""
    # Stocke un JAVA_HOME valide trouvé dans l'env, mais qui ne correspond pas à MIN_JAVA_VERSION (pour fallback)
    java_home_from_env_fallback: Optional[str] = None
    
    # Chemin spécifique prioritaire pour Java 21 (car mentionné comme disponible sur le système cible)
    # Cela peut être adapté ou supprimé si une détection plus générique est préférée.
    specific_java_21_path_str = "C:\\Program Files\\Java\\jdk-21"
    specific_java_21_path = pathlib.Path(specific_java_21_path_str)

    # 0. Vérifier le chemin spécifique priorisé pour Java 21 (ou autre version >= MIN_JAVA_VERSION si pertinent)
    if system == "Windows" and specific_java_21_path.is_dir():
        java_exe_specific = specific_java_21_path / "bin" / f"java{exe_suffix}"
        if java_exe_specific.is_file():
            # Ici, on pourrait ajouter une vérification de version si le chemin n'est pas garanti >= MIN_JAVA_VERSION
            logger.info(f"🎉 Java >= {MIN_JAVA_VERSION} (spécifiquement Java 21) trouvé au chemin priorisé: '{specific_java_21_path_str}'. Utilisation.")
            return str(specific_java_21_path)
        else:
            logger.info(f"ℹ️ Chemin spécifique Java 21 '{specific_java_21_path_str}' existe mais 'bin/java{exe_suffix}' non trouvé.")
    elif system == "Windows":
        logger.info(f"ℹ️ Chemin spécifique Java 21 '{specific_java_21_path_str}' non trouvé ou n'est pas un dossier.")

    # 1. Vérifier la variable d'environnement JAVA_HOME
    java_home_env_var = os.getenv("JAVA_HOME")
    if java_home_env_var:
        logger.info(f"ℹ️ Variable JAVA_HOME trouvée: '{java_home_env_var}'")
        java_home_path = pathlib.Path(java_home_env_var)
        if java_home_path.is_dir():
            java_exe = java_home_path / "bin" / f"java{exe_suffix}"
            if java_exe.is_file():
                logger.info(f"✔️ JAVA_HOME ('{java_home_env_var}') pointe vers une installation Java avec 'bin/java'.")
                # Tentative de déduire la version à partir du nom du chemin
                # C'est une heuristique et pourrait nécessiter d'exécuter `java -version` pour une certitude
                path_name_lower = java_home_path.name.lower()
                version_in_name = -1
                try:
                    # Cherche des nombres comme "15", "17", "21" dans le nom du dossier
                    import re
                    match = re.search(r'(?:jdk-|java-|openjdk-)?(\d+)', path_name_lower)
                    if match:
                        version_in_name = int(match.group(1))
                except: # noqa
                    pass # Ignorer les erreurs de parsing, version_in_name restera -1

                if version_in_name >= MIN_JAVA_VERSION:
                    logger.info(f"🎉 JAVA_HOME ('{java_home_env_var}') semble être une version Java >= {MIN_JAVA_VERSION} (version {version_in_name} déduite). Utilisation prioritaire.")
                    return str(java_home_path)
                elif version_in_name != -1 : # Version déduite mais < MIN_JAVA_VERSION
                    logger.info(f"   JAVA_HOME ('{java_home_env_var}') est valide (version {version_in_name} déduite) mais < {MIN_JAVA_VERSION}. Conservé comme fallback.")
                    java_home_from_env_fallback = str(java_home_path)
                else: # Impossible de déduire la version, on suppose qu'elle pourrait être bonne si l'utilisateur l'a mise
                    logger.info(f"   JAVA_HOME ('{java_home_env_var}') est valide, version non déduite du nom. On suppose qu'elle est >= {MIN_JAVA_VERSION} si définie par l'utilisateur.")
                    # On pourrait ici ajouter une vérification réelle de la version si nécessaire,
                    # mais pour l'instant, on fait confiance à l'utilisateur s'il a défini JAVA_HOME.
                    # Si on veut être strict, on ne le retourne que si on peut confirmer la version.
                    # Pour l'instant, on le retourne, en priorisant les détections explicites.
                    # Si on veut être plus strict, on le mettrait dans java_home_from_env_fallback
                    # et on ne le retournerait que si aucune autre option >= MIN_JAVA_VERSION n'est trouvée.
                    # Pour l'instant, on le retourne directement.
                    return str(java_home_path) # Optionnel: être plus strict et le mettre en fallback
            else:
                logger.warning(f"⚠️ JAVA_HOME ('{java_home_env_var}') trouvé mais 'bin/java{exe_suffix}' non trouvé ou n'est pas un fichier.")
        else:
            logger.warning(f"⚠️ JAVA_HOME ('{java_home_env_var}') n'est pas un dossier valide.")
    else:
        logger.info(f"ℹ️ Variable d'environnement JAVA_HOME non définie.")

    # 2. Tentative de détection via heuristiques spécifiques à l'OS
    logger.info(f"ℹ️ Tentative de détection via heuristiques (priorité Java >= {MIN_JAVA_VERSION}, après JAVA_HOME et chemin spécifique)...")
    potential_homes_dirs = []
    
    # Logique de collecte des chemins potentiels (inchangée pour la collecte, le filtrage se fera après)
    if system == "Windows":
        logger.debug("-> Recherche Windows...")
        program_files_paths_str = [os.getenv("ProgramFiles", "C:/Program Files"),
                                   os.getenv("ProgramFiles(x86)", "C:/Program Files (x86)")]
        # Ajout de "GraalVM" qui peut fournir des JDKs
        vendors = ["Java", "OpenJDK", "Eclipse Adoptium", "Amazon Corretto", "Microsoft", "Semeru", "Azul Systems", "BellSoft", "RedHat", "GraalVM"]
        for pf_path_str in filter(None, program_files_paths_str):
            pf_path = pathlib.Path(pf_path_str)
            for vendor in vendors:
                vendor_dir = pf_path / vendor
                if vendor_dir.is_dir():
                    logger.debug(f"  Scan du dossier: {vendor_dir}")
                    potential_homes_dirs.extend(vendor_dir.glob("jdk*"))
                    potential_homes_dirs.extend(vendor_dir.glob("jre*"))
                    potential_homes_dirs.extend(vendor_dir.glob("zulu*"))
                    potential_homes_dirs.extend(vendor_dir.glob("corretto*"))
                    potential_homes_dirs.extend(vendor_dir.glob("semeru*"))
                    potential_homes_dirs.extend(vendor_dir.glob("liberica*"))
                    potential_homes_dirs.extend(vendor_dir.glob("graalvm*")) # Pour GraalVM

    elif system == "Darwin": # macOS
        logger.debug("-> Recherche macOS...")
        mac_paths_str = ["/Library/Java/JavaVirtualMachines",
                         os.path.expanduser("~/Library/Java/JavaVirtualMachines")]
        for brew_prefix in ["/opt/homebrew", "/usr/local"]: # Homebrew paths
            if os.path.exists(f"{brew_prefix}/opt"): mac_paths_str.append(f"{brew_prefix}/opt")
            if os.path.exists(f"{brew_prefix}/Cellar"):
                cellar_path = pathlib.Path(f"{brew_prefix}/Cellar")
                potential_homes_dirs.extend(cellar_path.glob("openjdk*/*"))
                potential_homes_dirs.extend(cellar_path.glob("java*/*"))
                potential_homes_dirs.extend(cellar_path.glob("graalvm-ce-java*/*")) # GraalVM via Homebrew

        for base_path_str in mac_paths_str:
            base_path_p = pathlib.Path(base_path_str)
            if base_path_p.is_dir():
                logger.debug(f"  Scan du dossier: {base_path_p}")
                potential_homes_dirs.extend(base_path_p.glob("*.jdk"))
                potential_homes_dirs.extend(base_path_p.glob("openjdk*"))
                potential_homes_dirs.extend(base_path_p.glob("zulu*"))
                potential_homes_dirs.extend(base_path_p.glob("corretto*"))
                potential_homes_dirs.extend(base_path_p.glob("semeru*"))
                potential_homes_dirs.extend(base_path_p.glob("liberica*"))
                potential_homes_dirs.extend(base_path_p.glob("graalvm*"))
                for jdk_path in base_path_p.glob("*.jdk"):
                    if (jdk_path / "Contents" / "Home").is_dir():
                        potential_homes_dirs.append(jdk_path / "Contents" / "Home")
                for opt_path in base_path_p.glob("openjdk*"):
                    if (opt_path / "libexec" / "openjdk.jdk" / "Contents" / "Home").is_dir():
                        potential_homes_dirs.append(opt_path / "libexec" / "openjdk.jdk" / "Contents" / "Home")
                    elif (opt_path / "Contents" / "Home").is_dir():
                         potential_homes_dirs.append(opt_path / "Contents" / "Home")
                # GraalVM peut aussi avoir une structure Contents/Home
                for graal_path in base_path_p.glob("graalvm*"):
                     if (graal_path / "Contents" / "Home").is_dir():
                        potential_homes_dirs.append(graal_path / "Contents" / "Home")


    elif system == "Linux":
        logger.debug("-> Recherche Linux...")
        linux_paths_str = ["/usr/lib/jvm", "/usr/java", "/opt/java", "/usr/local/lib/jvm", "/opt/jdk", "/opt/jdks", "/opt/graalvm"]
        for base_path_str in linux_paths_str:
            base_path_p = pathlib.Path(base_path_str)
            if base_path_p.is_dir():
                logger.debug(f"  Scan du dossier: {base_path_p}")
                potential_homes_dirs.extend(base_path_p.glob("java-*"))
                potential_homes_dirs.extend(base_path_p.glob("jdk*"))
                potential_homes_dirs.extend(base_path_p.glob("jre*"))
                potential_homes_dirs.extend(base_path_p.glob("openjdk*"))
                potential_homes_dirs.extend(base_path_p.glob("zulu*"))
                potential_homes_dirs.extend(base_path_p.glob("corretto*"))
                potential_homes_dirs.extend(base_path_p.glob("semeru*"))
                potential_homes_dirs.extend(base_path_p.glob("liberica*"))
                potential_homes_dirs.extend(base_path_p.glob("graalvm*"))


    unique_potential_homes = sorted(list(set(p for p in potential_homes_dirs if p.is_dir())), key=lambda p: p.name, reverse=True)

    if unique_potential_homes:
        logger.info(f"  {len(unique_potential_homes)} installations Java potentielles (uniques, dossiers) trouvées par heuristique.")
        
        suitable_java_candidates = [] # Candidats >= MIN_JAVA_VERSION
        other_valid_candidates = []   # Candidats valides mais < MIN_JAVA_VERSION (pour fallback)
        
        logger.info(f"  Filtrage et validation des candidats Java (recherche >= {MIN_JAVA_VERSION})...")
        for home_candidate_path in unique_potential_homes:
            actual_home = home_candidate_path
            # Ajustements spécifiques OS (macOS .jdk, Homebrew, GraalVM)
            if system == "Darwin":
                if home_candidate_path.name.endswith(".jdk") and (home_candidate_path / "Contents" / "Home").is_dir():
                    actual_home = home_candidate_path / "Contents" / "Home"
                elif "Cellar" in str(home_candidate_path) and ("openjdk" in home_candidate_path.parent.name or "graalvm" in home_candidate_path.parent.name):
                    if (home_candidate_path / "libexec" / "openjdk.jdk" / "Contents" / "Home").is_dir(): # OpenJDK
                         actual_home = home_candidate_path / "libexec" / "openjdk.jdk" / "Contents" / "Home"
                    elif (home_candidate_path / "Contents" / "Home").is_dir(): # GraalVM ou autre
                         actual_home = home_candidate_path / "Contents" / "Home"
            
            java_exe = actual_home / "bin" / f"java{exe_suffix}"
            if java_exe.is_file():
                path_name_lower = actual_home.name.lower()
                version_in_name = -1
                try:
                    import re
                    # Regex améliorée pour extraire la version majeure (ex: jdk-17.0.1 -> 17, java-21-openjdk -> 21)
                    # Prend en compte les numéros seuls (11, 15, 21), ou avec préfixe (jdk-17, openjdk-11)
                    # ou avec séparateurs (java-11-openjdk, corretto-17.0.3)
                    match = re.search(r'(?:jdk-|jre-|java-|openjdk-|corretto-|zulu-|semeru-|liberica-|graalvm-ce-java)?(\d{1,2})(?:[.\-_]|$)', path_name_lower)
                    if not match and "jdk" in path_name_lower: # Cas comme "jdk17" sans séparateur
                         match = re.search(r'jdk(\d+)', path_name_lower)
                    if match:
                        version_in_name = int(match.group(1))
                except: # noqa
                    pass

                if version_in_name >= MIN_JAVA_VERSION:
                    logger.debug(f"    -> Candidat Java >= {MIN_JAVA_VERSION} (version {version_in_name} déduite, avec bin/java) trouvé: {actual_home}")
                    suitable_java_candidates.append(actual_home)
                elif version_in_name != -1: # Version déduite mais < MIN_JAVA_VERSION
                    logger.debug(f"    -> Candidat Java (version {version_in_name} déduite, < {MIN_JAVA_VERSION}, avec bin/java) trouvé: {actual_home}. Conservé pour fallback.")
                    other_valid_candidates.append(actual_home)
                else: # Impossible de déduire, on ne le considère pas prioritaire
                    logger.debug(f"    -> Candidat Java (version non déduite, avec bin/java) trouvé: {actual_home}. Conservé pour fallback si aucune version >= {MIN_JAVA_VERSION} n'est trouvée.")
                    other_valid_candidates.append(actual_home) # Peut être utilisé en dernier recours
            else:
                logger.debug(f"    -> 'bin/java{exe_suffix}' non trouvé dans {actual_home} (candidat ignoré).")
        
        # Trier les candidats valides (>= MIN_JAVA_VERSION) par version (plus haute d'abord), puis par nom
        suitable_java_candidates.sort(key=lambda x: (
            int(re.search(r'(\d+)', x.name.lower()).group(1)) if re.search(r'(\d+)', x.name.lower()) else 0,
            x.name
        ), reverse=True)
        
        if suitable_java_candidates:
            selected_java = suitable_java_candidates[0]
            logger.info(f"🎉 Java >= {MIN_JAVA_VERSION} trouvé par heuristique: '{selected_java}'. Utilisation.")
            return str(selected_java)
        else:
            logger.info(f"  Aucune installation Java >= {MIN_JAVA_VERSION} valide trouvée par heuristique.")
        
        # Fallback 1: Utiliser JAVA_HOME s'il était valide mais < MIN_JAVA_VERSION (et pas déjà retourné)
        if java_home_from_env_fallback:
            logger.info(f"✔️ JAVA_HOME ('{java_home_from_env_fallback}') était valide (mais < {MIN_JAVA_VERSION}), utilisation en fallback (après heuristique Java >= {MIN_JAVA_VERSION}).")
            return java_home_from_env_fallback

        # Fallback 2: Utiliser une autre version valide (< MIN_JAVA_VERSION) trouvée par heuristique (la plus récente par nom/version)
        if other_valid_candidates:
            other_valid_candidates.sort(key=lambda x: (
                int(re.search(r'(\d+)', x.name.lower()).group(1)) if re.search(r'(\d+)', x.name.lower()) else 0,
                x.name
            ), reverse=True)
            selected_other_home = other_valid_candidates[0]
            logger.info(f"✔️ Aucun Java >= {MIN_JAVA_VERSION} trouvé, utilisation d'une autre version Java valide trouvée par heuristique: '{selected_other_home}'.")
            return str(selected_other_home)
        
        logger.warning(f"⚠️ Heuristique a trouvé des dossiers Java mais aucun avec 'bin/java' valide (ni >= {MIN_JAVA_VERSION}, ni autre).")

    # Si aucune heuristique n'a rien donné, mais que JAVA_HOME était valide (et < MIN_JAVA_VERSION, et pas déjà retourné)
    elif java_home_from_env_fallback:
        logger.info(f"✔️ Aucune installation trouvée par heuristique, mais JAVA_HOME ('{java_home_from_env_fallback}') était valide (< {MIN_JAVA_VERSION}). Utilisation.")
        return java_home_from_env_fallback
    else:
        logger.info(f"  Aucune installation Java trouvée via heuristiques et JAVA_HOME non défini, non valide, ou déjà traité comme non prioritaire.")

    logger.error(f"❌ Recherche finale: Aucun répertoire Java Home valide n'a pu être localisé (Java >= {MIN_JAVA_VERSION} priorisé, puis autres).")
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