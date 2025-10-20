#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour tester l'orchestration à l'échelle sur un texte complexe.

Ce script sélectionne un texte complexe depuis les sources disponibles,
extrait son contenu et lance l'orchestration avec tous les agents.
"""

import sys
import asyncio
import logging
from pathlib import Path

# Ajouter le répertoire parent au chemin de recherche des modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("TestOrchestrationScale")

# Importer les fonctions nécessaires


async def load_kremlin_speech():
    """
    Charge directement le texte complet du discours du Kremlin depuis le cache.

    Returns:
        Le texte complet du discours
    """
    # Identifiant du fichier cache pour le discours du Kremlin
    cache_id = "4cf2d4853745719f6504a54610237738ad016de4f64176c3e8f5218f8fd2c01b"
    cache_path = Path(f"../text_cache/{cache_id}.txt")

    logger.info(f"Chargement direct du discours du Kremlin depuis le cache...")

    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            text = f.read()

        if not text:
            logger.error("Le fichier cache est vide.")
            return None

        logger.info(f"Texte chargé avec succès ({len(text)} caractères)")
        return text
    except Exception as e:
        logger.error(f"Erreur lors du chargement du fichier cache: {e}")
        return None


async def run_orchestration_test():
    """
    Exécute le test d'orchestration à l'échelle.
    """
    # Charger le texte du discours du Kremlin directement depuis le cache
    text_content = await load_kremlin_speech()

    if not text_content:
        logger.error("Impossible de charger le texte pour le test.")
        return

    logger.info(f"Texte chargé pour le test ({len(text_content)} caractères)")

    # Initialiser l'environnement (le chargement de .env est maintenant implicite via settings)

    # Initialisation de la JVM
    from argumentation_analysis.core.jvm_setup import initialize_jvm

    jvm_ready_status = initialize_jvm(lib_dir_path=LIBS_DIR)

    if not jvm_ready_status:
        logger.warning(
            "⚠️ JVM n'a pas pu être initialisée. L'agent PropositionalLogicAgent ne fonctionnera pas."
        )

    # Création du Service LLM
    from argumentation_analysis.core.llm_service import create_llm_service

    llm_service = create_llm_service(
        service_id="orchestration_scale_test", model_id="gpt-4o-mini"
    )

    if not llm_service:
        logger.error("❌ Impossible de créer le service LLM.")
        return

    # Exécuter l'orchestration avec tous les agents
    from argumentation_analysis.orchestration.analysis_runner import (
        run_analysis_conversation,
    )

    logger.info("Lancement de l'orchestration avec tous les agents...")
    start_time = asyncio.get_event_loop().time()

    try:
        await run_analysis_conversation(
            texte_a_analyser=text_content, llm_service=llm_service
        )

        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time

        logger.info(f"🏁 Orchestration terminée avec succès en {duration:.2f} secondes.")
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'orchestration: {e}", exc_info=True)


async def main():
    """
    Fonction principale du script.
    """
    logger.info("Démarrage du test d'orchestration à l'échelle...")
    await run_orchestration_test()
    logger.info("Test d'orchestration terminé.")


if __name__ == "__main__":
    asyncio.run(main())
