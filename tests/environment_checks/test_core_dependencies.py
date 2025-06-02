# tests/environment_checks/test_core_dependencies.py
import pytest

def test_import_jpype():
    """Tests if jpype can be imported."""
    try:
        import jpype
        print(f"JPype version: {getattr(jpype, '__version__', 'N/A')}")
    except ImportError as e:
        pytest.fail(f"Erreur lors de l'importation de JPype: {e}")

def test_import_numpy():
    """Tests if numpy can be imported."""
    try:
        import numpy
        print(f"NumPy version: {getattr(numpy, '__version__', 'N/A')}")
    except ImportError as e:
        pytest.fail(f"Erreur lors de l'importation de NumPy: {e}")

def test_import_torch():
    """Tests if torch can be imported."""
    try:
        import torch
        print(f"PyTorch version: {getattr(torch, '__version__', 'N/A')}")
    except ImportError as e:
        pytest.fail(f"Erreur lors de l'importation de PyTorch: {e}")

def test_import_transformers():
    """Tests if transformers can be imported."""
    try:
        import transformers
        print(f"Transformers version: {getattr(transformers, '__version__', 'N/A')}")
    except ImportError as e:
        pytest.fail(f"Erreur lors de l'importation de Transformers: {e}")

def test_import_networkx():
    """Tests if networkx can be imported."""
    try:
        import networkx
        print(f"NetworkX version: {getattr(networkx, '__version__', 'N/A')}")
    except ImportError as e:
        pytest.fail(f"Erreur lors de l'importation de NetworkX: {e}")