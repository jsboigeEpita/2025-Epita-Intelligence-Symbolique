#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module de compatibilité entre JPype et PyJNIus.
Ce module permet d'utiliser les mêmes interfaces que JPype avec PyJNIus.
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
logger = logging.getLogger("JPypeToPyJNIus")

# Vérifier si JPype est disponible
try:
    import jpype
    import jpype.imports
    HAS_JPYPE = True
    logger.info("JPype est disponible, utilisation de JPype")
except ImportError:
    HAS_JPYPE = False
    logger.info("JPype n'est pas disponible, utilisation du mock")

# Vérifier si PyJNIus est disponible
try:
    import jnius
    HAS_PYJNIUS = True
    logger.info("PyJNIus est disponible, utilisation de PyJNIus")
except ImportError:
    HAS_PYJNIUS = False
    logger.info("PyJNIus n'est pas disponible, utilisation du mock")

# Importer le mock si nécessaire
if not HAS_JPYPE and not HAS_PYJNIUS:
    try:
        from tests.mocks.jpype_mock import (
            isJVMStarted, startJVM, getJVMPath, getJVMVersion, getDefaultJVMPath,
            JClass, JException, JObject, JVMNotFoundException, imports, _jpype
        )
        logger.info("Mock JPype importé avec succès")
    except ImportError:
        logger.error("Impossible d'importer le mock JPype")
        raise

# Fonctions de compatibilité
def is_jvm_started() -> bool:
    """Vérifie si la JVM est démarrée."""
    if HAS_JPYPE:
        return jpype.isJVMStarted()
    elif HAS_PYJNIUS:
        return jnius.autoclass('java.lang.System') is not None
    else:
        return isJVMStarted()

def start_jvm(jvmpath: str, *args, **kwargs) -> None:
    """Démarre la JVM."""
    if HAS_JPYPE:
        if not jpype.isJVMStarted():
            jpype.startJVM(jvmpath, *args, **kwargs)
            jpype.imports.registerDomain("java")
    elif HAS_PYJNIUS:
        # PyJNIus démarre automatiquement la JVM lors de l'importation
        pass
    else:
        startJVM(jvmpath, *args, **kwargs)

def get_jvm_path() -> str:
    """Retourne le chemin de la JVM."""
    if HAS_JPYPE:
        return jpype.getJVMPath()
    elif HAS_PYJNIUS:
        return "PyJNIus JVM path"
    else:
        return getJVMPath()

def get_default_jvm_path() -> str:
    """Retourne le chemin par défaut de la JVM."""
    if HAS_JPYPE:
        return jpype.getDefaultJVMPath()
    elif HAS_PYJNIUS:
        return "PyJNIus default JVM path"
    else:
        return getDefaultJVMPath()

def get_jvm_version() -> str:
    """Retourne la version de la JVM."""
    if HAS_JPYPE:
        return jpype.getJVMVersion()
    elif HAS_PYJNIUS:
        if is_jvm_started():
            System = jnius.autoclass('java.lang.System')
            return System.getProperty('java.version')
        return "Unknown"
    else:
        return getJVMVersion()

def get_class(class_name: str) -> Any:
    """Retourne une classe Java."""
    if HAS_JPYPE:
        return jpype.JClass(class_name)
    elif HAS_PYJNIUS:
        return jnius.autoclass(class_name)
    else:
        return JClass(class_name)

def import_java_package(package_name: str) -> None:
    """Importe un package Java."""
    if HAS_JPYPE:
        jpype.imports.registerDomain(package_name)
    elif HAS_PYJNIUS:
        # PyJNIus n'a pas d'équivalent direct
        pass
    else:
        imports(package_name)

# Alias pour la compatibilité
JClass = get_class
isJVMStarted = is_jvm_started
startJVM = start_jvm
getJVMPath = get_jvm_path
getDefaultJVMPath = get_default_jvm_path
getJVMVersion = get_jvm_version

# Log de chargement
logger.info("Module jpype_to_pyjnius chargé")
