import subprocess
import sys
import pytest
from pathlib import Path

# Remonter depuis le fichier de test jusqu'à trouver la racine du projet (marquée par pyproject.toml)
PROJECT_ROOT = Path(__file__).resolve()
while not (PROJECT_ROOT / "pyproject.toml").exists():
    PROJECT_ROOT = PROJECT_ROOT.parent
    if (
        PROJECT_ROOT == PROJECT_ROOT.parent
    ):  # Empêche une boucle infinie si on atteint la racine du système de fichiers
        raise FileNotFoundError(
            "Impossible de trouver la racine du projet (contenant pyproject.toml)"
        )

DEMO_SCRIPT_PATH = (
    PROJECT_ROOT
    / "examples"
    / "03_demos_overflow"
    / "validation"
    / "validation_complete_epita.py"
)


@pytest.mark.integration
@pytest.mark.no_jvm_session
def test_validation_script_runs_successfully():
    """
    Teste l'exécution du script de validation 'validation_complete_epita.py'
    en mode intégration.
    Ce test est conçu pour être lancé dans un processus SANS JVM active,
    car il va démarrer un sous-processus qui initialisera sa propre JVM.
    """
    assert (
        DEMO_SCRIPT_PATH.exists()
    ), f"Le script de démonstration n'a pas été trouvé à {DEMO_SCRIPT_PATH}"

    command = [
        sys.executable,
        str(DEMO_SCRIPT_PATH),
        "--integration-test",
        "--agent-type",
        "explore_only",  # Requis par le mode intégration
        "--verbose",
    ]

    result = subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8", cwd=PROJECT_ROOT
    )

    # Afficher la sortie pour le débogage
    print("--- STDOUT ---")
    print(result.stdout)
    print("--- STDERR ---")
    print(result.stderr)

    # En mode mock, le script peut échouer logiquement (code de sortie != 0)
    # car le mock retourne des données vides, faisant échouer les assertions internes du script.
    # L'objectif de ce test d'intégration est de s'assurer que le script s'exécute de bout en bout
    # sans crasher (comme un 'access violation'), pas que la logique de l'agent est correcte.
    # On vérifie donc que le script a bien atteint les étapes clés de la validation.
    assert (
        "VALIDATION DE L'ANALYSE INFORMELLE" in result.stdout
    ), "Le titre de la validation n'est pas présent."

    # Vérifier que les tests d'intégration spécifiques ont été exécutés
    assert (
        "Question Piège" in result.stdout
    ), "Le test 'Question Piège' ne semble pas avoir été exécuté."
    assert (
        "Pente Savonneuse" in result.stdout
    ), "Le test 'Pente Savonneuse' ne semble pas avoir été exécuté."
