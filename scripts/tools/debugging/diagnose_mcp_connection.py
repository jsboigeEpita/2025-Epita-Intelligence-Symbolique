import asyncio
import sys
from pathlib import Path
import os
import argparse
import traceback
import subprocess

# --- Configuration du chemin d'accès au projet ---
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# --- Import des modules MCP ---
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import yaml
import json

def get_conda_env_name(file_path="environment.yml"):
    """
    Lit le nom de l'environnement Conda à partir du fichier environment.yml.
    """
    try:
        with open(file_path, 'r') as f:
            env_data = yaml.safe_load(f)
        return env_data.get('name', 'projet-is')  # Fallback au cas où
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

async def run_test(target: str):
    """
    Lance le serveur MCP spécifié en tant que sous-processus
    et exécute un test de connexion et d'outil.
    """
    print(f"--- Démarrage du test pour la cible: '{target}' ---")

    conda_env_name = get_conda_env_name()
    print(f"Utilisation de l'environnement Conda : {conda_env_name}")
    
    env = get_conda_env_vars(conda_env_name)
    env["PYTHONPATH"] = str(project_root)
    env["PYTHONUTF8"] = "1"

    env_prefix = get_conda_env_prefix(conda_env_name)
    python_executable = os.path.join(env_prefix, "python.exe")

    module_path = "services.mcp_server.main" if target == "main" else "services.mcp_server.minimal_main"

    server_params = StdioServerParameters(
        command=python_executable,
        args=["-u", "-m", module_path],
        env=env
    )

    try:
        print(f"--- Lancement du client et du serveur '{target}' via stdio_client ---")
        async with stdio_client(server_params) as (read, write):
            print("--- Connexion établie, initialisation de la session client ---")
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("--- Session initialisée ---")

                if target == "minimal":
                    print("--- Test du serveur MINIMAL : appel de l'outil 'ping' ---")
                    result = await session.call_tool("ping")
                    print(f"Réponse de 'ping': {result}")
                    if not result.isError and result.content and result.content[0].text == "pong":
                        print("\n--- [SUCCÈS] Le serveur minimal a répondu 'pong' ! ---")
                        return True
                    else:
                        print(f"\n--- [ÉCHEC] Réponse inattendue du serveur minimal: {result.result} ---")
                        return False
                else:
                    print("--- Test du serveur MAIN : listage des outils ---")
                    tools = await session.list_tools()
                    print(f"\n--- [SUCCÈS] Connexion réussie ! Outils ({len(tools.tools)}) ---")
                    return True

    except asyncio.TimeoutError:
        print("\n--- [ÉCHEC] Timeout lors de la communication avec le serveur. ---")
        return False
    except Exception as e:
        print(f"\n--- [ÉCHEC] Une erreur inattendue est survenue: {e} ---")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Script de diagnostic pour le serveur MCP.")
    parser.add_argument(
        "--target",
        type=str,
        choices=["main", "minimal"],
        default="main",
        help="Spécifie quel serveur MCP lancer: 'main' (défaut) ou 'minimal'."
    )
    args = parser.parse_args()

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    try:
        success = asyncio.run(asyncio.wait_for(run_test(args.target), timeout=15.0))
    except asyncio.TimeoutError:
        print("\n--- [ÉCHEC] Le script de diagnostic a dépassé le délai de 15 secondes. Le serveur est probablement bloqué. ---")
        success = False

    if success:
        print("\n--- Le diagnostic s'est terminé avec succès. ---")
        sys.exit(0)
    else:
        print("\n--- Le diagnostic a échoué. ---")
        sys.exit(1)
