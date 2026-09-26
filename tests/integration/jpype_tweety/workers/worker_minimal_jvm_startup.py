# -*- coding: utf-8 -*-
import jpype
import jpype.imports
import sys
import logging

from _production_jvm import start_jvm

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_minimal_startup_logic():
    """
    Logique de test pour un démarrage minimal de la JVM.
    S'assure que la JVM peut être démarrée et qu'une classe de base est accessible.
    """
    print("--- Début du worker pour test_minimal_startup_logic ---")

    if jpype.isJVMStarted():
        logger.warning(
            "La JVM était déjà démarrée au début du worker. Ce n'est pas attendu."
        )
        # Ce n'est pas une erreur fatale, mais c'est bon à savoir.

    # #2610: the JVM starts the way production starts it.
    start_jvm()

    try:
        assert jpype.isJVMStarted(), "La JVM devrait être active après startJVM."
        logger.info("Assertion jpype.isJVMStarted() réussie.")

        # Test de base pour s'assurer que la JVM est fonctionnelle
        StringClass = jpype.JClass("java.lang.String")
        java_string = StringClass("Test minimal réussi")
        assert str(java_string) == "Test minimal réussi"
        logger.info("Test de création/conversion de java.lang.String réussi.")

        print("--- Toutes les assertions du worker ont réussi ---")

    except Exception as e:
        logger.error(
            f"Erreur durant l'exécution de la logique du worker: {e}", exc_info=True
        )
        raise
    finally:
        # Ne pas arrêter la JVM ici. La fixture pytest s'en chargera.
        # if jpype.isJVMStarted():
        #     jpype.shutdownJVM()
        #     print("--- JVM arrêtée avec succès dans le worker ---")
        print(
            "--- Le worker a terminé sa tâche. La gestion de l'arrêt de la JVM est laissée au processus principal. ---"
        )


if __name__ == "__main__":
    try:
        test_minimal_startup_logic()
        print("--- Le worker de démarrage minimal s'est terminé avec succès. ---")
    except Exception as e:
        print(
            f"Une erreur est survenue dans le worker de démarrage minimal : {e}",
            file=sys.stderr,
        )
        sys.exit(1)
