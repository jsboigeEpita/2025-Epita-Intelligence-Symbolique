#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Façade CLI pour le Gestionnaire de Setup du Projet.
=====================================================

Ce script est le point d'entrée unique pour toutes les opérations de
configuration et de validation de l'environnement du projet. Il délègue
toute la logique d'exécution au module `project_setup` dans `project_core`.

Utilisation:
    python scripts/setup_manager.py setup --env test
    python scripts/setup_manager.py validate --all
    python scripts/setup_manager.py install

Auteur: Intelligence Symbolique EPITA
Date: 27/06/2025
"""

import sys
from pathlib import Path

# Assurer que la racine du projet est dans le sys.path pour les imports
# Ce montage est nécessaire pour exécuter le script depuis n'importe où
# tout en conservant des imports absolus cohérents.
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from project_core.core_from_scripts.project_setup import main as project_setup_main


def main():
    """
    Fonction principale qui agit comme un proxy direct vers le point
    d'entrée du gestionnaire de setup principal.

    Cette approche de "trampoline" assure que ce script reste un simple
    lanceur, tandis que toute la complexité (parsing des arguments, logique
    métier) est encapsulée dans le module `project_core`.
    """
    project_setup_main()


if __name__ == "__main__":
    main()
