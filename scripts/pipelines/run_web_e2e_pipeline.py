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
# Chemin vers le répertoire scripts pour l'orchestrateur
sys.path.insert(0, str(project_root / "scripts"))


try:
    from webapp.unified_web_orchestrator import UnifiedWebOrchestrator
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

def run_pipeline():
    """
    Orchestre le démarrage des services via UnifiedWebOrchestrator,
    l'exécution des tests E2E et l'arrêt des services.
    """
    orchestrator = UnifiedWebOrchestrator()

    try:
        logger.info("Démarrage des services via UnifiedWebOrchestrator...")
        orchestrator.start()
        logger.info("Services démarrés avec succès.")

        # Exécution des tests Playwright
        logger.info("Démarrage des tests Playwright...")
        try:
            playwright_process = subprocess.run(
                PLAYWRIGHT_TEST_COMMAND,
                cwd=PLAYWRIGHT_WORKING_DIR,
                capture_output=True,
                text=True,
                check=False, # Ne pas lever d'exception si le code de retour n'est pas 0
                shell=sys.platform == "win32" # shell=True pour Windows pour les .cmd
            )
            logger.info("Sortie des tests Playwright (stdout):")
            logger.info(playwright_process.stdout)
            if playwright_process.stderr:
                logger.error("Sortie d'erreur des tests Playwright (stderr):")
                logger.error(playwright_process.stderr)
            
            if playwright_process.returncode == 0:
                logger.info("Tests Playwright terminés avec succès.")
            else:
                logger.error(f"Les tests Playwright ont échoué avec le code de retour: {playwright_process.returncode}")

        except FileNotFoundError:
            logger.error(f"Erreur: Commande Playwright non trouvée ('npx'). Assurez-vous que Node.js et npm sont installés et dans le PATH.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Erreur lors de l'exécution des tests Playwright: {e}")
            logger.error(f"Stdout: {e.stdout}")
            logger.error(f"Stderr: {e.stderr}")
        except Exception as e:
            logger.error(f"Une erreur inattendue est survenue lors de l'exécution des tests Playwright: {e}")

    except Exception as e:
        logger.error(f"Une erreur est survenue lors du démarrage des services avec UnifiedWebOrchestrator: {e}")
    finally:
        logger.info("Nettoyage: Arrêt de tous les services via UnifiedWebOrchestrator...")
        orchestrator.stop()
        logger.info("Tous les services ont été arrêtés.")

if __name__ == "__main__":
    logger.info("Démarrage du pipeline de tests E2E Web...")
    run_pipeline()
    logger.info("Pipeline de tests E2E Web terminé.")