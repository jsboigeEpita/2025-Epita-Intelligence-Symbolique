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
        logger.info(f"(OK) JDK portable détecté : {PORTABLE_JDK_PATH}")
    else:
        logger.warning(f"(ATTENTION) JDK portable non trouvé à l'emplacement attendu : {_potential_jdk_path}")
except Exception as e:
    logger.error(f"(ERREUR) Erreur lors de la détection du JDK portable : {e}", exc_info=True)


def get_jvm_options(jdk_path: Optional[Path] = PORTABLE_JDK_PATH) -> List[str]:
    """Prépare les options pour le démarrage de la JVM, incluant le chemin du JDK si disponible."""
    options = [
        "-Xms128m",
        "-Xmx512m",
        "-Dfile.encoding=UTF-8",    # Ajouté
        "-Djava.awt.headless=true"  # Ajouté
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


        
        
    
        
def initialize_jvm(lib_dir_path: Optional[str] = None, jdk_path: Optional[Path] = PORTABLE_JDK_PATH, specific_jar_path: Optional[str] = None) -> bool:
    """
    Initialise la JVM avec les JARs de TweetyProject.
    Si specific_jar_path est fourni, utilise uniquement ce JAR.
    Sinon, si lib_dir_path n'est pas fourni, utilise la variable globale LIBS_DIR pour scanner les JARs.
    """
    logger.info(f"JVM_SETUP: initialize_jvm appelée. isJVMStarted au début: {jpype.isJVMStarted()}")
    try:
        # import jpype.version # Commenté car jpype est déjà importé globalement
        logger.info(f"JVM_SETUP: Version de JPype: {jpype.__version__}")
    except (ImportError, AttributeError):
        logger.warning("JVM_SETUP: Impossible d'obtenir la version de JPype via jpype.__version__.")
    if jpype.isJVMStarted():
        logger.info("JVM_SETUP: JVM déjà démarrée (vérifié au début de initialize_jvm).")
        return True

    try:
        jars: List[str] = []
        if specific_jar_path:
            specific_jar_file = Path(specific_jar_path)
            if specific_jar_file.is_file():
                jars = [str(specific_jar_file)]
                logger.info(f"Utilisation du JAR spécifique pour le classpath: {specific_jar_path}")
            else:
                logger.error(f"(ERREUR) Le fichier JAR spécifique '{specific_jar_path}' n'a pas été trouvé ou n'est pas un fichier.")
                return False
        else:
            effective_lib_dir_path = lib_dir_path
            if effective_lib_dir_path is None:
                if LIBS_DIR is not None: # LIBS_DIR est maintenant global
                    effective_lib_dir_path = str(LIBS_DIR)
                    logger.info(f"Utilisation de LIBS_DIR global: {effective_lib_dir_path}")
                else:
                    logger.error("(ERREUR) `lib_dir_path` non fourni, `specific_jar_path` non fourni, et `LIBS_DIR` global non défini. Impossible de localiser les JARs.")
                    return False
            
            jar_directory = Path(effective_lib_dir_path)
            if not jar_directory.is_dir():
                logger.error(f"(ERREUR) Le répertoire des JARs '{jar_directory}' n'existe pas ou n'est pas un répertoire (et specific_jar_path non fourni).")
                return False

            logger.info(f"Construction du classpath avec tous les JARs trouvés dans '{jar_directory}'.")
            jars = [str(jar_file) for jar_file in jar_directory.glob("*.jar")]
            logger.info(f"Classpath construit avec {len(jars)} JAR(s) depuis '{jar_directory}'.")

        if not jars:
            logger.error(f"(ERREUR) Aucun JAR à inclure dans le classpath ! Démarrage annulé. (specific_jar_path: {specific_jar_path}, lib_dir_path: {lib_dir_path})")
            return False
        
        # classpath_str = os.pathsep.join(jars) # Pour le log seulement
        # logger.info(f"Classpath construit avec {len(jars)} JAR(s).") # Déjà loggué au-dessus
        # logger.debug(f"Classpath (premiers 200 chars): {classpath_str[:200]}...")

        jvm_options = get_jvm_options(jdk_path)
        
        logger.info(f"JVM_SETUP: Avant startJVM. isJVMStarted: {jpype.isJVMStarted()}. Nombre de JARs: {len(jars)}. Options: {jvm_options}")
        
        jvm_started_successfully = False
        try:
            # Tentative 1: Laisser JPype trouver la JVM (via JAVA_HOME ou recherche système)
            logger.info("JVM_SETUP: Tentative 1 - Démarrage JVM avec détection automatique.")
            jpype.startJVM(classpath=jars, *jvm_options, convertStrings=False)
            logger.info(f"JVM_SETUP: Tentative 1 - JVM démarrée avec succès. isJVMStarted: {jpype.isJVMStarted()}.")
            jvm_started_successfully = True
        except jpype.JVMNotFoundException as e_not_found:
            logger.warning(f"JVM_SETUP: Tentative 1 - Échec (JVMNotFoundException): {e_not_found}.")
            
            portable_jvm_lib_path_str = None
            if jdk_path: # jdk_path est PORTABLE_JDK_PATH par défaut
                # Ordre de recherche commun pour les bibliothèques JVM
                # Windows
                if (jdk_path / "bin" / "server" / "jvm.dll").exists():
                    portable_jvm_lib_path_str = str(jdk_path / "bin" / "server" / "jvm.dll")
                elif (jdk_path / "jre" / "bin" / "server" / "jvm.dll").exists():
                    portable_jvm_lib_path_str = str(jdk_path / "jre" / "bin" / "server" / "jvm.dll")
                # Linux
                elif (jdk_path / "lib" / "server" / "libjvm.so").exists():
                     portable_jvm_lib_path_str = str(jdk_path / "lib" / "server" / "libjvm.so")
                elif (jdk_path / "jre" / "lib" / "amd64" / "server" / "libjvm.so").exists():
                     portable_jvm_lib_path_str = str(jdk_path / "jre" / "lib" / "amd64" / "server" / "libjvm.so")
                # MacOS (chemins typiques, peuvent varier)
                elif (jdk_path / "lib" / "jli" / "libjli.dylib").exists(): # Souvent un symlink ou chargeur
                     portable_jvm_lib_path_str = str(jdk_path / "lib" / "jli" / "libjli.dylib")
                elif (jdk_path / "lib" / "server" / "libjvm.dylib").exists():
                     portable_jvm_lib_path_str = str(jdk_path / "lib" / "server" / "libjvm.dylib")

            if portable_jvm_lib_path_str:
                logger.info(f"JVM_SETUP: Tentative 2 - Utilisation du JDK portable avec la bibliothèque JVM explicite: {portable_jvm_lib_path_str}")
                try:
                    # Le premier argument de startJVM peut être le chemin de la JVM
                    jpype.startJVM(portable_jvm_lib_path_str, classpath=jars, *jvm_options, convertStrings=False)
                    logger.info(f"JVM_SETUP: Tentative 2 - JVM démarrée avec succès en utilisant le JDK portable. isJVMStarted: {jpype.isJVMStarted()}.")
                    jvm_started_successfully = True
                except Exception as e_portable_start:
                    logger.error(f"JVM_SETUP: Tentative 2 - ÉCHEC CRITIQUE avec JDK portable ({portable_jvm_lib_path_str}): {e_portable_start}", exc_info=True)
                    # Ne pas lever ici pour permettre au flux principal de gérer l'échec global, mais s'assurer que jvm_started_successfully reste False
            else:
                logger.error("JVM_SETUP: JDK portable non trouvé ou bibliothèque JVM (jvm.dll/libjvm.so/libjli.dylib) manquante dans le JDK portable. Impossible de tenter le démarrage avec le JDK portable.")
                # Si le JDK portable était la solution de repli et qu'il échoue, on relance l'exception originale.
                raise e_not_found
        except Exception as e_other_start_error:
            # Attrape d'autres erreurs potentielles de la Tentative 1
            logger.error(f"JVM_SETUP: ÉCHEC CRITIQUE lors de la Tentative 1 (autre erreur que JVMNotFound): {e_other_start_error}", exc_info=True)
            raise # Relancer pour que le bloc try/except global de initialize_jvm le capture

        if not jvm_started_successfully:
            # Si on arrive ici, c'est que toutes les tentatives ont échoué et une exception aurait dû être levée.
            # Ce bloc est une sécurité supplémentaire.
            final_error_msg = "Échec du démarrage de la JVM après toutes les tentatives."
            logger.error(f"JVM_SETUP: {final_error_msg}")
            raise RuntimeError(final_error_msg)
            
        # logger.info("[OK] JVM démarrée avec succès (ou tentatives faites).") # Commenté car redondant avec les logs des tentatives
        
        try:
            _ = jpype.JClass("org.tweetyproject.logics.pl.syntax.PlSignature")
            logger.info("(OK) Test de chargement de classe Tweety (PlSignature) réussi.")
        except Exception as e_test:
            logger.error(f"(ERREUR) Test de chargement de classe Tweety échoué après démarrage JVM: {e_test}", exc_info=True)

        return True

    except Exception as e:
        logger.critical(f"(ERREUR CRITIQUE) Échec critique du démarrage de la JVM (dans le try/except global de initialize_jvm): {e}", exc_info=True)
        return False

def _safe_log(logger_instance, level, message, exc_info_val=False):
    """Effectue un log de manière sécurisée, avec un fallback sur print si les handlers sont fermés."""
    try:
        if logger_instance.hasHandlers(): # Vérifie si des handlers sont configurés
            if level == logging.INFO:
                logger_instance.info(message)
            elif level == logging.ERROR:
                logger_instance.error(message, exc_info=exc_info_val)
            elif level == logging.DEBUG:
                logger_instance.debug(message)
            elif level == logging.WARNING:
                logger_instance.warning(message)
            elif level == logging.CRITICAL:
                logger_instance.critical(message)
            # Ajoutez d'autres niveaux si nécessaire
        else: # Pas de handlers, utiliser print
            print(f"FALLBACK LOG (No handlers) ({logging.getLevelName(level)}): {message}")
            if exc_info_val:
                import traceback
                traceback.print_exc()
    except ValueError as e:
        if "I/O operation on closed file" in str(e):
            # Log a échoué car le fichier/stream est fermé, utiliser print comme fallback
            print(f"FALLBACK LOG (ValueError) ({logging.getLevelName(level)}): {message}")
            if exc_info_val:
                import traceback
                traceback.print_exc()
        else:
            raise # Renvoyer d'autres ValueErrors
    except Exception as e_other: # Attraper d'autres erreurs potentielles de logging
        print(f"FALLBACK LOG (Other Exception) ({logging.getLevelName(level)}): {message} - Error: {e_other}")
        if exc_info_val:
            import traceback
            traceback.print_exc()
        raise # Renvoyer l'erreur si elle n'est pas liée à un fichier fermé

def shutdown_jvm_if_needed():
    """Arrête la JVM si elle est démarrée, avec des logs."""
    _safe_log(logger, logging.INFO, "JVM_SETUP: Appel de shutdown_jvm_if_needed.")
    try:
        if jpype.isJVMStarted():
            _safe_log(logger, logging.INFO, f"JVM_SETUP: JVM est démarrée. Appel de jpype.shutdownJVM(). isJVMStarted avant: {jpype.isJVMStarted()}")
            jpype.shutdownJVM()
            _safe_log(logger, logging.INFO, f"JVM_SETUP: jpype.shutdownJVM() exécuté. isJVMStarted après: {jpype.isJVMStarted()}")
        else:
            _safe_log(logger, logging.INFO, f"JVM_SETUP: JVM n'était pas démarrée. Aucun arrêt nécessaire. isJVMStarted: {jpype.isJVMStarted()}")
    except Exception as e_shutdown:
        _safe_log(logger, logging.ERROR, f"JVM_SETUP: Erreur lors de jpype.shutdownJVM() ou de la vérification isJVMStarted: {e_shutdown}", exc_info_val=True)
        # Tenter de vérifier l'état même en cas d'erreur, si jpype est encore accessible
        try:
            _safe_log(logger, logging.ERROR, f"JVM_SETUP: État isJVMStarted après erreur de shutdown: {jpype.isJVMStarted()}")
        except Exception:
            _safe_log(logger, logging.ERROR, "JVM_SETUP: Impossible de vérifier isJVMStarted après erreur de shutdown.")


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