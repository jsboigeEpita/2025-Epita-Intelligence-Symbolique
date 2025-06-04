# argumentation_analysis/core/jvm_setup.py
import jpype
import jpype.imports
import logging
import os
from pathlib import Path
from typing import Optional, List

# Configuration du logger pour ce module
logger = logging.getLogger("Orchestration.JPype")
# Détermination du répertoire racine du projet
PROJECT_ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# Définition des chemins possibles pour LIBS_DIR
LIBS_DIR_PRIMARY = PROJECT_ROOT_DIR / "libs" / "tweety"
LIBS_DIR_FALLBACK = PROJECT_ROOT_DIR / "libs"

# Détermination de LIBS_DIR à utiliser globalement
LIBS_DIR: Optional[Path] = None
if LIBS_DIR_PRIMARY.is_dir() and list(LIBS_DIR_PRIMARY.glob("*.jar")):
    LIBS_DIR = LIBS_DIR_PRIMARY
    logger.info(f"LIBS_DIR (global) défini sur (primaire): {LIBS_DIR}")
elif LIBS_DIR_FALLBACK.is_dir() and list(LIBS_DIR_FALLBACK.glob("*.jar")):
    LIBS_DIR = LIBS_DIR_FALLBACK
    logger.info(f"LIBS_DIR (global) défini sur (fallback): {LIBS_DIR}")
else:
    logger.warning(
        f"Aucun JAR trouvé ni dans {LIBS_DIR_PRIMARY} ni dans {LIBS_DIR_FALLBACK}. "
        f"LIBS_DIR (global) n'est pas défini. Cela peut causer des problèmes si la JVM est initialisée sans chemin explicite."
    )
    # Optionnel: définir sur fallback même si vide pour éviter None si une valeur est toujours attendue
    # LIBS_DIR = LIBS_DIR_FALLBACK
    # logger.warning(f"LIBS_DIR (global) défini sur (fallback) {LIBS_DIR} malgré l'absence de JARs.")
TWEETY_VERSION = "1.28"

PORTABLE_JDK_PATH: Optional[Path] = None
try:
    # PROJECT_ROOT_DIR = Path(__file__).resolve().parent.parent.parent # Défini globalement à la ligne 12
    _JDK_SUBDIR = "libs/portable_jdk/jdk-17.0.11+9" 
    _potential_jdk_path = PROJECT_ROOT_DIR / _JDK_SUBDIR # Utilise le PROJECT_ROOT_DIR global
    if _potential_jdk_path.is_dir():
        PORTABLE_JDK_PATH = _potential_jdk_path
        logger.info(f"✅ JDK portable détecté : {PORTABLE_JDK_PATH}")
    else:
        logger.warning(f"⚠️ JDK portable non trouvé à l'emplacement attendu : {_potential_jdk_path}")
except Exception as e:
    logger.error(f"❌ Erreur lors de la détection du JDK portable : {e}", exc_info=True)


def get_jvm_options(jdk_path: Optional[Path] = PORTABLE_JDK_PATH) -> List[str]:
    """Prépare les options pour le démarrage de la JVM, incluant le chemin du JDK si disponible."""
    options = [
        "-Xms128m",
        "-Xmx512m"
    ]
    logger.info(f"Options JVM de base définies : {options}")
    if jdk_path and jdk_path.is_dir():
        jvm_dll_path = None
        if (jdk_path / "bin" / "server" / "jvm.dll").exists():
            jvm_dll_path = jdk_path / "bin" / "server" / "jvm.dll"
        elif (jdk_path / "jre" / "bin" / "server" / "jvm.dll").exists():
             jvm_dll_path = jdk_path / "jre" / "bin" / "server" / "jvm.dll"
        elif (jdk_path / "lib" / "server" / "libjvm.so").exists():
            jvm_dll_path = jdk_path / "lib" / "server" / "libjvm.so"
        elif (jdk_path / "jre" / "lib" / "amd64" / "server" / "libjvm.so").exists():
            jvm_dll_path = jdk_path / "jre" / "lib" / "amd64" / "server" / "libjvm.so"

        if jvm_dll_path:
            logger.info(f"Utilisation de la JVM spécifiée : {jvm_dll_path}")
        else:
            logger.warning(f"jvm.dll ou libjvm.so non trouvé dans {jdk_path}. Utilisation du JDK par défaut du système.")
    else:
        logger.info("Aucun JDK portable spécifié ou trouvé. Utilisation du JDK par défaut du système.")
    return options

def initialize_jvm(lib_dir_path: Optional[str] = None, jdk_path: Optional[Path] = PORTABLE_JDK_PATH) -> bool:
    """
    Initialise la JVM avec les JARs de TweetyProject.
    Si lib_dir_path n'est pas fourni, utilise la variable globale LIBS_DIR.
    """
    logger.info(f"JVM_SETUP: initialize_jvm appelée. isJVMStarted au début: {jpype.isJVMStarted()}")
    if jpype.isJVMStarted():
        logger.info("JVM_SETUP: JVM déjà démarrée (vérifié au début de initialize_jvm).")
        return True

    try:
        effective_lib_dir_path = lib_dir_path
        if effective_lib_dir_path is None:
            if LIBS_DIR is not None: # LIBS_DIR est maintenant global
                effective_lib_dir_path = str(LIBS_DIR)
                logger.info(f"Utilisation de LIBS_DIR global: {effective_lib_dir_path}")
            else:
                logger.error("❌ `lib_dir_path` non fourni et `LIBS_DIR` global non défini. Impossible de localiser les JARs.")
                return False
        
        jar_directory = Path(effective_lib_dir_path)
        if not jar_directory.is_dir():
            logger.error(f"❌ Le répertoire des JARs '{jar_directory}' n'existe pas ou n'est pas un répertoire.")
            return False

        logger.info(f"Construction du classpath avec tous les JARs trouvés dans '{jar_directory}'.")
        jars = [str(jar_file) for jar_file in jar_directory.glob("*.jar")]
        
        if not jars:
            logger.error(f"❌ Aucun JAR trouvé pour le classpath dans '{jar_directory}' ! Démarrage annulé.")
            return False
        
        # classpath_str = os.pathsep.join(jars) # Pour le log seulement
        logger.info(f"Classpath construit avec {len(jars)} JAR(s) depuis '{jar_directory}'.")
        # logger.debug(f"Classpath (premiers 200 chars): {classpath_str[:200]}...")

        jvm_options = get_jvm_options(jdk_path)
        
        jvm_dll_to_use = None # Ce n'est plus utilisé pour forcer jvmpath, mais gardé pour info
        if jdk_path:
            if (jdk_path / "bin" / "server" / "jvm.dll").exists():
                jvm_dll_to_use = str(jdk_path / "bin" / "server" / "jvm.dll")
            elif (jdk_path / "jre" / "bin" / "server" / "jvm.dll").exists(): 
                 jvm_dll_to_use = str(jdk_path / "jre" / "bin" / "server" / "jvm.dll")
            elif (jdk_path / "lib" / "server" / "libjvm.so").exists():
                jvm_dll_to_use = str(jdk_path / "lib" / "server" / "libjvm.so")
            elif (jdk_path / "jre" / "lib" / "amd64" / "server" / "libjvm.so").exists(): 
                jvm_dll_to_use = str(jdk_path / "jre" / "lib" / "amd64" / "server" / "libjvm.so")

            if jvm_dll_to_use:
                 logger.info(f"Un JDK portable a été détecté à {jdk_path} (jvm.dll estimé: {jvm_dll_to_use}), mais nous allons prioriser la configuration système/JAVA_HOME.")
            else:
                 logger.info(f"Aucun jvm.dll/libjvm.so trouvé dans le JDK portable spécifié: {jdk_path}. Nous allons utiliser la configuration système/JAVA_HOME.")
        else:
            logger.info("Aucun JDK portable spécifié. Nous allons utiliser la configuration système/JAVA_HOME.")

        logger.info(f"JVM_SETUP: Avant startJVM. isJVMStarted: {jpype.isJVMStarted()}. Nombre de JARs: {len(jars)}. Options: {jvm_options}")
        try:
            # JPype attend une liste de chemins pour le classpath.
            jpype.startJVM(classpath=jars, *jvm_options, convertStrings=False)
            logger.info(f"JVM_SETUP: JVM démarrée avec succès par startJVM. isJVMStarted: {jpype.isJVMStarted()}.")
        except Exception as e_system_start:
            logger.error(f"JVM_SETUP: ÉCHEC CRITIQUE de jpype.startJVM : {e_system_start}", exc_info=True)
            logger.error(f"JVM_SETUP: État isJVMStarted après échec de startJVM: {jpype.isJVMStarted()}")
            raise 
            
        logger.info("✅ JVM démarrée avec succès (ou tentatives faites).")
        
        try:
            _ = jpype.JClass("org.tweetyproject.logics.pl.syntax.PlSignature")
            logger.info("✅ Test de chargement de classe Tweety (PlSignature) réussi.")
        except Exception as e_test:
            logger.error(f"❌ Test de chargement de classe Tweety échoué après démarrage JVM: {e_test}", exc_info=True)

        return True

    except Exception as e:
        logger.critical(f"❌ Échec critique du démarrage de la JVM (dans le try/except global de initialize_jvm): {e}", exc_info=True)
        return False

def shutdown_jvm_if_needed():
    """Arrête la JVM si elle est démarrée, avec des logs."""
    logger.info("JVM_SETUP: Appel de shutdown_jvm_if_needed.")
    try:
        if jpype.isJVMStarted():
            logger.info(f"JVM_SETUP: JVM est démarrée. Appel de jpype.shutdownJVM(). isJVMStarted avant: {jpype.isJVMStarted()}")
            jpype.shutdownJVM()
            logger.info(f"JVM_SETUP: jpype.shutdownJVM() exécuté. isJVMStarted après: {jpype.isJVMStarted()}")
        else:
            logger.info(f"JVM_SETUP: JVM n'était pas démarrée. Aucun arrêt nécessaire. isJVMStarted: {jpype.isJVMStarted()}")
    except Exception as e_shutdown:
        logger.error(f"JVM_SETUP: Erreur lors de jpype.shutdownJVM() ou de la vérification isJVMStarted: {e_shutdown}", exc_info=True)
        # Tenter de vérifier l'état même en cas d'erreur, si jpype est encore accessible
        try:
            logger.error(f"JVM_SETUP: État isJVMStarted après erreur de shutdown: {jpype.isJVMStarted()}")
        except Exception:
            logger.error("JVM_SETUP: Impossible de vérifier isJVMStarted après erreur de shutdown.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    # La logique de actual_libs_dir_to_use est maintenant gérée par LIBS_DIR global
    # et la fonction initialize_jvm peut utiliser cette variable globale si aucun argument n'est passé.

    logger.info(f"Test: LIBS_DIR global est: {LIBS_DIR}")

    if LIBS_DIR: # Vérifie si LIBS_DIR a été défini globalement
        success = initialize_jvm() # Appelle sans argument pour utiliser LIBS_DIR global
        if success:
            logger.info("Test initialize_jvm: SUCCÈS")
            try:
                TestClass = jpype.JClass("org.tweetyproject.logics.pl.syntax.PropositionalSignature")
                logger.info(f"Classe de test chargée: {TestClass}")
                sig = TestClass()
                logger.info(f"Instance de signature créée: {sig}")
                sig.add(jpype.JClass("org.tweetyproject.logics.pl.syntax.Proposition")("a"))
                logger.info(f"Contient 'a' après ajout: {sig.contains('a')}")
                
            except Exception as e:
                logger.error(f"Erreur lors du test avec la classe Tweety: {e}", exc_info=True)
            finally:
                shutdown_jvm_if_needed()
        else:
            logger.error("Test initialize_jvm: ÉCHEC")
    else:
        logger.error("Test initialize_jvm: ÉCHEC - LIBS_DIR global n'a pas été défini ou aucun JAR trouvé.")