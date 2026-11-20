"""Witness for #3536: the AF frame's 40 nodes span the text's position bands.

The population builder cut the merged population at 40 in INSERTION order,
so a long document's frame held the text's head only — on the witness input
(120 units at even offsets over 60,000 characters) every node sat in the
first third. The fix routes the over-budget cut through the selector's
stratified position strategy; at or under the budget the frame is
byte-identical to the insertion-order frame (ask 2 — no reordering pass
touches a population the cap does not cut, and the control below plants
insertion order away from text order to catch one). The state records k of
N with the bands covered under ONE site name for the family (ask 3).

Free: no key, no network, no corpus — synthetic sentences only, offsets
planted by hand.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import argumentation_analysis.orchestration.invoke_callables as ic

RAW_LEN = 60_000
BAND_WIDTH = RAW_LEN // 3
N_OVER = 120
N_WITHIN = 30
SITE_NAME = "af_family_frame"


def _make_state(n_units: int, *, shuffle_offsets: bool = False) -> SimpleNamespace:
    """Synthetic state: ``arg_1…arg_n`` short sentences, planted offsets.

    ``shuffle_offsets`` plants insertion order AWAY from text order, so a
    control that must stay in insertion order cannot pass by accident.
    """
    identified = {f"arg_{i}": f"unit sentence {i}" for i in range(1, n_units + 1)}
    offsets: dict[str, int] = {}
    for i in range(1, n_units + 1):
        if shuffle_offsets:
            # arg_1 sits in the LAST third, arg_n in the first: text order is
            # the reverse of insertion order.
            offsets[f"arg_{i}"] = (n_units - i) * (RAW_LEN // n_units)
        else:
            offsets[f"arg_{i}"] = (i - 1) * 500
    provenance = {
        arg_id: {"offset": off, "producer": "witness"}
        for arg_id, off in offsets.items()
    }
    coverage_calls: list[dict] = []
    state = SimpleNamespace(
        raw_text="x" * RAW_LEN,
        identified_arguments=identified,
        argument_provenance=provenance,
    )

    def _record(phase, k, n_total, bands_covered, bands_total, **kwargs):
        coverage_calls.append(
            {
                "phase": phase,
                "k": k,
                "N": n_total,
                "bands_covered": bands_covered,
                "bands_total": bands_total,
                **kwargs,
            }
        )

    state.record_analysis_coverage = _record  # type: ignore[attr-defined]
    state.coverage_calls = coverage_calls  # type: ignore[attr-defined]
    return state


def _frame(state: SimpleNamespace):
    return ic._af_family_frame("", {"_state_object": state})


def _band_of(state: SimpleNamespace, unit_id: str) -> int:
    return state.argument_provenance[unit_id]["offset"] // BAND_WIDTH


class TestOverBudgetSpansTheBands:
    def test_forty_nodes_with_one_in_each_third(self):
        state = _make_state(N_OVER)
        node_ids, _labels, _by_label, payload = _frame(state)
        assert len(node_ids) == 40
        bands = {_band_of(state, unit_id) for unit_id in node_ids}
        assert bands == {0, 1, 2}

    def test_population_total_still_names_the_pre_cap_size(self):
        state = _make_state(N_OVER)
        _node_ids, _labels, _by_label, payload = _frame(state)
        assert payload["population_total"] == N_OVER

    def test_the_state_records_k_of_n_with_the_bands(self):
        state = _make_state(N_OVER)
        node_ids, _labels, _by_label, _payload = _frame(state)
        assert state.coverage_calls, "the family must record its coverage (ask 3)"
        call = state.coverage_calls[-1]
        assert call["phase"] == SITE_NAME
        assert call["k"] == 40
        assert call["N"] == N_OVER
        assert call["bands_covered"] == 3
        assert call["bands_total"] == 3
        assert call["unit_ids"] == list(node_ids)


class TestAtOrUnderBudgetIsByteIdentical:
    def test_thirty_units_keep_insertion_order_against_text_order(self):
        state = _make_state(N_WITHIN, shuffle_offsets=True)
        node_ids, labels, node_by_label, payload = _frame(state)
        assert node_ids == [f"arg_{i}" for i in range(1, N_WITHIN + 1)]
        assert labels == [f"unit sentence {i}" for i in range(1, N_WITHIN + 1)]
        assert node_by_label == {
            f"unit sentence {i}": f"arg_{i}" for i in range(1, N_WITHIN + 1)
        }
        assert payload == {
            "argument_labels": {
                f"arg_{i}": f"unit sentence {i}" for i in range(1, N_WITHIN + 1)
            },
            "population_total": N_WITHIN,
        }

    def test_the_state_records_the_whole_population_too(self):
        state = _make_state(N_WITHIN, shuffle_offsets=True)
        node_ids, _labels, _by_label, _payload = _frame(state)
        call = state.coverage_calls[-1]
        assert call["phase"] == SITE_NAME
        assert call["k"] == N_WITHIN
        assert call["N"] == N_WITHIN
        assert call["unit_ids"] == list(node_ids)


class TestExactlyAtBudget:
    def test_forty_units_of_forty_stay_in_insertion_order(self):
        state = _make_state(40, shuffle_offsets=True)
        node_ids, _labels, _by_label, _payload = _frame(state)
        assert node_ids == [f"arg_{i}" for i in range(1, 41)]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
