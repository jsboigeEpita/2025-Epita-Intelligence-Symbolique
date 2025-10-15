#!/usr/bin/env python3
"""
Script de validation de l'installation JDK 17 portable
"""

import argumentation_analysis.core.environment
import os
import subprocess
import sys
from pathlib import Path


# --- Correction du PYTHONPATH pour l'exécution autonome ---
def _setup_sys_path():
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


_setup_sys_path()
# --- Fin de la correction ---


def main():
    print("=== VALIDATION INSTALLATION JDK 17 PORTABLE ===")

    # Chemin JDK
    project_root = (
        Path(__file__).resolve().parents[2]
    )  # Corrigé pour pointer vers la vraie racine
    libs_dir = project_root / "libs"
    jdk_path = libs_dir / "portable_jdk" / "jdk-17.0.11+9"
    java_exe = jdk_path / "bin" / "java.exe"

    print(f"1. Vérification répertoire JDK: {jdk_path}")
    if jdk_path.exists():
        print("   [OK] Repertoire JDK trouve")
    else:
        print("   [ERREUR] Repertoire JDK manquant")
        return False

    print(f"2. Vérification exécutable Java: {java_exe}")
    if java_exe.exists():
        print("   [OK] Executable Java trouve")
    else:
        print("   [ERREUR] Executable Java manquant")
        return False

    print("3. Test version Java:")
    try:
        result = subprocess.run(
            [str(java_exe), "-version"], capture_output=True, text=True, check=True
        )
        print("   [OK] Java fonctionne:")
        for line in result.stderr.split("\n"):
            if line.strip():
                print(f"      {line}")
    except Exception as e:
        print(f"   [ERREUR] Erreur Java: {e}")
        return False

    print("4. Configuration variables d'environnement:")
    os.environ["JAVA_HOME"] = str(jdk_path)
    os.environ["PATH"] = f"{jdk_path / 'bin'}{os.pathsep}{os.environ.get('PATH', '')}"
    print(f"   [OK] JAVA_HOME: {os.environ['JAVA_HOME']}")

    print("5. Test TweetyProject:")
    try:
        from argumentation_analysis.agents.core.logic.tweety_initializer import (
            TweetyInitializer,
        )

        print("   [OK] TweetyInitializer importe avec succes")
    except Exception as e:
        print(f"   [WARN] Import TweetyInitializer: {e}")

    print("\n*** INSTALLATION JDK 17 PORTABLE REUSSIE ! ***")
    print(
        "INFO: Pour utiliser Java: configurez JAVA_HOME et PATH comme montre ci-dessus"
    )
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
