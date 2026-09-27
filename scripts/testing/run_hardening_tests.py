import sys
import subprocess
from pathlib import Path


def main():
    """
    Script de test autonome pour les scénarios de durcissement.

    Lance le test hermétique ``tests/integration/logical_agents/`` avec
    l'interpréteur courant. La racine du dépôt est deux niveaux au-dessus de
    ``scripts/testing/`` : ce script la prenait pour son propre dossier, et le
    chemin qu'il passait à pytest n'existait pas (#2703).
    """
    project_root = Path(__file__).resolve().parents[2]

    test_file = (
        project_root
        / "tests"
        / "integration"
        / "logical_agents"
        / "test_logic_puzzles_hardening.py"
    )

    command = [sys.executable, "-m", "pytest", "-s", "-vv", str(test_file)]

    print(f"Executing command: {' '.join(command)}")

    subprocess.run(command, check=True, cwd=project_root)


if __name__ == "__main__":
    main()
