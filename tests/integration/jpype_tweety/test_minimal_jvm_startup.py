import jpype
import jpype.imports
from jpype.types import *
import os
import pytest
from pathlib import Path
import logging
import time # Ajout pour débogage temporel

# Configuration du logging pour ce fichier de test
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# S'assurer qu'un handler est configuré si ce n'est pas déjà fait globalement
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Utiliser le chemin absolu du répertoire du projet
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
PORTABLE_JDK_PATH = str(PROJECT_ROOT / "libs" / "portable_jdk" / "jdk-17.0.11+9")
LIBS_DIR = str(PROJECT_ROOT / "libs")

# Variable globale pour suivre si la JVM a été démarrée par ce test
jvm_started_by_this_test_locally = False

def local_start_the_jvm_directly():
    """Tente de démarrer la JVM directement avec des paramètres connus."""
    global jvm_started_by_this_test_locally
    logger.info("Appel direct de jpype.startJVM() depuis une fonction LOCALE au test...")
    if jpype.isJVMStarted():
        logger.info("LOCAL_CALL: La JVM est déjà démarrée. Ne rien faire.")
        return True # Ou False, selon la sémantique désirée

    jvmpath = str(Path(PORTABLE_JDK_PATH) / "bin" / "server" / "jvm.dll")
    classpath_entries = [] # Vide pour le test minimal
    
    jvm_options = [
        '-Xms128m',
        '-Xmx512m',
        '-Dfile.encoding=UTF-8',
        '-Djava.awt.headless=true',
        '-verbose:jni',
        '-Xcheck:jni'
    ]

    logger.debug(f"  LOCAL_CALL jvmpath: {jvmpath}")
    logger.debug(f"  LOCAL_CALL classpath: {classpath_entries}")
    logger.debug(f"  LOCAL_CALL jvm_options: {jvm_options}")
    logger.debug(f"  LOCAL_CALL convertStrings: False")

    original_path = os.environ.get("PATH", "")
    jdk_bin_path = str(Path(PORTABLE_JDK_PATH) / "bin")
    
    logger.debug(f"  LOCAL_CALL Original PATH: {original_path[:200]}...") # Log tronqué pour la lisibilité
    
    # Mettre le répertoire bin du JDK portable en tête du PATH
    modified_path = jdk_bin_path + os.pathsep + original_path
    os.environ["PATH"] = modified_path
    logger.debug(f"  LOCAL_CALL Modified PATH: {os.environ['PATH'][:200]}...") # Log tronqué

    try:
        jpype.startJVM(
            jvmpath=jvmpath, # jvmpath pointe déjà vers .../bin/server/jvm.dll
            classpath=classpath_entries,
            *jvm_options,
            convertStrings=False
        )
        logger.info("LOCAL_CALL jpype.startJVM() exécuté.")
        jvm_started_by_this_test_locally = True
        return True
    except Exception as e:
        logger.error(f"LOCAL_CALL Erreur lors du démarrage de la JVM: {e}", exc_info=True)
        # Windows fatal exception: access violation est souvent non capturable ici
        # mais on loggue au cas où ce serait une autre exception.
        return False
    finally:
        # Restaurer le PATH original
        os.environ["PATH"] = original_path
        logger.debug(f"  LOCAL_CALL Restored PATH: {os.environ['PATH'][:200]}...") # Log tronqué

def test_minimal_jvm_startup_in_pytest():
    """
    Teste le démarrage minimal de la JVM directement dans un test pytest,
    en utilisant une fonction locale pour l'appel à startJVM.
    """
    global jvm_started_by_this_test_locally
    jvm_started_by_this_test_locally = False # Réinitialiser pour ce test

    logger.info("--- Début de test_minimal_jvm_startup_in_pytest (appel local) ---")
    
    original_use_real_jpype = os.environ.get('USE_REAL_JPYPE')
    os.environ['USE_REAL_JPYPE'] = 'true' # Forcer pour ce test
    logger.debug(f"Variable d'environnement USE_REAL_JPYPE (forcée pour ce test): '{os.environ.get('USE_REAL_JPYPE')}'")
    logger.debug(f"Chemin JDK portable (variable globale importée): {PORTABLE_JDK_PATH}")
    logger.debug(f"Chemin LIBS_DIR (variable globale importée): {LIBS_DIR}")

    is_started_before = jpype.isJVMStarted()
    logger.info(f"JVM démarrée avant l'appel à la fonction locale (jpype.isJVMStarted()): {is_started_before}")

    if not is_started_before: # Condition pour démarrer la JVM si elle ne l'est pas déjà
        logger.info("Appel de local_start_the_jvm_directly()...")
        startup_success = local_start_the_jvm_directly()
        logger.info(f"local_start_the_jvm_directly() a retourné: {startup_success}")
    else: # La JVM était déjà démarrée
        logger.info("La JVM était déjà démarrée, pas d'appel à local_start_the_jvm_directly().")
        startup_success = True # Considérer comme un succès si déjà démarrée

    is_started_after = jpype.isJVMStarted()
    logger.info(f"État de la JVM après local_start_the_jvm_directly (jpype.isJVMStarted()): {is_started_after}")

    if startup_success and is_started_after:
        logger.info("SUCCESS: JVM démarrée via une fonction LOCALE dans le contexte pytest.")
        # On pourrait ajouter un petit test Java ici si nécessaire
        # from jpype. JClass import java.lang.System
        # logger.info(f"Java version: {java.lang.System.getProperty('java.version')}")
    elif not startup_success and not is_started_after:
        logger.error("FAILURE: La JVM n'a pas pu être démarrée par l'appel local et n'est pas active.")
    elif startup_success and not is_started_after:
        logger.error("FAILURE INCONSISTENT: local_start_the_jvm_directly a rapporté un succès mais la JVM n'est pas active.")
    elif not startup_success and is_started_after:
         logger.warning("WARNING INCONSISTENT: local_start_the_jvm_directly a rapporté un échec MAIS la JVM EST active (possible crash?).")


    try:
        assert is_started_after, "La JVM devrait être démarrée après l'appel local."
    finally:
        logger.info("--- Bloc finally de test_minimal_jvm_startup_in_pytest ---")
        if jvm_started_by_this_test_locally and jpype.isJVMStarted():
            logger.info("Tentative d'arrêt de la JVM (car démarrée par l'appel local)...")
            # jpype.shutdownJVM() # Commenté car cause des problèmes de redémarrage / état
            logger.info("Arrêt de la JVM tenté (actuellement commenté).") 
            # jvm_started_by_this_test_locally = False # Normalement fait par shutdown

        if original_use_real_jpype is None:
            del os.environ['USE_REAL_JPYPE']
        else:
            os.environ['USE_REAL_JPYPE'] = original_use_real_jpype
        logger.debug(f"Variable d'environnement USE_REAL_JPYPE restaurée à: '{os.environ.get('USE_REAL_JPYPE')}'")
        logger.info("--- Fin de test_minimal_jvm_startup_in_pytest ---")