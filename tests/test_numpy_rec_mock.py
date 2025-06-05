#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test spécifique pour vérifier que le mock numpy.rec fonctionne correctement.
Ce test vérifie que le problème "ModuleNotFoundError: No module named 'numpy.rec'" est résolu.
"""

import unittest
import sys
import os
import pytest # Ajout de pytest pour les marqueurs

# # Ajouter la racine du projet à sys.path # Géré par pytest.ini (pythonpath = .) ou PYTHONPATH env var
# project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# if project_root not in sys.path:
#     sys.path.insert(0, project_root)

# # Forcer l'utilisation du mock numpy # Sera géré par la fixture
# sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'mocks'))
# import legacy_numpy_array_mock
# # sys.modules['numpy'] = legacy_numpy_array_mock # Géré par la fixture

# Importer la fixture nécessaire si elle n'est pas autouse (ce qui est notre cas maintenant)
# from tests.mocks.numpy_setup import setup_numpy_for_tests_fixture # Pas besoin d'importer si on utilise usefixtures

# Appliquer les fixtures à toutes les fonctions de test de ce module
pytestmark = [
    pytest.mark.usefixtures("setup_numpy_for_tests_fixture"),
    pytest.mark.use_mock_numpy
]

def test_numpy_rec_import():
    """Test que numpy.rec peut être importé sans erreur."""
    try:
        import numpy
        assert hasattr(numpy, 'rec'), "numpy.rec doit exister"
    except ImportError as e:
        pytest.fail(f"Impossible d'importer numpy: {e}")

def test_numpy_rec_recarray_exists():
    """Test que numpy.rec.recarray existe."""
    import numpy
    assert hasattr(numpy.rec, 'recarray'), "numpy.rec.recarray doit exister"

def test_numpy_rec_recarray_instantiation():
    """Test que numpy.rec.recarray peut être instancié."""
    import numpy
    
    # Test avec shape et formats requis
    arr1 = numpy.rec.recarray((2, 2), formats=['i4', 'f8'], names=['id', 'value'])
    assert arr1 is not None
    assert arr1.shape == (2, 2)
    
    # Test avec formats et names
    arr2 = numpy.rec.recarray(5, formats=['i4', 'f8'], names=['x', 'y'])
    assert arr2 is not None
    assert arr2.names == ['x', 'y']
    assert arr2.formats == ['i4', 'f8']
    
    # Test avec shape et dtype
    arr3 = numpy.rec.recarray(shape=(3, 3), dtype='f8')
    assert arr3 is not None
    assert arr3.shape == (3, 3)

def test_numpy_rec_recarray_properties():
    """Test que les propriétés de recarray fonctionnent."""
    import numpy
    
    arr = numpy.rec.recarray(3, formats=['i4', 'f8'], names=['id', 'value'])
    
    # Test des propriétés
    assert arr.names == ['id', 'value']
    assert arr.formats == ['i4', 'f8']
    
    # Test d'accès aux champs (doit retourner un ndarray)
    field_access = arr.id  # Ceci utilise __getattr__
    assert field_access is not None

def test_pandas_compatibility():
    """Test que le mock est compatible avec l'utilisation par pandas."""
    import numpy
    
    # Simuler ce que pandas pourrait faire
    try:
        # pandas essaie souvent d'accéder à numpy.rec.recarray
        recarray_class = numpy.rec.recarray
        assert recarray_class is not None
        
        # pandas pourrait instancier un recarray
        arr = recarray_class((10,), formats=['i4'], names=['data'])
        assert arr is not None
        
    except Exception as e:
        pytest.fail(f"Erreur de compatibilité pandas: {e}")

# La section if __name__ == "__main__": n'est plus nécessaire avec pytest
# if __name__ == "__main__":
#     unittest.main()