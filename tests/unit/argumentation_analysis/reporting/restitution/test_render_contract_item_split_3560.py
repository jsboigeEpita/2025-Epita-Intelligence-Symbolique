# -*- coding: utf-8 -*-
"""#3560 item 23b — the motif states the review-item channel's split.

The per-item treatment of the review-item channel is not measurable (the
#3560 finding: the quote run is language-bound, the unit binding is
necessary-not-sufficient), so no count of TREATED items can be stated. What
IS deterministic is the channel's STRUCTURE: how many items sit on units
the evidence explicitly did not examine (« non examinés »), how many on
everything else. The motif states that split — « N constats remis : X sur
unités examinées, Y sur unités non examinées » — and ONLY the motif: the
reader's count line states proven channels only, and the split says the
structure, not the treatment, so it never reaches the reader
(coordinator anti-pendulum: no new line in the reader's text).

Witnessed here, with no key, no network and no corpus (the document and
its passages are made up):

- the unmeasured motif clause carries the split, and the split sums to
  the channel's total by construction;
- the reader's count line gains NO split — its vocabulary is unchanged;
- the check's FAIL reasons gain no split either;
- ``read_render_contract`` derives the split from the evidence itself: an
  item on a unit the « non examinés » movement carries counts Y; an item
  on a taxonomy movement's unit or with no unit at all counts X.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from argumentation_analysis.agents.core.reading.coverage_review import LENS_BY_CLASS
from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_evidence,
)
from argumentation_analysis.reporting.restitution.movement_render_contract import (
    RenderContractReading,
    check_render_contract,
    read_render_contract,
    render_contract_motif,
    render_count_line,
)

# --- the shared synthetic document (same family as the 3560 witness) -------

OPENING = "Speaker_A ouvre le débat sur une thèse simple."
FILLER = " ".join(
    f"Phrase de contexte numéro {index} pour installer le débat."
    for index in range(1, 31)
)
DOCUMENT = f"{OPENING} {FILLER}"
UNITS = {
    "arg_1": "Un cas unique est monté en règle pour justifier la mesure.",
    "arg_5": "Une réserve tardive n'entre jamais dans le débat principal.",
}
FALLACIES = {
    "f_1": {
        "target_argument_id": "arg_1",
        "family": "Erreur de raisonnement",
        "type": "Généralisation hâtive",
        "justification": "Un cas unique ne fonde pas une règle générale.",
    },
}


def _item(unit_id: str) -> dict:
    return {
        "unit_id": unit_id,
        "quote": "Trois chiffres sur quatre appuient la mesure, sans jamais la qualifier.",
        "offset": 0,
        "class": "statistical",
        "lens": LENS_BY_CLASS["statistical"],
        "reason": "le manquer coûterait au lecteur sa décision",
        "conclusion": "cet argument conclut par lui-même que la mesure tient",
        "rank": 1,
        "routed": {
            "lens": LENS_BY_CLASS["statistical"],
            "status": "lens_not_wired",
            "reason": "synthetic",
        },
    }


def _state() -> SimpleNamespace:
    """arg_5 is a unit the per-argument fallacy pass did NOT examine.

    ``analysis_coverage['fallacy_per_argument']['unit_ids']`` records the
    pass's sample; arg_5 sits outside it and carries no fallacy, so the
    evidence builder assigns it the canonical « non examinés » movement.
    """
    return SimpleNamespace(
        raw_text=DOCUMENT,
        identified_arguments=dict(UNITS),
        identified_fallacies={k: dict(v) for k, v in FALLACIES.items()},
        argument_quality_scores={},
        counter_arguments=[],
        analysis_coverage={
            "fallacy_per_argument": {"unit_ids": ["arg_1"]},
        },
        coverage_review={
            "status": "ok",
            "items": [_item("arg_1"), _item("arg_5"), _item("")],
            "examined": 3,
            "examined_by_class": {},
            "document_chars": len(DOCUMENT),
            "dropped": {},
            "reason": "",
            "basis": "coverage_review",
        },
    )


def _reading(**kwargs) -> RenderContractReading:
    base = dict(
        movements_total=2,
        movements_treated=2,
        items_total=15,
        items_treated=8,
        items_measured=False,
        items_on_unexamined_units=6,
    )
    base.update(kwargs)
    return RenderContractReading(**base)


class TestMotifStatesTheSplit:
    def test_the_unmeasured_clause_carries_the_split(self):
        motif = render_contract_motif(_reading())
        assert (
            "15 constats de couverture remis au rédacteur : "
            "9 sur unités examinées, 6 sur unités non examinées, "
            "mesure non éprouvée sur ce canal — aucun compte énoncé" in motif
        )

    def test_the_split_sums_to_the_total_by_construction(self):
        reading = _reading(items_total=15, items_on_unexamined_units=6)
        assert reading.items_on_examined_units == 9
        assert (
            reading.items_on_examined_units + reading.items_on_unexamined_units
            == reading.items_total
        )


class TestTheReaderGainsNoSplit:
    """Anti-pendulum: the split says structure, not treatment — the reader's
    surfaces (count line, FAIL reasons) never see it."""

    def test_the_count_line_names_no_unit_population(self):
        line = render_count_line(_reading())
        assert "unités examinées" not in line
        assert "unités non examinées" not in line

    def test_the_fail_reasons_name_no_unit_population(self):
        reading = _reading(movements_total=3, movements_treated=1)
        verdict = check_render_contract(reading)
        assert verdict.band == "FAIL"
        for reason in verdict.reasons:
            assert "unités examinées" not in reason
            assert "unités non examinées" not in reason


class TestTheReadingDerivesTheSplit:
    def test_items_on_the_non_examine_movement_count_as_such(self):
        reading = read_render_contract(
            "Un cas unique est monté en règle pour justifier la mesure.",
            build_act2_evidence(_state()),
            _state(),
        )
        assert reading.items_total == 3
        assert reading.items_on_unexamined_units == 1
        assert reading.items_on_examined_units == 2

    def test_a_state_without_the_sample_records_no_split_either_way(self):
        """When the pass did not record its sample, no unit can be called
        non-examined — the split reads all-examined and says so."""
        state = _state()
        state.analysis_coverage = {}
        reading = read_render_contract(
            "Un cas unique est monté en règle pour justifier la mesure.",
            build_act2_evidence(state),
            state,
        )
        assert reading.items_on_unexamined_units == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
