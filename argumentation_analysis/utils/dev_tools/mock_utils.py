#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Utilitaires pour la création de mocks (objets factices) pour le développement et les tests.

Ce module fournit des fonctions pour remplacer des dépendances externes complexes,
comme JPype, par des mocks. Cela permet d'isoler le code à tester et
d'exécuter des tests unitaires ou des portions d'application même lorsque
les dépendances réelles ne sont pas disponibles ou configurées (par exemple,
dans un environnement d'intégration continue sans installation Java).

Conformité:
  - PEP 257 (Docstring Conventions)
  - PEP 8 (Style Guide for Python Code)
"""

import logging
from typing import Optional, Dict
from typing import Optional, Dict, Callable, Any
from unittest import mock
import sys

# Configuration du logger
logger = logging.getLogger(__name__)

def setup_jpype_mock(mock_jvm_path: Optional[str] = None) -> Callable[[], None]:
    """
    Configure et active un mock complet pour le module JPype en l'injectant
    directement dans sys.modules.

    Cette fonction crée un MagicMock pour simuler le module jpype, y attache
    des comportements mockés pour ses fonctions principales, puis place ce
    module mocké dans sys.modules['jpype'].

    :param mock_jvm_path: Le chemin JVM à simuler pour getDefaultJVMPath.
                          Si None, "mock/jvm/path" est utilisé.
    :return: Une fonction de teardown qui, lorsqu'elle est appelée, restaure
             l'état précédent de sys.modules['jpype'].
    """
    logger.info("Activation du mock JPype par injection dans sys.modules...")

    original_jpype_in_sys_modules = sys.modules.get('jpype')
    
    # Créer le mock principal pour le module jpype
    # spec=True aide à attraper les accès à des attributs non mockés.
    # On pourrait utiliser spec=jpype si jpype pouvait être importé sans erreur
    # dans un contexte de setup, mais c'est justement ce qu'on essaie d'éviter.
    mock_jpype_module = mock.MagicMock(name="jpype_module_mock", spec=True)

    # État de la JVM simulée
    jvm_started_state = [False]

    # Fonctions mockées
    def mock_getDefaultJVMPath_func() -> str:
        return mock_jvm_path if mock_jvm_path else "mock/jvm/path"

    def mock_isJVMStarted_func() -> bool:
        return jvm_started_state[0]

    def mock_startJVM_func(*args, **kwargs) -> None:
        path_used = kwargs.get('jvmpath', args[0] if args else mock_getDefaultJVMPath_func())
        logger.info(f"jpype.startJVM (mock) appelé. Chemin (simulé): {path_used}")
        jvm_started_state[0] = True
        # On s'assure que l'attribut config existe et est un mock, car le vrai jpype.config existe
        if not hasattr(mock_jpype_module, 'config'):
            mock_jpype_module.config = mock.MagicMock(name="jpype_config_mock")


    def mock_shutdownJVM_func() -> None:
        logger.info("jpype.shutdownJVM (mock) appelé.")
        jvm_started_state[0] = False

    # Mock pour JPackage
    mock_jpackage_instance = mock.MagicMock(name="JPackage_mock_instance")
    mock_java_pkg = mock.MagicMock(name="java_package_mock")
    mock_lang_pkg = mock.MagicMock(name="lang_package_mock")
    mock_string_cls = mock.MagicMock(name="String_class_mock")
    mock_jpackage_instance.return_value = mock_java_pkg
    mock_java_pkg.lang = mock_lang_pkg
    mock_lang_pkg.String = mock_string_cls
    mock_string_cls.return_value = mock.MagicMock(name="String_instance_mock")

    # Attribuer les fonctions et objets mockés au module jpype mocké
    mock_jpype_module.getDefaultJVMPath = mock.Mock(side_effect=mock_getDefaultJVMPath_func)
    mock_jpype_module.isJVMStarted = mock.Mock(side_effect=mock_isJVMStarted_func)
    mock_jpype_module.startJVM = mock.Mock(side_effect=mock_startJVM_func)
    mock_jpype_module.shutdownJVM = mock.Mock(side_effect=mock_shutdownJVM_func)
    mock_jpype_module.JPackage = mock_jpackage_instance
    
    # Simuler d'autres attributs/exceptions couramment utilisés si nécessaire
    mock_jpype_module.JBoolean = mock.MagicMock(name="JBoolean_mock")
    mock_jpype_module.JString = mock.MagicMock(name="JString_mock")
    mock_jpype_module.JInt = mock.MagicMock(name="JInt_mock")
    # Pour les exceptions, on peut assigner des classes d'exception réelles ou mockées
    mock_jpype_module.JavaException = type('MockJavaException', (Exception,), {})
    if not hasattr(mock_jpype_module, 'config'): # Assurer que config existe
        mock_jpype_module.config = mock.MagicMock(name="jpype_config_mock")


    # Injecter le module mocké dans sys.modules
    sys.modules['jpype'] = mock_jpype_module
    # Assurer que les sous-modules potentiellement problématiques sont aussi mockés s'ils sont accédés
    sys.modules['jpype._core'] = mock.MagicMock(name="jpype_core_mock")
    sys.modules['jpype._jinit'] = mock.MagicMock(name="jpype_jinit_mock", __all__=[])


    logger.info("Mock JPype injecté dans sys.modules.")

    def teardown_jpype_mock():
        logger.info("Restauration de sys.modules['jpype']...")
        if original_jpype_in_sys_modules is not None:
            sys.modules['jpype'] = original_jpype_in_sys_modules
            logger.info("Module JPype original restauré dans sys.modules.")
        else:
            del sys.modules['jpype']
            logger.info("Module JPype mocké supprimé de sys.modules.")
        
        # Nettoyer aussi les sous-modules mockés
        if 'jpype._core' in sys.modules and isinstance(sys.modules['jpype._core'], mock.MagicMock):
            del sys.modules['jpype._core']
        if 'jpype._jinit' in sys.modules and isinstance(sys.modules['jpype._jinit'], mock.MagicMock):
            del sys.modules['jpype._jinit']

    return teardown_jpype_mock

if __name__ == '__main__':
    # Exemple d'utilisation et de test simple
    logging.basicConfig(level=logging.INFO)
    
    # Activer le mock
    teardown_mock = setup_jpype_mock(mock_jvm_path="/custom/mock/jvm")
    
    # Tenter d'utiliser jpype (qui devrait maintenant être mocké)
    try:
        import jpype
        
        print(f"Chemin JVM par défaut (mocké) : {jpype.getDefaultJVMPath()}")
        
        if not jpype.isJVMStarted():
            print("Démarrage de la JVM (mockée)...")
            jpype.startJVM(jpype.getDefaultJVMPath(), "-ea") # Les arguments sont optionnels pour le mock
        
        if jpype.isJVMStarted():
            print("La JVM (mockée) est démarrée.")
            
            # Tester JPackage
            print("Test de JPackage (mocké)...")
            try:
                # Accès simulé à java.lang.String
                JavaLangString = jpype.JPackage("java").lang.String
                print(f"Mock de java.lang.String obtenu : {JavaLangString}")
                
                # Création d'une "instance" (qui sera un autre mock)
                my_string_mock = JavaLangString("test")
                print(f"Instance mockée de String : {my_string_mock}")
                my_string_mock.toString.return_value = "mocked_value" # Configurer le comportement
                print(f"Appel de toString() sur l'instance mockée : {my_string_mock.toString()}")

            except Exception as e_jpackage:
                print(f"Erreur lors du test de JPackage (mocké) : {e_jpackage}")
        
            print("Arrêt de la JVM (mockée)...")
            jpype.shutdownJVM()
            
            if not jpype.isJVMStarted():
                print("La JVM (mockée) est arrêtée.")
        else:
            print("Échec du démarrage de la JVM (mockée).")
            
    except ImportError:
        print("Erreur : JPype n'a pas pu être importé. Le mock a-t-il échoué ?")
    except Exception as e:
        print(f"Une erreur s'est produite lors du test du mock JPype : {e}")
        import traceback
        traceback.print_exc()

    # Optionnel : arrêter les mocks si on a fini
    try:
        teardown_mock()
        print("Mock JPype nettoyé.")
    except Exception as e_teardown:
        print(f"Erreur lors du nettoyage du mock JPype : {e_teardown}")