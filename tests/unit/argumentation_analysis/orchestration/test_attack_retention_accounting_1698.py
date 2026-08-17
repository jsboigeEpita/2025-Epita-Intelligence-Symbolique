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
            "ready_initializer",
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
            "ready_initializer",
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
            "ready_initializer",
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
            "ready_initializer",
            return_value=None,
        ):
            output = await _invoke_weighted("text", {"arguments": ["a", "b"]})

        assert sink["weighted"] == []
        assert output["attacks_submitted"] == 0


# ============================================================
# R791 item 1 — the honest report reaches the CURATED surface
# (dung_frameworks[*], the one the conclusion reads)
# ============================================================


class TestCarryAttackRetentionWriters:
    """#1698 (R791 item 1): the #1704 submitted/retained/dropped accounting
    must reach ``dung_frameworks[*]`` — the surface the conclusion reads —
    not only the invoke output persisted under ``formal_synthesis_reports``.
    Built through the real ``UnifiedAnalysisState.add_dung_framework`` entry
    point (anti-#1019: no dict-literal state)."""

    def test_dung_writer_carries_accounting_onto_curated_entry(self) -> None:
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState
        from argumentation_analysis.orchestration.state_writers import (
            _write_dung_extensions_to_state,
        )

        state = UnifiedAnalysisState(initial_text="x")
        output = {
            "semantics": "grounded",
            "arguments": ["a", "b"],
            "attacks": [],
            "extensions": {"grounded": ["a", "b"]},
            # The #1704 accounting, as the producer now declares it.
            "attacks_submitted": 2,
            "attacks_retained": 0,
            "attacks_dropped": 2,
        }
        _write_dung_extensions_to_state(output, state, {})
        entry = next(iter(state.dung_frameworks.values()))
        assert entry["attacks_submitted"] == 2
        assert entry["attacks_retained"] == 0
        assert entry["attacks_dropped"] == 2

    def test_all_four_annotated_writers_carry_the_accounting(self) -> None:
        """Dung, social, setaf, weighted all project the frozen subset — the
        accounting must ride on each curated entry, not be writer-specific."""
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState
        from argumentation_analysis.orchestration.state_writers import (
            _write_dung_extensions_to_state,
            _write_setaf_to_state,
            _write_social_to_state,
            _write_weighted_to_state,
        )

        cases = [
            (
                _write_dung_extensions_to_state,
                {
                    "semantics": "grounded",
                    "arguments": ["a", "b"],
                    "attacks": [],
                    "extensions": {"grounded": ["a", "b"]},
                },
            ),
            (
                _write_social_to_state,
                {"arguments": ["a", "b"], "attacks": [], "ranking": [], "scores": {}},
            ),
            (
                _write_setaf_to_state,
                {"semantics": "grounded", "arguments": ["a", "b"], "attacks": []},
            ),
            (
                _write_weighted_to_state,
                {"semantics": "grounded", "arguments": ["a", "b"], "attacks": []},
            ),
        ]
        for writer, base in cases:
            state = UnifiedAnalysisState(initial_text="x")
            output = dict(base)
            output.update(
                {
                    "attacks_submitted": 3,
                    "attacks_retained": 1,
                    "attacks_dropped": 2,
                }
            )
            writer(output, state, {})
            assert state.dung_frameworks, f"{writer.__name__} wrote nothing"
            for entry in state.dung_frameworks.values():
                assert entry["attacks_submitted"] == 3, writer.__name__
                assert entry["attacks_retained"] == 1, writer.__name__
                assert entry["attacks_dropped"] == 2, writer.__name__

    def test_writer_does_not_synthesise_accounting_when_keys_absent(self) -> None:
        """Absent keys ⇒ nothing carried: a legacy producer (or a writer path
        without annotation) must not gain a fabricated accounting (#1019)."""
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState
        from argumentation_analysis.orchestration.state_writers import (
            _write_dung_extensions_to_state,
        )

        state = UnifiedAnalysisState(initial_text="x")
        _write_dung_extensions_to_state(
            {"semantics": "grounded", "arguments": ["a"], "attacks": []}, state, {}
        )
        entry = next(iter(state.dung_frameworks.values()))
        assert "attacks_submitted" not in entry
        assert "attacks_retained" not in entry
        assert "attacks_dropped" not in entry


# ============================================================
# R791 item 3 — internal-contradiction guard (DoD item 4)
# ============================================================


class TestInternalContradictionGuard:
    """#1698 DoD item 4: a framework that RETAINED edges yet whose acceptance
    semantics all return the full inventory is internally contradictory — it
    must be detected, not published as a normal verdict.

    Armed by a framework that declares edges and accepts everything.
    Substitution control: reverting the guard condition (e.g. dropping the
    ``attacks_retained > 0`` gate or the ``all(members == inventory)`` check)
    makes ``test_guard_detects_retained_edges_with_full_acceptance`` red.
    """

    def test_guard_detects_retained_edges_with_full_acceptance(self) -> None:
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState
        from argumentation_analysis.orchestration.state_writers import (
            _write_dung_extensions_to_state,
        )

        state = UnifiedAnalysisState(initial_text="x")
        output = {
            "semantics": "grounded",
            "arguments": ["a", "b"],
            "attacks": [["a", "b"]],  # a live edge IS in the frame
            "extensions": {"grounded": ["a", "b"], "preferred": ["a", "b"]},
            "attacks_submitted": 1,
            "attacks_retained": 1,
            "attacks_dropped": 0,
        }
        _write_dung_extensions_to_state(output, state, {})
        entry = next(iter(state.dung_frameworks.values()))
        assert entry["internal_contradiction"] is True
        # The contradiction is declared in the trace, not silent (#1019).
        assert any(
            "contradiction interne" in str(t.get("summary", ""))
            for t in state.analysis_trace
        )

    def test_guard_silent_when_zero_retained(self) -> None:
        """submitted > 0 with retained == 0 is NOT a contradiction — it is the
        honest empty report of #1704 doing its job (the edges never reached
        the evaluated graph). This is the exact 3-corpus real shape."""
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState
        from argumentation_analysis.orchestration.state_writers import (
            _write_dung_extensions_to_state,
        )

        state = UnifiedAnalysisState(initial_text="x")
        output = {
            "semantics": "grounded",
            "arguments": ["a", "b"],
            "attacks": [],
            "extensions": {"grounded": ["a", "b"]},
            "attacks_submitted": 15,
            "attacks_retained": 0,
            "attacks_dropped": 15,
        }
        _write_dung_extensions_to_state(output, state, {})
        entry = next(iter(state.dung_frameworks.values()))
        assert "internal_contradiction" not in entry

    def test_guard_silent_when_some_semantics_exclude(self) -> None:
        """A framework whose semantics discriminate (at least one excludes
        something) is healthy — no contradiction."""
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState
        from argumentation_analysis.orchestration.state_writers import (
            _write_dung_extensions_to_state,
        )

        state = UnifiedAnalysisState(initial_text="x")
        output = {
            "semantics": "grounded",
            "arguments": ["a", "b"],
            "attacks": [["a", "b"]],
            "extensions": {"grounded": ["a"], "preferred": ["a"]},
            "attacks_submitted": 1,
            "attacks_retained": 1,
            "attacks_dropped": 0,
        }
        _write_dung_extensions_to_state(output, state, {})
        entry = next(iter(state.dung_frameworks.values()))
        assert "internal_contradiction" not in entry

    def test_guard_silent_without_accounting_keys(self) -> None:
        """No accounting keys ⇒ guard has nothing to judge (never flags on a
        producer that did not run the annotation)."""
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState
        from argumentation_analysis.orchestration.state_writers import (
            _write_dung_extensions_to_state,
        )

        state = UnifiedAnalysisState(initial_text="x")
        _write_dung_extensions_to_state(
            {
                "semantics": "grounded",
                "arguments": ["a", "b"],
                "attacks": [["a", "b"]],
                "extensions": {"grounded": ["a", "b"]},
            },
            state,
            {},
        )
        entry = next(iter(state.dung_frameworks.values()))
        assert "internal_contradiction" not in entry


# ============================================================
# R791 item 2 — dropped-edge split by source nature
# (fallacy_* vs CA: vs other) — producer side + probe side
# ============================================================


class TestAttackSourceNatureSplit:
    """#1698 (R791 item 2): the accounting is split by the NATURE of the
    synthetic source the producer minted (``fallacy_*`` / ``CA: ...`` /
    ``other``). The split is declared at the annotation point where the
    candidates are in hand — reproducible by construction, never
    reconstructed post-hoc. Keys are counts only: the ``CA:`` sources embed
    counter-argument text (= corpus) and must never be printed."""

    def test_source_nature_classification(self) -> None:
        from argumentation_analysis.orchestration.invoke_callables import (
            _attack_source_nature,
        )

        assert _attack_source_nature("fallacy_0_ad_hominem") == "fallacy"
        assert _attack_source_nature("CA: contredit cette affirmation") == "ca"
        # A real inventory member (upstream-provided context["attacks"]) or a
        # malformed source lands in the defensive ``other`` bucket.
        assert _attack_source_nature("arg_1") == "other"
        assert _attack_source_nature(None) == "other"
        assert _attack_source_nature("") == "other"

    def test_annotation_splits_by_nature_all_dropped(self) -> None:
        """Mixed candidates with synthetic sources: every edge is dropped (the
        sources are never inventory members) — the split reflects each
        family's submitted count."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _annotate_attack_retention,
        )

        candidates = [
            ["fallacy_0_ad_hominem", "a"],
            ["fallacy_1_faux_dilemme", "b"],
            ["CA: contredit cette affirmation", "a"],
            ["c", "a"],  # real member source → other, retained
        ]
        output = _annotate_attack_retention(
            {}, ["a", "b", "c"], candidates, framework_name="test"
        )
        assert output["attacks_submitted"] == 4
        assert output["attacks_retained"] == 1
        assert output["attacks_dropped"] == 3
        assert output["attacks_submitted_fallacy"] == 2
        assert output["attacks_dropped_fallacy"] == 2
        assert output["attacks_submitted_ca"] == 1
        assert output["attacks_dropped_ca"] == 1
        assert output["attacks_submitted_other"] == 1
        assert output["attacks_dropped_other"] == 0
        # Invariant: the split recomposes the totals (verifiable honesty).
        assert (
            output["attacks_submitted_fallacy"]
            + output["attacks_submitted_ca"]
            + output["attacks_submitted_other"]
            == output["attacks_submitted"]
        )
        assert (
            output["attacks_dropped_fallacy"]
            + output["attacks_dropped_ca"]
            + output["attacks_dropped_other"]
            == output["attacks_dropped"]
        )

    def test_annotation_splits_setaf_shapes(self) -> None:
        """SetAF specs carry the source under ``attackers`` — the split must
        classify the same way as pairs."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _annotate_attack_retention,
        )

        candidates = [
            {"attackers": ["CA: contredit ce point"], "target": "a"},
            {"attackers": ["fallacy_0_generalisation"], "target": "b"},
        ]
        output = _annotate_attack_retention(
            {}, ["a", "b"], candidates, framework_name="test"
        )
        assert output["attacks_submitted_fallacy"] == 1
        assert output["attacks_dropped_fallacy"] == 1
        assert output["attacks_submitted_ca"] == 1
        assert output["attacks_dropped_ca"] == 1


class TestAttackSourceNatureProbe:
    """The probe is a READ-ONLY reader of the numeric accounting keys — it
    aggregates counts by surface (curated vs bulk) and never touches source
    strings (#1698 privacy HARD: ``CA:`` embeds corpus text)."""

    def _probe(self) -> Any:
        from scripts.probe_attack_source_nature_split import (
            _aggregate,
            _collect_accounting,
        )

        return _collect_accounting, _aggregate

    def test_probe_reads_split_off_a_real_state(self) -> None:
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState
        from argumentation_analysis.orchestration.state_writers import (
            _write_dung_extensions_to_state,
        )

        collect, aggregate = self._probe()
        state = UnifiedAnalysisState(initial_text="x")
        output = {
            "semantics": "grounded",
            "arguments": ["a", "b"],
            "attacks": [],
            "extensions": {"grounded": ["a", "b"]},
            "attacks_submitted": 3,
            "attacks_retained": 0,
            "attacks_dropped": 3,
            "attacks_submitted_fallacy": 2,
            "attacks_dropped_fallacy": 2,
            "attacks_submitted_ca": 1,
            "attacks_dropped_ca": 1,
            "attacks_submitted_other": 0,
            "attacks_dropped_other": 0,
        }
        _write_dung_extensions_to_state(output, state, {})
        # Same declaration also lands in the bulk phase_results — the probe
        # reports each surface separately, never double-counting.
        state.add_formal_synthesis_report("synthesis", {"dung_grounded": output}, 0.0)

        blocks = collect(state.get_state_snapshot())
        agg = aggregate(blocks)
        curated = agg["surfaces"]["curated"]
        bulk = agg["surfaces"]["bulk"]
        assert curated["attacks_submitted"] == 3
        assert curated["by_nature"]["fallacy"] == {"submitted": 2, "dropped": 2}
        assert curated["by_nature"]["ca"] == {"submitted": 1, "dropped": 1}
        assert bulk["attacks_submitted"] == 3
        assert bulk["by_nature"]["fallacy"] == {"submitted": 2, "dropped": 2}
        assert agg["nature_keys_present"] is True

    def test_probe_honest_when_split_absent(self) -> None:
        """Pre-instrumentation snapshots carry totals only — the probe says so
        instead of fabricating a split (#1019)."""
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState
        from argumentation_analysis.orchestration.state_writers import (
            _write_dung_extensions_to_state,
        )
        from scripts.probe_attack_source_nature_split import _render

        collect, aggregate = self._probe()
        state = UnifiedAnalysisState(initial_text="x")
        _write_dung_extensions_to_state(
            {
                "semantics": "grounded",
                "arguments": ["a", "b"],
                "attacks": [],
                "extensions": {"grounded": ["a", "b"]},
                "attacks_submitted": 15,
                "attacks_retained": 0,
                "attacks_dropped": 15,
            },
            state,
            {},
        )
        blocks = collect(state.get_state_snapshot())
        agg = aggregate(blocks)
        assert agg["nature_keys_present"] is False
        rendered = _render({"document": "doc", **agg}, as_json=False)
        assert "UNAVAILABLE" in rendered
        # R794 follow-up: on a pre-instrumentation surface the per-nature
        # values are absent, so the invariant must NOT print a spurious
        # MISMATCH (a verdict on a magnitude the surface never declared —
        # #1019 one level up). It prints N/A instead. Substitution control:
        # reverting _render_surface to an unconditional invariant makes the
        # MISMATCH assertion red.
        assert "MISMATCH" not in rendered
        assert "N/A (split unavailable)" in rendered
        # The per-surface flag is set, not only the document-global one.
        assert agg["surfaces"]["curated"]["nature_keys_present"] is False

    def test_probe_never_leaks_ca_source_text(self) -> None:
        """The probe output must never contain the ``CA:`` source string —
        it embeds counter-argument text (= corpus)."""
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState
        from argumentation_analysis.orchestration.state_writers import (
            _write_dung_extensions_to_state,
        )
        from scripts.probe_attack_source_nature_split import _render

        collect, aggregate = self._probe()
        state = UnifiedAnalysisState(initial_text="x")
        secret = "CA: contenu contre-argumentaire sensible non publiable"
        _write_dung_extensions_to_state(
            {
                "semantics": "grounded",
                "arguments": ["a", "b"],
                "attacks": [[secret, "a"]],  # the CA source IS in the state
                "extensions": {"grounded": ["a", "b"]},
                "attacks_submitted": 1,
                "attacks_retained": 0,
                "attacks_dropped": 1,
                "attacks_submitted_ca": 1,
                "attacks_dropped_ca": 1,
                "attacks_submitted_fallacy": 0,
                "attacks_dropped_fallacy": 0,
                "attacks_submitted_other": 0,
                "attacks_dropped_other": 0,
            },
            state,
            {},
        )
        blocks = collect(state.get_state_snapshot())
        agg = aggregate(blocks)
        rendered = _render({"document": "doc", **agg}, as_json=False)
        assert "contenu contre-argumentaire" not in rendered
        assert "ca:      1 / 1" in rendered  # nature KEY yes, source text no


class TestAttackSourceNatureProbeDedup:
    """R792 regression: the probe must NOT sum a surface raw. The same
    accounting declaration is replicated — the curated carry projects one
    axe onto several framework entries (×12 on corpus_A) and the bulk surface
    emits one block per axe over a shared candidate set (×2). Summing raw
    published 468 / 78 where the real candidate count is 39: a value true at
    every site, false once aggregated (#1019). Dedup by fingerprint collapses
    the replicas; the curated-vs-bulk agreement on deduped totals is printed
    as the verdict.

    Armed by the dedup — reverting to a raw sum makes the deduped-count
    assertion red (submitted would read 468, not 39). The snapshot dict is
    built directly: the probe is a reader of the snapshot shape, and the
    shape (14 entries / 2 fingerprints on corpus_A) is what the real state
    genuinely carries (measured R792).
    """

    _ACCOUNTING = {
        "attacks_submitted": 39,
        "attacks_retained": 0,
        "attacks_dropped": 39,
        "attacks_submitted_fallacy": 38,
        "attacks_dropped_fallacy": 38,
        "attacks_submitted_ca": 1,
        "attacks_dropped_ca": 1,
        "attacks_submitted_other": 0,
        "attacks_dropped_other": 0,
    }

    @classmethod
    def _block(cls, **overrides: Any) -> Dict[str, Any]:
        b: Dict[str, Any] = {"arguments": ["a", "b"], "attacks": []}
        b.update(cls._ACCOUNTING)
        b.update(overrides)
        return b

    def test_dedup_collapses_replication_to_the_real_candidate_count(self) -> None:
        from scripts.probe_attack_source_nature_split import (
            _aggregate,
            _collect_accounting,
            _render,
        )

        # corpus_A shape (R792): 14 curated entries — 12 share the accounting
        # fingerprint, 2 carry zeros — and 4 bulk axes — dung/social non-zero
        # and identical, setaf/weighted zero.
        zero = {
            "arguments": [],
            "attacks": [],
            "attacks_submitted": 0,
            "attacks_retained": 0,
            "attacks_dropped": 0,
        }
        curated = {f"fw_{i}": self._block(name=f"fw_{i}") for i in range(12)}
        curated["zero_a"] = dict(zero)
        curated["zero_b"] = dict(zero)
        state = {
            "dung_frameworks": curated,
            "formal_synthesis_reports": [
                {
                    "phase_results": {
                        "dung_extensions": self._block(),
                        "social_reasoning": self._block(),
                        "setaf_reasoning": dict(zero),
                        "weighted_reasoning": dict(zero),
                    }
                }
            ],
        }
        blocks = _collect_accounting(state)
        agg = _aggregate(blocks)

        curated_agg = agg["surfaces"]["curated"]
        assert curated_agg["blocks"] == 14
        assert curated_agg["distinct_fingerprints"] == 2  # the 39-block + zero
        assert curated_agg["max_multiplicity"] == 12
        assert curated_agg["replicated"] is True
        # Deduped total == the real candidate count, NOT 12 × 39 = 468.
        assert curated_agg["attacks_submitted"] == 39
        assert curated_agg["by_nature"]["fallacy"]["submitted"] == 38
        assert curated_agg["by_nature"]["ca"]["submitted"] == 1
        # The raw (inflated) sum is kept as a diagnostic.
        assert curated_agg["raw_attacks_submitted"] == 12 * 39

        bulk_agg = agg["surfaces"]["bulk"]
        assert bulk_agg["attacks_submitted"] == 39  # NOT 2 × 39 = 78
        assert bulk_agg["raw_attacks_submitted"] == 2 * 39

        # Both surfaces dedup to 39 ⇒ agreement, printed as the verdict.
        assert agg["inter_surface"]["comparable"] is True
        assert agg["inter_surface"]["agree"] is True
        rendered = _render({"document": "corpus_A", **agg}, as_json=False)
        assert "inter-surface verdict: AGREE (curated==bulk==39)" in rendered
        # The replication stays visible (it is not hidden by the dedup).
        assert "inflated 12x" in rendered

    def test_verdict_prints_disagreement_when_surfaces_diverge_after_dedup(
        self,
    ) -> None:
        from scripts.probe_attack_source_nature_split import (
            _aggregate,
            _collect_accounting,
            _render,
        )

        # Curated dedups to 39, bulk dedups to 15 ⇒ a genuine, post-dedup
        # disagreement that the verdict must surface (not paper over).
        state = {
            "dung_frameworks": {"fw_0": self._block()},
            "formal_synthesis_reports": [
                {
                    "phase_results": {
                        "dung_extensions": self._block(
                            attacks_submitted=15,
                            attacks_dropped=15,
                            attacks_submitted_fallacy=9,
                            attacks_dropped_fallacy=9,
                            attacks_submitted_ca=6,
                            attacks_dropped_ca=6,
                        )
                    }
                }
            ],
        }
        blocks = _collect_accounting(state)
        agg = _aggregate(blocks)
        assert agg["inter_surface"]["agree"] is False
        assert agg["inter_surface"]["ratio"] == round(39 / 15, 2)
        rendered = _render({"document": "divergent", **agg}, as_json=False)
        assert "inter-surface verdict: DISAGREE" in rendered
