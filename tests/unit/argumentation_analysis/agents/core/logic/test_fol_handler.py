"""Tests for FOL handler solver fallback (#949).

Verifies that when the configured external solver (eprover/prover9) is absent,
FOLHandler gracefully falls back to the in-JVM Tweety reasoner — mirroring
the modal pattern.  A ``solver_fallback`` flag is returned so callers can
track degradation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestFOLSolverFallback:
    """Test graceful solver downgrade when external binary is absent."""

    @pytest.fixture
    def handler(self):
        """Create a FOLHandler with a mock initializer."""
        from argumentation_analysis.agents.core.logic.fol_handler import FOLHandler
        from argumentation_analysis.agents.core.logic.tweety_initializer import (
            TweetyInitializer,
        )

        mock_initializer = MagicMock(spec=TweetyInitializer)
        mock_initializer.get_fol_parser.return_value = MagicMock()

        with patch(
            "argumentation_analysis.agents.core.logic.fol_handler.settings"
        ) as mock_settings:
            mock_settings.solver = MagicMock()
            mock_settings.solver.value = "eprover"
            # Force tweety path for constructor
            from argumentation_analysis.core.config import SolverChoice
            mock_settings.solver = SolverChoice.TWEETY
            handler = FOLHandler(initializer_instance=mock_initializer)
            # Now override to eprover for test
            mock_settings.solver = SolverChoice.EPROVER

        handler._initializer_instance = mock_initializer
        return handler

    @pytest.mark.asyncio
    async def test_eprover_absent_falls_back_to_tweety_consistency(self, handler):
        """When eprover binary is absent, consistency check uses Tweety fallback."""
        from argumentation_analysis.core.config import SolverChoice

        with patch(
            "argumentation_analysis.agents.core.logic.fol_handler.settings"
        ) as mock_settings:
            mock_settings.solver = SolverChoice.EPROVER

            # Mock eprover to raise RuntimeError (binary absent)
            with patch.object(
                handler,
                "_fol_check_consistency_with_eprover",
                new_callable=AsyncMock,
                side_effect=RuntimeError("EProver binary not found"),
            ):
                # Mock tweety fallback to succeed
                with patch.object(
                    handler,
                    "_fol_check_consistency_with_tweety",
                    new_callable=AsyncMock,
                    return_value=(True, "Tweety-based consistency check result: True"),
                ):
                    belief_set = MagicMock()
                    belief_set.size.return_value = 2
                    result = await handler.fol_check_consistency(belief_set)

        # Result should be (is_consistent, msg, solver_fallback=True)
        assert len(result) == 3
        is_consistent, msg, solver_fallback = result
        assert is_consistent is True
        assert solver_fallback is True, "solver_fallback flag must be True when degraded"
        assert "Tweety" in msg

    @pytest.mark.asyncio
    async def test_eprover_present_no_fallback(self, handler):
        """When eprover is available, no fallback occurs."""
        from argumentation_analysis.core.config import SolverChoice

        with patch(
            "argumentation_analysis.agents.core.logic.fol_handler.settings"
        ) as mock_settings:
            mock_settings.solver = SolverChoice.EPROVER

            with patch.object(
                handler,
                "_fol_check_consistency_with_eprover",
                new_callable=AsyncMock,
                return_value=(False, "EProver-based consistency check result: False"),
            ):
                belief_set = MagicMock()
                belief_set.size.return_value = 2
                result = await handler.fol_check_consistency(belief_set)

        # No fallback — result is (is_consistent, msg) from eprover directly
        assert len(result) == 2
        is_consistent, msg = result
        assert is_consistent is False
        assert "EProver" in msg

    @pytest.mark.asyncio
    async def test_tweety_path_no_fallback(self, handler):
        """When solver is Tweety directly, no fallback mechanism is needed."""
        from argumentation_analysis.core.config import SolverChoice

        with patch(
            "argumentation_analysis.agents.core.logic.fol_handler.settings"
        ) as mock_settings:
            mock_settings.solver = SolverChoice.TWEETY

            with patch.object(
                handler,
                "_fol_check_consistency_with_tweety",
                new_callable=AsyncMock,
                return_value=(True, "Tweety-based consistency check result: True"),
            ):
                belief_set = MagicMock()
                belief_set.size.return_value = 1
                result = await handler.fol_check_consistency(belief_set)

        # Direct Tweety path — 2-tuple, no fallback flag
        assert len(result) == 2
        is_consistent, msg = result
        assert is_consistent is True

    def test_eprover_absent_falls_back_to_tweety_query(self, handler):
        """When eprover binary is absent, FOL query uses Tweety fallback."""
        from argumentation_analysis.core.config import SolverChoice

        with patch(
            "argumentation_analysis.agents.core.logic.fol_handler.settings"
        ) as mock_settings:
            mock_settings.solver = SolverChoice.EPROVER

            with patch.object(
                handler,
                "_fol_query_with_eprover",
                side_effect=RuntimeError("EProver binary not found"),
            ):
                with patch.object(
                    handler,
                    "_fol_query_with_tweety",
                    return_value=True,
                ):
                    belief_set = MagicMock()
                    result = handler.fol_query(belief_set, "mortal(socrates)")

        # Result is (entailed, solver_fallback)
        entailed, solver_fallback = result
        assert entailed is True
        assert solver_fallback is True, "solver_fallback must be True on query degradation"

    def test_eprover_present_no_query_fallback(self, handler):
        """When eprover is available, query returns (entailed, False)."""
        from argumentation_analysis.core.config import SolverChoice

        with patch(
            "argumentation_analysis.agents.core.logic.fol_handler.settings"
        ) as mock_settings:
            mock_settings.solver = SolverChoice.EPROVER

            with patch.object(
                handler,
                "_fol_query_with_eprover",
                return_value=True,
            ):
                belief_set = MagicMock()
                result = handler.fol_query(belief_set, "mortal(socrates)")

        entailed, solver_fallback = result
        assert entailed is True
        assert solver_fallback is False, "solver_fallback must be False when eprover works"

    @pytest.mark.asyncio
    async def test_both_solvers_absent_raises(self, handler):
        """When both external and Tweety solvers fail, RuntimeError is raised."""
        from argumentation_analysis.core.config import SolverChoice

        with patch(
            "argumentation_analysis.agents.core.logic.fol_handler.settings"
        ) as mock_settings:
            mock_settings.solver = SolverChoice.EPROVER

            with patch.object(
                handler,
                "_fol_check_consistency_with_eprover",
                new_callable=AsyncMock,
                side_effect=RuntimeError("EProver binary not found"),
            ):
                with patch.object(
                    handler,
                    "_fol_check_consistency_with_tweety",
                    new_callable=AsyncMock,
                    side_effect=NotImplementedError("Tweety also failed"),
                ):
                    belief_set = MagicMock()
                    belief_set.size.return_value = 2
                    with pytest.raises(RuntimeError, match="FOL consistency check failed"):
                        await handler.fol_check_consistency(belief_set)
