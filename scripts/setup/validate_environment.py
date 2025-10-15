#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de validation rapide de l'environnement.
Généré automatiquement par diagnostic_environnement.py
"""

import argumentation_analysis.core.environment
import sys
import importlib
from pathlib import Path  # Ajout pour la clarté

# Ajout du répertoire racine du projet au chemin pour permettre l'import des modules
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def validate_environment():
    """Valide rapidement l'environnement."""
    print("Validation rapide de l'environnement...")

    # Vérifier le package principal
    try:
        import argumentation_analysis

        print("Package argumentation_analysis: OK")
    except ImportError as e:
        print(f"❌ Package argumentation_analysis: {e}")
        return False

    # Vérifier dépendances essentielles
    essential_deps = ["numpy", "pandas", "matplotlib", "cryptography"]
    for dep in essential_deps:
        try:
            importlib.import_module(dep)
            print(f"{dep}: OK")
        except ImportError:
            print(f"❌ {dep}: Manquant")
            return False

    # Vérifier JPype ou mock
    jpype_ok = False
    try:
        import jpype

        print("jpype: OK")
        jpype_ok = True
    except ImportError:
        try:
            from tests.mocks import jpype_mock

            print("Mock JPype: OK")
            jpype_ok = True
        except ImportError:
            print("JPype/Mock: Non disponible")

    print("\nValidation terminee!")
    return True


if __name__ == "__main__":
    success = validate_environment()
    sys.exit(0 if success else 1)
