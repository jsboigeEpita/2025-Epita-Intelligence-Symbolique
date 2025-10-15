#!/usr/bin/env python3
"""
Remplacement pour backend_failover_non_interactive
Généré automatiquement par migrate_to_service_manager.py
"""

import sys
import subprocess
from pathlib import Path

# Ajout du chemin du projet
sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    """Exécute le remplacement pour backend_failover_non_interactive"""
    replacement_cmd = "python -c \"from project_core.service_manager import *; sm = ServiceManager(); sm.start_service_with_failover('backend-flask')\""
    print(f"Exécution du remplacement pour backend_failover_non_interactive")
    print(f"Commande: {replacement_cmd}")

    try:
        if replacement_cmd.startswith("python -m"):
            # Commande module Python
            parts = replacement_cmd.split()
            result = subprocess.run(parts, check=True)
            return result.returncode
        elif replacement_cmd.startswith("python -c"):
            # Code Python direct
            code = replacement_cmd[11:-1]  # Enlever 'python -c "' et '"'
            exec(code)
            return 0
        else:
            # Commande shell générique
            result = subprocess.run(replacement_cmd, shell=True, check=True)
            return result.returncode

    except subprocess.CalledProcessError as e:
        print(f"Erreur exécution: {e}")
        return e.returncode
    except Exception as e:
        print(f"Erreur: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
