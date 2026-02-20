import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock
import jpype
import jpype.imports

_jpype_is_mocked = isinstance(sys.modules.get("jpype"), MagicMock)

# Ce test vérifie que la JVM, démarrée par la fixture de session, est fonctionnelle.


@pytest.mark.real_jpype
@pytest.mark.skipif(
    _jpype_is_mocked, reason="jpype is mocked by --disable-jvm-session"
)
def test_minimal_jvm_is_functional(jvm_session):
    """
    Vérifie que la JVM est démarrée et fonctionnelle en exécutant une opération simple.
    La fixture 'jvm_session' garantit que la JVM est initialisée.
    """
    # La fixture 'jvm_session' yields the jpype module when JVM is started.
    assert jvm_session is not None, "La fixture de session JVM n'a pas réussi."

    import jpype
    import jpype.imports

    print(
        "--- Vérification de l'état de la JVM dans le processus de test principal ---"
    )

    assert (
        jpype.isJVMStarted()
    ), "La JVM devrait être active (gérée par la fixture de session)."

    print("Assertion jpype.isJVMStarted() réussie.")

    # Test de base pour s'assurer que la JVM est fonctionnelle
    StringClass = jpype.JClass("java.lang.String")
    java_string = StringClass("Test minimal dans le processus principal réussi")

    assert str(java_string) == "Test minimal dans le processus principal réussi"

    print("Test de création/conversion de java.lang.String réussi.")
    print("--- Le test de fonctionnalité JVM s'est terminé avec succès. ---")
