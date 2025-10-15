# -*- coding: utf-8 -*-

"""
Tests d'intégration pour le script principal main_orchestrator.py.
"""

import os
import subprocess
import json
import pytest
from pathlib import Path

# Définir le chemin racine du projet pour faciliter l'accès aux fichiers
# Le chemin racine est le parent du répertoire 'argumentation_analysis'
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
MAIN_ORCHESTRATOR_PATH = (
    PROJECT_ROOT / "argumentation_analysis" / "main_orchestrator.py"
)


@pytest.fixture(scope="module")
def sample_text_file():
    """
    Fixture qui crée un fichier texte temporaire pour les tests
    et le supprime après l'exécution des tests du module.
    """
    content = "Le changement climatique est une réalité indéniable. Les activités humaines, notamment la combustion des énergies fossiles, en sont la principale cause."
    test_file_path = Path("test_input.txt")

    # S'assurer que le fichier est bien dans le répertoire du projet pour que le script le trouve
    file_path_in_project = PROJECT_ROOT / test_file_path

    # Créer le répertoire 'argumentation_analysis' s'il n'existe pas
    # ce qui ne devrait pas arriver dans un contexte de test normal.
    (PROJECT_ROOT / "argumentation_analysis").mkdir(exist_ok=True)

    with open(file_path_in_project, "w", encoding="utf-8") as f:
        f.write(content)

    yield file_path_in_project

    os.remove(file_path_in_project)


def run_orchestrator_process(text_file_path, orchestrator_key=None):
    """
    Exécute le script main_orchestrator.py dans un sous-processus.

    Args:
        text_file_path (Path): Le chemin vers le fichier texte à analyser.
        orchestrator_key (str, optional): La clé de l'orchestrateur spécialisé.

    Returns:
        tuple: (stdout, stderr, return_code)
    """
    # Construire la commande complète avec le wrapper PowerShell
    wrapper_path = PROJECT_ROOT / "activate_project_env.ps1"
    # La commande à exécuter par le script PS doit être une seule chaîne
    command_to_run = (
        f'python "{MAIN_ORCHESTRATOR_PATH}" --skip-ui --text-file "{text_file_path}"'
    )

    command = [
        "powershell",
        "-File",
        str(wrapper_path),
        "-CommandToRun",
        command_to_run,
    ]

    # Exécuter depuis la racine du projet
    process = subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8", cwd=str(PROJECT_ROOT)
    )

    return process.stdout, process.stderr, process.returncode


def test_hierarchical_orchestration(sample_text_file):
    """
    Teste le flux d'orchestration par défaut (hiérarchique).

    Ce test vérifie que le script s'exécute jusqu'au bout et produit
    une sortie JSON structurée contenant les clés attendues.
    """
    stdout, stderr, return_code = run_orchestrator_process(sample_text_file)

    # Débogage : afficher les sorties uniquement en cas d'échec
    if return_code != 0:
        print("--- STDOUT CAPTURE ---")
        print(stdout)
        print("--- STDERR CAPTURE ---")
        print(stderr)
        print("--- FIN CAPTURE ---")

    assert return_code == 0, "Le script doit se terminer sans erreur."

    assert stdout, "La sortie standard ne doit pas être vide."

    # Logique de parsing JSON multi-lignes améliorée pour trouver le premier bloc complet
    json_output = None
    lines = stdout.splitlines()
    start_index = -1
    for i, line in enumerate(lines):
        if line.strip().startswith("{"):
            start_index = i
            break

    if start_index != -1:
        json_str_builder = ""
        # On recommence à construire et à parser depuis le début du bloc potentiel
        for line in lines[start_index:]:
            json_str_builder += line
            try:
                # On tente de parser à chaque ajout de ligne
                json_output = json.loads(json_str_builder)
                # Si c'est un succès, on a trouvé notre bloc JSON complet.
                break
            except json.JSONDecodeError:
                # Si ça échoue, c'est que le JSON n'est pas encore complet, on continue.
                continue

    assert (
        json_output is not None
    ), "Aucun bloc JSON valide et complet n'a été trouvé dans stdout."

    # Vérifier la structure de base du JSON
    assert "status" in json_output
    assert json_output["status"] == "success"
    assert "analysis" in json_output
    assert "history" in json_output

    # Vérifier quelques clés dans la partie "analysis"
    analysis_data = json_output.get("analysis", {})
    assert "raw_text" in analysis_data
    assert "analysis_tasks" in analysis_data
    # La présence d'autres clés comme 'history' est déjà validée plus haut.


# NOTE : Le test pour l'orchestrateur spécialisé via "--orchestrator-key"
# n'est pas implémenté car l'argument n'est pas géré par le `main_orchestrator.py`
# tel qu'il est actuellement. Cette fonctionnalité semble être gérée par un autre
# point d'entrée ou une version différente du projet.
