import os
import sys
from pathlib import Path
import pytest

from project_core.utils.shell import run_sync, ShellCommandError

# Test pour vérifier que le chemin du projet est correctement ajouté à PYTHONPATH
def test_run_command_with_custom_pythonpath():
    """
    Vérifie que l'exécution d'une commande avec un PYTHONPATH personnalisé fonctionne
    et permet de trouver des modules du projet.
    """
    # Calculer la racine du projet pour l'ajouter au PYTHONPATH
    project_root = Path(__file__).resolve().parents[4]
    
    # Préparer l'environnement
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    
    # Construire le nouveau PYTHONPATH
    new_pythonpath = str(project_root)
    if existing_pythonpath:
        new_pythonpath = f"{new_pythonpath}{os.pathsep}{existing_pythonpath}"
    
    env["PYTHONPATH"] = new_pythonpath

    # Commande à exécuter, qui devrait échouer sans le bon PYTHONPATH
    # Il s'agit d'un exemple, le module doit exister
    command = [sys.executable, "-m", "argumentation_analysis.core.llm_service"]

    # Exécuter la commande avec l'environnement personnalisé
    try:
        result = run_sync(command, env=env, check_errors=True)
        # S'assurer que la commande a réussi
        assert result.returncode == 0
    except ShellCommandError as e:
        pytest.fail(f"La commande a échoué avec le PYTHONPATH personnalisé: {e}\n"
                    f"PYTHONPATH: {env.get('PYTHONPATH')}\n"
                    f"STDOUT: {e.stdout}\n"
                    f"STDERR: {e.stderr}")
    except FileNotFoundError:
        pytest.fail("Le module `argumentation_analysis.core.llm_service` est introuvable. "
                    "Vérifiez que le chemin et le module sont corrects.")
