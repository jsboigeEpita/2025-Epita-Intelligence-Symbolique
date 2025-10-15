# Strategic-Tactical Communication Example

import asyncio
from argumentation_analysis.orchestration.hierarchical.strategic.planner import (
    StrategicPlanner,
)
from argumentation_analysis.orchestration.hierarchical.tactical.resolver import (
    TacticalResolver,
)
from argumentation_analysis.orchestration.hierarchical.interfaces.strategic_tactical import (
    StrategicTacticalInterface,
)


async def run_strategic_tactical_communication():
    """
    Exemple de communication hiérarchique entre niveaux stratégique et tactique
    """
    # Initialisation des composants
    strategic_planner = StrategicPlanner()
    tactical_resolver = TacticalResolver()
    interface = StrategicTacticalInterface()

    # Connexion des composants
    await interface.connect(strategic_planner, tactical_resolver)

    # Plan stratégique initial
    strategic_plan = {
        "objectives": ["analyser_coherence", "detecter_sophismes"],
        "constraints": {"max_duration": "30s", "priority": "high"},
        "text": "La réforme éducative est nécessaire pour améliorer la qualité des enseignants.",
    }

    # Envoi du plan stratégique
    logger.info("Envoi du plan stratégique vers le niveau tactique")
    tactical_response = await interface.send_to_tactical(strategic_plan)

    # Affichage de la réponse tactique
    logger.info(f"Plan tactique reçu: {json.dumps(tactical_response, indent=2)}")

    # Mise à jour stratégique
    strategic_update = {
        "type": "priority_change",
        "content": {
            "new_priority": "critical",
            "reason": "Détecté sophisme potentiel dans le texte",
        },
    }

    # Envoi de la mise à jour stratégique
    logger.info("Envoi de mise à jour stratégique")
    final_response = await interface.send_to_tactical(strategic_update)

    logger.info(f"Résultat final: {json.dumps(final_response, indent=2)}")


if __name__ == "__main__":
    asyncio.run(run_strategic_tactical_communication())
