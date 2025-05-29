"""
Classe de base pour les tests qui dépendent de la JVM.

Cette classe fournit une base pour les tests qui nécessitent la JVM,
en s'assurant que la JVM est correctement initialisée avant l'exécution
des tests et en sautant les tests si la JVM n'est pas disponible.
"""

import sys
import os

# Ajouter le répertoire site-packages utilisateur au sys.path si JPype1 n'est pas trouvé
# Ceci est un contournement pour les environnements où le site-packages utilisateur n'est pas automatiquement inclus.
try:
    import jpype
    # Si l'import réussit, jpype est accessible.
    # On peut vérifier son chemin pour s'assurer que ce n'est pas le mock.
    if hasattr(jpype, '__file__') and 'tests.mocks.jpype_mock' in jpype.__file__:
        print(f"[JVMTestCase WARNING] L'import de 'jpype' a chargé le mock: {jpype.__file__}. Cela ne devrait pas arriver ici si le vrai jpype est attendu.")
    else:
        print(f"[JVMTestCase INFO] 'jpype' trouvé dans sys.path: {getattr(jpype, '__file__', 'Chemin inconnu')}")

except ModuleNotFoundError:
    print("[JVMTestCase INFO] 'jpype' non trouvé initialement. Tentative d'ajout du site-packages utilisateur.")
    # Construire le chemin vers le site-packages utilisateur.
    # Note: Python{sys.version_info.major}{sys.version_info.minor} est une convention commune.
    # Pour Python 3.13, ce serait Python313.
    # Le chemin exact peut varier légèrement (ex: PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\LocalCache\Roaming...)
    # La sortie de `pip install` montrait: c:\users\jsboi\appdata\roaming\python\python313\site-packages
    
    # Tentative 1: Chemin exact vu dans pip
    user_site_packages_specific = os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'Python', f'Python{sys.version_info.major}{sys.version_info.minor}', 'site-packages')
    
    # Tentative 2: Structure plus générique pour les installations utilisateur via pip (souvent via `python -m site --user-site`)
    # Ceci est plus portable mais peut ne pas correspondre à toutes les configurations Windows.
    # Pour Windows, `site.USER_SITE` est généralement le bon chemin.
    user_site_packages_generic = None
    try:
        import site
        if hasattr(site, 'USER_SITE') and site.USER_SITE:
            user_site_packages_generic = site.USER_SITE
            print(f"[JVMTestCase DEBUG] site.USER_SITE trouvé: {user_site_packages_generic}")
    except ImportError:
        print("[JVMTestCase DEBUG] Module 'site' non trouvé, ne peut pas utiliser site.USER_SITE.")
        
    path_to_add = None
    if os.path.isdir(user_site_packages_specific):
        path_to_add = user_site_packages_specific
    elif user_site_packages_generic and os.path.isdir(user_site_packages_generic):
        path_to_add = user_site_packages_generic
        
    if path_to_add:
        if path_to_add not in sys.path:
            print(f"[JVMTestCase INFO] Ajout de {path_to_add} à sys.path pour trouver 'jpype'.")
            sys.path.insert(0, path_to_add)
            # Essayer à nouveau d'importer après avoir ajouté le chemin
            try:
                import jpype
                print(f"[JVMTestCase INFO] 'jpype' importé avec succès après ajout de {path_to_add} à sys.path. Chemin: {getattr(jpype, '__file__', 'Inconnu')}")
            except ModuleNotFoundError:
                print(f"[JVMTestCase ERROR] 'jpype' toujours non trouvé après ajout de {path_to_add} à sys.path.")
        else:
            # Si le chemin est déjà là, et que l'import initial a échoué, le problème est ailleurs.
            print(f"[JVMTestCase INFO] Le chemin {path_to_add} est déjà dans sys.path, mais 'jpype' n'a pas été trouvé initialement. Vérifiez l'installation de JPype1.")
    else:
        print(f"[JVMTestCase WARNING] 'jpype' non trouvé et les répertoires site-packages utilisateur potentiels ({user_site_packages_specific}, {user_site_packages_generic}) n'existent pas ou n'ont pas pu être déterminés.")

import unittest
# os a déjà été importé
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
            from argumentation_analysis.core.jvm_setup import initialize_jvm
            from argumentation_analysis.paths import LIBS_DIR
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