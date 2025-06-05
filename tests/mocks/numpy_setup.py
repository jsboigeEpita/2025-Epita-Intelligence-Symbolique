import sys
from unittest.mock import MagicMock
import pytest
import importlib # Ajouté pour numpy_mock si besoin d'import dynamique
import logging # Ajout pour la fonction helper
from types import ModuleType # Ajouté pour créer des objets modules

# Configuration du logger pour ce module si pas déjà fait globalement
# Ceci est un exemple, adaptez selon la configuration de logging du projet.
# Si un logger est déjà configuré au niveau racine et propagé, ceci n'est pas nécessaire.
logger = logging.getLogger(__name__)
# Pour s'assurer que les messages INFO de la fonction helper sont visibles pendant le test:
# if not logger.handlers: # Décommentez et ajustez si les logs ne s'affichent pas comme attendu
#     handler = logging.StreamHandler(sys.stdout)
#     handler.setFormatter(logging.Formatter('%(levelname)s:%(name)s:%(message)s'))
#     logger.addHandler(handler)
#     logger.setLevel(logging.INFO)


# DÉBUT : Fonction helper à ajouter
def deep_delete_from_sys_modules(module_name_prefix, logger_instance):
    keys_to_delete = [k for k in sys.modules if k == module_name_prefix or k.startswith(module_name_prefix + '.')]
    if keys_to_delete:
        logger_instance.info(f"Nettoyage des modules sys pour préfixe '{module_name_prefix}': {keys_to_delete}")
    for key in keys_to_delete:
        try:
            del sys.modules[key]
        except KeyError:
            logger_instance.warning(f"Clé '{key}' non trouvée dans sys.modules lors de la tentative de suppression (deep_delete).")
# FIN : Fonction helper


# Tentative d'importation de numpy_mock. S'il est dans le même répertoire (tests/mocks), cela devrait fonctionner.
try:
    from tests.mocks import legacy_numpy_array_mock # MODIFIÉ: Import absolu
except ImportError:
    print("ERREUR: numpy_setup.py: Impossible d'importer legacy_numpy_array_mock via 'from tests.mocks'.")
    numpy_mock = MagicMock(name="numpy_mock_fallback_in_numpy_setup")
    numpy_mock.typing = MagicMock()
    numpy_mock._core = MagicMock() 
    numpy_mock.core = MagicMock()  
    numpy_mock.linalg = MagicMock()
    numpy_mock.fft = MagicMock()
    numpy_mock.lib = MagicMock()
    numpy_mock.__version__ = '1.24.3.mock_fallback'
    if hasattr(numpy_mock._core, 'multiarray'): # Pourrait être redondant si core est bien mocké
        numpy_mock._core.multiarray = MagicMock()
    if hasattr(numpy_mock.core, 'multiarray'):
        numpy_mock.core.multiarray = MagicMock()
    if hasattr(numpy_mock.core, 'numeric'):
        numpy_mock.core.numeric = MagicMock()
    if hasattr(numpy_mock._core, 'numeric'):
        numpy_mock._core.numeric = MagicMock()


class MockRecarray:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        shape_arg = kwargs.get('shape')
        if shape_arg is not None:
            self.shape = shape_arg
        elif args and isinstance(args[0], tuple): 
             self.shape = args[0]
        elif args and args[0] is not None: 
             self.shape = (args[0],)
        else:
             self.shape = (0,) 
        self.dtype = MagicMock(name="recarray_dtype_mock")
        names_arg = kwargs.get('names')
        self.dtype.names = list(names_arg) if names_arg is not None else []
        self._formats = kwargs.get('formats') 

    @property
    def names(self):
        return self.dtype.names

    @property
    def formats(self):
        return self._formats

    def __getattr__(self, name):
        if name == 'names': 
            return self.dtype.names
        if name == 'formats': 
            return self._formats
        if name in self.kwargs.get('names', []):
            field_mock = MagicMock(name=f"MockRecarray.field.{name}")
            return field_mock
        if name in ['shape', 'dtype', 'args', 'kwargs']:
            return object.__getattribute__(self, name)
        return MagicMock(name=f"MockRecarray.unhandled.{name}")

    def __getitem__(self, key):
        if isinstance(key, str) and key in self.kwargs.get('names', []):
            field_mock = MagicMock(name=f"MockRecarray.field_getitem.{key}")
            field_mock.__getitem__ = lambda idx: MagicMock(name=f"MockRecarray.field_getitem.{key}.item_{idx}")
            return field_mock
        elif isinstance(key, int):
            row_mock = MagicMock(name=f"MockRecarray.row_{key}")
            def get_field_from_row(field_name):
                if field_name in self.kwargs.get('names', []):
                    return MagicMock(name=f"MockRecarray.row_{key}.field_{field_name}")
                raise KeyError(field_name)
            row_mock.__getitem__ = get_field_from_row
            return row_mock
        return MagicMock(name=f"MockRecarray.getitem.{key}")

def _install_numpy_mock_immediately():
    logger.info("numpy_setup.py: _install_numpy_mock_immediately: Installation du mock NumPy.")
    try:
        # S'assurer que legacy_numpy_array_mock est importé
        if 'legacy_numpy_array_mock' not in globals() or globals()['legacy_numpy_array_mock'] is None: # Vérifier aussi si None à cause du try/except global
            try:
                from tests.mocks import legacy_numpy_array_mock as legacy_numpy_array_mock_module # MODIFIÉ: Import absolu
                # Rendre accessible globalement dans ce module si ce n'est pas déjà le cas
                globals()['legacy_numpy_array_mock'] = legacy_numpy_array_mock_module
                logger.info("legacy_numpy_array_mock importé avec succès dans _install_numpy_mock_immediately.")
            except ImportError as e_direct_import:
                logger.error(f"Échec de l'import de tests.mocks.legacy_numpy_array_mock dans _install_numpy_mock_immediately: {e_direct_import}")
                # Fallback sur le MagicMock si l'import échoue ici aussi, pour éviter des erreurs en aval
                legacy_numpy_array_mock_module = MagicMock(name="legacy_numpy_array_mock_fallback_in_install_func")
                legacy_numpy_array_mock_module.__path__ = [] # Nécessaire pour être traité comme un package
                legacy_numpy_array_mock_module.rec = MagicMock(name="rec_fallback")
                legacy_numpy_array_mock_module.rec.recarray = MagicMock(name="recarray_fallback")
                legacy_numpy_array_mock_module.typing = MagicMock(name="typing_fallback")
                legacy_numpy_array_mock_module.core = MagicMock(name="core_fallback")
                legacy_numpy_array_mock_module._core = MagicMock(name="_core_fallback")
                legacy_numpy_array_mock_module.linalg = MagicMock(name="linalg_fallback")
                legacy_numpy_array_mock_module.fft = MagicMock(name="fft_fallback")
                legacy_numpy_array_mock_module.lib = MagicMock(name="lib_fallback")
                legacy_numpy_array_mock_module.random = MagicMock(name="random_fallback")
                globals()['legacy_numpy_array_mock'] = legacy_numpy_array_mock_module # S'assurer qu'il est dans globals
        else:
            legacy_numpy_array_mock_module = globals()['legacy_numpy_array_mock']
            logger.info("legacy_numpy_array_mock déjà présent dans globals() pour _install_numpy_mock_immediately.")

        # 1. Créer le module principal mock 'numpy'
        # On utilise directement le module legacy_numpy_array_mock comme base pour sys.modules['numpy']
        # car il contient déjà la plupart des attributs nécessaires.
        # Il faut s'assurer qu'il a __path__ pour être traité comme un package.
        if not hasattr(legacy_numpy_array_mock_module, '__path__'):
            legacy_numpy_array_mock_module.__path__ = [] # Indispensable pour que 'import numpy.submodule' fonctionne
        
        sys.modules['numpy'] = legacy_numpy_array_mock_module
        logger.info(f"NumpyMock: sys.modules['numpy'] est maintenant legacy_numpy_array_mock (ID: {id(legacy_numpy_array_mock_module)}). __path__ = {legacy_numpy_array_mock_module.__path__}")

        # 2. Configurer numpy.rec
        # legacy_numpy_array_mock.rec est déjà une instance de _NumPy_Rec_Mock configurée avec __name__, __package__, __path__
        if hasattr(legacy_numpy_array_mock_module, 'rec'):
            numpy_rec_mock_instance = legacy_numpy_array_mock_module.rec
            sys.modules['numpy.rec'] = numpy_rec_mock_instance
            # Assurer que le module 'numpy' a aussi 'rec' comme attribut pointant vers ce module mock
            setattr(sys.modules['numpy'], 'rec', numpy_rec_mock_instance)
            logger.info(f"NumpyMock: numpy.rec configuré. sys.modules['numpy.rec'] (ID: {id(numpy_rec_mock_instance)}), type: {type(numpy_rec_mock_instance)}")
            if hasattr(numpy_rec_mock_instance, 'recarray'):
                 logger.info(f"NumpyMock: numpy.rec.recarray est disponible (type: {type(numpy_rec_mock_instance.recarray)}).")
            else:
                 logger.warning("NumpyMock: numpy.rec.recarray NON disponible sur l'instance mock de rec.")
        else:
            logger.error("NumpyMock: legacy_numpy_array_mock n'a pas d'attribut 'rec' pour configurer numpy.rec.")

        # 3. Configurer numpy.typing
        if hasattr(legacy_numpy_array_mock_module, 'typing'):
            # legacy_numpy_array_mock.typing est une CLASSE. Nous devons créer un objet module.
            numpy_typing_module_obj = ModuleType('numpy.typing')
            numpy_typing_module_obj.__package__ = 'numpy'
            numpy_typing_module_obj.__path__ = []
            
            # Copier les attributs de la classe mock 'typing' vers l'objet module
            # (NDArray, ArrayLike, etc. devraient être des attributs de classe de legacy_numpy_array_mock.typing)
            typing_class_mock = legacy_numpy_array_mock_module.typing
            for attr_name in dir(typing_class_mock):
                if not attr_name.startswith('__'):
                    setattr(numpy_typing_module_obj, attr_name, getattr(typing_class_mock, attr_name))
            
            sys.modules['numpy.typing'] = numpy_typing_module_obj
            setattr(sys.modules['numpy'], 'typing', numpy_typing_module_obj)
            logger.info(f"NumpyMock: numpy.typing configuré. sys.modules['numpy.typing'] (ID: {id(numpy_typing_module_obj)}).")
            if hasattr(numpy_typing_module_obj, 'NDArray'):
                 logger.info(f"NumpyMock: numpy.typing.NDArray est disponible.")
            else:
                 logger.warning("NumpyMock: numpy.typing.NDArray NON disponible sur le module mock de typing.")
        else:
            logger.error("NumpyMock: legacy_numpy_array_mock n'a pas d'attribut 'typing' pour configurer numpy.typing.")

        # 4. Configurer les autres sous-modules (core, linalg, fft, lib)
        # Ces modules sont déjà des instances de classes mock (_NumPy_Lib_Mock, etc.)
        # dans legacy_numpy_array_mock.py et ont __name__, __package__, __path__
        submodules_to_setup = ['core', '_core', 'linalg', 'fft', 'lib', 'random'] # 'random' ajouté
        for sub_name in submodules_to_setup:
            if hasattr(legacy_numpy_array_mock_module, sub_name):
                submodule_instance = getattr(legacy_numpy_array_mock_module, sub_name)
                # S'assurer que l'instance a les bons attributs de module si ce n'est pas déjà un ModuleType
                if not isinstance(submodule_instance, ModuleType):
                    # Si c'est une de nos classes _NumPy_X_Mock, elle devrait avoir __name__, __package__, __path__
                    # On peut la mettre directement dans sys.modules si elle est bien formée.
                    # Ou créer un ModuleType et copier les attributs.
                    # Pour l'instant, on suppose que nos instances _NumPy_X_Mock sont "assez bonnes" pour sys.modules.
                     if not hasattr(submodule_instance, '__name__'): submodule_instance.__name__ = f'numpy.{sub_name}'
                     if not hasattr(submodule_instance, '__package__'): submodule_instance.__package__ = 'numpy'
                     if not hasattr(submodule_instance, '__path__'): submodule_instance.__path__ = []


                sys.modules[f'numpy.{sub_name}'] = submodule_instance
                setattr(sys.modules['numpy'], sub_name, submodule_instance)
                logger.info(f"NumpyMock: numpy.{sub_name} configuré (type: {type(submodule_instance)}).")

                # Cas spécial pour numpy.core._multiarray_umath et numpy._core._multiarray_umath
                if sub_name == 'core' or sub_name == '_core':
                    if hasattr(submodule_instance, '_multiarray_umath'):
                        umath_instance = submodule_instance._multiarray_umath
                        if not isinstance(umath_instance, ModuleType):
                             if not hasattr(umath_instance, '__name__'): umath_instance.__name__ = f'numpy.{sub_name}._multiarray_umath'
                             if not hasattr(umath_instance, '__package__'): umath_instance.__package__ = f'numpy.{sub_name}'
                             if not hasattr(umath_instance, '__path__'): umath_instance.__path__ = []
                        sys.modules[f'numpy.{sub_name}._multiarray_umath'] = umath_instance
                        setattr(submodule_instance, '_multiarray_umath', umath_instance)
                        logger.info(f"NumpyMock: numpy.{sub_name}._multiarray_umath configuré.")
            else:
                logger.warning(f"NumpyMock: legacy_numpy_array_mock n'a pas d'attribut '{sub_name}'.")
        
        logger.info("NumpyMock: Mock NumPy et sous-modules principaux installés dans sys.modules.")

    except ImportError as e_import_mock:
        logger.error(f"ERREUR dans numpy_setup.py/_install_numpy_mock_immediately lors de l'import de legacy_numpy_array_mock: {e_import_mock}")
    except Exception as e_global_install:
        logger.error(f"ERREUR GLOBALE dans numpy_setup.py/_install_numpy_mock_immediately: {type(e_global_install).__name__}: {e_global_install}", exc_info=True)
# pass # Laisser la fonction vide pour le test


def is_module_available(module_name): 
    if module_name in sys.modules:
        if isinstance(sys.modules[module_name], MagicMock):
            return True 
    try:
        spec = importlib.util.find_spec(module_name)
        return spec is not None
    except (ImportError, ValueError):
        return False

def setup_numpy():
    if (sys.version_info.major == 3 and sys.version_info.minor >= 12) or not is_module_available('numpy'):
        if not is_module_available('numpy'): print("NumPy non disponible, utilisation du mock (depuis numpy_setup.py).")
        else: print("Python 3.12+ détecté, utilisation du mock NumPy (depuis numpy_setup.py).")
        
        _install_numpy_mock_immediately()
        print("INFO: numpy_setup.py: Mock NumPy configuré dynamiquement via setup_numpy -> _install_numpy_mock_immediately.")
        return sys.modules['numpy']
    else:
        import numpy
        print(f"Utilisation de la vraie bibliothèque NumPy (version {getattr(numpy, '__version__', 'inconnue')}) (depuis numpy_setup.py).")
        return numpy

@pytest.fixture(scope="function")
def setup_numpy_for_tests_fixture(request):
    """
    Fixture pour gérer dynamiquement l'utilisation du vrai NumPy ou de son mock.
    Assure un nettoyage complet de sys.modules avant et après chaque test pour éviter la pollution d'état.
    """
    # --- 1. Sauvegarde de l'état initial ---
    initial_modules_state = {
        name: sys.modules.get(name) for name in ['numpy', 'pandas', 'scipy', 'sklearn', 'pyarrow']
        if sys.modules.get(name) is not None
    }
    logger.info(f"Fixture pour {request.node.name}: État initial sauvegardé pour {list(initial_modules_state.keys())}.")

    # --- 2. Nettoyage systématique avant le test ---
    logger.info(f"Fixture pour {request.node.name}: Nettoyage systématique AVANT le test.")
    for lib in ['numpy', 'pandas', 'scipy', 'sklearn', 'pyarrow']:
        deep_delete_from_sys_modules(lib, logger)

    try:
        # --- 3. Décision et configuration (Mock vs. Réel) ---
        use_mock_numpy_marker = request.node.get_closest_marker("use_mock_numpy")

        if use_mock_numpy_marker:
            # --- Branche MOCK ---
            logger.info(f"Test {request.node.name} marqué 'use_mock_numpy': Installation du MOCK NumPy.")
            _install_numpy_mock_immediately()
            yield  # Le test s'exécute ici avec le mock
        else:
            # --- Branche RÉELLE (par défaut) ---
            logger.info(f"Test {request.node.name} (DEFAULT/real_numpy): Configuration pour le VRAI NumPy.")
            try:
                # Importation du vrai NumPy
                importlib.import_module('numpy')
                logger.info(f"Vrai NumPy importé avec succès pour {request.node.name}.")
                
                # Forcer la réimportation des bibliothèques dépendantes pour qu'elles utilisent le vrai NumPy
                for lib in ['pandas', 'scipy', 'sklearn', 'pyarrow']:
                    if lib in initial_modules_state and lib in sys.modules:
                        logger.info(f"Forcing reload of {lib} for {request.node.name} after loading real NumPy.")
                        try:
                            importlib.reload(sys.modules[lib])
                            logger.info(f"{lib} reloaded successfully.")
                        except Exception as e:
                            logger.error(f"Failed to reload {lib}: {e}")
                
                yield  # Le test s'exécute ici avec le vrai NumPy
            except ImportError:
                logger.error(f"Impossible d'importer le vrai NumPy pour {request.node.name}.")
                pytest.skip("Vrai NumPy non disponible.")
                yield

    finally:
        # --- 4. Nettoyage et restauration systématiques après le test ---
        logger.info(f"Fixture pour {request.node.name}: Nettoyage et restauration FINALE.")
        
        # D'abord, nettoyer tout ce qui a pu être ajouté pendant le test
        for lib in ['numpy', 'pandas', 'scipy', 'sklearn', 'pyarrow']:
            deep_delete_from_sys_modules(lib, logger)
        
        # Ensuite, restaurer l'état initial des modules
        restored_count = 0
        for name, module in initial_modules_state.items():
            if module is not None:
                sys.modules[name] = module
                restored_count += 1
        if restored_count > 0:
            logger.info(f"{restored_count} modules restaurés à leur état initial ({list(initial_modules_state.keys())}).")
        
        logger.info(f"Fin de la fixture pour {request.node.name}.")