"""Tests for external solver routing in spectacular workflow (#504).

Verifies that fol_solver and modal_solver phases exist in spectacular,
are registered as services in the registry, and have state writers.
"""

from unittest.mock import MagicMock, patch


class TestExternalSolverSpectacular:
    """Verify external solver phases in spectacular workflow."""

    def test_spectacular_has_fol_solver_phase(self):
        from argumentation_analysis.orchestration.workflows import (
            build_spectacular_workflow,
        )

        wf = build_spectacular_workflow()
        phase = {p.name: p for p in wf.phases}
        assert "fol_solver" in phase
        assert phase["fol_solver"].capability == "external_fol_solving"
        assert "fol" in phase["fol_solver"].depends_on
        assert phase["fol_solver"].optional is True

    def test_spectacular_has_modal_solver_phase(self):
        from argumentation_analysis.orchestration.workflows import (
            build_spectacular_workflow,
        )

        wf = build_spectacular_workflow()
        phase = {p.name: p for p in wf.phases}
        assert "modal_solver" in phase
        assert phase["modal_solver"].capability == "external_modal_solving"
        assert "modal" in phase["modal_solver"].depends_on
        assert phase["modal_solver"].optional is True

    def test_spectacular_phase_count_with_solvers(self):
        from argumentation_analysis.orchestration.workflows import (
            build_spectacular_workflow,
        )

        wf = build_spectacular_workflow()
        assert len(wf.phases) == 27

    def test_external_fol_solver_service_registered(self):
        from argumentation_analysis.orchestration.registry_setup import setup_registry

        registry = setup_registry()
        providers = registry.find_for_capability("external_fol_solving")
        names = [p.name for p in providers]
        assert "external_fol_solver_service" in names
        provider = next(p for p in providers if p.name == "external_fol_solver_service")
        assert provider.invoke is not None

    def test_external_modal_solver_service_registered(self):
        from argumentation_analysis.orchestration.registry_setup import setup_registry

        registry = setup_registry()
        providers = registry.find_for_capability("external_modal_solving")
        names = [p.name for p in providers]
        assert "external_modal_solver_service" in names
        provider = next(
            p for p in providers if p.name == "external_modal_solver_service"
        )
        assert provider.invoke is not None

    def test_external_fol_solver_state_writer(self):
        from argumentation_analysis.orchestration.state_writers import (
            _write_external_fol_solver_to_state,
        )

        state = MagicMock()
        state.fol_analysis_results = {}
        output = {
            "formulas": ["P(a)", "Q(b)"],
            "consistent": True,
            "solver": "eprover",
        }
        _write_external_fol_solver_to_state(output, state, {})
        assert state.fol_analysis_results == {
            "external_solver": "eprover",
            "external_consistent": True,
        }

    def test_external_modal_solver_state_writer(self):
        from argumentation_analysis.orchestration.state_writers import (
            _write_external_modal_solver_to_state,
        )

        state = MagicMock()
        state.modal_analysis_results = {}
        output = {
            "formulas": ["[]p", "<>q"],
            "valid": True,
            "solver": "spass",
        }
        _write_external_modal_solver_to_state(output, state, {})
        assert state.modal_analysis_results == {
            "external_solver": "spass",
            "external_valid": True,
        }

    def test_invoke_external_fol_solver_fallback(self):
        """When no external solver is available, falls back to TweetyBridge."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_external_fol_solver,
        )
        import asyncio

        async def _run():
            ctx = {
                "phase_fol_output": {
                    "formulas": ["Asserted(arg1)"],
                    "fol_signature": [],
                }
            }
            result = await _invoke_external_fol_solver("test text", ctx)
            assert "solver" in result
            assert result["logic_type"] == "first_order"

        asyncio.get_event_loop().run_until_complete(_run())

    def test_invoke_external_modal_solver_fallback(self):
        """When SPASS is unavailable, falls back to TweetyBridge."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_external_modal_solver,
        )
        import asyncio

        async def _run():
            ctx = {
                "phase_modal_output": {
                    "formulas": ["[]p -> <>q"],
                    "modalities": ["necessity"],
                }
            }
            result = await _invoke_external_modal_solver("test text", ctx)
            assert "solver" in result
            assert result["logic_type"] == "modal"

        asyncio.get_event_loop().run_until_complete(_run())
