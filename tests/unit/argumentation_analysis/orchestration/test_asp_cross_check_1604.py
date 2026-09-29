"""#1604 — wire ``asp_reasoning``: AF→ASP stable-extension cross-check.

The phase encodes the run's Dung AF as the standard ASP stable-extension
program and compares clingo's answer sets with Tweety's stable extensions —
two independent solvers, same framework (#1735 differential). Guards:

- the builder emits exactly the prescribed program (arg/att facts + the two
  stable-extension rules), with unsafe argument names carried by a bijection;
- the Python clingo binding is the decider (NAF): the JVM parser cannot
  express ``not out(X)`` — it would mint an atom named ``not out(X)`` and the
  rule could never fire, a quiet wrong verdict (#1019);
- known synthetic AFs agree (one stable extension, none, several);
- a hand-built disagreement witness reddens the comparison (the solver truth
  vs a hand-lie on the Tweety side);
- a phase without an AF (or without Tweety stable extensions) is ``skipped``
  with a named reason — it never "runs on the text";
- the state writer records the agreement as its own field.
"""

import pytest

from argumentation_analysis.orchestration.invoke_callables import (
    _af_to_asp_program,
    _asp_cross_check_from_dung,
    _compare_extension_sets,
    _invoke_asp_reasoning,
)
from argumentation_analysis.orchestration.state_writers import (
    _write_asp_to_state,
)


def _dung_output(arguments, attacks, stable):
    """Hand-build the enriched shape the dung_extensions phase emits."""
    return {
        "arguments": list(arguments),
        "attacks": [list(a) for a in attacks],
        "extensions": {"stable": {"extensions": [list(e) for e in stable]}},
    }


class TestBuilder:
    def test_program_text_is_the_prescribed_encoding(self):
        program, names = _af_to_asp_program(["a", "b"], [["a", "b"]])
        lines = program.splitlines()
        # constants are index-prefixed (categorically injective: no
        # predicate/variable clash, no prose ever reaches the parser)
        assert "arg(c0_a)." in lines
        assert "arg(c1_b)." in lines
        assert "att(c0_a,c1_b)." in lines
        assert "in(X) :- arg(X), not out(X)." in lines
        assert "out(X) :- att(Y,X), in(Y)." in lines
        assert lines[-1] == "#show in/1."
        assert names == {"a": "c0_a", "b": "c1_b"}

    def test_unsafe_names_are_carried_by_a_bijection(self):
        program, names = _af_to_asp_program(["la dette publique", "dette_publique"], [])
        # both sanitize to the same constant if naively stripped — the
        # builder must disambiguate, or the bijection is not injective
        assert len(set(names.values())) == len(names), f"constant collision: {names}"
        # no atom in the program carries a space (prose names never reach
        # the ASP parser)
        for line in program.splitlines():
            if line.startswith(("arg(", "att(")):
                assert " " not in line, line

    def test_attacks_outside_arguments_are_dropped(self):
        program, _ = _af_to_asp_program(["a"], [["a", "ghost"], ["ghost", "a"]])
        assert "ghost" not in program


class TestNAFDecider:
    def test_cross_check_decider_is_the_python_binding(self):
        result = _asp_cross_check_from_dung(
            _dung_output(["a", "b"], [["a", "b"]], [["a"]]), {}
        )
        assert result["status"] == "cross_check"
        assert result["solver"] == "clingo_python", (
            "the JVM parser cannot express NAF and must not decide the "
            "stable-extension program"
        )

    def test_no_naf_solver_is_a_named_degradation(self, monkeypatch):
        import sys

        monkeypatch.setitem(sys.modules, "clingo", None)
        result = _asp_cross_check_from_dung(_dung_output(["a"], [], [["a"]]), {})
        assert result["status"] == "degraded"
        assert "naf" in result["reason"].lower()
        assert "answer_sets" not in result, "no fabricated answer sets (#1019)"


class TestAgreement:
    def test_single_unattacked_argument_agrees(self):
        result = _asp_cross_check_from_dung(_dung_output(["a"], [], [["a"]]), {})
        assert result["agreement"] == "equal"
        assert result["asp_answer_sets"] == [["a"]]
        assert result["asp_only_extensions"] == []
        assert result["tweety_only_extensions"] == []

    def test_two_cycle_several_stable_extensions_agree(self):
        result = _asp_cross_check_from_dung(
            _dung_output(["a", "b"], [["a", "b"], ["b", "a"]], [["a"], ["b"]]),
            {},
        )
        assert result["agreement"] == "equal"
        assert sorted(map(tuple, result["asp_answer_sets"])) == [("a",), ("b",)]

    def test_self_attacker_no_stable_extension_agrees(self):
        result = _asp_cross_check_from_dung(_dung_output(["c"], [["c", "c"]], []), {})
        assert result["agreement"] == "equal"
        assert result["asp_answer_sets"] == []

    def test_hand_built_disagreement_witness_reddens(self):
        # ground truth: the 2-cycle has stable extensions {a} and {b}; the
        # Tweety side hand-lies with only {a}. The comparison must say so,
        # not rubber-stamp equality: ASP has a private extension, Tweety
        # has none — the verdict is "asp_only", and the private list names it.
        result = _asp_cross_check_from_dung(
            _dung_output(["a", "b"], [["a", "b"], ["b", "a"]], [["a"]]), {}
        )
        assert result["agreement"] == "asp_only"
        assert result["asp_only_extensions"] == [["b"]]
        assert result["tweety_only_extensions"] == []

    def test_compare_function_both_sides_differ(self):
        verdict = _compare_extension_sets([["a"], ["c"]], [["b"], ["c"]])
        assert verdict["agreement"] == "differ"
        assert verdict["asp_only_extensions"] == [["a"]]
        assert verdict["tweety_only_extensions"] == [["b"]]


class TestSkipDiscipline:
    async def test_no_af_no_program_keeps_legacy_path(self):
        result = await _invoke_asp_reasoning(
            "Long texte de discours politique, pas un programme ASP.",
            {},
        )
        # without a Dung AF the handler keeps its legacy program behaviour
        # (hand-written callers pass a program or expect this text path);
        # it must NOT be reported as a cross-check.
        assert result.get("status") != "cross_check"
        assert "agreement" not in result

    async def test_phase_without_af_is_skipped_with_named_reason(self):
        result = await _invoke_asp_reasoning(
            "Long texte de discours politique.",
            {"phase_dung_extensions_output": {"arguments": [], "attacks": []}},
        )
        assert result["status"] == "skipped"
        assert result["reason"] == "no_argumentation_framework"
        assert "answer_sets" not in result

    async def test_phase_without_tweety_stable_is_skipped_with_named_reason(self):
        af = _dung_output(["a"], [], [])
        af["extensions"] = {}  # degraded Dung run computed no semantics
        result = await _invoke_asp_reasoning(
            "Long texte de discours politique.",
            {"phase_dung_extensions_output": af},
        )
        assert result["status"] == "skipped"
        assert result["reason"] == "no_tweety_stable_extensions"

    async def test_dung_output_routes_to_cross_check_not_prose_parsing(self):
        # The routing itself: a context carrying the Dung phase output must
        # never feed the analysed prose to the ASP parser.
        result = await _invoke_asp_reasoning(
            "Le ministre affirme que la dette s'effondrera.",
            {"phase_dung_extensions_output": _dung_output(["a"], [], [["a"]])},
        )
        assert result["status"] == "cross_check"
        assert result["agreement"] == "equal"

    async def test_explicit_program_still_wins(self):
        result = await _invoke_asp_reasoning(
            "a.",
            {
                "program": "a :- not b.",
                "phase_dung_extensions_output": _dung_output(["x"], [], [["x"]]),
            },
        )
        # the explicit program path is unchanged (hand-written callers)
        assert result["answer_sets"] == [["a"]]


class TestWriter:
    def test_agreement_is_its_own_field(self):
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        state = UnifiedAnalysisState(initial_text="texte")
        output = _asp_cross_check_from_dung(
            _dung_output(["a", "b"], [["a", "b"], ["b", "a"]], [["a"], ["b"]]),
            {},
        )
        _write_asp_to_state(output, state, {})
        entries = [
            e
            for e in state.dung_frameworks.values()
            if "asp_cross_check" in (e.get("formalism_specific") or {})
        ]
        assert len(entries) == 1
        cross = entries[0]["formalism_specific"]["asp_cross_check"]
        assert cross["agreement"] == "equal"
        assert cross["solver"] == "clingo_python"
        assert entries[0]["extensions"]["asp_answer_sets"] == [["a"], ["b"]]

    def test_skipped_output_writes_nothing(self):
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        state = UnifiedAnalysisState(initial_text="texte")
        _write_asp_to_state({"status": "skipped", "reason": "x"}, state, {})
        assert not any(
            "asp_cross_check" in (e.get("formalism_specific") or {})
            for e in state.dung_frameworks.values()
        )


class TestSelectorSelectsSomethingReal:
    """#1604 DoD: ``--formal-extension=asp`` selects the cross-check phase."""

    def test_asp_filter_keeps_the_cross_check_phase(self):
        from argumentation_analysis.orchestration.workflows import (
            build_formal_extended_workflow,
            filter_formal_extensions,
        )

        wf = filter_formal_extensions(build_formal_extended_workflow(), "asp")
        caps = [p.capability for p in wf.phases]
        assert (
            "asp_reasoning" in caps
        ), "'asp' passed the unknown-name check and must select the phase"
        # core drops the extensions, asp included
        wf_core = filter_formal_extensions(build_formal_extended_workflow(), "core")
        assert "asp_reasoning" not in [p.capability for p in wf_core.phases]
