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
            raise FileNotFoundError(f"Le script de test à exécuter n'a pas été trouvé : {script_path}")

        # Nouvelle approche: l'injection de PYTHONPATH via un script Python est plus fiable
        project_root = Path(__file__).parent.parent.parent.resolve()
        
        # La commande complète pour le sous-processus
        command_for_subprocess = [sys.executable, str(script_path)]

        # Créer un environnement pour le sous-processus qui inclut la racine du projet dans PYTHONPATH
        env = os.environ.copy()
        env['PYTHONPATH'] = str(project_root) + os.pathsep + env.get('PYTHONPATH', '')
        
        print(f"Exécution du worker en sous-processus avec PYTHONPATH: {' '.join(command_for_subprocess)}")

        result = subprocess.run(
            command_for_subprocess,
            capture_output=True,
            text=True,
            encoding='utf-8',
            check=False,
            cwd=project_root,
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