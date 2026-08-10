"""Tests for the honest attack-retention accounting (#1698 item 3).

The Dung-family producers (``_invoke_dung_extensions`` / ``_invoke_setaf`` /
``_invoke_weighted`` / ``_invoke_social``) used to paste the INPUT attacks back
into their output as if they were the evaluated graph, while every handler
silently drops any edge with an endpoint outside the inventory
(``_generate_attacks_from_args`` mints synthetic sources ``fallacy_*`` / ``CA:*``
that are never members). On the real corpus this means 100% of edges are
dropped yet the artefact presents K attacks as a result.

``_annotate_attack_retention`` replaces the echo with the edges actually in the
frame plus a submitted/retained/dropped accounting, so a graph evaluated with
no edge declares itself. These tests exercise the real accounting functions
(not literal fixtures — anti-#1019), built around the two states the DoD names:
sources outside the inventory (⇒ 0 retained) vs sources that are members (⇒ N
retained). Two states that differ must produce two outputs that differ.
"""

from __future__ import annotations

from typing import Any, Dict, List

import pytest
from unittest.mock import AsyncMock, patch

from argumentation_analysis.orchestration.invoke_callables import (
    _annotate_attack_retention,
    _retained_attacks,
)

# ============================================================
# _retained_attacks — membership logic per handler shape
# ============================================================


class TestRetainedAttacksPairShape:
    """Dung/Social pair-list shape ``[source, target]``."""

    def test_synthetic_sources_dropped(self) -> None:
        # The exact shape _generate_attacks_from_args emits (invoke:3204/3221):
        # sources are synthetic fallacy / counter-arg labels, never members.
        arguments = ["claim_one", "claim_two"]
        submitted = [
            ["fallacy_0_ad_hominem", "claim_one"],
            ["CA: counter text snippet", "claim_two"],
        ]
        assert _retained_attacks(arguments, submitted) == []

    def test_member_sources_kept(self) -> None:
        arguments = ["a", "b", "c"]
        submitted = [["c", "a"], ["a", "b"]]
        assert _retained_attacks(arguments, submitted) == [["c", "a"], ["a", "b"]]

    def test_partial_membership_drops_the_edge(self) -> None:
        # An attack with one endpoint in, one out, is not in the frame.
        arguments = ["a", "b"]
        submitted = [["a", "x_not_in_inventory"]]
        assert _retained_attacks(arguments, submitted) == []


class TestRetainedAttacksWeightedShape:
    """Weighted triple shape ``(source, target, weight)``."""

    def test_synthetic_source_triple_dropped(self) -> None:
        arguments = ["arg_a", "arg_b"]
        submitted = [("fallacy_1_strawman", "arg_a", 0.7), ("CA: x", "arg_b", 0.3)]
        assert _retained_attacks(arguments, submitted) == []

    def test_member_source_triple_kept_with_weight(self) -> None:
        arguments = ["a", "b"]
        submitted = [("b", "a", 0.9)]
        assert _retained_attacks(arguments, submitted) == [("b", "a", 0.9)]


class TestRetainedAttacksSetafShape:
    """SetAF joint-attack spec ``{"attackers": [...], "target"}``.

    The handler keeps an attack whose target is a member AND at least one
    attacker is a member (it stores the partial attacker set). This is why
    SetAF discriminated once on the real corpus (7/8) when its translator
    path produced genuine member attacks — it must NOT be absorbed into a
    global "nothing is ever excluded" claim.
    """

    def test_target_member_one_attacker_member_kept(self) -> None:
        arguments = ["a", "b", "c"]
        submitted = [{"attackers": ["b", "fallacy_0_x"], "target": "a"}]
        # target "a" is a member, attacker "b" is a member (fallacy_0_x is not)
        assert _retained_attacks(arguments, submitted) == submitted

    def test_all_attackers_synthetic_dropped(self) -> None:
        arguments = ["a", "b"]
        submitted = [{"attackers": ["fallacy_0_x", "fallacy_1_y"], "target": "a"}]
        assert _retained_attacks(arguments, submitted) == []

    def test_target_not_member_dropped(self) -> None:
        arguments = ["a", "b"]
        submitted = [{"attackers": ["a"], "target": "x_not_in"}]
        assert _retained_attacks(arguments, submitted) == []

    def test_setaf_discriminates_when_member_attacker_present(self) -> None:
        # Reproduces the corpus_B 7/8 signature: a genuine member attacker
        # excludes the target. Retention is non-empty here.
        arguments = ["arg1", "arg2", "arg3"]
        submitted = [{"attackers": ["arg2"], "target": "arg1"}]
        assert len(_retained_attacks(arguments, submitted)) == 1


class TestRetainedAttacksMalformed:
    def test_unknown_shape_dropped(self) -> None:
        arguments = ["a"]
        assert (
            _retained_attacks(arguments, [{"weird": "shape"}, "bare_string", []]) == []
        )


# ============================================================
# _annotate_attack_retention — the honest report (DoD)
# ============================================================


class _FakeState:
    """Captures trace entries so we can assert the drop is declared."""

    def __init__(self) -> None:
        self.traces: List[Dict[str, Any]] = []

    def add_trace_entry(self, **kwargs: Any) -> None:
        self.traces.append(kwargs)


class TestAnnotateHonestReport:
    def _pair_output(self, attacks: List[Any]) -> Dict[str, Any]:
        # The shape a Dung/Social handler returns (echo of the input attacks).
        return {
            "semantics": "grounded",
            "arguments": ["a", "b"],
            "attacks": attacks,
            "extensions": [["a", "b"]],
            "statistics": {"arguments_count": 2, "attacks_count": len(attacks)},
        }

    def test_synthetic_sources_declare_zero_retained(self) -> None:
        """DoD: input with sources outside inventory ⇒ output declares 0 retained."""
        state = _FakeState()
        output = self._pair_output([["fallacy_0_x", "a"], ["CA: snippet", "b"]])
        result = _annotate_attack_retention(
            output,
            ["a", "b"],
            output["attacks"],
            framework_name="verification",
            state=state,
        )
        assert result["attacks"] == []
        assert result["attacks_submitted"] == 2
        assert result["attacks_retained"] == 0
        assert result["attacks_dropped"] == 2
        # statistics.attacks_count now counts what was EVALUATED (#1698).
        assert result["statistics"]["attacks_count"] == 0
        assert result["statistics"]["attacks_submitted"] == 2
        # The drop is declared in the trace (not silent).
        assert len(state.traces) == 1
        assert "2 retenue" not in state.traces[0]["summary"]
        assert "droppée" in state.traces[0]["summary"]

    def test_member_sources_declare_n_retained(self) -> None:
        """DoD: input with member sources ⇒ output declares N retained."""
        state = _FakeState()
        output = self._pair_output([["b", "a"], ["a", "b"]])
        result = _annotate_attack_retention(
            output,
            ["a", "b"],
            output["attacks"],
            framework_name="verification",
            state=state,
        )
        assert result["attacks"] == [["b", "a"], ["a", "b"]]
        assert result["attacks_retained"] == 2
        assert result["attacks_dropped"] == 0
        # No drop ⇒ no drop-declaration trace.
        assert state.traces == []

    def test_two_states_produce_two_outputs_that_differ(self) -> None:
        """DoD (anti-#1019): two inputs that differ ⇒ two outputs that differ.

        A "the output is non-empty" assertion would see nothing — both states
        carry attacks. The discriminating signal is the retained count and the
        retained edge list.
        """
        args_inventory = ["a", "b"]
        synthetic = _annotate_attack_retention(
            self._pair_output([["fallacy_0_x", "a"]]),
            args_inventory,
            [["fallacy_0_x", "a"]],
            framework_name="verification",
        )
        genuine = _annotate_attack_retention(
            self._pair_output([["b", "a"]]),
            args_inventory,
            [["b", "a"]],
            framework_name="verification",
        )
        assert synthetic["attacks_retained"] != genuine["attacks_retained"]
        assert synthetic["attacks"] != genuine["attacks"]
        assert synthetic["attacks_dropped"] == 1
        assert genuine["attacks_dropped"] == 0

    def test_setaf_partial_attacker_set_is_honest(self) -> None:
        """SetAF retains an attack with one member attacker even if others are
        synthetic — the report must preserve this discrimination."""
        output = {
            "semantics": "grounded",
            "arguments": ["a", "b"],
            "attacks": [{"attackers": ["b", "fallacy_x"], "target": "a"}],
            "extensions": [["a", "b"]],
            "statistics": {"arguments_count": 2, "attacks_count": 1},
        }
        result = _annotate_attack_retention(
            output,
            ["a", "b"],
            output["attacks"],
            framework_name="setaf_grounded",
        )
        assert result["attacks_retained"] == 1
        assert result["attacks_dropped"] == 0

    def test_no_state_no_trace_no_crash(self) -> None:
        output = self._pair_output([["fallacy_0_x", "a"]])
        # state=None must not crash even when edges are dropped.
        result = _annotate_attack_retention(
            output,
            ["a", "b"],
            [["fallacy_0_x", "a"]],
            framework_name="verification",
            state=None,
        )
        assert result["attacks_dropped"] == 1

    def test_empty_submitted_is_honest_zero(self) -> None:
        output = self._pair_output([])
        result = _annotate_attack_retention(
            output,
            ["a", "b"],
            [],
            framework_name="verification",
        )
        assert result["attacks"] == []
        assert result["attacks_submitted"] == 0
        assert result["attacks_retained"] == 0
        assert result["attacks_dropped"] == 0

    def test_existing_statistics_preserved_beyond_attacks_count(self) -> None:
        # annotate must align attacks_count but not clobber sibling stats.
        output = {
            "attacks": [["fallacy_0_x", "a"]],
            "statistics": {
                "arguments_count": 2,
                "attacks_count": 1,
                "semantics_computed": 4,
                "handler": "AFHandler",
            },
        }
        result = _annotate_attack_retention(
            output,
            ["a", "b"],
            [["fallacy_0_x", "a"]],
            framework_name="verification",
        )
        assert result["statistics"]["semantics_computed"] == 4
        assert result["statistics"]["handler"] == "AFHandler"
        assert result["statistics"]["attacks_count"] == 0  # aligned to retained


# ============================================================
# #1629 soustraction — translator answered "nothing" ⇒ no fabrication
# ============================================================
#
# Coord ruling (R786, posted on #1629): when a translator arbitrated and
# returned ``no_genuine_relations``, the synthetic ``_generate_attacks_from_args``
# fallback must NOT fire. Tested through the real ``_invoke_setaf`` /
# ``_invoke_weighted`` with the translator outcome + handler stubbed
# (anti-#1019: real producer path, not a literal). Dung/social have no
# translator covering naked attacks and stay out of this scope.


class TestSoustractionNoGenuineRelations1629:
    """#1629: ``no_genuine_relations`` (arbiter answered nothing) ⇒ fabricate
    nothing. ``evaluated`` ⇒ use the genuine relations. ``translator_failed`` /
    absent ⇒ arbiter did not answer ⇒ synthetic fallback stands (regression)."""

    @staticmethod
    def _stub_handler_module(attacks_sink: Dict[str, Any]) -> Any:
        """Build a stub SetAFHandler/WeightedHandler capturing the attacks it
        received, so we can assert what the invoke layer fed it."""

        class _Stub:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                pass

            def analyze_setaf(
                self, args: Any, attacks: Any, semantics: Any
            ) -> Dict[str, Any]:
                attacks_sink["setaf"] = attacks
                return {
                    "semantics": semantics,
                    "arguments": list(args),
                    "attacks": attacks,
                    "extensions": [],
                    "statistics": {
                        "arguments_count": len(args),
                        "attacks_count": len(attacks),
                    },
                }

            def analyze_weighted_framework(
                self, args: Any, attacks: Any, semantics: Any
            ) -> Dict[str, Any]:
                attacks_sink["weighted"] = attacks
                return {
                    "semantics": semantics,
                    "arguments": list(args),
                    "attacks": [
                        {"source": s, "target": t, "weight": w} for s, t, w in attacks
                    ],
                    "extensions": [],
                    "statistics": {
                        "arguments_count": len(args),
                        "attacks_count": len(attacks),
                    },
                }

        return _Stub

    async def test_setaf_subtracts_when_translator_found_nothing(self) -> None:
        from argumentation_analysis.orchestration.invoke_callables import _invoke_setaf
        from argumentation_analysis.orchestration.structured_arg_translator import (
            CAUSE_NO_GENUINE_RELATIONS,
            TranslationResult,
        )

        sink: Dict[str, Any] = {}
        outcome = TranslationResult(
            relations=[], cause=CAUSE_NO_GENUINE_RELATIONS, error=""
        )
        with patch(
            "argumentation_analysis.orchestration.structured_arg_translator."
            "translate_to_setaf_attacks",
            new=AsyncMock(return_value=outcome),
        ), patch(
            "argumentation_analysis.agents.core.logic.setaf_handler.SetAFHandler",
            self._stub_handler_module(sink),
        ), patch(
            "argumentation_analysis.agents.core.logic.tweety_initializer."
            "TweetyInitializer",
            return_value=None,
        ):
            output = await _invoke_setaf("text", {"arguments": ["a", "b"]})

        # Soustraction: the handler received NO fabricated attacks.
        assert sink["setaf"] == []
        assert output["attacks"] == []
        assert output["attacks_submitted"] == 0
        assert output["attacks_dropped"] == 0  # nothing dropped: nothing fabricated

    async def test_setaf_uses_genuine_when_translator_evaluated(self) -> None:
        from argumentation_analysis.orchestration.invoke_callables import _invoke_setaf
        from argumentation_analysis.orchestration.structured_arg_translator import (
            CAUSE_EVALUATED,
            TranslationResult,
        )

        sink: Dict[str, Any] = {}
        # corpus_B signature: 3 genuine member joint-attacks.
        genuine = [
            {"attackers": ["b"], "target": "a"},
            {"attackers": ["c"], "target": "a"},
            {"attackers": ["c"], "target": "b"},
        ]
        outcome = TranslationResult(relations=genuine, cause=CAUSE_EVALUATED)
        with patch(
            "argumentation_analysis.orchestration.structured_arg_translator."
            "translate_to_setaf_attacks",
            new=AsyncMock(return_value=outcome),
        ), patch(
            "argumentation_analysis.agents.core.logic.setaf_handler.SetAFHandler",
            self._stub_handler_module(sink),
        ), patch(
            "argumentation_analysis.agents.core.logic.tweety_initializer."
            "TweetyInitializer",
            return_value=None,
        ):
            output = await _invoke_setaf("text", {"arguments": ["a", "b", "c"]})

        assert sink["setaf"] == genuine  # genuine relations used as-is
        assert output["attacks_retained"] == 3  # all members ⇒ all retained

    async def test_setaf_falls_back_when_translator_failed(self) -> None:
        """Regression: translator_failed = arbiter did NOT answer ⇒ synthetic
        fallback stands (soustraction does NOT fire on failure)."""
        from argumentation_analysis.orchestration.invoke_callables import _invoke_setaf
        from argumentation_analysis.orchestration.structured_arg_translator import (
            CAUSE_TRANSLATOR_FAILED,
            TranslationResult,
        )

        sink: Dict[str, Any] = {}
        outcome = TranslationResult(
            relations=[], cause=CAUSE_TRANSLATOR_FAILED, error="RuntimeError"
        )
        with patch(
            "argumentation_analysis.orchestration.structured_arg_translator."
            "translate_to_setaf_attacks",
            new=AsyncMock(return_value=outcome),
        ), patch(
            "argumentation_analysis.orchestration.invoke_callables."
            "_generate_attacks_from_args",
            return_value=[["arg1", "arg2"]],  # synthetic, member sources
        ), patch(
            "argumentation_analysis.agents.core.logic.setaf_handler.SetAFHandler",
            self._stub_handler_module(sink),
        ), patch(
            "argumentation_analysis.agents.core.logic.tweety_initializer."
            "TweetyInitializer",
            return_value=None,
        ):
            output = await _invoke_setaf("text", {"arguments": ["arg1", "arg2"]})

        # Fallback fired (NOT subtracted): handler received the synthetic pair.
        assert len(sink["setaf"]) == 1
        assert output["attacks_submitted"] == 1

    async def test_weighted_subtracts_when_translator_found_nothing(self) -> None:
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_weighted,
        )
        from argumentation_analysis.orchestration.structured_arg_translator import (
            CAUSE_NO_GENUINE_RELATIONS,
            TranslationResult,
        )

        sink: Dict[str, Any] = {}
        outcome = TranslationResult(
            relations=[], cause=CAUSE_NO_GENUINE_RELATIONS, error=""
        )
        with patch(
            "argumentation_analysis.orchestration.structured_arg_translator."
            "translate_to_weighted_attacks",
            new=AsyncMock(return_value=outcome),
        ), patch(
            "argumentation_analysis.agents.core.logic.weighted_handler."
            "WeightedHandler",
            self._stub_handler_module(sink),
        ), patch(
            "argumentation_analysis.agents.core.logic.tweety_initializer."
            "TweetyInitializer",
            return_value=None,
        ):
            output = await _invoke_weighted("text", {"arguments": ["a", "b"]})

        assert sink["weighted"] == []
        assert output["attacks_submitted"] == 0
