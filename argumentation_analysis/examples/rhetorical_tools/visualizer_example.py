# Visualizer Example

import asyncio
from argumentation_analysis.tools.argument_structure_visualizer import (
    ArgumentStructureVisualizer,
)


async def run_visualizer():
    """
    Exemple d'utilisation du Visualizer pour l'analyse rhétorique
    """
    # Initialisation du visualiseur
    visualizer = ArgumentStructureVisualizer(output_format="graphviz")

    # Structure d'argument à visualiser
    argument_structure = {
        "main_claim": "La vaccination devrait être obligatoire",
        "premises": [
            {
                "statement": "Les vaccins sont sûrs selon les études",
                "supporting_evidence": [
                    "Étude 1: 2000 participants, 0 effets graves",
                    "Étude 2: Revue systématique de 50 études",
                ],
                "counterarguments": [
                    "Certains effets secondaires mineurs peuvent survenir"
                ],
            },
            {
                "statement": "L'immunité collective protège les vulnérables",
                "supporting_evidence": [
                    "Données épidémiologiques montrant la réduction des maladies"
                ],
            },
        ],
        "conclusion": "Donc, la vaccination obligatoire sauve des vies",
    }

    # Génération de la visualisation
    logger.info("Génération de la visualisation de la structure d'argument...")
    visualization = await visualizer.generate_visualization(argument_structure)

    # Affichage et sauvegarde
    logger.info("Visualisation générée:")
    logger.info(f"{visualization}")
    logger.info("Sauvegarde en format DOT...")
    await visualizer.save_visualization("vaccination_argument_structure.dot")


if __name__ == "__main__":
    asyncio.run(run_visualizer())
