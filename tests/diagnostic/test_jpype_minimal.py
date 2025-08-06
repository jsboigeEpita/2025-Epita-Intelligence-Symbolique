# tests/diagnostic/test_jpype_minimal.py
import pytest
import jpype
import jpype.imports
import os
import sys

@pytest.mark.jvm_test
def test_jvm_initialization(jvm_session):
    """
    Teste que la JVM est correctement démarrée par la fixture de session
    et qu'il est possible d'interagir avec.
    """
    print("--- Début du script de test JPype minimal ---")
    print(f"Version de Python: {sys.version}")
    print(f"Version de JPype: {jpype.__version__}")

    # La fixture jvm_fixture a déjà démarré la JVM, on vérifie juste.
    assert jpype.isJVMStarted(), "La fixture de session n'a pas réussi à démarrer la JVM."
    print("Assertion OK: jpype.isJVMStarted() retourne True.")

    # Test simple après démarrage
    try:
        print("Tentative d'accès à java.lang.System...")
        System = jpype.JClass("java.lang.System")
        java_version_from_jvm = System.getProperty("java.version")
        print(f"SUCCESS: Version Java obtenue depuis la JVM: {java_version_from_jvm}")
        assert java_version_from_jvm is not None
    except Exception as e_jclass:
        pytest.fail(f"ERREUR lors du test post-démarrage (JClass): {e_jclass}")

    print("--- Fin du script de test JPype minimal ---")