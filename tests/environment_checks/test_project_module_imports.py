# tests/environment_checks/test_project_module_imports.py
import pytest
import importlib
import logging  # Gardé pour l'exemple de logging.info, peut être enlevé si non utilisé.

# Liste des modules du projet à vérifier
PROJECT_MODULES_TO_CHECK = [
    "argumentation_analysis.core.jvm_setup",
    "argumentation_analysis.core.state_manager_plugin",  # Ancien nom potentiel, à vérifier
    "argumentation_analysis.core.shared_state",
    "argumentation_analysis.agents.core.informal.informal_agent",
    "argumentation_analysis.agents.core.extract.extract_agent",
    "argumentation_analysis.orchestration.analysis_runner",
    # Ajoutez ici d'autres modules internes importants si nécessaire
]


@pytest.mark.parametrize("module_name", PROJECT_MODULES_TO_CHECK)
def test_import_project_module(module_name):
    """Tests if a key project module can be imported."""
    try:
        importlib.import_module(module_name)
        # Optionnel: logging pour garder une trace visible avec -s
        logging.info(f"Module {module_name} importé avec succès.")
        print(f"Module {module_name} importé avec succès.")
    except ImportError as e:
        # Re-lever l'exception pour voir le traceback complet
        print(
            f"DEBUG: ImportError pour {module_name}: {e}"
        )  # Ajout d'un print pour visibilité
        raise
    except Exception as e:
        # Re-lever aussi pour les autres exceptions inattendues
        print(
            f"DEBUG: Exception pour {module_name}: {e}"
        )  # Ajout d'un print pour visibilité
        raise


EXTERNAL_DEPENDENCIES_FOR_PROJECT_CONTEXT = [
    "semantic_kernel",
    "pandas",
    "numpy",
    "jpype",
]


@pytest.mark.use_real_numpy  # Ajout du marqueur ici
@pytest.mark.parametrize("module_name", EXTERNAL_DEPENDENCIES_FOR_PROJECT_CONTEXT)
def test_import_external_dependency_for_project(module_name):
    """Tests if an external dependency relevant to project modules can be imported."""
    try:
        importlib.import_module(module_name)
        # Optionnel: logging pour garder une trace visible avec -s
        logging.info(f"Dépendance externe {module_name} importée avec succès.")
        print(f"Dépendance externe {module_name} importée avec succès.")
    except ImportError as e:
        pytest.fail(
            f"Erreur lors de l'importation de la dépendance externe {module_name}: {e}"
        )
    except Exception as e:
        pytest.fail(f"Erreur inattendue lors de l'importation de {module_name}: {e}")
