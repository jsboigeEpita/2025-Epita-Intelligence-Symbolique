import pytest
import subprocess
import os
import sys
import glob
import json
import shutil
from unittest.mock import patch, AsyncMock, MagicMock

# Assurer que la racine du projet est dans le path pour les imports
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

SCRIPT_PATH = os.path.join(
    PROJECT_ROOT, "scripts", "sherlock_watson", "run_unified_investigation.py"
)
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results", "unified_investigation")
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs", "unified_investigation")


@pytest.fixture(scope="module")
def setup_test_environment():
    """Crée les répertoires de résultats et de logs s'ils n'existent pas."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)

    yield

    # Nettoyage après les tests du module
    # Commentez les lignes suivantes si vous souhaitez inspecter les résultats
    # for d in glob.glob(os.path.join(RESULTS_DIR, "*")):
    #     shutil.rmtree(d)
    # for f in glob.glob(os.path.join(LOGS_DIR, "*.log")):
    #     os.remove(f)


@pytest.mark.skip(
    reason="Le script run_unified_investigation.py a été supprimé lors du refactoring. Ce test doit être réécrit."
)
def test_cluedo_workflow_integration(setup_test_environment):
    """
    Test d'intégration réel pour le workflow 'cluedo'.
    Ce test vérifie que le script peut s'exécuter de bout en bout
    en utilisant les vrais services. Il nécessite une configuration d'environnement
    valide, y compris les clés API si elles ne sont pas déjà configurées.
    """
    # --- Exécution du script ---
    command = [sys.executable, SCRIPT_PATH, "--workflow", "cluedo", "--no-java"]

    # Le script utilisera les variables d'environnement existantes.
    # Assurez-vous que OPENAI_API_KEY est définie. Vous pouvez utiliser
    # un fichier .env à la racine du projet pour cela.
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        env=os.environ,
    )

    # --- Vérifications ---
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)

    # 1. Vérifier que le script s'est terminé sans erreur
    assert (
        result.returncode == 0
    ), f"Le script a échoué avec le code {result.returncode}\nSTDERR: {result.stderr}"

    # 2. Vérifier qu'un fichier de résultat a été créé
    session_dirs = sorted(
        [
            d
            for d in os.listdir(RESULTS_DIR)
            if os.path.isdir(os.path.join(RESULTS_DIR, d))
        ]
    )
    assert len(session_dirs) > 0, "Aucun répertoire de session n'a été créé."

    latest_session_dir = os.path.join(RESULTS_DIR, session_dirs[-1])

    result_files = glob.glob(os.path.join(latest_session_dir, "result_cluedo_*.json"))

    assert (
        len(result_files) == 1
    ), f"Un seul fichier de résultat JSON était attendu, mais {len(result_files)} ont été trouvés."

    result_file_path = result_files[0]
    assert os.path.exists(
        result_file_path
    ), "Le fichier de trace JSON n'a pas été créé."

    # 3. Vérifier le contenu de base du fichier de résultat
    with open(result_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["session_metadata"]["workflow"] == "cluedo"
        assert data["execution_result"]["status"] == "completed"
        assert "result_summary" in data["execution_result"]
        # On vérifie la structure de la solution correcte
        result_summary = data["execution_result"]["result_summary"]
        assert "correct_solution" in result_summary
        correct_solution = result_summary["correct_solution"]
        assert "suspect" in correct_solution
        assert "arme" in correct_solution
        assert "lieu" in correct_solution
