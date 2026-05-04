"""Tests for Dung/ASPIC framework wiring into pipeline and conversational modes (#286).

Validates:
- _invoke_dung_extensions uses extract_arguments and generate_attacks helpers
- _python_dung_fallback computes grounded extension correctly
- _write_dung_extensions_to_state stores actual attacks and arguments
- _generate_attacks_from_args matches fallacies to arguments by text content
- Standard and full workflows include dung_extensions and aspic_analysis phases
- jtms_dung_loop workflow uses correct dung_extensions capability
- FormalAgent instructions include Dung analysis step
- AGENT_SPECIALITY_MAP includes tweety_logic for formal_logic agents
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# ============================================================
# Test: _invoke_dung_extensions uses helper functions
# ============================================================


class TestInvokeDungExtensions:
    """Test that _invoke_dung_extensions properly wires helpers."""

    @pytest.mark.asyncio
    async def test_extracts_arguments_from_context(self):
        """Dung function uses _extract_arguments_from_context."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_dung_extensions,
        )

        context = {
            "phase_extract_output": {
                "arguments": [
                    {"text": "Les impots doivent augmenter"},
                    {"text": "L'etat est endette"},
                ]
            },
        }

        with patch(
            "argumentation_analysis.agents.core.logic.af_handler.AFHandler"
        ) as mock_af:
            mock_handler = MagicMock()
            mock_handler.analyze_dung_framework.return_value = {
                "extensions": {"grounded": ["arg_0"]},
            }
            mock_af.return_value = mock_handler

            with patch(
                "argumentation_analysis.agents.core.logic.tweety_initializer.TweetyInitializer"
            ) as mock_init:
                mock_init.return_value = MagicMock()
                result = await _invoke_dung_extensions("test text", context)

        # Should have called AFHandler with extracted arguments
        call_args = mock_handler.analyze_dung_framework.call_args
        args_passed = call_args[0][0]  # First positional arg = arguments
        assert len(args_passed) == 2
        assert "impots" in args_passed[0].lower() or "impots" in args_passed[0]

    @pytest.mark.asyncio
    async def test_generates_attacks_from_fallacies(self):
        """Dung function uses _generate_attacks_from_args for cross-KB."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_dung_extensions,
        )

        context = {
            "phase_extract_output": {
                "arguments": [
                    {"text": "Ce regime est le meilleur car le professeur le dit"},
                    {"text": "Les etudes montrent le contraire"},
                ]
            },
            "phase_hierarchical_fallacy_output": {
                "fallacies": [
                    {
                        "type": "Appel a l'autorite",
                        "target_text": "Ce regime est le meilleur car le professeur le dit",
                    }
                ]
            },
        }

        with patch(
            "argumentation_analysis.agents.core.logic.af_handler.AFHandler"
        ) as mock_af:
            mock_handler = MagicMock()
            mock_handler.analyze_dung_framework.return_value = {
                "extensions": {},
            }
            mock_af.return_value = mock_handler

            with patch(
                "argumentation_analysis.agents.core.logic.tweety_initializer.TweetyInitializer"
            ) as mock_init:
                mock_init.return_value = MagicMock()
                result = await _invoke_dung_extensions("test text", context)

        # Attacks should have been generated from the fallacy
        call_args = mock_handler.analyze_dung_framework.call_args
        attacks_passed = call_args[0][1]  # Second positional arg = attacks
        assert len(attacks_passed) > 0
        # The fallacy should attack the targeted argument
        assert any("fallacy" in str(a).lower() for a in attacks_passed)

    @pytest.mark.asyncio
    async def test_returns_multi_semantics(self):
        """Dung function computes multiple semantics (grounded, preferred, stable)."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_dung_extensions,
        )

        context = {
            "phase_extract_output": {"arguments": [{"text": "arg1"}, {"text": "arg2"}]}
        }

        with patch(
            "argumentation_analysis.agents.core.logic.af_handler.AFHandler"
        ) as mock_af:
            mock_handler = MagicMock()
            mock_handler.analyze_dung_framework.return_value = {
                "extensions": {"set": ["arg1"]},
            }
            mock_af.return_value = mock_handler

            with patch(
                "argumentation_analysis.agents.core.logic.tweety_initializer.TweetyInitializer"
            ) as mock_init:
                mock_init.return_value = MagicMock()
                result = await _invoke_dung_extensions("test text", context)

        assert result["semantics"] == "multi"
        assert "all_extensions" in result
        assert "grounded" in result["all_extensions"]
        assert "preferred" in result["all_extensions"]
        assert "stable" in result["all_extensions"]
        assert "arguments" in result
        assert "attacks" in result

    @pytest.mark.asyncio
    async def test_fallback_to_python(self):
        """Dung function falls back to Python when JVM unavailable."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_dung_extensions,
        )

        context = {
            "phase_extract_output": {"arguments": [{"text": "arg1"}, {"text": "arg2"}]}
        }

        with patch(
            "argumentation_analysis.agents.core.logic.af_handler.AFHandler",
            side_effect=ImportError("No JVM"),
        ):
            with patch(
                "argumentation_analysis.agents.core.logic.tweety_initializer.TweetyInitializer",
                side_effect=ImportError("No JVM"),
            ):
                result = await _invoke_dung_extensions("test text", context)

        assert result["semantics"] == "python_fallback"
        assert len(result["arguments"]) == 2


# ============================================================
# Test: Python Dung fallback
# ============================================================


class TestPythonDungFallback:
    """Test pure-Python Dung extension computation."""

    def test_empty_arguments(self):
        """Fallback returns empty result for no arguments."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _python_dung_fallback,
        )

        result = _python_dung_fallback([], [])
        assert result["statistics"]["arguments_count"] == 0

    def test_simple_framework(self):
        """Fallback computes grounded extension for simple AF."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _python_dung_fallback,
        )

        args = ["a", "b", "c"]
        attacks = [["a", "b"]]  # a attacks b
        result = _python_dung_fallback(args, attacks)

        assert result["semantics"] == "python_fallback"
        assert len(result["arguments"]) == 3
        assert len(result["attacks"]) == 1
        # 'a' has no attacker, so it should be in grounded
        # 'b' is attacked by 'a' (which is defended), so b not in grounded
        # 'c' has no attacker, so it should be in grounded
        grounded = result.get("extensions", {}).get("grounded", [])
        assert "a" in grounded
        assert "c" in grounded
        assert "b" not in grounded

    def test_self_attack(self):
        """Fallback handles self-attacking arguments."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _python_dung_fallback,
        )

        args = ["a", "b"]
        attacks = [["a", "a"]]  # a attacks itself
        result = _python_dung_fallback(args, attacks)

        # a is self-attacking, should not be in grounded
        grounded = result.get("extensions", {}).get("grounded", [])
        assert "a" not in grounded

    def test_no_attacks(self):
        """All arguments in grounded when no attacks."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _python_dung_fallback,
        )

        args = ["a", "b", "c"]
        result = _python_dung_fallback(args, [])

        grounded = result.get("extensions", {}).get("grounded", [])
        assert set(grounded) == {"a", "b", "c"}


# ============================================================
# Test: State writer
# ============================================================


class TestDungStateWriter:
    """Test _write_dung_extensions_to_state."""

    def test_writes_actual_attacks(self):
        """State writer stores actual attacks, not empty list."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_dung_extensions_to_state,
        )

        state = MagicMock()
        output = {
            "semantics": "multi",
            "extensions": {"grounded": ["arg1"]},
            "arguments": ["arg1", "arg2"],
            "attacks": [["arg1", "arg2"]],
        }

        _write_dung_extensions_to_state(output, state, {})

        # Should have called add_dung_framework with actual attacks
        state.add_dung_framework.assert_called()
        call_kwargs = state.add_dung_framework.call_args[1]
        assert call_kwargs["attacks"] == [["arg1", "arg2"]]
        assert call_kwargs["arguments"] == ["arg1", "arg2"]

    def test_writes_multi_semantics(self):
        """State writer stores additional semantics when computed."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_dung_extensions_to_state,
        )

        state = MagicMock()
        output = {
            "semantics": "multi",
            "extensions": {"preferred": ["arg1"]},
            "all_extensions": {
                "grounded": {"set": ["arg1"]},
                "preferred": {"set": ["arg1"]},
                "stable": {"set": ["arg1", "arg2"]},
            },
            "arguments": ["arg1", "arg2"],
            "attacks": [["arg1", "arg2"]],
        }

        _write_dung_extensions_to_state(output, state, {})

        # Should have called add_dung_framework for each semantics
        assert state.add_dung_framework.call_count >= 2

    def test_handles_empty_output(self):
        """State writer handles None/empty output gracefully."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_dung_extensions_to_state,
        )

        state = MagicMock()
        _write_dung_extensions_to_state(None, state, {})
        _write_dung_extensions_to_state({}, state, {})
        state.add_dung_framework.assert_not_called()


# ============================================================
# Test: Cross-KB fallacy → attack generation
# ============================================================


class TestCrossKBFallacyAttacks:
    """Test _generate_attacks_from_args with text-based fallacy matching."""

    def test_matches_by_text_overlap(self):
        """Fallacies matched to arguments by text content, not just index."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _generate_attacks_from_args,
        )

        arguments = [
            "Le professeur Dupont affirme que ce regime est le meilleur",
            "Les etudes scientifiques montrent le contraire",
        ]
        context = {
            "phase_hierarchical_fallacy_output": {
                "fallacies": [
                    {
                        "type": "Appel a l'autorite",
                        "target_text": "Le professeur Dupont affirme que ce regime",
                    }
                ]
            }
        }

        attacks = _generate_attacks_from_args(arguments, context)

        assert len(attacks) > 0
        # The fallacy should target the first argument (text overlap)
        assert any(
            "professeur" in a[1].lower() or "dupont" in a[1].lower() for a in attacks
        )

    def test_fallacy_label_in_attack(self):
        """Attack labels include fallacy type."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _generate_attacks_from_args,
        )

        arguments = ["Argument avec appel a l'autorite", "Argument valide"]
        context = {
            "phase_hierarchical_fallacy_output": {
                "fallacies": [
                    {"type": "Appel a l'autorite", "target_text": "appel a l'autorite"}
                ]
            }
        }

        attacks = _generate_attacks_from_args(arguments, context)
        assert len(attacks) > 0
        assert any(
            "appel" in str(a[0]).lower() or "autorite" in str(a[0]).lower()
            for a in attacks
        )

    def test_counter_argument_attacks(self):
        """Counter-arguments generate attack relations."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _generate_attacks_from_args,
        )

        arguments = ["Les impots doivent augmenter", "L'economie va bien"]
        context = {
            "phase_counter_output": {
                "llm_counter_arguments": [
                    {
                        "target_argument": "Les impots doivent augmenter",
                        "counter_argument": "Les impots sont deja trop eleves",
                    }
                ]
            }
        }

        attacks = _generate_attacks_from_args(arguments, context)
        assert len(attacks) > 0
        assert any("CA" in a[0] for a in attacks)

    def test_fallback_heuristic(self):
        """Sparse heuristic used when no upstream data."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _generate_attacks_from_args,
        )

        arguments = ["arg1", "arg2", "arg3"]
        attacks = _generate_attacks_from_args(arguments, None)
        assert len(attacks) > 0  # Should generate some attacks


# ============================================================
# Test: Workflow definitions
# ============================================================


class TestWorkflowDungPhases:
    """Validate workflows include Dung/ASPIC phases."""

    def test_standard_workflow_has_dung(self):
        """Standard workflow includes dung_extensions phase."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_standard_workflow,
        )

        wf = build_standard_workflow()
        phase_names = [p.name for p in wf.phases]
        assert "dung_extensions" in phase_names

    def test_standard_workflow_has_aspic(self):
        """Standard workflow includes aspic_analysis phase."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_standard_workflow,
        )

        wf = build_standard_workflow()
        phase_names = [p.name for p in wf.phases]
        assert "aspic_analysis" in phase_names

    def test_full_workflow_has_dung(self):
        """Full workflow includes dung_extensions phase."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_full_workflow,
        )

        wf = build_full_workflow()
        phase_names = [p.name for p in wf.phases]
        assert "dung_extensions" in phase_names

    def test_full_workflow_has_aspic(self):
        """Full workflow includes aspic_analysis phase."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_full_workflow,
        )

        wf = build_full_workflow()
        phase_names = [p.name for p in wf.phases]
        assert "aspic_analysis" in phase_names

    def test_dung_depends_on_fallacy_and_pl(self):
        """Dung phase depends on both fallacy detection and PL."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_standard_workflow,
        )

        wf = build_standard_workflow()
        dung_phase = next(p for p in wf.phases if p.name == "dung_extensions")
        assert "hierarchical_fallacy" in dung_phase.depends_on
        assert "pl" in dung_phase.depends_on

    def test_aspic_depends_on_dung(self):
        """ASPIC phase depends on Dung phase."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_standard_workflow,
        )

        wf = build_standard_workflow()
        aspic_phase = next(p for p in wf.phases if p.name == "aspic_analysis")
        assert "dung_extensions" in aspic_phase.depends_on

    def test_jtms_dung_loop_uses_correct_capability(self):
        """jtms_dung_loop workflow uses dung_extensions capability (not ranking)."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_jtms_dung_loop_workflow,
        )

        wf = build_jtms_dung_loop_workflow()
        dung_phase = next((p for p in wf.phases if p.name == "dung_extensions"), None)
        assert dung_phase is not None
        assert dung_phase.capability == "dung_extensions"

    def test_jtms_dung_loop_has_aspic(self):
        """jtms_dung_loop workflow includes ASPIC phase."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_jtms_dung_loop_workflow,
        )

        wf = build_jtms_dung_loop_workflow()
        phase_names = [p.name for p in wf.phases]
        assert "aspic_analysis" in phase_names


# ============================================================
# Test: FormalAgent instructions
# ============================================================


class TestFormalAgentInstructions:
    """Test FormalAgent instructions include Dung analysis."""

    def test_formal_agent_mentions_dung(self):
        """FormalAgent instructions mention Dung analysis."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            AGENT_CONFIG,
        )

        instructions = AGENT_CONFIG["FormalAgent"]["instructions"]
        assert "Dung" in instructions or "dung" in instructions.lower()

    def test_formal_agent_has_analyze_dung_workflow(self):
        """FormalAgent instructions include analyze_dung_framework call."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            AGENT_CONFIG,
        )

        instructions = AGENT_CONFIG["FormalAgent"]["instructions"]
        assert "analyze_dung_framework" in instructions

    def test_formal_agent_has_4_steps(self):
        """FormalAgent workflow now has 4 steps (was 3)."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            AGENT_CONFIG,
        )

        instructions = AGENT_CONFIG["FormalAgent"]["instructions"]
        assert "ETAPE 4" in instructions

    def test_formal_agent_speciality_has_tweety(self):
        """FormalAgent's speciality includes tweety_logic plugin."""
        from argumentation_analysis.agents.factory import AGENT_SPECIALITY_MAP

        plugins = AGENT_SPECIALITY_MAP.get("formal_logic", [])
        assert "tweety_logic" in plugins


# ============================================================
# Test: Formal verification workflow integration
# ============================================================


class TestFormalVerificationWorkflow:
    """Test formal_verification workflow includes Dung/ASPIC."""

    def test_formal_verification_has_dung(self):
        """Formal verification workflow includes dung_analysis phase."""
        from argumentation_analysis.workflows.formal_verification import (
            build_formal_verification_workflow,
        )

        wf = build_formal_verification_workflow()
        phase_names = [p.name for p in wf.phases]
        assert "dung_analysis" in phase_names

    def test_formal_verification_has_aspic(self):
        """Formal verification workflow includes aspic_analysis phase."""
        from argumentation_analysis.workflows.formal_verification import (
            build_formal_verification_workflow,
        )

        wf = build_formal_verification_workflow()
        phase_names = [p.name for p in wf.phases]
        assert "aspic_analysis" in phase_names

    def test_aspic_depends_on_dung_in_formal(self):
        """In formal verification, ASPIC depends on Dung."""
        from argumentation_analysis.workflows.formal_verification import (
            build_formal_verification_workflow,
        )

        wf = build_formal_verification_workflow()
        aspic = next(p for p in wf.phases if p.name == "aspic_analysis")
        assert "dung_analysis" in aspic.depends_on
