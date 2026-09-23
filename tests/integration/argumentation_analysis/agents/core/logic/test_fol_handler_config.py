import pytest
import os
from unittest.mock import patch, MagicMock

# Importer le module config pour pouvoir le recharger
from argumentation_analysis.core import config
from argumentation_analysis.agents.core.logic.fol_handler import FOLHandler
from argumentation_analysis.agents.core.logic.tweety_initializer import (
    TweetyInitializer,
)


@pytest.fixture
def mock_belief_set():
    """Fixture to create a mock FolBeliefSet."""
    bs = MagicMock()
    bs.toString.return_value = "some_formula(a)."
    bs.size.return_value = 1
    # A FolBeliefSet is a Java Collection, which the LADR writer iterates
    # (#2482, #2504): this one is empty.
    bs.__iter__.side_effect = lambda: iter([])
    return bs


# --- Tests Refactorisés avec Paramétrisation ---


@pytest.mark.parametrize(
    "solver_choice, should_mock_prover9",
    [
        ("tweety", False),
        ("prover9", True),
    ],
)
def test_fol_query_solver_dispatch(
    solver_choice, should_mock_prover9, mock_belief_set, monkeypatch
):
    """
    Tests that fol_query correctly dispatches to the right solver based on configuration.
    This replaces the previous separate tests.
    """
    # NB: pas d'importlib.reload(config) ici — il remplaçait l'objet settings
    # du module partagé, orphelinant les références figées des tests suivants
    # (tripwire #1804 : test_invoke_modal_logic_reaches_solver basculait sur
    # SPASS via les défauts du nouvel objet).
    # #2482: the query is parsed against the KB's signature, which a mock
    # belief set does not carry, and Prover9's answer is read from its stdout;
    # an undecided run falls back to Tweety, so the double must decide: it
    # ends like the binary's output, with its proof count and exit (#2506).
    # The LADR writer needs the parsed Java formula (#2504), which a mock
    # query is not, so the input it builds is doubled too.
    with patch(
        "argumentation_analysis.agents.core.logic.fol_handler._prover9_input",
        return_value="formulas(goals).\nquery(a).\nend_of_list.\n",
    ), patch(
        "argumentation_analysis.agents.core.logic.fol_handler.run_prover9",
        return_value="THEOREM PROVED\n\nExiting with 1 proof.\n\n"
        "Process 1 exit (max_proofs) Wed Sep 23 21:10:43 2026\n",
    ) as mock_run_prover9, patch.object(
        FOLHandler, "_fol_query_with_tweety"
    ) as mock_tweety_query, patch.object(
        FOLHandler, "_parse_query", return_value=MagicMock()
    ), patch(
        "argumentation_analysis.agents.core.logic.fol_handler.settings"
    ) as mock_settings:
        mock_settings.solver = config.SolverChoice(solver_choice)

        # Configurer le handler en fonction du test
        if should_mock_prover9:
            handler = FOLHandler()  # Pas d'initialiseur pour prover9
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


@pytest.mark.parametrize(
    "solver_choice, should_mock_prover9",
    [
        ("tweety", False),
        ("prover9", True),
    ],
)
@pytest.mark.asyncio
async def test_fol_consistency_solver_dispatch(
    solver_choice, should_mock_prover9, mock_belief_set, monkeypatch
):
    """
    Tests that fol_check_consistency correctly dispatches to the right solver.
    """
    with patch.object(
        FOLHandler, "_fol_check_consistency_with_prover9"
    ) as mock_prover9_impl, patch.object(
        FOLHandler, "_fol_check_consistency_with_tweety"
    ) as mock_tweety_impl, patch(
        "argumentation_analysis.agents.core.logic.fol_handler.settings"
    ) as mock_settings:
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
