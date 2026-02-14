"""
Exemple d'utilisation des agents dans l'architecture hiérarchique à trois niveaux.

Ce script montre comment utiliser les adaptateurs et le gestionnaire opérationnel
pour exécuter des tâches d'analyse dans la nouvelle architecture hiérarchique.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
import json

# Ajouter le répertoire parent au chemin de recherche des modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from argumentation_analysis.orchestration.hierarchical.operational.state import (
    OperationalState,
)
from argumentation_analysis.orchestration.hierarchical.operational.agent_registry import (
    OperationalAgentRegistry,
)
from argumentation_analysis.orchestration.hierarchical.operational.manager import (
    OperationalManager,
)
from argumentation_analysis.orchestration.hierarchical.interfaces.tactical_operational import (
    TacticalOperationalInterface,
)
from argumentation_analysis.orchestration.hierarchical.tactical.state import (
    TacticalState,
)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("HierarchicalExample")


async def example_extract_agent():
    """
    Exemple d'utilisation de l'agent d'extraction dans la nouvelle architecture.
    """
    logger.info("=== Exemple d'utilisation de l'agent d'extraction ===")

    # Créer les états
    tactical_state = TacticalState()
    operational_state = OperationalState()

    # Créer l'interface tactique-opérationnelle
    interface = TacticalOperationalInterface(tactical_state, operational_state)

    # Créer le gestionnaire opérationnel
    manager = OperationalManager(operational_state, interface)
    await manager.start()

    try:
        # Créer une tâche tactique pour l'extraction
        tactical_task = {
            "id": "task-extract-1",
            "description": "Extraire les segments de texte contenant des arguments potentiels",
            "objective_id": "obj-1",
            "estimated_duration": "short",
            "required_capabilities": ["text_extraction"],
            "priority": "high",
        }

        # Ajouter la tâche à l'état tactique
        tactical_state.add_task(tactical_task)

        # Traiter la tâche
        logger.info(f"Traitement de la tâche tactique: {tactical_task['id']}")
        result = await manager.process_tactical_task(tactical_task)

        # Afficher le résultat
        logger.info(f"Résultat: {json.dumps(result, indent=2)}")

    finally:
        # Arrêter le gestionnaire
        await manager.stop()


async def example_informal_agent():
    """
    Exemple d'utilisation de l'agent informel dans la nouvelle architecture.
    """
    logger.info("=== Exemple d'utilisation de l'agent informel ===")

    # Créer les états
    tactical_state = TacticalState()
    operational_state = OperationalState()

    # Créer l'interface tactique-opérationnelle
    interface = TacticalOperationalInterface(tactical_state, operational_state)

    # Créer le gestionnaire opérationnel
    manager = OperationalManager(operational_state, interface)
    await manager.start()

    try:
        # Créer une tâche tactique pour l'analyse informelle
        tactical_task = {
            "id": "task-informal-1",
            "description": "Identifier les arguments et analyser les sophismes",
            "objective_id": "obj-1",
            "estimated_duration": "medium",
            "required_capabilities": ["argument_identification", "fallacy_detection"],
            "priority": "high",
        }

        # Ajouter la tâche à l'état tactique
        tactical_state.add_task(tactical_task)

        # Traiter la tâche
        logger.info(f"Traitement de la tâche tactique: {tactical_task['id']}")
        result = await manager.process_tactical_task(tactical_task)

        # Afficher le résultat
        logger.info(f"Résultat: {json.dumps(result, indent=2)}")

    finally:
        # Arrêter le gestionnaire
        await manager.stop()


async def example_pl_agent():
    """
    Exemple d'utilisation de l'agent de logique propositionnelle dans la nouvelle architecture.
    """
    logger.info("=== Exemple d'utilisation de l'agent de logique propositionnelle ===")

    # Créer les états
    tactical_state = TacticalState()
    operational_state = OperationalState()

    # Créer l'interface tactique-opérationnelle
    interface = TacticalOperationalInterface(tactical_state, operational_state)

    # Créer le gestionnaire opérationnel
    manager = OperationalManager(operational_state, interface)
    await manager.start()

    try:
        # Créer une tâche tactique pour l'analyse formelle
        tactical_task = {
            "id": "task-pl-1",
            "description": "Formaliser les arguments en logique propositionnelle et vérifier leur validité",
            "objective_id": "obj-1",
            "estimated_duration": "medium",
            "required_capabilities": ["formal_logic", "validity_checking"],
            "priority": "high",
        }

        # Ajouter la tâche à l'état tactique
        tactical_state.add_task(tactical_task)

        # Traiter la tâche
        logger.info(f"Traitement de la tâche tactique: {tactical_task['id']}")
        result = await manager.process_tactical_task(tactical_task)

        # Afficher le résultat
        logger.info(f"Résultat: {json.dumps(result, indent=2)}")

    finally:
        # Arrêter le gestionnaire
        await manager.stop()


async def example_complete_analysis():
    """
    Exemple d'analyse complète utilisant les trois agents dans la nouvelle architecture.
    """
    logger.info("=== Exemple d'analyse complète ===")

    # Créer les états
    tactical_state = TacticalState()
    operational_state = OperationalState()

    # Créer l'interface tactique-opérationnelle
    interface = TacticalOperationalInterface(tactical_state, operational_state)

    # Créer le gestionnaire opérationnel
    manager = OperationalManager(operational_state, interface)
    await manager.start()

    try:
        # Texte à analyser
        text = """
        La vaccination devrait être obligatoire pour tous les enfants. Les vaccins ont été prouvés sûrs par de nombreuses études scientifiques. De plus, la vaccination de masse crée une immunité collective qui protège les personnes vulnérables qui ne peuvent pas être vaccinées pour des raisons médicales. Certains parents s'inquiètent des effets secondaires, mais ces effets sont généralement mineurs et temporaires. Le risque de complications graves dues aux maladies évitables par la vaccination est bien plus élevé que le risque d'effets secondaires graves des vaccins.
        """

        # Ajouter le texte à l'état tactique
        tactical_state.raw_text = text

        # 1. Extraction des segments pertinents
        extract_task = {
            "id": "task-extract-1",
            "description": "Extraire les segments de texte contenant des arguments potentiels",
            "objective_id": "obj-1",
            "estimated_duration": "short",
            "required_capabilities": ["text_extraction"],
            "priority": "high",
        }

        # Ajouter la tâche à l'état tactique
        tactical_state.add_task(extract_task)

        # Traiter la tâche
        logger.info(f"1. Traitement de la tâche d'extraction: {extract_task['id']}")
        extract_result = await manager.process_tactical_task(extract_task)
        logger.info(f"Résultat de l'extraction: {json.dumps(extract_result, indent=2)}")

        # 2. Analyse informelle
        informal_task = {
            "id": "task-informal-1",
            "description": "Identifier les arguments et analyser les sophismes",
            "objective_id": "obj-1",
            "estimated_duration": "medium",
            "required_capabilities": ["argument_identification", "fallacy_detection"],
            "priority": "high",
        }

        # Ajouter la tâche à l'état tactique
        tactical_state.add_task(informal_task)

        # Traiter la tâche
        logger.info(
            f"2. Traitement de la tâche d'analyse informelle: {informal_task['id']}"
        )
        informal_result = await manager.process_tactical_task(informal_task)
        logger.info(
            f"Résultat de l'analyse informelle: {json.dumps(informal_result, indent=2)}"
        )

        # 3. Analyse formelle
        pl_task = {
            "id": "task-pl-1",
            "description": "Formaliser les arguments en logique propositionnelle et vérifier leur validité",
            "objective_id": "obj-1",
            "estimated_duration": "medium",
            "required_capabilities": ["formal_logic", "validity_checking"],
            "priority": "high",
        }

        # Ajouter la tâche à l'état tactique
        tactical_state.add_task(pl_task)

        # Traiter la tâche
        logger.info(f"3. Traitement de la tâche d'analyse formelle: {pl_task['id']}")
        pl_result = await manager.process_tactical_task(pl_task)
        logger.info(
            f"Résultat de l'analyse formelle: {json.dumps(pl_result, indent=2)}"
        )

        # Afficher un résumé
        logger.info("=== Résumé de l'analyse ===")
        logger.info(f"Texte analysé: {text}")
        logger.info(f"Extraction: {extract_result['completion_status']}")
        logger.info(f"Analyse informelle: {informal_result['completion_status']}")
        logger.info(f"Analyse formelle: {pl_result['completion_status']}")

    finally:
        # Arrêter le gestionnaire
        await manager.stop()


async def main():
    """
    Fonction principale exécutant les exemples.
    """
    logger.info("Démarrage des exemples d'utilisation de l'architecture hiérarchique")

    # Exécuter les exemples
    await example_extract_agent()
    await example_informal_agent()
    await example_pl_agent()
    await example_complete_analysis()

    logger.info("Fin des exemples")


if __name__ == "__main__":
    # Exécuter la fonction principale
    asyncio.run(main())
