import os
from unittest.mock import patch

# Les réglages se lisent à la construction : ces tests construisent un
# ArgAnalysisSettings() neuf sous l'environnement mocké. Ils ne rechargent plus
# le module (importlib.reload) : un reload remplace `config.settings` et
# `ModalSolverChoice` pour toute la session, et un test qui a figé l'ancien objet
# épingle alors un objet que plus personne ne lit (#1804, #2471).


def test_default_fol_solver_is_eprover():
    """
    Vérifie que le solveur FOL par défaut est 'eprover' lorsqu'aucune variable
    d'environnement n'est définie (#940 : eprover est le défaut robust, tweety
    est désormais un fallback de dernier recours seulement).
    """
    # S'assurer que la variable d'env n'est pas définie pour ce test
    with patch.dict(os.environ, {}, clear=True):
        from argumentation_analysis.core import config

        assert config.ArgAnalysisSettings().solver == config.SolverChoice.EPROVER


def test_solver_loads_from_environment_variable():
    """
    Vérifie que le solveur est correctement défini sur 'prover9' lorsque
    la variable d'environnement ARG_ANALYSIS_SOLVER est positionnée.
    """
    with patch.dict(os.environ, {"ARG_ANALYSIS_SOLVER": "prover9"}, clear=True):
        from argumentation_analysis.core import config

        assert config.ArgAnalysisSettings().solver == config.SolverChoice.PROVER9


def test_solver_enum_values():
    """Vérifie les valeurs textuelles de l'énumération SolverChoice."""
    from argumentation_analysis.core.config import SolverChoice

    assert SolverChoice.TWEETY.value == "tweety"
    assert SolverChoice.PROVER9.value == "prover9"
