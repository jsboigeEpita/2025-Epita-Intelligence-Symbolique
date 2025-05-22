#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script d'initialisation pour la compatibilité JPype1/pyjnius.
Ce script détecte la version de Python et importe le module mock si nécessaire.
"""

import sys
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("init_jpype_compatibility")

def init_compatibility():
    """
    Initialise la compatibilité JPype1/pyjnius en fonction de la version de Python.
    """
    # Vérifier la version de Python
    if sys.version_info.major == 3 and sys.version_info.minor >= 12:
        logger.info("Python 3.12 ou supérieur détecté, utilisation du module mock JPype1")
        try:
            # Importer le module mock
            from tests.mocks import jpype_to_pyjnius
            logger.info("Module mock JPype1 importé avec succès")
            return True
        except ImportError as e:
            logger.error(f"Erreur lors de l'importation du module mock JPype1 : {e}")
            return False
    else:
        logger.info(f"Python {sys.version_info.major}.{sys.version_info.minor} détecté, utilisation de JPype1 standard")
        return True

if __name__ == "__main__":
    init_compatibility()
