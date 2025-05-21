"""
Mock pour le module numpy.

Ce module fournit des implémentations factices des fonctionnalités de numpy
qui sont utilisées dans le projet, permettant d'exécuter les tests sans avoir besoin
de numpy.
"""

import sys
from unittest.mock import MagicMock

# Créer un mock pour numpy.array
def array(data, dtype=None):
    """Mock pour numpy.array."""
    return data

# Créer un mock pour numpy.ndarray
class ndarray(list):
    """Mock pour numpy.ndarray."""
    
    def __init__(self, data=None):
        super().__init__(data or [])
        self.shape = (len(self),)
    
    def mean(self, axis=None):
        """Mock pour ndarray.mean."""
        if not self:
            return 0
        return sum(self) / len(self)
    
    def sum(self, axis=None):
        """Mock pour ndarray.sum."""
        return sum(self)
    
    def reshape(self, *shape):
        """Mock pour ndarray.reshape."""
        return self
    
    def dot(self, other):
        """Mock pour ndarray.dot."""
        if not self or not other:
            return 0
        return sum(a * b for a, b in zip(self, other))

# Créer des mocks pour les fonctions numpy couramment utilisées
mean = lambda x, axis=None: sum(x) / len(x) if x else 0
sum = lambda x, axis=None: sum(x)
zeros = lambda shape, dtype=None: [0] * shape[0] if isinstance(shape, tuple) else [0] * shape
ones = lambda shape, dtype=None: [1] * shape[0] if isinstance(shape, tuple) else [1] * shape
dot = lambda a, b: sum(a_i * b_i for a_i, b_i in zip(a, b)) if a and b else 0
concatenate = lambda arrays, axis=0: [item for sublist in arrays for item in sublist]
vstack = lambda arrays: arrays
hstack = lambda arrays: [item for sublist in arrays for item in sublist]
argmax = lambda a, axis=None: a.index(max(a)) if a else 0
argmin = lambda a, axis=None: a.index(min(a)) if a else 0
max = lambda a, axis=None: max(a) if a else 0
min = lambda a, axis=None: min(a) if a else 0

# Créer un mock pour numpy.random
class RandomMock:
    """Mock pour numpy.random."""
    
    def rand(self, *args):
        """Mock pour numpy.random.rand."""
        if not args:
            return 0.5
        if len(args) == 1:
            return [0.5] * args[0]
        return [[0.5 for _ in range(args[1])] for _ in range(args[0])]
    
    def randn(self, *args):
        """Mock pour numpy.random.randn."""
        return self.rand(*args)
    
    def randint(self, low, high=None, size=None):
        """Mock pour numpy.random.randint."""
        if high is None:
            high = low
            low = 0
        if size is None:
            return (low + high) // 2
        if isinstance(size, int):
            return [(low + high) // 2] * size
        return [[(low + high) // 2 for _ in range(size[1])] for _ in range(size[0])]
    
    def choice(self, a, size=None, replace=True, p=None):
        """Mock pour numpy.random.choice."""
        if size is None:
            return a[0] if a else None
        if isinstance(size, int):
            return [a[0] if a else None] * size
        return [[a[0] if a else None for _ in range(size[1])] for _ in range(size[0])]
    
    def shuffle(self, x):
        """Mock pour numpy.random.shuffle."""
        pass

# Créer l'instance de RandomMock
random = RandomMock()

# Installer le mock dans sys.modules pour qu'il soit utilisé lors des importations
sys.modules['numpy'] = sys.modules.get('numpy', MagicMock(
    array=array,
    ndarray=ndarray,
    mean=mean,
    sum=sum,
    zeros=zeros,
    ones=ones,
    dot=dot,
    concatenate=concatenate,
    vstack=vstack,
    hstack=hstack,
    argmax=argmax,
    argmin=argmin,
    max=max,
    min=min,
    random=random
))