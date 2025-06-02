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
from unittest import mock

# Configuration du logger
logger = logging.getLogger(__name__)

def setup_jpype_mock(mock_jvm_path: Optional[str] = None) -> Dict[str, mock.patch]:
    """
    Configure et active un mock complet pour le module JPype.

    Cette fonction remplace les principales fonctionnalités de JPype par des mocks,
    permettant ainsi de simuler le comportement de JPype sans nécessiter
    une installation Java ou une configuration JPype fonctionnelle. C'est
    particulièrement utile pour les tests unitaires ou pour le développement
    dans des environnements isolés.

    Les éléments suivants de JPype sont mockés :
      - `jpype.startJVM`: Simule le démarrage de la JVM.
      - `jpype.shutdownJVM`: Simule l'arrêt de la JVM.
      - `jpype.isJVMStarted`: Simule l'état de la JVM (démarrée/arrêtée).
      - `jpype.JPackage`: Simule l'accès aux packages Java.
      - `jpype.getDefaultJVMPath`: Simule la récupération du chemin de la JVM.

    :param mock_jvm_path: Le chemin du fichier JVM à retourner par le mock de
                          `jpype.getDefaultJVMPath()`. Si `None`, une valeur
                          par défaut ("mock/jvm/path") sera utilisée.
    :type mock_jvm_path: Optional[str]
    :return: Un dictionnaire contenant les objets patch actifs, avec leurs noms
             comme clés (ex: "startJVM", "JPackage"). Cela permet d'arrêter
             les mocks individuellement si nécessaire.
    :rtype: Dict[str, mock.patch]
    :raises ImportError: Si le module `jpype` ne peut pas être importé au moment
                         où les patches sont appliqués (ce qui serait inattendu
                         car le but est de le mocker).
    :raises Exception: Diverses exceptions peuvent survenir si la configuration
                       des mocks échoue pour une raison imprévue.
    """
    logger.info("Activation du mock pour JPype...")

    # Mock de jpype.getDefaultJVMPath
    mock_get_default_jvm_path = mock.Mock(return_value=mock_jvm_path if mock_jvm_path else "mock/jvm/path")
    
    # Mock de jpype.isJVMStarted
    # Utilisation d'une liste pour `jvm_started_state` afin de permettre sa modification
    # par les fonctions imbriquées `mock_is_jvm_started`, `mock_start_jvm`, et `mock_shutdown_jvm`.
    # En Python, les types non mutables (comme les booléens) ne peuvent pas être
    # réassignés directement dans une portée interne si la variable est définie
    # dans une portée externe, à moins d'utiliser `nonlocal` (Python 3+).
    # Une liste est un objet mutable, donc ses éléments peuvent être modifiés.
    jvm_started_state = [False]  # État initial: JVM non démarrée

    def mock_is_jvm_started() -> bool:
        """Simule jpype.isJVMStarted()."""
        return jvm_started_state[0]

    def mock_start_jvm(*args, **kwargs) -> None:
        """Simule jpype.startJVM()."""
        logger.info("jpype.startJVM (mock) appelé.")
        jvm_started_state[0] = True
        # Simuler le retour de getDefaultJVMPath si nécessaire dans startJVM
        if "jvmpath" not in kwargs and mock_jvm_path is None:
            kwargs["jvmpath"] = mock_get_default_jvm_path()
            logger.info(f"Utilisation du chemin JVM mocké par défaut : {kwargs['jvmpath']}")
        elif "jvmpath" not in kwargs and mock_jvm_path is not None:
             kwargs["jvmpath"] = mock_jvm_path
             logger.info(f"Utilisation du chemin JVM mocké fourni : {kwargs['jvmpath']}")


        logger.info("jpype.startJVM (mock) appelé.")
        jvm_started_state[0] = True
        # Simuler le retour de getDefaultJVMPath si nécessaire dans startJVM
        if "jvmpath" not in kwargs and mock_jvm_path is None:
            kwargs["jvmpath"] = mock_get_default_jvm_path()
            logger.info(f"Utilisation du chemin JVM mocké par défaut : {kwargs['jvmpath']}")
        elif "jvmpath" not in kwargs and mock_jvm_path is not None:
             kwargs["jvmpath"] = mock_jvm_path
             logger.info(f"Utilisation du chemin JVM mocké fourni : {kwargs['jvmpath']}")

    def mock_shutdown_jvm() -> None:
        """Simule jpype.shutdownJVM()."""
        logger.info("jpype.shutdownJVM (mock) appelé.")
        jvm_started_state[0] = False

    # Mock de jpype.JPackage
    # Crée un MagicMock qui peut simuler l'accès à des packages et classes Java.
    # Par exemple, jpype.JPackage("java").lang.String pourrait être simulé.
    # MagicMock est flexible et retournera d'autres MagicMocks pour les attributs
    # et appels non explicitement configurés, ce qui est idéal pour simuler des API.
    mock_jpackage_instance = mock.MagicMock(name="JPackage_mock_instance")

    # Configuration spécifique pour simuler une structure de package commune (java.lang.String)
    # Cela permet aux tests d'utiliser jpype.JPackage('java').lang.String sans erreur.
    mock_java_pkg = mock.MagicMock(name="java_package_mock")
    mock_lang_pkg = mock.MagicMock(name="lang_package_mock")
    mock_string_cls = mock.MagicMock(name="String_class_mock")

    # Lorsque JPackage est appelé (ex: jpype.JPackage('java')), il retourne mock_java_pkg
    mock_jpackage_instance.return_value = mock_java_pkg
    # L'accès à .lang sur mock_java_pkg retourne mock_lang_pkg
    mock_java_pkg.lang = mock_lang_pkg
    # L'accès à .String sur mock_lang_pkg retourne mock_string_cls
    mock_lang_pkg.String = mock_string_cls
    # On peut même simuler la création d'une instance de String
    mock_string_cls.return_value = mock.MagicMock(name="String_instance_mock")


    # Appliquer les patches
    # Il est crucial de patcher 'jpype' dans le module où il est importé et utilisé.
    # Si jpype est importé directement (import jpype), alors 'jpype' est le bon target.
    # Si c'est 'from jpype import ...', il faut cibler spécifiquement.
    # Pour une couverture générale, on patche 'jpype' au niveau global.
    # Les modules qui importent 'jpype' par la suite utiliseront la version mockée
    # qui se trouve dans sys.modules.
    
    # On mocke les fonctions individuellement pour plus de contrôle et de clarté.
    # `mock.patch` remplace temporairement l'objet cible par un mock.
    # `side_effect` permet d'appeler notre propre fonction mock lorsque l'original est appelé.
    patch_start_jvm = mock.patch('jpype.startJVM', side_effect=mock_start_jvm)
    patch_shutdown_jvm = mock.patch('jpype.shutdownJVM', side_effect=mock_shutdown_jvm)
    patch_is_jvm_started = mock.patch('jpype.isJVMStarted', side_effect=mock_is_jvm_started)
    # Pour JPackage, on assigne directement notre instance MagicMock configurée.
    patch_jpackage = mock.patch('jpype.JPackage', mock_jpackage_instance)
    patch_get_default_jvm_path = mock.patch('jpype.getDefaultJVMPath', mock_get_default_jvm_path)

    # Démarrer les patches. Ils doivent être arrêtés explicitement si le mock
    # n'est plus nécessaire (généralement avec `patch_obj.stop()` dans un `tearDown`
    # ou un bloc `finally` pour les tests). Pour un script de setup global,
    # on les laisse actifs pendant toute la durée de vie du processus.
    try:
        patch_start_jvm.start()
        patch_shutdown_jvm.start()
        patch_is_jvm_started.start()
        patch_jpackage.start()
        patch_get_default_jvm_path.start()
    except Exception as e:
        logger.error(f"Erreur lors du démarrage des patches JPype : {e}")
        # Si le démarrage des patches échoue, il est préférable de lever l'exception
        # pour signaler un problème critique dans la configuration du mock.
        raise

    # Vérification que les mocks sont bien en place.
    # Cette étape est cruciale pour s'assurer que le patching a fonctionné comme prévu.
    try:
        import jpype # Tenter d'importer jpype (devrait être la version mockée)
        
        # Vérifier que chaque attribut attendu de jpype est maintenant un objet mock.
        # isinstance(obj, mock.Mock) est une vérification générale.
        # MagicMock hérite de Mock, donc cela couvre aussi mock_jpackage_instance.
        if not (isinstance(jpype.startJVM, mock.Mock) and
                isinstance(jpype.shutdownJVM, mock.Mock) and
                isinstance(jpype.isJVMStarted, mock.Mock) and
                isinstance(jpype.JPackage, mock.MagicMock) and # JPackage est notre MagicMock
                isinstance(jpype.getDefaultJVMPath, mock.Mock)):
            logger.warning(
                "Certains mocks JPype n'ont pas pu être appliqués correctement. "
                "Les fonctionnalités dépendant de JPype pourraient ne pas se comporter comme prévu."
            )
        else:
            logger.info("Le mock JPype est correctement configuré et actif.")
            
    except ImportError:
        # Cela ne devrait pas arriver si jpype est listé comme dépendance (même optionnelle)
        # ou si le but est de le mocker complètement sans l'installer.
        # Cependant, si le patching lui-même dépend d'une structure de module jpype
        # qui n'existe pas du tout, cela pourrait échouer.
        logger.error(
            "Le module JPype n'a pas pu être importé après la tentative de mock. "
            "Assurez-vous que la structure de patching cible ('jpype.quelquechose') "
            "est valide ou que le module 'jpype' est au moins simulable."
        )
        # Lever l'exception peut être approprié ici car le mock n'est pas fonctionnel.
        raise
    except Exception as e:
        logger.error(f"Erreur inattendue lors de la vérification des mocks JPype : {e}")
        raise

    # Retourner les objets patch pour permettre un contrôle externe (ex: arrêt dans les tests)
    return {
        "startJVM": patch_start_jvm,
        "shutdownJVM": patch_shutdown_jvm,
        "isJVMStarted": patch_is_jvm_started,
        "JPackage": patch_jpackage,
        "getDefaultJVMPath": patch_get_default_jvm_path,
    }

if __name__ == '__main__':
    # Exemple d'utilisation et de test simple
    logging.basicConfig(level=logging.INFO)
    
    # Activer le mock
    active_mocks = setup_jpype_mock(mock_jvm_path="/custom/mock/jvm")
    
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

    # Optionnel : arrêter les mocks si on a fini (plus pertinent dans un contexte de test unitaire)
    # for patch_name, patch_obj in active_mocks.items():
    #     try:
    #         patch_obj.stop()
    #         print(f"Mock pour {patch_name} arrêté.")
    #     except Exception as e_stop:
    #         print(f"Erreur lors de l'arrêt du mock {patch_name}: {e_stop}")
    # print("Tous les mocks JPype ont été arrêtés.")