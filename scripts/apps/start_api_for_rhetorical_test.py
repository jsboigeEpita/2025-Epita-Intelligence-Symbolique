import os
import sys
import logging
from pathlib import Path
import time
import asyncio # Ajout pour l'asynchronisme

# Assurer l'accès aux modules du projet
try:
    current_script_path = Path(__file__).resolve()
    project_root = current_script_path.parent.parent.parent
except NameError:
    project_root = Path(os.getcwd())

sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "scripts")) # Pour unified_web_orchestrator

try:
    from webapp.unified_web_orchestrator import UnifiedWebOrchestrator
except ImportError as e:
    print(f"Erreur: Impossible d'importer UnifiedWebOrchestrator.")
    print(f"Détails: {e}")
    print(f"project_root: {project_root}")
    print(f"sys.path: {sys.path}")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("StartApiForRhetoricalTest")

async def main(): # Rendre main asynchrone
    logger.info("Initialisation de UnifiedWebOrchestrator pour démarrer l'API...")
    orchestrator = UnifiedWebOrchestrator()

    try:
        logger.info("Démarrage des services (API backend uniquement via start_webapp)...")
        # Appeler start_webapp avec frontend_enabled=False et await
        success = await orchestrator.start_webapp(frontend_enabled=False)
        
        if success:
            logger.info("L'API backend devrait être démarrée (via start_webapp).")
            logger.info("Le script va maintenant attendre. Appuyez sur Ctrl+C pour arrêter l'orchestrateur et quitter.")
            # Boucle pour maintenir le script actif jusqu'à une interruption manuelle
            while True:
                await asyncio.sleep(60) # Utiliser asyncio.sleep dans un contexte asynchrone
        else:
            logger.error("Échec du démarrage de l'orchestrateur via start_webapp.")

    except KeyboardInterrupt:
        logger.info("Interruption clavier détectée. Arrêt de l'orchestrateur...")
    except Exception as e:
        logger.error(f"Erreur lors du démarrage ou de l'exécution de l'orchestrateur: {e}", exc_info=True)
    finally:
        logger.info("Arrêt de l'orchestrateur...")
        await orchestrator.stop_webapp() # Utiliser await pour la méthode asynchrone stop_webapp
        logger.info("Orchestrateur arrêté.")

if __name__ == "__main__":
    asyncio.run(main()) # Exécuter la fonction main asynchrone