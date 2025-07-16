# -*- coding: utf-8 -*-
"""
Module de démonstration : Analyse d'Arguments & Sophismes
Ce module utilise la AgentFactory pour instancier dynamiquement un agent
d'analyse en fonction des paramètres fournis.
"""
import asyncio
import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import OpenAITextCompletion
from argumentation_analysis.agents.agent_factory import AgentFactory
from argumentation_analysis.core.llm_service import create_llm_service
from modules.demo_utils import DemoLogger, pause_interactive, confirmer_action
from argumentation_analysis.config.settings import AppSettings

# L'initialisation de l'environnement est maintenant gérée par l'import de `environment`
# et la configuration des services LLM est centralisée dans `create_llm_service`.

def _create_kernel_and_factory() -> tuple[sk.Kernel, AgentFactory, str]:
    """Crée le kernel, le service LLM et la factory d'agents."""
    kernel = sk.Kernel()
    settings = AppSettings()
    llm_service_id = settings.service_manager.default_llm_service_id or "default_service"
    model_id = settings.service_manager.default_model_id or "gpt-4o-mini" # Fallback
    
    # Utilise la factory centralisée pour créer le service LLM
    llm_service = create_llm_service(service_id=llm_service_id, model_id=model_id, force_authentic=True)
    kernel.add_service(llm_service)
    
    # La factory d'agents a maintenant besoin du kernel et des settings
    agent_factory = AgentFactory(kernel, settings)
    
    return kernel, agent_factory, llm_service_id

async def _run_analysis(logger: DemoLogger, agent_type: str, taxonomy_path: str, text_to_analyze: str):
    """
    Logique centrale pour exécuter l'analyse d'argumentation.
    Initialise le kernel, la factory, crée l'agent et lance l'analyse.
    """
    try:
        logger.info(f"Initialisation du Kernel et de la Factory...")
        kernel, agent_factory, _ = _create_kernel_and_factory()
        
        logger.info(f"Création de l'agent via la factory avec le type : '{agent_type}'")
        agent = agent_factory.create_agent(agent_type)

        logger.info(f"Configuration de l'agent avec la taxonomie : '{taxonomy_path}'")
        await agent.configure(taxonomy_path=taxonomy_path)

        logger.info("Lancement de l'analyse du texte...")
        logger.separator()
        print(f"Texte à analyser :\n---\n{text_to_analyze}\n---")
        logger.separator()
        
        result = await agent.analyze(text_to_analyze)
        
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

        if user_input.lower() == 'q':
            logger.info("Sortie de la démo interactive.")
            break

        if not user_input:
            user_input = (
                "Le nouveau système d'exploitation est forcément le meilleur car c'est le plus récent. "
                "Ne pas l'adopter serait une erreur monumentale pour notre entreprise."
            )
            logger.info("Utilisation d'un texte d'exemple.")

        if confirmer_action("Lancer l'analyse sur le texte fourni ?"):
            succes = asyncio.run(_run_analysis(logger, agent_type, taxonomy_path, user_input))
            if not succes:
                logger.error("L'analyse a échoué. Veuillez vérifier les logs.")
        
        if not confirmer_action("Analyser un autre texte ?"):
            break
            
    return True