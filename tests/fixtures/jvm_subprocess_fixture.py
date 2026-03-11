import pytest
import subprocess
import sys
import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv


@pytest.fixture(scope="function")
def run_in_jvm_subprocess():
    """
    Fixture qui fournit une fonction pour exécuter un script de test Python
    dans un sous-processus isolé. Cela garantit que chaque test utilisant la JVM
    obtient un environnement propre, évitant les conflits de DLL et les crashs.
    """

    def runner(script_path: Path, *args):
        """
        Exécute le script de test donné dans un sous-processus en utilisant
        le même interpréteur Python et en passant par le wrapper d'environnement.
        """
        script_path = Path(script_path)
        if not script_path.exists():
            raise FileNotFoundError(
                f"Le script de test à exécuter n'a pas été trouvé : {script_path}"
            )

        project_root = Path(__file__).parent.parent.parent.resolve()

        command_for_subprocess = [sys.executable, str(script_path)]

        # Créer un environnement pour le sous-processus
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_root) + os.pathsep + env.get("PYTHONPATH", "")
        env["PROJECT_ROOT"] = str(project_root)

        # Remove PYTEST_CURRENT_TEST to prevent auto-mock in subprocess
        env.pop("PYTEST_CURRENT_TEST", None)

        # Charger les variables du fichier .env
        dotenv_path = find_dotenv(str(project_root / ".env"))
        if dotenv_path:
            load_dotenv(dotenv_path=dotenv_path, override=True)
            env.update(
                {
                    k: v
                    for k, v in os.environ.items()
                    if k in ["JAVA_HOME", "TWEETY_CLASSPATH"]
                }
            )

        print(
            f"Exécution du worker en sous-processus: {' '.join(command_for_subprocess)}"
        )

        result = subprocess.run(
            command_for_subprocess,
            capture_output=True,
            check=False,
            cwd=project_root,
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        # Print captured output so pytest shows it
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)

        if result.returncode != 0:
            pytest.fail(
                f"Le sous-processus de test JVM a échoué avec le code {result.returncode}.\n"
                f"STDOUT:\n{result.stdout[-2000:] if result.stdout else '(vide)'}\n"
                f"STDERR:\n{result.stderr[-2000:] if result.stderr else '(vide)'}",
                pytrace=False,
            )

        return result

    return runner
