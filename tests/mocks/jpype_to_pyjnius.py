#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module mock pour rediriger JPype1 vers pyjnius.
Ce module est utilisé pour la compatibilité avec Python 3.12.
"""

import sys
import logging
import importlib.util

logger = logging.getLogger(__name__)

try:
    import jnius
    
    # Créer un module jpype qui redirige vers jnius
    class JPypeModule:
        def __init__(self):
            self.jnius = jnius
            
        def __getattr__(self, name):
            if name == 'startJVM':
                # pyjnius initialise la JVM automatiquement
                return lambda *args, **kwargs: None
            elif name == 'shutdownJVM':
                # pyjnius gère l'arrêt de la JVM automatiquement
                return lambda: None
            elif name == 'JClass':
                return lambda class_name: jnius.autoclass(class_name)
            elif name == 'JArray':
                return jnius.array
            elif name == 'java':
                # Créer un proxy pour jpype.java
                class JavaPackage:
                    def __getattr__(self, name):
                        if name == 'lang':
                            # Créer un proxy pour jpype.java.lang
                            class LangPackage:
                                def __getattr__(self, name):
                                    return jnius.autoclass(f"java.lang.{name}")
                            return LangPackage()
                        return jnius.autoclass(f"java.{name}")
                return JavaPackage()
            else:
                try:
                    return getattr(jnius, name)
                except AttributeError:
                    logger.warning(f"Attribut {name} non trouvé dans jnius")
                    # Retourner une fonction qui ne fait rien
                    return lambda *args, **kwargs: None
    
    # Installer le module mock
    sys.modules['jpype'] = JPypeModule()
    sys.modules['jpype.types'] = JPypeModule()
    sys.modules['jpype.imports'] = JPypeModule()
    
    logger.info("Module mock JPype1 installé avec succès (redirection vers pyjnius)")
    
except ImportError:
    logger.error("Impossible d'importer jnius. Veuillez installer pyjnius.")
    raise
