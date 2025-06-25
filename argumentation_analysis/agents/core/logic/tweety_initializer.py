# argumentation_analysis/agents/core/logic/tweety_initializer.py
"""
Gestionnaire d'initialisation pour les composants Tweety.
Ce module suppose que la JVM a déjà été démarrée et configurée par un
gestionnaire externe (ex: une fixture pytest de session).
"""
import jpype
import logging

logger = logging.getLogger(__name__)

class TweetyInitializer:
    """
    Vérifie que la JVM est démarrée et importe les classes Java essentielles
    de TweetyProject.
    """
    _jvm_started = False
    _classes_loaded = False
    _pl_parser = None
    _fol_parser = None
    _modal_parser = None

    def __init__(self):
        """
        Valide l'état de la JVM et charge les classes Java.
        """
        if not jpype.isJVMStarted():
            logger.critical("TweetyInitializer a été appelé, mais la JVM n'est pas démarrée. "
                          "Le cycle de vie de la JVM doit être géré en amont.")
            raise RuntimeError("JVM not started. Cannot proceed with TweetyInitializer.")
        
        TweetyInitializer._jvm_started = True
        logger.info("TweetyInitializer confirme que la JVM est démarrée.")

        if not TweetyInitializer._classes_loaded:
            self._import_java_classes()

    def _import_java_classes(self):
        """
        Importe les classes Java requises et les met en cache.
        Lève une RuntimeError si une classe n'est pas trouvée, indiquant un
        problème de classpath.
        """
        logger.info("Importation des classes Java de TweetyProject...")
        try:
            # Log du classpath pour le débogage
            class_path = jpype.java.lang.System.getProperty("java.class.path")
            logger.debug(f"Java ClassPath: {class_path}")

            # Classes essentielles
            jpype.JClass("org.tweetyproject.logics.pl.syntax.PlBeliefSet")
            jpype.JClass("org.tweetyproject.logics.fol.syntax.FolBeliefSet")
            jpype.JClass("org.tweetyproject.logics.ml.syntax.MlBeliefSet")

            # Parsers
            TweetyInitializer._pl_parser = jpype.JClass("org.tweetyproject.logics.pl.parser.PlParser")()
            TweetyInitializer._fol_parser = jpype.JClass("org.tweetyproject.logics.fol.parser.FolParser")()
            TweetyInitializer._modal_parser = jpype.JClass("org.tweetyproject.logics.ml.parser.MlParser")()

            TweetyInitializer._classes_loaded = True
            logger.info("Toutes les classes et parseurs Java de Tweety ont été chargés avec succès.")

        except jpype.JException as e:
            logger.critical(f"Échec de l'importation d'une classe Java : {e.getMessage()}", exc_info=True)
            logger.critical("Cela indique un problème fatal avec le classpath fourni à la JVM.")
            raise RuntimeError(f"Failed to import a required Tweety class: {e.getMessage()}") from e

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

    def is_jvm_started(self) -> bool:
        return TweetyInitializer._jvm_started