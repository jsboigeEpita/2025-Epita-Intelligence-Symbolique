# -*- coding: utf-8 -*-
"""
Script pour installer les dépendances du projet abs_arg_dung
dans l'environnement conda projet-is.
"""

import argumentation_analysis.core.environment
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

    print("[INSTALL SCRIPT] Import de 'scripts.core.auto_env' pour activation...")
    import scripts.core.auto_env

    print("[INSTALL SCRIPT] Environnement prêt.")

except Exception as e:
    print(
        f"[INSTALL SCRIPT] ERREUR CRITIQUE lors de l'activation de l'environnement: {e}"
    )
    sys.exit(1)

# --- DÉBUT DE L'INSTALLATION DES DÉPENDANCES ---

print("\n" + "=" * 50)
print("   INSTALLATION DES DÉPENDANCES POUR 'abs_arg_dung'")
print("=" * 50 + "\n")

# Chemin vers le répertoire du projet étudiant et le fichier requirements
dung_dir_path = project_root / "abs_arg_dung"
requirements_path = dung_dir_path / "requirements.txt"

if not requirements_path.exists():
    print(f"[ERREUR] Le fichier '{requirements_path}' n'existe pas.")
    sys.exit(1)

print(f"Installation des dépendances depuis '{requirements_path}'...")

# Définir le JAVA_HOME pour pointer vers le JDK portable
java_home_path = project_root / "portable_jdk"
if not java_home_path.exists():
    print(f"[ERREUR] Le répertoire JDK portable '{java_home_path}' est introuvable.")
    sys.exit(1)

print(f"[INFO] Utilisation de JAVA_HOME='{java_home_path}'")
env_vars = os.environ.copy()
env_vars["JAVA_HOME"] = str(java_home_path)

# --- Mise à jour des outils de build ---
print("\n[STEP 1/2] Mise à jour de pip, setuptools et wheel...")
update_command = [
    sys.executable,
    "-m",
    "pip",
    "install",
    "--upgrade",
    "pip",
    "setuptools",
    "wheel",
]
update_process = subprocess.run(
    update_command,
    env=env_vars,
    capture_output=True,
    text=True,
    check=False,
    encoding="utf-8",
)

if update_process.returncode != 0:
    print("[WARN] La mise à jour des outils de build a échoué, mais on continue...")
    print(update_process.stderr)
else:
    print("[SUCCES] Outils de build mis à jour.")

# --- Installation des dépendances ---
print(f"\n[STEP 2/2] Installation des dépendances depuis '{requirements_path}'...")
install_command = [
    sys.executable,
    "-m",
    "pip",
    "install",
    "--no-cache-dir",
    "-r",
    str(requirements_path),
]

try:
    process = subprocess.run(
        install_command, env=env_vars, capture_output=True, check=False
    )

    output_log_path = dung_dir_path / "install_output.log"

    # Écrire la sortie et l'erreur dans un fichier de log pour éviter les problèmes d'encodage
    with open(output_log_path, "wb") as f:
        f.write(b"--- stdout ---\n")
        f.write(process.stdout)
        f.write(b"\n\n--- stderr ---\n")
        f.write(process.stderr)

    print(
        f"\n[INFO] La sortie complète de l'installation a été enregistrée dans : {output_log_path}"
    )
    print(f"[INFO] Code de sortie du processus : {process.returncode}")

    if process.returncode == 0:
        print("\n[SUCCES] Dépendances installées avec succès.")
    else:
        print(
            f"\n[ERREUR] L'installation a échoué (code {process.returncode}). Veuillez consulter le fichier log."
        )
        sys.exit(1)

except Exception as e:
    print(f"\n[ERREUR FATALE] Erreur lors de l'exécution de pip : {e}")
    sys.exit(1)
