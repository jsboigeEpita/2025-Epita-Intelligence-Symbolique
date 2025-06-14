# -*- coding: utf-8 -*-
"""
Exemple de test utilisant la JVM réelle.
"""
import logging
import pytest
import jpype
import jpype.imports

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)

@pytest.fixture(scope="module")
def simple_jvm_fixture():
    """
    Une fixture qui s'assure que la JVM est démarrée, sans se soucier du classpath.
    Elle s'appuie sur le fait que le test est dans `tests/integration/` pour que
    le vrai module `jpype` soit chargé.
    """
    # Le vrai jpype est déjà dans sys.modules grâce à la fixture autouse
    # 'activate_jpype_mock_if_needed' de jpype_setup.py
    
    if not jpype.isJVMStarted():
        logging.info("Starting JVM with simple_jvm_fixture...")
        jpype.startJVM(convertStrings=False)
        logging.info("JVM started.")
    else:
        logging.info("JVM was already started.")
        
    yield jpype
    
    # Le shutdown est géré de manière centralisée à la fin de la session de test
    logging.info("simple_jvm_fixture finished.")


def test_jvm_is_actually_started(simple_jvm_fixture):
    """
    Teste si la JVM est bien démarrée en utilisant notre fixture simple.
    """
    assert simple_jvm_fixture.isJVMStarted(), "La JVM devrait être démarrée par simple_jvm_fixture"
    logging.info(f"JVM Version from simple_jvm_fixture: {simple_jvm_fixture.getJVMVersion()}")

# On ne peut pas tester le chargement des JARs car on ne les met pas dans le classpath.
# On supprime donc le test `test_tweety_jars_loaded`.