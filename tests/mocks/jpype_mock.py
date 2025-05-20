"""
Mock pour le module jpype et _jpype.

Ce module fournit des implémentations factices des fonctionnalités de jpype et _jpype
qui sont utilisées dans le projet, permettant d'exécuter les tests sans avoir besoin
d'une JVM réelle.
"""

import sys
from unittest.mock import MagicMock

# Mock pour les classes Java
class JClassMock:
    def __init__(self, class_name):
        self.class_name = class_name
        
    def __call__(self, *args, **kwargs):
        # Retourne une instance mock de la classe Java
        instance = MagicMock()
        instance.__class__.__name__ = self.class_name.split('.')[-1]
        return instance

# Mock pour les exceptions Java
class JExceptionMock(Exception):
    def __init__(self, message="Mock Java Exception"):
        self.message = message
        super().__init__(message)
        
    def getClass(self):
        cls = MagicMock()
        cls.getName.return_value = "org.mockexception.MockException"
        return cls
        
    def getMessage(self):
        return self.message

# Mock pour JObject
def JObjectMock(obj, cls):
    # Toujours retourner True pour les vérifications de type
    return True

# Variables globales pour l'état de la JVM
_jvm_started = False
_jvm_path = "C:/mock/path/to/jvm.dll"
_jvm_version = "11.0.0"

# Fonctions mock pour jpype
def isJVMStarted():
    return _jvm_started

def startJVM(*args, **kwargs):
    global _jvm_started
    _jvm_started = True
    return None

def getJVMPath():
    return _jvm_path

def getJVMVersion():
    return _jvm_version

def getDefaultJVMPath():
    return _jvm_path

# Exception pour JVM non trouvée
class JVMNotFoundException(Exception):
    pass

# Mock pour jpype.imports
class ImportsMock:
    def registerDomain(self, domain, alias=None):
        pass

# Créer l'instance de ImportsMock
imports = ImportsMock()

# Créer les mocks pour les fonctions et classes principales
JClass = JClassMock
JException = JExceptionMock
JObject = JObjectMock

# Mock pour _jpype (module interne)
class _JpypeMock:
    """Mock pour le module interne _jpype."""
    
    def __init__(self):
        # Ajouter ici toutes les fonctionnalités internes de _jpype qui sont utilisées
        pass
    
    # Ajouter des méthodes mock si nécessaire

# Créer l'instance de _JpypeMock
_jpype = _JpypeMock()

# Installer le mock dans sys.modules pour qu'il soit utilisé lors des importations
sys.modules['_jpype'] = _jpype
sys.modules['jpype'] = sys.modules.get('jpype', type('jpype', (), {
    'isJVMStarted': isJVMStarted,
    'startJVM': startJVM,
    'getJVMPath': getJVMPath,
    'getJVMVersion': getJVMVersion,
    'getDefaultJVMPath': getDefaultJVMPath,
    'JClass': JClass,
    'JException': JException,
    'JObject': JObject,
    'JVMNotFoundException': JVMNotFoundException,
    'imports': imports,
}))