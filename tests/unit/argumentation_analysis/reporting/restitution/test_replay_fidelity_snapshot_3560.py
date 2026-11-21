# -*- coding: utf-8 -*-
"""#3560 item 25 — the snapshot replay reproduces the Act II evidence.

The coordinator's replay reading of the recorded cycles measured render
divergences whose seat was not named: either the REPLAY is unfaithful (a
code cause — the snapshot loses or degrades something the evidence
builder reads) or the RECORDED RUN itself diverged (then the witness
stays green and the seat of record is the run, read on the coordinator's
own archives).

This witness is the synthetic control for the first branch: it builds a
state through the PRODUCTION class and its PRODUCTION setters, builds the
live evidence, takes the snapshot exactly the way the dump writer does
(``get_state_snapshot(summarize=False)`` then a JSON text), rebuilds a
state from the parsed dump the way a replay does (attribute access), and
rebuilds the evidence. The comparison covers what the dispatch names:
the movements' TOTALS and the TARGET IDS each movement carries — plus
the render-contract reading's structural numbers, which the replay
exists to compute.

No key, no network, no corpus — the document and its passages are made
up.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from argumentation_analysis.agents.core.reading.coverage_review import LENS_BY_CLASS
from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_evidence,
)
from argumentation_analysis.reporting.restitution.movement_render_contract import (
    read_render_contract,
)

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
    "f_2": {
        "target_argument_id": "arg_9",
        "family": "Erreur de raisonnement",
        "type": "Appel à l'autorité",
        "justification": "Une unité inconnue du débat porte la charge.",
    },
}


def _review_item(unit_id: str) -> dict:
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


def _state() -> UnifiedAnalysisState:
    """A state built the way the run builds it — production class,
    production setters, production shapes."""
    state = UnifiedAnalysisState(DOCUMENT)
    state.identified_arguments = dict(UNITS)
    state.identified_fallacies = {k: dict(v) for k, v in FALLACIES.items()}
    state.argument_quality_scores = {
        "arg_1": {"scores": {"clarte": 4.0, "pertinence": 3.5}, "overall": 3.75},
    }
    state.counter_arguments = [
        {
            "target_arg_id": "arg_1",
            "strategy": "counter-example",
            "counter_content": "Le contre-exemple voisin dit le contraire de la règle.",
            "validation": {"is_valid_attack": True, "counter_succeeds": False},
        },
    ]
    state.record_analysis_coverage(
        phase="fallacy_per_argument",
        k=1,
        n_total=2,
        bands_covered=3,
        bands_total=3,
        unit_ids=["arg_1"],
    )
    state.coverage_review = {
        "status": "ok",
        "items": [_review_item("arg_1"), _review_item("arg_5"), _review_item("")],
        "examined": 3,
        "examined_by_class": {"statistical": 3},
        "document_chars": len(DOCUMENT),
        "dropped": {},
        "reason": "",
        "basis": "coverage_review",
    }
    return state


def _movement_targets(evidence: any) -> list:
    """The dispatch's comparison key: each movement's theme and the target
    ids it carries (units, then each unit's fallacy targets)."""
    rows = []
    for movement in evidence.movements:
        units = []
        for argument in movement.arguments:
            units.append(
                (
                    argument.arg_id,
                    tuple(f.target_arg_id for f in argument.fallacies),
                    argument.fallacy_examined,
                )
            )
        rows.append((movement.theme, tuple(units)))
    return rows


def _replayed_state(state: UnifiedAnalysisState) -> SimpleNamespace:
    """The dump writer's round-trip, then the replay's reconstruction.

    The writer dumps ``get_state_snapshot(summarize=False)`` as JSON text
    (``run_corpus_batch._run_single``); a replay parses that text and reads
    it by attribute — no field-by-field restoration exists in production.
    """
    snapshot = state.get_state_snapshot(summarize=False)
    dump_text = json.dumps(snapshot, ensure_ascii=False, indent=2)
    return SimpleNamespace(**json.loads(dump_text))


class TestMovementsSurviveTheSnapshot:
    def test_totals_and_target_ids_are_identical(self):
        state = _state()
        live = build_act2_evidence(state)
        replay = build_act2_evidence(_replayed_state(state))
        assert len(live.movements) == len(replay.movements)
        assert _movement_targets(live) == _movement_targets(replay)

    def test_fallacy_counts_are_identical(self):
        state = _state()
        live = build_act2_evidence(state)
        replay = build_act2_evidence(_replayed_state(state))
        assert live.args_total == replay.args_total
        assert live.fallacies_total == replay.fallacies_total
        assert live.unattributed_fallacies == replay.unattributed_fallacies
        assert live.fallacy_sample_recorded == replay.fallacy_sample_recorded


class TestTheContractReadingSurvivesTheSnapshot:
    def test_the_structural_numbers_are_identical(self):
        state = _state()
        live_reading = read_render_contract("", build_act2_evidence(state), state)
        replay_state = _replayed_state(state)
        replay_reading = read_render_contract(
            "", build_act2_evidence(replay_state), replay_state
        )
        assert replay_reading.movements_total == live_reading.movements_total
        assert replay_reading.items_total == live_reading.items_total
        assert (
            replay_reading.items_on_unexamined_units
            == live_reading.items_on_unexamined_units
        )


class TestTheWitnessCanSeeAnUnfaithfulReplay:
    """The green above is a measurement only if the comparison can fail.

    A dump that loses its coverage record is exactly the unfaithful replay
    this witness exists to catch: the unexamined unit's theme silently
    shifts from « non examinés » to « échantillon non enregistré ». The
    production round-trip does not lose it — this control pins that the
    witness's silence means fidelity, not blindness.
    """

    def test_a_dump_without_the_coverage_record_diverges(self):
        state = _state()
        live = build_act2_evidence(state)
        snapshot = state.get_state_snapshot(summarize=False)
        del snapshot["analysis_coverage"]
        degraded = SimpleNamespace(
            **json.loads(json.dumps(snapshot, ensure_ascii=False))
        )
        replay = build_act2_evidence(degraded)
        assert _movement_targets(live) != _movement_targets(replay)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
