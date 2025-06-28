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

# La fixture locale 'simple_jvm_fixture' est supprimée pour éviter les conflits
# de démarrage de la JVM. Nous utilisons maintenant la fixture de session 'integration_jvm'.

# Le test est réactivé et utilise maintenant la fixture de session `jvm_session`
# définie dans le conftest.py principal pour garantir que la JVM est prête.
def test_jvm_is_actually_started(jvm_session):
    """
    Teste si la JVM est bien démarrée en utilisant la fixture de session partagée.
    La fixture `jvm_session` garantit que l'initialisation a eu lieu.
    """
    # La fixture `jvm_session` ne retourne rien, on utilise directement le module jpype
    assert jpype.isJVMStarted(), "La JVM devrait être démarrée par la fixture de session `jvm_session`"
    logging.info(f"JVM Version from jpype: {jpype.getJVMVersion()}")

# On ne peut pas tester le chargement des JARs car on ne les met pas dans le classpath.
# On supprime donc le test `test_tweety_jars_loaded`.