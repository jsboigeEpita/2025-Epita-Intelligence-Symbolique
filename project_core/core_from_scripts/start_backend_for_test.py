# -*- coding: utf-8 -*-
"""
Utilitaire pour lancer le backend de l'application en arrière-plan,
spécifiquement pour les besoins des tests automatisés.

Ce script est conçu pour être appelé depuis un script shell (ex: PowerShell)
qui orchestre les tests. Il démarre le serveur webapp, écrit son PID dans
un fichier pour permettre au script appelant de le gérer (attendre, ou
terminer le processus), et redirige stdout/stderr vers des fichiers de log.
"""
import os
import sys
import subprocess
from pathlib import Path

def main():
    """
    Point d'entrée principal du script.
    """
    # Déterminer la racine du projet à partir de l'emplacement de ce script
    # project_core/core_from_scripts/start_backend_for_test.py -> project_root
    project_root = Path(__file__).parent.parent.parent.absolute()
    
    # Valider que nous sommes bien à la racine attendue
    if not (project_root / 'pyproject.toml').exists():
        print(f"ERREUR: Impossible de trouver la racine du projet. Attendu un 'pyproject.toml' dans {project_root}", file=sys.stderr)
        sys.exit(1)

    # Configuration des chemins
    orchestrator_module = "argumentation_analysis.webapp.orchestrator"
    log_dir = project_root / '_temp'
    log_dir.mkdir(exist_ok=True) # S'assurer que le répertoire de log existe
    
    backend_stdout_log = log_dir / 'backend_stdout.log'
    backend_stderr_log = log_dir / 'backend_stderr.log'
    pid_file = log_dir / 'backend.pid'

    # S'assurer que la racine du projet est dans le PYTHONPATH
    # pour que l'import de l'orchestrateur fonctionne
    sys.path.insert(0, str(project_root))
    
    # Construction de la commande de lancement
    # On utilise sys.executable pour s'assurer qu'on utilise le python
    # de l'environnement conda activé.
    orchestrator_cmd = [
        sys.executable,
        "-m",
        orchestrator_module,
        "--backend-only",
        "--config",
        str(project_root / "config/webapp_config.yml")
    ]

    print(f"--- Lancement du Backend pour les tests (via {__file__}) ---")
    print(f"  - Commande: {' '.join(orchestrator_cmd)}")
    print(f"  - PID file: {pid_file}")
    print(f"  - Logs: {log_dir}")

    # Ouvrir les fichiers de log pour la redirection
    # L'encodage utf-8 est crucial pour éviter les erreurs sur Windows
    stdout_log = open(backend_stdout_log, 'w', encoding='utf-8')
    stderr_log = open(backend_stderr_log, 'w', encoding='utf-8')

    # Démarrer le processus en arrière-plan
    # Popen est non-bloquant
    process = subprocess.Popen(
        orchestrator_cmd,
        cwd=project_root,
        stdout=stdout_log,
        stderr=stderr_log,
        env=os.environ.copy() # Transmettre l'environnement actuel
    )
    
    # Écrire le PID dans le fichier pour que le script appelant puisse le tuer
    try:
        with open(pid_file, 'w', encoding='utf-8') as f:
            f.write(str(process.pid))
        print(f"Backend lancé avec succès. PID: {process.pid}")
    except IOError as e:
        print(f"ERREUR: Impossible d'écrire dans le fichier PID '{pid_file}': {e}", file=sys.stderr)
        # Tenter de tuer le processus qu'on vient de lancer pour ne pas le laisser zombie
        process.kill()
        sys.exit(1)

if __name__ == "__main__":
    main()