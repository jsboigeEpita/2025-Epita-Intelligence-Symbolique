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

# Initialisation du logger pour ce module.
setup_logging("INFO")
logger = logging.getLogger(__name__)

class TweetyInitializer:
    """
    Handles the initialization of JVM and components for TweetyProject.
    The JVM lifecycle is now managed by the central jvm_setup.py module.
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

    def __init__(self, tweety_bridge_instance):
        self._tweety_bridge = tweety_bridge_instance

        if os.environ.get('DISABLE_JAVA_LOGIC') == '1':
            logger.info("Java logic is disabled via 'DISABLE_JAVA_LOGIC'. Skipping JVM checks.")
            self.__class__._jvm_started = False
            return

        # L'initialisation se fait maintenant à la demande, ici.
        if not is_jvm_started():
            logger.info("JVM not started. Calling the robust initializer from jvm_setup.")
            if not self.initialize_jvm():
                # Si l'initialisation échoue, on lève une exception claire.
                raise RuntimeError("JVM could not be started by the robust initializer. Check logs.")

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
        Importe les classes Java requises et les met en cache.
        Lève une RuntimeError si une classe n'est pas trouvée, indiquant un
        problème de classpath.
        """
        logger.info("Importation des classes Java de TweetyProject...")
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
            _ = jpype.JClass("org.tweetyproject.commons.Signature")
            _ = jpype.JClass("org.tweetyproject.logics.commons.syntax.Constant")
            logger.info("Successfully imported TweetyProject Java classes.")

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
