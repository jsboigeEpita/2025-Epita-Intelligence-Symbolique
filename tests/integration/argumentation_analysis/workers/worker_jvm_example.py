# -*- coding: utf-8 -*-
# tests/integration/argumentation_analysis/workers/worker_jvm_example.py
"""
Worker pour l'exécution du test d'exemple JVM dans un sous-processus.
"""

import logging
import pytest
import jpype
import jpype.imports
import sys
import os
from argumentation_analysis.core.jvm_setup import JvmManager

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

# Assurer que le chemin du projet est dans le sys.path
project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)


@pytest.fixture(scope="module")
def jvm_session():
    """Fixture pour gérer le cycle de vie de la JVM pour le module de test."""
    jvm_manager = JvmManager()
    try:
        jvm_manager.start_jvm()
        logging.info("JVM démarrée pour la session de test du worker.")
        yield
    finally:
        if jvm_manager.is_jvm_started():
            logging.info("Arrêt de la JVM pour la session de test du worker.")
            jvm_manager.shutdown_jvm()


def test_jvm_is_actually_started(jvm_session):
    """
    Teste si la JVM est bien démarrée en utilisant la fixture de session partagée.
    """
    assert (
        jpype.isJVMStarted()
    ), "La JVM devrait être démarrée par la fixture de session"
    logging.info(f"JVM Version from jpype: {jpype.getJVMVersion()}")


def main():
    """Point d'entrée principal pour l'exécution des tests."""
    logging.info("Démarrage du worker pour le test d'exemple JVM...")
    try:
        result = pytest.main([__file__])
        if result == pytest.ExitCode.OK:
            logging.info("Test d'exemple JVM terminé avec succès.")
            sys.exit(0)
        else:
            logging.error(f"Le test d'exemple JVM a échoué: {result}")
            sys.exit(int(result))
    except Exception as e:
        logging.critical(
            f"Erreur critique dans le worker d'exemple JVM: {e}", exc_info=True
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
