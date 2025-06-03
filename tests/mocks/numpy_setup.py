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
    import legacy_numpy_array_mock # legacy_numpy_array_mock.py devrait définir .core, ._core, et dans ceux-ci, ._multiarray_umath
except ImportError:
    print("ERREUR: numpy_setup.py: Impossible d'importer numpy_mock directement.")
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
    print("INFO: numpy_setup.py: _install_numpy_mock_immediately: Tentative d'installation/réinstallation du mock NumPy.")
    try:
        # Utiliser legacy_numpy_array_mock directement ici
        mock_numpy_attrs = {attr: getattr(legacy_numpy_array_mock, attr) for attr in dir(legacy_numpy_array_mock) if not attr.startswith('__')}
        mock_numpy_attrs['__version__'] = legacy_numpy_array_mock.__version__ if hasattr(legacy_numpy_array_mock, '__version__') else '1.24.3.mock'
        
        mock_numpy_module = type('numpy', (), mock_numpy_attrs)
        mock_numpy_module.__path__ = []
        sys.modules['numpy'] = mock_numpy_module
        
        if hasattr(legacy_numpy_array_mock, 'typing'):
            sys.modules['numpy.typing'] = legacy_numpy_array_mock.typing

        # Configuration de numpy.core comme un module
        if hasattr(legacy_numpy_array_mock, 'core'):
            numpy_core_obj = type('core', (object,), {})
            numpy_core_obj.__name__ = 'numpy.core'
            numpy_core_obj.__package__ = 'numpy'
            numpy_core_obj.__path__ = [] 
            
            # Assigner les attributs de la classe numpy_mock.core à l'objet module
            # (legacy_numpy_array_mock.core est la classe définie dans legacy_numpy_array_mock.py)
            # (legacy_numpy_array_mock.core._multiarray_umath est _multiarray_umath_mock_instance)
            if hasattr(legacy_numpy_array_mock.core, '_multiarray_umath'):
                # Créer un véritable objet ModuleType pour _multiarray_umath
                umath_module_name_core = 'numpy.core._multiarray_umath'
                umath_mock_obj_core = ModuleType(umath_module_name_core)
                
                # Copier les attributs de l'instance de _NumPy_Core_Multiarray_Umath_Mock
                # vers le nouvel objet module. legacy_numpy_array_mock.core._multiarray_umath est l'instance.
                source_mock_instance_core = legacy_numpy_array_mock.core._multiarray_umath
                for attr_name in dir(source_mock_instance_core):
                    if not attr_name.startswith('__') or attr_name in ['__name__', '__package__', '__path__']: # Copier certains dunders
                        setattr(umath_mock_obj_core, attr_name, getattr(source_mock_instance_core, attr_name))
                
                # S'assurer que les attributs essentiels de module sont là
                if not hasattr(umath_mock_obj_core, '__name__'):
                    umath_mock_obj_core.__name__ = umath_module_name_core
                if not hasattr(umath_mock_obj_core, '__package__'):
                    umath_mock_obj_core.__package__ = 'numpy.core'
                if not hasattr(umath_mock_obj_core, '__path__'):
                     umath_mock_obj_core.__path__ = [] # Les modules C n'ont pas de __path__ mais pour un mock c'est ok
                # Forcer _ARRAY_API à None pour éviter les conflits
                umath_mock_obj_core._ARRAY_API = None

                numpy_core_obj._multiarray_umath = umath_mock_obj_core
                sys.modules[umath_module_name_core] = umath_mock_obj_core
                logger.info(f"NumpyMock: {umath_module_name_core} configuré comme ModuleType et défini dans sys.modules.")

            if hasattr(legacy_numpy_array_mock.core, 'multiarray'): # legacy_numpy_array_mock.core.multiarray est une CLASSE vide
                multiarray_module_name_core = 'numpy.core.multiarray'
                multiarray_mock_obj_core = ModuleType(multiarray_module_name_core)
                multiarray_mock_obj_core.__name__ = multiarray_module_name_core
                multiarray_mock_obj_core.__package__ = 'numpy.core'
                multiarray_mock_obj_core.__path__ = []
                multiarray_mock_obj_core._ARRAY_API = None # Forcer à None

                # Potentiellement copier d'autres attributs si _NumPy_Core_Multiarray_Mock était plus fournie
                # source_multiarray_cls_core = legacy_numpy_array_mock.core.multiarray
                # try:
                #     # Si c'est une classe avec des attributs statiques ou un __init__ simple
                #     # pour une instance temporaire afin de copier les attributs.
                #     temp_instance = source_multiarray_cls_core()
                #     for attr_name_ma in dir(temp_instance):
                #         if not attr_name_ma.startswith('__') or attr_name_ma in ['__name__', '__package__', '__path__']:
                #             setattr(multiarray_mock_obj_core, attr_name_ma, getattr(temp_instance, attr_name_ma))
                # except TypeError: # Si la classe ne peut pas être instanciée simplement
                #     logger.warning(f"NumpyMock: La classe {source_multiarray_cls_core} pour multiarray n'a pas pu être instanciée pour copier les attributs.")
                #     pass


                numpy_core_obj.multiarray = multiarray_mock_obj_core
                sys.modules[multiarray_module_name_core] = multiarray_mock_obj_core
                logger.info(f"NumpyMock: {multiarray_module_name_core} configuré comme ModuleType et défini dans sys.modules.")

            if hasattr(legacy_numpy_array_mock.core, 'numeric'):
                numpy_core_obj.numeric = legacy_numpy_array_mock.core.numeric
            for attr_name in dir(legacy_numpy_array_mock.core):
                if not attr_name.startswith('__') and not hasattr(numpy_core_obj, attr_name):
                    setattr(numpy_core_obj, attr_name, getattr(legacy_numpy_array_mock.core, attr_name))
            
            sys.modules['numpy.core'] = numpy_core_obj
            if hasattr(mock_numpy_module, '__dict__'):
                mock_numpy_module.core = numpy_core_obj
            logger.info(f"NumpyMock: numpy.core configuré comme module. _multiarray_umath présent: {hasattr(numpy_core_obj, '_multiarray_umath')}")

        # Configuration de numpy._core comme un module
        if hasattr(legacy_numpy_array_mock, '_core'):
            numpy_underscore_core_obj = type('_core', (object,), {})
            numpy_underscore_core_obj.__name__ = 'numpy._core'
            numpy_underscore_core_obj.__package__ = 'numpy'
            numpy_underscore_core_obj.__path__ = []

            if hasattr(legacy_numpy_array_mock._core, '_multiarray_umath'):
                # Créer un véritable objet ModuleType pour _multiarray_umath
                umath_module_name_underscore_core = 'numpy._core._multiarray_umath'
                umath_mock_obj_underscore_core = ModuleType(umath_module_name_underscore_core)

                # Copier les attributs de l'instance de _NumPy_Core_Multiarray_Umath_Mock
                source_mock_instance_underscore_core = legacy_numpy_array_mock._core._multiarray_umath
                for attr_name in dir(source_mock_instance_underscore_core):
                    if not attr_name.startswith('__') or attr_name in ['__name__', '__package__', '__path__']:
                        setattr(umath_mock_obj_underscore_core, attr_name, getattr(source_mock_instance_underscore_core, attr_name))
                
                if not hasattr(umath_mock_obj_underscore_core, '__name__'):
                    umath_mock_obj_underscore_core.__name__ = umath_module_name_underscore_core
                if not hasattr(umath_mock_obj_underscore_core, '__package__'):
                     umath_mock_obj_underscore_core.__package__ = 'numpy._core'
                if not hasattr(umath_mock_obj_underscore_core, '__path__'):
                     umath_mock_obj_underscore_core.__path__ = []
                     # Forcer _ARRAY_API à None pour éviter les conflits
                     umath_mock_obj_underscore_core._ARRAY_API = None

                numpy_underscore_core_obj._multiarray_umath = umath_mock_obj_underscore_core
                sys.modules[umath_module_name_underscore_core] = umath_mock_obj_underscore_core
                logger.info(f"NumpyMock: {umath_module_name_underscore_core} configuré comme ModuleType et défini dans sys.modules.")
            
            if hasattr(legacy_numpy_array_mock._core, 'multiarray'): # legacy_numpy_array_mock._core.multiarray est une CLASSE vide
                multiarray_module_name_underscore_core = 'numpy._core.multiarray'
                multiarray_mock_obj_underscore_core = ModuleType(multiarray_module_name_underscore_core)
                multiarray_mock_obj_underscore_core.__name__ = multiarray_module_name_underscore_core
                multiarray_mock_obj_underscore_core.__package__ = 'numpy._core'
                multiarray_mock_obj_underscore_core.__path__ = []
                # Forcer _ARRAY_API à None pour éviter les conflits
                multiarray_mock_obj_underscore_core._ARRAY_API = None

                # Idem pour copier les attributs si _NumPy_Core_Multiarray_Mock était plus fournie
                # source_multiarray_cls_underscore_core = legacy_numpy_array_mock._core.multiarray
                # try:
                #     temp_instance_uc = source_multiarray_cls_underscore_core()
                #     for attr_name_ma_uc in dir(temp_instance_uc):
                #         if not attr_name_ma_uc.startswith('__') or attr_name_ma_uc in ['__name__', '__package__', '__path__']:
                #             setattr(multiarray_mock_obj_underscore_core, attr_name_ma_uc, getattr(temp_instance_uc, attr_name_ma_uc))
                # except TypeError:
                #     logger.warning(f"NumpyMock: La classe {source_multiarray_cls_underscore_core} pour _core.multiarray n'a pas pu être instanciée.")
                #     pass

                numpy_underscore_core_obj.multiarray = multiarray_mock_obj_underscore_core
                sys.modules[multiarray_module_name_underscore_core] = multiarray_mock_obj_underscore_core
                logger.info(f"NumpyMock: {multiarray_module_name_underscore_core} configuré comme ModuleType et défini dans sys.modules.")

            if hasattr(legacy_numpy_array_mock._core, 'numeric'):
                numpy_underscore_core_obj.numeric = legacy_numpy_array_mock._core.numeric
            for attr_name in dir(legacy_numpy_array_mock._core):
                if not attr_name.startswith('__') and not hasattr(numpy_underscore_core_obj, attr_name):
                    setattr(numpy_underscore_core_obj, attr_name, getattr(legacy_numpy_array_mock._core, attr_name))
            
            sys.modules['numpy._core'] = numpy_underscore_core_obj
            if hasattr(mock_numpy_module, '__dict__'):
                mock_numpy_module._core = numpy_underscore_core_obj
            logger.info(f"NumpyMock: numpy._core configuré comme module. _multiarray_umath présent: {hasattr(numpy_underscore_core_obj, '_multiarray_umath')}")
        
        _mock_rec_submodule = type('rec', (), {})
        _mock_rec_submodule.recarray = MockRecarray
        sys.modules['numpy.rec'] = _mock_rec_submodule

        if 'numpy' in sys.modules and sys.modules['numpy'] is mock_numpy_module:
            mock_numpy_module.rec = _mock_rec_submodule
        else:
            print("AVERTISSEMENT: numpy_setup.py: mock_numpy_module n'était pas sys.modules['numpy'] lors de l'attribution de .rec")
            if 'numpy' in sys.modules and hasattr(sys.modules['numpy'], '__dict__'):
                 setattr(sys.modules['numpy'], 'rec', _mock_rec_submodule)
        
        print(f"INFO: numpy_setup.py: Mock numpy.rec configuré. sys.modules['numpy.rec'] (ID: {id(sys.modules.get('numpy.rec'))}), mock_numpy_module.rec (ID: {id(getattr(mock_numpy_module, 'rec', None))})")
        
        if hasattr(legacy_numpy_array_mock, 'linalg'):
             sys.modules['numpy.linalg'] = legacy_numpy_array_mock.linalg
        if hasattr(legacy_numpy_array_mock, 'fft'):
             sys.modules['numpy.fft'] = legacy_numpy_array_mock.fft
        if hasattr(legacy_numpy_array_mock, 'lib'):
             sys.modules['numpy.lib'] = legacy_numpy_array_mock.lib
        
        print("INFO: numpy_setup.py: Mock NumPy installé immédiatement (avec sous-modules).")
    except ImportError as e:
        print(f"ERREUR dans numpy_setup.py lors de l'installation immédiate du mock NumPy: {e}")
    except Exception as e_global:
        print(f"ERREUR GLOBALE dans numpy_setup.py/_install_numpy_mock_immediately: {type(e_global).__name__}: {e_global}")


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

@pytest.fixture(scope="function", autouse=True)
def setup_numpy_for_tests_fixture(request):
    # Nettoyage FORCÉ au tout début de chaque exécution de la fixture
    logger.info(f"Fixture numpy_setup pour {request.node.name}: Nettoyage FORCÉ initial systématique de numpy, pandas, scipy, sklearn.")
    deep_delete_from_sys_modules("numpy", logger)
    deep_delete_from_sys_modules("pandas", logger)
    deep_delete_from_sys_modules("scipy", logger)
    deep_delete_from_sys_modules("sklearn", logger)

    use_real_numpy_marker = request.node.get_closest_marker("use_real_numpy")
    real_jpype_marker = request.node.get_closest_marker("real_jpype")

    print(f"DEBUG: numpy_setup.py: sys.path au début de la fixture pour {request.node.name}: {sys.path}")
    
    # L'état de numpy est capturé APRÈS le nettoyage forcé initial.
    # Il devrait idéalement être None ici si le nettoyage a bien fonctionné.
    numpy_state_before_this_fixture = sys.modules.get('numpy')
    numpy_rec_state_before_this_fixture = sys.modules.get('numpy.rec')

    _initial_numpy_after_forced_clean = sys.modules.get('numpy')
    try:
        if _initial_numpy_after_forced_clean:
            print(f"DEBUG: numpy_setup.py: NumPy PRÉSENT dans sys.modules pour {request.node.name} APRÈS NETTOYAGE FORCÉ INITIAL: {getattr(_initial_numpy_after_forced_clean, '__version__', 'inconnue')} (ID: {id(_initial_numpy_after_forced_clean)}) from {getattr(_initial_numpy_after_forced_clean, '__file__', 'N/A')}")
        else:
            print(f"DEBUG: numpy_setup.py: NumPy NON PRÉSENT dans sys.modules pour {request.node.name} APRÈS NETTOYAGE FORCÉ INITIAL.")
    except Exception as e_debug_initial:
        print(f"DEBUG: numpy_setup.py: Erreur lors du log de NumPy APRÈS NETTOYAGE FORCÉ pour {request.node.name}: {e_debug_initial}")

    if numpy_state_before_this_fixture: # Devrait être None si le nettoyage forcé a fonctionné
        logger.info(f"Fixture pour {request.node.name}: État de sys.modules['numpy'] APRÈS NETTOYAGE FORCÉ (devrait être None): version {getattr(numpy_state_before_this_fixture, '__version__', 'N/A')}, ID {id(numpy_state_before_this_fixture)}")
    else:
        logger.info(f"Fixture pour {request.node.name}: sys.modules['numpy'] est absent APRÈS NETTOYAGE FORCÉ (comme attendu).")
    
    # La logique de nettoyage spécifique à la branche (use_real_numpy vs mock) suit.
    # Le nettoyage ci-dessous est donc une DEUXIÈME passe de nettoyage pour la branche use_real_numpy.
    if use_real_numpy_marker or real_jpype_marker:
        marker_name = "use_real_numpy" if use_real_numpy_marker else "real_jpype"
        logger.info(f"Test {request.node.name} marqué {marker_name}: Configuration pour VRAI NumPy.")

        # Nettoyage agressif juste avant d'importer le vrai numpy
        logger.info(f"Nettoyage agressif de numpy et pandas avant import réel pour {request.node.name}")
        deep_delete_from_sys_modules("numpy", logger)
        deep_delete_from_sys_modules("pandas", logger) # Assurons-nous que pandas est aussi nettoyé ici

        # Vérification supplémentaire et suppression forcée si nécessaire
        if 'numpy' in sys.modules:
            logger.warning(f"NumPy (ID: {id(sys.modules['numpy'])}, Version: {getattr(sys.modules['numpy'], '__version__', 'N/A')}) encore dans sys.modules APRÈS deep_delete pour {request.node.name}. Suppression forcée.")
            del sys.modules['numpy']
            # Nettoyer aussi les sous-modules courants qui pourraient persister si la clé principale est supprimée mais pas les enfants
            keys_to_delete_numpy_children = [k for k in sys.modules if k.startswith('numpy.')]
            if keys_to_delete_numpy_children:
                logger.warning(f"Suppression forcée des sous-modules NumPy enfants: {keys_to_delete_numpy_children}")
                for k_child in keys_to_delete_numpy_children:
                    del sys.modules[k_child]
        
        if 'pandas' in sys.modules:
            logger.warning(f"Pandas (ID: {id(sys.modules['pandas'])}) encore dans sys.modules APRÈS deep_delete pour {request.node.name}. Suppression forcée.")
            del sys.modules['pandas']
            keys_to_delete_pandas_children = [k for k in sys.modules if k.startswith('pandas.')]
            if keys_to_delete_pandas_children:
                logger.warning(f"Suppression forcée des sous-modules Pandas enfants: {keys_to_delete_pandas_children}")
                for k_child in keys_to_delete_pandas_children:
                    del sys.modules[k_child]
        
        imported_numpy_for_test = None
        try:
            logger.info(f"Tentative d'importation du vrai NumPy pour {request.node.name}.")
            imported_numpy_for_test = importlib.import_module('numpy')
            sys.modules['numpy'] = imported_numpy_for_test 
            logger.info(f"Vrai NumPy (version {getattr(imported_numpy_for_test, '__version__', 'inconnue')}, ID: {id(imported_numpy_for_test)}) dynamiquement importé et placé dans sys.modules pour {request.node.name}.")
            
            if hasattr(imported_numpy_for_test, 'rec'):
                if not ('numpy.rec' in sys.modules and sys.modules['numpy.rec'] is imported_numpy_for_test.rec):
                    sys.modules['numpy.rec'] = imported_numpy_for_test.rec
                    logger.info(f"Vrai numpy.rec (depuis import dynamique) assigné pour {request.node.name}.")

            logger.info(f"Forcing re-import of pandas for {request.node.name} after loading real NumPy.")
            logger.info(f"Nettoyage agressif de pandas et ses sous-modules _libs avant réimportation pour {request.node.name}")
            deep_delete_from_sys_modules("pandas._libs", logger) # Cibler _libs spécifiquement
            deep_delete_from_sys_modules("pandas", logger)       # Ensuite, le reste de pandas
            try:
                import pandas # Réimporter pandas
                logger.info(f"Pandas re-imported successfully for {request.node.name} using real NumPy (version {getattr(sys.modules.get('numpy'), '__version__', 'N/A')}, ID: {id(sys.modules.get('numpy'))}). Pandas ID: {id(pandas)}")
            except ImportError as e_pandas_reimport:
                logger.error(f"Failed to re-import pandas for {request.node.name} after loading real NumPy: {e_pandas_reimport}")
                # Optionnel: skipper le test si pandas ne peut être réimporté
                # pytest.skip(f"Pandas re-import failed: {e_pandas_reimport}")

            logger.info(f"Forcing re-import of scipy for {request.node.name} after loading real NumPy.")
            deep_delete_from_sys_modules("scipy", logger)
            try:
                import scipy # Réimporter scipy
                logger.info(f"Scipy re-imported successfully for {request.node.name} using real NumPy. Scipy ID: {id(scipy)}")
            except ImportError as e_scipy_reimport:
                logger.error(f"Failed to re-import scipy for {request.node.name} after loading real NumPy: {e_scipy_reimport}")

            yield imported_numpy_for_test

        except ImportError:
            logger.error(f"Impossible d'importer dynamiquement le vrai NumPy pour {request.node.name} après nettoyage.")
            pytest.skip("Vrai NumPy non disponible après tentative d'import dynamique.")
            yield None 
        finally:
            logger.info(f"Fin de la section '{marker_name}' pour {request.node.name}. Restauration de l'état PRÉ-FIXTURE (avant nettoyage par CETTE fixture).")
            if imported_numpy_for_test and 'numpy' in sys.modules and sys.modules['numpy'] is imported_numpy_for_test:
                logger.info(f"Suppression du NumPy (ID: {id(imported_numpy_for_test)}) spécifiquement importé pour {request.node.name} ({marker_name}).")
                del sys.modules['numpy']
                if hasattr(imported_numpy_for_test, 'rec') and 'numpy.rec' in sys.modules and sys.modules['numpy.rec'] is imported_numpy_for_test.rec:
                    del sys.modules['numpy.rec']
            
            if numpy_state_before_this_fixture:
                sys.modules['numpy'] = numpy_state_before_this_fixture
                logger.info(f"Restauré sys.modules['numpy'] à l'état pré-fixture (ID: {id(numpy_state_before_this_fixture)}) pour {request.node.name} ({marker_name}).")
            elif 'numpy' in sys.modules: 
                logger.warning(f"Après suppression du NumPy de test ({marker_name}), 'numpy' (ID: {id(sys.modules['numpy'])}) est toujours dans sys.modules alors qu'il n'y avait rien à l'origine (avant cette fixture). Suppression.")
                del sys.modules['numpy']

            if numpy_rec_state_before_this_fixture:
                 sys.modules['numpy.rec'] = numpy_rec_state_before_this_fixture
                 logger.info(f"Restauré sys.modules['numpy.rec'] à l'état pré-fixture pour {request.node.name} ({marker_name}).")
            elif 'numpy.rec' in sys.modules:
                 if not ('numpy' in sys.modules and hasattr(sys.modules['numpy'], 'rec') and sys.modules['numpy'].rec is sys.modules['numpy.rec']):
                    logger.warning(f"Après suppression du NumPy de test ({marker_name}), 'numpy.rec' est toujours dans sys.modules et n'appartient pas au numpy restauré/absent. Suppression.")
                    del sys.modules['numpy.rec']
            logger.info(f"Fin de la restauration pour {request.node.name} (branche {marker_name}).")
        return

    else: 
        logger.info(f"Test {request.node.name} SANS marqueur: Configuration pour MOCK NumPy.")
        _install_numpy_mock_immediately() 
        yield 
        logger.info(f"Fin de la section SANS marqueur pour {request.node.name}. Restauration de l'état PRÉ-FIXTURE.")
        current_numpy_in_sys = sys.modules.get('numpy')
        is_our_mock = False
        if current_numpy_in_sys:
            if type(current_numpy_in_sys).__name__ == 'numpy' and hasattr(current_numpy_in_sys, '__path__') and not current_numpy_in_sys.__path__:
                is_our_mock = True
            elif hasattr(current_numpy_in_sys, '__version__') and "mock" in current_numpy_in_sys.__version__: 
                is_our_mock = True

        if is_our_mock:
            logger.info(f"Suppression du Mock NumPy (ID: {id(current_numpy_in_sys)}) installé par {request.node.name}.")
            del sys.modules['numpy']
            if 'numpy.rec' in sys.modules and hasattr(current_numpy_in_sys, 'rec') and sys.modules['numpy.rec'] is getattr(current_numpy_in_sys, 'rec', None):
                 del sys.modules['numpy.rec']
            # Nettoyer aussi les sous-modules de core qui auraient pu être mis directement dans sys.modules
            if 'numpy.core._multiarray_umath' in sys.modules:
                del sys.modules['numpy.core._multiarray_umath']
            if 'numpy._core._multiarray_umath' in sys.modules:
                del sys.modules['numpy._core._multiarray_umath']
            if 'numpy.core.multiarray' in sys.modules: # Nettoyage supplémentaire
                del sys.modules['numpy.core.multiarray']
            if 'numpy._core.multiarray' in sys.modules: # Nettoyage supplémentaire
                del sys.modules['numpy._core.multiarray']
            if 'numpy.core' in sys.modules:
                del sys.modules['numpy.core']
                logger.info(f"Supprimé sys.modules['numpy.core'] pour {request.node.name} (mock cleanup).")
            if 'numpy._core' in sys.modules:
                del sys.modules['numpy._core']
                logger.info(f"Supprimé sys.modules['numpy._core'] pour {request.node.name} (mock cleanup).")

        elif current_numpy_in_sys:
             logger.warning(f"Tentative de restauration pour {request.node.name} (mock), mais sys.modules['numpy'] (ID: {id(current_numpy_in_sys)}) n'est pas le mock attendu.")

        if numpy_state_before_this_fixture:
            sys.modules['numpy'] = numpy_state_before_this_fixture
            logger.info(f"Restauré sys.modules['numpy'] à l'état pré-fixture (ID: {id(numpy_state_before_this_fixture)}) pour {request.node.name} (mock).")
        elif 'numpy' in sys.modules: 
            logger.warning(f"Après suppression du Mock NumPy, 'numpy' (ID: {id(sys.modules['numpy'])}) est toujours dans sys.modules alors qu'il n'y avait rien à l'origine (avant cette fixture). Suppression.")
            del sys.modules['numpy']

        if numpy_rec_state_before_this_fixture:
            sys.modules['numpy.rec'] = numpy_rec_state_before_this_fixture
            logger.info(f"Restauré sys.modules['numpy.rec'] à l'état pré-fixture pour {request.node.name} (mock).")
        elif 'numpy.rec' in sys.modules:
            if not ('numpy' in sys.modules and hasattr(sys.modules['numpy'], 'rec') and sys.modules['numpy'].rec is sys.modules['numpy.rec']):
                logger.warning(f"Après suppression du Mock NumPy, 'numpy.rec' est toujours dans sys.modules et n'appartient pas au numpy restauré/absent. Suppression.")
                del sys.modules['numpy.rec']
        logger.info(f"Fin de la restauration pour {request.node.name} (branche mock).")

# if (sys.version_info.major == 3 and sys.version_info.minor >= 10):
# _install_numpy_mock_immediately()