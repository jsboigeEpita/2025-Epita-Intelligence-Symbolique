import pytest
from pathlib import Path
import jpype
import jpype.imports

# Ce test vérifie que la JVM, démarrée par la fixture de session, est fonctionnelle.

@pytest.mark.real_jpype
def test_minimal_jvm_is_functional(jvm_session):
    """
    Vérifie que la JVM est démarrée et fonctionnelle en exécutant une opération simple.
    La fixture 'jvm_session' garantit que la JVM est initialisée.
    """
    # La fixture 'jvm_session' a déjà été résolue, donc la JVM doit être active.
    assert jvm_session is True, "La fixture de session JVM n'a pas réussi."
    
    # Importation nécessaire de jpype
    import jpype
    import jpype.imports

    print("--- Vérification de l'état de la JVM dans le processus de test principal ---")
    
    assert jpype.isJVMStarted(), "La JVM devrait être active (gérée par la fixture de session)."
    
    print("Assertion jpype.isJVMStarted() réussie.")
    
    # Test de base pour s'assurer que la JVM est fonctionnelle
    StringClass = jpype.JClass("java.lang.String")
    java_string = StringClass("Test minimal dans le processus principal réussi")
    
    assert str(java_string) == "Test minimal dans le processus principal réussi"
    
    print("Test de création/conversion de java.lang.String réussi.")
    print("--- Le test de fonctionnalité JVM s'est terminé avec succès. ---")