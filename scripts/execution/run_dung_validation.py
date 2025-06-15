import project_core.core_from_scripts.auto_env
# -*- coding: utf-8 -*-
"""
Script pour lancer la validation complète du projet abs_arg_dung
dans l'environnement conda projet-is.
"""

import os
import sys
import subprocess
from pathlib import Path

# --- Activation de l'environnement ---
try:
    project_root = Path(__file__).parent.parent
    scripts_core_path = project_root / "scripts" / "core"
    
    if str(scripts_core_path) not in sys.path:
        sys.path.insert(0, str(scripts_core_path))
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    print("[VALIDATION SCRIPT] Import de 'scripts.core.auto_env' pour activation...")
    import scripts.core.auto_env
    print("[VALIDATION SCRIPT] Environnement prêt.")

except Exception as e:
    print(f"[VALIDATION SCRIPT] ERREUR CRITIQUE lors de l'activation de l'environnement: {e}")
    sys.exit(1)

# --- DÉBUT DE LA VALIDATION ---

print("\n" + "="*50)
print("   LANCEMENT DE LA VALIDATION DU PROJET 'abs_arg_dung'")
print("="*50 + "\n")

# Chemin vers le répertoire du projet étudiant
dung_dir_path = project_root / 'abs_arg_dung'

if not dung_dir_path.exists():
    print(f"[ERREUR] Le répertoire '{dung_dir_path}' n'existe pas.")
    sys.exit(1)

# Le script de validation à exécuter
validation_script_path = dung_dir_path / 'validate_project.py'

if not validation_script_path.exists():
    print(f"[ERREUR] Le script de validation '{validation_script_path}' n'a pas été trouvé.")
    sys.exit(1)

print(f"Exécution de '{validation_script_path}' dans le répertoire '{dung_dir_path}'...")

# Exécution du script de validation en changeant le répertoire de travail
# afin que tous les chemins relatifs dans le script étudiant fonctionnent correctement.
try:
    process = subprocess.run(
        [sys.executable, str(validation_script_path)],
        cwd=str(dung_dir_path),
        capture_output=True,
        check=False
    )

    output_log_path = dung_dir_path / 'validation_output.log'
    
    # Écrire la sortie et l'erreur dans un fichier de log pour éviter les problèmes d'encodage de la console
    with open(output_log_path, 'wb') as f:
        f.write(b"--- STDOUT ---\n")
        f.write(process.stdout)
        f.write(b"\n\n--- STDERR ---\n")
        f.write(process.stderr)

    print(f"\n[INFO] La sortie complète de la validation a été enregistrée dans : {output_log_path}")
    print(f"[INFO] Code de sortie du processus : {process.returncode}")

    if process.returncode == 0:
        print("\n[SUCCES] La validation s'est terminée sans erreur (code 0).")
    else:
        print(f"\n[ERREUR] La validation s'est terminée avec un code d'erreur ({process.returncode}). Veuillez consulter le fichier log.")

except Exception as e:
    print(f"\n[ERREUR FATALE] Erreur lors de l'exécution du script de validation : {e}")
    sys.exit(1)

# Optionnel: Supprimer l'ancien script d'exploration
old_script = project_root / 'scripts' / 'explore_dung_env.py'
if old_script.exists():
    try:
        os.remove(old_script)
        print(f"\n[CLEANUP] Ancien script '{old_script.name}' supprimé.")
    except OSError as e:
        print(f"\n[CLEANUP] Erreur en supprimant l'ancien script : {e}")