import os
import sys
from pathlib import Path

# --- Configuration du PYTHONPATH ---
# Cette section doit être la première pour que les imports du projet fonctionnent.
try:
    # Résoudre le chemin racine du projet par rapport à l'emplacement de ce script.
    current_script_path = Path(__file__).resolve()
    project_root = current_script_path.parent.parent.parent.parent
except NameError:
    # Fallback si __file__ n'est pas défini (ex: REPL), en supposant que CWD est la racine.
    project_root = Path(os.getcwd())

# Insérer la racine du projet au début de sys.path pour prioriser les modules locaux.
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Maintenant que le path est configuré, on peut importer les modules du projet.
from argumentation_analysis.core.bootstrap import initialize_project_environment
import subprocess
import logging
from dotenv import load_dotenv
import asyncio

# Maintenant que le path est configuré, on peut importer les modules du projet.
from argumentation_analysis.core.bootstrap import initialize_project_environment
from types import SimpleNamespace
from argumentation_analysis.webapp.orchestrator import UnifiedWebOrchestrator # Utiliser l'orchestrateur centralisé


# Configuration du logging
log_dir = project_root / "logs"
log_dir.mkdir(exist_ok=True)
main_log_file = log_dir / "pipeline_e2e.log"
pytest_stdout_log = log_dir / "pytest_stdout.log"
pytest_stderr_log = log_dir / "pytest_stderr.log"

# Nettoyage des anciens logs
for log_file in [main_log_file, pytest_stdout_log, pytest_stderr_log]:
    if log_file.exists():
        log_file.unlink()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(main_log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("WebE2EPipeline")


def build_frontend():
    """
    Construit l'application frontend React.
    Cette fonction s'assure que les dépendances Node.js sont installées et
    que le build de production est généré.
    """
    frontend_dir = project_root / "services" / "web_api" / "interface-web-argumentative"
    logger.info(f"Début du build du frontend dans : {frontend_dir}")

    if not frontend_dir.exists():
        logger.error(f"Le répertoire du frontend n'a pas été trouvé à l'emplacement attendu.")
        return False

    try:
        # Étape 1: Installer les dépendances npm
        logger.info("Exécution de 'npm install'...")
        install_process = subprocess.run(
            ["npm", "install"],
            cwd=str(frontend_dir),
            capture_output=True,
            text=True,
            shell=True  # Requis pour trouver npm sous Windows
        )
        if install_process.returncode != 0:
            logger.error("Échec de 'npm install'.")
            logger.error(install_process.stderr)
            return False
        logger.info("'npm install' terminé avec succès.")

        # Étape 2: Construire l'application React
        logger.info("Exécution de 'npm run build'...")
        build_process = subprocess.run(
            ["npm", "run", "build"],
            cwd=str(frontend_dir),
            capture_output=True,
            text=True,
            shell=True
        )
        if build_process.returncode != 0:
            logger.error("Échec de 'npm run build'.")
            logger.error(build_process.stderr)
            return False
        logger.info("'npm run build' terminé avec succès.")
        
        # Vérifier si le répertoire de build a été créé
        build_dir = frontend_dir / "build"
        if not build_dir.exists():
            logger.error("Le répertoire 'build' n'a pas été créé après le build.")
            return False

        logger.info("Build du frontend terminé avec succès.")
        return True

    except FileNotFoundError:
        logger.error("La commande 'npm' est introuvable. Assurez-vous que Node.js est installé et dans le PATH.")
        return False
    except Exception as e:
        logger.error(f"Une erreur inattendue est survenue lors du build du frontend: {e}", exc_info=True)
        return False


def run_pytest_tests():
    """
    Exécute les tests E2E avec pytest, en redirigeant stdout et stderr vers des fichiers de log.
    Toute la gestion des services est désormais déléguée aux fixtures pytest.
    """
    test_dir = str(project_root / "tests" / "e2e")
    
    command = [
        sys.executable,
        "-m",
        "pytest",
        test_dir,
        "--verbose",
        "--asyncio-mode=strict",  # Forcer le mode strict pour éviter les conflits de boucle d'événements
        "--headed"  # Lancer avec un navigateur visible pour le débogage
    ]

    logger.info(f"Lancement de la commande pytest : {' '.join(command)}")
    logger.info(f"La sortie standard sera redirigée vers : {pytest_stdout_log}")
    logger.info(f"La sortie d'erreur sera redirigée vers : {pytest_stderr_log}")

    try:
        with open(pytest_stdout_log, 'w') as f_stdout, open(pytest_stderr_log, 'w') as f_stderr:
            process = subprocess.run(
                command,
                cwd=str(project_root),
                stdout=f_stdout,
                stderr=f_stderr,
                text=True,
                encoding='utf-8'
            )
        
        if process.returncode == 0:
            logger.info("Pytest a terminé avec SUCCÈS.")
            return True
        else:
            logger.error(f"Pytest a terminé en ÉCHEC avec le code de retour {process.returncode}.")
            logger.error(f"Consultez les logs pour plus de détails:")
            logger.error(f"  - Sortie standard: {pytest_stdout_log}")
            logger.error(f"  - Sortie d'erreur: {pytest_stderr_log}")
            return False

    except FileNotFoundError:
        logger.error("Erreur: La commande 'pytest' n'a pas été trouvée.")
        logger.error("Assurez-vous que pytest est installé et que l'environnement virtuel est activé.")
        return False
    except Exception as e:
        logger.error(f"Une erreur est survenue lors de l'exécution de pytest : {e}", exc_info=True)
        return False
        
async def main_async():
    """Point d'entrée asynchrone pour gérer le cycle de vie des services."""
    logger.info("Démarrage du pipeline de tests E2E Web...")

    # Charger les variables d'environnement pour les ports
    dotenv_path = project_root / '.env'
    load_dotenv(dotenv_path=dotenv_path)
    backend_port = int(os.environ.get("BACKEND_PORT", 8095))
    frontend_port = int(os.environ.get("FRONTEND_PORT", 8085))

    # Configuration de l'orchestrateur centralisé
    config_path = project_root / 'scripts' / 'webapp' / 'config' / 'webapp_config.yml'
    # Créer un objet de configuration simulant argparse.Namespace pour l'orchestrateur
    # pour instancier UnifiedWebOrchestrator en dehors de son contexte CLI.
    orchestrator_args = SimpleNamespace(
        config=str(config_path),
        log_level='INFO',
        headless=True,
        visible=False,
        timeout=15, # Timeout de 15 minutes pour le pipeline complet
        no_trace=False,
        frontend=True, # Forcer le démarrage du frontend pour les tests E2E
        tests=None,
        no_playwright=False,
        exit_after_start=False,
        start=False,
        stop=False,
        test=False,
        integration=True
    )
    orchestrator = UnifiedWebOrchestrator(orchestrator_args)
    orchestrator.headless = True # Toujours en headless pour les tests CI/CD

    pipeline_status = 1  # 1 pour échec par défaut

    try:
        # --- Étape 1: Construire le frontend ---
        logger.info("Étape 1: Démarrage du build de l'application frontend React...")
        if not build_frontend():
            logger.error("Le build du frontend a échoué. Arrêt du pipeline.")
            return 1 # Échec

        # --- Étape 2: Initialisation de l'environnement Python ---
        logger.info("Étape 2: Initialisation de l'environnement du projet...")
        if not initialize_project_environment():
            logger.error("Échec de l'initialisation de l'environnement. Arrêt.")
            return 1

        # --- Étape 3: Démarrer les services web ---
        logger.info(f"Étape 3: Démarrage des services (Backend: {backend_port}, Frontend: {frontend_port})...")
        services_started = await orchestrator.start_webapp(
            headless=orchestrator.headless,
            frontend_enabled=True
        )
        if not services_started:
            logger.error("Échec du démarrage des services web via UnifiedWebOrchestrator. Arrêt.")
            return 1
        
        logger.info("Services web démarrés avec succès.")
        
        # --- Étape 4: Lancement des tests ---
        logger.info("Étape 4: Lancement des tests pytest...")
        tests_passed = run_pytest_tests()
        
        if tests_passed:
            logger.info("Pipeline de tests E2E Web terminé avec SUCCÈS.")
            pipeline_status = 0 # Succès
        else:
            logger.error("Pipeline de tests E2E Web terminé en ÉCHEC.")
            pipeline_status = 1 # Échec

    except Exception as e:
        logger.error(f"Une erreur critique est survenue dans le pipeline : {e}", exc_info=True)
    finally:
        logger.info("Arrêt des services web...")
        await orchestrator.stop_webapp()
        logger.info("Services web arrêtés.")
    
    return pipeline_status


if __name__ == "__main__":
    exit_code = asyncio.run(main_async())
    sys.exit(exit_code)