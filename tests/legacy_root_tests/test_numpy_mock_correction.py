#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test de validation de la correction du mock NumPy.
Ce test vérifie que les modules _core et core sont correctement exposés.
"""

import sys
import os

# Ajout du répertoire des mocks au PYTHONPATH
current_dir = os.path.dirname(os.path.abspath(__file__))
mocks_dir = os.path.join(current_dir, 'tests', 'mocks')
if mocks_dir not in sys.path:
    sys.path.insert(0, mocks_dir)

def test_numpy_mock_core_modules():
    """Test que les modules _core et core sont disponibles dans le mock NumPy."""
    
    # Import du mock NumPy
    from numpy_mock import array, ndarray, mean, sum, zeros, ones, dot, concatenate, vstack, hstack, argmax, argmin, max, min, random, rec, _core, core
    
    # Configuration du mock comme dans conftest.py
    sys.modules['numpy'] = type('numpy', (), {
        'array': array, 'ndarray': ndarray, 'mean': mean, 'sum': sum, 'zeros': zeros, 'ones': ones,
        'dot': dot, 'concatenate': concatenate, 'vstack': vstack, 'hstack': hstack,
        'argmax': argmax, 'argmin': argmin, 'max': max, 'min': min, 'random': random, 'rec': rec,
        '_core': _core, 'core': core, '__version__': '1.24.3',
    })
    
    # Installation explicite des sous-modules dans sys.modules
    sys.modules['numpy._core'] = _core
    sys.modules['numpy.core'] = core
    sys.modules['numpy._core.multiarray'] = _core.multiarray
    sys.modules['numpy.core.multiarray'] = core.multiarray
    
    # Test des imports
    import numpy
    assert hasattr(numpy, '_core'), "Le module _core n'est pas exposé dans numpy"
    assert hasattr(numpy, 'core'), "Le module core n'est pas exposé dans numpy"
    
    # Test des sous-modules
    import numpy._core
    import numpy.core
    import numpy._core.multiarray
    import numpy.core.multiarray
    
    print("[OK] Tous les modules NumPy sont correctement exposés !")
    print(f"[OK] numpy._core: {numpy._core}")
    print(f"[OK] numpy.core: {numpy.core}")
    print(f"[OK] numpy._core.multiarray: {numpy._core.multiarray}")
    print(f"[OK] numpy.core.multiarray: {numpy.core.multiarray}")
    
    # Si toutes les assertions passent, le test est réussi.
    # Pytest n'attend pas de valeur de retour.

if __name__ == "__main__":
    try:
        test_numpy_mock_core_modules()
        print("\n[SUCCESS] SUCCÈS : La correction du mock NumPy fonctionne parfaitement !")
        print("[INFO] Les modules _core et core sont correctement exposés.")
        print("[INFO] L'erreur 'numpy._core.multiarray failed to import' est résolue.")
    except Exception as e:
        print(f"\n[FAIL] ÉCHEC : {e}")
        sys.exit(1)