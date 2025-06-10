import os
import sys
import subprocess
import logging
import threading
from pathlib import Path

# Ajouter project_core au path pour l'import de ServiceManager
# S'assurer que le chemin est relatif à ce script ou au CWD
# Ici, on suppose que le script est dans scripts/pipelines/ et project_core est à la racine
# donc ../../project_core
try:
    # Tentative de résolution relative au script actuel
    current_script_path = Path(__file__).resolve()
    project_root = current_script_path.parent.parent.parent 
except NameError:
    # __file__ n'est pas défini (par exemple, dans un interpréteur interactif)
    # On suppose que le CWD est la racine du projet
    project_root = Path(os.getcwd())

sys.path.insert(0, str(project_root / "project_core"))

try:
    from service_manager import InfrastructureServiceManager, ServiceConfig
except ImportError as e:
    print(f"Erreur: Impossible d'importer InfrastructureServiceManager. Vérifiez PYTHONPATH et l'emplacement du module.")
    print(f"Détails de l'erreur: {e}")
    print(f"project_root calculé: {project_root}")
    print(f"sys.path: {sys.path}")
    sys.exit(1)

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("WebE2EPipeline")

# Configuration des services
BACKEND_COMMAND = ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "5000"]
BACKEND_WORKING_DIR = str(project_root) # Racine du projet
BACKEND_HEALTH_CHECK_URL = "http://localhost:5000/docs" # ou /health si implémenté

FRONTEND_COMMAND = ["npm", "start"]
FRONTEND_WORKING_DIR = str(project_root / "services" / "web_api" / "interface-web-argumentative")
FRONTEND_HEALTH_CHECK_URL = "http://localhost:3000"

# Configuration des tests Playwright
# S'assurer que le CWD pour Playwright est correct pour qu'il trouve sa config
PLAYWRIGHT_TEST_COMMAND = ["npx", "playwright", "test"] 
PLAYWRIGHT_WORKING_DIR = str(project_root / "tests_playwright")

def run_pipeline():
    """
    Orchestre le démarrage des services, l'exécution des tests E2E et l'arrêt des services.
    """
    manager = InfrastructureServiceManager()

    backend_config = ServiceConfig(
        name="backend-api",
        command=BACKEND_COMMAND,
        working_dir=BACKEND_WORKING_DIR,
        port=5000,
        health_check_url=BACKEND_HEALTH_CHECK_URL,
        startup_timeout=60 # Augmenter si l'API prend du temps à démarrer
    )

    frontend_config = ServiceConfig(
        name="frontend-react",
        command=FRONTEND_COMMAND,
        working_dir=FRONTEND_WORKING_DIR,
        port=3000,
        health_check_url=FRONTEND_HEALTH_CHECK_URL,
        startup_timeout=120 # React peut être long à compiler au premier démarrage
    )

    manager.register_service(backend_config)
    manager.register_service(frontend_config)

    services_started_successfully = False
    try:
        logger.info("Démarrage des services en parallèle...")
        
        service_threads = []
        results = {} # Pour stocker les résultats de démarrage des threads

        def start_service_thread(service_name, results_dict):
            logger.info(f"Tentative de démarrage du service: {service_name}")
            success, port = manager.start_service_with_failover(service_name)
            results_dict[service_name] = success
            if success:
                logger.info(f"Service {service_name} démarré avec succès sur le port {port}.")
            else:
                logger.error(f"Échec du démarrage du service: {service_name}")

        for service_name in [backend_config.name, frontend_config.name]:
            thread = threading.Thread(target=start_service_thread, args=(service_name, results))
            service_threads.append(thread)
            thread.start()

        for thread in service_threads:
            thread.join() # Attendre la fin de chaque thread de démarrage

        if all(results.values()):
            logger.info("Tous les services ont démarré avec succès.")
            services_started_successfully = True
        else:
            failed_services = [name for name, status in results.items() if not status]
            logger.error(f"Échec du démarrage des services suivants: {', '.join(failed_services)}")
            logger.error("Le pipeline ne peut pas continuer sans tous les services.")
            return # Arrêter ici si les services n'ont pas démarré

        # Exécution des tests Playwright
        if services_started_successfully:
            logger.info("Démarrage des tests Playwright...")
            try:
                # Utilisation de shell=True avec prudence, ou s'assurer que la commande est bien formée
                # Pour npx, il est généralement préférable de ne pas utiliser shell=True sur Windows si possible
                # et de s'assurer que npx est dans le PATH ou utiliser le chemin complet.
                # Sur Windows, npm et npx sont souvent des .cmd, donc shell=True peut être nécessaire
                # ou utiliser `cmd /c npx playwright test`
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

    finally:
        logger.info("Nettoyage: Arrêt de tous les services...")
        manager.stop_all_services()
        logger.info("Tous les services ont été arrêtés.")

if __name__ == "__main__":
    logger.info("Démarrage du pipeline de tests E2E Web...")
    run_pipeline()
    logger.info("Pipeline de tests E2E Web terminé.")