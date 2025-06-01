import sys
from unittest.mock import MagicMock
import pytest
import importlib # Ajouté pour numpy_mock si besoin d'import dynamique

# Tentative d'importation de numpy_mock. S'il est dans le même répertoire (tests/mocks), cela devrait fonctionner.
try:
    import numpy_mock
except ImportError:
    # Fallback si l'import direct échoue, pourrait indiquer un problème de structure ou de PYTHONPATH
    # pour l'exécution de ce module isolément, bien que pytest devrait le gérer.
    print("ERREUR: numpy_setup.py: Impossible d'importer numpy_mock directement.")
    numpy_mock = MagicMock(name="numpy_mock_fallback_in_numpy_setup")
    numpy_mock.typing = MagicMock()
    numpy_mock._core = MagicMock()
    numpy_mock.core = MagicMock()
    numpy_mock.linalg = MagicMock()
    numpy_mock.fft = MagicMock()
    numpy_mock.lib = MagicMock()
    numpy_mock.__version__ = '1.24.3.mock_fallback'
    # Simuler les sous-modules de core si nécessaire pour éviter des AttributeError
    if hasattr(numpy_mock._core, 'multiarray'):
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
        elif args and isinstance(args[0], tuple): # shape as positional arg
             self.shape = args[0]
        elif args and args[0] is not None: # shape as single integer positional arg
             self.shape = (args[0],)
        else:
             self.shape = (0,) # Default or if no shape info
        self.dtype = MagicMock(name="recarray_dtype_mock")
        names_arg = kwargs.get('names')
        self.dtype.names = list(names_arg) if names_arg is not None else []
        self._formats = kwargs.get('formats') # Stocker les formats

    @property
    def names(self):
        return self.dtype.names

    @property
    def formats(self):
        return self._formats

    def __getattr__(self, name):
        if name == 'names': # Gérer l'accès à .names via __getattr__ si @property n'est pas suffisant (ne devrait pas être le cas)
            return self.dtype.names
        if name == 'formats': # Gérer l'accès à .formats via __getattr__
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
        # numpy_mock est importé en haut du fichier
        mock_numpy_attrs = {attr: getattr(numpy_mock, attr) for attr in dir(numpy_mock) if not attr.startswith('__')}
        mock_numpy_attrs['__version__'] = numpy_mock.__version__ if hasattr(numpy_mock, '__version__') else '1.24.3.mock'
        
        mock_numpy_module = type('numpy', (), mock_numpy_attrs)
        mock_numpy_module.__path__ = [] 
        sys.modules['numpy'] = mock_numpy_module
        
        if hasattr(numpy_mock, 'typing'):
            sys.modules['numpy.typing'] = numpy_mock.typing
        if hasattr(numpy_mock, '_core'):
            sys.modules['numpy._core'] = numpy_mock._core
        if hasattr(numpy_mock, 'core'):
            sys.modules['numpy.core'] = numpy_mock.core
        
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

        if hasattr(numpy_mock, '_core') and hasattr(numpy_mock._core, 'multiarray'):
             sys.modules['numpy._core.multiarray'] = numpy_mock._core.multiarray
        if hasattr(numpy_mock, 'core') and hasattr(numpy_mock.core, 'multiarray'):
             sys.modules['numpy.core.multiarray'] = numpy_mock.core
        if hasattr(numpy_mock, 'core') and hasattr(numpy_mock.core, 'numeric'):
             sys.modules['numpy.core.numeric'] = numpy_mock.core.numeric
        if hasattr(numpy_mock, '_core') and hasattr(numpy_mock._core, 'numeric'):
             sys.modules['numpy._core.numeric'] = numpy_mock._core.numeric
        if hasattr(numpy_mock, 'linalg'):
             sys.modules['numpy.linalg'] = numpy_mock.linalg
        if hasattr(numpy_mock, 'fft'):
             sys.modules['numpy.fft'] = numpy_mock.fft
        if hasattr(numpy_mock, 'lib'):
             sys.modules['numpy.lib'] = numpy_mock.lib
        
        print("INFO: numpy_setup.py: Mock NumPy installé immédiatement (avec sous-modules).")
    except ImportError as e:
        print(f"ERREUR dans numpy_setup.py lors de l'installation immédiate du mock NumPy: {e}")
    except Exception as e_global: # Attraper d'autres erreurs potentielles
        print(f"ERREUR GLOBALE dans numpy_setup.py/_install_numpy_mock_immediately: {type(e_global).__name__}: {e_global}")


def is_module_available(module_name): # Copié depuis conftest.py, pourrait être dans un utilitaire partagé
    if module_name in sys.modules:
        if isinstance(sys.modules[module_name], MagicMock):
            return True # Si c'est déjà un mock, on considère "disponible" pour la logique de mock
    try:
        spec = importlib.util.find_spec(module_name)
        return spec is not None
    except (ImportError, ValueError):
        return False

def setup_numpy():
    # numpy_mock est importé en haut
    if (sys.version_info.major == 3 and sys.version_info.minor >= 12) or not is_module_available('numpy'):
        if not is_module_available('numpy'): print("NumPy non disponible, utilisation du mock (depuis numpy_setup.py).")
        else: print("Python 3.12+ détecté, utilisation du mock NumPy (depuis numpy_setup.py).")
        
        mock_numpy_attrs = {attr: getattr(numpy_mock, attr) for attr in dir(numpy_mock) if not attr.startswith('__')}
        mock_numpy_attrs['__version__'] = numpy_mock.__version__ if hasattr(numpy_mock, '__version__') else '1.24.3.mock'

        mock_numpy_module_setup_func = type('numpy', (), mock_numpy_attrs)
        mock_numpy_module_setup_func.__path__ = []
        sys.modules['numpy'] = mock_numpy_module_setup_func
        
        if hasattr(numpy_mock, 'typing'):
            sys.modules['numpy.typing'] = numpy_mock.typing
        if hasattr(numpy_mock, '_core'):
            sys.modules['numpy._core'] = numpy_mock._core
        if hasattr(numpy_mock, 'core'):
            sys.modules['numpy.core'] = numpy_mock.core
            if 'numpy' in sys.modules and hasattr(sys.modules['numpy'], 'core'):
                sys.modules['numpy'].core = numpy_mock.core

        _mock_rec_submodule_setup = type('rec', (), {})
        _mock_rec_submodule_setup.recarray = MockRecarray
        sys.modules['numpy.rec'] = _mock_rec_submodule_setup
        
        if 'numpy' in sys.modules and sys.modules['numpy'] is mock_numpy_module_setup_func:
            mock_numpy_module_setup_func.rec = _mock_rec_submodule_setup
        else:
            print("AVERTISSEMENT: numpy_setup.py: mock_numpy_module_setup_func n'était pas sys.modules['numpy'] lors de l'attribution de .rec dans setup_numpy")
            if 'numpy' in sys.modules and hasattr(sys.modules['numpy'], '__dict__'):
                 setattr(sys.modules['numpy'], 'rec', _mock_rec_submodule_setup)
        
        print(f"INFO: numpy_setup.py: Mock numpy.rec configuré dans setup_numpy. sys.modules['numpy.rec'] (ID: {id(sys.modules.get('numpy.rec'))}), mock_numpy_module_setup_func.rec (ID: {id(getattr(mock_numpy_module_setup_func, 'rec', None))})")
        
        if hasattr(numpy_mock, '_core') and hasattr(numpy_mock._core, 'multiarray'):
            sys.modules['numpy._core.multiarray'] = numpy_mock._core.multiarray
        if hasattr(numpy_mock, 'core') and hasattr(numpy_mock.core, 'multiarray'):
            sys.modules['numpy.core.multiarray'] = numpy_mock.core
        if hasattr(numpy_mock, 'core') and hasattr(numpy_mock.core, 'numeric'):
            sys.modules['numpy.core.numeric'] = numpy_mock.core.numeric
        if hasattr(numpy_mock, '_core') and hasattr(numpy_mock._core, 'numeric'):
            sys.modules['numpy._core.numeric'] = numpy_mock._core.numeric
        if hasattr(numpy_mock, 'linalg'):
            sys.modules['numpy.linalg'] = numpy_mock.linalg
        if hasattr(numpy_mock, 'fft'):
            sys.modules['numpy.fft'] = numpy_mock.fft
        if hasattr(numpy_mock, 'lib'):
            sys.modules['numpy.lib'] = numpy_mock.lib

        print("INFO: numpy_setup.py: Mock NumPy configuré dynamiquement.")
        return sys.modules['numpy']
    else:
        import numpy
        print(f"Utilisation de la vraie bibliothèque NumPy (version {getattr(numpy, '__version__', 'inconnue')}) (depuis numpy_setup.py).")
        return numpy

@pytest.fixture(scope="function", autouse=True)
def setup_numpy_for_tests_fixture(request):
    use_real_numpy_marker = request.node.get_closest_marker("use_real_numpy")
    real_jpype_marker = request.node.get_closest_marker("real_jpype")

    if use_real_numpy_marker or real_jpype_marker:
        marker_name = "use_real_numpy" if use_real_numpy_marker else "real_jpype"
        print(f"INFO: numpy_setup.py: setup_numpy_for_tests_fixture: Test {request.node.name} marqué {marker_name}, tentative d'utilisation du vrai NumPy.")
        
        original_numpy = sys.modules.get('numpy')
        original_numpy_rec = sys.modules.get('numpy.rec')
        
        # Supprimer le mock de sys.modules s'il est présent
        if 'numpy' in sys.modules and isinstance(sys.modules['numpy'], type) and sys.modules['numpy'].__name__ == 'numpy' and hasattr(sys.modules['numpy'], '__path__') and not sys.modules['numpy'].__path__:
            print("INFO: numpy_setup.py: Mock NumPy détecté, suppression pour utiliser le vrai NumPy.")
            del sys.modules['numpy']
            if 'numpy.rec' in sys.modules: # Supprimer aussi les sous-modules mockés
                del sys.modules['numpy.rec']
            # Potentiellement d'autres sous-modules à supprimer: numpy.typing, numpy.core, etc.
            # Pour l'instant, on se concentre sur numpy et numpy.rec

        try:
            import numpy
            print(f"INFO: numpy_setup.py: Vrai NumPy (version {getattr(numpy, '__version__', 'inconnue')}) importé avec succès.")
            # S'assurer que les sous-modules importants sont aussi les vrais
            if hasattr(numpy, 'rec') and 'numpy.rec' in sys.modules and isinstance(sys.modules['numpy.rec'], type) and sys.modules['numpy.rec'].__name__ == 'rec':
                 pass # Vrai numpy.rec est déjà là ou sera chargé par le vrai numpy
            elif hasattr(numpy, 'rec'):
                 sys.modules['numpy.rec'] = numpy.rec


        except ImportError:
            print("ERREUR: numpy_setup.py: Impossible d'importer le vrai NumPy. Le mock restera probablement actif si installé précédemment.")
            # Si le vrai numpy ne peut être importé, on ne fait rien de plus, le mock pourrait déjà être là.
        
        yield # Laisser le test s'exécuter avec le vrai NumPy (ou ce qui a pu être chargé)

        # Restauration après le test (si nécessaire, mais pour 'use_real_numpy' on veut le vrai)
        # Si un mock était là avant et qu'on l'a enlevé, il faut le remettre pour les autres tests.
        # Cette logique devient complexe. Pour l'instant, on suppose que les tests marqués
        # 'use_real_numpy' sont exécutés dans un contexte où le vrai numpy est souhaité et disponible.
        # La restauration du mock initial est gérée par la logique 'else' ci-dessous.
        # Si original_numpy était le mock, il sera restauré par la branche 'else'.
        # Si original_numpy était le vrai, il est déjà là.
        # Si original_numpy était None, et qu'on a chargé le vrai, c'est ok.
        # Le problème est si un mock était là, qu'on charge le vrai, puis qu'un autre test a besoin du mock.
        # La fixture étant 'function' scope, la restauration ci-dessous devrait gérer cela.

        # On restaure ce qui était là avant CE test spécifique si ce test utilisait le vrai numpy
        if original_numpy:
            sys.modules['numpy'] = original_numpy
        elif 'numpy' in sys.modules and not use_real_numpy_marker and not real_jpype_marker:
            # Si on n'avait rien à l'origine et qu'on a chargé le vrai, on le supprime pour que le mock soit réinstallé
            # pour les tests suivants qui n'ont pas le marqueur.
            # Mais seulement si ce n'est pas un test qui voulait le vrai numpy.
            # Cette partie est délicate. La logique principale de mock/démock est mieux gérée
            # par _install_numpy_mock_immediately et la restauration simple.
             pass


        if original_numpy_rec:
            sys.modules['numpy.rec'] = original_numpy_rec
        elif 'numpy.rec' in sys.modules and not use_real_numpy_marker and not real_jpype_marker:
            pass
        return

    # Logique existante pour les tests qui N'ONT PAS le marqueur 'use_real_numpy' ou 'real_jpype'
    # C'est ici qu'on s'assure que le mock est bien actif.
    _original_numpy_before_mock_install = sys.modules.get('numpy')
    _original_numpy_rec_before_mock_install = sys.modules.get('numpy.rec')

    _install_numpy_mock_immediately() # Assure que le mock est en place

    yield

    # Restauration pour les tests qui utilisaient le mock
    if _original_numpy_before_mock_install:
        sys.modules['numpy'] = _original_numpy_before_mock_install
    elif 'numpy' in sys.modules:
        # Si on a mis notre mock et qu'il n'y avait rien, on le laisse pour l'instant
        # ou on pourrait le supprimer si on est sûr qu'aucun autre test n'en dépendrait
        # de manière inattendue. Pour l'instant, on le laisse.
        pass
        
    if _original_numpy_rec_before_mock_install:
        sys.modules['numpy.rec'] = _original_numpy_rec_before_mock_install
    elif 'numpy.rec' in sys.modules:
        pass

# Condition pour l'installation immédiate, si ce fichier est importé directement
# et que la version de Python correspond. Pytest gérera cela via la fixture autouse.
# if (sys.version_info.major == 3 and sys.version_info.minor >= 10):
# _install_numpy_mock_immediately()