import asyncio
import logging
import json
from config.unified_config import PresetConfigs
from argumentation_analysis.orchestration.cluedo_extended_orchestrator import CluedoExtendedOrchestrator

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

async def run_test():
    """
    Exécute un test de bout en bout du CluedoExtendedOrchestrator avec la nouvelle architecture de tool-calling.
    """
    logger.info("🚀 Démarrage du test d'orchestration Cluedo avec Tool Calling...")

    try:
        # 1. Obtenir la configuration authentique par défaut
        config = PresetConfigs.authentic_fol()
        logger.info(f"Configuration chargée: {config.to_dict()}")

        # 2. Créer un kernel authentique avec le service LLM
        logger.info("Création du kernel Semantic Kernel avec le service GPT-4o-mini...")
        kernel = config.get_kernel_with_gpt4o_mini()
        logger.info("✅ Kernel créé avec succès.")

        # 3. Instancier l'orchestrateur
        orchestrator = CluedoExtendedOrchestrator(
            kernel=kernel,
            max_turns=10,  # Limiter le nombre de tours pour le test
            service_id="gpt-4o-mini-authentic" # Utiliser le service ID correct
        )
        logger.info("✅ Orchestrateur instancié.")

        # 4. Configurer le workflow
        logger.info("Configuration du workflow Cluedo (agents, state, plugins)...")
        await orchestrator.setup_workflow()
        logger.info("✅ Workflow configuré.")

        # 5. Exécuter le workflow
        initial_question = "L'enquête sur le meurtre du Manoir Tudor commence. Sherlock, à vous l'honneur."
        logger.info(f"▶️  Exécution du workflow avec la question initiale : '{initial_question}'")
        results = await orchestrator.execute_workflow(initial_question)
        logger.info("✅ Workflow terminé.")

        # 6. Afficher les résultats
        logger.info("\n" + "="*50 + " RÉSULTATS FINALS " + "="*50)
        print(json.dumps(results, indent=2, ensure_ascii=False))
        logger.info("="*120 + "\n")

        # Validation simple
        if results and results.get("final_state", {}).get("solution_trouvee"):
            logger.info("✅ SUCCÈS : La solution a été trouvée !")
        else:
            logger.warning("⚠️ AVERTISSEMENT : La solution n'a pas été trouvée dans les tours impartis.")

    except Exception as e:
        logger.error(f"❌ ERREUR FATALE durant le test d'orchestration : {e}", exc_info=True)

if __name__ == "__main__":
    # Assurez-vous que les variables d'environnement (comme OPENAI_API_KEY) sont chargées.
    # Par exemple, via un fichier .env et `dotenv.load_dotenv()` si nécessaire.
    # Dans ce projet, cela semble géré automatiquement.
    asyncio.run(run_test())