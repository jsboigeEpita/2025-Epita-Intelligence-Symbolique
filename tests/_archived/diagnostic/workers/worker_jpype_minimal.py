# tests/diagnostic/workers/worker_jpype_minimal.py
import pytest
import jpype
import jpype.imports
import os
import sys
import logging
from argumentation_analysis.core.jvm_setup import JvmManager

# Configuration du logger
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] %(message)s", datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Assurer que le chemin du projet est dans le sys.path
project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)


# La fixture jvm_session est maintenant gérée par le worker
@pytest.fixture(scope="module")
def jvm_session():
    """Fixture pour gérer le cycle de vie de la JVM pour le module de test."""
    jvm_manager = JvmManager()
    try:
        jvm_manager.start_jvm()
        logger.info("JVM démarrée pour la session de test du worker.")
        yield
    finally:
        if jvm_manager.is_jvm_started():
            logger.info("Arrêt de la JVM pour la session de test du worker.")
            jvm_manager.shutdown_jvm()


def test_jvm_initialization(jvm_session):
    """
    Teste que la JVM est correctement démarrée et qu'il est possible d'interagir avec.
    """
    logger.info("--- Début du test JPype minimal dans le worker ---")
    logger.info(f"Version de Python: {sys.version}")
    logger.info(f"Version de JPype: {jpype.__version__}")

    assert (
        jpype.isJVMStarted()
    ), "La fixture de session n'a pas réussi à démarrer la JVM."
    logger.info("Assertion OK: jpype.isJVMStarted() retourne True.")

    try:
        logger.info("Tentative d'accès à java.lang.System...")
        System = jpype.JClass("java.lang.System")
        java_version_from_jvm = System.getProperty("java.version")
        logger.info(
            f"SUCCESS: Version Java obtenue depuis la JVM: {java_version_from_jvm}"
        )
        assert java_version_from_jvm is not None
    except Exception as e_jclass:
        pytest.fail(f"ERREUR lors du test post-démarrage (JClass): {e_jclass}")

    logger.info("--- Fin du test JPype minimal dans le worker ---")


def main():
    """Point d'entrée principal pour l'exécution des tests."""
    logger.info("Démarrage du worker pour le test JPype minimal...")
    try:
        result = pytest.main([__file__])
        if result == pytest.ExitCode.OK:
            logger.info("Test JPype minimal terminé avec succès.")
            sys.exit(0)
        else:
            logger.error(
                f"Le test JPype minimal a échoué avec le code de sortie: {result}"
            )
            sys.exit(int(result))
    except Exception as e:
        logger.critical(
            f"Erreur critique dans le worker JPype minimal: {e}", exc_info=True
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
