# argumentation_analysis/agents/core/logic/tweety_initializer.py
"""
Gestionnaire d'initialisation pour les composants Tweety.
Ce module suppose que la JVM a déjà été démarrée et configurée par un
gestionnaire externe (ex: une fixture pytest de session).
"""
import jpype
import logging
import platform
import sys
import threading
from argumentation_analysis.core.utils.logging_utils import setup_logging
# from argumentation_analysis.core.utils.path_operations import get_project_root # Différé
from pathlib import Path
import os

# Initialisation du logger pour ce module.
setup_logging("INFO")
logger = logging.getLogger(__name__)

class TweetyInitializer:
    """
    Handles the initialization of JVM and components for TweetyProject.
    The JVM lifecycle is now managed by pytest fixtures in conftest.py.
    This class acts as a central point for initialization logic and component access.
    """
    _jvm_started = False
    _classes_loaded = False
    _pl_parser = None
    _fol_parser = None
    _modal_parser = None
    _modal_reasoner = None
    _tweety_bridge = None
    _initialized_components = False

    # FOL classes
    FolBeliefSet = None
    FolSignature = None
    Sort = None
    Constant = None
    Predicate = None
    FolFormula = None
    FolAtom = None
    Universal = None # Déprécié, remplacé par ForallQuantifiedFormula
    ForallQuantifiedFormula = None
    ExistsQuantifiedFormula = None
    Variable = None
    Implication = None
    Conjunction = None

    def __init__(self, tweety_bridge_instance):
        self._tweety_bridge = tweety_bridge_instance

        if os.environ.get('DISABLE_JAVA_LOGIC') == '1':
            logger.info("Java logic is disabled via 'DISABLE_JAVA_LOGIC'. Skipping JVM checks.")
            self.__class__._jvm_started = False
            return

        if not jpype.isJVMStarted():
            logger.critical("FATAL: TweetyInitializer expects the JVM to be started by the test session setup (conftest.py).")
            raise RuntimeError("JVM not started. Please run tests using pytest.")

        self.__class__._jvm_started = True

        if not self.__class__._initialized_components:
            logger.info("JVM is running. Initializing Java class imports and components.")
            self._import_java_classes()
            self.initialize_pl_components()
            self.initialize_fol_components()
            self.initialize_modal_components()
            self.__class__._initialized_components = True
        else:
            logger.debug("Java components already initialized for this session.")

    @staticmethod
    def initialize_jvm():
        """
        Main logic to start the JVM. Should only be called once per session,
        typically from a pytest fixture.
        """
        if jpype.isJVMStarted():
            logger.warning("initialize_jvm called but JVM is already running.")
            return

        try:
            logger.info("Starting JVM...")
            from argumentation_analysis.utils.system_utils import get_project_root
            project_root = get_project_root()

            # --- STRATEGIC JVM SELECTION ---
            default_jvm_path = jpype.getDefaultJVMPath()
            jvm_path_to_use = default_jvm_path
            logger.info(f"Default JVM Path (from JPype): {default_jvm_path}")
            
            # This logic is crucial because the default JVM (Java 8) is incompatible with the Tweety JARs (compiled with Java 15+).
            # We must force the use of the portable JDK.
            hardcoded_jdk_path = project_root / "portable_jdk" / "jdk-17.0.2+8"
            logger.info(f"Checking for portable JDK at: {hardcoded_jdk_path}")

            if os.path.isdir(hardcoded_jdk_path):
                logger.info(f"Portable JDK directory found. Identifying JVM library for platform '{sys.platform}'...")
                if sys.platform == "win32":
                    lib_name = "jvm.dll"
                    potential_jvm_path = hardcoded_jdk_path / "bin" / "server" / lib_name
                else:
                    lib_name = "libjvm.so"
                    potential_jvm_path = hardcoded_jdk_path / "lib" / "server" / lib_name

                logger.info(f"Checking for JVM library at: {potential_jvm_path}")
                if potential_jvm_path.is_file():
                    jvm_path_to_use = str(potential_jvm_path)
                    logger.info(f"SUCCESS: Portable JVM library found. Overriding default path. Will use: '{jvm_path_to_use}'")
                else:
                    logger.warning(f"Portable JVM library not found at '{potential_jvm_path}'. Falling back to default JVM. THIS WILL LIKELY FAIL.")
            else:
                logger.warning(f"Portable JDK path '{hardcoded_jdk_path}' not found. Falling back to default JVM. THIS WILL LIKELY FAIL.")
            
            # --- PRE-STARTUP VALIDATION (G-FORCE LOGGING) ---
            logger.info("--- G-FORCE JVM PRE-STARTUP VALIDATION ---")
            logger.info(f"Final JVM path to be used: '{jvm_path_to_use}'")
            logger.info(f"Does the path exist? {os.path.exists(jvm_path_to_use)}")
            logger.info(f"Is it a file? {os.path.isfile(jvm_path_to_use)}")
            logger.info(f"Python architecture: {platform.architecture()}")
            logger.info("--- END VALIDATION ---")

            # --- CLASSPATH CONFIGURATION ---
            tweety_libs_path = project_root / "libs" / "tweety"
            full_jar_path = tweety_libs_path / "org.tweetyproject.tweety-full-1.28-with-dependencies.jar"
            classpath = [str(full_jar_path)]
            logger.info(f"Using classpath: {classpath}")

            jpype.startJVM(
                jvm_path_to_use,
                "-ea",
                classpath=classpath,
                convertStrings=False
            )
            TweetyInitializer._jvm_started = True
            logger.info("JVM started successfully.")

            java_system = jpype.JClass("java.lang.System")
            actual_classpath = java_system.getProperty("java.class.path")
            logger.info(f"Actual Java Classpath from System.getProperty: {actual_classpath}")

        except Exception as e:
            logger.error(f"Failed to start JVM: {e}", exc_info=True)
            raise RuntimeError(f"JVM Initialization failed: {e}") from e

    def _import_java_classes(self):
        """
        Importe les classes Java requises et les met en cache.
        Lève une RuntimeError si une classe n'est pas trouvée, indiquant un
        problème de classpath.
        """
        if TweetyInitializer._classes_loaded:
            return

        logger.info("Importing and caching TweetyProject Java classes...")
        try:
            # PL Classes
            jpype.JClass("org.tweetyproject.logics.pl.syntax.PlSignature")
            jpype.JClass("org.tweetyproject.logics.pl.syntax.Proposition")
            jpype.JClass("org.tweetyproject.logics.pl.syntax.PlBeliefSet")
            jpype.JClass("org.tweetyproject.logics.pl.reasoner.SatReasoner")
            jpype.JClass("org.tweetyproject.logics.pl.sat.Sat4jSolver")

            # FOL Classes
            TweetyInitializer.FolBeliefSet = jpype.JClass("org.tweetyproject.logics.fol.syntax.FolBeliefSet")
            TweetyInitializer.FolSignature = jpype.JClass("org.tweetyproject.logics.fol.syntax.FolSignature")
            TweetyInitializer.FolFormula = jpype.JClass("org.tweetyproject.logics.fol.syntax.FolFormula")
            TweetyInitializer.FolAtom = jpype.JClass("org.tweetyproject.logics.fol.syntax.FolAtom")
            
            # These are quantifiers, often in commons
            # Remplacé par la classe plus spécifique ci-dessous
            # TweetyInitializer.Universal = jpype.JClass("org.tweetyproject.logics.commons.syntax.Universal")
            TweetyInitializer.ForallQuantifiedFormula = jpype.JClass("org.tweetyproject.logics.fol.syntax.ForallQuantifiedFormula")
            TweetyInitializer.ExistsQuantifiedFormula = jpype.JClass("org.tweetyproject.logics.fol.syntax.ExistsQuantifiedFormula")
            TweetyInitializer.Variable = jpype.JClass("org.tweetyproject.logics.commons.syntax.Variable")
            TweetyInitializer.Predicate = jpype.JClass("org.tweetyproject.logics.commons.syntax.Predicate")

            # Common Classes
            TweetyInitializer.Sort = jpype.JClass("org.tweetyproject.logics.commons.syntax.Sort")
            TweetyInitializer.Constant = jpype.JClass("org.tweetyproject.logics.commons.syntax.Constant")
            TweetyInitializer.Implication = jpype.JClass("org.tweetyproject.logics.fol.syntax.Implication")
            TweetyInitializer.Conjunction = jpype.JClass("org.tweetyproject.logics.fol.syntax.Conjunction")
            jpype.JClass("org.tweetyproject.commons.ParserException")

            logger.info("Successfully imported and cached TweetyProject Java classes.")
            TweetyInitializer._classes_loaded = True

        except Exception as e:
            logger.error(f"Error importing Java classes: {e}", exc_info=True)
            java_system = jpype.JClass("java.lang.System")
            actual_classpath = java_system.getProperty("java.class.path")
            logger.error(f"Classpath at time of error: {actual_classpath}")
            raise RuntimeError(f"Java class import failed: {e}") from e

    def initialize_pl_components(self):
        if self.__class__._pl_parser and self.__class__._pl_reasoner:
            return
        try:
            logger.debug("Initializing PL components...")
            self.__class__._pl_reasoner = jpype.JClass("org.tweetyproject.logics.pl.reasoner.SimplePlReasoner")()
            self.__class__._pl_parser = jpype.JClass("org.tweetyproject.logics.pl.parser.PlParser")()
            logger.info("PL components initialized.")
        except Exception as e:
            logger.error(f"Error initializing PL components: {e}", exc_info=True)
            raise

    def initialize_fol_components(self):
        if self.__class__._fol_parser:
            return
        try:
            logger.debug("Initializing FOL components...")
            self.__class__._fol_parser = jpype.JClass("org.tweetyproject.logics.fol.parser.FolParser")()
            logger.info("FOL parser initialized.")
        except Exception as e:
            logger.error(f"Error initializing FOL components: {e}", exc_info=True)
            raise

    def initialize_modal_components(self):
        if self.__class__._modal_parser:
            return
        try:
            logger.debug("Initializing Modal Logic components...")
            self.__class__._modal_parser = jpype.JClass("org.tweetyproject.logics.ml.parser.MlParser")()
            logger.info("Modal Logic parser initialized.")
        except Exception as e:
            logger.error(f"Error initializing Modal Logic components: {e}", exc_info=True)
            raise

    @staticmethod
    def get_pl_parser():
        if not TweetyInitializer._pl_parser:
            raise RuntimeError("PL Parser not initialized.")
        return TweetyInitializer._pl_parser

    @staticmethod
    def get_fol_parser():
        if not TweetyInitializer._fol_parser:
            raise RuntimeError("FOL Parser not initialized.")
        return TweetyInitializer._fol_parser

    @staticmethod
    def get_modal_parser():
        if not TweetyInitializer._modal_parser:
            raise RuntimeError("Modal Parser not initialized.")
        return TweetyInitializer._modal_parser

    def is_jvm_started(self):
        return self.__class__._jvm_started
