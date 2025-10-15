#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test de validation du mock NumPy.
Ce test vérifie que les modules _core et core sont correctement exposés.
"""

import sys
import os

# L'import de numpy_mock doit être adapté en fonction de sa localisation réelle.
# Si numpy_mock.py est dans le même répertoire (tests/mocks), l'import relatif est correct.
from .legacy_numpy_array_mock import (
    array,
    ndarray,
    mean,
    sum,
    zeros,
    ones,
    dot,
    concatenate,
    vstack,
    hstack,
    argmax,
    argmin,
    max,
    min,
    random,
    rec,
    _core,
    core,
)


def test_numpy_mock_core_modules():
    """Test que les modules _core et core sont disponibles dans le mock NumPy."""

    # Sauvegarde de l'état original de sys.modules pour numpy et ses sous-modules
    original_numpy = sys.modules.get("numpy")
    original_numpy_core = sys.modules.get("numpy.core")
    original_numpy__core = sys.modules.get("numpy._core")
    original_numpy_core_multiarray = sys.modules.get("numpy.core.multiarray")
    original_numpy__core_multiarray = sys.modules.get("numpy._core.multiarray")

    try:
        # Configuration du mock comme dans conftest.py
        numpy_mock_module = type(
            "numpy",
            (),
            {
                "array": array,
                "ndarray": ndarray,
                "mean": mean,
                "sum": sum,
                "zeros": zeros,
                "ones": ones,
                "dot": dot,
                "concatenate": concatenate,
                "vstack": vstack,
                "hstack": hstack,
                "argmax": argmax,
                "argmin": argmin,
                "max": max,
                "min": min,
                "random": random,
                "rec": rec,
                "_core": _core,
                "core": core,
                "__version__": "1.24.3",
            },
        )

        sys.modules["numpy"] = numpy_mock_module

        # Installation explicite des sous-modules dans sys.modules
        sys.modules["numpy._core"] = _core
        sys.modules["numpy.core"] = core
        if hasattr(_core, "multiarray"):
            sys.modules["numpy._core.multiarray"] = _core.multiarray
        if hasattr(core, "multiarray"):
            sys.modules["numpy.core.multiarray"] = core.multiarray

        # Test des imports
        import numpy

        assert hasattr(numpy, "_core"), "Le module _core n'est pas exposé dans numpy"
        assert hasattr(numpy, "core"), "Le module core n'est pas exposé dans numpy"

        # Test des sous-modules
        import numpy._core
        import numpy.core

        # Affichages pour le débogage / information
        print("[OK] Tous les modules NumPy sont correctement exposés !")
        print(f"[INFO] numpy._core: {numpy._core}")
        print(f"[INFO] numpy.core: {numpy.core}")

        if hasattr(_core, "multiarray"):
            import numpy._core.multiarray

            print(f"[INFO] numpy._core.multiarray: {numpy._core.multiarray}")
        if hasattr(core, "multiarray"):
            import numpy.core.multiarray

            print(f"[INFO] numpy.core.multiarray: {numpy.core.multiarray}")

    finally:
        # Restauration de l'état original de sys.modules
        if original_numpy is None:
            if "numpy" in sys.modules:
                del sys.modules["numpy"]
        else:
            sys.modules["numpy"] = original_numpy

        if original_numpy_core is None:
            if "numpy.core" in sys.modules:
                del sys.modules["numpy.core"]
        else:
            sys.modules["numpy.core"] = original_numpy_core

        if original_numpy__core is None:
            if "numpy._core" in sys.modules:
                del sys.modules["numpy._core"]
        else:
            sys.modules["numpy._core"] = original_numpy__core

        if original_numpy_core_multiarray is None:
            if "numpy.core.multiarray" in sys.modules:
                del sys.modules["numpy.core.multiarray"]
        else:
            sys.modules["numpy.core.multiarray"] = original_numpy_core_multiarray

        if original_numpy__core_multiarray is None:
            if "numpy._core.multiarray" in sys.modules:
                del sys.modules["numpy._core.multiarray"]
        else:
            sys.modules["numpy._core.multiarray"] = original_numpy__core_multiarray
