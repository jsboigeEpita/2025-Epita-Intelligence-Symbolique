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
from pathlib import Path
import os
import subprocess

setup_logging("INFO")
logger = logging.getLogger(__name__)

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

        if not jpype.isJVMStarted():
            logger.info("JVM not detected as started. TweetyInitializer will now attempt to start it.")
            self._start_jvm()
        else:
            logger.info("TweetyInitializer confirmed that JVM is already started by another component.")
            TweetyInitializer._jvm_started = True
            self._import_java_classes()

    def _start_jvm(self):
        """Starts the JVM and sets up the classpath."""
        global logger
        if logger is None:
            setup_logging("INFO")
            logger = logging.getLogger(__name__)
            logger.error("CRITICAL: TweetyInitializer module logger was None and had to be re-initialized in _start_jvm.")

        if TweetyInitializer._jvm_started:
            logger.info("JVM already started.")
            return

        try:
            project_root = Path(__file__).resolve().parents[4]
            tweety_lib_path = project_root / "libs" / "tweety"
            logger.info(f"Contenu de tweety_lib_path ({tweety_lib_path}):")
            try:
                for item in os.listdir(tweety_lib_path):
                    logger.info(f"  - {item}")
            except Exception as e_ls:
                logger.error(f"    Impossible de lister {tweety_lib_path}: {e_ls}")

            tweety_jar_file = tweety_lib_path / "org.tweetyproject.tweety-full-1.28-with-dependencies.jar"

            classpath_entries = [tweety_jar_file]
            classpath = [str(p) for p in classpath_entries]
            logger.info(f"Calculated Classpath: {classpath}")

            if not jpype.isJVMStarted():
                logger.info("Starting JVM...")
                try:
                    java_home = os.environ.get('JAVA_HOME')
                    jvm_path = None
                    if java_home:
                        java_home_path = Path(java_home)
                        if not java_home_path.is_absolute():
                            java_home_path = (project_root / java_home.lstrip('./')).resolve()
                        
                        logger.info(f"Chemin JAVA_HOME résolu: {java_home_path}")

                        if os.name == 'nt':  # Windows
                            possible_jvm_paths = [
                                java_home_path / 'bin' / 'server' / 'jvm.dll',
                                java_home_path / 'bin' / 'client' / 'jvm.dll',
                                java_home_path / 'bin' / 'jvm.dll'
                            ]
                            for path in possible_jvm_paths:
                                if path.exists():
                                    jvm_path = str(path)
                                    logger.info(f"Utilisation du JVM depuis JAVA_HOME: {jvm_path}")
                                    break
                            if not jvm_path:
                                logger.warning(f"JVM introuvable dans les chemins standards de JAVA_HOME: {java_home_path}")
                        else:  # Unix/Linux
                            path = java_home_path / 'lib' / 'server' / 'libjvm.so'
                            if path.exists():
                                jvm_path = str(path)
                                logger.info(f"Utilisation du JVM depuis JAVA_HOME: {jvm_path}")
                            else:
                                logger.warning(f"JVM introuvable dans JAVA_HOME: {path}")

                    if not jvm_path:
                        logger.info("Utilisation du JVM par défaut du système")
                        jvm_path = jpype.getDefaultJVMPath()

                    logger.info(f"Using JVM Path: {jvm_path}")
                    
                    jpype.startJVM(
                        jvm_path,
                        f"-Djava.class.path={os.pathsep.join(classpath)}",
                        "-Xmx1g",
                        "-Xms256m",
                        "-XX:+UseG1GC",
                        "-XX:MaxMetaspaceSize=256m",
                        "-Dfile.encoding=UTF-8",
                        convertStrings=False,
                        ignoreUnrecognized=False
                    )
                    TweetyInitializer._jvm_started = True
                    logger.info("JVM started successfully.")
                except Exception as e:
                    logger.error(f"Échec d'initialisation JVM: {e}")
                    raise RuntimeError(f"Impossible d'initialiser la JVM: {e}") from e
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