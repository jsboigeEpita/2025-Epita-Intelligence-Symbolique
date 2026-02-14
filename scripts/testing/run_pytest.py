#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lanceur de tests pytest dédié et robuste pour cet environnement complexe.
"""

import sys
import pytest
import os

# 1. Activation et validation de l'environnement via le mécanisme centralisé moderne
try:
    import argumentation_analysis.core.environment
except (ImportError, RuntimeError) as e:
    print(
        f"ERREUR CRITIQUE: Impossible d'activer ou de valider l'environnement du projet."
    )
    print(f"Erreur: {e}")
    sys.exit(1)

# 2. Point d'entrée principal
if __name__ == "__main__":
    # La liste des arguments passés au script, en excluant le nom du script lui-même
    pytest_args = sys.argv[1:]

    if not pytest_args:
        print(
            "Usage: python run_pytest.py <chemin_vers_test_ou_dossier> [options_pytest_supplémentaires]"
        )
        sys.exit(1)

    print(f"Lanceur Pytest: Démarrage de pytest avec les arguments: {pytest_args}")

    # 3. Exécution de pytest par programmation
    exit_code = pytest.main(pytest_args)

    print(f"Lanceur Pytest: Pytest terminé avec le code de sortie: {exit_code}")
    sys.exit(exit_code)
