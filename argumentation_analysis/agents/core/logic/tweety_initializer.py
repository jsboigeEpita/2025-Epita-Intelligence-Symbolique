# argumentation_analysis/agents/core/logic/tweety_initializer.py
"""
Gestionnaire d'initialisation pour les composants Tweety.
Ce module suppose que la JVM a déjà été démarrée et configurée par un
gestionnaire externe (ex: une fixture pytest de session).
"""
import jpype
import logging
import os
from argumentation_analysis.core.utils.logging_utils import setup_logging
# On importe directement la fonction d'initialisation robuste
from argumentation_analysis.core.jvm_setup import initialize_jvm as initialize_jvm_robustly
from argumentation_analysis.core.jvm_setup import shutdown_jvm, is_jvm_started

logger = logging.getLogger(__name__)

class TweetyInitializer:
    """
    Handles the initialization of JVM and components for TweetyProject.
    The JVM lifecycle is now managed by the central jvm_setup.py module.
    This class acts as a central point for initialization logic and component access.
    """
    _classes_loaded = False
    _pl_parser = None
    _fol_parser = None
    _modal_parser = None
    _modal_reasoner = None
    _initialized_components = False
    _jvm_started = False

    # FOL classes (will be populated by _import_java_classes)
    FolBeliefSet = None
    FolSignature = None
    Sort = None
    Constant = None
    Predicate = None
    FolFormula = None
    FolAtom = None
    ForallQuantifiedFormula = None
    ExistsQuantifiedFormula = None
    Variable = None
    Implication = None
    Conjunction = None

    def __init__(self, tweety_bridge_instance=None):
        if tweety_bridge_instance:
            self._tweety_bridge = tweety_bridge_instance

        if os.environ.get('DISABLE_JAVA_LOGIC') == '1':
            logger.info("Java logic is disabled via 'DISABLE_JAVA_LOGIC'. Skipping JVM checks.")
            return

        # L'initialisation se fait maintenant à la demande, ici.
        if not is_jvm_started():
            logger.info("JVM not started. Calling the robust initializer from jvm_setup.")
            if not self.initialize_jvm():
                # Si l'initialisation échoue, on lève une exception claire.
                raise RuntimeError("JVM could not be started by the robust initializer. Check logs.")

        self.__class__._jvm_started = True

        if not self.__class__._initialized_components:
            logger.info("JVM is running. Initializing Java class imports and components for the first time.")
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
        Delegates JVM initialization to the robust, centralized jvm_setup.py script.
        This script handles JDK provisioning (download, unzip) and proper JVM startup.
        """
        logger.info("Delegating JVM initialization to core.jvm_setup.initialize_jvm...")
        try:
            # On appelle la fonction renommée pour plus de clarté
            if initialize_jvm_robustly():
                logger.info("Robust JVM initialization successful.")
                TweetyInitializer._jvm_started = True
                return True
            else:
                logger.error("Robust JVM initialization failed.")
                return False
        except Exception as e:
            logger.critical(f"An unhandled exception occurred during robust JVM initialization: {e}", exc_info=True)
            return False

    def _import_java_classes(self):
        """
        Imports and caches required Java classes.
        Raises RuntimeError if a class is not found, indicating a classpath issue.
        """
        logger.info("Importation des classes Java de TweetyProject...")
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
            
            # Modal classes
            _ = jpype.JClass("org.tweetyproject.logics.ml.syntax.MlFormula")
            _ = jpype.JClass("org.tweetyproject.logics.ml.syntax.MlBeliefSet")
            _ = jpype.JClass("org.tweetyproject.logics.ml.reasoner.SimpleMlReasoner")
            _ = jpype.JClass("org.tweetyproject.logics.ml.parser.MlParser")
            _ = jpype.JClass("org.tweetyproject.commons.Signature")

            # Reasoner (using EProver, not Prover9)
            jpype.JClass("org.tweetyproject.logics.fol.reasoner.SimpleFolReasoner")
            
            logger.info("Successfully imported and cached TweetyProject Java classes.")
            TweetyInitializer._classes_loaded = True

        except jpype.JException as e:
            logger.error(f"A Java exception occurred during class import: {e.stacktrace()}", exc_info=True)
            java_system = jpype.JClass("java.lang.System")
            actual_classpath = java_system.getProperty("java.class.path")
            logger.error(f"Classpath at time of error: {actual_classpath}")
            raise RuntimeError(f"Java class import failed: {e}") from e
        except Exception as e:
             logger.error(f"A Python exception occurred during class import: {e}", exc_info=True)
             raise RuntimeError(f"A non-Java exception occurred during class import: {e}") from e


    def initialize_pl_components(self):
        if self.__class__._pl_parser:
            return
        try:
            logger.debug("Initializing PL components...")
            self.__class__._pl_parser = jpype.JClass("org.tweetyproject.logics.pl.parser.PlParser")()
            logger.info("PL parser initialized.")
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

    @staticmethod
    def is_jvm_ready() -> bool:
        """Checks if the JVM is started and classes are loaded."""
        return is_jvm_started() and TweetyInitializer._classes_loaded

    def is_jvm_started(self):
         return self.__class__._jvm_started
