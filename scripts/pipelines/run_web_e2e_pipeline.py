import os
import sys
from pathlib import Path

# --- Configuration du PYTHONPATH ---
# Cette section doit être la première pour que les imports du projet fonctionnent.
try:
    # Résoudre le chemin racine du projet par rapport à l'emplacement de ce script.
    current_script_path = Path(__file__).resolve()
    project_root = current_script_path.parent.parent.parent
except NameError:
    # Fallback si __file__ n'est pas défini (ex: REPL), en supposant que CWD est la racine.
    project_root = Path(os.getcwd())

# Insérer la racine du projet au début de sys.path pour prioriser les modules locaux.
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Maintenant que le path est configuré, on peut importer les modules du projet.
import project_core.core_from_scripts.auto_env
import subprocess
import logging


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


def run_pytest_tests():
    """
    Exécute les tests E2E avec pytest, en redirigeant stdout et stderr vers des fichiers de log.
    Toute la gestion des services est désormais déléguée aux fixtures pytest.
    """
    test_dir = str(project_root / "tests" / "e2e")
    
    command = [
        "pytest",
        test_dir,
        "--verbose",
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


if __name__ == "__main__":
    logger.info("Démarrage du pipeline de tests E2E Web...")
    success = run_pytest_tests()
    
    if success:
        logger.info("Pipeline de tests E2E Web terminé avec SUCCÈS.")
        sys.exit(0)
    else:
        logger.error("Pipeline de tests E2E Web terminé en ÉCHEC.")
        sys.exit(1)