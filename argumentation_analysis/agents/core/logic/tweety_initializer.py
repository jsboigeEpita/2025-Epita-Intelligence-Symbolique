# ===== AUTO-ACTIVATION ENVIRONNEMENT =====
try:
    import project_core.core_from_scripts.auto_env  # Auto-activation environnement intelligent
except ImportError:
    # Dans le contexte des tests, auto_env peut déjà être activé
    pass
# =========================================
import jpype
import logging
from argumentation_analysis.utils.core_utils.logging_utils import setup_logging
# from argumentation_analysis.utils.core_utils.path_operations import get_project_root # Différé
from pathlib import Path
import os # Ajout de l'import os

# Initialisation du logger pour ce module.
# setup_logging() est appelé pour configurer le logging global.
# Il est important que setup_logging soit idempotent ou gère les appels multiples (ce qu'il fait avec force=True).
setup_logging("INFO")  # Appel avec un niveau de log valide comme "INFO" ou selon la config souhaitée.
logger = logging.getLogger(__name__) # Obtention correcte du logger pour ce module.

class TweetyInitializer:
    """
    Handles the initialization of JVM components for TweetyProject.
    """

    _jvm_started = False
    _pl_reasoner = None
    _pl_parser = None
    _fol_parser = None
    _fol_reasoner = None
    _modal_logic = None
    _modal_parser = None
    _modal_reasoner = None
    _tweety_bridge = None

    def __init__(self, tweety_bridge_instance):
        self._tweety_bridge = tweety_bridge_instance

        if os.environ.get('DISABLE_JAVA_LOGIC') == '1':
            logger.info("Java logic is disabled via environment variable 'DISABLE_JAVA_LOGIC'. Skipping JVM initialization.")
            TweetyInitializer._jvm_started = False
            return

        # It's crucial to ensure the classpath is correct BEFORE any JVM interaction.
        self._ensure_classpath()

        if not jpype.isJVMStarted():
            logger.info("JVM not detected as started. TweetyInitializer will now attempt to start it.")
            self._start_jvm()
        else:
            logger.info("TweetyInitializer confirmed that JVM is already started by another component.")
            # Even if started, we must ensure our classes are available.
            TweetyInitializer._jvm_started = True
            self._import_java_classes()

    def _ensure_classpath(self):
        """Ensures the Tweety JAR is in the JPype classpath."""
        try:
            from argumentation_analysis.utils.system_utils import get_project_root
            project_root = get_project_root()
            jar_path = project_root / "libs" / "tweety" / "org.tweetyproject.tweety-full-1.28-with-dependencies.jar"
            jar_path_str = str(jar_path)

            if not jar_path.exists():
                logger.error(f"Tweety JAR not found at {jar_path_str}")
                raise RuntimeError(f"Tweety JAR not found at {jar_path_str}")

            # This check needs to happen before the JVM starts if possible,
            # but jpype.getClassPath() works even on a running JVM.
            current_classpath = jpype.getClassPath()
            if jar_path_str not in current_classpath:
                logger.info(f"Adding Tweety JAR to classpath: {jar_path_str}")
                jpype.addClassPath(jar_path_str)
                # Verification after adding
                new_classpath = jpype.getClassPath()
                if jar_path_str not in new_classpath:
                     logger.warning(f"Failed to dynamically add {jar_path_str} to classpath. This might cause issues.")
            else:
                logger.debug(f"Tweety JAR already in classpath.")

        except Exception as e:
            logger.error(f"Failed to ensure Tweety classpath: {e}", exc_info=True)
            raise RuntimeError(f"Classpath configuration failed: {e}") from e


    def _start_jvm(self):
        """Starts the JVM. The classpath should have been configured by _ensure_classpath."""
        global logger
        if logger is None:
            setup_logging("INFO")
            logger = logging.getLogger(__name__)
            logger.error("CRITICAL: TweetyInitializer logger re-initialized in _start_jvm.")

        if TweetyInitializer._jvm_started:
            logger.info("JVM already started.")
            return

        try:
            if not jpype.isJVMStarted():
                logger.info("Starting JVM...")
                # The classpath is now managed by _ensure_classpath and addClassPath.
                # startJVM will pick up the modified classpath.
                jpype.startJVM(
                    jpype.getDefaultJVMPath(),
                    "-ea",
                    convertStrings=False
                )
                TweetyInitializer._jvm_started = True
                logger.info("JVM started successfully.")
            else:
                logger.info("JVM was already started by another component.")
                TweetyInitializer._jvm_started = True

            java_system = jpype.JClass("java.lang.System")
            actual_classpath = java_system.getProperty("java.class.path")
            logger.info(f"Actual Java Classpath from System.getProperty: {actual_classpath}")

            self._import_java_classes()

        except Exception as e:
            logger.error(f"Failed to start or connect to JVM: {e}", exc_info=True)
            raise RuntimeError(f"JVM Initialization failed: {e}") from e

    def _import_java_classes(self):
        logger.info("Attempting to import TweetyProject Java classes...")
        try:
            _ = jpype.JClass("org.tweetyproject.logics.pl.syntax.PlSignature")
            _ = jpype.JClass("org.tweetyproject.logics.pl.syntax.Proposition")
            _ = jpype.JClass("org.tweetyproject.logics.pl.syntax.PlBeliefSet")
            _ = jpype.JClass("org.tweetyproject.logics.pl.reasoner.SatReasoner")
            _ = jpype.JClass("org.tweetyproject.logics.pl.sat.Sat4jSolver")
            _ = jpype.JClass("org.tweetyproject.logics.fol.syntax.FolSignature")
            _ = jpype.JClass("org.tweetyproject.logics.fol.syntax.FolBeliefSet")
            _ = jpype.JClass("org.tweetyproject.logics.fol.reasoner.SimpleFolReasoner")
            _ = jpype.JClass("org.tweetyproject.logics.ml.syntax.MlFormula")
            _ = jpype.JClass("org.tweetyproject.logics.ml.syntax.MlBeliefSet")
            _ = jpype.JClass("org.tweetyproject.logics.ml.reasoner.SimpleMlReasoner")
            _ = jpype.JClass("org.tweetyproject.logics.ml.parser.MlParser")
            _ = jpype.JClass("org.tweetyproject.commons.ParserException")
            _ = jpype.JClass("org.tweetyproject.logics.commons.syntax.Sort")
            logger.info("Successfully imported TweetyProject Java classes.")
        except Exception as e:
            logger.error(f"Error importing Java classes: {e}", exc_info=True)
            raise RuntimeError(f"Java class import failed: {e}") from e


    def initialize_pl_components(self):
        if not TweetyInitializer._jvm_started:
            self._start_jvm()
        try:
            logger.debug("Initializing PL components...")
            TweetyInitializer._pl_reasoner = jpype.JClass("org.tweetyproject.logics.pl.reasoner.SimplePlReasoner")()
            TweetyInitializer._pl_parser = jpype.JClass("org.tweetyproject.logics.pl.parser.PlParser")()
            logger.info("PL components initialized.")
            return TweetyInitializer._pl_parser, TweetyInitializer._pl_reasoner
        except Exception as e:
            logger.error(f"Error initializing PL components: {e}", exc_info=True)
            raise

    def initialize_fol_components(self):
        if not TweetyInitializer._jvm_started:
            self._start_jvm()
        try:
            logger.debug("Initializing FOL components...")
            TweetyInitializer._fol_parser = jpype.JClass("org.tweetyproject.logics.fol.parser.FolParser")()
            logger.info("FOL parser initialized.")
            return TweetyInitializer._fol_parser
        except Exception as e:
            logger.error(f"Error initializing FOL components: {e}", exc_info=True)
            raise

    def initialize_modal_components(self):
        if not TweetyInitializer._jvm_started:
            self._start_jvm()
        try:
            logger.debug("Initializing Modal Logic components...")
            TweetyInitializer._modal_parser = jpype.JClass("org.tweetyproject.logics.ml.parser.MlParser")()
            logger.info("Modal Logic parser initialized.")
            return TweetyInitializer._modal_parser
        except Exception as e:
            logger.error(f"Error initializing Modal Logic components: {e}", exc_info=True)
            raise

    @staticmethod
    def get_pl_parser():
        return TweetyInitializer._pl_parser

    @staticmethod
    def get_pl_reasoner():
        return TweetyInitializer._pl_reasoner

    @staticmethod
    def get_fol_parser():
        return TweetyInitializer._fol_parser
    
    @staticmethod
    def get_modal_parser():
        return TweetyInitializer._modal_parser

    def is_jvm_started(self):
        return TweetyInitializer._jvm_started

    def shutdown_jvm(self):
        if TweetyInitializer._jvm_started and jpype.isJVMStarted():
            try:
                TweetyInitializer._pl_reasoner = None
                TweetyInitializer._pl_parser = None
                TweetyInitializer._fol_parser = None
                TweetyInitializer._fol_reasoner = None
                TweetyInitializer._modal_logic = None
                TweetyInitializer._modal_parser = None
                TweetyInitializer._modal_reasoner = None
                
                logger.info("Shutting down JVM...")
                jpype.shutdownJVM()
                TweetyInitializer._jvm_started = False
                logger.info("JVM shut down successfully.")
            except Exception as e:
                logger.error(f"Error during JVM shutdown: {e}", exc_info=True)
        elif not TweetyInitializer._jvm_started:
            logger.info("JVM was not started by this class or already shut down.")
        else:
            logger.info("JVM is started but perhaps not by this class, not shutting down.")