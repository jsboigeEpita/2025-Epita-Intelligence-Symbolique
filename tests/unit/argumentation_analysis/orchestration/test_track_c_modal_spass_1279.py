"""Track C #1279 — modal routed to vendored SPASS (fail-loud, no OOM→degraded).

Pins the issue #1279 DoD:

  1. When a vendored SPASS binary is detected, ``_invoke_modal_logic`` ROUTES to
     it (flips ``modal_solver`` to SPASS for the call, restored after) — the
     solver that decides without OOM, instead of the SimpleMlReasoner default.
  2. When SPASS/the KB is unavailable, the axis fails loud
     (``unavailable:no-translation`` / ``unavailable:no-solver``) — never a
     silent OOM→None (#1019).

Covers the routing logic (mocked ModalHandler — no JVM), the KB-starvation gate
(cohérent Track B #1278), the state-writer ``modal_status`` passthrough, and the
act2 honest 'Modal indisponible' surfacing. The real-JVM "SPASS decides"
verdict is exercised by ``test_invoke_modal_logic_reaches_solver`` (integration).
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

MODAL_HANDLER_MOD = "argumentation_analysis.agents.core.logic.modal_handler"
TWEETY_INIT_PATH = (
    "argumentation_analysis.agents.core.logic.tweety_initializer.TweetyInitializer"
)


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# DoD #2 — KB starvation → unavailable:no-translation (cohérent Track B)
# ---------------------------------------------------------------------------


class TestModalStarvationNoTranslation:
    """No nl_to_logic modal translation AND no direct formulas → axis is
    unavailable:no-translation, NOT raw-corpus silent degraded."""

    def test_no_formulas_marks_unavailable(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_modal_logic,
        )

        # No phase_nl_to_logic_output, no context["formulas"] → starvation gate.
        result = _run(_invoke_modal_logic("some raw corpus paragraph", {}))
        assert result["modal_status"] == "unavailable:no-translation"
        assert result["valid"] is None
        assert result["formulas"] == []


# ---------------------------------------------------------------------------
# DoD #1 — SPASS routing: flip + restore + decided verdict
# ---------------------------------------------------------------------------


class TestModalSpassRouting:
    """When vendored SPASS is detected (+ prefer flag + default TWEETY),
    ``_invoke_modal_logic`` routes to SPASS and restores the global after."""

    def test_spass_routed_decides_and_restores_global(self):
        from argumentation_analysis.core.config import ModalSolverChoice, settings
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_modal_logic,
        )

        prev = settings.modal_solver
        prev_prefer = settings.modal_prefer_spass_when_available
        settings.modal_solver = ModalSolverChoice.TWEETY
        object.__setattr__(settings, "modal_prefer_spass_when_available", True)
        try:
            mock_handler = MagicMock()
            mock_handler.is_modal_kb_consistent.return_value = (
                True,
                "SPASS: consistent.",
            )
            mock_initializer = MagicMock()
            with (
                patch(MODAL_HANDLER_MOD + ".ModalHandler", return_value=mock_handler),
                patch(
                    MODAL_HANDLER_MOD + "._get_spass_path",
                    return_value="/fake/ext_tools/spass/SPASS.exe",
                ),
                patch(TWEETY_INIT_PATH, return_value=mock_initializer),
            ):
                result = _run(
                    _invoke_modal_logic(
                        "ignored",
                        {"formulas": ["type(p)", "type(q)", "[](p => q)", "p"]},
                    )
                )

            # Routed to SPASS → a real verdict, modal_status=decided.
            assert result["modal_status"] == "decided"
            assert result["valid"] is True
            # solver reflects the SPASS routing (modal_solver.value at call time).
            assert result["solver"] == "spass"
            # ModalHandler was actually driven with the SPASS-routed config.
            assert mock_handler.is_modal_kb_consistent.called
        finally:
            settings.modal_solver = prev
            object.__setattr__(
                settings, "modal_prefer_spass_when_available", prev_prefer
            )

        # The global modal_solver is restored (no leaked side-effect, #1219).
        assert settings.modal_solver == ModalSolverChoice.TWEETY

    def test_prefer_flag_opts_out_of_spass(self):
        """``modal_prefer_spass_when_available=False`` keeps TWEETY even when a
        vendored SPASS is detected — the explicit opt-out the #1219 regression
        test uses to pin the SimpleMlReasoner path."""
        from argumentation_analysis.core.config import ModalSolverChoice, settings
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_modal_logic,
        )

        prev = settings.modal_solver
        prev_prefer = settings.modal_prefer_spass_when_available
        settings.modal_solver = ModalSolverChoice.TWEETY
        object.__setattr__(settings, "modal_prefer_spass_when_available", False)
        try:
            mock_handler = MagicMock()
            mock_handler.is_modal_kb_consistent.return_value = (True, "ok")
            mock_initializer = MagicMock()
            captured = {}

            def _capture_init(initializer_instance=None):
                captured["solver_at_call"] = settings.modal_solver
                return mock_handler

            with (
                patch(MODAL_HANDLER_MOD + ".ModalHandler", side_effect=_capture_init),
                patch(
                    MODAL_HANDLER_MOD + "._get_spass_path",
                    return_value="/fake/SPASS",
                ),
                patch(TWEETY_INIT_PATH, return_value=mock_initializer),
            ):
                result = _run(
                    _invoke_modal_logic("ignored", {"formulas": ["type(p)", "p"]})
                )
            # Opted out → stayed on TWEETY (SimpleMlReasoner), not SPASS.
            assert captured["solver_at_call"] == ModalSolverChoice.TWEETY
            assert result["solver"] == "tweety"
            assert result["modal_status"] == "decided"
        finally:
            settings.modal_solver = prev
            object.__setattr__(
                settings, "modal_prefer_spass_when_available", prev_prefer
            )


# ---------------------------------------------------------------------------
# State writer — modal_status passthrough
# ---------------------------------------------------------------------------


class TestStateWriterModalStatus:
    """_write_modal_to_state carries the honest status as ``message`` (#1279)."""

    def test_unavailable_message_passed_to_state(self):
        from argumentation_analysis.orchestration.state_writers import (
            _write_modal_to_state,
        )

        state = MagicMock()
        output = {
            "formulas": [],
            "valid": None,
            "modalities": [],
            "modal_status": "unavailable:no-solver",
        }
        _write_modal_to_state(output, state, {})

        assert state.add_modal_analysis_result.called
        call = state.add_modal_analysis_result.call_args
        assert call[0][1] is None  # valid preserved as None (not False, #1019)
        assert call.kwargs.get("message") == "unavailable:no-solver"

    def test_decided_keeps_solver_message(self):
        from argumentation_analysis.orchestration.state_writers import (
            _write_modal_to_state,
        )

        state = MagicMock()
        output = {
            "formulas": ["type(p)", "p"],
            "valid": True,
            "modalities": ["necessity"],
            "modal_status": "decided",
            "message": "SPASS: consistent.",
        }
        _write_modal_to_state(output, state, {})

        call = state.add_modal_analysis_result.call_args
        assert call[0][1] is True
        assert call.kwargs.get("message") == "SPASS: consistent."


# ---------------------------------------------------------------------------
# act2 — honest 'Modal indisponible' surfacing
# ---------------------------------------------------------------------------


def _findings_state(modal_results):
    return SimpleNamespace(
        propositional_analysis_results=[],
        fol_analysis_results=[],
        modal_analysis_results=modal_results,
        dung_frameworks={},
    )


class TestAct2ModalIndisponibleSurfacing:
    """When modal is unavailable, the restitution surfaces it honestly
    instead of silence (DoD #2)."""

    def test_unavailable_modal_surfaces_indisponible(self):
        from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
            _collect_formal_findings,
        )

        state = _findings_state(
            [{"valid": None, "message": "unavailable:no-translation"}]
        )
        findings = _collect_formal_findings(state)
        modal = [f for f in findings if f.kind == "modal"]
        assert len(modal) == 1
        assert "indisponible" in modal[0].verdict.lower()

    def test_decided_modal_not_marked_indisponible(self):
        from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
            _collect_formal_findings,
        )

        state = _findings_state([{"valid": True}])
        findings = _collect_formal_findings(state)
        modal = [f for f in findings if f.kind == "modal"]
        assert len(modal) == 1
        assert "indisponible" not in modal[0].verdict.lower()
        assert "consistante" in modal[0].verdict.lower()

    def test_no_modal_results_no_finding(self):
        from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
            _collect_formal_findings,
        )

        state = _findings_state([])
        findings = _collect_formal_findings(state)
        assert not any(f.kind == "modal" for f in findings)
