# -*- coding: utf-8 -*-
"""#3146 — a refuted PL record's recorded core IS the tested content.

The R1106 tunnel pass measured two acts contradicting each other: Act II
rendered « contenu non disponible, attached to no move » for a PL refutation
whose ``consistency_cause`` records ``mus = true`` with a two-formula core at
indices ``[4, 6]`` — the exact conflict — while Act III and the synthesis,
reading the same state, described the two-formula minimal core. Two defects,
one under the other:

* ``_UNIT_LITERAL`` rejects ``'! p'`` (the translator writes a space after
  the negation), so the offline localizer finds no pair and the tested
  content renders as absent for content that exists;
* the localizer re-derives offline what #3122's deletion sweep already
  computed exactly — ``consistency_cause.core.indices`` is the minimal
  unsatisfiable core, and the regex is a weaker second producer of the same
  fact (#2960 predates #3122).

The fix reads the recorded core FIRST (``mus`` true only — the degraded
whole-theory shape minimised nothing and is not a core), keeps the localizer
as the fallback for records without one, and hands the cause's source units
back so the finding binds the verdict to the batch's units instead of
« attached to no move ».

Synthetic atoms only — no corpus text (privacy HARD). The decoy pair
(``!q_decoy`` / ``q_decoy``, no space, first in list order) is what makes the
mutation observable: a fallback that ignores the recorded core localizes the
DECOY, and the witness asserting the core's atom goes red — #2960's principle
(the verdict belongs to the conflict the solver singled out, not to whatever
comes first in list order) made falsifiable.
"""

from types import SimpleNamespace

from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    _collect_formal_findings,
    build_act2_evidence,
    build_act2_prompt,
)
from argumentation_analysis.reporting.restitution.formal_derivation import (
    _locate_conflict_pair,
    extract_tested_content,
)


def _pl_verdict(r):
    sat = r.get("satisfiable")
    if sat is None:
        sat = r.get("consistent")
    return sat if isinstance(sat, bool) else None


# The measured shape of a #3122 PL cause for an unsplittable translation
# batch: batch_attribution, a 2-formula MUS at [4, 6], three source units.
_CORE_RECORD = {
    "formulas": [
        "!q_decoy",  # 0 — decoy pair: localizable by list order alone
        "q_decoy",  # 1
        "filler_left && side_b",  # 2 — compound filler
        "another_plain_filler",  # 3
        "! p_core",  # 4 — the recorded core: space after the negation
        "middle_filler",  # 5
        "p_core",  # 6
    ],
    "satisfiable": False,
    "consistency_cause": {
        "cause": "batch_attribution",
        "ground": False,
        "mus": True,
        "core": {"size": 2, "indices": [4, 6]},
        "pairs": [
            {
                "sources": [["arg_53", "arg_65", "arg_76"], []],
                "speakers": [[], []],
                "cause": "batch_attribution",
            }
        ],
        "formulas": 7,
        "units_known": True,
        "speakers_known": False,
    },
}


class TestRecordedCoreFirst:
    """DoD 1 — the recorded core is the tested content, not the decoy."""

    def test_a_refuted_records_recorded_core_is_the_tested_content(self):
        """A refuted record with a 2-formula core at [4, 6] (``! p_core`` /
        ``p_core``, with a space) yields tested content naming the core —
        red on main: the regex rejects the spaced negation and the localizer
        falls back to the decoy pair first in list order."""
        out = extract_tested_content([_CORE_RECORD], _pl_verdict, refuted=True)
        assert out is not None
        assert "p core" in out
        # the decoy pair (list order) is NOT the conflict the run recorded
        assert "q decoy" not in out

    def test_the_tuple_reader_hands_back_content_and_units(self):
        """#3146 request 3: the same reader hands back the source units the
        cause names — the binding is to the batch's unit set, never to one
        unit the state did not single out."""
        from argumentation_analysis.reporting.restitution.formal_derivation import (
            tested_content_and_units,
        )

        content, units = tested_content_and_units(
            [_CORE_RECORD], _pl_verdict, refuted=True
        )
        assert content is not None
        assert "p core" in content
        assert units == ["arg_53", "arg_65", "arg_76"]


class TestFallbackToleratesWhitespace:
    """DoD 2 — the offline localizer accepts ``! atom`` (with a space)."""

    def test_the_localizer_matches_a_spaced_negation(self):
        pair = _locate_conflict_pair(["! p_unit", "p_unit"])
        assert pair == ("! p_unit", "p_unit")

    def test_a_record_without_a_core_localizes_its_spaced_pair(self):
        records = [
            {
                "formulas": ["first_standing_claim", "! spaced_atom", "spaced_atom"],
                "satisfiable": False,
            }
        ]
        out = extract_tested_content(records, _pl_verdict, refuted=True)
        assert out is not None
        assert "spaced atom" in out
        assert "first standing claim" not in out


class TestHonestBoundaries:
    """DoD 3 — the controls: no recorded core, and no core claimed either."""

    def test_a_record_without_a_core_still_yields_none_on_a_spread_conflict(self):
        """#2960 control: a conflict spread over compound formulas without a
        recorded core is not localizable offline — the honest absence."""
        records = [
            {
                "formulas": [
                    "alliance_holds & trade_open",
                    "!alliance_holds || !trade_open",
                ],
                "satisfiable": False,
            }
        ]
        assert extract_tested_content(records, _pl_verdict, refuted=True) is None

    def test_a_whole_theory_cause_is_not_a_localized_core(self):
        """The degraded ``mus`` false shape minimised NOTHING — rendering the
        whole theory would pin the refutation on the batch (#2960's defect in
        another font). It must not be read as a core."""
        records = [
            {
                "formulas": [
                    "alliance_holds & trade_open",
                    "!alliance_holds || !trade_open",
                ],
                "satisfiable": False,
                "consistency_cause": {
                    "cause": "batch_attribution",
                    "mus": False,
                    "core": {"size": 2, "indices": [0, 1]},
                    "pairs": [{"sources": [["arg_7"], []], "speakers": [[], []]}],
                    "formulas": 2,
                    "units_known": True,
                },
            }
        ]
        assert extract_tested_content(records, _pl_verdict, refuted=True) is None


class TestUnitsReachTheAct:
    """#3146 request 3 — the finding carries the units; the act can bind."""

    @staticmethod
    def _state():
        return SimpleNamespace(
            propositional_analysis_results=[dict(_CORE_RECORD)],
            fol_analysis_results=None,
            modal_analysis_results=None,
            identified_arguments={},
            identified_fallacies=None,
            argument_quality_scores=None,
        )

    def test_the_pl_finding_carries_the_cores_source_units(self):
        findings = _collect_formal_findings(self._state())
        pl = next(f for f in findings if f.kind == "pl")
        assert getattr(pl, "units", None) == ["arg_53", "arg_65", "arg_76"]

    def test_the_units_reach_the_conductors_formal_anchor(self):
        """The anchor line the conductor reads names the batch's units — the
        verdict binds to a move instead of « attached to no move »."""
        prompt = build_act2_prompt(build_act2_evidence(self._state()))
        assert "arg_53" in prompt
        assert "arg_76" in prompt
        # and the binding rule says the lot, not one unit
        assert "lot de traduction" in prompt
