"""
Mock de JPype1 pour la compatibilité avec Python 3.12+.
Ce fichier sert de point d'entrée principal pour le mock JPype,
important les composants spécifiques depuis le package jpype_components.
"""

import sys
import logging
from unittest.mock import MagicMock # Gardé pour _MockInternalJpypeModule si besoin, ou autres mocks directs

# Importer les composants nécessaires depuis le package jpype_components
from tests.mocks.jpype_components.jvm import ( # MODIFIÉ
    isJVMStarted,
    startJVM,
    shutdownJVM,
    getDefaultJVMPath,
    getJVMPath,
    getJVMVersion,
    getClassPath,
    _jvm_started, # Exposer pour _MockInternalJpypeModule
    _jvm_path # Exposer si nécessaire globalement
)
from tests.mocks.jpype_components.config import config # MODIFIÉ
from tests.mocks.jpype_components.imports import imports # MODIFIÉ
from tests.mocks.jpype_components.types import ( # MODIFIÉ
    JString,
    JArray,
    JObject,
    JBoolean,
    JInt,
    JDouble,
    JLong,
    JFloat,
    JShort,
    JByte,
    JChar
)
from tests.mocks.jpype_components.exceptions import JException, JVMNotFoundException # MODIFIÉ
from tests.mocks.jpype_components.jclass_core import MockJClassCore # MODIFIÉ
from tests.mocks.jpype_components import tweety_enums # MODIFIÉ

# Configuration du logging pour le mock principal
mock_logger = logging.getLogger(__name__)
if not mock_logger.hasHandlers():
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('[MOCK JPYPE MAIN LOG] %(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    mock_logger.addHandler(handler)
mock_logger.setLevel(logging.DEBUG)

mock_logger.info("jpype_mock.py (principal) en cours de chargement.")

# Version du mock
__version__ = "1.4.0-mock-refactored"

# --- _MockInternalJpypeModule ---
# Cette classe simule le module `_jpype` interne que `jpype.imports` pourrait utiliser.
# Elle doit rester ici ou être accessible globalement car `sys.modules['jpype._jpype']` est patché.
class _MockInternalJpypeModule:
    def isStarted(self):
        # Utilise la variable _jvm_started importée depuis .jpype_components.jvm
        mock_logger.debug(f"[MOCK jpype._jpype.isStarted()] Appelée. Retourne: {_jvm_started}")
        return _jvm_started

    def getVersion(self):
        return f"Mocked _jpype module (simulated in jpype_mock.py, JVM version: {getJVMVersion()})"

    def isPackage(self, name):
        # Simule la vérification de l'existence d'un package.
        # Retourne True si notre mock considère la JVM comme démarrée.
        mock_logger.debug(f"[MOCK jpype._jpype.isPackage('{name}')] Appelée. _jvm_started: {_jvm_started}. Retourne: {_jvm_started}")
        return _jvm_started

_jpype_internal_module_instance = _MockInternalJpypeModule()
sys.modules['jpype._jpype'] = _jpype_internal_module_instance
mock_logger.info("Instance de _MockInternalJpypeModule injectée dans sys.modules['jpype._jpype'].")


# --- MockJavaNamespace ---
# Simule jpype.java (pour accès comme jpype.java.lang.String)
class MockJavaNamespace:
    def __init__(self, path_prefix=""):
        self._path_prefix = path_prefix
        mock_logger.debug(f"MockJavaNamespace créé pour préfixe: '{path_prefix}'")

    def __getattr__(self, name):
        new_path = f"{self._path_prefix}.{name}" if self._path_prefix else name
        final_segment = new_path.split('.')[-1]

        # Heuristique: si le dernier segment commence par une majuscule, c'est une classe.
        if final_segment and final_segment[0].isupper():
            mock_logger.debug(f"Accès à jpype.java...{new_path}, interprété comme JClass('{new_path}')")
            return JClass(new_path) # Utilise la fonction JClass définie ci-dessous
        else:
            mock_logger.debug(f"Accès à jpype.java...{new_path}, interprété comme sous-namespace")
            return MockJavaNamespace(new_path)

java = MockJavaNamespace("java") # Pour jpype.java.xxx
# Potentiellement d'autres namespaces de haut niveau si nécessaire (org, net, etc.)
# Exemple: org = MockJavaNamespace("org")

# --- Fonction JClass principale ---
# Cette fonction est le point d'entrée pour obtenir des classes Java mockées.
# Elle utilisera MockJClassCore et appliquera des configurations spécifiques.
_jclass_cache = {} # Cache simple pour les instances de MockJClassCore

def JClass(name: str, *args, **kwargs): # Ajout de *args, **kwargs pour ignorer les arguments non supportés comme 'loader'
    """
    Simule jpype.JClass(). Retourne une instance de MockJClassCore configurée.
    """
    mock_logger.info(f"[MOCK JPYPE JClass] Appelée avec name='{name}', args={args}, kwargs={kwargs}") # Log ajouté
    if name in _jclass_cache:
        # mock_logger.debug(f"JClass('{name}') trouvé dans le cache.")
        return _jclass_cache[name]

    mock_logger.debug(f"JClass('{name}') demandé.")

    # Vérifier si c'est une énumération Tweety connue
    if name in tweety_enums.ENUM_MAPPINGS:
        enum_class_mock = tweety_enums.ENUM_MAPPINGS[name]
        # Assurer que les membres de l'enum sont initialisés si ce n'est pas déjà fait
        # Normalement, la métaclasse s'en charge, mais une vérification ici peut être utile.
        # hasattr(enum_class_mock, '_initialize_enum_members') and enum_class_mock._initialize_enum_members()
        # La métaclasse devrait avoir déjà appelé _initialize_enum_members.
        # On s'assure que la classe retournée a bien le jclass_provider si besoin (pas typique pour les enums statiques)
        # et que son __name__ correspond bien au nom Java demandé.
        # Les classes Enum mockées héritent de MockJClassCore, donc elles ont un __name__ et un class_name.
        # Il faut s'assurer que le nom Java est bien celui attendu.
        # Le MOCK_JAVA_CLASS_NAME est utilisé pour cela.
        mock_logger.info(f"JClass('{name}') identifié comme une énumération Tweety. Retourne la classe mockée: {enum_class_mock}.")
        _jclass_cache[name] = enum_class_mock
        return enum_class_mock

    mock_logger.debug(f"JClass('{name}'): Pas une énumération Tweety connue. Création d'une instance de MockJClassCore.")
    # Passer la fonction JClass elle-même pour que MockJClassCore puisse la fournir aux configurateurs.
    core_class_mock = MockJClassCore(name, jclass_provider_func=JClass)

    # La configuration des reasoners et agents est maintenant gérée dans MockJClassCore.__call__
    # via le module tweety_reasoners.
    # Exemple:
    # if name.startswith("org.tweetyproject.arg"):
    #     from .jpype_components import tweety_syntax # ou autre module pertinent
    #     tweety_syntax.configure_tweety_argument_class(core_class_mock)
    # elif name.startswith("org.tweetyproject.logics"):
    #     # ...
    #     pass

    _jclass_cache[name] = core_class_mock
    return core_class_mock


# --- Patchs finaux et exports ---

# Le patch pour jpype.imports._jpype.isStarted est maintenant géré par
# le fait que _MockInternalJpypeModule utilise _jvm_started de jvm.py.

# Le module `imports` (qui est `jpype_components.imports.imports_module`)
# est déjà dans sys.modules['jpype.imports'] grâce à son propre code d'initialisation.
# On s'assure juste qu'il est exposé par ce module principal si on fait `import jpype_mock; jpype_mock.imports`.
# La variable `imports` importée de `.jpype_components.imports` est déjà le module correct.

# Les variables globales _jvm_started et _jvm_path sont gérées dans jvm.py.
# Les fonctions comme isJVMStarted, startJVM, etc., sont importées directement.
# L'instance `config` est importée directement.
# Les types JString, JArray, etc., sont importés directement.
# Les exceptions JException, JVMNotFoundException sont importées directement.

mock_logger.info("Mock JPype1 (jpype_mock.py principal) initialisé et refactorisé.")
mock_logger.info("Les composants sont maintenant dans le package 'jpype_components'.")

# Optionnel: Exposer explicitement ce qui fait partie de l'API publique du mock
# __all__ = [
#     "__version__",
#     "isJVMStarted", "startJVM", "shutdownJVM",
#     "getDefaultJVMPath", "getJVMPath", "getJVMVersion", "getClassPath",
#     "config",
#     "imports",
#     "java", # Pour jpype.java.xxx
#     "JClass", "JString", "JArray", "JObject",
#     "JBoolean", "JInt", "JDouble", "JLong", "JFloat", "JShort", "JByte", "JChar",
#     "JException", "JVMNotFoundException",
#     # Les classes MockJClassCore, MockJavaCollection ne sont pas typiquement accédées directement
#     # par l'utilisateur du mock, mais via JClass() ou des méthodes retournant des collections.
# ]

# Exposer l'instance du mock interne _jpype pour que conftest.py puisse l'importer
_jpype = _jpype_internal_module_instance
_jpype = _jpype_internal_module_instance
