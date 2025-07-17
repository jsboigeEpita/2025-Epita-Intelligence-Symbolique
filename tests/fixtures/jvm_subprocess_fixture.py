import pytest
import subprocess
import sys
import os
import subprocess
from pathlib import Path
import subprocess
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
        env['PROJECT_ROOT'] = str(project_root)
        
        print(f"Exécution du worker en sous-processus avec PYTHONPATH et PROJECT_ROOT: {' '.join(command_for_subprocess)}")

        # On capture la sortie pour pouvoir l'afficher en cas d'erreur.
        result = subprocess.run(
            command_for_subprocess,
            capture_output=True,
            check=False,  # On gère l'échec manuellement avec pytest.fail
            cwd=project_root,
            env=env,
            text=True,
            encoding='utf-8'
        )
        
        # La sortie (stdout/stderr) s'affichera directement dans la console pytest.
        # Nous vérifions uniquement le code de retour.

        # Vérifier manuellement le code de sortie
        if result.returncode != 0:
            pytest.fail(
                f"Le sous-processus de test JVM a échoué avec le code {result.returncode}. "
                "Vérifiez la sortie de la console ci-dessus pour les logs du worker, "
                "y compris les erreurs potentielles de téléchargement ou d'initialisation de la JVM.",
                pytrace=False
            )
            
        return result

    return runner