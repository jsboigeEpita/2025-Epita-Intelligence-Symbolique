"""
Classe de base pour les tests qui dépendent de la JVM.

Cette classe fournit une base pour les tests qui nécessitent la JVM,
en s'assurant que la JVM est correctement initialisée avant l'exécution
des tests et en sautant les tests si la JVM n'est pas disponible.
"""

import sys
import os
import unittest
from pathlib import Path
import logging
import shutil

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)

class JVMTestCase(unittest.TestCase):
    """Classe de base pour les tests qui dépendent de la JVM."""
    
    @classmethod
    def setUpClass(cls):
        """
        La JVM est maintenant initialisée globalement par conftest.py (racine).
        Cette méthode vérifie simplement si elle est prête.
        """
        import jpype # Nécessaire pour vérifier jpype.isJVMStarted()
        if not jpype.isJVMStarted():
            logging.error("JVMTestCase.setUpClass: La JVM n'a pas été démarrée par conftest.py (racine).")
            cls.jvm_ready = False
        else:
            logging.info("JVMTestCase.setUpClass: La JVM est déjà démarrée (par conftest.py racine).")
            cls.jvm_ready = True
            # La variable d'environnement est une indication supplémentaire
            jvm_env_status = os.getenv("JPYPE_REAL_JVM_INITIALIZED", "0")
            if jvm_env_status == "1":
                logging.info("JVMTestCase.setUpClass: JPYPE_REAL_JVM_INITIALIZED=1 confirme l'initialisation.")
            else:
                logging.warning("JVMTestCase.setUpClass: JPYPE_REAL_JVM_INITIALIZED n'est pas à 1. Incohérence possible.")


    def setUp(self):
        """Vérifie si la JVM est prête avant chaque test."""
        # Tenter d'importer jpype ici pour s'assurer qu'il est accessible
        try:
            import jpype
        except ImportError:
            self.fail("Échec de l'import de jpype dans JVMTestCase.setUp. JPype doit être installé.")

        if not hasattr(self.__class__, 'jvm_ready') or not self.__class__.jvm_ready:
            # Si jvm_ready n'a pas été défini ou est False après setUpClass
            # Cela signifie que la JVM n'a pas été démarrée par le conftest racine.
            self.skipTest("JVM non disponible ou non initialisée par conftest.py (racine). Test sauté.")
        elif not jpype.isJVMStarted():
            # Double vérification au cas où quelque chose aurait arrêté la JVM entre-temps.
            self.skipTest("JVM non démarrée (vérification dans setUp). Test sauté.")
        else:
            logging.info(f"JVMTestCase.setUp: Test '{self.id()}' démarre. JVM est prête.")