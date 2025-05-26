#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Mock pour JPype pour les tests.
Ce mock permet d'exécuter les tests sans avoir besoin d'installer JPype.
"""

import logging
import sys
from typing import Any, Dict, List, Optional, Union, Callable

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("JPypeMock")

# Variables globales
_jvm_started = False
_jvm_path = None
_jvm_options = []
_class_cache = {}

# Exceptions
class JVMNotFoundException(Exception):
    """Exception levée quand la JVM n'est pas trouvée."""
    pass

class JException(Exception):
    """Exception Java."""
    
    def __init__(self, message="Java Exception", *args):
        super().__init__(message, *args)
        self.message = message
        self.args = args
        # Ajouter les attributs manquants pour la compatibilité
        self.stacktrace = None
        self.cause = None
    
    def getMessage(self):
        """Retourne le message de l'exception."""
        return self.message
    
    def toString(self):
        """Retourne la représentation string de l'exception."""
        return f"JException: {self.message}"
    
    def getClass(self):
        """Retourne la classe de l'exception."""
        class MockClass:
            def getName(self):
                return "org.mockexception.MockException"
        return MockClass()

class JObject:
    """Mock pour les objets Java."""
    
    def __init__(self, obj, cls=None):
        self._obj = obj
        self._class = cls
    
    def __getattr__(self, name):
        """Simule l'accès aux attributs et méthodes Java."""
        if name.startswith('_'):
            return super().__getattribute__(name)
        
        def method(*args, **kwargs):
            logger.debug(f"Appel de la méthode {name} avec args={args}, kwargs={kwargs}")
            return None
        
        return method
    
    def __str__(self):
        return f"JObject({self._obj})"
    
    def __repr__(self):
        return self.__str__()

class JClass:
    """Mock pour les classes Java."""
    
    def __init__(self, class_name):
        self._class_name = class_name
        self._methods = {}
        self._fields = {}
        
        # Ajouter quelques méthodes et champs communs
        self._methods["toString"] = lambda: class_name
        self._fields["class"] = self
        
        # Ajouter l'attribut class_name pour la compatibilité
        self.class_name = class_name
    
    def __call__(self, *args, **kwargs):
        """Simule la création d'une instance de la classe."""
        logger.debug(f"Création d'une instance de {self._class_name} avec args={args}, kwargs={kwargs}")
        return JObject(None, self)
    
    def __getattr__(self, name):
        """Simule l'accès aux méthodes et champs statiques."""
        # Vérifier d'abord les attributs spéciaux
        if name == "class_name":
            return self._class_name
            
        if name in self._methods:
            return self._methods[name]
        
        if name in self._fields:
            return self._fields[name]
        
        # Méthode par défaut
        def static_method(*args, **kwargs):
            logger.debug(f"Appel de la méthode statique {name} avec args={args}, kwargs={kwargs}")
            return None
        
        return static_method
    
    def __str__(self):
        return f"JClass({self._class_name})"
    
    def __repr__(self):
        return self.__str__()

# Fonctions principales
def isJVMStarted() -> bool:
    """Vérifie si la JVM est démarrée."""
    return _jvm_started

def getJVMPath() -> str:
    """Retourne le chemin de la JVM."""
    if not _jvm_path:
        raise JVMNotFoundException("JVM path not set")
    return _jvm_path

def getDefaultJVMPath() -> str:
    """Retourne le chemin par défaut de la JVM."""
    return "/path/to/mock/jvm"

def getJVMVersion() -> str:
    """Retourne la version de la JVM."""
    return "Mock JVM 1.8.0"

def startJVM(jvmpath: Optional[str] = None, *args, **kwargs) -> None:
    """Démarre la JVM."""
    global _jvm_started, _jvm_path, _jvm_options
    
    if _jvm_started:
        logger.warning("JVM already started")
        return
    
    _jvm_started = True
    _jvm_path = jvmpath or getDefaultJVMPath()
    _jvm_options = list(args)
    
    # Traiter les arguments nommés courants
    classpath = kwargs.get('classpath', kwargs.get('-Djava.class.path', ''))
    if classpath:
        _jvm_options.append(f'-Djava.class.path={classpath}')
    
    # Traiter d'autres options JVM courantes
    for key, value in kwargs.items():
        if key.startswith('-D') or key.startswith('-X'):
            _jvm_options.append(f'{key}={value}' if value else key)
    
    logger.info(f"Mock JVM started with path: {_jvm_path}")
    logger.info(f"JVM options: {_jvm_options}")

def imports(package_or_class: str) -> Any:
    """Importe un package ou une classe Java."""
    if not _jvm_started:
        raise RuntimeError("JVM not started")
    
    if package_or_class in _class_cache:
        return _class_cache[package_or_class]
    
    if package_or_class.endswith(".*"):
        # C'est un package
        package = package_or_class[:-2]
        logger.debug(f"Importing package: {package}")
        return None
    else:
        # C'est une classe
        logger.debug(f"Importing class: {package_or_class}")
        cls = JClass(package_or_class)
        _class_cache[package_or_class] = cls
        return cls

# Module _jpype pour la compatibilité
class _JClass:
    """Classe interne pour la compatibilité avec _jpype."""
    pass

class _JObject:
    """Classe interne pour la compatibilité avec _jpype."""
    pass

class _JException:
    """Classe interne pour la compatibilité avec _jpype."""
    pass

class _JArray:
    """Classe interne pour la compatibilité avec _jpype."""
    pass

# Module _jpype
_jpype = type('_jpype', (), {
    '_jclass': _JClass,
    '_jobject': _JObject,
    '_jexception': _JException,
    '_jarray': _JArray
})

# Log de chargement
logger.info("Module jpype_mock chargé")