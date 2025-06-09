"""
Fixtures d'intégration pour les tests.

Ce module contient les fixtures nécessaires pour les tests d'intégration,
incluant la configuration JVM et les classes Java.
"""
import pytest
import logging
from unittest.mock import MagicMock

logger = logging.getLogger(__name__)

@pytest.fixture(scope="session")
def integration_jvm():
    """Fixture pour initialiser la JVM pour les tests d'intégration."""
    logger.info("Initialisation de la JVM pour les tests d'intégration")
    
    # Mock JVM pour les tests
    jvm_mock = MagicMock(name="integration_jvm_mock")
    jvm_mock.started = False
    
    def start_jvm():
        jvm_mock.started = True
        logger.info("JVM mock démarrée")
    
    def stop_jvm():
        jvm_mock.started = False
        logger.info("JVM mock arrêtée")
    
    jvm_mock.start = start_jvm
    jvm_mock.stop = stop_jvm
    
    return jvm_mock

@pytest.fixture
def dung_classes(integration_jvm):
    """Fixture pour les classes Dung."""
    return MagicMock(name="dung_classes_mock")

@pytest.fixture
def dl_syntax_parser(integration_jvm):
    """Fixture pour le parseur de syntaxe DL."""
    return MagicMock(name="dl_syntax_parser_mock")

@pytest.fixture
def fol_syntax_parser(integration_jvm):
    """Fixture pour le parseur de syntaxe FOL."""
    return MagicMock(name="fol_syntax_parser_mock")

@pytest.fixture
def pl_syntax_parser(integration_jvm):
    """Fixture pour le parseur de syntaxe PL."""
    return MagicMock(name="pl_syntax_parser_mock")

@pytest.fixture
def cl_syntax_parser(integration_jvm):
    """Fixture pour le parseur de syntaxe CL."""
    return MagicMock(name="cl_syntax_parser_mock")

@pytest.fixture
def tweety_logics_classes(integration_jvm):
    """Fixture pour les classes de logique Tweety."""
    return MagicMock(name="tweety_logics_classes_mock")

@pytest.fixture
def tweety_string_utils(integration_jvm):
    """Fixture pour les utilitaires de chaînes Tweety."""
    return MagicMock(name="tweety_string_utils_mock")

@pytest.fixture
def tweety_math_utils(integration_jvm):
    """Fixture pour les utilitaires mathématiques Tweety."""
    return MagicMock(name="tweety_math_utils_mock")

@pytest.fixture
def tweety_probability(integration_jvm):
    """Fixture pour les classes de probabilité Tweety."""
    return MagicMock(name="tweety_probability_mock")

@pytest.fixture
def tweety_conditional_probability(integration_jvm):
    """Fixture pour les probabilités conditionnelles Tweety."""
    return MagicMock(name="tweety_conditional_probability_mock")

@pytest.fixture
def tweety_parser_exception(integration_jvm):
    """Fixture pour les exceptions de parseur Tweety."""
    return Exception

@pytest.fixture
def tweety_io_exception(integration_jvm):
    """Fixture pour les exceptions IO Tweety."""
    return Exception

@pytest.fixture
def tweety_qbf_classes(integration_jvm):
    """Fixture pour les classes QBF Tweety."""
    return MagicMock(name="tweety_qbf_classes_mock")

@pytest.fixture
def belief_revision_classes(integration_jvm):
    """Fixture pour les classes de révision de croyances."""
    return MagicMock(name="belief_revision_classes_mock")

@pytest.fixture
def dialogue_classes(integration_jvm):
    """Fixture pour les classes de dialogue."""
    return MagicMock(name="dialogue_classes_mock")