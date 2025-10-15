#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test spécifique pour vérifier que le mock numpy.rec fonctionne correctement.
Ce test vérifie que le problème "ModuleNotFoundError: No module named 'numpy.rec'" est résolu.
"""

import unittest
import sys
import os

# Ajouter la racine du projet à sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Forcer l'utilisation du mock numpy
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "mocks")
)  # Doit être après l'ajout de project_root pour prioriser le mock local
import legacy_numpy_array_mock

sys.modules["numpy"] = legacy_numpy_array_mock


class TestNumpyRecMock(unittest.TestCase):
    """Tests pour vérifier que numpy.rec est correctement mocké."""

    def test_numpy_rec_import(self):
        """Test que numpy.rec peut être importé sans erreur."""
        try:
            import numpy

            self.assertTrue(hasattr(numpy, "rec"), "numpy.rec doit exister")
        except ImportError as e:
            self.fail(f"Impossible d'importer numpy: {e}")

    def test_numpy_rec_recarray_exists(self):
        """Test que numpy.rec.recarray existe."""
        import numpy

        self.assertTrue(
            hasattr(numpy.rec, "recarray"), "numpy.rec.recarray doit exister"
        )

    def test_numpy_rec_recarray_instantiation(self):
        """Test que numpy.rec.recarray peut être instancié."""
        import numpy

        # Test avec shape et formats requis
        arr1 = numpy.rec.recarray((2, 2), formats=["i4", "f8"], names=["id", "value"])
        self.assertIsNotNone(arr1)
        self.assertEqual(arr1.shape, (2, 2))

        # Test avec formats et names
        arr2 = numpy.rec.recarray(5, formats=["i4", "f8"], names=["x", "y"])
        self.assertIsNotNone(arr2)
        self.assertEqual(arr2.names, ["x", "y"])
        self.assertEqual(arr2.formats, ["i4", "f8"])

        # Test avec shape et dtype
        arr3 = numpy.rec.recarray(shape=(3, 3), dtype="f8")
        self.assertIsNotNone(arr3)
        self.assertEqual(arr3.shape, (3, 3))

    def test_numpy_rec_recarray_properties(self):
        """Test que les propriétés de recarray fonctionnent."""
        import numpy

        arr = numpy.rec.recarray(3, formats=["i4", "f8"], names=["id", "value"])

        # Test des propriétés
        self.assertEqual(arr.names, ["id", "value"])
        self.assertEqual(arr.formats, ["i4", "f8"])

        # Test d'accès aux champs (doit retourner un ndarray)
        field_access = arr.id  # Ceci utilise __getattr__
        self.assertIsNotNone(field_access)

    def test_pandas_compatibility(self):
        """Test que le mock est compatible avec l'utilisation par pandas."""
        import numpy

        # Simuler ce que pandas pourrait faire
        try:
            # pandas essaie souvent d'accéder à numpy.rec.recarray
            recarray_class = numpy.rec.recarray
            self.assertIsNotNone(recarray_class)

            # pandas pourrait instancier un recarray
            arr = recarray_class((10,), formats=["i4"], names=["data"])
            self.assertIsNotNone(arr)

        except Exception as e:
            self.fail(f"Erreur de compatibilité pandas: {e}")


if __name__ == "__main__":
    unittest.main()
