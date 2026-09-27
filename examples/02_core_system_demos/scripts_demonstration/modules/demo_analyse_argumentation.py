# -*- coding: utf-8 -*-
"""
Module de démonstration : Analyse d'Arguments & Sophismes
Ce module utilise la AgentFactory pour instancier dynamiquement un agent
d'analyse en fonction des paramètres fournis.
"""

import asyncio
from typing import cast

import semantic_kernel as sk
from argumentation_analysis.agents.factory import AgentFactory
from argumentation_analysis.agents.concrete_agents.informal_fallacy_agent import (
    InformalFallacyAgent,
)
from argumentation_analysis.core.llm_service import create_llm_service
from argumentation_analysis.utils.taxonomy_loader import get_taxonomy_path
from modules.demo_utils import DemoLogger, confirmer_action
from argumentation_analysis.config.settings import AppSettings

AGENT_CONFIGS = {"informal": "simple", "full": "full"}

# L'initialisation de l'environnement est maintenant gérée par l'import de `environment`
# et la configuration des services LLM est centralisée dans `create_llm_service`.


def _create_kernel_and_factory() -> tuple[sk.Kernel, AgentFactory, str]:
    """Crée le kernel, le service LLM et la factory d'agents."""
    kernel = sk.Kernel()
    settings = AppSettings()
    llm_service_id = (
        settings.service_manager.default_llm_service_id or "default_service"
    )
    # Pas de model_id (#2377) : le repli « or "gpt-5.6-luna" » qui vivait ici
    # était une 5ᵉ copie du défaut, libre de diverger des quatre autres ; la
    # fabrique résout seule le modèle (#2728 a retiré le dernier site qui
    # passait le sien).
    llm_service = create_llm_service(service_id=llm_service_id, force_authentic=True)
    kernel.add_service(llm_service)

    # La factory d'agents prend le kernel et l'id du service qu'il porte (#2627)
    agent_factory = AgentFactory(kernel, llm_service_id)

    return kernel, agent_factory, llm_service_id


async def _run_analysis(
    logger: DemoLogger, agent_type: str, taxonomy_path: str, text_to_analyze: str
):
    """Crée l'agent informel demandé et exécute son analyse."""
    if agent_type not in AGENT_CONFIGS:
        raise ValueError(f"unknown demo agent type: {agent_type!r}")

    try:
        logger.info("Initialisation du Kernel et de la Factory...")
        _, agent_factory, _ = _create_kernel_and_factory()

        taxonomy_file = taxonomy_path or str(get_taxonomy_path())
        logger.info(
            f"Création de l'agent '{agent_type}' avec la taxonomie : '{taxonomy_file}'"
        )
        agent = cast(
            InformalFallacyAgent,
            agent_factory.create_informal_fallacy_agent(
                config_name=AGENT_CONFIGS[agent_type], taxonomy_file_path=taxonomy_file
            ),
        )

        logger.info("Lancement de l'analyse du texte...")
        logger.separator()
        print(f"Texte à analyser :\n---\n{text_to_analyze}\n---")
        logger.separator()

        result = await agent.analyze_text(text_to_analyze)

        logger.header("Résultat de l'analyse")
        print(result)
        logger.separator()

        return True

    except Exception as e:
        logger.error(f"Une erreur est survenue lors de l'analyse : {e}")
        import traceback

        traceback.print_exc()
        return False


def run_demo_rapide(agent_type: str, taxonomy_path: str) -> bool:
    """Démonstration rapide, non-interactive."""
    logger = DemoLogger("analyse_argumentation_rapide")
    logger.header("Démonstration Rapide : Analyse d'Arguments")

    texte_exemple = (
        "Tous les politiciens sont des menteurs. "
        "Jean est un politicien, donc il ment certainement. "
        "D'ailleurs, cette idée est supportée par le célèbre philosophe Dr. Anonyme, "
        "il faut donc lui faire confiance."
    )

    return asyncio.run(_run_analysis(logger, agent_type, taxonomy_path, texte_exemple))


def run_demo_interactive(agent_type: str, taxonomy_path: str) -> bool:
    """Démonstration interactive où l'utilisateur fournit le texte."""
    logger = DemoLogger("analyse_argumentation_interactive")
    logger.header("Démonstration Interactive : Analyse d'Arguments")

    while True:
        print("\nEntrez le texte que vous souhaitez analyser.")
        print("Laissez vide pour utiliser un exemple, ou tapez 'q' pour quitter.")

        user_input = input("> ").strip()

        if user_input.lower() == "q":
            logger.info("Sortie de la démo interactive.")
            break

        if not user_input:
            user_input = (
                "Le nouveau système d'exploitation est forcément le meilleur car c'est le plus récent. "
                "Ne pas l'adopter serait une erreur monumentale pour notre entreprise."
            )
            logger.info("Utilisation d'un texte d'exemple.")

        if confirmer_action("Lancer l'analyse sur le texte fourni ?"):
            succes = asyncio.run(
                _run_analysis(logger, agent_type, taxonomy_path, user_input)
            )
            if not succes:
                logger.error("L'analyse a échoué. Veuillez vérifier les logs.")

        if not confirmer_action("Analyser un autre texte ?"):
            break

    return True
