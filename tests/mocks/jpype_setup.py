"""
Configuration et setup pour JPype dans les tests.

Ce module gère la configuration de JPype pour les tests, incluant les mocks
et la détection de JPype réel si disponible.
"""
import os
import sys
import logging
from unittest.mock import MagicMock
import importlib.util

logger = logging.getLogger(__name__)

# Variables globales pour JPype
_REAL_JPYPE_MODULE = None
_REAL_JPYPE_AVAILABLE = False
_JPYPE_MODULE_MOCK_OBJ_GLOBAL = None
_MOCK_DOT_JPYPE_MODULE_GLOBAL = None

def setup_jpype():
    """
    Configure JPype pour les tests.
    Détecte si JPype réel est disponible ou utilise des mocks.
    """
    global _REAL_JPYPE_MODULE, _REAL_JPYPE_AVAILABLE
    global _JPYPE_MODULE_MOCK_OBJ_GLOBAL, _MOCK_DOT_JPYPE_MODULE_GLOBAL
    
    logger.info("Configuration de JPype pour les tests...")
    
    # Essayer de charger JPype réel
    try:
        import jpype
        _REAL_JPYPE_MODULE = jpype
        _REAL_JPYPE_AVAILABLE = True
        logger.info("JPype réel détecté et disponible")
    except ImportError:
        logger.warning("JPype réel non disponible, utilisation des mocks")
        _REAL_JPYPE_AVAILABLE = False
        
        # Créer les mocks JPype
        _create_jpype_mocks()

def _create_jpype_mocks():
    """Crée les objets mock pour JPype."""
    global _JPYPE_MODULE_MOCK_OBJ_GLOBAL, _MOCK_DOT_JPYPE_MODULE_GLOBAL
    
    # Mock pour le module principal jpype
    _JPYPE_MODULE_MOCK_OBJ_GLOBAL = MagicMock(name="jpype_mock")
    _JPYPE_MODULE_MOCK_OBJ_GLOBAL.__path__ = []
    _JPYPE_MODULE_MOCK_OBJ_GLOBAL.__version__ = "1.x.mock"
    
    # Fonctions principales de JPype
    _JPYPE_MODULE_MOCK_OBJ_GLOBAL.isJVMStarted = MagicMock(return_value=False)
    _JPYPE_MODULE_MOCK_OBJ_GLOBAL.startJVM = MagicMock()
    _JPYPE_MODULE_MOCK_OBJ_GLOBAL.getJVMPath = MagicMock(return_value="/mock/jvm/path")
    _JPYPE_MODULE_MOCK_OBJ_GLOBAL.getJVMVersion = MagicMock(return_value="11.0.mock")
    _JPYPE_MODULE_MOCK_OBJ_GLOBAL.getDefaultJVMPath = MagicMock(return_value="/mock/default/jvm")
    
    # Classes principales
    _JPYPE_MODULE_MOCK_OBJ_GLOBAL.JClass = MagicMock()
    _JPYPE_MODULE_MOCK_OBJ_GLOBAL.JException = Exception
    _JPYPE_MODULE_MOCK_OBJ_GLOBAL.JObject = MagicMock()
    _JPYPE_MODULE_MOCK_OBJ_GLOBAL.JVMNotFoundException = Exception
    
    # Types Java
    for java_type in ["JString", "JArray", "JBoolean", "JInt", "JDouble", 
                      "JLong", "JFloat", "JShort", "JByte", "JChar"]:
        setattr(_JPYPE_MODULE_MOCK_OBJ_GLOBAL, java_type, MagicMock(name=f"Mock{java_type}"))
    
    # Modules internes
    _JPYPE_MODULE_MOCK_OBJ_GLOBAL.config = MagicMock()
    _JPYPE_MODULE_MOCK_OBJ_GLOBAL.config.destroy_jvm = True
    _JPYPE_MODULE_MOCK_OBJ_GLOBAL.imports = MagicMock()
    
    # Mock pour _jpype (module C)
    _MOCK_DOT_JPYPE_MODULE_GLOBAL = MagicMock(name="_jpype_mock")
    
    logger.info("Mocks JPype créés avec succès")

def activate_jpype_mock_if_needed():
    """
    Active les mocks JPype dans sys.modules si nécessaire.
    """
    if not _REAL_JPYPE_AVAILABLE and _JPYPE_MODULE_MOCK_OBJ_GLOBAL:
        sys.modules['jpype'] = _JPYPE_MODULE_MOCK_OBJ_GLOBAL
        sys.modules['_jpype'] = _MOCK_DOT_JPYPE_MODULE_GLOBAL
        sys.modules['jpype._core'] = _MOCK_DOT_JPYPE_MODULE_GLOBAL
        sys.modules['jpype.imports'] = _JPYPE_MODULE_MOCK_OBJ_GLOBAL.imports
        sys.modules['jpype.config'] = _JPYPE_MODULE_MOCK_OBJ_GLOBAL.config
        
        # Types
        types_mock = MagicMock(name="jpype.types_mock")
        for java_type in ["JString", "JArray", "JObject", "JBoolean", "JInt", 
                          "JDouble", "JLong", "JFloat", "JShort", "JByte", "JChar"]:
            setattr(types_mock, java_type, getattr(_JPYPE_MODULE_MOCK_OBJ_GLOBAL, java_type))
        sys.modules['jpype.types'] = types_mock
        sys.modules['jpype.JProxy'] = MagicMock(name="jpype.JProxy_mock")
        
        logger.info("Mocks JPype activés dans sys.modules")

def pytest_sessionstart(session):
    """Hook pytest appelé au début de la session de tests."""
    logger.info("Début de la session de tests - initialisation JPype")
    setup_jpype()
    activate_jpype_mock_if_needed()

def pytest_sessionfinish(session, exitstatus):
    """Hook pytest appelé à la fin de la session de tests."""
    logger.info(f"Fin de la session de tests - code de sortie: {exitstatus}")
    
    # Nettoyage si nécessaire
    if _REAL_JPYPE_AVAILABLE and _REAL_JPYPE_MODULE:
        try:
            if hasattr(_REAL_JPYPE_MODULE, 'isJVMStarted') and _REAL_JPYPE_MODULE.isJVMStarted():
                logger.info("Arrêt de la JVM JPype réelle")
                # Note: JPype ne permet généralement pas l'arrêt de la JVM
        except Exception as e:
            logger.warning(f"Erreur lors du nettoyage JPype: {e}")

# Initialiser automatiquement
setup_jpype()