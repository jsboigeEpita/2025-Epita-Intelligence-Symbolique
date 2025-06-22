import pytest
import subprocess
import sys
import os
from pathlib import Path

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
            raise FileNotFoundError(f"Le script de test à exécuter n'a pas été trouvé : {script_path}")

        # Construit la commande à passer au script d'activation.
        command_to_run = [
            sys.executable,          # Le chemin vers python.exe de l'env actuel
            str(script_path.resolve()),  # Le script de test
            *args                    # Arguments supplémentaires pour le script
        ]
        
        # On utilise le wrapper d'environnement, comme on le ferait manuellement.
        # C'est la manière la plus robuste de s'assurer que l'env est correct.
        wrapper_command = [
            "powershell",
            "-File",
            ".\\activate_project_env.ps1",
            "-CommandToRun",
            " ".join(f'"{part}"' for part in command_to_run) # Reassemble la commande en une seule chaine
        ]

        print(f"Exécution du sous-processus JVM via : {' '.join(wrapper_command)}")
        
        # On exécute le processus. `check=True` lèvera une exception si le
        # sous-processus retourne un code d'erreur.
        # Cloner l'environnement actuel et ajouter la racine du projet au PYTHONPATH.
        # C'est crucial pour que les imports comme `from tests.fixtures...` fonctionnent
        # dans le sous-processus.
        env = os.environ.copy()
        project_root = str(Path(__file__).parent.parent.parent.resolve())
        python_path = env.get('PYTHONPATH', '')
        if project_root not in python_path:
            env['PYTHONPATH'] = f"{project_root}{os.pathsep}{python_path}"

        result = subprocess.run(
            wrapper_command,
            capture_output=True,
            text=True,
            encoding='utf-8',
            check=False, # On met à False pour pouvoir afficher les logs même si ça plante
            env=env
        )
        
        # Afficher la sortie pour le débogage, surtout en cas d'échec
        print("\n--- STDOUT du sous-processus ---")
        print(result.stdout)
        print("--- STDERR du sous-processus ---")
        print(result.stderr)
        print("--- Fin du sous-processus ---")

        # Vérifier manuellement le code de sortie
        if result.returncode != 0:
            pytest.fail(f"Le sous-processus de test JVM a échoué avec le code {result.returncode}.", pytrace=False)
            
        return result

    return runner