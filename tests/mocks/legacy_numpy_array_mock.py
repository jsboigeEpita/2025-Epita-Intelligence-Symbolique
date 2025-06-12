#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Mock pour numpy pour les tests.
Ce mock permet d'exécuter les tests sans avoir besoin d'installer numpy.
"""

import logging
from typing import Any, Dict, List, Optional, Union, Callable, Tuple, NewType
from unittest.mock import MagicMock

import sys
# MagicMock est déjà importé à la ligne 11, donc pas besoin de le réimporter ici.

_actual_numpy_module = None
_real_numpy_flatiter = None
_real_numpy_broadcast = None
_real_numpy_inexact = None
_real_numpy_flexible = None
_real_numpy_character = None
_real_numpy_ufunc = None

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("NumpyMock")

# Attempt to import the real numpy to use some of its components
try:
    # Renommer l'import pour éviter les conflits si ce mock est lui-même importé comme 'numpy'
    import numpy as actual_numpy_for_mock
    _actual_numpy_module = actual_numpy_for_mock
    _real_numpy_flatiter = getattr(_actual_numpy_module, 'flatiter', None)
    _real_numpy_broadcast = getattr(_actual_numpy_module, 'broadcast', None)
    _real_numpy_inexact = getattr(_actual_numpy_module, 'inexact', None)
    _real_numpy_flexible = getattr(_actual_numpy_module, 'flexible', None)
    _real_numpy_character = getattr(_actual_numpy_module, 'character', None)
    _real_numpy_ufunc = getattr(_actual_numpy_module, 'ufunc', None)
    logger.info("NumpyMock: Successfully imported real numpy for some components.")
except ImportError:
    logger.warning("NumpyMock: Real numpy not found. Some mock components might be less accurate (e.g., flatiter).")
    pass # Le vrai numpy n'est pas disponible

# Adding typecodes definition
typecodes = {
    'Character': 'c',
    'Integer': 'bhilqp',
    'UnsignedInteger': 'BHILQP',
    'Float': 'efdg',
    'Complex': 'FDG',
    'AllInteger': 'bBhHiIlLqQpP',
    'AllFloat': 'efdgFDG',
    'Datetime': 'M',
    'Timedelta': 'm',
    'Object': 'O',
    'String': 'S',
    'Unicode': 'U',
    'Void': 'V',
    'All': '?bhilqpBHILQPefdgFDGSUVOMm'
}

# Version
if _actual_numpy_module and hasattr(_actual_numpy_module, '__version__'):
    __version__ = _actual_numpy_module.__version__
    logger.info(f"NumpyMock: Using real numpy version: {__version__}")
else:
    __version__ = "1.24.3.mock" # Ensure mock is in version if real numpy not found or has no version
    logger.info(f"NumpyMock: Using mock numpy version: {__version__}")

__spec__ = MagicMock(name='numpy.__spec__') # Ajout pour compatibilité import
_CopyMode = MagicMock(name='numpy._CopyMode') # Ajout pour compatibilité scipy/sklearn

# Classes de base
if _actual_numpy_module and hasattr(_actual_numpy_module, 'generic'):
    generic = _actual_numpy_module.generic
else:
    class generic_mock: # Classe de base pour les scalaires NumPy
        def __init__(self, value):
            self.value = value
        def __repr__(self):
            return f"numpy.{self.__class__.__name__}({self.value})"
        # Ajouter d'autres méthodes communes si nécessaire (ex: itemsize, flags, etc.)
    generic = generic_mock

class dtype:
    """Mock pour numpy.dtype."""
    
    def __init__(self, type_spec):
        self.names = None
        self.descr = []
        if isinstance(type_spec, list) and type_spec and isinstance(type_spec[0], tuple):
            # Structured dtype, ex: [('x', 'i4'), ('y', 'f8')]
            self.names = tuple([t[0] for t in type_spec])
            self.descr = type_spec
            # Pour un dtype structuré, 'name' est une représentation de la structure
            self.name = str(type_spec)
            self.type = 'void' # Souvent un type void pour les dtypes structurés
        elif isinstance(type_spec, str):
            self.name = type_spec
            self.type = type_spec
        elif isinstance(type_spec, type):
            if type_spec is float: self.name = 'float64'
            elif type_spec is int: self.name = 'int64'
            elif type_spec is bool: self.name = 'bool_'
            elif type_spec is complex: self.name = 'complex128'
            else: self.name = type_spec.__name__
            self.type = type_spec
        else:
            self.name = str(getattr(type_spec, '__name__', str(type_spec)))
            self.type = type_spec

        self.char = self.name[0] if self.name else ''
        self.num = 0 # Placeholder
        self.itemsize = 8 # Placeholder, typiquement 8 pour float64/int64
        if '32' in self.name or 'bool' in self.name or 'byte' in self.name or 'short' in self.name:
            self.itemsize = 4
        if '16' in self.name: # float16, int16, uint16
            self.itemsize = 2
        if '8' in self.name and '64' not in self.name and '32' not in self.name and '16' not in self.name: # int8, uint8, mais pas float16/32/64
            self.itemsize = 1
        
        self.fields = None # Pour les dtypes structurés, None pour les simples
        self.alignment = self.itemsize # Souvent égal à itemsize
        self.byteorder = '=' # Ordre natif
        self.flags = 0 # Généralement 0 pour les dtypes simples


    def __str__(self):
        return self.name
    
    def __repr__(self):
        return f"dtype('{self.name}')"

class ndarray:
    """Mock pour numpy.ndarray."""
    
    def __init__(self, shape=None, dtype=None, buffer=None, offset=0,
                 strides=None, order=None):
        self.shape = shape if shape is not None else (0,)
        self.dtype = dtype
        self.data = buffer
        self.size = 0
        if shape:
            self.size = 1
            for dim in shape:
                self.size *= dim
    
    def __getitem__(self, key):
        """Simule l'accès aux éléments."""
        return 0
    
    def __setitem__(self, key, value):
        """Simule la modification des éléments."""
        pass
    
    def __len__(self):
        """Retourne la taille du premier axe."""
        return self.shape[0] if self.shape else 0
    
    def __str__(self):
        return f"ndarray(shape={self.shape}, dtype={self.dtype})"
    
    def __repr__(self):
        return self.__str__()
    
    def reshape(self, *args):
        """Simule le changement de forme."""
        if len(args) == 1 and isinstance(args[0], tuple):
            new_shape = args[0]
        else:
            new_shape = args
        return ndarray(shape=new_shape, dtype=self.dtype)
    
    def mean(self, axis=None):
        """Simule le calcul de la moyenne."""
        return 0.0
    
    def sum(self, axis=None):
        """Simule le calcul de la somme."""
        return 0.0
    
    def max(self, axis=None):
        """Simule le calcul du maximum."""
        return 0.0
    
    def min(self, axis=None):
        """Simule le calcul du minimum."""
        return 0.0

# Fonctions principales
def array(object, dtype=None, copy=True, order='K', subok=False, ndmin=0):
    """Crée un tableau numpy."""
    if isinstance(object, (list, tuple)):
        shape = (len(object),)
        if object and isinstance(object[0], (list, tuple)):
            shape = (len(object), len(object[0]))
    else:
        shape = (1,)
    return ndarray(shape=shape, dtype=dtype)

asarray = array  # Ajout de asarray comme alias de array
ma = MagicMock(name='numpy.ma')
atleast_2d = lambda x: array(x) # Simule la conversion en tableau 2D
reshape = lambda a, newshape: ndarray(shape=newshape) # Simule reshape
newaxis = None # Placeholder pour numpy.newaxis
# zeros est déjà défini
# dot est déjà défini
# exp est déjà défini
# pi est déjà défini
atleast_1d = lambda x: array(x) # Simule la conversion en tableau 1D
cov = MagicMock(name='numpy.cov')
iinfo = MagicMock(return_value=MagicMock(max=2**31 - 1)) # Simule iinfo pour int32
# class flatiter: # Défini comme une classe
#     def __init__(self, array):
#         self.array = array
#         self.index = 0
#     def __iter__(self):
#         return self
#     def __next__(self):
#         if self.index < self.array.size: # Supposant que ndarray a un attribut size
#             # Simuler la récupération de l'élément aplati
#             # Ceci est une simplification grossière
#             self.index += 1
#             return 0 # Retourner une valeur factice
#         else:
#             raise StopIteration

if _real_numpy_flatiter:
    flatiter = _real_numpy_flatiter  # Utilise le vrai flatiter si numpy est disponible
else:
    # Fallback si le vrai numpy (et donc le vrai flatiter) n'est pas disponible.
    # Ce cas ne devrait idéalement pas être atteint si scipy est importé.
    class flatiter(MagicMock):
        pass
if _real_numpy_broadcast:
    broadcast = _real_numpy_broadcast # Utilise le vrai broadcast si numpy est disponible
else:
    # Fallback si le vrai numpy (et donc le vrai broadcast) n'est pas disponible.
    class broadcast(MagicMock):
        """Mock pour numpy.broadcast."""
        # scipy.linalg._cythonized_array_utils attend que ce soit un type,
        # pas une instance de MagicMock directement.
        # Si des instances sont créées, elles hériteront de MagicMock.
        pass

def zeros(shape, dtype=None):
    """Crée un tableau de zéros."""
    return ndarray(shape=shape, dtype=dtype)

def ones(shape, dtype=None):
    """Crée un tableau de uns."""
    return ndarray(shape=shape, dtype=dtype)

def empty(shape, dtype=None):
    """Crée un tableau vide."""
    return ndarray(shape=shape, dtype=dtype)
# Mock pour numpy.core.numeric
class _NumPy_Core_Numeric_Mock:
    """Mock pour le module numpy.core.numeric."""
    def __init__(self):
        self.__name__ = 'numpy.core.numeric'
        self.__package__ = 'numpy.core'
        self.__path__ = [] # Nécessaire pour être traité comme un module/package

        # Fonctions et attributs attendus dans numpy.core.numeric
        self.normalize_axis_tuple = MagicMock(name='numpy.core.numeric.normalize_axis_tuple')
        self.absolute = MagicMock(name='numpy.core.numeric.absolute') # np.absolute est souvent np.core.numeric.absolute
        self.add = MagicMock(name='numpy.core.numeric.add')
        self.subtract = MagicMock(name='numpy.core.numeric.subtract')
        self.multiply = MagicMock(name='numpy.core.numeric.multiply')
        self.divide = MagicMock(name='numpy.core.numeric.divide') # ou true_divide
        self.true_divide = MagicMock(name='numpy.core.numeric.true_divide')
        self.floor_divide = MagicMock(name='numpy.core.numeric.floor_divide')
        self.power = MagicMock(name='numpy.core.numeric.power')
        # ... et potentiellement beaucoup d'autres ufuncs et fonctions de base

    def __getattr__(self, name):
        logger.info(f"NumpyMock: numpy.core.numeric.{name} accédé (retourne MagicMock).")
        # Retourner un MagicMock pour tout attribut non explicitement défini
        return MagicMock(name=f"numpy.core.numeric.{name}")

# Instance globale du mock pour numpy.core.numeric
# Cela permet de l'assigner à numpy.core.numeric et aussi de le mettre dans sys.modules si besoin.
# Mock pour numpy.linalg
class _NumPy_Linalg_Mock:
    """Mock pour le module numpy.linalg."""
    def __init__(self):
        self.__name__ = 'numpy.linalg'
        self.__package__ = 'numpy'
        self.__path__ = [] # Nécessaire pour être traité comme un module/package

        # Fonctions courantes de numpy.linalg
        self.norm = MagicMock(name='numpy.linalg.norm')
        self.svd = MagicMock(name='numpy.linalg.svd')
        self.solve = MagicMock(name='numpy.linalg.solve')
        self.inv = MagicMock(name='numpy.linalg.inv')
        self.det = MagicMock(name='numpy.linalg.det')
        self.eig = MagicMock(name='numpy.linalg.eig')
        self.eigh = MagicMock(name='numpy.linalg.eigh')
        self.qr = MagicMock(name='numpy.linalg.qr')
        self.cholesky = MagicMock(name='numpy.linalg.cholesky')
        self.matrix_rank = MagicMock(name='numpy.linalg.matrix_rank')
        self.pinv = MagicMock(name='numpy.linalg.pinv')
        self.slogdet = MagicMock(name='numpy.linalg.slogdet')
        
        self.__all__ = [
            'norm', 'svd', 'solve', 'inv', 'det', 'eig', 'eigh', 'qr',
            'cholesky', 'matrix_rank', 'pinv', 'slogdet', 'lstsq', 'cond',
            'eigvals', 'eigvalsh', 'tensorinv', 'tensorsolve', 'matrix_power',
            'LinAlgError'
        ]
        # Alias ou variantes
        self.lstsq = MagicMock(name='numpy.linalg.lstsq')
        self.cond = MagicMock(name='numpy.linalg.cond')
        self.eigvals = MagicMock(name='numpy.linalg.eigvals')
        self.eigvalsh = MagicMock(name='numpy.linalg.eigvalsh')
        self.tensorinv = MagicMock(name='numpy.linalg.tensorinv')
        self.tensorsolve = MagicMock(name='numpy.linalg.tensorsolve')
        self.matrix_power = MagicMock(name='numpy.linalg.matrix_power')
        # Erreur spécifique
        self.LinAlgError = type('LinAlgError', (Exception,), {})


    def __getattr__(self, name):
        logger.info(f"NumpyMock: numpy.linalg.{name} accédé (retourne MagicMock).")
        return MagicMock(name=f"numpy.linalg.{name}")
# Mock pour numpy.fft
class _NumPy_FFT_Mock:
    """Mock pour le module numpy.fft."""
    def __init__(self):
        self.__name__ = 'numpy.fft'
        self.__package__ = 'numpy'
        self.__path__ = [] # Nécessaire pour être traité comme un module/package

        # Fonctions courantes de numpy.fft
        self.fft = MagicMock(name='numpy.fft.fft')
        self.ifft = MagicMock(name='numpy.fft.ifft')
        self.fft2 = MagicMock(name='numpy.fft.fft2')
        self.ifft2 = MagicMock(name='numpy.fft.ifft2')
        self.fftn = MagicMock(name='numpy.fft.fftn')
        self.ifftn = MagicMock(name='numpy.fft.ifftn')
        self.rfft = MagicMock(name='numpy.fft.rfft')
        self.irfft = MagicMock(name='numpy.fft.irfft')
        self.hfft = MagicMock(name='numpy.fft.hfft')
        self.ihfft = MagicMock(name='numpy.fft.ihfft')
        # Alias
        self.fftshift = MagicMock(name='numpy.fft.fftshift')
        self.ifftshift = MagicMock(name='numpy.fft.ifftshift')
        self.fftfreq = MagicMock(name='numpy.fft.fftfreq')
        self.rfftfreq = MagicMock(name='numpy.fft.rfftfreq')
        
        self.__all__ = [
            'fft', 'ifft', 'fft2', 'ifft2', 'fftn', 'ifftn', 
            'rfft', 'irfft', 'hfft', 'ihfft',
            'fftshift', 'ifftshift', 'fftfreq', 'rfftfreq'
        ]

    def __getattr__(self, name):
        logger.info(f"NumpyMock: numpy.fft.{name} accédé (retourne MagicMock).")
        return MagicMock(name=f"numpy.fft.{name}")
# Mock pour numpy.lib
class _NumPy_Lib_Mock:
    """Mock pour le module numpy.lib."""
    def __init__(self):
        self.__name__ = 'numpy.lib'
        self.__package__ = 'numpy'
        self.__path__ = []

        class NumpyVersion:
            def __init__(self, version_string):
                self.version = version_string
                # Simplification: extraire les composants majeurs/mineurs pour la comparaison
                try:
                    self.major, self.minor, self.patch = map(int, version_string.split('.')[:3])
                except ValueError: # Gérer les cas comme '1.24.3.mock'
                    self.major, self.minor, self.patch = 0,0,0


            def __ge__(self, other_version_string):
                # Comparaison simplifiée pour 'X.Y.Z'
                try:
                    other_major, other_minor, other_patch = map(int, other_version_string.split('.')[:3])
                    if self.major > other_major: return True
                    if self.major == other_major and self.minor > other_minor: return True
                    if self.major == other_major and self.minor == other_minor and self.patch >= other_patch: return True
                    return False
                except ValueError:
                    return False # Ne peut pas comparer si le format est inattendu
            
            def __lt__(self, other_version_string):
                try:
                    other_major, other_minor, other_patch = map(int, other_version_string.split('.')[:3])
                    if self.major < other_major: return True
                    if self.major == other_major and self.minor < other_minor: return True
                    if self.major == other_major and self.minor == other_minor and self.patch < other_patch: return True
                    return False
                except ValueError:
                    return False

        self.NumpyVersion = NumpyVersion
        # Autres éléments potentiels de numpy.lib peuvent être ajoutés ici si nécessaire
        # ex: self.stride_tricks = MagicMock(name='numpy.lib.stride_tricks')

        self.__all__ = ['NumpyVersion'] # Ajouter d'autres si besoin

    def __getattr__(self, name):
        logger.info(f"NumpyMock: numpy.lib.{name} accédé (retourne MagicMock).")
        return MagicMock(name=f"numpy.lib.{name}")

# Instance globale du mock pour numpy.lib
lib_module_mock_instance = _NumPy_Lib_Mock()

# Exposer lib au niveau du module numpy_mock pour qu'il soit copié par conftest
lib = lib_module_mock_instance

# Instance globale du mock pour numpy.fft
fft_module_mock_instance = _NumPy_FFT_Mock()

# Exposer fft au niveau du module numpy_mock pour qu'il soit copié par conftest
fft = fft_module_mock_instance

# Instance globale du mock pour numpy.linalg
linalg_module_mock_instance = _NumPy_Linalg_Mock()

# Exposer linalg au niveau du module numpy_mock pour qu'il soit copié par conftest
linalg = linalg_module_mock_instance
numeric_module_mock_instance = _NumPy_Core_Numeric_Mock()
# Exceptions pour compatibilité avec scipy et autres bibliothèques
AxisError = type('AxisError', (ValueError,), {})
ComplexWarning = type('ComplexWarning', (Warning,), {})
VisibleDeprecationWarning = type('VisibleDeprecationWarning', (UserWarning,), {})
DTypePromotionError = type('DTypePromotionError', (TypeError,), {}) # Pour numpy >= 1.25
# S'assurer que les exceptions sont dans __all__ si on veut qu'elles soient importables avec *
# Cependant, la copie dynamique des attributs dans conftest.py devrait les rendre disponibles.
# Pour être explicite, on pourrait les ajouter à une liste __all__ au niveau du module numpy_mock.py
# __all__ = [ ... noms de fonctions ..., 'AxisError', 'ComplexWarning', 'VisibleDeprecationWarning', 'DTypePromotionError']
# Mais pour l'instant, la copie d'attributs devrait suffire.

def arange(start, stop=None, step=1, dtype=None):
    """Crée un tableau avec des valeurs espacées régulièrement."""
    if stop is None:
        stop = start
        start = 0
    size = max(0, int((stop - start) / step))
    return ndarray(shape=(size,), dtype=dtype)

def linspace(start, stop, num=50, endpoint=True, retstep=False, dtype=None):
    """Crée un tableau avec des valeurs espacées linéairement."""
    arr = ndarray(shape=(num,), dtype=dtype)
    if retstep:
        return arr, (stop - start) / (num - 1 if endpoint else num)
    return arr

def random_sample(size=None):
    """Génère des nombres aléatoires uniformes."""
    if size is None:
        return 0.5
    if isinstance(size, int):
        size = (size,)
    return ndarray(shape=size, dtype=float)

# Fonctions supplémentaires requises par conftest.py
def mean(a, axis=None):
    """Calcule la moyenne d'un tableau."""
    if isinstance(a, ndarray):
        return a.mean(axis)
    return 0.0

def sum(a, axis=None):
    """Calcule la somme d'un tableau."""
    if isinstance(a, ndarray):
        return a.sum(axis)
    return 0.0

def max(a, axis=None):
    """Calcule le maximum d'un tableau."""
    if isinstance(a, ndarray):
        return a.max(axis)
    return 0.0

def min(a, axis=None):
    """Calcule le minimum d'un tableau."""
    if isinstance(a, ndarray):
        return a.min(axis)
    return 0.0

def dot(a, b):
    """Calcule le produit scalaire de deux tableaux."""
    return ndarray(shape=(1,))

def concatenate(arrays, axis=0):
    """Concatène des tableaux."""
    return ndarray(shape=(1,))

def vstack(arrays):
    """Empile des tableaux verticalement."""
    return ndarray(shape=(1,))

def hstack(arrays):
    """Empile des tableaux horizontalement."""
    return ndarray(shape=(1,))

def argmax(a, axis=None):
    """Retourne l'indice du maximum."""
    return 0

def argmin(a, axis=None):
    """Retourne l'indice du minimum."""
    return 0
def abs(x, out=None):
    """Mock pour numpy.abs."""
    if isinstance(x, ndarray):
        # Pour un ndarray, on pourrait vouloir retourner un nouveau ndarray
        # avec les valeurs absolues, mais pour un mock simple, retourner 0.0
        # ou une nouvelle instance de ndarray est suffisant.
        return ndarray(shape=x.shape, dtype=x.dtype)
    return 0.0 if not isinstance(x, (int, float)) else x if x >= 0 else -x

def round(a, decimals=0, out=None):
    """Mock pour numpy.round."""
    if isinstance(a, ndarray):
        return ndarray(shape=a.shape, dtype=a.dtype)
    # Comportement simplifié pour les scalaires
    return float(int(a)) if decimals == 0 else a

def percentile(a, q, axis=None, out=None, overwrite_input=False, method="linear", keepdims=False):
    """Mock pour numpy.percentile."""
    if isinstance(q, (list, tuple)):
        return ndarray(shape=(len(q),), dtype=float)
    return 0.0
# Fonctions mathématiques supplémentaires pour compatibilité scipy/transformers
def arccos(x, out=None):
    """Mock pour numpy.arccos."""
    if isinstance(x, ndarray):
        return ndarray(shape=x.shape, dtype=x.dtype)
    return 0.0 # Valeur de retour simplifiée

def arcsin(x, out=None):
    """Mock pour numpy.arcsin."""
    if isinstance(x, ndarray):
        return ndarray(shape=x.shape, dtype=x.dtype)
    return 0.0

def arctan(x, out=None):
    """Mock pour numpy.arctan."""
    if isinstance(x, ndarray):
        return ndarray(shape=x.shape, dtype=x.dtype)
    return 0.0
def arccosh(x, out=None):
    """Mock pour numpy.arccosh."""
    if isinstance(x, ndarray):
        return ndarray(shape=x.shape, dtype=x.dtype)
    return 0.0 # Valeur de retour simplifiée

def arcsinh(x, out=None):
    """Mock pour numpy.arcsinh."""
    if isinstance(x, ndarray):
        return ndarray(shape=x.shape, dtype=x.dtype)
    return 0.0

def arctanh(x, out=None):
    """Mock pour numpy.arctanh."""
    if isinstance(x, ndarray):
        return ndarray(shape=x.shape, dtype=x.dtype)
    return 0.0
def arctan2(y, x, out=None):
    """Mock pour numpy.arctan2."""
    if isinstance(y, ndarray) or isinstance(x, ndarray):
        shape = y.shape if isinstance(y, ndarray) else x.shape
        dtype_res = y.dtype if isinstance(y, ndarray) else x.dtype
        return ndarray(shape=shape, dtype=dtype_res)
    return 0.0 # Valeur de retour simplifiée

def sinh(x, out=None):
    """Mock pour numpy.sinh."""
    if isinstance(x, ndarray):
        return ndarray(shape=x.shape, dtype=x.dtype)
    return 0.0

def cosh(x, out=None):
    """Mock pour numpy.cosh."""
    if isinstance(x, ndarray):
        return ndarray(shape=x.shape, dtype=x.dtype)
    return 1.0 # cosh(0) = 1

def tanh(x, out=None):
    """Mock pour numpy.tanh."""
    if isinstance(x, ndarray):
        return ndarray(shape=x.shape, dtype=x.dtype)
    return 0.0
# Fonctions bitwise
def left_shift(x1, x2, out=None):
    """Mock pour numpy.left_shift."""
    if isinstance(x1, ndarray):
        return ndarray(shape=x1.shape, dtype=x1.dtype)
    return 0 # Valeur de retour simplifiée

def right_shift(x1, x2, out=None):
    """Mock pour numpy.right_shift."""
    if isinstance(x1, ndarray):
        return ndarray(shape=x1.shape, dtype=x1.dtype)
def rint(x, out=None):
    """Mock pour numpy.rint. Arrondit à l'entier le plus proche."""
    if isinstance(x, ndarray):
        return ndarray(shape=x.shape, dtype=x.dtype)
    # Comportement simplifié pour les scalaires
    return round(x) # Utilise notre mock round

def sign(x, out=None):
    """Mock pour numpy.sign."""
    if isinstance(x, ndarray):
        # Pourrait retourner un ndarray de -1, 0, 1
        return ndarray(shape=x.shape, dtype=int) 
    if x > 0: return 1
    if x < 0: return -1
    return 0

def expm1(x, out=None):
    """Mock pour numpy.expm1 (exp(x) - 1)."""
    if isinstance(x, ndarray):
        return ndarray(shape=x.shape, dtype=x.dtype)
    return exp(x) - 1 # Utilise notre mock exp

def log1p(x, out=None):
    """Mock pour numpy.log1p (log(1 + x))."""
    if isinstance(x, ndarray):
        return ndarray(shape=x.shape, dtype=x.dtype)
    return log(1 + x) # Utilise notre mock log

def deg2rad(x, out=None):
    """Mock pour numpy.deg2rad."""
    if isinstance(x, ndarray):
        return ndarray(shape=x.shape, dtype=x.dtype)
    return x * (pi / 180) # Utilise notre mock pi

def rad2deg(x, out=None):
    """Mock pour numpy.rad2deg."""
    if isinstance(x, ndarray):
        return ndarray(shape=x.shape, dtype=x.dtype)
    return x * (180 / pi) # Utilise notre mock pi

def trunc(x, out=None):
    """Mock pour numpy.trunc. Retourne la partie entière."""
    if isinstance(x, ndarray):
        return ndarray(shape=x.shape, dtype=x.dtype)
    return float(int(x))
    return 0

def bitwise_and(x1, x2, out=None):
    """Mock pour numpy.bitwise_and."""
    if isinstance(x1, ndarray):
        return ndarray(shape=x1.shape, dtype=x1.dtype)
    return 0

def bitwise_or(x1, x2, out=None):
    """Mock pour numpy.bitwise_or."""
def power(x1, x2, out=None):
    """Mock pour numpy.power."""
    if isinstance(x1, ndarray):
        # Si x2 est un scalaire ou un ndarray compatible
        if not isinstance(x2, ndarray) or x1.shape == x2.shape or x2.size == 1:
             return ndarray(shape=x1.shape, dtype=x1.dtype)
        # Si x1 est un scalaire et x2 un ndarray
    elif isinstance(x2, ndarray) and not isinstance(x1, ndarray):
        return ndarray(shape=x2.shape, dtype=x2.dtype)
    elif not isinstance(x1, ndarray) and not isinstance(x2, ndarray):
        try:
            return x1 ** x2 # Comportement scalaire simple
        except TypeError:
            return 0 # Fallback pour types non numériques
    # Cas plus complexes de broadcasting non gérés, retourne un ndarray par défaut si l'un est un ndarray
    if isinstance(x1, ndarray) or isinstance(x2, ndarray):
        shape = x1.shape if isinstance(x1, ndarray) else x2.shape # Simplification
        dtype_res = x1.dtype if isinstance(x1, ndarray) else (x2.dtype if isinstance(x2, ndarray) else float)
        return ndarray(shape=shape, dtype=dtype_res)
    return 0 # Fallback général
    if isinstance(x1, ndarray):
        return ndarray(shape=x1.shape, dtype=x1.dtype)
    return 0

def bitwise_xor(x1, x2, out=None):
    """Mock pour numpy.bitwise_xor."""
    if isinstance(x1, ndarray):
        return ndarray(shape=x1.shape, dtype=x1.dtype)
    return 0

def invert(x, out=None): # Aussi connu comme bitwise_not
    """Mock pour numpy.invert (bitwise_not)."""
    if isinstance(x, ndarray):
        return ndarray(shape=x.shape, dtype=x.dtype)
    return 0

bitwise_not = invert # Alias

def sin(x, out=None):
    """Mock pour numpy.sin."""
    if isinstance(x, ndarray):
        return ndarray(shape=x.shape, dtype=x.dtype)
    return 0.0

def cos(x, out=None):
    """Mock pour numpy.cos."""
    if isinstance(x, ndarray):
        return ndarray(shape=x.shape, dtype=x.dtype)
    return 0.0

def tan(x, out=None):
    """Mock pour numpy.tan."""
    if isinstance(x, ndarray):
        return ndarray(shape=x.shape, dtype=x.dtype)
    return 0.0

def sqrt(x, out=None):
    """Mock pour numpy.sqrt."""
    if isinstance(x, ndarray):
        return ndarray(shape=x.shape, dtype=x.dtype)
    return 0.0 if not isinstance(x, (int, float)) or x < 0 else x**0.5

def exp(x, out=None):
    """Mock pour numpy.exp."""
    if isinstance(x, ndarray):
        return ndarray(shape=x.shape, dtype=x.dtype)
    return 1.0 # Valeur de retour simplifiée

def log(x, out=None):
    """Mock pour numpy.log."""
    if isinstance(x, ndarray):
        return ndarray(shape=x.shape, dtype=x.dtype)
    return 0.0 # Valeur de retour simplifiée

def log10(x, out=None):
    """Mock pour numpy.log10."""
    if isinstance(x, ndarray):
        return ndarray(shape=x.shape, dtype=x.dtype)
    return 0.0

# Et d'autres qui pourraient être nécessaires par scipy.special ou autre part
pi = 3.141592653589793
e = 2.718281828459045

# Constantes numériques
nan = float('nan')
inf = float('inf')
NINF = float('-inf')
PZERO = 0.0
NZERO = -0.0
euler_gamma = 0.5772156649015329

# Fonctions de test de type
def isfinite(x, out=None):
    if isinstance(x, ndarray):
        return ndarray(shape=x.shape, dtype=bool)
    return x not in [float('inf'), float('-inf'), float('nan')]

def isnan(x, out=None):
    if isinstance(x, ndarray):
        return ndarray(shape=x.shape, dtype=bool)
    return x != x # Propriété de NaN

def isinf(x, out=None):
    if isinstance(x, ndarray):
        return ndarray(shape=x.shape, dtype=bool)
    return x == float('inf') or x == float('-inf')

# Plus de fonctions mathématiques
def floor(x, out=None):
    if isinstance(x, ndarray):
        return ndarray(shape=x.shape, dtype=x.dtype)
    return float(int(x // 1))

def ceil(x, out=None):
    if isinstance(x, ndarray):
        return ndarray(shape=x.shape, dtype=x.dtype)
    return float(int(x // 1 + (1 if x % 1 != 0 else 0)))

# S'assurer que les alias sont bien définis si numpy_mock est importé directement
# (bien que conftest.py soit la méthode préférée pour mocker)
abs = abs
round = round
max = max
min = min
sum = sum
# etc. pour les autres fonctions déjà définies plus haut si nécessaire.
# Sous-modules
class BitGenerator:
    """Mock pour numpy.random.BitGenerator."""
    
    def __init__(self, seed=None):
        self.seed = seed

class RandomState:
    """Mock pour numpy.random.RandomState."""
    
    def __init__(self, seed=None):
        self.seed = seed
    
    def random(self, size=None):
        """Génère des nombres aléatoires uniformes."""
        if size is None:
            return 0.5
        if isinstance(size, int):
            size = (size,)
        return ndarray(shape=size, dtype=float)
    
    def randint(self, low, high=None, size=None, dtype=int):
        """Génère des entiers aléatoires."""
        if high is None:
            high = low
            low = 0
        if size is None:
            return low
        if isinstance(size, int):
            size = (size,)
        return ndarray(shape=size, dtype=dtype)

class Generator:
    """Mock pour numpy.random.Generator."""
    
    def __init__(self, bit_generator=None):
        self.bit_generator = bit_generator
    
    def random(self, size=None, dtype=float, out=None):
        """Génère des nombres aléatoires uniformes."""
        if size is None:
            return 0.5
        if isinstance(size, int):
            size = (size,)
        return ndarray(shape=size, dtype=dtype)
    
    def integers(self, low, high=None, size=None, dtype=int, endpoint=False):
        """Génère des entiers aléatoires."""
        if high is None:
            high = low
            low = 0
        if size is None:
            return low
        if isinstance(size, int):
            size = (size,)
        return ndarray(shape=size, dtype=dtype)

class random:
    """Mock pour numpy.random."""
    
    # Classes pour pandas
    BitGenerator = BitGenerator
    Generator = Generator
    RandomState = RandomState
    
    @staticmethod
    def rand(*args):
        """Génère des nombres aléatoires uniformes."""
        if not args:
            return 0.5
        shape = args
        return ndarray(shape=shape, dtype=float)
    
    @staticmethod
    def randn(*args):
        """Génère des nombres aléatoires normaux."""
        if not args:
            return 0.0
        shape = args
        return ndarray(shape=shape, dtype=float)
    
    @staticmethod
    def randint(low, high=None, size=None, dtype=int):
        """Génère des entiers aléatoires."""
        if high is None:
            high = low
            low = 0
        if size is None:
            return low
        if isinstance(size, int):
            size = (size,)
        return ndarray(shape=size, dtype=dtype)
    
    @staticmethod
    def normal(loc=0.0, scale=1.0, size=None):
        """Génère des nombres aléatoires normaux."""
        if size is None:
            return loc
        if isinstance(size, int):
            size = (size,)
        return ndarray(shape=size, dtype=float)
    
    @staticmethod
    def uniform(low=0.0, high=1.0, size=None):
        """Génère des nombres aléatoires uniformes."""
        if size is None:
            return (low + high) / 2
        if isinstance(size, int):
            size = (size,)
        return ndarray(shape=size, dtype=float)

# Module rec pour les record arrays - Refonte pour un comportement de sous-module
class _NumPy_Rec_Mock:
    """Mock pour le module numpy.rec (record arrays)."""
    def __init__(self):
        self.__name__ = 'numpy.rec'
        self.__package__ = 'numpy' # Indique qu'il appartient au package 'numpy'
        self.__path__ = []       # Indique qu'il peut être traité comme un package (pour les imports)
        # La classe recarray est définie comme une classe imbriquée ci-dessous
        # et sera attachée comme un attribut à l'instance.
        self.recarray = _NumPy_Rec_Mock._recarray_impl # Attacher la classe interne

    class _recarray_impl(ndarray): # Renommée pour éviter confusion, ndarray est défini plus haut
        """Mock pour numpy.rec.recarray."""
        def __init__(self, input_array=None, shape=None, dtype=None, buf=None, offset=0, strides=None, formats=None, names=None, titles=None, byteorder=None, aligned=False, order='C'):
            # La signature de np.rec.array (qui crée un recarray) est complexe.
            # np.rec.recarray peut aussi être appelé directement.
            # Simplifions pour le mock.
            
            _shape_arg = shape
            _dtype_arg = dtype
            _names_arg = names
            _formats_arg = formats

            if input_array is not None:
                # Si input_array est un tuple et que shape n'est pas explicitement fourni,
                # il est probable que input_array SOIT la shape.
                if isinstance(input_array, tuple) and all(isinstance(dim, int) for dim in input_array) and _shape_arg is None:
                    _shape_arg = input_array
                # Sinon, si input_array est un autre array-like, essayer d'en déduire la forme.
                elif hasattr(input_array, 'shape'):
                    _shape_arg = input_array.shape
                
                if hasattr(input_array, 'dtype') and _dtype_arg is None: # Ne pas écraser un dtype explicite
                    _dtype_arg = input_array.dtype
            
            if _shape_arg is None: # Fallback si shape n'est toujours pas déductible ou fourni
                # Si names est fourni, on peut supposer une shape 1D basée sur le nombre de noms
                # Ceci est une heuristique et pourrait ne pas couvrir tous les cas d'usage de recarray.
                _shape_arg = (0,) if _names_arg is None else (len(_names_arg) if isinstance(_names_arg, (list, tuple)) else 0,)


            # Gestion du dtype pour les recarrays (très simplifié)
            if _dtype_arg is None and _names_arg and _formats_arg:
                # Essayer de construire un dtype structuré simple si names et formats sont là
                # Ceci est un placeholder, la vraie construction de dtype structuré est complexe.
                # Pour le mock, on peut juste utiliser un dtype objet ou le premier format.
                try:
                    # Utiliser le mock dtype global défini dans ce fichier
                    _dtype_arg = globals()['dtype'](list(zip(_names_arg, _formats_arg)))
                except Exception:
                    _dtype_arg = globals()['dtype'](object) # Fallback
            elif _dtype_arg is None:
                _dtype_arg = globals()['dtype'](object) # Fallback général

            super().__init__(shape=_shape_arg, dtype=_dtype_arg)
            
            self._names = _names_arg or []
            self._formats = _formats_arg or []
            # self.titles = titles # Non géré dans ce mock simple
            # self.byteorder = byteorder # Non géré
            # self.aligned = aligned # Non géré

        @property
        def names(self):
            return tuple(self._names) # Doit retourner un tuple
        
        @property
        def formats(self):
            return self._formats # Peut rester une liste
        
        @property
        def fields(self):
            # Simuler le dictionnaire fields
            if self.dtype and hasattr(self.dtype, 'fields') and self.dtype.fields:
                return self.dtype.fields
            # Construire un mock fields si le dtype ne le fournit pas
            field_dict = {}
            if self._names and self._formats and len(self._names) == len(self._formats):
                for i, name in enumerate(self._names):
                    # Créer un mock de dtype pour chaque champ
                    # Le tuple contient (dtype, offset[, title])
                    field_dtype_mock = globals()['dtype'](self._formats[i])
                    field_dict[name] = (field_dtype_mock, i * field_dtype_mock.itemsize) # Offset simplifié
            return field_dict if field_dict else None


        def __getattr__(self, name):
            # Simule l'accès aux champs par nom
            if name in self._names:
                # Pour un mock, retourner un ndarray simple de la même longueur que la première dimension
                field_shape = (self.shape[0],) if self.shape and len(self.shape) > 0 else (0,)
                # Essayer de trouver le format pour ce champ
                try:
                    idx = self._names.index(name)
                    field_format = self._formats[idx] if self._formats and idx < len(self._formats) else object
                except ValueError:
                    field_format = object
                
                return ndarray(shape=field_shape, dtype=globals()['dtype'](field_format))
            
            # Si l'attribut n'est pas un champ, essayer de le chercher sur la superclasse (ndarray)
            try:
                return super().__getattr__(name)
            except AttributeError:
                raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}' and it's not a field name")

        def field(self, attr, val=None):
            """Simule la méthode field pour accéder ou modifier les champs."""
            if val is None: # Accès
                return self.__getattr__(attr)
            else: # Modification (simplifié, ne modifie pas vraiment les données)
                if attr not in self._names:
                    raise AttributeError(f"Unknown field name: {attr}")
                # Pour un mock, on ne fait rien de plus.
                pass


# Instance du mock de module 'rec'
_rec_module_mock_instance = _NumPy_Rec_Mock()

# Exposer cette instance comme 'rec' au niveau de notre module mock 'numpy'
# Ainsi, numpy.rec pointera vers _rec_module_mock_instance,
# et numpy.rec.recarray pointera vers _rec_module_mock_instance.recarray (qui est _NumPy_Rec_Mock._recarray_impl)
rec = _rec_module_mock_instance

# Classes de types de données pour compatibilité PyTorch
class dtype_base(type):
    """Métaclasse de base pour les types de données NumPy."""
    def __new__(cls, name, bases=(), attrs=None):
        if attrs is None:
            attrs = {}
        attrs['__name__'] = name
        attrs['__module__'] = 'numpy'
        return super().__new__(cls, name, bases, attrs)
    
    def __str__(cls):
        return cls.__name__
    
    def __repr__(cls):
        return f"<class 'numpy.{cls.__name__}'>"

if _actual_numpy_module and hasattr(_actual_numpy_module, 'bool_'):
    bool_ = _actual_numpy_module.bool_
else:
    class bool__mock(metaclass=dtype_base): # Renommé pour éviter conflit
        """Type booléen NumPy."""
        __name__ = 'bool_'
        __module__ = 'numpy'
        def __new__(cls, value=False):
            return bool(value)
    bool_ = bool__mock

if _actual_numpy_module and hasattr(_actual_numpy_module, 'number'):
    number = _actual_numpy_module.number
else:
    class number_mock(metaclass=dtype_base): # Renommé
        """Type numérique de base NumPy."""
        __name__ = 'number'
        __module__ = 'numpy'
    number = number_mock

if _actual_numpy_module and hasattr(_actual_numpy_module, 'object_'):
    object_ = _actual_numpy_module.object_
else:
    class object__mock(metaclass=dtype_base): # Renommé
        """Type objet NumPy."""
        __name__ = 'object_'
        __module__ = 'numpy'
        def __new__(cls, value=None):
            return object() if value is None else value
    object_ = object__mock

if _real_numpy_inexact: # Garder la logique existante si _real_numpy_inexact est déjà défini
    inexact = _real_numpy_inexact
elif _actual_numpy_module and hasattr(_actual_numpy_module, 'inexact'):
    inexact = _actual_numpy_module.inexact
else:
    class inexact_mock(number, metaclass=dtype_base): # Hérite de number (qui pourrait être le vrai ou le mock)
        """Type de base pour les nombres inexacts (flottants, complexes) NumPy."""
        __name__ = 'inexact'
        __module__ = 'numpy'
    inexact = inexact_mock

if _real_numpy_flexible: # Garder existant
    flexible = _real_numpy_flexible
elif _actual_numpy_module and hasattr(_actual_numpy_module, 'flexible'):
    flexible = _actual_numpy_module.flexible
else:
    class flexible_mock(generic, metaclass=dtype_base): # Hérite de generic (vrai ou mock)
        """Type de base pour les types de données flexibles (chaînes, bytes) NumPy."""
        __name__ = 'flexible'
        __module__ = 'numpy'
    flexible = flexible_mock

if _real_numpy_character: # Garder existant
    character = _real_numpy_character
elif _actual_numpy_module and hasattr(_actual_numpy_module, 'character'):
    character = _actual_numpy_module.character
else:
    class character_mock(flexible, metaclass=dtype_base): # Hérite de flexible (vrai ou mock)
        """Type de base pour les types de données caractères (chaînes, bytes) NumPy."""
        __name__ = 'character'
        __module__ = 'numpy'
    character = character_mock

if _real_numpy_ufunc: # Garder existant
    ufunc = _real_numpy_ufunc
elif _actual_numpy_module and hasattr(_actual_numpy_module, 'ufunc'):
    ufunc = _actual_numpy_module.ufunc
else:
    class ufunc_mock(MagicMock):
        """Mock pour numpy.ufunc."""
        nin = 2; nout = 1; nargs = 2
        types = ['FF->F', 'dd->d', 'gg->g']; identity = None
    ufunc = ufunc_mock

# Types de données (classes, pas instances) - Appliquer le pattern
# Utiliser getattr pour plus de sécurité au cas où certains types ne seraient pas présents dans toutes les versions de numpy
def _get_real_or_mock_type(type_name_str, base_classes=(), metaclass_type=dtype_base):
    if _actual_numpy_module and hasattr(_actual_numpy_module, type_name_str):
        return getattr(_actual_numpy_module, type_name_str)
    else:
        # Créer la classe mockée dynamiquement
        mock_class_name = f"{type_name_str}_mock"
        # S'assurer que les bases sont des types, pas des chaînes
        actual_base_classes = []
        for bc in base_classes:
            if isinstance(bc, str): # Si on a passé un nom de type de base (ex: 'number')
                # Essayer de le résoudre depuis le scope actuel (qui peut contenir le vrai type ou un mock)
                resolved_bc = globals().get(bc, None)
                if resolved_bc is None: # Fallback sur generic_mock si non résolu
                    logger.warning(f"Type de base '{bc}' non résolu pour {type_name_str}, fallback sur generic.")
                    actual_base_classes.append(generic) # generic est déjà défini (vrai ou mock)
                else:
                    actual_base_classes.append(resolved_bc)
            else: # C'est déjà un type
                actual_base_classes.append(bc)
        
        # Si aucune base n'est fournie et que ce n'est pas 'generic' lui-même, hériter de 'generic'
        if not actual_base_classes and type_name_str != 'generic':
             actual_base_classes = (generic,)


        attrs = {'__name__': type_name_str, '__module__': 'numpy'}
        new_type = metaclass_type(mock_class_name, tuple(actual_base_classes), attrs)
        return new_type

float64 = _get_real_or_mock_type('float64', (inexact,))
float32 = _get_real_or_mock_type('float32', (inexact,))
int64 = _get_real_or_mock_type('int64', (number,)) # number est déjà défini (vrai ou mock)
int32 = _get_real_or_mock_type('int32', (number,))
uint64 = _get_real_or_mock_type('uint64', (number,))
uint32 = _get_real_or_mock_type('uint32', (number,))
int8 = _get_real_or_mock_type('int8', (number,))
int16 = _get_real_or_mock_type('int16', (number,))
uint8 = _get_real_or_mock_type('uint8', (number,))
uint16 = _get_real_or_mock_type('uint16', (number,))

class byte(metaclass=dtype_base): pass # byte est np.int8
byte = byte

class ubyte(metaclass=dtype_base): pass # ubyte est np.uint8
ubyte = ubyte

class short(metaclass=dtype_base): pass # short est np.int16
short = short

class ushort(metaclass=dtype_base): pass # ushort est np.uint16
ushort = ushort

class complex64(metaclass=dtype_base): pass
complex64 = complex64

class complex128(metaclass=dtype_base): pass
complex128 = complex128

# class longdouble(metaclass=dtype_base): pass # Commenté pour tester avec une chaîne
longdouble = "longdouble"

# Alias pour compatibilité
int_ = int64
uint = uint64
longlong = int64       # np.longlong (souvent int64)
ulonglong = uint64      # np.ulonglong (souvent uint64)
clongdouble = "clongdouble" # np.clongdouble (souvent complex128)
complex_ = complex128
intc = int32            # np.intc (C int, souvent int32)
uintc = uint32           # np.uintc (C unsigned int, souvent uint32)
intp = int64            # np.intp (taille d'un pointeur, souvent int64)

# Types de données flottants supplémentaires (souvent des chaînes ou des types spécifiques)
float16 = "float16" # Garder comme chaîne si c'est ainsi qu'il est utilisé, ou définir avec dtype_base

# Ajouter des logs pour diagnostiquer l'utilisation par PyTorch
logger.info(f"Types NumPy définis: bool_={bool_}, number={number}, object_={object_}")
logger.info(f"Type de bool_: {type(bool_)}, Type de number: {type(number)}, Type de object_: {type(object_)}")

# Types de données temporelles requis par pandas
datetime64 = MagicMock(name="numpy.datetime64")
timedelta64 = MagicMock(name="numpy.timedelta64")

# Types de données supplémentaires requis par pandas
float_ = float64  # Alias pour float64 (maintenant une instance de classe)
str_ = "str"
unicode_ = "unicode"

# Types numériques supplémentaires (maintenant aliasés aux instances de classe ou aux vrais types)
integer = _get_real_or_mock_type('integer', (number,))
floating = _get_real_or_mock_type('floating', (inexact,))
complexfloating = _get_real_or_mock_type('complexfloating', (inexact,))
signedinteger = _get_real_or_mock_type('signedinteger', (integer,))
unsignedinteger = _get_real_or_mock_type('unsignedinteger', (integer,))

# Types de données complexes
class complex64(metaclass=dtype_base):
    __name__ = 'complex64'
    __module__ = 'numpy'

class complex128(metaclass=dtype_base):
    __name__ = 'complex128'
    __module__ = 'numpy'

complex_ = complex128 # Alias

# Types de données entiers supplémentaires
class int8(metaclass=dtype_base):
    __name__ = 'int8'
    __module__ = 'numpy'

    
    def __init__(self, weekmask='1111100', holidays=None):
        self.weekmask = weekmask
        self.holidays = holidays or []

# Types de données flottants supplémentaires
# float16 est déjà défini plus haut (ligne 935)
# busdaycalendar est déjà défini plus haut (fusionné depuis le stash)

# Fonctions utilitaires supplémentaires
def busday_count(begindates, enddates, weekmask='1111100', holidays=None, busdaycal=None, out=None):
    """Mock pour numpy.busday_count."""
    return 0

def is_busday(dates, weekmask='1111100', holidays=None, busdaycal=None, out=None):
    """Mock pour numpy.is_busday."""
# Sous-module typing pour compatibilité avec scipy/_lib/_array_api.py
class typing:
    """Mock pour numpy.typing."""
    # Utiliser Any pour une compatibilité maximale avec les annotations de type
    # qui utilisent | (union de types) comme dans scipy.
    NDArray = Any
    ArrayLike = Any
    # Si des types plus spécifiques sont nécessaires, ils peuvent être ajoutés ici.
    # Par exemple, en utilisant NewType:
    # NDArray = NewType('NDArray', Any)
    # ArrayLike = NewType('ArrayLike', Any)


    def __getattr__(self, name):
        # Retourner un MagicMock pour tout attribut non défini explicitement
        # Cela peut aider si d'autres types spécifiques sont demandés.
        logger.info(f"NumpyMock: numpy.typing.{name} accédé (retourne MagicMock).")
        return MagicMock(name=f"numpy.typing.{name}")

# Attribuer le mock de typing au module numpy_mock pour qu'il soit importable
# par conftest.py lors de la construction du mock sys.modules['numpy']
# Exemple: from legacy_numpy_array_mock import typing as numpy_typing_mock

def busday_offset(dates, offsets, roll='raise', weekmask='1111100', holidays=None, busdaycal=None, out=None):
    """Mock pour numpy.busday_offset."""
    return dates

# Sous-modules internes pour pandas

class _NumPy_Core_Multiarray_Umath_Mock:
    """Mock pour le module numpy.core._multiarray_umath."""
    def __init__(self):
        self.__name__ = 'numpy.core._multiarray_umath'
        self.__package__ = 'numpy.core'
        self.__path__ = []
        self._ARRAY_API = MagicMock(name='numpy.core._multiarray_umath._ARRAY_API')
        # Ajouter ici des mocks pour les fonctions/constantes spécifiques de _multiarray_umath si nécessaire
        # Par exemple, celles qui pourraient être liées aux dtypes ou à l'API C.
        # Pour l'instant, un MagicMock générique pour les attributs non définis.
        # self.some_c_api_function = MagicMock(name='numpy.core._multiarray_umath.some_c_api_function')

    def __getattr__(self, name):
        logger.info(f"NumpyMock: numpy.core._multiarray_umath.{name} accédé (retourne MagicMock).")
        return MagicMock(name=f"numpy.core._multiarray_umath.{name}")

_multiarray_umath_mock_instance = _NumPy_Core_Multiarray_Umath_Mock()

class _core:
    """Mock pour numpy._core."""
    numeric = numeric_module_mock_instance # Ajout de l'attribut numeric
    _multiarray_umath = _multiarray_umath_mock_instance # Ajout du mock
    
    class multiarray:
        """Mock pour numpy._core.multiarray."""
        pass
    
    class umath:
        """Mock pour numpy._core.umath."""
        pass

class core:
    """Mock pour numpy.core."""
    numeric = numeric_module_mock_instance # Ajout de l'attribut numeric
    _multiarray_umath = _multiarray_umath_mock_instance # Ajout du mock
    
    class multiarray:
        """Mock pour numpy.core.multiarray."""
        pass
    
    class umath:
        """Mock pour numpy.core.umath."""
        pass

# Log de chargement
logger.info("Module numpy_mock chargé")