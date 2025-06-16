#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Mock pour numpy pour les tests.
Ce mock permet d'exécuter les tests sans avoir besoin d'installer numpy,
en simulant sa structure de package et ses attributs essentiels.
"""

import logging
from unittest.mock import MagicMock, Mock

# Configuration du logging
logger = logging.getLogger(__name__)

def create_numpy_mock():
    """
    Crée un mock complet pour la bibliothèque NumPy, en simulant sa structure
    de package et les attributs essentiels nécessaires pour que des bibliothèques
    comme pandas, matplotlib et scipy puissent être importées sans erreur.
    """
    # ----- Création du mock principal (le package numpy) -----
    numpy_mock = MagicMock(name='numpy_mock_package')
    numpy_mock.__version__ = '1.24.3.mock'
    
    # Pour que le mock soit considéré comme un package, il doit avoir un __path__
    numpy_mock.__path__ = ['/mock/path/numpy']

    # ----- Types de données scalaires et de base -----
    # Imiter les types de données de base de NumPy
    class MockDtype:
        def __init__(self, dtype_info):
            self.descr = []
            if isinstance(dtype_info, list):
                # Gère les dtypes structurés comme [('field1', 'i4'), ('field2', 'f8')]
                self.names = tuple(item[0] for item in dtype_info if isinstance(item, tuple) and len(item) > 0)
                self.descr = dtype_info
            else:
                 self.names = ()
        
        def __getattr__(self, name):
            # Retourne un mock pour tout autre attribut non défini
            return MagicMock(name=f'Dtype.{name}')

    class ndarray(Mock):
        def __init__(self, shape=(0,), dtype='float64', *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.shape = shape
            self.dtype = MockDtype(dtype)
            # Simuler d'autres attributs si nécessaire
            self.size = 0
            if shape:
                self.size = 1
                for dim in shape:
                    if isinstance(dim, int): self.size *= dim
            self.ndim = len(shape) if isinstance(shape, tuple) else 1

        def __getattr__(self, name):
            # Comportement par défaut pour les attributs inconnus
            if name == 'dtype':
                 return self.dtype
            return MagicMock(name=f'ndarray.{name}')

    class MockRecarray(ndarray):
        def __init__(self, shape=(0,), formats=None, names=None, dtype=None, *args, **kwargs):
            # Le constructeur de recarray peut prendre un simple entier pour la shape
            if isinstance(shape, int):
                shape = (shape,)
            
            # Pour un recarray, `formats` ou `dtype` définit la structure.
            # `formats` est juste une autre façon de spécifier `dtype`.
            dtype_arg = formats or dtype
            
            super().__init__(shape=shape, dtype=dtype_arg, *args, **kwargs)
            
            # `names` peut être passé séparément et devrait surcharger ceux du dtype.
            if names:
                self.dtype.names = tuple(names) if names else self.dtype.names
            
            # Assigner `formats` pour la compatibilité
            self.formats = formats

    class generic: pass
    class number: pass
    class integer(number): pass
    class signedinteger(integer): pass
    class unsignedinteger(integer): pass
    class floating(number): pass
    class complexfloating(number): pass
    
    # Attacher les classes de base au mock
    numpy_mock.ndarray = ndarray
    numpy_mock.generic = generic
    numpy_mock.number = number
    numpy_mock.integer = integer
    numpy_mock.signedinteger = signedinteger
    numpy_mock.unsignedinteger = unsignedinteger
    numpy_mock.floating = floating
    numpy_mock.complexfloating = complexfloating
    numpy_mock.dtype = MagicMock(name='dtype_constructor', return_value=MagicMock(name='dtype_instance', kind='f', itemsize=8))

    # Types spécifiques
    for type_name in ['float64', 'float32', 'int64', 'int32', 'uint8', 'bool_', 'object_']:
        setattr(numpy_mock, type_name, type(type_name, (object,), {}))
    
    # ----- Fonctions de base de NumPy -----
    numpy_mock.array = MagicMock(name='array', return_value=ndarray())
    numpy_mock.zeros = MagicMock(name='zeros', return_value=ndarray())
    numpy_mock.ones = MagicMock(name='ones', return_value=ndarray())
    numpy_mock.empty = MagicMock(name='empty', return_value=ndarray())
    numpy_mock.isfinite = MagicMock(name='isfinite', return_value=True)
    
    # ----- Création des sous-modules internes (_core, core, etc.) -----
    
    # Sub-module: numpy._core
    _core_mock = MagicMock(name='_core_submodule')
    _core_mock.__path__ = ['/mock/path/numpy/_core']
    
    # Sub-sub-module: numpy._core._multiarray_umath
    _multiarray_umath_mock = MagicMock(name='_multiarray_umath_submodule')
    _multiarray_umath_mock.add = MagicMock(name='add_ufunc')
    _multiarray_umath_mock.subtract = MagicMock(name='subtract_ufunc')
    _multiarray_umath_mock.multiply = MagicMock(name='multiply_ufunc')
    _multiarray_umath_mock.divide = MagicMock(name='divide_ufunc')
    _multiarray_umath_mock.implement_array_function = None
    _core_mock._multiarray_umath = _multiarray_umath_mock
    
    # Attacher _core au mock numpy principal
    numpy_mock._core = _core_mock

    # Sub-module: numpy.core (souvent un alias ou une surcouche de _core)
    core_mock = MagicMock(name='core_submodule')
    core_mock.__path__ = ['/mock/path/numpy/core']
    core_mock.multiarray = MagicMock(name='core_multiarray') # Alias/Compatibilité
    core_mock.umath = MagicMock(name='core_umath')             # Alias/Compatibilité
    core_mock._multiarray_umath = _multiarray_umath_mock      # Rendre accessible via core également
    numpy_mock.core = core_mock

    # Sub-module: numpy.linalg
    linalg_mock = MagicMock(name='linalg_submodule')
    linalg_mock.__path__ = ['/mock/path/numpy/linalg']
    linalg_mock.LinAlgError = type('LinAlgError', (Exception,), {})
    numpy_mock.linalg = linalg_mock
    
    # Sub-module: numpy.fft
    fft_mock = MagicMock(name='fft_submodule')
    fft_mock.__path__ = ['/mock/path/numpy/fft']
    numpy_mock.fft = fft_mock

    # Sub-module: numpy.random
    random_mock = MagicMock(name='random_submodule')
    random_mock.__path__ = ['/mock/path/numpy/random']
    random_mock.rand = MagicMock(return_value=0.5)
    numpy_mock.random = random_mock
    
    # Sub-module: numpy.rec (pour les recarrays)
    rec_mock = MagicMock(name='rec_submodule')
    rec_mock.__path__ = ['/mock/path/numpy/rec']
    rec_mock.recarray = MockRecarray
    numpy_mock.rec = rec_mock
    
    # Sub-module: numpy.typing
    typing_mock = MagicMock(name='typing_submodule')
    typing_mock.__path__ = ['/mock/path/numpy/typing']
    typing_mock.NDArray = MagicMock()
    numpy_mock.typing = typing_mock

    # Sub-module: numpy.lib
    lib_mock = MagicMock(name='lib_submodule')
    lib_mock.__path__ = ['/mock/path/numpy/lib']
    class NumpyVersion:
        def __init__(self, version_string):
            self.version = version_string
        def __ge__(self, other): return True
        def __lt__(self, other): return False
    lib_mock.NumpyVersion = NumpyVersion
    numpy_mock.lib = lib_mock

    logger.info(f"Mock NumPy créé avec __version__='{numpy_mock.__version__}' et la structure de sous-modules.")
    
    return numpy_mock

# Pourrait être utilisé pour un import direct, mais la création via `create_numpy_mock` est plus sûre.
numpy_mock_instance = create_numpy_mock()