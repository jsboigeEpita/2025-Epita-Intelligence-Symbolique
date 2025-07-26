import sys
from pathlib import Path
import jpype
import jpype.imports

# Ajout du chemin racine pour que les importations fonctionnent dans le sous-processus
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from argumentation_analysis.core.jvm_setup import initialize_jvm, shutdown_jvm

def main():
    """
    Point d'entrée pour le script de test exécuté en sous-processus.
    """
    print("--- Début du worker de test JVM en sous-processus ---")
    try:
        print("Initialisation de la JVM...")
        if not initialize_jvm():
            print("Échec de l'initialisation de la JVM.")
            sys.exit(1)
        
        print("JVM initialisée avec succès.")
        
        assert jpype.isJVMStarted(), "La JVM devrait être démarrée."
        print("Assertion jpype.isJVMStarted() réussie.")

        StringClass = jpype.JClass("java.lang.String")
        java_string = StringClass("Test minimal dans le sous-processus réussi")
        
        assert str(java_string) == "Test minimal dans le sous-processus réussi"
        print("Test de création/conversion de java.lang.String réussi.")

    except Exception as e:
        print(f"Une erreur est survenue dans le worker : {e}", file=sys.stderr)
        # Tenter de fermer la JVM même en cas d'erreur
        if jpype.isJVMStarted():
            shutdown_jvm()
        sys.exit(1)
    finally:
        if jpype.isJVMStarted():
            print("Arrêt de la JVM...")
            shutdown_jvm()
            print("JVM arrêtée.")
    
    print("--- Fin du worker de test JVM en sous-processus (Succès) ---")
    sys.exit(0)

if __name__ == "__main__":
    main()