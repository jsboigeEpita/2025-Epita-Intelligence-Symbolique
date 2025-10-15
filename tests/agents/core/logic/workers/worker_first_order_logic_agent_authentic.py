# -*- coding: utf-8 -*-
# tests/agents/core/logic/workers/worker_first_order_logic_agent_authentic.py
"""
Worker pour l'exécution des tests de FOLLogicAgent dans un sous-processus JVM isolé.
"""
import pytest
import sys
import os
import logging

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
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Imports originaux migrés
from semantic_kernel import Kernel
from argumentation_analysis.agents.core.logic.fol_logic_agent import FOLLogicAgent
from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge
from argumentation_analysis.core.jvm_setup import JvmManager


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


@pytest.mark.asyncio
async def test_agent_initialization_simplified(jvm_session):
    """
    Test d'initialisation simplifié pour valider la configuration de base.
    """
    logger.info("\n--- Démarrage du test d'initialisation simplifié dans le worker ---")

    # 1. Initialisation du Kernel
    kernel = Kernel()
    llm_service_id = "test_service"

    # 2. Initialisation de TweetyBridge (en utilisant la fixture jvm_session)
    try:
        tweety_bridge = TweetyBridge()
        tweety_available = tweety_bridge.initializer.is_jvm_ready()
        assert tweety_available, "La JVM de TweetyBridge n'est pas prête."
        logger.info(
            f"✅ TweetyBridge est prêt (JVM démarrée par jvm_session: {tweety_available})"
        )
    except Exception as e:
        pytest.fail(f"Échec de l'initialisation de TweetyBridge: {e}")

    # 3. Initialisation de l'agent
    agent = FOLLogicAgent(
        kernel, tweety_bridge=tweety_bridge, service_id=llm_service_id
    )
    assert agent is not None
    assert agent.tweety_bridge is tweety_bridge
    logger.info("✅ Agent FOLLogicAgent initialisé")

    logger.info(
        "--- Test d'initialisation simplifié terminé avec succès dans le worker ---"
    )


def main():
    """Point d'entrée principal pour l'exécution des tests."""
    logger.info("Démarrage du worker pour TestFirstOrderLogicAgent...")

    try:
        # Exécuter les tests pytest
        # Le test est dans ce même fichier.
        result = pytest.main([__file__])

        if result == pytest.ExitCode.OK:
            logger.info("Tests terminés avec succès dans le worker.")
            sys.exit(0)
        else:
            logger.error(
                f"Les tests ont échoué dans le worker avec le code de sortie: {result}"
            )
            sys.exit(int(result))

    except Exception as e:
        logger.critical(
            f"Une erreur critique est survenue dans le worker: {e}", exc_info=True
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
