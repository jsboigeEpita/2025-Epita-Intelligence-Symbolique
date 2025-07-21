import pytest
import os
import importlib
from unittest.mock import patch, MagicMock

# Importer le module config pour pouvoir le recharger
from argumentation_analysis.core import config
from argumentation_analysis.agents.core.logic.fol_handler import FOLHandler
from argumentation_analysis.agents.core.logic.tweety_initializer import TweetyInitializer

@pytest.fixture
def mock_belief_set():
    """Fixture to create a mock FolBeliefSet."""
    bs = MagicMock()
    bs.toString.return_value = "some_formula(a)."
    bs.size.return_value = 1
    return bs

# --- Tests Refactorisés avec Paramétrisation ---

@pytest.mark.parametrize("solver_choice, should_mock_prover9", [
    ("tweety", False),
    ("prover9", True),
])
def test_fol_query_solver_dispatch(solver_choice, should_mock_prover9, mock_belief_set, monkeypatch):
    """
    Tests that fol_query correctly dispatches to the right solver based on configuration.
    This replaces the previous separate tests.
    """
    # Recharger la configuration au cas où
    importlib.reload(config)

    with patch('argumentation_analysis.agents.core.logic.fol_handler.run_prover9') as mock_run_prover9, \
         patch.object(FOLHandler, '_fol_query_with_tweety') as mock_tweety_query, \
         patch('argumentation_analysis.agents.core.logic.fol_handler.settings') as mock_settings:
        
        mock_settings.solver = config.SolverChoice(solver_choice)

        # Configurer le handler en fonction du test
        if should_mock_prover9:
            handler = FOLHandler() # Pas d'initialiseur pour prover9
        else:
            mock_initializer = MagicMock(spec=TweetyInitializer)
            handler = FOLHandler(initializer_instance=mock_initializer)

        # Exécuter la méthode
        handler.fol_query(mock_belief_set, "query(a)")

        # Vérifier que le bon chemin a été pris
        if should_mock_prover9:
            mock_run_prover9.assert_called_once()
            mock_tweety_query.assert_not_called()
        else:
            mock_run_prover9.assert_not_called()
            mock_tweety_query.assert_called_once()

@pytest.mark.parametrize("solver_choice, should_mock_prover9", [
    ("tweety", False),
    ("prover9", True),
])
@pytest.mark.asyncio
async def test_fol_consistency_solver_dispatch(solver_choice, should_mock_prover9, mock_belief_set, monkeypatch):
    """
    Tests that fol_check_consistency correctly dispatches to the right solver.
    """
    importlib.reload(config)
    
    with patch.object(FOLHandler, '_fol_check_consistency_with_prover9') as mock_prover9_impl, \
         patch.object(FOLHandler, '_fol_check_consistency_with_tweety') as mock_tweety_impl, \
         patch('argumentation_analysis.agents.core.logic.fol_handler.settings') as mock_settings:
        
        mock_settings.solver = config.SolverChoice(solver_choice)
        
        # Pour rendre les mocks awaitable
        async def async_return_true(*args, **kwargs):
            return (True, "Consistent")
        mock_prover9_impl.return_value = async_return_true()
        mock_tweety_impl.return_value = async_return_true()

        # Configurer le handler
        if should_mock_prover9:
            handler = FOLHandler()
        else:
            mock_initializer = MagicMock(spec=TweetyInitializer)
            handler = FOLHandler(initializer_instance=mock_initializer)

        await handler.fol_check_consistency(mock_belief_set)

        if should_mock_prover9:
            mock_prover9_impl.assert_awaited_once()
            mock_tweety_impl.assert_not_called()
        else:
            mock_prover9_impl.assert_not_called()
            mock_tweety_impl.assert_awaited_once()
