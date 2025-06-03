# tests/environment_checks/test_core_dependencies.py
import importlib
import pytest

# Liste des dépendances majeures du projet à vérifier
# Certaines sont testées individuellement ci-dessous pour des raisons spécifiques (ex: affichage version)
# Les autres sont testées via la fonction paramétrée.
CORE_DEPENDENCIES_INDIVIDUAL = [
    "jpype", "numpy", "torch", "transformers", "networkx"
]

PROJECT_DEPENDENCIES_PARAMETRIZED = [
    "pandas", "scipy", "sklearn", "nltk", "spacy",
    "pydantic", "requests", "matplotlib", "seaborn",
    "dotenv", "semantic_kernel", "pytest", "coverage", "cryptography"
]

ALL_PROJECT_DEPENDENCIES = CORE_DEPENDENCIES_INDIVIDUAL + PROJECT_DEPENDENCIES_PARAMETRIZED

@pytest.mark.use_real_numpy
def test_import_jpype():
    """Tests if jpype can be imported."""
    try:
        import jpype
        print(f"JPype version: {getattr(jpype, '__version__', 'N/A')}")
    except ImportError as e:
        pytest.fail(f"Erreur lors de l'importation de JPype: {e}")
    except Exception as e:
        pytest.fail(f"Erreur inattendue lors de l'importation de JPype: {e}")

@pytest.mark.use_real_numpy
def test_import_numpy():
    """Tests if numpy can be imported."""
    try:
        import numpy
        print(f"NumPy version: {getattr(numpy, '__version__', 'N/A')}")
    except ImportError as e:
        pytest.fail(f"Erreur lors de l'importation de NumPy: {e}")
    except Exception as e:
        pytest.fail(f"Erreur inattendue lors de l'importation de NumPy: {e}")

@pytest.mark.use_real_numpy
def test_import_torch():
    """Tests if torch can be imported."""
    try:
        import torch
        print(f"PyTorch version: {getattr(torch, '__version__', 'N/A')}")
    except ImportError as e:
        pytest.fail(f"Erreur lors de l'importation de PyTorch: {e}")
    except Exception as e:
        pytest.fail(f"Erreur inattendue lors de l'importation de PyTorch: {e}")

@pytest.mark.use_real_numpy
def test_import_transformers():
    """Tests if transformers can be imported."""
    try:
        import transformers
        print(f"Transformers version: {getattr(transformers, '__version__', 'N/A')}")
    except ImportError as e:
        pytest.fail(f"Erreur lors de l'importation de Transformers: {e}")
    except Exception as e:
        pytest.fail(f"Erreur inattendue lors de l'importation de Transformers: {e}")

@pytest.mark.use_real_numpy
def test_import_networkx():
    """Tests if networkx can be imported."""
    try:
        import networkx
        print(f"NetworkX version: {getattr(networkx, '__version__', 'N/A')}")
    except ImportError as e:
        pytest.fail(f"Erreur lors de l'importation de NetworkX: {e}")
    except Exception as e:
        pytest.fail(f"Erreur inattendue lors de l'importation de NetworkX: {e}")

@pytest.mark.use_real_numpy
@pytest.mark.parametrize("dependency", PROJECT_DEPENDENCIES_PARAMETRIZED)
def test_parametrized_dependency_import(dependency):
    """Vérifie que chaque dépendance majeure paramétrée peut être importée."""
    try:
        importlib.import_module(dependency)
        # Optionnel: afficher la version si disponible
        # module = importlib.import_module(dependency)
        # print(f"{dependency} version: {getattr(module, '__version__', 'N/A')}")
    except ImportError as e:
        pytest.fail(f"Échec de l'importation de la dépendance '{dependency}': {e}")
    except Exception as e:
        pytest.fail(f"Erreur inattendue lors de l'importation de '{dependency}': {e}")