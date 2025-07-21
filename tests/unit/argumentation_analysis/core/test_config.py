import os
import importlib
from unittest.mock import patch

# Important: il faut importer le module config APRÈS avoir mocké l'environnement
# ou utiliser importlib.reload pour forcer la relecture.

def test_default_solver_is_tweety():
    """
    Vérifie que le solveur par défaut est 'tweety' lorsqu'aucune variable
    d'environnement n'est définie.
    """
    # S'assurer que la variable d'env n'est pas définie pour ce test
    with patch.dict(os.environ, {}, clear=True):
        from argumentation_analysis.core import config
        # Forcer la relecture du module pour prendre en compte l'environnement mocké
        importlib.reload(config)
        assert config.settings.solver == config.SolverChoice.TWEETY

def test_solver_loads_from_environment_variable():
    """
    Vérifie que le solveur est correctement défini sur 'prover9' lorsque
    la variable d'environnement ARG_ANALYSIS_SOLVER est positionnée.
    """
    with patch.dict(os.environ, {"ARG_ANALYSIS_SOLVER": "prover9"}, clear=True):
        from argumentation_analysis.core import config
        importlib.reload(config)
        assert config.settings.solver == config.SolverChoice.PROVER9

def test_solver_enum_values():
    """Vérifie les valeurs textuelles de l'énumération SolverChoice."""
    from argumentation_analysis.core.config import SolverChoice
    assert SolverChoice.TWEETY.value == "tweety"
    assert SolverChoice.PROVER9.value == "prover9"
