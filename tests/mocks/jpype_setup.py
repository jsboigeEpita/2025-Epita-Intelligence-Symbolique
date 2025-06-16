# tests/mocks/jpype_setup.py
"""
Ce module fournit des fixtures pytest pour gérer le cycle de vie de JPype
et de la JVM, permettant de basculer entre un mock complet et la vraie bibliothèque.
"""

import sys
import os
import pytest
from unittest.mock import MagicMock, patch
import importlib.util
from argumentation_analysis.core.jvm_setup import shutdown_jvm_if_needed, start_jvm_if_needed, is_jvm_started
import logging

# Configuration du logging
logger = logging.getLogger(__name__)

# --- Configuration Globale ---

_use_real_jpype = os.environ.get('USE_REAL_JPYPE', 'false').lower() in ('true', '1')
_jpype_mock = None
_jpype_patcher = None

# --- Sauvegarde du module JPype potentiellement pré-importé ou import frais ---
_REAL_JPYPE_MODULE = None
_PRE_EXISTING_JPYPE_IN_SYS_MODULES = sys.modules.get('jpype')

if _PRE_EXISTING_JPYPE_IN_SYS_MODULES:
    _REAL_JPYPE_MODULE = _PRE_EXISTING_JPYPE_IN_SYS_MODULES
    logger.info(f"jpype_setup.py: _REAL_JPYPE_MODULE initialisé à partir de _PRE_EXISTING_JPYPE_IN_SYS_MODULES (ID: {id(_REAL_JPYPE_MODULE)}).")
else:
    logger.info("jpype_setup.py: JPype non préchargé, tentative d'import frais.")
    try:
        import jpype as r_jpype_fresh_import
        _REAL_JPYPE_MODULE = r_jpype_fresh_import
        logger.info(f"jpype_setup.py: Vrai module JPype importé fraîchement (ID: {id(_REAL_JPYPE_MODULE)}).")
    except ImportError as e_fresh_import:
        logger.warning(f"jpype_setup.py: Le vrai module JPype n'a pas pu être importé fraîchement: {e_fresh_import}")
        _REAL_JPYPE_MODULE = None
    except NameError as e_name_error_fresh_import:
        logger.error(f"jpype_setup.py: NameError lors de l'import frais de JPype: {e_name_error_fresh_import}.")
        _REAL_JPYPE_MODULE = None

if _REAL_JPYPE_MODULE is None:
    logger.error("jpype_setup.py: _REAL_JPYPE_MODULE EST NONE après la tentative d'initialisation.")
else:
    logger.info(f"jpype_setup.py: _REAL_JPYPE_MODULE est initialisé (ID: {id(_REAL_JPYPE_MODULE)}) avant la définition des fixtures.")
# Initialisation des globales pour les objets mock, au cas où ils ne seraient pas créés
_JPYPE_MODULE_MOCK_OBJ_GLOBAL = None
_MOCK_DOT_JPYPE_MODULE_GLOBAL = None

# --- Mock JPype ---
_REAL_JPYPE_AVAILABLE = _REAL_JPYPE_MODULE is not None

if not _REAL_JPYPE_AVAILABLE:
    try:
        import jpype_mock # Importer le module directement
        # Importer le vrai module mock d'imports depuis le sous-package jpype_components
        from jpype_components.imports import imports as actual_mock_jpype_imports_module

        jpype_module_mock_obj = MagicMock(name="jpype_module_mock")
        jpype_module_mock_obj.__path__ = []
        jpype_module_mock_obj.isJVMStarted = jpype_mock.isJVMStarted
        jpype_module_mock_obj.startJVM = jpype_mock.startJVM
        jpype_module_mock_obj.getJVMPath = jpype_mock.getJVMPath
        jpype_module_mock_obj.getJVMVersion = jpype_mock.getJVMVersion
        jpype_module_mock_obj.getDefaultJVMPath = jpype_mock.getDefaultJVMPath
        jpype_module_mock_obj.JClass = jpype_mock.JClass
        jpype_module_mock_obj.JException = jpype_mock.JException
        jpype_module_mock_obj.JObject = jpype_mock.JObject
        jpype_module_mock_obj.JVMNotFoundException = jpype_mock.JVMNotFoundException
        jpype_module_mock_obj.__version__ = '1.4.1.mock' # ou jpype_mock.__version__ si défini
        jpype_module_mock_obj.imports = actual_mock_jpype_imports_module
        _JPYPE_MODULE_MOCK_OBJ_GLOBAL = jpype_module_mock_obj
        _MOCK_DOT_JPYPE_MODULE_GLOBAL = jpype_mock._jpype # Accéder à _jpype depuis le module jpype_mock importé
        logger.info("jpype_setup.py: Mock JPype préparé.")
    except ImportError as e_jpype:
        logger.error(f"jpype_setup.py: ERREUR CRITIQUE lors de l'import de jpype_mock ou ses composants: {e_jpype}. Utilisation de mocks de fallback pour JPype.")
        _fb_jpype_mock = MagicMock(name="jpype_fallback_mock")
        _fb_jpype_mock.imports = MagicMock(name="jpype.imports_fallback_mock")
        _fb_dot_jpype_mock = MagicMock(name="_jpype_fallback_mock")

        _JPYPE_MODULE_MOCK_OBJ_GLOBAL = _fb_jpype_mock
        _MOCK_DOT_JPYPE_MODULE_GLOBAL = _fb_dot_jpype_mock
        logger.info("jpype_setup.py: Mock JPype de FALLBACK préparé et assigné aux variables globales de mock.")


@pytest.fixture(scope="function", autouse=True)
def activate_jpype_mock_if_needed(request):
    global _JPYPE_MODULE_MOCK_OBJ_GLOBAL, _MOCK_DOT_JPYPE_MODULE_GLOBAL, _REAL_JPYPE_MODULE

    # Déterminer si le vrai JPype doit être utilisé
    env_use_real_jpype = os.environ.get('USE_REAL_JPYPE', 'false').lower() in ('true', '1')
    
    use_real_jpype_marker = False
    if request.node.get_closest_marker("real_jpype"):
        use_real_jpype_marker = True
        
    use_real_jpype_path = False
    path_str = str(request.node.fspath).replace(os.sep, '/')
    if 'tests/integration/' in path_str or 'tests/minimal_jpype_tweety_tests/' in path_str:
        use_real_jpype_path = True
        
    final_use_real_jpype = False
    if env_use_real_jpype:
        final_use_real_jpype = True
        logger.info(f"Test {request.node.name}: REAL JPype forcé par la variable d'environnement USE_REAL_JPYPE.")
    elif use_real_jpype_marker:
        final_use_real_jpype = True
        logger.info(f"Test {request.node.name}: REAL JPype demandé par le marqueur 'real_jpype'.")
    elif use_real_jpype_path:
        final_use_real_jpype = True
        logger.info(f"Test {request.node.name}: REAL JPype activé par chemin ({path_str}).")
    # else: final_use_real_jpype reste False

    if final_use_real_jpype:
        logger.info(f"Test {request.node.name} demande REAL JPype. Configuration de sys.modules pour utiliser le vrai JPype.")
        if _REAL_JPYPE_MODULE:
            sys.modules['jpype'] = _REAL_JPYPE_MODULE
            if hasattr(_REAL_JPYPE_MODULE, '_jpype'):
                sys.modules['_jpype'] = _REAL_JPYPE_MODULE._jpype
            elif '_jpype' in sys.modules and sys.modules.get('_jpype') is not getattr(_REAL_JPYPE_MODULE, '_jpype', None) :
                del sys.modules['_jpype']
            if hasattr(_REAL_JPYPE_MODULE, 'imports'):
                sys.modules['jpype.imports'] = _REAL_JPYPE_MODULE.imports
            elif 'jpype.imports' in sys.modules and sys.modules.get('jpype.imports') is not getattr(_REAL_JPYPE_MODULE, 'imports', None):
                del sys.modules['jpype.imports']
            logger.debug(f"REAL JPype (ID: {id(_REAL_JPYPE_MODULE)}) est maintenant sys.modules['jpype'].")
        else:
            logger.error(f"Test {request.node.name} demande REAL JPype, mais _REAL_JPYPE_MODULE n'est pas disponible. Test échouera probablement.")
        yield
    else:
        logger.info(f"Test {request.node.name} utilise MOCK JPype.")
        try:
            jpype_components_jvm_module = sys.modules.get('tests.mocks.jpype_components.jvm')
            if jpype_components_jvm_module:
                if hasattr(jpype_components_jvm_module, '_jvm_started'):
                    jpype_components_jvm_module._jvm_started = False
                if hasattr(jpype_components_jvm_module, '_jvm_path'):
                    jpype_components_jvm_module._jvm_path = None
                if hasattr(_JPYPE_MODULE_MOCK_OBJ_GLOBAL, 'config') and hasattr(_JPYPE_MODULE_MOCK_OBJ_GLOBAL.config, 'jvm_path'):
                    _JPYPE_MODULE_MOCK_OBJ_GLOBAL.config.jvm_path = None
                logger.info("État (_jvm_started, _jvm_path, config.jvm_path) du mock JPype réinitialisé pour le test.")
            else:
                logger.warning("Impossible de réinitialiser l'état du mock JPype: module 'tests.mocks.jpype_components.jvm' non trouvé.")
        except Exception as e_reset_mock:
            logger.error(f"Erreur lors de la réinitialisation de l'état du mock JPype: {e_reset_mock}")

        original_modules = {}
        modules_to_handle = ['jpype', '_jpype', 'jpype._core', 'jpype.imports', 'jpype.types', 'jpype.config', 'jpype.JProxy']

        if 'jpype.imports' in sys.modules and \
           hasattr(sys.modules['jpype.imports'], '_jpype') and \
           _MOCK_DOT_JPYPE_MODULE_GLOBAL is not None and \
           hasattr(_MOCK_DOT_JPYPE_MODULE_GLOBAL, 'isStarted'):
            if sys.modules['jpype.imports']._jpype is not _MOCK_DOT_JPYPE_MODULE_GLOBAL:
                if 'jpype.imports._jpype_original' not in original_modules:
                     original_modules['jpype.imports._jpype_original'] = sys.modules['jpype.imports']._jpype
                logger.debug(f"Patch direct de sys.modules['jpype.imports']._jpype avec notre mock _jpype.")
                sys.modules['jpype.imports']._jpype = _MOCK_DOT_JPYPE_MODULE_GLOBAL
            else:
                logger.debug("sys.modules['jpype.imports']._jpype est déjà notre mock.")

        for module_name in modules_to_handle:
            if module_name in sys.modules:
                is_current_module_our_mock = False
                if module_name == 'jpype' and sys.modules[module_name] is _JPYPE_MODULE_MOCK_OBJ_GLOBAL: is_current_module_our_mock = True
                elif module_name in ['_jpype', 'jpype._core'] and sys.modules[module_name] is _MOCK_DOT_JPYPE_MODULE_GLOBAL: is_current_module_our_mock = True
                elif module_name == 'jpype.imports' and hasattr(_JPYPE_MODULE_MOCK_OBJ_GLOBAL, 'imports') and sys.modules[module_name] is _JPYPE_MODULE_MOCK_OBJ_GLOBAL.imports: is_current_module_our_mock = True
                elif module_name == 'jpype.config' and hasattr(_JPYPE_MODULE_MOCK_OBJ_GLOBAL, 'config') and sys.modules[module_name] is _JPYPE_MODULE_MOCK_OBJ_GLOBAL.config: is_current_module_our_mock = True

                if not is_current_module_our_mock and module_name not in original_modules:
                    original_modules[module_name] = sys.modules.pop(module_name)
                    logger.debug(f"Supprimé et sauvegardé sys.modules['{module_name}']")
                elif module_name in sys.modules and is_current_module_our_mock:
                    del sys.modules[module_name]
                    logger.debug(f"Supprimé notre mock préexistant pour sys.modules['{module_name}'].")
                elif module_name in sys.modules:
                    del sys.modules[module_name]
                    logger.debug(f"Supprimé sys.modules['{module_name}'] (sauvegarde prioritaire existante).")

        sys.modules['jpype'] = _JPYPE_MODULE_MOCK_OBJ_GLOBAL
        sys.modules['_jpype'] = _MOCK_DOT_JPYPE_MODULE_GLOBAL
        sys.modules['jpype._core'] = _MOCK_DOT_JPYPE_MODULE_GLOBAL
        if hasattr(_JPYPE_MODULE_MOCK_OBJ_GLOBAL, 'imports'):
            sys.modules['jpype.imports'] = _JPYPE_MODULE_MOCK_OBJ_GLOBAL.imports
        else:
            sys.modules['jpype.imports'] = MagicMock(name="jpype.imports_fallback_in_fixture")

        if hasattr(_JPYPE_MODULE_MOCK_OBJ_GLOBAL, 'config'):
            sys.modules['jpype.config'] = _JPYPE_MODULE_MOCK_OBJ_GLOBAL.config
        else:
            sys.modules['jpype.config'] = MagicMock(name="jpype.config_fallback_in_fixture")

        mock_types_module = MagicMock(name="jpype.types_mock_module_dynamic_in_fixture")
        for type_name in ["JString", "JArray", "JObject", "JBoolean", "JInt", "JDouble", "JLong", "JFloat", "JShort", "JByte", "JChar"]:
            if hasattr(_JPYPE_MODULE_MOCK_OBJ_GLOBAL, type_name):
                setattr(mock_types_module, type_name, getattr(_JPYPE_MODULE_MOCK_OBJ_GLOBAL, type_name))
            else:
                setattr(mock_types_module, type_name, MagicMock(name=f"Mock{type_name}_in_fixture"))
        sys.modules['jpype.types'] = mock_types_module

        sys.modules['jpype.JProxy'] = MagicMock(name="jpype.JProxy_mock_module_dynamic_in_fixture")
        logger.debug(f"Mocks JPype (principal, _jpype/_core, imports, config, types, JProxy) mis en place.")
        yield
        logger.debug(f"Nettoyage après test {request.node.name} (utilisation du mock).")

        if 'jpype.imports._jpype_original' in original_modules:
            if 'jpype.imports' in sys.modules and hasattr(sys.modules['jpype.imports'], '_jpype'):
                sys.modules['jpype.imports']._jpype = original_modules['jpype.imports._jpype_original']
                logger.debug("Restauré jpype.imports._jpype à sa valeur originale.")
            del original_modules['jpype.imports._jpype_original']

        modules_we_set_up_in_fixture = ['jpype', '_jpype', 'jpype._core', 'jpype.imports', 'jpype.config', 'jpype.types', 'jpype.JProxy']
        for module_name in modules_we_set_up_in_fixture:
            current_module_in_sys = sys.modules.get(module_name)
            is_our_specific_mock_from_fixture = False
            if module_name == 'jpype' and current_module_in_sys is _JPYPE_MODULE_MOCK_OBJ_GLOBAL: is_our_specific_mock_from_fixture = True
            elif module_name in ['_jpype', 'jpype._core'] and current_module_in_sys is _MOCK_DOT_JPYPE_MODULE_GLOBAL: is_our_specific_mock_from_fixture = True
            elif module_name == 'jpype.imports' and hasattr(_JPYPE_MODULE_MOCK_OBJ_GLOBAL, 'imports') and current_module_in_sys is _JPYPE_MODULE_MOCK_OBJ_GLOBAL.imports: is_our_specific_mock_from_fixture = True
            elif module_name == 'jpype.config' and hasattr(_JPYPE_MODULE_MOCK_OBJ_GLOBAL, 'config') and current_module_in_sys is _JPYPE_MODULE_MOCK_OBJ_GLOBAL.config: is_our_specific_mock_from_fixture = True
            elif module_name == 'jpype.types' and current_module_in_sys is mock_types_module: is_our_specific_mock_from_fixture = True
            elif module_name == 'jpype.JProxy' and isinstance(current_module_in_sys, MagicMock) and hasattr(current_module_in_sys, 'name') and "jpype.JProxy_mock_module_dynamic_in_fixture" in current_module_in_sys.name : is_our_specific_mock_from_fixture = True

            if is_our_specific_mock_from_fixture:
                if module_name in sys.modules:
                    del sys.modules[module_name]
                    logger.debug(f"Supprimé notre mock pour sys.modules['{module_name}']")

        for module_name, original_module in original_modules.items():
            sys.modules[module_name] = original_module
            logger.debug(f"Restauré sys.modules['{module_name}'] à {original_module}")

        logger.info(f"État de JPype restauré après test {request.node.name} (utilisation du mock).")