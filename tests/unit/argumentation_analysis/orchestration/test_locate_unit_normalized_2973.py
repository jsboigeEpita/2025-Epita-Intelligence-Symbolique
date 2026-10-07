"""#2973 — locate_unit_offset survives the producer's normalization.

On the paid run of 06/10, **33 of 94** provenance entries carried
``offset: None`` — all heuristic units. ``locate_unit_offset`` searched the
text for the unit's EXACT text, but the heuristic producer joins
stripped sentences with single spaces, so the unit never occurs verbatim
in the source (measured: a 40-character prefix WAS found). The 33 assert
moves left the narrated argumentative sequence for that reason alone, and
nobody knew the census until the traces were analyzed by hand.

The rule is now a cascade — exact unique, whitespace-flexible unique, then
a unique prefix of at least ``_UNIT_PREFIX_MIN`` characters — and NEVER a
non-unique match: ambiguity is a named absence, not a guess (#1019). The
assert anchor (``_record_assert_move``) uses the SAME rule, and the census
of unanchored units is recorded IN the run (``anchor_census`` coverage
entry).

Privacy: invented filler, opaque ids. Deterministic: no JVM, no LLM.
"""

from __future__ import annotations

from argumentation_analysis.core.shared_state import (
    UnifiedAnalysisState,
    locate_unit_offset,
    locate_unit_span,
)
from argumentation_analysis.orchestration.state_writers import (
    _record_assert_move,
    _write_text_to_kb_to_state,
)

# The source's shape: sentences separated by newlines and double spaces.
_RAW = (
    "Premier développement assez long pour être une phrase complète.  \n"
    "Deuxième développement qui suit, avec sa propre ponctuation.   \n"
    "Troisième segment pour donner du corps au texte et une deuxième\n"
    "occurrence possible."
)
# The heuristic unit: the same sentences, stripped and joined by ONE space —
# exactly what _heuristic_extract_arguments produces.
_UNIT = (
    "Deuxième développement qui suit, avec sa propre ponctuation. "
    "Troisième segment pour donner du corps au texte et une deuxième "
    "occurrence possible."
)
_EXACT = "Premier développement assez long pour être une phrase complète."


class TestTheCascade:
    def test_exact_unit_keeps_its_exact_offset(self) -> None:
        offset, basis = locate_unit_offset(_EXACT, _RAW)
        assert offset == _RAW.find(_EXACT)
        assert "espaces flexibles" not in basis  # the exact basis stays the exact one

    def test_the_issues_witness_normalized_unit_is_located(self) -> None:
        """A unit equal to a span modulo collapsed whitespace: located, at
        the span's start — on main this was ``None``."""
        offset, basis = locate_unit_offset(_UNIT, _RAW)
        assert offset == _RAW.find("Deuxième développement")
        assert "espaces flexibles" in basis

    def test_a_unique_prefix_locates_when_the_full_unit_fails(self) -> None:
        """The arg_12 shape: the full text differs beyond the prefix, but a
        unique 40-character prefix is enough to place the unit."""
        # unit whose tail was rewritten by the producer (case shift never
        # happens in production; the prefix carries the localization)
        unit = _UNIT[:40] + " et une fin que le texte source ne porte pas."
        offset, _ = locate_unit_offset(unit, _RAW)
        assert offset == _RAW.find("Deuxième développement")

    def test_positive_control_a_duplicated_prefix_stays_unlocated(self) -> None:
        """Never a non-unique match: a unit whose prefix occurs twice keeps
        ``None`` and the reason names the ambiguity."""
        raw = _RAW + "\n" + _RAW  # everything occurs twice
        offset, basis = locate_unit_offset(_UNIT, raw)
        assert offset is None
        assert "ambiguë" in basis or "ambigu" in basis


class TestTheAssertAnchorUsesTheSameRule:
    def _state(self) -> UnifiedAnalysisState:
        return UnifiedAnalysisState(_RAW)

    def test_the_normalized_unit_gets_its_anchored_assert(self) -> None:
        """The measured consequence: on main the 33 heuristic units' asserts
        left the sequence because the anchor re-searched the exact text."""
        state = self._state()
        arg_id = state.add_argument(_UNIT, producer="kb_heuristic")
        _record_assert_move(state, arg_id, _UNIT, _RAW)
        entry = state.analysis_trace[-1]
        assert entry["anchor"] is not None
        assert entry["anchor"]["offset"] == _RAW.find("Deuxième développement")
        # the anchor's length is the RAW span's length, not the key's
        span, _ = locate_unit_span(_UNIT, _RAW)
        assert entry["anchor"]["length"] == span[1] - span[0]

    def test_exact_quote_keeps_the_exact_basis(self) -> None:
        state = self._state()
        arg_id = state.add_argument(_EXACT, producer="llm_extract")
        _record_assert_move(state, arg_id, _EXACT, _RAW)
        entry = state.analysis_trace[-1]
        assert entry["anchor"]["offset"] == 0
        assert "ancre offset 0" in entry["summary"]

    def test_absent_quote_stays_an_absence_with_a_reason(self) -> None:
        state = self._state()
        arg_id = state.add_argument("introuvable ici", producer="llm_extract")
        _record_assert_move(state, arg_id, "introuvable ici", _RAW)
        entry = state.analysis_trace[-1]
        assert "anchor" not in entry
        assert "sans ancre" in entry["summary"]


class TestTheCensusIsInTheRun:
    def test_text_to_kb_records_the_unanchored_census(self) -> None:
        """The issue's DoD: the census is part of the run's coverage record,
        not something trace analysis discovers afterwards."""
        state = UnifiedAnalysisState(_RAW)
        output = {
            "arguments": [
                {"text": _UNIT},  # locatable after the fix
                {"text": "une unité que le texte ne porte pas du tout ici"},
            ],
            "belief_candidates": [],
        }
        _write_text_to_kb_to_state(output, state, {})
        census = state.analysis_coverage.get("anchor_census")
        assert census is not None
        assert census["N"] == 2
        assert census["k"] == 1  # the normalized unit is now anchored
        assert census["unanchored_by_producer"] == {"kb_heuristic": 1}
        assert len(census["unanchored_ids"]) == 1

    def test_all_anchored_is_said_as_such(self) -> None:
        state = UnifiedAnalysisState(_RAW)
        _write_text_to_kb_to_state(
            {"arguments": [{"text": _EXACT}], "belief_candidates": []}, state, {}
        )
        census = state.analysis_coverage["anchor_census"]
        assert census["k"] == census["N"] == 1
        assert census["unanchored_ids"] == []
        assert census["unanchored_by_producer"] == {}

    def test_the_census_renders_as_its_own_anchoring_clause(self) -> None:
        """Review #2979 (ai-01, R1072): the census counts units LOCATED in the
        text, not units EXAMINED — inside « Couverture de l'analyse » it reads
        as one more analysis. It renders in its own clause, worded as
        anchoring, and still borrows no bands (« 0/0 tiers »)."""
        from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
            build_act1_prompt,
        )
        from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
            build_act1_evidence,
        )

        state = UnifiedAnalysisState(_RAW)
        _write_text_to_kb_to_state(
            {"arguments": [{"text": _EXACT}], "belief_candidates": []}, state, {}
        )
        # a real examined phase, so the coverage parenthesis exists beside the
        # census — the contrast the review asks for
        state.analysis_coverage["atms"] = {
            "k": 1,
            "N": 1,
            "bands_covered": 0,
            "bands_total": 3,
        }
        prompt = build_act1_prompt(build_act1_evidence(state))
        assert "Ancrage dans le texte : 1/1 unités localisées" in prompt
        # the census is OUT of the coverage parenthesis — a reader must not
        # read « 1/1 » as analysis coverage
        coverage = prompt.split("Couverture de l'analyse (", 1)[1].split(")", 1)[0]
        assert "anchor_census" not in coverage
        assert "atms : 1/1 unités" in coverage
        assert "0/0 tiers" not in prompt

    def test_a_partial_census_says_what_is_missing(self) -> None:
        """A unit the text does not carry is stated, not glossed over."""
        from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
            build_act1_prompt,
        )
        from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
            build_act1_evidence,
        )

        state = UnifiedAnalysisState(_RAW)
        _write_text_to_kb_to_state(
            {
                "arguments": [
                    {"text": _UNIT},
                    {"text": "une unité que le texte ne porte pas du tout ici"},
                ],
                "belief_candidates": [],
            },
            state,
            {},
        )
        prompt = build_act1_prompt(build_act1_evidence(state))
        assert "Ancrage dans le texte : 1/2 unités localisées" in prompt
        assert "1 sans position, lecture heuristique" in prompt
