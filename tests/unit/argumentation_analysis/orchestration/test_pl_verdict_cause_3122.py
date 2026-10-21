"""#3122 — a PL UNSAT states its cause, and the acts read it.

The PL twin of #3107. The render was handed one fact — ``satisfiable: False``
— and no cause: the R1104 entry held 38 formulas, 10 unit literals, 0
complementary unit pairs, the contradiction spread over 28 implications, and
the synthesis read the bare UNSAT as "the discourse does not hold together as
a single consistent set of commitments" — exactly the conclusion #3107
removed from the FOL leg on a two-voice document.

The repair is the same fact, not a prompt: each formula keeps the source unit
it was translated from (``formula_sources``), an UNSAT verdict carries a
minimal unsatisfiable subset computed by deletion (≤ one solver call per
formula), mapped to its units and classified with the SAME cause classes and
phrasing as the FOL leg — one shared classifier in ``fol_cause``, not a copy.

Witnessed here:

* a minimal core spanning two source units ⇒ ``between_sources`` — the phrase
  names the units, never "voices";
* a core inside one unit ⇒ ``self_contradiction`` — a real finding, kept
  (anti-pendulum: the UNSAT itself is never hidden or downgraded);
* two known speakers ⇒ ``between_voices``; one speaker across their own
  units ⇒ ``self_contradiction`` (FOL parity);
* the deletion loop costs at most one oracle call per formula and every core
  member is necessary (removing any one makes the set satisfiable);
* the real solver (PySAT, offline) finds the same core the fake oracle does.

Real ``UnifiedAnalysisState`` objects, the production writer and readers,
opaque atoms — no network, no LLM, zero spend.
"""

from __future__ import annotations

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.fol_cause import (
    cause_phrase,
    classify_pl_inconsistency,
    mus_by_deletion,
)
from argumentation_analysis.orchestration.state_writers import (
    _write_propositional_to_state,
)
from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    _collect_formal_findings,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    _collect_weak_points,
    _pl_stated_causes,
    build_act3_prompt,
    Act3Evidence,
)
from argumentation_analysis.reporting.restitution.appendix import _pl_axis_status

#: The R1104 shape in miniature: UNSAT with no complementary unit pair —
#: the contradiction is carried by the implication chain, not by two units.
_CHAIN = ["a => b", "b => c", "a", "!c"]
_CHAIN_SOURCES_SPLIT = [["u1"], ["u2"], ["u1"], ["u2"]]
_CHAIN_SOURCES_ONE_UNIT = [["u1"], ["u1"], ["u1"], ["u1"]]


def _pl_output(
    formulas,
    sources,
    cause,
    satisfiable=False,
    extra=None,
):
    out = {
        "formulas": list(formulas),
        "satisfiable": satisfiable,
        "model": {},
        "axiom_count": len(formulas),
        "query_count": 0,
        "message": "Inconsistent (UNSAT). Solver: cadical195",
        "logic_type": "propositional",
    }
    if sources is not None:
        out["formula_sources"] = [list(s) for s in sources]
    if cause is not None:
        out["consistency_cause"] = cause
    if extra:
        out.update(extra)
    return out


class TestMusByDeletion:
    def test_deletion_finds_a_minimal_core_with_at_most_one_call_per_formula(self):
        # UNSAT exactly when {0, 1, 2} are all present; formula 3 is a spectator.
        idx = {f: i for i, f in enumerate(_CHAIN)}
        core_needed = {0, 1, 2}
        calls = []

        def oracle(subset):
            calls.append(1)
            present = {idx[str(f)] for f in subset}
            return core_needed <= present

        core = mus_by_deletion(_CHAIN, oracle)
        assert sorted(core) == [0, 1, 2]
        assert len(calls) <= len(
            _CHAIN
        ), "the issue bounds the sweep: one call per formula"

    def test_every_core_member_is_necessary(self):
        idx = {f: i for i, f in enumerate(_CHAIN)}

        def oracle(subset):
            present = {idx[str(f)] for f in subset}
            return {0, 1, 2} <= present

        core = sorted(mus_by_deletion(_CHAIN, oracle))
        for drop in core:
            remaining = [f for j, f in enumerate(_CHAIN) if j in core and j != drop]
            assert (
                oracle(remaining) is False
            ), "removing any core member must satisfy the set"

    def test_the_caller_establishes_unsat_that_is_the_contract(self):
        # A satisfiable set must not be fed to the loop; the production caller
        # gates on the verdict (``satisfiable is False``), mirroring #3107's
        # ``_cause_for``. This witness pins the shape, not the guard.
        assert mus_by_deletion(["p"], lambda subset: True) == [0]


class TestPlCauseClassification:
    def test_a_core_spanning_two_source_units_is_between_sources(self):
        cause = classify_pl_inconsistency(
            _CHAIN, _CHAIN_SOURCES_SPLIT, {}, core_indices=[0, 1, 2, 3]
        )
        assert cause["cause"] == "between_sources"
        assert cause["mus"] is True
        assert cause["core"]["size"] == 4
        phrase = cause_phrase(cause)
        assert "unités sources" in phrase
        assert "voix" not in phrase, "an unknown speaker must not be invented"
        assert "cœur minimal" in phrase, "the MUS is the stated mechanism"

    def test_a_core_inside_one_unit_is_self_contradiction(self):
        cause = classify_pl_inconsistency(
            _CHAIN, _CHAIN_SOURCES_ONE_UNIT, {}, core_indices=[0, 1, 2, 3]
        )
        assert cause["cause"] == "self_contradiction"
        phrase = cause_phrase(cause)
        assert "auto-contradiction de u1" in phrase

    def test_two_known_speakers_make_between_voices(self):
        speakers = {"u1": "Speaker_A", "u2": "Speaker_B"}
        cause = classify_pl_inconsistency(
            _CHAIN, _CHAIN_SOURCES_SPLIT, speakers, core_indices=[0, 1, 2, 3]
        )
        assert cause["cause"] == "between_voices"
        phrase = cause_phrase(cause)
        assert "Speaker_A" in phrase and "Speaker_B" in phrase

    def test_one_speaker_across_their_own_units_is_self_contradiction(self):
        speakers = {"u1": "Speaker_A", "u2": "Speaker_A"}
        cause = classify_pl_inconsistency(
            _CHAIN, _CHAIN_SOURCES_SPLIT, speakers, core_indices=[0, 1, 2, 3]
        )
        assert cause["cause"] == "self_contradiction"
        assert "Speaker_A" in cause_phrase(cause)

    def test_entangled_batches_stay_batch_attribution(self):
        sources = [["u1", "u2"]] * 4
        cause = classify_pl_inconsistency(
            _CHAIN, sources, {}, core_indices=[0, 1, 2, 3]
        )
        assert cause["cause"] == "batch_attribution"
        assert "lot de traduction" in cause_phrase(cause)

    def test_unknown_provenance_is_undetermined_but_the_core_still_counts(self):
        cause = classify_pl_inconsistency(
            _CHAIN, [[], [], [], []], {}, core_indices=[0, 1, 2, 3]
        )
        assert cause["cause"] == "undetermined"
        phrase = cause_phrase(cause)
        assert "cause non établie" in phrase
        assert (
            "cœur minimal" in phrase
        ), "the core is established even when units are not"

    def test_without_a_core_the_whole_theory_is_the_honest_boundary(self):
        cause = classify_pl_inconsistency(_CHAIN, _CHAIN_SOURCES_SPLIT, {})
        assert cause["cause"] == "between_sources"
        assert cause["mus"] is False
        assert "cœur minimal" not in cause_phrase(cause)


class TestRealSolverCore:
    """The deletion loop against the real PySAT engine — offline, no JVM."""

    def _oracle(self):
        from argumentation_analysis.agents.core.logic.sat_handler import SATHandler

        handler = SATHandler()

        def oracle(subset):
            ok, _msg = handler.check_consistency(list(subset))
            return ok is False

        return oracle

    def test_the_real_solver_finds_the_chain_core_and_classifies_it(self):
        cause = classify_pl_inconsistency(
            _CHAIN,
            _CHAIN_SOURCES_SPLIT,
            {},
            is_unsat=self._oracle(),
        )
        assert cause["mus"] is True
        assert cause["core"]["size"] == 4, "the chain needs all four formulas"
        assert cause["cause"] == "between_sources"

    def test_a_direct_pair_inside_one_unit_is_self_contradiction(self):
        cause = classify_pl_inconsistency(
            ["p", "!p"], [["u1"], ["u1"]], {}, is_unsat=self._oracle()
        )
        assert cause["core"]["size"] == 2
        assert cause["cause"] == "self_contradiction"


class TestWriterAndRender:
    def _state_with_unsat(self, sources, speakers=None):
        state = UnifiedAnalysisState("texte")
        for unit, speaker in (speakers or {}).items():
            state.argument_provenance[unit] = {"speaker": speaker}
        cause = classify_pl_inconsistency(
            _CHAIN, sources, speakers or {}, core_indices=[0, 1, 2, 3]
        )
        _write_propositional_to_state(_pl_output(_CHAIN, sources, cause), state, {})
        return state, cause

    def test_unsat_entry_carries_sources_and_cause(self):
        state, cause = self._state_with_unsat(_CHAIN_SOURCES_SPLIT)
        entry = state.propositional_analysis_results[0]
        assert entry["satisfiable"] is False
        assert entry["formula_sources"] == _CHAIN_SOURCES_SPLIT
        assert entry["consistency_cause"]["cause"] == "between_sources"

        status = _pl_axis_status(state.propositional_analysis_results)
        assert status["insatisfiables"] == 1
        assert any("unités sources" in c for c in status.get("causes", [])), status

    def test_act2_finding_carries_the_cause(self):
        state, _ = self._state_with_unsat(_CHAIN_SOURCES_SPLIT)
        findings = _collect_formal_findings(state)
        pl = [f for f in findings if f.kind == "pl"]
        assert len(pl) == 1
        assert "unités sources" in pl[0].detail
        assert "invalid" not in pl[0].detail.lower()

    def test_act3_weak_point_and_prompt_read_the_cause(self):
        state, _ = self._state_with_unsat(_CHAIN_SOURCES_SPLIT)
        assert any(
            "unités sources" in c for c in _pl_stated_causes(state)
        ), _pl_stated_causes(state)
        weak = _collect_weak_points(
            {}, {}, 1, 0, None, pl_causes=_pl_stated_causes(state)
        )
        assert "unités sources" in weak[0].label

        prompt = build_act3_prompt(Act3Evidence())
        assert "DIS LA CAUSE" in prompt
        assert "insatisfiable" in prompt, "the rule covers the PL verdict too"

    def test_a_satisfiable_theory_states_no_cause(self):
        state = UnifiedAnalysisState("texte")
        _write_propositional_to_state(
            _pl_output(_CHAIN, _CHAIN_SOURCES_SPLIT, None, satisfiable=True),
            state,
            {},
        )
        entry = state.propositional_analysis_results[0]
        assert entry["satisfiable"] is True
        assert "consistency_cause" not in entry

    def test_misaligned_sources_are_not_attached(self):
        state = UnifiedAnalysisState("texte")
        _write_propositional_to_state(_pl_output(_CHAIN, [["u1"]], None), state, {})
        entry = state.propositional_analysis_results[0]
        assert "formula_sources" not in entry

    def test_guest_entries_never_state_a_cause(self):
        state = UnifiedAnalysisState("texte")
        state.add_propositional_analysis_result(
            ["CL(3 conditionals): analysed"], False, {}
        )
        assert _pl_stated_causes(state) == []

    def test_the_synthesis_briefing_carries_the_cause(self):
        from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
            DeepSynthesisAgent,
        )

        state, _ = self._state_with_unsat(_CHAIN_SOURCES_SPLIT)
        briefing = DeepSynthesisAgent.build_artifact_briefing(state)
        pl_lines = [
            line
            for line in briefing.splitlines()
            if "propositional_analysis_results" in line
        ]
        assert pl_lines, "the PL digest must reach the briefing"
        assert any(
            "cause=contradiction entre unités sources" in l for l in pl_lines
        ), pl_lines
