"""
Mock de JPype1 pour la compatibilité avec Python 3.12+.

Ce mock simule les fonctionnalités essentielles de JPype1 utilisées par le projet.
"""

import sys
import os
from unittest.mock import MagicMock

# Version du mock
__version__ = "1.4.0-mock"

# Variables globales pour simuler l'état de la JVM
_jvm_started = False
_jvm_path = None

def isJVMStarted():
    """Simule jpype.isJVMStarted()."""
    return _jvm_started

def startJVM(jvmpath=None, *args, **kwargs):
    """Simule jpype.startJVM()."""
    global _jvm_started, _jvm_path
    _jvm_started = True
    _jvm_path = jvmpath or getDefaultJVMPath()
    print(f"[MOCK] JVM démarrée avec le chemin: {_jvm_path}")

def shutdownJVM():
    """Simule jpype.shutdownJVM()."""
    global _jvm_started
    print("[MOCK DEBUG] Avant opérations dans shutdownJVM:")
    jpype_module = sys.modules.get('jpype')
    print(f"[MOCK DEBUG] sys.modules.get('jpype'): {jpype_module}")
    print(f"[MOCK DEBUG] getattr(jpype_module, '__file__', 'N/A'): {getattr(jpype_module, '__file__', 'N/A')}")
    print(f"[MOCK DEBUG] hasattr(jpype_module, 'config'): {hasattr(jpype_module, 'config')}")
    has_core = hasattr(jpype_module, '_core')
    print(f"[MOCK DEBUG] hasattr(jpype_module, '_core'): {has_core}")
    if has_core and jpype_module._core is not None: # Vérifier aussi que _core n'est pas None
        print(f"[MOCK DEBUG] hasattr(jpype_module._core, '_JTerminate'): {hasattr(jpype_module._core, '_JTerminate')}")
    elif has_core and jpype_module._core is None:
        print(f"[MOCK DEBUG] jpype_module._core est None.")
    
    _jvm_started = False
    print("[MOCK] JVM arrêtée")
    
    print("[MOCK DEBUG] Après opérations dans shutdownJVM (état similaire attendu):")
    jpype_module_after = sys.modules.get('jpype')
    print(f"[MOCK DEBUG] sys.modules.get('jpype'): {jpype_module_after}")
    print(f"[MOCK DEBUG] getattr(jpype_module_after, '__file__', 'N/A'): {getattr(jpype_module_after, '__file__', 'N/A')}")
    print(f"[MOCK DEBUG] hasattr(jpype_module_after, 'config'): {hasattr(jpype_module_after, 'config')}")
    has_core_after = hasattr(jpype_module_after, '_core')
    print(f"[MOCK DEBUG] hasattr(jpype_module_after, '_core'): {has_core_after}")
    if has_core_after and jpype_module_after._core is not None:
        print(f"[MOCK DEBUG] hasattr(jpype_module_after._core, '_JTerminate'): {hasattr(jpype_module_after._core, '_JTerminate')}")
    elif has_core_after and jpype_module_after._core is None:
        print(f"[MOCK DEBUG] jpype_module_after._core est None.")

def getDefaultJVMPath():
    """Simule jpype.getDefaultJVMPath()."""
    # Retourner un chemin par défaut basé sur l'OS
    if sys.platform == "win32":
        return "C:\\Program Files\\Java\\jdk-11\\bin\\server\\jvm.dll"
    elif sys.platform == "darwin":
        return "/Library/Java/JavaVirtualMachines/jdk-11.jdk/Contents/Home/lib/server/libjvm.dylib"
    else:
        return "/usr/lib/jvm/java-11-openjdk/lib/server/libjvm.so"

def getJVMPath():
    """Simule jpype.getJVMPath()."""
    return _jvm_path or getDefaultJVMPath()

def getJVMVersion():
    """Simule jpype.getJVMVersion()."""
    # Retourne un tuple similaire à celui de JPype: (version_string, major, minor, patch)
    return ("Mock JVM Version 1.0 (Java 11 compatible)", 11, 0, 0)

class MockJClass:
    """Mock pour JClass avec attributs spécifiques."""
    def __init__(self, name):
        self.__name__ = name
        self.class_name = name
        
    def __call__(self, *args, **kwargs):
        return MagicMock()

def JClass(name):
    """Simule jpype.JClass()."""
    return MockJClass(name)

def JArray(type_):
    """Simule jpype.JArray()."""
    return MagicMock()

def JString(value):
    """Simule jpype.JString()."""
    return str(value)

# Classes Java simulées
class JObject:
    """Simule jpype.JObject."""
    pass

class JException(Exception):
    """Simule jpype.JException."""
    def __init__(self, message="Mock Java Exception"):
        super().__init__(message)
        self.message = message
    
    def getClass(self):
        """Simule la méthode getClass() de Java."""
        class MockClass:
            def getName(self):
                return "org.mockexception.MockException"
        return MockClass()
    
    def getMessage(self):
        """Simule la méthode getMessage() de Java."""
        return self.message

config = MagicMock() # Ajout pour simuler jpype.config

# Installer le mock dans sys.modules
sys.modules['jpype1'] = sys.modules[__name__]
sys.modules['jpype'] = sys.modules[__name__]

print("[MOCK] Mock JPype1 activé pour la compatibilité Python 3.12+")
