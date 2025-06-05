import jpype
import jpype.imports
from jpype.types import JString
import logging
from argumentation_analysis.utils.core_utils.logging_utils import setup_logging
from argumentation_analysis.utils.core_utils.file_utils import get_project_root
from pathlib import Path

logger = setup_logging(__name__)

class TweetyInitializer:
    """
    Handles the initialization of JVM components for TweetyProject.
    This includes starting the JVM, setting up classpaths, and initializing
    specific logic components like PL, FOL, and Modal logic.
    """

    _jvm_started = False
    _pl_reasoner = None
    _pl_parser = None
    _fol_parser = None
    _fol_reasoner = None
    _modal_logic = None
    _modal_parser = None
    _modal_reasoner = None
    _tweety_bridge = None # Reference to the main bridge

    def __init__(self, tweety_bridge_instance):
        self._tweety_bridge = tweety_bridge_instance
        if not TweetyInitializer._jvm_started:
            self._start_jvm()

    def _start_jvm(self):
        """Starts the JVM and sets up the classpath."""
        if TweetyInitializer._jvm_started:
            logger.info("JVM already started.")
            return

        try:
            project_root = get_project_root()
            tweety_lib_path = project_root / "libs" / "tweety"
            
            # Updated classpath based on previous successful runs
            classpath_entries = [
                tweety_lib_path / "tweety.jar",
                tweety_lib_path / "lib" / "*", # General libs
            ]
            
            # Convert Path objects to strings for jpype
            classpath = [str(p) for p in classpath_entries]
            logger.info(f"Calculated Classpath: {classpath}")

            if not jpype.isJVMStarted():
                logger.info("Starting JVM...")
                jpype.startJVM(
                    jpype.getDefaultJVMPath(),
                    "-ea",
                    f"-Djava.class.path={Path.pathsep.join(classpath)}",
                    convertStrings=False
                )
                TweetyInitializer._jvm_started = True
                logger.info("JVM started successfully.")
            else:
                logger.info("JVM was already started by another component.")
                TweetyInitializer._jvm_started = True

            # Import necessary Java classes after JVM start
            self._import_java_classes()

        except Exception as e:
            logger.error(f"Failed to start or connect to JVM: {e}", exc_info=True)
            # Propagate the exception if critical for the application
            raise RuntimeError(f"JVM Initialization failed: {e}") from e

    def _import_java_classes(self):
        """Imports Java classes required by TweetyBridge."""
        try:
            # Propositional Logic
            jpype.imports.org.tweetyproject.logics.pl.syntax
            jpype.imports.org.tweetyproject.logics.pl.reasoner
            jpype.imports.org.tweetyproject.logics.pl.sat
            # First-Order Logic
            jpype.imports.org.tweetyproject.logics.fol.syntax
            jpype.imports.org.tweetyproject.logics.fol.reasoner
            # Modal Logic
            jpype.imports.org.tweetyproject.logics.ml.syntax
            jpype.imports.org.tweetyproject.logics.ml.reasoner
            jpype.imports.org.tweetyproject.logics.ml.parser.MlParser # Specific import for Modal parser
            # General TweetyProject classes
            jpype.imports.org.tweetyproject.commons.ParserException
            jpype.imports.org.tweetyproject.logics.commons.syntax.Sort
            logger.info("Successfully imported TweetyProject Java classes.")
        except Exception as e:
            logger.error(f"Error importing Java classes: {e}", exc_info=True)
            raise RuntimeError(f"Java class import failed: {e}") from e


    def initialize_pl_components(self):
        """Initializes components for Propositional Logic."""
        if not TweetyInitializer._jvm_started:
            self._start_jvm()
        try:
            logger.debug("Initializing PL components...")
            TweetyInitializer._pl_reasoner = jpype.JClass("org.tweetyproject.logics.pl.reasoner.SatReasoner")()
            TweetyInitializer._pl_parser = jpype.JClass("org.tweetyproject.logics.pl.parser.PlParser")()
            logger.info("PL components initialized.")
            return TweetyInitializer._pl_parser, TweetyInitializer._pl_reasoner
        except Exception as e:
            logger.error(f"Error initializing PL components: {e}", exc_info=True)
            raise

    def initialize_fol_components(self):
        """Initializes components for First-Order Logic."""
        if not TweetyInitializer._jvm_started:
            self._start_jvm()
        try:
            logger.debug("Initializing FOL components...")
            TweetyInitializer._fol_parser = jpype.JClass("org.tweetyproject.logics.fol.parser.FolParser")()
            # FOL reasoner might depend on specific setup or be a more general interface
            # For now, let's assume a default or no specific reasoner instance needed at class level
            # TweetyInitializer._fol_reasoner = ...
            logger.info("FOL parser initialized.")
            return TweetyInitializer._fol_parser
        except Exception as e:
            logger.error(f"Error initializing FOL components: {e}", exc_info=True)
            raise

    def initialize_modal_components(self):
        """Initializes components for Modal Logic."""
        if not TweetyInitializer._jvm_started:
            self._start_jvm()
        try:
            logger.debug("Initializing Modal Logic components...")
            # Modal logic might have different types (K, S4, S5 etc.)
            # For now, let's assume a general parser and perhaps a default logic
            # The MlParser class was specifically imported
            TweetyInitializer._modal_parser = jpype.JClass("org.tweetyproject.logics.ml.parser.MlParser")()
            
            # Example: Defaulting to S4 logic if a specific one is needed for the reasoner
            # TweetyLogic = jpype.JClass("org.tweetyproject.logics.ml.syntax.ModalLogicType")
            # TweetyInitializer._modal_logic = TweetyLogic.S4

            # Modal reasoner might also depend on the specific modal logic type
            # TweetyInitializer._modal_reasoner = ...
            logger.info("Modal Logic parser initialized.")
            return TweetyInitializer._modal_parser
        except Exception as e:
            logger.error(f"Error initializing Modal Logic components: {e}", exc_info=True)
            raise

    @staticmethod
    def get_pl_parser():
        if TweetyInitializer._pl_parser is None:
            # This might indicate an issue if called before initialization by the bridge
            logger.warning("PL Parser accessed before explicit initialization by TweetyBridge.")
            # Fallback or error, for now, let's assume bridge handles init order
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

    # Add other static getters if needed for reasoners or specific logic instances

    def is_jvm_started(self):
        """Checks if the JVM is started."""
        return TweetyInitializer._jvm_started

    def shutdown_jvm(self):
        """Shuts down the JVM if it was started by this class."""
        if TweetyInitializer._jvm_started and jpype.isJVMStarted():
            try:
                # Perform any necessary cleanup of TweetyProject resources here
                # For example, explicitly nullifying static references if they hold onto Java objects
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