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

PORTABLE_JDK_DOWNLOAD_URL = "https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.10%2B7/OpenJDK17U-jdk_x64_windows_hotspot_17.0.10_7.zip"
# Note: Utilisation d'une version légèrement plus ancienne pour tester (17.0.10+7 au lieu de 17.0.15+6)

# Les fonctions suivantes liées au téléchargement des JARs Tweety (download_tweety_jars,
# _download_file_with_progress, et la classe TqdmUpTo) sont supprimées de ce fichier.
# La logique de téléchargement est maintenant supposée être gérée en dehors de l'initialisation
# de la JVM pour les tests, par exemple via un script de setup séparé ou manuellement.
# La fixture `ensure_tweety_libs` dans `tests/conftest.py` vérifiera la présence des libs.

PORTABLE_JDK_DIR_NAME = "portable_jdk"
PORTABLE_JDK_ZIP_NAME = "OpenJDK17U-jdk_x64_windows_hotspot_17.0.10_7.zip"
TEMP_DIR_NAME = "_temp"

def _check_java_version_and_path(java_home_candidate: str, exe_suffix: str) -> Optional[str]:
    """Vérifie si le java_home_candidate est valide et contient une version de Java suffisante."""
    import subprocess
    java_home_path = pathlib.Path(java_home_candidate)
    if not java_home_path.is_dir():
        logger.debug(f"  '{java_home_candidate}' n'est pas un répertoire.")
        return None

    java_exe = java_home_path / "bin" / f"java{exe_suffix}"
    if not java_exe.is_file():
        logger.debug(f"  Exécutable Java non trouvé à '{java_exe}'.")
        # Sur macOS, JAVA_HOME peut pointer vers le dossier "Home" à l'intérieur du bundle .app
        if platform.system() == "Darwin" and (java_home_path / "Contents" / "Home" / "bin" / f"java{exe_suffix}").is_file():
            java_exe = java_home_path / "Contents" / "Home" / "bin" / f"java{exe_suffix}"
            java_home_path = java_home_path / "Contents" / "Home" # Ajuster java_home_path pour refléter le vrai JAVA_HOME
            logger.debug(f"  Exécutable Java trouvé dans la structure .app macOS à '{java_exe}'. JAVA_HOME ajusté à '{java_home_path}'")
        elif (java_home_path / "jre" / "bin" / f"java{exe_suffix}").is_file(): # Structure alternative avec JRE
             java_exe = java_home_path / "jre" / "bin" / f"java{exe_suffix}"
             logger.debug(f"  Exécutable Java trouvé dans jre/bin à '{java_exe}'.")
        else:
            return None

    try:
        result = subprocess.run([str(java_exe), "-version"], capture_output=True, text=True, check=False, timeout=10)
        version_output = result.stderr # Java version est souvent sur stderr
        
        if result.returncode != 0:
            logger.warning(f"  Échec de l'exécution de '{java_exe} -version'. Code de retour: {result.returncode}. Sortie: {version_output or result.stdout}")
            return None

        first_line = version_output.splitlines()[0] if version_output else ""
        version_str_parts = first_line.split('"')
        if len(version_str_parts) > 1:
            version_str = version_str_parts[1]
            major_version_str = version_str.split('.')[0]
            if major_version_str.startswith("1."): # Pour Java 8 (1.8), Java 7 (1.7) etc.
                major_version_str = version_str.split('.')[1]

            try:
                major_version = int(major_version_str)
                if major_version >= MIN_JAVA_VERSION:
                    logger.info(f"  Version Java {major_version} (>= {MIN_JAVA_VERSION}) trouvée à '{java_home_path}' (via '{java_exe}').")
                    return str(java_home_path.resolve())
                else:
                    logger.debug(f"  Version Java {major_version} (< {MIN_JAVA_VERSION}) trouvée à '{java_home_path}'. Ignoré.")
            except ValueError:
                logger.warning(f"  Impossible d'analyser la version majeure depuis '{version_str}' à '{java_home_path}'.")
        else:
            logger.warning(f"  Format de sortie de version Java inattendu à '{java_home_path}': {version_output}")
    except subprocess.TimeoutExpired:
        logger.warning(f"  Timeout lors de l'exécution de '{java_exe} -version'.")
    except Exception as e:
        logger.warning(f"  Erreur lors de la vérification de la version Java à '{java_home_path}': {e}")
    return None

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

def find_valid_java_home() -> Optional[str]:
    logger.debug(f"Début recherche répertoire Java Home valide (priorité Java >= {MIN_JAVA_VERSION})...")
    
    system = platform.system()
    exe_suffix = ".exe" if system == "Windows" else ""
    
    # 1. Vérifier les variables d'environnement JAVA_HOME et JDK_HOME
    env_vars_to_check = ["JAVA_HOME", "JDK_HOME"]
    logger.debug(f"Vérification des variables d'environnement: {env_vars_to_check}")
    for var_name in env_vars_to_check:
        java_home_env = os.getenv(var_name)
        if java_home_env:
            logger.debug(f"  Variable '{var_name}' trouvée: '{java_home_env}'")
            valid_path = _check_java_version_and_path(java_home_env, exe_suffix)
            if valid_path:
                logger.info(f"🎉 Utilisation de {var_name} pointant vers un JDK valide: '{valid_path}'")
                return valid_path
        else:
            logger.debug(f"  Variable '{var_name}' non définie.")

    # 2. Essayer de trouver 'java' dans le PATH et remonter au JAVA_HOME
    logger.debug("Vérification du PATH système pour 'java'...")
    java_exe_path_str = shutil.which(f"java{exe_suffix}")
    if java_exe_path_str:
        java_exe_path = pathlib.Path(java_exe_path_str)
        logger.debug(f"  Exécutable 'java' trouvé dans le PATH: '{java_exe_path}'")
        try:
            # Tenter de résoudre le lien symbolique (surtout pour Linux/macOS)
            resolved_java_exe_path = java_exe_path.resolve(strict=True)
            logger.debug(f"  Chemin résolu de 'java': '{resolved_java_exe_path}'")
            # Remonter au dossier JAVA_HOME (typiquement ../.. depuis bin/java ou ../../.. pour Contents/Home/bin/java sur macOS)
            potential_java_home = resolved_java_exe_path.parent.parent # bin -> java_home
            if potential_java_home.name == "Home" and potential_java_home.parent.name == "Contents": # Cas macOS .app
                potential_java_home = potential_java_home.parent.parent
            
            logger.debug(f"  JAVA_HOME potentiel déduit du PATH: '{potential_java_home}'")
            valid_path = _check_java_version_and_path(str(potential_java_home), exe_suffix)
            if valid_path:
                logger.info(f"🎉 Utilisation d'un JDK valide déduit du PATH: '{valid_path}'")
                return valid_path
        except Exception as e:
            logger.debug(f"  Erreur lors de la tentative de déduction de JAVA_HOME depuis le PATH '{java_exe_path}': {e}")
    else:
        logger.debug("  Exécutable 'java' non trouvé dans le PATH système.")

    # 3. Logique du JDK Portable (Fallback)
    project_root = PROJECT_ROOT_DIR
    portable_jdk_parent_dir = project_root / "libs" / PORTABLE_JDK_DIR_NAME
    portable_jdk_zip_path = project_root / TEMP_DIR_NAME / PORTABLE_JDK_ZIP_NAME
    logger.info(f"Aucun JDK système valide trouvé. Tentative d'utilisation du JDK portable intégré situé dans '{portable_jdk_parent_dir}'...")
    potential_jdk_root_dir = None
    if portable_jdk_parent_dir.is_dir():
        for item in portable_jdk_parent_dir.iterdir():
            if item.is_dir() and item.name.startswith("jdk-"):
                java_exe_portable = item / "bin" / f"java{exe_suffix}"
                if java_exe_portable.is_file():
                    logger.info(f"JDK portable trouvé et valide dans: '{item}'")
                    potential_jdk_root_dir = item
                    break # Utiliser le premier trouvé
    
    if potential_jdk_root_dir:
        # Vérifier la version du JDK portable également, par cohérence
        valid_portable_path = _check_java_version_and_path(str(potential_jdk_root_dir), exe_suffix)
        if valid_portable_path:
            logger.info(f"🎉 Utilisation du JDK portable intégré: '{valid_portable_path}'")
            return valid_portable_path
        else:
            logger.warning(f"JDK portable trouvé à '{potential_jdk_root_dir}' mais sa version n'est pas valide ou n'a pu être vérifiée.")


    logger.info(f"JDK portable non trouvé ou non validé dans '{portable_jdk_parent_dir}'. Vérification de l'archive ZIP '{portable_jdk_zip_path}'...")
    if portable_jdk_zip_path.is_file():
        logger.info(f"Archive ZIP du JDK portable trouvée. Tentative d'extraction...")
        portable_jdk_parent_dir.mkdir(parents=True, exist_ok=True)
        extracted_jdk_root = _extract_portable_jdk(project_root, portable_jdk_parent_dir, portable_jdk_zip_path)
        
        if extracted_jdk_root:
            valid_extracted_path = _check_java_version_and_path(str(extracted_jdk_root), exe_suffix)
            if valid_extracted_path:
                logger.info(f"🎉 JDK portable extrait et validé avec succès: '{valid_extracted_path}'. Utilisation.")
                return valid_extracted_path
            else:
                logger.error(f"JDK portable extrait dans '{extracted_jdk_root}', mais sa version n'est pas valide ou 'bin/java{exe_suffix}' non trouvé/vérifiable.")
        else:
            logger.error(f"Échec de l'extraction du JDK portable depuis '{portable_jdk_zip_path}'.")
    else:
        logger.info(f"Archive ZIP du JDK portable '{portable_jdk_zip_path.name}' non trouvée. Tentative de téléchargement...")
        import urllib.request # Import local pour cette fonction
        temp_dir = project_root / TEMP_DIR_NAME
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            logger.info(f"Téléchargement de {PORTABLE_JDK_DOWNLOAD_URL} vers {portable_jdk_zip_path}...")
            # Utilisation d'un user-agent pour éviter les blocages potentiels
            hdr = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
            req = urllib.request.Request(PORTABLE_JDK_DOWNLOAD_URL, headers=hdr)
            with urllib.request.urlopen(req) as response, open(portable_jdk_zip_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
            logger.info(f"JDK portable téléchargé avec succès : '{portable_jdk_zip_path}'.")
            jdk_downloaded = True
        except Exception as e:
            logger.error(f"Échec du téléchargement du JDK portable depuis '{PORTABLE_JDK_DOWNLOAD_URL}': {e}", exc_info=True)
            jdk_downloaded = False

        if jdk_downloaded:
            logger.info(f"Tentative d'extraction après téléchargement...")
            portable_jdk_parent_dir.mkdir(parents=True, exist_ok=True) # Assurer que le parent existe
            extracted_jdk_root = _extract_portable_jdk(project_root, portable_jdk_parent_dir, portable_jdk_zip_path)
            if extracted_jdk_root:
                valid_extracted_path = _check_java_version_and_path(str(extracted_jdk_root), exe_suffix)
                if valid_extracted_path:
                    logger.info(f"🎉 JDK portable téléchargé, extrait et validé avec succès: '{valid_extracted_path}'. Utilisation.")
                    return valid_extracted_path
                else:
                    logger.error(f"JDK portable téléchargé et extrait dans '{extracted_jdk_root}', mais sa version n'est pas valide ou 'bin/java{exe_suffix}' non trouvé/vérifiable.")
            else:
                logger.error(f"Échec de l'extraction du JDK portable après téléchargement depuis '{portable_jdk_zip_path}'.")
        else:
            logger.error(f"Le JDK portable n'a pas pu être téléchargé et ne sera pas utilisé.")


    logger.error(f"❌ Recherche finale: Aucun répertoire Java Home valide (système ou portable) n'a pu être localisé ou validé (Java >= {MIN_JAVA_VERSION}).")
    return None

def _build_effective_classpath(
    lib_dir_path_str: str = str(LIBS_DIR), # Utiliser str() pour compatibilité avec pathlib.Path()
    project_root_dir_str: str = str(PROJECT_ROOT_DIR)
) -> tuple[list[str], str]:
    """
    Construit la liste des JARs pour le classpath et la chaîne de classpath.
    Retourne un tuple (liste_des_jars, chaine_classpath_formatee).
    """
    LIB_DIR = pathlib.Path(lib_dir_path_str)
    PROJECT_ROOT = pathlib.Path(project_root_dir_str)
    classpath_separator = os.pathsep

    # Construire la liste des JARs principaux depuis lib_dir_path (qui est LIB_DIR ici)
    main_jar_list = sorted([str(p.resolve()) for p in LIB_DIR.glob("*.jar")])
    logger.info(f"   _build_effective_classpath: JARs principaux trouvés dans '{LIB_DIR}': {len(main_jar_list)}")

    # --- EXCLUSION TEMPORAIREMENT RETIRÉE ---
    # jar_to_exclude = "org.tweetyproject.lp.asp-1.28-with-dependencies.jar"
    # original_main_jar_count = len(main_jar_list)
    # main_jar_list = [jar_path for jar_path in main_jar_list if jar_to_exclude not in pathlib.Path(jar_path).name]
    # if len(main_jar_list) < original_main_jar_count:
    #     logger.info(f"   _build_effective_classpath: Exclusion de '{jar_to_exclude}' retirée. Nombre de JARs principaux: {len(main_jar_list)}.")
    
    test_libs_dir_path_obj = PROJECT_ROOT / "argumentation_analysis" / "tests" / "resources" / "libs"
    test_jar_list = []
    if test_libs_dir_path_obj.is_dir():
        test_jar_list = sorted([str(p.resolve()) for p in test_libs_dir_path_obj.glob("*.jar")])
        logger.info(f"   _build_effective_classpath: JARs de test trouvés dans '{test_libs_dir_path_obj}': {len(test_jar_list)}")
    else:
        logger.info(f"   _build_effective_classpath: Répertoire des JARs de test '{test_libs_dir_path_obj}' non trouvé ou non accessible.")

    main_jars_map = {pathlib.Path(p).name: p for p in main_jar_list}
    test_jars_map = {pathlib.Path(p).name: p for p in test_jar_list}
    final_jars_map = {**test_jars_map, **main_jars_map}
    all_available_jars = sorted(list(final_jars_map.values()))
    
    logger.info("   _build_effective_classpath: Utilisation de tous les JARs disponibles (all_available_jars) pour le classpath.")
    combined_jar_list = all_available_jars

    logger.info(f"   _build_effective_classpath: Nombre total de JARs pour le classpath final: {len(combined_jar_list)}")
    if not combined_jar_list:
        logger.error("❌ _build_effective_classpath: Aucun JAR trouvé pour le classpath !")
        return [], ""
    
    logger.info(f"   _build_effective_classpath: --- Liste détaillée des JARs pour le Classpath ({len(combined_jar_list)} JARs) ---")
    for i, jar_item in enumerate(combined_jar_list):
        logger.info(f"     _build_effective_classpath: JAR {i+1}: {jar_item}")
    logger.info(f"   _build_effective_classpath: --- Fin de la liste détaillée des JARs ---")
    
    classpath_str = classpath_separator.join(combined_jar_list)
    logger.info(f"   _build_effective_classpath: Classpath combiné construit ({len(combined_jar_list)} JARs).")
    logger.debug(f"   _build_effective_classpath: CLASSPATH pour JVM: {classpath_str}")
    return combined_jar_list, classpath_str

def initialize_jvm(
    lib_dir_path: str = str(LIBS_DIR), # Assurer que c'est une chaîne
    native_lib_subdir: str = "native",
    tweety_version: str = TWEETY_VERSION,
    extra_jvm_args: Optional[list[str]] = None # Nouveau paramètre
) -> bool:
    import jpype
    try:
        import jpype.imports
    except (ImportError, ModuleNotFoundError):
        pass
    logger.info("\n--- Préparation et Initialisation de la JVM via JPype ---")
    
    LIB_DIR = pathlib.Path(lib_dir_path) # Convertir en Path ici
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
            logger.info(f"   [DEBUG] Définition de os.environ['JAVA_HOME'] temporairement DÉSACTIVÉE. jvm_path_to_use_explicit sera utilisé.")
        except Exception as e_setenv:
            logger.error(f"❌ Impossible de définir JAVA_HOME dynamiquement: {e_setenv}")
    elif not java_home_to_set:
         logger.error("❌ JAVA_HOME non trouvé. Démarrage JVM impossible.")
         return False
         
    jvm_path_final = None
    jvm_args = []
    if extra_jvm_args: # Ajout des arguments supplémentaires
        jvm_args.extend(extra_jvm_args)
        logger.info(f"   Arguments JVM supplémentaires fournis: {extra_jvm_args}")

    try:
        logger.info(f"⏳ Tentative de démarrage JVM...")
        try:
            jvm_path_final = jpype.getDefaultJVMPath()
            logger.info(f"   (Chemin JVM par défaut détecté par JPype: {jvm_path_final})")
        except jpype.JVMNotFoundException:
            logger.warning("   (JPype n'a pas trouvé de JVM par défaut - dépendra de JAVA_HOME)")
            jvm_path_final = None
        
        combined_jar_list, classpath_str_for_env_and_log = _build_effective_classpath(lib_dir_path, str(PROJECT_ROOT_DIR))
        
        if not combined_jar_list:
             return False # Erreur déjà loggée par _build_effective_classpath

        try:
            os.environ['CLASSPATH'] = classpath_str_for_env_and_log
            logger.info(f"   Variable d'environnement CLASSPATH définie.")
        except Exception as e_set_classpath_env:
            logger.error(f"   ❌ Impossible de définir la variable d'environnement CLASSPATH: {e_set_classpath_env}")
            
        # jvm_args sont déjà initialisés (et peuvent contenir extra_jvm_args)
        
        if NATIVE_LIBS_DIR.exists() and any(NATIVE_LIBS_DIR.iterdir()):
            native_path_arg = f"-Djava.library.path={NATIVE_LIBS_DIR.resolve()}"
            jvm_args.append(native_path_arg)
            logger.info(f"   Argument JVM natif ajouté: {native_path_arg}")
        else:
            logger.info(f"   (Pas de bibliothèques natives trouvées dans '{NATIVE_LIBS_DIR.resolve()}', -Djava.library.path non ajouté)")
        # logger.info(f"   [DEBUG] -Djava.library.path temporairement désactivé.") # Commenté pour réactiver
        
        # jvm_memory_options = ["-Xms256m", "-Xmx512m"]
        # jvm_args.extend(jvm_memory_options)
        # logger.info(f"   Options de mémoire JVM ajoutées: {jvm_memory_options}")
        logger.info(f"   [DEBUG] Options de mémoire JVM temporairement désactivées.")

        # Début de la section fusionnée pour Conflit 2
        # Ajout des options de débogage JVM et JPype (de origin/main)
        # Ces options sont maintenant gérées via le paramètre extra_jvm_args
        # jvm_debug_options = ["-Xcheck:jni"]
        # jpype_debug_options = ["-Djpype.debug=True", "-Djpype.jni_debug=True"]
        # if "-Xcheck:jni" not in jvm_args: # Ne pas ajouter si déjà présent via extra_jvm_args
        #    logger.info(f"   Option de débogage JVM (-Xcheck:jni) TEMPORAIREMENT DÉSACTIVÉE (ou gérée par extra_jvm_args).")
        # if not any(arg.startswith("-Djpype.debug") or arg.startswith("-Djpype.jni_debug") for arg in jvm_args):
        #    logger.info(f"   Options de débogage JPype (debug, jni_debug) TEMPORAIREMENT DÉSACTIVÉES (ou gérées par extra_jvm_args).")

        jvm_path_to_use_explicit: Optional[str] = None
        # logger.info(f"   [DEBUG] Forçage de jvm_path_to_use_explicit à None pour utiliser la détection JPype par défaut.") # Commenté pour test
        if java_home_to_set:
            _java_home_path = pathlib.Path(java_home_to_set)
            _system = platform.system()
            _jvm_dll_path: Optional[pathlib.Path] = None
            if _system == "Windows":
                _jvm_dll_path = _java_home_path / "bin" / "server" / "jvm.dll"
            elif _system == "Darwin":
                _jvm_dll_path = _java_home_path / "lib" / "server" / "libjvm.dylib"
                if not _jvm_dll_path.is_file() and (_java_home_path / "Contents" / "Home" / "lib" / "server" / "libjvm.dylib").is_file():
                     _jvm_dll_path = _java_home_path / "Contents" / "Home" / "lib" / "server" / "libjvm.dylib"
                elif not _jvm_dll_path.is_file():
                     _jvm_dll_path = _java_home_path / "jre" / "lib" / "server" / "libjvm.dylib"
            else: # Linux et autres
                _jvm_dll_path = _java_home_path / "lib" / "server" / "libjvm.so"
                if not _jvm_dll_path.is_file(): # Tentative avec jre/lib/server
                    _jvm_dll_path_jre_variant = _java_home_path / "jre" / "lib" / "server" / "libjvm.so"
                    if _jvm_dll_path_jre_variant.is_file():
                        _jvm_dll_path = _jvm_dll_path_jre_variant
                    else: # Tentatives plus génériques pour certaines distributions Linux
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
        if hasattr(jpype, 'config'):
            jpype.config.destroy_jvm = False
            logger.info(f"DEBUG_JVM_SETUP: jpype.config.destroy_jvm défini sur False.")
            # logger.info(f"DEBUG_JVM_SETUP: jpype.config.destroy_jvm NON défini sur False (utilisation du défaut JPype).")
        else:
            logger.warning("DEBUG_JVM_SETUP: jpype.config non disponible, impossible de définir destroy_jvm.")

        logger.info(f"DEBUG_JVM_SETUP: APPEL IMMINENT DE jpype.startJVM()")
        if jvm_path_to_use_explicit:
            jpype.startJVM(jvm_path_to_use_explicit, classpath=combined_jar_list, *jvm_args, convertStrings=False, ignoreUnrecognized=True)
        else:
            logger.warning("   Aucun chemin JVM explicite fourni à startJVM, utilisation de la détection interne de JPype.")
            jpype.startJVM(classpath=combined_jar_list, *jvm_args, convertStrings=False, ignoreUnrecognized=True)
        logger.info(f"DEBUG_JVM_SETUP: jpype.startJVM() APPELÉ. Vérification avec jpype.isJVMStarted(): {jpype.isJVMStarted()}")
        
        jvm_fully_initialized = False
        if jpype.isJVMStarted():
            classpath_from_jvm = None
            try:
                classpath_from_jvm = jpype.getClassPath()
                logger.info(f"   Classpath rapporté par jpype.getClassPath() juste après startJVM: {classpath_from_jvm}")
            except Exception as e_cp:
                logger.warning(f"   Impossible d'obtenir jpype.getClassPath() juste après startJVM: {e_cp}")

            if classpath_from_jvm: # Vérifier si le classpath est non vide
                if hasattr(jpype, 'imports') and jpype.imports is not None:
                    try:
                        jpype.imports.registerDomain("java", alias="java")
                        jpype.imports.registerDomain("org", alias="org")
                        jpype.imports.registerDomain("net", alias="net")
                        jpype.imports.registerDomain("net.sf", alias="sf")
                        jpype.imports.registerDomain("net.sf.tweety", alias="tweety")
                        logger.info("✅ JVM démarrée avec succès, classpath chargé ET domaines (java, org, net, sf, tweety) enregistrés.")
                        jvm_fully_initialized = True
                    except Exception as e_reg_domain_jvm_setup:
                        logger.error(f"❌ Erreur lors de l'enregistrement des domaines JPype (classpath semblait OK): {e_reg_domain_jvm_setup}")
                else:
                    logger.warning("✅ JVM démarrée et classpath chargé, mais jpype.imports non disponible pour enregistrer les domaines.")
                    # On considère quand même que c'est mieux que rien si le classpath est là
                    jvm_fully_initialized = True
            else:
                logger.error("❌ JVM démarrée (isJVMStarted()=True) MAIS le classpath est VIDE ou inaccessible. Les classes Java ne seront pas trouvées.")
        else:
            logger.error("❌ JVM non démarrée (isJVMStarted()=False).")
            
        jvm_ready = jvm_fully_initialized
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