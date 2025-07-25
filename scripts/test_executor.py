import argparse
import json
import os
import subprocess
import sys
import yaml

def get_conda_env_name(file_path="environment.yml"):
    """
    Lit le nom de l'environnement Conda à partir du fichier environment.yml.
    """
    try:
        with open(file_path, 'r') as f:
            env_data = yaml.safe_load(f)
        return env_data.get('name', 'e2e_test_env')  # Fallback au cas où
    except FileNotFoundError:
        print(f"Erreur : Le fichier {file_path} n'a pas été trouvé.", file=sys.stderr)
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Erreur lors de la lecture du fichier YAML {file_path}: {e}", file=sys.stderr)
        sys.exit(1)

def get_conda_env_vars(env_name):
    """
    Récupère les variables d'environnement d'un environnement Conda spécifique.
    """
    command = [
        "conda", "run", "-n", env_name,
        "python", "-c", "import os, json; print(json.dumps(dict(os.environ)))"
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8')
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Erreur lors de la récupération des variables d'environnement pour '{env_name}':", file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Erreur lors du décodage du JSON des variables d'environnement: {e}", file=sys.stderr)
        sys.exit(1)

def get_conda_env_prefix(env_name):
    """
    Récupère le chemin du préfixe (racine) d'un environnement Conda.
    """
    command = ["conda", "env", "list", "--json"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8')
        env_list = json.loads(result.stdout)
        for env_path in env_list.get("envs", []):
            if env_path.endswith(env_name):
                return env_path
        print(f"Erreur: Environnement Conda '{env_name}' non trouvé dans la liste.", file=sys.stderr)
        sys.exit(1)
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        print(f"Erreur lors de la récupération du préfixe de l'environnement Conda: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    """
    Point d'entrée du script.
    """
    parser = argparse.ArgumentParser(
        description="Exécuteur de tests intelligent pour contourner les problèmes de 'conda run'."
    )
    parser.add_argument(
        "--original-command",
        required=True,
        help="La commande de test originale à exécuter (ex: 'pytest -m jvm_test')."
    )
    args = parser.parse_args()

    print("--- Début de l'exécution des tests via test_executor.py ---")

    # 1. Déterminer l'environnement Conda cible
    conda_env_name = get_conda_env_name()
    print(f"Environnement Conda cible : {conda_env_name}")

    # 2. Récupérer les variables d'environnement de l'environnement cible
    print("Récupération des variables d'environnement...")
    target_env = get_conda_env_vars(conda_env_name)
    
    # On s'assure que l'encodage est bien UTF-8, c'est une bonne pratique
    target_env['PYTHONIOENCODING'] = 'utf-8'
    target_env['PYTHONUTF8'] = '1'

    # 3. Récupérer le chemin préfixe de l'environnement et construire les chemins des exécutables
    print("Localisation du préfixe de l'environnement Conda...")
    env_prefix = get_conda_env_prefix(conda_env_name)
    print(f"Préfixe de l'environnement trouvé : {env_prefix}")

    python_executable = os.path.join(env_prefix, "python.exe")
    pytest_executable = os.path.join(env_prefix, "Scripts", "pytest.exe")

    # 4. Construire et exécuter la commande finale
    # La commande originale est une chaîne, il faut la séparer en arguments.
    command_to_run = args.original_command.split()
    
    if not os.path.exists(python_executable):
        print(f"Erreur: L'exécutable Python n'a pas été trouvé à l'emplacement attendu: {python_executable}", file=sys.stderr)
        sys.exit(1)
        
    if not os.path.exists(pytest_executable):
        print(f"Erreur: Pytest n'a pas été trouvé à l'emplacement attendu: {pytest_executable}", file=sys.stderr)
        sys.exit(1)

    final_command = [pytest_executable] + command_to_run[1:]

    print(f"Construction de l'environnement d'exécution et appel à subprocess...")
    print(f"Commande finale : {' '.join(final_command)}")

    try:
        # Utilise le shell de l'OS courant et passe les variables d'environnement
        result = subprocess.run(
            final_command,
            env=target_env,
            check=False  # On ne veut pas que le script s'arrête si les tests échouent
        )
        print("--- Fin de l'exécution des tests ---")
        # Propage le code de sortie des tests
        sys.exit(result.returncode)

    except FileNotFoundError:
        print(f"Erreur : La commande '{final_command[0]}' n'a pas été trouvée.", file=sys.stderr)
        print("Assurez-vous que le chemin vers l'exécutable est correct.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Une erreur inattendue est survenue : {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()