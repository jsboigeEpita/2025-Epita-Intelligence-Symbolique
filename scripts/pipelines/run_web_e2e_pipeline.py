import project_core.core_from_scripts.auto_env
import os
import sys
import subprocess
import logging
from pathlib import Path

# Ajouter project_core au path pour l'import de ServiceManager et UnifiedWebOrchestrator
# S'assurer que le chemin est relatif à ce script ou au CWD
# Ici, on suppose que le script est dans scripts/pipelines/ et project_core est à la racine
# donc ../../
try:
    # Tentative de résolution relative au script actuel
    current_script_path = Path(__file__).resolve()
    project_root = current_script_path.parent.parent.parent
except NameError:
    # __file__ n'est pas défini (par exemple, dans un interpréteur interactif)
    # On suppose que le CWD est la racine du projet
    project_root = Path(os.getcwd())

# Ajout des chemins nécessaires pour les imports
# Chemin vers project_core pour les modules partagés
sys.path.insert(0, str(project_root))
# Le PYTHONPATH est déjà configuré par l'activateur, plus besoin de manipuler sys.path ici.


try:
    from project_core.webapp_from_scripts.unified_web_orchestrator import UnifiedWebOrchestrator
except ImportError as e:
    print(f"Erreur: Impossible d'importer UnifiedWebOrchestrator. Vérifiez PYTHONPATH et l'emplacement du module.")
    print(f"Détails de l'erreur: {e}")
    print(f"project_root calculé: {project_root}")
    print(f"sys.path: {sys.path}")
    sys.exit(1)

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("WebE2EPipeline")

# Configuration des tests Playwright
# S'assurer que le CWD pour Playwright est correct pour qu'il trouve sa config
PLAYWRIGHT_TEST_COMMAND = ["npx", "playwright", "test"]
PLAYWRIGHT_WORKING_DIR = str(project_root / "tests_playwright")

async def run_pipeline_async():
    """
    Orchestre le démarrage des services, l'exécution des tests et l'arrêt des services
    de manière asynchrone, en utilisant les vraies méthodes de l'orchestrateur.
    """
    import argparse
    default_args = argparse.Namespace(
        config='scripts/webapp/config/webapp_config.yml',
        headless=True,
        visible=False,
        log_level='INFO',
        timeout=20,
        no_trace=False,
        no_playwright=False,
        exit_after_start=False,
        start=False,
        stop=False,
        test=True, # Par défaut, on veut exécuter les tests
        integration=True,
        frontend=False,
        tests=None
    )
    
    orchestrator = UnifiedWebOrchestrator(args=default_args)

    try:
        logger.info("Lancement du test d'intégration complet via l'orchestrateur...")
        # La méthode full_integration_test gère le démarrage, les tests et l'arrêt.
        success = await orchestrator.full_integration_test(
            headless=default_args.headless,
            frontend_enabled=default_args.frontend
        )

        if success:
            logger.info("Pipeline de tests E2E terminé avec SUCCÈS.")
        else:
            logger.error("Pipeline de tests E2E terminé en ÉCHEC.")

    except Exception as e:
        logger.error(f"Une erreur majeure est survenue dans le pipeline: {e}", exc_info=True)
    finally:
        # L'arrêt est déjà géré dans full_integration_test, mais on s'assure
        # qu'un arrêt est tenté en cas de crash avant.
        logger.info("Nettoyage final du pipeline...")
        await orchestrator.shutdown()


if __name__ == "__main__":
    import asyncio
    logger.info("Démarrage du pipeline de tests E2E Web...")
    # Exécution de la nouvelle fonction asynchrone
    asyncio.run(run_pipeline_async())
    logger.info("Pipeline de tests E2E Web terminé.")