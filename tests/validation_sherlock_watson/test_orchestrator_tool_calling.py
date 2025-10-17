import sys
import os
import importlib

print("--- DIAGNOSTIC DE L'ENVIRONNEMENT ---")
print(f"Version de Python: {sys.version}")
print("sys.path:")
for path in sys.path:
    print(f"  - {path}")

try:
    import semantic_kernel

    spec = importlib.util.find_spec("semantic_kernel")
    if spec and spec.origin:
        print(f"\n'semantic_kernel' est chargé depuis: {spec.origin}")
        sk_version = getattr(semantic_kernel, "__version__", "Version non trouvée")
        print(f"Version de semantic_kernel: {sk_version}")
    else:
        print(
            "\n'semantic_kernel' a été trouvé, mais son chemin d'origine (spec.origin) est introuvable."
        )
except ImportError:
    print("\nERREUR: 'semantic_kernel' ne peut pas être importé.")
except Exception as e:
    print(
        f"\nUne erreur inattendue est survenue lors de l'inspection de semantic_kernel: {e}"
    )

print("--- FIN DU DIAGNOSTIC ---\n")
import asyncio
import logging
import json
from config.unified_config import PresetConfigs
from argumentation_analysis.orchestration.cluedo_extended_orchestrator import (
    CluedoExtendedOrchestrator,
)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_test():
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
            service_id="gpt-5-mini-authentic",  # Utiliser le service ID correct
        )
        logger.info("✅ Orchestrateur instancié.")

        # 4. Configurer le workflow
        logger.info("Configuration du workflow Cluedo (agents, state, plugins)...")
        asyncio.run(orchestrator.setup_workflow())
        logger.info("✅ Workflow configuré.")

        # 5. Exécuter le workflow
        initial_question = "L'enquête sur le meurtre du Manoir Tudor commence. Sherlock, à vous l'honneur."
        logger.info(
            f"▶️  Exécution du workflow avec la question initiale : '{initial_question}'"
        )
        results = asyncio.run(orchestrator.execute_workflow(initial_question))
        logger.info("✅ Workflow terminé.")

        # 6. Afficher les résultats
        logger.info("\n" + "=" * 50 + " RÉSULTATS FINALS " + "=" * 50)
        print(json.dumps(results, indent=2, ensure_ascii=False))
        logger.info("=" * 120 + "\n")

        # Validation simple
        if results and results.get("final_state", {}).get("solution_trouvee"):
            logger.info("✅ SUCCÈS : La solution a été trouvée !")
        else:
            logger.warning(
                "⚠️ AVERTISSEMENT : La solution n'a pas été trouvée dans les tours impartis."
            )

    except Exception as e:
        logger.error(
            f"❌ ERREUR FATALE durant le test d'orchestration : {e}", exc_info=True
        )


if __name__ == "__main__":
    # Assurez-vous que les variables d'environnement (comme OPENAI_API_KEY) sont chargées.
    # Par exemple, via un fichier .env et `dotenv.load_dotenv()` si nécessaire.
    # Dans ce projet, cela semble géré automatiquement.
    run_test()
