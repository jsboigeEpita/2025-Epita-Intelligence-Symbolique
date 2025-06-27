import sys
import subprocess
import argparse
import os
import shlex

print("--- ENV MANAGER SUPER MINIMAL ---")
parser = argparse.ArgumentParser()
parser.add_argument('--command', '-c', type=str, required=True)
# Ignorer les autres arguments pour l'instant
parser.add_argument('--env-name', '-e', type=str, default=None)
args = parser.parse_args()

print(f"Commande reçue: {args.command}")

try:
    # shlex.split pour gérer les arguments avec espaces
    command_list = shlex.split(args.command, posix=(os.name != 'nt'))
    print(f"Commande découpée: {command_list}")

    # Exécution directe sans conda run
    result = subprocess.run(
        command_list,
        check=False,
        text=True,
        capture_output=True, # Capturer la sortie pour le débogage
        encoding='utf-8'
    )

    print("--- SORTIE DU SOUS-PROCESSUS ---")
    print(f"STDOUT:\n{result.stdout}")
    print(f"STDERR:\n{result.stderr}")
    print("---------------------------------")
    print(f"Code de sortie du sous-processus: {result.returncode}")
    sys.exit(result.returncode)

except Exception as e:
    print(f"Erreur dans le script de débogage minimal: {e}")
    sys.exit(1)