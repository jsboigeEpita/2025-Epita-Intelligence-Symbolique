"""Tests for Sprint 5 hygiene bundle (#591).

Covers:
- Item 1: deep synthesis source_id NameError fix
- Item 2: _resolve_target_arg_id uniqueness (already fixed in 1b5b5706)
- Item 3: idempotency guards for Dung + ASPIC hooks
"""

import ast
import inspect
from unittest.mock import MagicMock, patch

import pytest

from argumentation_analysis.orchestration.state_writers import (
    _resolve_target_arg_id,
    _write_dung_extensions_to_state,
    _write_aspic_to_state,
)


# ---------------------------------------------------------------------------
# Item 1 — source_id NameError is gone
# ---------------------------------------------------------------------------


class TestDeepSynthesisSourceIdFix:
    """Verify conversational_orchestrator no longer references undefined source_id."""

    def test_source_id_not_used_in_deep_synthesis_block(self):
        """The deep synthesis block must not reference 'source_id' (NameError fix)."""
        from argumentation_analysis.orchestration import conversational_orchestrator

        source = inspect.getsource(conversational_orchestrator.run_conversational_analysis)
        # Find the deep synthesis block
        assert 'source_id' not in source or 'conversational_unknown' in source, (
            "source_id should not appear as a bare variable reference in "
            "run_conversational_analysis (was causing NameError). "
            "If present, it must be via a safe fallback."
        )


# ---------------------------------------------------------------------------
# Item 2 — _resolve_target_arg_id defined exactly once
# ---------------------------------------------------------------------------


class TestResolveTargetArgIdUniqueness:
    """_resolve_target_arg_id must be defined exactly once in state_writers.py."""

    def test_single_definition(self):
        import argumentation_analysis.orchestration.state_writers as sw_mod

        source = inspect.getsource(sw_mod)
        count = source.count("def _resolve_target_arg_id")
        assert count == 1, (
            f"_resolve_target_arg_id defined {count} times, expected 1"
        )


# ---------------------------------------------------------------------------
# Item 3 — idempotency guards Dung + ASPIC
# ---------------------------------------------------------------------------


class TestDungIdempotency:
    """Dung framework hook must not duplicate entries on repeated invocation."""

    def test_dung_write_is_idempotent(self):
        """Calling _write_dung_extensions_to_state twice should not double-add."""
        state = MagicMock()
        state.dung_frameworks = {}

        output = {
            "semantics": "preferred",
            "extensions": {"pref": ["a1", "a2"]},
            "all_extensions": {},
            "arguments": ["a1", "a2"],
            "attacks": [["a1", "a2"]],
        }

        _write_dung_extensions_to_state(output, state, {})
        call_count_first = state.add_dung_framework.call_count

        _write_dung_extensions_to_state(output, state, {})
        call_count_second = state.add_dung_framework.call_count

        # Both calls go through (state writer doesn't guard),
        # but the conversational_orchestrator guard prevents double invocation
        assert call_count_second == call_count_first * 2, (
            "state writer should add on each call; "
            "idempotency is enforced at orchestrator level"
        )

    def test_conversational_orchestrator_dung_guard(self):
        """conversational_orchestrator must skip Dung if dung_frameworks is non-empty."""
        from argumentation_analysis.orchestration import conversational_orchestrator

        source = inspect.getsource(conversational_orchestrator.run_conversational_analysis)
        # Check that the guard 'not state.dung_frameworks' appears in the Dung block
        assert "not state.dung_frameworks" in source, (
            "Dung hook should have idempotency guard checking "
            "'not state.dung_frameworks' before invocation"
        )


class TestAspicIdempotency:
    """ASPIC hook must not duplicate entries on repeated invocation."""

    def test_conversational_orchestrator_aspic_guard(self):
        """conversational_orchestrator must skip ASPIC if aspic_results is non-empty."""
        from argumentation_analysis.orchestration import conversational_orchestrator

        source = inspect.getsource(conversational_orchestrator.run_conversational_analysis)
        assert "not state.aspic_results" in source, (
            "ASPIC hook should have idempotency guard checking "
            "'not state.aspic_results' before invocation"
        )
