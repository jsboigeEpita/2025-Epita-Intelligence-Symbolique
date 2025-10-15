import sys
import os
import pytest
from unittest.mock import MagicMock
import importlib.util
from argumentation_analysis.core.jvm_setup import shutdown_jvm  # MODIFIED
import logging

# --- Configuration du Logger ---
logger = logging.getLogger(__name__)
# Configuration basique si le logger n'est pas déjà configuré par pytest ou autre
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)  # Ou logging.DEBUG pour plus de détails
    logger.propagate = False

# --- Détermination de la disponibilité du vrai JPype via variable d'environnement ---
# Cette variable est utilisée par les décorateurs skipif dans les fichiers de test.
logger.info(f"jpype_setup.py: Évaluation de _REAL_JPYPE_AVAILABLE...")
logger.info(
    f"jpype_setup.py: Valeur brute de os.environ.get('USE_REAL_JPYPE', 'false'): '{os.environ.get('USE_REAL_JPYPE', 'false')}'"
)
_REAL_JPYPE_AVAILABLE = os.environ.get("USE_REAL_JPYPE", "false").lower() in (
    "true",
    "1",
)
logger.info(f"jpype_setup.py: _REAL_JPYPE_AVAILABLE évalué à: {_REAL_JPYPE_AVAILABLE}")
# Les prints de débogage précédents ont confirmé que _REAL_JPYPE_AVAILABLE est correctement évalué.
# La cause du skip était une erreur dans la fixture integration_jvm (chemin des libs).


# --- Sauvegarde du module JPype potentiellement pré-importé ou import frais ---
_REAL_JPYPE_MODULE = None
_PRE_EXISTING_JPYPE_IN_SYS_MODULES = sys.modules.get("jpype")

if _PRE_EXISTING_JPYPE_IN_SYS_MODULES:
    _REAL_JPYPE_MODULE = _PRE_EXISTING_JPYPE_IN_SYS_MODULES
    logger.info(
        f"jpype_setup.py: _REAL_JPYPE_MODULE initialisé à partir de _PRE_EXISTING_JPYPE_IN_SYS_MODULES (ID: {id(_REAL_JPYPE_MODULE)})."
    )
else:
    logger.info("jpype_setup.py: JPype non préchargé, tentative d'import frais.")
    try:
        import jpype as r_jpype_fresh_import

        _REAL_JPYPE_MODULE = r_jpype_fresh_import
        logger.info(
            f"jpype_setup.py: Vrai module JPype importé fraîchement (ID: {id(_REAL_JPYPE_MODULE)})."
        )
    except ImportError as e_fresh_import:
        logger.warning(
            f"jpype_setup.py: Le vrai module JPype n'a pas pu être importé fraîchement: {e_fresh_import}"
        )
        _REAL_JPYPE_MODULE = None
    except NameError as e_name_error_fresh_import:
        logger.error(
            f"jpype_setup.py: NameError lors de l'import frais de JPype: {e_name_error_fresh_import}."
        )
        _REAL_JPYPE_MODULE = None

if _REAL_JPYPE_MODULE is None:
    logger.error(
        "jpype_setup.py: _REAL_JPYPE_MODULE EST NONE après la tentative d'initialisation."
    )
else:
    logger.info(
        f"jpype_setup.py: _REAL_JPYPE_MODULE est initialisé (ID: {id(_REAL_JPYPE_MODULE)}) avant la définition des fixtures."
    )

# --- Mock JPype ---
try:
    from tests.mocks import jpype_mock  # Importer le module via son chemin de package

    # Importer le vrai module mock d'imports depuis le sous-package jpype_components
    from tests.mocks.jpype_components.imports import (
        imports_module as actual_mock_jpype_imports_module,
    )

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
    jpype_module_mock_obj.__version__ = (
        "1.4.1.mock"  # ou jpype_mock.__version__ si défini
    )
    jpype_module_mock_obj.imports = actual_mock_jpype_imports_module
    _JPYPE_MODULE_MOCK_OBJ_GLOBAL = jpype_module_mock_obj
    _MOCK_DOT_JPYPE_MODULE_GLOBAL = (
        jpype_mock._jpype
    )  # Accéder à _jpype depuis le module jpype_mock importé
    logger.info("jpype_setup.py: Mock JPype préparé.")
except ImportError as e_jpype:
    logger.error(
        f"jpype_setup.py: ERREUR CRITIQUE lors de l'import de jpype_mock ou ses composants: {e_jpype}. Utilisation de mocks de fallback pour JPype."
    )
    _fb_jpype_mock = MagicMock(name="jpype_fallback_mock")
    _fb_jpype_mock.imports = MagicMock(name="jpype.imports_fallback_mock")
    _fb_dot_jpype_mock = MagicMock(name="_jpype_fallback_mock")

    _JPYPE_MODULE_MOCK_OBJ_GLOBAL = _fb_jpype_mock
    _MOCK_DOT_JPYPE_MODULE_GLOBAL = _fb_dot_jpype_mock
    logger.info(
        "jpype_setup.py: Mock JPype de FALLBACK préparé et assigné aux variables globales de mock."
    )


# Simplification radicale: Pour l'instant, on force le mock.
# La fixture autouse=True est supprimée pour éviter le patching/dépatching constant.
# Le patching sera fait une seule fois dans pytest_sessionstart.
def activate_jpype_mock_if_needed(request):
    pass  # Remplacé par le hook sessionstart


def pytest_sessionstart(session):
    """Applique le mock JPype pour toute la session de test."""
    global _JPYPE_MODULE_MOCK_OBJ_GLOBAL, _MOCK_DOT_JPYPE_MODULE_GLOBAL, logger
    logger.info(
        "jpype_setup.py: pytest_sessionstart: Application globale du mock JPype."
    )

    # Appliquer les mocks à sys.modules
    sys.modules["jpype"] = _JPYPE_MODULE_MOCK_OBJ_GLOBAL
    sys.modules["_jpype"] = _MOCK_DOT_JPYPE_MODULE_GLOBAL
    sys.modules["jpype._core"] = _MOCK_DOT_JPYPE_MODULE_GLOBAL  # Assurer la cohérence

    # Mocker les sous-modules importants
    if hasattr(_JPYPE_MODULE_MOCK_OBJ_GLOBAL, "imports"):
        sys.modules["jpype.imports"] = _JPYPE_MODULE_MOCK_OBJ_GLOBAL.imports

    _JPYPE_MODULE_MOCK_OBJ_GLOBAL.config = MagicMock(
        name="jpype.config_mock_from_sessionstart"
    )
    _JPYPE_MODULE_MOCK_OBJ_GLOBAL.config.destroy_jvm = True
    sys.modules["jpype.config"] = _JPYPE_MODULE_MOCK_OBJ_GLOBAL.config

    _mock_types_module = MagicMock(name="jpype.types_mock_from_sessionstart")
    for type_name in [
        "JString",
        "JArray",
        "JObject",
        "JBoolean",
        "JInt",
        "JDouble",
        "JLong",
        "JFloat",
        "JShort",
        "JByte",
        "JChar",
    ]:
        setattr(
            _mock_types_module,
            type_name,
            getattr(jpype_mock, type_name, MagicMock(name=f"Mock{type_name}")),
        )
    sys.modules["jpype.types"] = _mock_types_module
    sys.modules["jpype.JProxy"] = MagicMock(name="jpype.JProxy_mock_from_sessionstart")

    logger.info("Mock JPype globalement appliqué via sys.modules.")


def pytest_sessionfinish(session, exitstatus):
    pass  # Le nettoyage est maintenant géré par la fixture activate_jpype_mock_globally
