#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Mock pour numpy pour les tests.
Ce mock permet d'exécuter les tests sans avoir besoin d'installer numpy.
"""

import logging
from typing import Any, Dict, List, Optional, Union, Callable, Tuple

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("NumpyMock")

# Version
__version__ = "1.24.3"

# Classes de base
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

# Sous-modules
class random:
    """Mock pour numpy.random."""
    
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

# Types de données
float64 = "float64"
float32 = "float32"
int64 = "int64"
int32 = "int32"
int_ = "int64"  # Alias pour int64
uint = "uint64"  # Type unsigned int
uint64 = "uint64"
uint32 = "uint32"
bool_ = "bool"

# Log de chargement
logger.info("Module numpy_mock chargé")