import sys
import subprocess
from pathlib import Path


def main():
    """
    Script de test autonome pour les scénarios de durcissement.
    """
    project_root = Path(__file__).resolve().parent
    sys.path.insert(0, str(project_root))

    test_file = (
        project_root
        / "tests"
        / "integration"
        / "logical_agents"
        / "test_logic_puzzles_hardening.py"
    )

    command = ["pytest", "-s", "-vv", str(test_file)]

    print(f"Executing command: {' '.join(command)}")

    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
