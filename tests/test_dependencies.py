# -*- coding: utf-8 -*-
import importlib
import sys
import os

# Ajouter le répertoire racine au chemin Python pour pouvoir importer les modules du projet
# Cela suppose que ce script est dans le répertoire 'tests' à la racine du projet.
# Si ce n'est pas le cas, ajustez le chemin.
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir) 
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Tenter d'importer jpype pour obtenir sa version, mais ne pas échouer si non disponible ici.
try:
    import jpype
    import jpype.imports
except ImportError:
    jpype = None # jpype ne sera pas disponible si le mock est utilisé ou s'il n'est pas installé

# Liste des dépendances à vérifier
# Note: 'java' n'est pas un module Python, sa présence est vérifiée différemment.
# 'pyjnius' est également une dépendance qui peut nécessiter une configuration spéciale.
DEPENDENCIES = [
    "numpy", "pandas", "scipy", "sklearn", "nltk", "spacy", 
    "torch", "transformers", "pydantic", "requests", "matplotlib", 
    "seaborn", "networkx", "python-dotenv", "semantic_kernel", 
    "pytest", "coverage", "cryptography", "jpype" # jpype est listé ici pour la vérification d'import
]

def check_dependencies():
    """Vérifie la présence et l'importation des dépendances listées."""
    print("Vérification des dépendances Python...")
    dependencies_status = {}
    for dep in DEPENDENCIES:
        try:
            module = importlib.import_module(dep)
            if dep == "jpype" and jpype and hasattr(jpype, '__version__'):
                print(f"[OK] {dep} (version {jpype.__version__}) importé avec succès")
            else:
                print(f"[OK] {dep} importé avec succès")
            dependencies_status[dep] = True
        except ImportError as e:
            print(f"[ERREUR] Échec de l'importation de {dep}: {e}")
            dependencies_status[dep] = False
        except Exception as e:
            print(f"[ERREUR] Erreur inattendue lors de l'importation de {dep}: {e}")
            dependencies_status[dep] = False
            
    print("\nRésumé des dépendances:")
    for dep, status in dependencies_status.items():
        print(f"  - {dep}: {'Installée' if status else 'Manquante ou erreur'}")
    
    if all(dependencies_status.values()):
        print("\nToutes les dépendances Python listées semblent être correctement installées et importables.")
    else:
        print("\nCertaines dépendances Python sont manquantes ou ont des problèmes d'importation.")

if __name__ == "__main__":
    # Ceci est pour l'exécution directe du script, pas pour pytest.
    # Pytest ne devrait pas exécuter cette partie directement.
    
    # Vérifier si le mock JPype est actif (si jpype a été remplacé par le mock)
    if jpype and hasattr(jpype, '_is_mock') and jpype._is_mock:
        print("INFO: Le mock JPype est actif.")
    
    check_dependencies()

    # Test spécifique pour JPype si le vrai module est chargé
    if jpype and not (hasattr(jpype, '_is_mock') and jpype._is_mock):
        print("\nTest de démarrage de la JVM avec JPype (si non mocké)...")
        try:
            if not jpype.isJVMStarted():
                # Tenter de trouver le chemin JVM par défaut si non fourni
                jvm_path = jpype.getDefaultJVMPath()
                if not jvm_path:
                    print("ERREUR: Chemin JVM par défaut non trouvé. Impossible de démarrer la JVM.")
                    print("  Veuillez vous assurer que JAVA_HOME est configuré ou que la JVM est dans le PATH.")
                else:
                    print(f"  Utilisation du chemin JVM par défaut: {jvm_path}")
                    jpype.startJVM(jvm_path) # Passer le chemin explicitement
                    print("  JVM démarrée avec succès.")
            else:
                print("  JVM déjà démarrée.")
        except Exception as e:
            print(f"ERREUR lors du test de démarrage de la JVM: {e}")
            print("  Assurez-vous que Java Development Kit (JDK) est installé et configuré correctement.")
            print("  Vérifiez la variable d'environnement JAVA_HOME ou le PATH système.")

    # Exemple d'utilisation de jpype.imports (si jpype est disponible et la JVM démarrée)
    if jpype and jpype.isJVMStarted() and not (hasattr(jpype, '_is_mock') and jpype._is_mock) :
        try:
            print("\nTest de jpype.imports...")
            from java.util import ArrayList # Test d'importation d'une classe Java
            my_list = ArrayList()
            my_list.add("Test JPype Imports")
            print(f"  Contenu de ArrayList via jpype.imports: {my_list.get(0)}")
            print("  jpype.imports semble fonctionner.")
        except Exception as e:
            print(f"ERREUR lors du test de jpype.imports: {e}")

    print("\nFin des vérifications de dépendances.")