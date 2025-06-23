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

        # Construit la commande à passer au script d'activation.
        command_to_run = [
            sys.executable,
            str(script_path.resolve()),
            *args
        ]

        print(f"Exécution du sous-processus JVM direct : {' '.join(command_to_run)}")
        
        # On exécute le processus. `check=True` lèvera une exception si le
        # sous-processus retourne un code d'erreur.
        # Cloner l'environnement actuel et ajouter la racine du projet au PYTHONPATH.
        # C'est crucial pour que les imports comme `from tests.fixtures...` fonctionnent
        # dans le sous-processus.
        # Forcer le rechargement du .env pour s'assurer que les dernières
        # modifications sont prises en compte dans le sous-processus.
        # C'est CRUCIAL car le processus pytest principal ne relit pas le .env
        # après son démarrage initial. override=True garantit que les
        # variables en mémoire (potentiellement périmées) sont écrasées.
        load_dotenv(find_dotenv(), override=True)
        
        # La configuration du PYTHONPATH est maintenant gérée de manière centralisée
        # dans tests/conftest.py, qui s'applique à l'ensemble du processus pytest et
        # à ses processus enfants. Il n'est plus nécessaire de le définir ici.
        env = os.environ.copy()

        result = subprocess.run(
            command_to_run,
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