import project_core.core_from_scripts.auto_env
import asyncio
import logging
import json
import sys
import os

# Ajoute le répertoire racine du projet au PYTHONPATH
# pour permettre les imports de modules comme 'argumentation_analysis'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from argumentation_analysis.pipelines.unified_orchestration_pipeline import UnifiedOrchestrationPipeline, create_extended_config_from_params

async def main():
    """
    Script de validation pour tester le chemin d'exécution via le nouveau MainOrchestrator.
    """
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    logger.info("--- Début du test du nouveau chemin d'orchestration ---")

    # Étape 1 : Créer une configuration activant le nouveau moteur
    logger.info("Configuration du pipeline pour utiliser 'use_new_orchestrator=True'")
    config = create_extended_config_from_params(use_new_orchestrator=True)

    # Étape 2 : Instancier le pipeline de façade
    pipeline = UnifiedOrchestrationPipeline(config=config)

    # Étape 3 : Définir les données d'entrée
    text_input = "Le réchauffement climatique est une réalité indéniable, principalement causée par les activités humaines. Les preuves scientifiques s'accumulent et les conséquences sont déjà visibles."
    
    # Configuration neutre pour tester le chemin d'orchestration par défaut.
    # Pour des scénarios de test spécifiques (ex: forcer une stratégie, simuler une source),
    # veuillez utiliser des scripts de validation dédiés ou modifier ce bloc temporairement.
    custom_config = None
    source_info = None

    # Étape 4 : Exécuter l'analyse
    try:
        await pipeline.initialize()
        result = await pipeline.analyze_text_orchestrated(
            text=text_input,
            source_info=source_info,
            custom_config=custom_config  # Passe None
        )

        # Étape 5 : Afficher le résultat
        logger.info("--- Résultat de l'analyse ---")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        logger.info("--- Fin du test ---")

        if result.get("status") == "success" and "new MainOrchestrator" in result.get("message", ""):
             logger.info("VALIDATION RÉUSSIE : Le nouveau chemin a été emprunté et a terminé avec succès.")
        else:
             logger.warning("VALIDATION PARTIELLE/ÉCHOUÉE : Vérifiez les logs et le résultat ci-dessus.")

    except Exception as e:
        logger.error(f"Une erreur est survenue durant l'exécution du pipeline: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())