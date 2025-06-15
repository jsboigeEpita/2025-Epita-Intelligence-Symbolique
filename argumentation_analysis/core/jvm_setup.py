# argumentation_analysis/core/jvm_setup.py
import jpype
import jpype.imports
import logging
import os
from pathlib import Path
from typing import Optional, List

# Configuration du logger pour ce module
logger = logging.getLogger("Orchestration.JPype")

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
            logger.info(f"Classpath construit avec {len(jars)} JAR(s) depuis '{jar_directory}'.")
            logger.info(f"Classpath configuré avec {len(jars)} JARs (JPype {jpype.__version__})")

        if not jars:
            logger.error("(ERREUR) Aucun JAR trouvé pour le classpath. Démarrage annulé.")
            return False
        
        jvm_options = get_jvm_options()
        jdk_path = find_jdk_path()
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