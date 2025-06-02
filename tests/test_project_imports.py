# -*- coding: utf-8 -*-
import importlib
import pytest

# Liste des dépendances majeures du projet à vérifier
PROJECT_DEPENDENCIES = [
    "numpy", "pandas", "scipy", "sklearn", "nltk", "spacy",
    "torch", "transformers", "pydantic", "requests", "matplotlib",
    "seaborn", "networkx", "dotenv", "semantic_kernel",
    "pytest", "coverage", "cryptography", "jpype"
]

@pytest.mark.use_real_numpy
@pytest.mark.parametrize("dependency", PROJECT_DEPENDENCIES)
def test_dependency_import(dependency):
    """Vérifie que chaque dépendance majeure peut être importée."""
    try:
        importlib.import_module(dependency)
    except ImportError as e:
        pytest.fail(f"Échec de l'importation de la dépendance '{dependency}': {e}")
    except Exception as e:
        pytest.fail(f"Erreur inattendue lors de l'importation de '{dependency}': {e}")