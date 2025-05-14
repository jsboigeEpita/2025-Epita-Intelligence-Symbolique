"""
Classe de base pour les tests qui dépendent de la JVM.

Cette classe fournit une base pour les tests qui nécessitent la JVM,
en s'assurant que la JVM est correctement initialisée avant l'exécution
des tests et en sautant les tests si la JVM n'est pas disponible.
"""

import unittest
import os
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
        """Initialise la JVM avant l'exécution des tests."""
        # Importer les modules nécessaires
        try:
            from argumentiation_analysis.core.jvm_setup import initialize_jvm
            from argumentiation_analysis.paths import LIBS_DIR
        except ImportError as e:
            logging.error(f"Erreur d'importation: {e}")
            cls.jvm_ready = False
            return
        
        # Déterminer le chemin vers les JARs de test
        test_resources_dir = Path(__file__).parent / "resources" / LIBS_DIR
        
        # Vérifier si les JARs de test existent
        if test_resources_dir.exists() and any(test_resources_dir.glob("*.jar")):
            logging.info(f"Utilisation des JARs de test depuis {test_resources_dir}")
            
            # Copier les JARs de test vers le répertoire libs/ si nécessaire
            if not LIBS_DIR.exists() or not any(LIBS_DIR.glob("*.jar")):
                logging.info(f"Copie des JARs de test vers {LIBS_DIR}")
                LIBS_DIR.mkdir(exist_ok=True)
                
                for jar_file in test_resources_dir.glob("*.jar"):
                    shutil.copy2(jar_file, LIBS_DIR / jar_file.name)
                
                # Copier les bibliothèques natives si elles existent
                test_native_dir = test_resources_dir / "native"
                if test_native_dir.exists():
                    native_dir = LIBS_DIR / "native"
                    native_dir.mkdir(exist_ok=True)
                    
                    for native_file in test_native_dir.glob("*.*"):
                        shutil.copy2(native_file, native_dir / native_file.name)
        
        # Initialiser la JVM
        try:
            cls.jvm_ready = initialize_jvm(lib_dir_path=str(LIBS_DIR))
            if cls.jvm_ready:
                logging.info("✅ JVM initialisée avec succès pour les tests.")
            else:
                logging.warning("⚠️ JVM n'a pas pu être initialisée. Les tests dépendant de la JVM seront sautés.")
        except Exception as e:
            logging.error(f"❌ Erreur lors de l'initialisation de la JVM: {e}")
            cls.jvm_ready = False
    
    def setUp(self):
        """Vérifie si la JVM est prête avant chaque test."""
        if not getattr(self.__class__, 'jvm_ready', False):
            self.skipTest("JVM non disponible. Test sauté.")