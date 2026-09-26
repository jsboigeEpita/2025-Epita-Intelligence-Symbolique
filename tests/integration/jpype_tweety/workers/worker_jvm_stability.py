# -*- coding: utf-8 -*-
import jpype
import jpype.imports
import sys
import logging

from _production_jvm import start_jvm

# Configuration du logger pour le worker
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_jvm_stability_logic():
    """
    Contient la logique de test pour la stabilité de base de la JVM,
    exécutée dans un sous-processus.
    """
    print("--- Début du worker pour test_jvm_stability_logic ---")

    # #2610: the JVM starts the way production starts it.
    start_jvm()

    # Logique de test issue de TestJvmStability
    try:
        logger.info("Vérification si la JVM est démarrée...")
        assert jpype.isJVMStarted(), "La JVM devrait être démarrée."
        logger.info("JVM démarrée avec succès.")

        logger.info("Tentative de chargement de java.lang.String...")
        StringClass = jpype.JClass("java.lang.String")
        assert StringClass is not None, "java.lang.String n'a pas pu être chargée."
        logger.info("java.lang.String chargée avec succès.")

        # Test simple d'utilisation
        java_string = StringClass("Hello from JPype worker")
        py_string = str(java_string)
        assert (
            py_string == "Hello from JPype worker"
        ), "La conversion de chaîne Java en Python a échoué."
        logger.info(f"Chaîne Java créée et convertie: '{py_string}'")

    except Exception as e:
        logger.error(f"Erreur lors du test de stabilité de la JVM: {e}")
        # En cas d'erreur, nous voulons que le processus worker échoue
        # et propage l'erreur au test principal.
        raise
    finally:
        # Ne pas arrêter la JVM ici. La fixture pytest s'en chargera.
        # if jpype.isJVMStarted():
        #     jpype.shutdownJVM()
        #     print("--- JVM arrêtée avec succès dans le worker ---")
        print(
            "--- Le worker a terminé sa tâche. La gestion de l'arrêt de la JVM est laissée au processus principal. ---"
        )

    print("--- Assertions du worker réussies ---")


if __name__ == "__main__":
    try:
        test_jvm_stability_logic()
        print("--- Le worker de stabilité JVM s'est terminé avec succès. ---")
    except Exception as e:
        print(
            f"Une erreur est survenue dans le worker de stabilité JVM : {e}",
            file=sys.stderr,
        )
        sys.exit(1)
