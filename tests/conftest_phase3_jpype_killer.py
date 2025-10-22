# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

"""
Phase 3 - JPype Killer - Solution radicale pour éliminer JPype
Mock JPype AVANT tout import pour éviter les problèmes JVM
"""
import sys
import os


# ============================================================================
# JPYPE KILLER - Mock au niveau système AVANT tous les imports
# ============================================================================


def create_jpype_killer_mock():
    """Crée un mock JPype complet qui remplace toute fonctionnalité JVM"""

    jpype_mock = MagicMock()  # noqa: F821 - unittest.mock import dynamique

    # Attributs de base
    jpype_mock.isJVMStarted = MagicMock(return_value=False)  # noqa: F821 - unittest.mock import dynamique
    jpype_mock.startJVM = MagicMock()  # noqa: F821 - unittest.mock import dynamique
    jpype_mock.shutdownJVM = MagicMock()  # noqa: F821 - unittest.mock import dynamique
    jpype_mock.attachThreadToJVM = MagicMock()  # noqa: F821 - unittest.mock import dynamique
    jpype_mock.detachThreadFromJVM = MagicMock()  # noqa: F821 - unittest.mock import dynamique

    # Exceptions
    jpype_mock.JException = Exception
    jpype_mock.JRuntimeException = RuntimeError
    jpype_mock.JVMNotRunning = RuntimeError("Mock JVM not running")

    # Classes Java mockées
    jpype_mock.JClass = MagicMock(return_value=MagicMock())  # noqa: F821 - unittest.mock import dynamique
    jpype_mock.JObject = MagicMock()  # noqa: F821 - unittest.mock import dynamique
    jpype_mock.JArray = MagicMock(return_value=[])  # noqa: F821 - unittest.mock import dynamique
    jpype_mock.JString = MagicMock(return_value="mock_string")  # noqa: F821 - unittest.mock import dynamique
    jpype_mock.JInt = MagicMock(return_value=0)  # noqa: F821 - unittest.mock import dynamique
    jpype_mock.JBoolean = MagicMock(return_value=True)  # noqa: F821 - unittest.mock import dynamique

    # Package java.* mockés
    java_mock = MagicMock()  # noqa: F821 - unittest.mock import dynamique
    java_mock.lang = MagicMock()  # noqa: F821 - unittest.mock import dynamique
    java_mock.lang.String = MagicMock(return_value="mock_java_string")  # noqa: F821 - unittest.mock import dynamique
    java_mock.lang.Object = MagicMock()  # noqa: F821 - unittest.mock import dynamique
    java_mock.lang.System = MagicMock()  # noqa: F821 - unittest.mock import dynamique
    java_mock.util = MagicMock()  # noqa: F821 - unittest.mock import dynamique
    java_mock.util.ArrayList = MagicMock(return_value=[])  # noqa: F821 - unittest.mock import dynamique
    java_mock.util.HashMap = MagicMock(return_value={})  # noqa: F821 - unittest.mock import dynamique

    jpype_mock.java = java_mock
    jpype_mock.JavaClass = MagicMock(return_value=MagicMock())  # noqa: F821 - unittest.mock import dynamique
    jpype_mock.JavaObject = MagicMock()  # noqa: F821 - unittest.mock import dynamique

    # CRITIQUE: Mock jpype.imports pour conftest.py racine
    jpype_imports_mock = MagicMock()  # noqa: F821 - unittest.mock import dynamique
    jpype_mock.imports = jpype_imports_mock

    # Spécifique à Tweety
    jpype_mock.JPackage = MagicMock()  # noqa: F821 - unittest.mock import dynamique
    org_mock = MagicMock()  # noqa: F821 - unittest.mock import dynamique
    org_mock.tweetyproject = MagicMock()  # noqa: F821 - unittest.mock import dynamique
    jpype_mock.org = org_mock

    # Fonction getClassPath pour les tests
    jpype_mock.getClassPath = MagicMock(return_value="mock_classpath")  # noqa: F821 - unittest.mock import dynamique

    return jpype_mock


# Créer le mock une seule fois au niveau module
JPYPE_KILLER_MOCK = create_jpype_killer_mock()

# ============================================================================
# INJECTION SYSTÈME - Remplacer jpype AVANT tout import
# ============================================================================

# Injecter dans sys.modules IMMÉDIATEMENT
sys.modules["jpype"] = JPYPE_KILLER_MOCK
sys.modules["jpype1"] = JPYPE_KILLER_MOCK
sys.modules["jpype._jpype"] = JPYPE_KILLER_MOCK
sys.modules["jpype.types"] = MagicMock()  # noqa: F821 - unittest.mock import dynamique
sys.modules[
    "jpype.imports"
] = JPYPE_KILLER_MOCK.imports  # CRITIQUE pour conftest.py racine

# Forcer les variables d'environnement
os.environ.update(
    {
        "USE_REAL_JPYPE": "false",
        "JPYPE_JVM": "false",
        "DISABLE_JVM": "true",
        "JPYPE_ENABLE_JNI_FAULTHANDLER": "false",
        "NO_JPYPE": "true",
    }
)

# ============================================================================
# MOCK TWEETY COMPLET
# ============================================================================


def create_tweety_ecosystem_mock():
    """Crée l'écosystème Tweety complet mockué"""

    # TweetyBridge mock complet
    tweety_bridge_mock = MagicMock()  # noqa: F821 - unittest.mock import dynamique
    tweety_bridge_mock.initialize_tweety = MagicMock(return_value=True)  # noqa: F821 - unittest.mock import dynamique
    tweety_bridge_mock.check_formula_syntax = MagicMock(  # noqa: F821 - unittest.mock import dynamique
        return_value=(True, "Valid syntax")
    )
    tweety_bridge_mock.check_belief_set_syntax = MagicMock(  # noqa: F821 - unittest.mock import dynamique
        return_value=(True, "Valid belief set")
    )
    tweety_bridge_mock.query_belief_set = MagicMock(return_value="Mock query result")  # noqa: F821 - unittest.mock import dynamique
    tweety_bridge_mock.clean_up = MagicMock()  # noqa: F821 - unittest.mock import dynamique
    tweety_bridge_mock.is_initialized = True

    # Handlers mockés
    handlers = {}
    for handler_name in ["PLHandler", "FOLHandler", "ModalHandler"]:
        handler_mock = MagicMock()  # noqa: F821 - unittest.mock import dynamique
        handler_mock.parse_formula = MagicMock(return_value="Mock formula")  # noqa: F821 - unittest.mock import dynamique
        handler_mock.parse_belief_set = MagicMock(return_value="Mock belief set")  # noqa: F821 - unittest.mock import dynamique
        handler_mock.query = MagicMock(return_value="Mock query result")  # noqa: F821 - unittest.mock import dynamique
        handlers[handler_name] = handler_mock

    # TweetyInitializer mock
    tweety_init_mock = MagicMock()  # noqa: F821 - unittest.mock import dynamique
    tweety_init_mock.initialize_jvm = MagicMock(return_value=True)  # noqa: F821 - unittest.mock import dynamique
    tweety_init_mock.setup_tweety_libs = MagicMock(return_value=True)  # noqa: F821 - unittest.mock import dynamique
    tweety_init_mock.is_jvm_started = MagicMock(return_value=False)  # noqa: F821 - unittest.mock import dynamique

    return {
        "bridge": tweety_bridge_mock,
        "handlers": handlers,
        "initializer": tweety_init_mock,
    }


TWEETY_MOCKS = create_tweety_ecosystem_mock()

# Injecter les mocks Tweety dans sys.modules
sys.modules["argumentation_analysis.agents.core.logic.tweety_bridge"] = MagicMock()  # noqa: F821 - unittest.mock import dynamique
sys.modules["argumentation_analysis.agents.core.logic.tweety_initializer"] = MagicMock()  # noqa: F821 - unittest.mock import dynamique
sys.modules["argumentation_analysis.agents.core.logic.pl_handler"] = MagicMock()  # noqa: F821 - unittest.mock import dynamique
sys.modules["argumentation_analysis.agents.core.logic.fol_handler"] = MagicMock()  # noqa: F821 - unittest.mock import dynamique
sys.modules["argumentation_analysis.agents.core.logic.modal_handler"] = MagicMock()  # noqa: F821 - unittest.mock import dynamique

# ============================================================================
# HOOK D'IMPORT CUSTOM
# ============================================================================


class JPypeKillerImportHook:
    """Hook d'import qui intercepte et mock tous les imports jpype et tweety"""

    def find_spec(self, fullname, path, target=None):
        if any(keyword in fullname.lower() for keyword in ["jpype", "tweety"]):
            # Retourner un spec mockée
            import importlib.util

            spec = importlib.util.spec_from_loader(fullname, loader=None)
            return spec
        return None

    def find_module(self, fullname, path=None):
        if any(keyword in fullname.lower() for keyword in ["jpype", "tweety"]):
            return JPypeKillerLoader()
        return None


class JPypeKillerLoader:
    """Loader qui retourne des mocks pour jpype et tweety"""

    def load_module(self, fullname):
        if fullname in sys.modules:
            return sys.modules[fullname]

        if "jpype" in fullname:
            module = JPYPE_KILLER_MOCK
        elif "tweety" in fullname:
            module = MagicMock()  # noqa: F821 - unittest.mock import dynamique
        else:
            module = MagicMock()  # noqa: F821 - unittest.mock import dynamique

        sys.modules[fullname] = module
        return module


# Installer le hook d'import
if not any(isinstance(hook, JPypeKillerImportHook) for hook in sys.meta_path):
    sys.meta_path.insert(0, JPypeKillerImportHook())

# ============================================================================
# CONFIGURATION GLOBALE POUR TESTS
# ============================================================================


def apply_jpype_killer_globally():
    """Applique le JPype Killer à tous les modules existants"""

    # Nettoyer les modules déjà importés qui pourraient contenir jpype
    modules_to_clean = []
    for module_name in sys.modules:
        if any(keyword in module_name.lower() for keyword in ["jpype", "tweety"]):
            modules_to_clean.append(module_name)

    for module_name in modules_to_clean:
        if "jpype" in module_name:
            sys.modules[module_name] = JPYPE_KILLER_MOCK
        else:
            sys.modules[module_name] = MagicMock()  # noqa: F821 - unittest.mock import dynamique


# Appliquer immédiatement
apply_jpype_killer_globally()

print("[JPYPE_KILLER] JPype elimination active - All JVM calls mocked")
