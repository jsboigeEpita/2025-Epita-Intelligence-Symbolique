#!/usr/bin/env python3
"""Script pour vérifier l'architecture Python vs JDK"""

import argumentation_analysis.core.environment
import platform
import sys
import subprocess
from pathlib import Path


def check_python_architecture():
    """Vérifier l'architecture Python"""
    print("=== ARCHITECTURE PYTHON ===")
    print(f"Architecture Python: {platform.architecture()}")
    print(f"Machine: {platform.machine()}")
    print(f"Processeur: {platform.processor()}")
    print(f"Plateforme: {platform.platform()}")
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")


def check_jdk_architecture():
    """Vérifier l'architecture JDK"""
    print("\n=== ARCHITECTURE JDK PORTABLE ===")

    project_root = Path(__file__).resolve().parent
    jdk_path = project_root / "libs/portable_jdk/jdk-17.0.11+9"
    java_exe = jdk_path / "bin" / "java.exe"

    print(f"JDK Path: {jdk_path}")
    print(f"Java executable: {java_exe}")
    print(f"Java executable exists: {java_exe.exists()}")

    if java_exe.exists():
        try:
            # Exécuter java -version
            result = subprocess.run(
                [str(java_exe), "-version"], capture_output=True, text=True, timeout=10
            )
            print(f"Java version output:")
            print(result.stderr)  # java -version écrit sur stderr

            # Détecter l'architecture dans la sortie
            output = result.stderr.lower()
            if "64-bit" in output:
                print("Architecture JDK détectée: 64-bit")
            elif "32-bit" in output:
                print("Architecture JDK détectée: 32-bit")
            else:
                print("Architecture JDK non détectée")

        except subprocess.TimeoutExpired:
            print("ERREUR: Timeout lors de l'exécution de java -version")
        except Exception as e:
            print(f"ERREUR lors de l'exécution de java -version: {e}")


def check_dll_dependencies():
    """Vérifier les dépendances de jvm.dll"""
    print("\n=== VERIFICATION DLL DEPENDENCIES ===")

    project_root = Path(__file__).resolve().parent
    jvm_dll = project_root / "libs/portable_jdk/jdk-17.0.11+9/bin/server/jvm.dll"

    print(f"jvm.dll path: {jvm_dll}")
    print(f"jvm.dll exists: {jvm_dll.exists()}")
    print(
        f"jvm.dll size: {jvm_dll.stat().st_size if jvm_dll.exists() else 'N/A'} bytes"
    )


def main():
    """Fonction principale"""
    check_python_architecture()
    check_jdk_architecture()
    check_dll_dependencies()


if __name__ == "__main__":
    main()
