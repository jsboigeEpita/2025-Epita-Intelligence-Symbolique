#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Mock pour numpy pour les tests.
Ce mock permet d'exécuter les tests sans avoir besoin d'installer numpy.
"""

import logging
from typing import Any, Dict, List, Optional, Union, Callable, Tuple, NewType
from unittest.mock import MagicMock

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("NumpyMock")

# Version
__version__ = "1.24.3"
__spec__ = MagicMock(name='numpy.__spec__') # Ajout pour compatibilité import
_CopyMode = MagicMock(name='numpy._CopyMode') # Ajout pour compatibilité scipy/sklearn

# Classes de base
class generic: # Classe de base pour les scalaires NumPy
    def __init__(self, value):
        self.value = value
    def __repr__(self):
        return f"numpy.{self.__class__.__name__}({self.value})"
    # Ajouter d'autres méthodes communes si nécessaire (ex: itemsize, flags, etc.)

class dtype:
    """Mock pour numpy.dtype."""
    
    def __init__(self, type_spec):
        # Si type_spec est une chaîne (ex: 'float64'), la stocker.
        # Si c'est un type Python (ex: float), stocker cela.
        # Si c'est une instance de nos classes de type (ex: float64), utiliser son nom.
        if isinstance(type_spec, str):
            self.name = type_spec
            self.type = type_spec # Garder une trace du type original si possible
        elif isinstance(type_spec, type):
             # Cas où on passe un type Python comme float, int
            if type_spec is float: self.name = 'float64'
            elif type_spec is int: self.name = 'int64'
            elif type_spec is bool: self.name = 'bool_'
            elif type_spec is complex: self.name = 'complex128'
            else: self.name = type_spec.__name__
            self.type = type_spec
        else: # Supposer que c'est une de nos classes de type mockées
            self.name = str(getattr(type_spec, '__name__', str(type_spec)))
            self.type = type_spec

        # Attributs attendus par certaines bibliothèques
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
    return np.round(x) # Utilise notre mock np.round

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
    return np.exp(x) - 1 # Utilise notre mock np.exp

def log1p(x, out=None):
    """Mock pour numpy.log1p (log(1 + x))."""
    if isinstance(x, ndarray):
        return ndarray(shape=x.shape, dtype=x.dtype)
    return np.log(1 + x) # Utilise notre mock np.log

def deg2rad(x, out=None):
    """Mock pour numpy.deg2rad."""
    if isinstance(x, ndarray):
        return ndarray(shape=x.shape, dtype=x.dtype)
    return x * (np.pi / 180) # Utilise notre mock np.pi

def rad2deg(x, out=None):
    """Mock pour numpy.rad2deg."""
    if isinstance(x, ndarray):
        return ndarray(shape=x.shape, dtype=x.dtype)
    return x * (180 / np.pi) # Utilise notre mock np.pi

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

# Module rec pour les record arrays
class rec:
    """Mock pour numpy.rec (record arrays)."""
    
    class recarray(ndarray):
        """Mock pour numpy.rec.recarray."""
        
        def __init__(self, shape=None, dtype=None, formats=None, names=None, **kwargs):
            # Gérer les différents formats d'arguments pour recarray
            if isinstance(shape, tuple):
                super().__init__(shape=shape, dtype=dtype)
            elif shape is not None:
                super().__init__(shape=(shape,), dtype=dtype)
            else:
                super().__init__(shape=(0,), dtype=dtype)
            
            self._names = names or []
            self._formats = formats or []
        
        @property
        def names(self):
            return self._names
        
        @property
        def formats(self):
            return self._formats
        
        def __getattr__(self, name):
            # Simule l'accès aux champs par nom
            return ndarray(shape=(len(self),))

# Instance du module rec pour l'exposition
rec.recarray = rec.recarray

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

class bool_(metaclass=dtype_base):
    """Type booléen NumPy."""
    __name__ = 'bool_'
    __module__ = 'numpy'
    
    def __new__(cls, value=False):
        return bool(value)

class number(metaclass=dtype_base):
    """Type numérique de base NumPy."""
    __name__ = 'number'
    __module__ = 'numpy'

class object_(metaclass=dtype_base):
    """Type objet NumPy."""
    __name__ = 'object_'
    __module__ = 'numpy'
    
    def __new__(cls, value=None):
        return object() if value is None else value

# Types de données (classes, pas instances)
class float64(metaclass=dtype_base):
    __name__ = 'float64'
    __module__ = 'numpy'
float64 = float64 # Rendre l'instance accessible

class float32(metaclass=dtype_base):
    __name__ = 'float32'
    __module__ = 'numpy'
float32 = float32

class int64(metaclass=dtype_base):
    __name__ = 'int64'
    __module__ = 'numpy'
int64 = int64

class int32(metaclass=dtype_base):
    __name__ = 'int32'
    __module__ = 'numpy'
int32 = int32

class uint64(metaclass=dtype_base):
    __name__ = 'uint64'
    __module__ = 'numpy'
uint64 = uint64

class uint32(metaclass=dtype_base):
    __name__ = 'uint32'
    __module__ = 'numpy'
uint32 = uint32

class int8(metaclass=dtype_base): pass
int8 = int8

class int16(metaclass=dtype_base): pass
int16 = int16

class uint8(metaclass=dtype_base): pass
uint8 = uint8

class uint16(metaclass=dtype_base): pass
uint16 = uint16

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

# Types numériques supplémentaires (maintenant aliasés aux instances de classe)
integer = int64  # Type entier générique
floating = float64  # Type flottant générique
complexfloating = complex128  # Type complexe
signedinteger = int64  # Type entier signé
unsignedinteger = uint64  # Type entier non signé

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

class int16(metaclass=dtype_base):
    __name__ = 'int16'
    __module__ = 'numpy'

class uint8(metaclass=dtype_base):
    __name__ = 'uint8'
    __module__ = 'numpy'

class uint16(metaclass=dtype_base):
    __name__ = 'uint16'
    __module__ = 'numpy'

# Alias pour compatibilité avec scipy (intc, intp)
intc = int32
intp = int64

# Classes utilitaires pour pandas
class busdaycalendar:
    """Mock pour numpy.busdaycalendar."""
    
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