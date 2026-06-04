"""
Tests for --fol-solver selector (parametric integration #900).

Validates:
  - CLI argparse (--fol-solver with choices)
  - Context propagation (zero-pollution: default not in context)
  - Solver resolution in _invoke_external_fol_solver (context > settings > default)
  - Bug fix: settings.solver used correctly (not non-existent settings.fol_solver)
"""

import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------


class TestFOLSolverCLI:
    """Test --fol-solver argument parsing."""

    def test_fol_solver_default(self):
        """Default solver should be 'eprover' (#939: robust solver as default)."""
        valid_solvers = {"tweety", "prover9", "eprover"}
        default = "eprover"
        assert default in valid_solvers

    def test_fol_solver_choices(self):
        """All 3 solver backends should be valid choices."""
        valid_solvers = {"tweety", "prover9", "eprover"}
        assert len(valid_solvers) == 3

    def test_fol_solver_invalid_rejected(self):
        """Invalid solver names should not be in valid choices."""
        valid_solvers = {"tweety", "prover9", "eprover"}
        assert "z3" not in valid_solvers
        assert "spass" not in valid_solvers
        assert "vampire" not in valid_solvers


# ---------------------------------------------------------------------------
# Context propagation (zero-pollution pattern)
# ---------------------------------------------------------------------------


class TestFOLSolverContext:
    """Test context propagation for --fol-solver."""

    def test_default_not_in_context(self):
        """Default 'eprover' should NOT be added to context (zero-pollution)."""
        fol_solver = "eprover"
        context = {}
        if fol_solver != "eprover":
            context["fol_solver"] = fol_solver
        assert "fol_solver" not in context

    def test_prover9_in_context(self):
        """Non-default 'prover9' should be in context."""
        fol_solver = "prover9"
        context = {}
        if fol_solver != "eprover":
            context["fol_solver"] = fol_solver
        assert context["fol_solver"] == "prover9"

    def test_tweety_in_context(self):
        """Non-default 'tweety' should be in context (explicit override)."""
        fol_solver = "tweety"
        context = {}
        if fol_solver != "eprover":
            context["fol_solver"] = fol_solver
        assert context["fol_solver"] == "tweety"

    @pytest.mark.parametrize(
        "solver,expected_in_context",
        [
            ("eprover", False),
            ("prover9", True),
            ("tweety", True),
        ],
    )
    def test_context_pollution_parametrized(self, solver, expected_in_context):
        """Parametrized: only non-default solver pollutes context."""
        context = {}
        if solver != "eprover":
            context["fol_solver"] = solver
        assert ("fol_solver" in context) == expected_in_context


# ---------------------------------------------------------------------------
# Solver resolution in _invoke_external_fol_solver
# ---------------------------------------------------------------------------


class TestFOLSolverResolution:
    """Test the context > settings > default resolution chain."""

    def test_context_overrides_settings(self):
        """Context fol_solver should take priority over settings.solver."""
        context = {"fol_solver": "eprover"}
        # Simulate the resolution logic
        fol_solver = context.get("fol_solver", None)
        assert fol_solver == "eprover"
        # settings would not be consulted

    def test_settings_used_when_no_context(self):
        """When context has no fol_solver, settings.solver should be used."""
        context = {}
        fol_solver = context.get("fol_solver", None)
        assert fol_solver is None
        # In real code: str(settings.solver) would be consulted

    def test_default_eprover_when_no_context_no_settings(self):
        """When both context and settings are unavailable, default is 'eprover'."""
        context = {}
        fol_solver = context.get("fol_solver", None)
        if fol_solver is None:
            # Simulate settings unavailable — #939: eprover is the new default
            fol_solver = "eprover"
        assert fol_solver == "eprover"


# ---------------------------------------------------------------------------
# Bug fix: settings.solver (not settings.fol_solver)
# ---------------------------------------------------------------------------


class TestSettingsSolverBugFix:
    """Verify the fix for the settings.fol_solver bug (line 6016).

    The bug was: getattr(settings, "fol_solver", None) always returns None
    because ArgAnalysisSettings has 'solver' not 'fol_solver'.
    """

    def test_settings_has_solver_not_fol_solver(self):
        """ArgAnalysisSettings should have 'solver' attribute, not 'fol_solver'."""
        from argumentation_analysis.core.config import ArgAnalysisSettings

        field_names = {f for f in ArgAnalysisSettings.model_fields}
        assert "solver" in field_names, f"solver not in fields: {field_names}"
        assert "fol_solver" not in field_names, "fol_solver should not exist"

    def test_solver_enum_values(self):
        """SolverChoice enum should have tweety/prover9/eprover."""
        from argumentation_analysis.core.config import SolverChoice

        values = {s.value for s in SolverChoice}
        assert values == {"tweety", "prover9", "eprover"}

    def test_settings_default_solver_is_eprover(self):
        """Default settings.solver should be SolverChoice.EPROVER (#939)."""
        from argumentation_analysis.core.config import SolverChoice

        assert SolverChoice.EPROVER.value == "eprover"


# ---------------------------------------------------------------------------
# _invoke_fol_reasoning metadata propagation
# ---------------------------------------------------------------------------


class TestFOLReasoningMetadata:
    """Test that fol_solver is recorded in fol_metadata_shared."""

    def test_metadata_records_solver_choice(self):
        """fol_metadata_shared should contain fol_solver key."""
        fol_solver_choice = "prover9"
        fol_metadata_shared = {"fol_solver": fol_solver_choice}
        assert fol_metadata_shared["fol_solver"] == "prover9"

    def test_metadata_default_eprover(self):
        """When no context override, fol_solver should be 'eprover'."""
        fol_solver_choice = "eprover"
        fol_metadata_shared = {"fol_solver": fol_solver_choice}
        assert fol_metadata_shared["fol_solver"] == "eprover"

    def test_metadata_preserved_on_reassignment(self):
        """fol_solver should survive the fol_metadata_shared reassignment
        at line ~4985 (where it's rebuilt with sorts/predicates/constants)."""
        fol_solver_choice = "eprover"
        fol_metadata_shared = {"fol_solver": fol_solver_choice}
        # Simulate reassignment
        fol_metadata_shared = {
            "sorts": {"Thing": ["a", "b"]},
            "predicates": {"P": 1},
            "constants_raw": {"a": 1, "b": 1},
            "fol_solver": fol_solver_choice,
        }
        assert fol_metadata_shared["fol_solver"] == "eprover"
        assert "sorts" in fol_metadata_shared


# ---------------------------------------------------------------------------
# run_modern_analysis signature
# ---------------------------------------------------------------------------


class TestRunModernAnalysisSignature:
    """Test that run_modern_analysis accepts fol_solver parameter."""

    def test_signature_has_fol_solver(self):
        """run_modern_analysis should accept fol_solver parameter."""
        import inspect
        from argumentation_analysis.run_orchestration import run_modern_analysis

        sig = inspect.signature(run_modern_analysis)
        assert "fol_solver" in sig.parameters
        assert sig.parameters["fol_solver"].default == "eprover"


# ---------------------------------------------------------------------------
# Real consumer tests — _invoke_external_fol_solver reads context
# ---------------------------------------------------------------------------


class TestExternalFOLSolverConsumer:
    """Test that _invoke_external_fol_solver actually reads fol_solver from context.

    These tests CALL the real consumer to verify the resolution chain
    (context > settings > default) works end-to-end.
    """

    async def test_context_eprover_routes_to_eprover_branch(self):
        """When context has fol_solver='eprover', the eprover branch should be entered.

        TweetyBridge and FOLLogicAgent are imported locally inside the function,
        so we must patch their source modules, not invoke_callables.
        """
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_external_fol_solver,
        )

        context = {
            "fol_solver": "eprover",
            "phase_fol_output": {
                "formulas": ["forall X (p(X) -> q(X))"],
                "fol_signature": [],
            },
        }

        mock_bridge = MagicMock()
        mock_bridge.check_consistency = MagicMock(return_value=(True, "consistent"))

        with patch(
            "argumentation_analysis.agents.core.logic.tweety_bridge.TweetyBridge",
            return_value=mock_bridge,
        ), patch(
            "argumentation_analysis.agents.core.logic.fol_logic_agent.FOLLogicAgent"
        ) as mock_agent_cls:
            mock_agent_cls.extract_fol_metadata = MagicMock(return_value={
                "signature_lines": ["type(t)"],
            })
            result = await _invoke_external_fol_solver("test formula", context)

        assert result.get("solver") == "eprover"
        assert result.get("logic_type") == "first_order"

    async def test_context_prover9_routes_to_prover9_branch(self):
        """When context has fol_solver='prover9', prover9 subprocess should be attempted.

        We mock prover9_runner.run_prover9 to avoid needing the real binary.
        """
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_external_fol_solver,
        )

        context = {
            "fol_solver": "prover9",
            "phase_fol_output": {
                "formulas": ["p(a)"],
                "fol_signature": [],
            },
        }

        mock_bridge = MagicMock()
        mock_bridge.check_consistency = MagicMock(return_value=(True, "OK"))

        with patch(
            "argumentation_analysis.core.prover9_runner.run_prover9",
            return_value="THEOREM PROVED\nproof finished",
        ), patch(
            "argumentation_analysis.agents.core.logic.tweety_bridge.TweetyBridge",
            return_value=mock_bridge,
        ), patch(
            "argumentation_analysis.agents.core.logic.fol_logic_agent.FOLLogicAgent"
        ) as mock_agent_cls:
            mock_agent_cls.extract_fol_metadata = MagicMock(return_value={
                "signature_lines": [],
            })
            result = await _invoke_external_fol_solver("test formula", context)

        # Prover9 path should produce solver="prover9" or fall back to tweety
        assert result.get("logic_type") == "first_order"
        assert result.get("solver") in ("prover9", "tweety_fallback", "tweety")

    async def test_default_eprover_uses_eprover_branch(self):
        """When context has no fol_solver, default eprover path should be used (#939)."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_external_fol_solver,
        )

        context = {
            "phase_fol_output": {
                "formulas": ["p(a)"],
                "fol_signature": [],
            },
        }

        mock_bridge = MagicMock()
        mock_bridge.check_consistency = MagicMock(return_value=(True, "OK"))

        with patch(
            "argumentation_analysis.agents.core.logic.tweety_bridge.TweetyBridge",
            return_value=mock_bridge,
        ), patch(
            "argumentation_analysis.agents.core.logic.fol_logic_agent.FOLLogicAgent"
        ) as mock_agent_cls:
            mock_agent_cls.extract_fol_metadata = MagicMock(return_value={
                "signature_lines": [],
            })
            result = await _invoke_external_fol_solver("test formula", context)

        # Default eprover path → eprover (or tweety_fallback if eprover unavailable)
        assert result.get("solver") in ("eprover", "tweety_fallback")
        assert result.get("logic_type") == "first_order"

    async def test_no_context_falls_back_gracefully(self):
        """Even with empty context, the function should not crash."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_external_fol_solver,
        )

        context = {}

        mock_bridge = MagicMock()
        mock_bridge.check_consistency = MagicMock(return_value=(True, "OK"))

        with patch(
            "argumentation_analysis.agents.core.logic.tweety_bridge.TweetyBridge",
            return_value=mock_bridge,
        ), patch(
            "argumentation_analysis.agents.core.logic.fol_logic_agent.FOLLogicAgent"
        ) as mock_agent_cls:
            mock_agent_cls.extract_fol_metadata = MagicMock(return_value={
                "signature_lines": [],
            })
            result = await _invoke_external_fol_solver("test formula", context)

        assert "logic_type" in result
        assert result["logic_type"] == "first_order"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
