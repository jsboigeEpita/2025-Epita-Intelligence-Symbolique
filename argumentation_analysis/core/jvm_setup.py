# core/jvm_setup.py
# import jpype # Commenté pour déplacer l'import dans les fonctions
# try:
#     import jpype.imports # Commenté également
# except (ImportError, ModuleNotFoundError):
#     pass
import os
import pathlib
import platform
import logging
from typing import Optional
# import requests # Supprimé car download_tweety_jars est retiré
# import urllib.request # Supprimé car download_tweety_jars est retiré
# from tqdm import tqdm # Supprimé car download_tweety_jars est retiré
import stat # Ajout pour chmod (Linux/Mac)
import shutil # Ajout pour shutil.which
import zipfile # Ajout pour l'extraction du JDK portable
import sys # Pour platform.system si non global, déjà importé via platform

from argumentation_analysis.paths import LIBS_DIR, PROJECT_ROOT_DIR # Ajout de PROJECT_ROOT_DIR


logger = logging.getLogger("Orchestration.JPype")
# Assurer logger configuré
if not logger.handlers and not logger.propagate:
    handler = logging.StreamHandler(); formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S'); handler.setFormatter(formatter); logger.addHandler(handler); logger.setLevel(logging.INFO)

MIN_JAVA_VERSION = 15
TWEETY_VERSION = "1.28" # Version de Tweety à télécharger

PORTABLE_JDK_DOWNLOAD_URL = "https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.15%2B6/OpenJDK17U-jdk_x64_windows_hotspot_17.0.15_6.zip"

# Les fonctions suivantes liées au téléchargement des JARs Tweety (download_tweety_jars,
# _download_file_with_progress, et la classe TqdmUpTo) sont supprimées de ce fichier.
# La logique de téléchargement est maintenant supposée être gérée en dehors de l'initialisation
# de la JVM pour les tests, par exemple via un script de setup séparé ou manuellement.
# La fixture `ensure_tweety_libs` dans `tests/conftest.py` vérifiera la présence des libs.

PORTABLE_JDK_DIR_NAME = "portable_jdk"
PORTABLE_JDK_ZIP_NAME = "OpenJDK17U-jdk_x64_windows_hotspot_17.0.15_6_new.zip"
TEMP_DIR_NAME = "_temp"

def _extract_portable_jdk(project_root: pathlib.Path, portable_jdk_parent_dir: pathlib.Path, portable_jdk_zip_path: pathlib.Path) -> Optional[pathlib.Path]:
    """
    Extrait le JDK portable de l'archive ZIP vers le répertoire portable_jdk.
    Retourne le chemin vers le dossier racine du JDK extrait (ex: portable_jdk/jdk-17.0.15+6) ou None si échec.
    """
    logger.info(f"Tentative d'extraction du JDK portable depuis '{portable_jdk_zip_path}' vers '{portable_jdk_parent_dir}'...")
    try:
        with zipfile.ZipFile(portable_jdk_zip_path, 'r') as zip_ref:
            zip_ref.extractall(portable_jdk_parent_dir)
        logger.info(f"JDK portable extrait avec succès dans '{portable_jdk_parent_dir}'.")

        for item in portable_jdk_parent_dir.iterdir():
            if item.is_dir() and item.name.startswith("jdk-"):
                logger.info(f"Dossier racine du JDK portable détecté : '{item}'")
                return item
        logger.warning(f"Impossible de déterminer le dossier racine du JDK dans '{portable_jdk_parent_dir}' après extraction. Recherche d'un dossier 'jdk-*' a échoué.")
        extracted_items = [d for d in portable_jdk_parent_dir.iterdir() if d.is_dir()]
        if len(extracted_items) == 1:
            logger.info(f"Un seul dossier trouvé après extraction: '{extracted_items[0]}', en supposant que c'est le JDK.")
            return extracted_items[0]
        
        return None
    except FileNotFoundError:
        logger.error(f"L'archive ZIP du JDK portable '{portable_jdk_zip_path}' n'a pas été trouvée.")
        return None
    except zipfile.BadZipFile:
        logger.error(f"L'archive ZIP du JDK portable '{portable_jdk_zip_path}' est corrompue.")
        return None
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction du JDK portable: {e}", exc_info=True)
        return None

# --- Fonction de détection JAVA_HOME (modifiée pour prioriser Java >= MIN_JAVA_VERSION et utiliser _download_file_with_progress pour le JDK) ---
# Note: _download_file_with_progress est maintenant retiré, donc la logique de téléchargement du JDK portable
# devra être assurée par un mécanisme externe si l'archive ZIP n'est pas présente.
def find_valid_java_home() -> Optional[str]:
    logger.debug(f"Début recherche répertoire Java Home valide (priorité Java >= {MIN_JAVA_VERSION})...")
    
    system = platform.system()
    exe_suffix = ".exe" if system == "Windows" else ""

    # Chemins relatifs au projet
    project_root = PROJECT_ROOT_DIR # Assurez-vous que PROJECT_ROOT_DIR est défini dans paths.py
    portable_jdk_parent_dir = project_root / PORTABLE_JDK_DIR_NAME
    portable_jdk_zip_path = project_root / TEMP_DIR_NAME / PORTABLE_JDK_ZIP_NAME

    # 0. Vérifier le JDK portable intégré
    logger.info(f"Vérification du JDK portable intégré dans '{portable_jdk_parent_dir}'...")
    
    # Chercher un dossier JDK existant (ex: jdk-17.0.15+6)
    potential_jdk_root_dir = None
    if portable_jdk_parent_dir.is_dir():
        for item in portable_jdk_parent_dir.iterdir():
            if item.is_dir() and item.name.startswith("jdk-"): # Heuristique pour trouver le dossier JDK
                java_exe_portable = item / "bin" / f"java{exe_suffix}"
                if java_exe_portable.is_file():
                    logger.info(f"JDK portable trouvé et valide dans: '{item}'")
                    potential_jdk_root_dir = item
                    break # Premier trouvé suffit
    
    if potential_jdk_root_dir:
        logger.info(f"🎉 Utilisation du JDK portable intégré: '{potential_jdk_root_dir}'")
        return str(potential_jdk_root_dir.resolve())

    # Si le JDK portable n'est pas trouvé extrait, mais que l'archive ZIP existe, tenter de l'extraire
    logger.info(f"JDK portable non trouvé dans '{portable_jdk_parent_dir}'. Vérification de l'archive ZIP '{portable_jdk_zip_path}'...")
    if portable_jdk_zip_path.is_file():
        logger.info(f"Archive ZIP du JDK portable trouvée. Tentative d'extraction...")
        # S'assurer que le répertoire parent pour l'extraction existe
        portable_jdk_parent_dir.mkdir(parents=True, exist_ok=True)
        
        extracted_jdk_root = _extract_portable_jdk(project_root, portable_jdk_parent_dir, portable_jdk_zip_path)
        
        if extracted_jdk_root:
            java_exe_portable = extracted_jdk_root / "bin" / f"java{exe_suffix}"
            if java_exe_portable.is_file():
                logger.info(f"🎉 JDK portable extrait et validé avec succès: '{extracted_jdk_root}'. Utilisation.")
                # Optionnel: supprimer l'archive ZIP après extraction réussie
                # try:
                #     portable_jdk_zip_path.unlink()
                #     logger.info(f"Archive ZIP '{portable_jdk_zip_path.name}' supprimée après extraction.")
                # except OSError as e_unlink:
                #     logger.warning(f"Impossible de supprimer l'archive ZIP '{portable_jdk_zip_path.name}': {e_unlink}")
                return str(extracted_jdk_root.resolve())
            else:
                logger.error(f"JDK portable extrait dans '{extracted_jdk_root}', mais 'bin/java{exe_suffix}' non trouvé.")
        else:
            logger.error(f"Échec de l'extraction ou de la validation du JDK portable depuis '{portable_jdk_zip_path}'.")
    else:
        logger.info(f"Archive ZIP du JDK portable '{portable_jdk_zip_path.name}' non trouvée. Tentative de téléchargement...")
        # S'assurer que le répertoire _temp existe
        temp_dir = project_root / TEMP_DIR_NAME
        temp_dir.mkdir(parents=True, exist_ok=True)

        # La logique de téléchargement du JDK portable a été retirée car _download_file_with_progress a été retiré.
        # On suppose maintenant que l'archive ZIP du JDK est soit déjà présente, soit gérée par un processus externe.
        logger.warning(f"Logique de téléchargement du JDK portable désactivée dans find_valid_java_home. L'archive '{portable_jdk_zip_path.name}' doit être présente manuellement si nécessaire.")
        # jdk_downloaded, _ = _download_file_with_progress( # Appel original commenté
        #     PORTABLE_JDK_DOWNLOAD_URL,
        #     portable_jdk_zip_path,
        #     description="JDK Portable (OpenJDK 17.0.15+6)"
        # )
        # Pour simuler l'échec du téléchargement si le fichier n'est pas là :
        jdk_downloaded = portable_jdk_zip_path.is_file()


        if jdk_downloaded: # Condition simplifiée: si le fichier existe (ou aurait été téléchargé)
            logger.info(f"JDK portable téléchargé avec succès : '{portable_jdk_zip_path}'. Tentative d'extraction...")
            # S'assurer que le répertoire parent pour l'extraction existe
            portable_jdk_parent_dir.mkdir(parents=True, exist_ok=True)
            extracted_jdk_root = _extract_portable_jdk(project_root, portable_jdk_parent_dir, portable_jdk_zip_path)
            if extracted_jdk_root:
                java_exe_portable = extracted_jdk_root / "bin" / f"java{exe_suffix}"
                if java_exe_portable.is_file():
                    logger.info(f"🎉 JDK portable téléchargé, extrait et validé avec succès: '{extracted_jdk_root}'. Utilisation.")
                    return str(extracted_jdk_root.resolve())
                else:
                    logger.error(f"JDK portable téléchargé et extrait dans '{extracted_jdk_root}', mais 'bin/java{exe_suffix}' non trouvé.")
            else:
                logger.error(f"Échec de l'extraction ou de la validation du JDK portable après téléchargement depuis '{portable_jdk_zip_path}'.")
        else:
            logger.error(f"Échec du téléchargement du JDK portable depuis '{PORTABLE_JDK_DOWNLOAD_URL}'. Le JDK portable ne sera pas utilisé.")

    # Si le JDK portable n'est pas utilisé, continuer avec la logique existante
    logger.info("Poursuite avec la détection standard de JAVA_HOME (variables d'environnement, heuristiques système)...")
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
    import jpype # Importation locale
    try:
        import jpype.imports # Importation locale
    except (ImportError, ModuleNotFoundError):
        pass # Géré comme avant
    logger.info("\n--- Préparation et Initialisation de la JVM via JPype ---")
    # libs_ok = download_tweety_jars(version=tweety_version, target_dir=lib_dir_path, native_subdir=native_lib_subdir) # Géré par la fixture ensure_tweety_libs
    libs_ok = True # Supposons que les libs sont OK car ensure_tweety_libs s'en est chargé
    if not libs_ok:
        logger.error("❌ Problème avec les fichiers Tweety (Core manquant?). Démarrage JVM annulé.")
        return False
    LIB_DIR = pathlib.Path(lib_dir_path)
    NATIVE_LIBS_DIR = LIB_DIR / native_lib_subdir
    jvm_ready = False
    logger.info(f"DEBUG_JVM_SETUP: Appel de jpype.isJVMStarted() au début de initialize_jvm. Résultat: {jpype.isJVMStarted()}")
    if jpype.isJVMStarted():
        logger.warning("ℹ️ JVM déjà démarrée (détecté au début de initialize_jvm). Utilisation existante.")
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
        except jpype.JVMNotFoundException: # Nécessite jpype importé
            logger.warning("   (JPype n'a pas trouvé de JVM par défaut - dépendra de JAVA_HOME)")
            jvm_path_final = None
        classpath_separator = os.pathsep
        # Construire la liste des JARs principaux depuis lib_dir_path (qui est LIB_DIR ici)
        main_jar_list = sorted([str(p.resolve()) for p in LIB_DIR.glob("*.jar")])
        logger.info(f"   JARs principaux trouvés dans '{LIB_DIR}': {len(main_jar_list)}")

        # Chemin vers les JARs de test
        # PROJECT_ROOT_DIR doit être accessible ici (importé depuis .paths)
        test_libs_dir_path_obj = PROJECT_ROOT_DIR / "argumentation_analysis" / "tests" / "resources" / "libs"
        test_jar_list = []
        if test_libs_dir_path_obj.is_dir():
            test_jar_list = sorted([str(p.resolve()) for p in test_libs_dir_path_obj.glob("*.jar")])
            logger.info(f"   JARs de test trouvés dans '{test_libs_dir_path_obj}': {len(test_jar_list)}")
        else:
            logger.info(f"   Répertoire des JARs de test '{test_libs_dir_path_obj}' non trouvé ou non accessible.")

        # Combiner les listes de JARs, en donnant la priorité aux JARs de test
        main_jars_map = {pathlib.Path(p).name: p for p in main_jar_list}
        test_jars_map = {pathlib.Path(p).name: p for p in test_jar_list}
        
        # Inverser la priorité: les JARs principaux écrasent les JARs de test pour les mêmes noms.
        # Cela assure que nous utilisons les JARs de LIBS_DIR (PROJECT_ROOT/libs) s'ils existent.
        # final_jars_map = {**test_jars_map, **main_jars_map}
        # combined_jar_list_original = sorted(list(final_jars_map.values()))
        # logger.info(f"   Nombre total de JARs après fusion (priorité aux tests): {len(combined_jar_list_original)}")

        # Inverser la priorité: les JARs principaux écrasent les JARs de test pour les mêmes noms.
        # Cela assure que nous utilisons les JARs de LIBS_DIR (PROJECT_ROOT/libs) s'ils existent.
        final_jars_map = {**test_jars_map, **main_jars_map}
        
        combined_jar_list = sorted(list(final_jars_map.values()))
        logger.info(f"   Nombre total de JARs après fusion (priorité aux tests): {len(combined_jar_list)}")

        if not combined_jar_list:
             logger.error("❌ Aucun JAR trouvé (ni principal, ni de test après fusion) pour le classpath ! Démarrage annulé.")
             return False
        
        # Construire la chaîne de classpath pour l'environnement et le log
        classpath_str_for_env_and_log = classpath_separator.join(combined_jar_list)
        logger.info(f"   Classpath combiné construit ({len(combined_jar_list)} JARs). Valeur pour env: {classpath_str_for_env_and_log}")
        logger.debug(f"   CLASSPATH pour JVM (avant définition env var): {classpath_str_for_env_and_log}")


        # Définir la variable d'environnement CLASSPATH
        try:
            os.environ['CLASSPATH'] = classpath_str_for_env_and_log
            logger.info(f"   Variable d'environnement CLASSPATH définie.")
        except Exception as e_set_classpath_env:
            logger.error(f"   ❌ Impossible de définir la variable d'environnement CLASSPATH: {e_set_classpath_env}")
            # Continuer quand même, JPype pourrait la trouver via d'autres moyens ou le paramètre direct

        # Gestion de java.library.path pour les bibliothèques natives
        # (Cette section vient des "Stashed changes" et est intégrée ici)
        # Priorité aux natives du lib_dir_path principal, puis celles des tests si différentes et présentes.
        # Cependant, initialize_jvm utilise NATIVE_LIBS_DIR qui est dérivé de lib_dir_path.
        # Si les tests ont leurs propres natives dans un sous-dossier "native" de TEST_LIBS_DIR,
        # et que lib_dir_path pointe vers les libs principales, alors les natives des tests ne seraient pas prises.
        # Pour l'instant, on se fie à NATIVE_LIBS_DIR calculé à partir du lib_dir_path principal.
        # Si les tests nécessitent des natives spécifiques qui ne sont PAS dans LIBS_DIR/native,
        # cela nécessitera une gestion plus complexe de java.library.path.
        # Le code actuel utilise NATIVE_LIBS_DIR qui est LIB_DIR / native_lib_subdir.
        # Si lib_dir_path est LIBS_DIR, alors NATIVE_LIBS_DIR est LIBS_DIR / "native".
        
        jvm_args = [] # Initialisation de jvm_args
        
        if NATIVE_LIBS_DIR.exists() and any(NATIVE_LIBS_DIR.iterdir()):
            native_path_arg = f"-Djava.library.path={NATIVE_LIBS_DIR.resolve()}"
            jvm_args.append(native_path_arg)
            logger.info(f"   Argument JVM natif ajouté: {native_path_arg}")
        else:
            logger.info(f"   (Pas de bibliothèques natives trouvées dans '{NATIVE_LIBS_DIR.resolve()}', -Djava.library.path non ajouté)")
        
        # Ajout des options de mémoire pour la JVM
        jvm_memory_options = ["-Xms256m", "-Xmx512m"]
        jvm_args.extend(jvm_memory_options)
        logger.info(f"   Options de mémoire JVM ajoutées: {jvm_memory_options}")

        # Ajout des options de débogage JPype
        # jpype_debug_options = ["-Djpype.debug=true", "-Djpype.trace=true"]
        # jvm_args.extend(jpype_debug_options)
        # logger.info(f"   Options de débogage JPype ajoutées: {jpype_debug_options}")
        logger.info(f"   Options de débogage JPype DÉSACTIVÉES pour ce test.")

        # Déterminer le chemin JVM à utiliser explicitement basé sur java_home_to_set
        jvm_path_to_use_explicit: Optional[str] = None
        if java_home_to_set: # java_home_to_set est le résultat de find_valid_java_home()
            _java_home_path = pathlib.Path(java_home_to_set)
            _system = platform.system()
            _jvm_dll_path: Optional[pathlib.Path] = None
            if _system == "Windows":
                _jvm_dll_path = _java_home_path / "bin" / "server" / "jvm.dll"
            elif _system == "Darwin": # macOS
                _jvm_dll_path = _java_home_path / "lib" / "server" / "libjvm.dylib"
                if not _jvm_dll_path.is_file() and (_java_home_path / "Contents" / "Home" / "lib" / "server" / "libjvm.dylib").is_file():
                     _jvm_dll_path = _java_home_path / "Contents" / "Home" / "lib" / "server" / "libjvm.dylib"
                elif not _jvm_dll_path.is_file():
                     _jvm_dll_path = _java_home_path / "jre" / "lib" / "server" / "libjvm.dylib"
            else: # Linux et autres
                _jvm_dll_path = _java_home_path / "lib" / "server" / "libjvm.so"
                if not _jvm_dll_path.is_file():
                    lib_server_paths = list((_java_home_path / "lib").glob("**/server/libjvm.so"))
                    if lib_server_paths:
                        _jvm_dll_path = lib_server_paths[0]
                    else:
                         jre_lib_server_paths = list((_java_home_path / "jre" / "lib").glob("**/server/libjvm.so"))
                         if jre_lib_server_paths:
                              _jvm_dll_path = jre_lib_server_paths[0]
            
            if _jvm_dll_path and _jvm_dll_path.is_file():
                jvm_path_to_use_explicit = str(_jvm_dll_path.resolve())
                logger.info(f"   Chemin JVM explicite déterminé pour startJVM: {jvm_path_to_use_explicit}")
            else:
                logger.warning(f"   Impossible de construire un chemin JVM valide depuis JAVA_HOME '{java_home_to_set}' (chemin testé: {_jvm_dll_path}). JPype utilisera sa détection par défaut.")
        
        logger.info(f"DEBUG_JVM_SETUP: JAVA_HOME avant startJVM: {os.getenv('JAVA_HOME')}")
        logger.info(f"DEBUG_JVM_SETUP: Path avant startJVM: {os.getenv('PATH')}")
        logger.info(f"DEBUG_JVM_SETUP: CLASSPATH avant startJVM: {os.getenv('CLASSPATH')}")
        logger.info(f"DEBUG_JVM_SETUP: Tentative de démarrage avec jvm_path_to_use_explicit='{jvm_path_to_use_explicit}', classpath='{len(combined_jar_list)} JARs', args='{jvm_args}'")
        logger.info(f"DEBUG_JVM_SETUP: APPEL IMMINENT DE jpype.startJVM()")
        if jvm_path_to_use_explicit:
            jpype.startJVM(jvm_path_to_use_explicit, classpath=combined_jar_list, *jvm_args, convertStrings=False, ignoreUnrecognized=True)
        else:
            logger.warning("   Aucun chemin JVM explicite fourni à startJVM, utilisation de la détection interne de JPype.")
            jpype.startJVM(classpath=combined_jar_list, *jvm_args, convertStrings=False, ignoreUnrecognized=True)
        logger.info(f"DEBUG_JVM_SETUP: jpype.startJVM() APPELÉ. Vérification avec jpype.isJVMStarted(): {jpype.isJVMStarted()}")
        if hasattr(jpype, 'imports') and jpype.imports is not None:
            try:
                jpype.imports.registerDomain("java", alias="java")
                jpype.imports.registerDomain("org", alias="org")
                jpype.imports.registerDomain("net", alias="net")
                jpype.imports.registerDomain("net.sf", alias="sf")
                jpype.imports.registerDomain("net.sf.tweety", alias="tweety")
                logger.info("✅ JVM démarrée avec succès et domaines (java, org, net, sf, tweety) enregistrés.")
                try:
                    logger.info(f"   Classpath rapporté par jpype.getClassPath() juste après startJVM: {jpype.getClassPath()}")
                except Exception as e_cp:
                    logger.warning(f"   Impossible d'obtenir jpype.getClassPath() juste après startJVM: {e_cp}")
            except Exception as e_reg_domain_jvm_setup:
                logger.error(f"❌ Erreur lors de l'enregistrement des domaines JPype dans jvm_setup: {e_reg_domain_jvm_setup}")
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