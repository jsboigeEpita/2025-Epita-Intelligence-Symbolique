"""#3105 — each fallacy site credits only what its own path produced.

The R1102 tunnel pass measured the defect on doc_A: `_site_fed` credited the
whole `identified_fallacies` population to the 500-char descent head — 16 of
16 retained fallacies came from the per-argument enrichment, whose reading
was never recorded, and 11 of the 16 sat beyond char 8 000, so neither the
head nor the wide net could have produced them.

The fix is provenance, not prose: the merge tags each retained fallacy with
the path(s) that produced it, the state carries the tag, the per-argument
reading becomes its own site (units read + span), and `_site_fed` counts per
site. A fallacy found by both paths carries both tags; an untagged (legacy)
fallacy is never credited to the descent.

Counts and opaque ids only; synthetic states.
"""

from types import SimpleNamespace

import pytest

from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_evidence,
    build_act2_prompt,
)
from argumentation_analysis.reporting.restitution.reading_record import (
    _site_fed,
    build_reading_record,
    format_reading_block,
)

_DESCENT = "fallacy_descent"
_PER_ARG = "fallacy_per_argument"
_ONE_SHOT = "fallacy_one_shot"


def _state(fallacies, window_status=None):
    state = SimpleNamespace()
    state.raw_text = "x" * 56_430
    state.source_metadata = {}
    state.stakes_and_stakeholders = {
        "stakes": [],
        "stakeholders": [],
        "rhetorical_register": "",
        "discursive_arena": "",
    }
    state.deanonymized = True
    state.identified_fallacies = fallacies
    state.propositional_analysis_results = []
    state.fol_analysis_results = []
    state.counter_arguments = []
    state.governance_decisions = []
    state.argument_provenance = {
        f"arg_{i}": {"producer": "llm_extract", "offset": i * 500} for i in range(10)
    }
    state.reading_window_status = window_status or {}
    return state


def _fallacy(paths):
    entry = {"type": "Appel à l'autorité", "justification": "…"}
    if paths is not None:
        entry["detection_paths"] = list(paths)
    return entry


class TestPerSiteCounts:
    def test_each_site_counts_only_its_own_path(self):
        """The R1102 shape: most fallacies come from the per-argument pass.
        The descent line must not repeat the total the issue is about."""
        state = _state(
            {
                "fallacy_1": _fallacy([_DESCENT]),
                "fallacy_2": _fallacy([_DESCENT]),
                "fallacy_3": _fallacy([_ONE_SHOT]),
                "fallacy_4": _fallacy([_PER_ARG]),
                "fallacy_5": _fallacy([_PER_ARG]),
                "fallacy_6": _fallacy([_PER_ARG]),
                "fallacy_7": _fallacy([_DESCENT, _PER_ARG]),
            }
        )
        descent = _site_fed(_DESCENT, state)
        per_arg = _site_fed(_PER_ARG, state)
        one_shot = _site_fed(_ONE_SHOT, state)
        assert "(3 retenus)" in descent, (
            "the descent owns its 3 confirmed fallacies — not the 7 the state "
            "holds: crediting the total to the head is the #3105 defect"
        )
        assert (
            "(4 retenus)" in per_arg
        ), "the per-argument path owns its 3 + the 1 found by both"
        assert "(1 retenu)" in one_shot
        # The overlap is stated, never silently doubled under both sites.
        assert "partagé" in descent or "partagé" in per_arg, (
            "a fallacy found by both paths must be said as shared on at "
            "least one of the two lines"
        )

    def test_untagged_fallacies_are_not_credited_to_the_descent(self):
        """Legacy states (R1101 dump) carry no tags: the descent line says
        how many are unattributed rather than absorbing them silently."""
        state = _state(
            {
                "fallacy_1": _fallacy(None),
                "fallacy_2": _fallacy(None),
                "fallacy_3": _fallacy([_DESCENT]),
            }
        )
        descent = _site_fed(_DESCENT, state)
        assert "(1 retenu" in descent
        assert "sans origine enregistrée" in descent and "2" in descent, (
            "the 2 untagged entries must be named as unattributed — silence "
            "would credit them to the descent again"
        )


class TestPerArgumentReadingIsItsOwnSite:
    def test_the_units_site_names_units_and_span(self):
        state = _state(
            {"fallacy_1": _fallacy([_PER_ARG])},
            window_status={
                _PER_ARG: {
                    "status": "selected",
                    "offset": 1776,
                    "window": 2124,
                    "units": 5,
                    "unit_total": 10,
                    "span_lo": 1776,
                    "span_hi": 3900,
                },
                _DESCENT: {"status": "selected", "offset": 0, "window": 500},
            },
        )
        block = format_reading_block(build_reading_record(state))
        assert "5 unités sur 10" in block, (
            "the per-argument reading says how many units it read, out of "
            "how many exist — '10 units out of 88' in the issue's words"
        )
        assert (
            "0.03" in block and "0.07" in block
        ), "the span it covers must be stated as offsets of the text"
        assert "lecture par argument" in block, "the site has a reader label"

    def test_the_head_only_state_keeps_the_descent_line(self):
        """Anti-pendulum: the 500-char descent line survives — the descent
        does read its head; only its credited count changes."""
        state = _state(
            {"fallacy_1": _fallacy([_DESCENT])},
            window_status={
                _DESCENT: {"status": "selected", "offset": 0, "window": 500}
            },
        )
        block = format_reading_block(build_reading_record(state))
        assert "500 des 56430 caractères" in block
        assert "(1 retenu)" in block


class TestTheMergeKeepsBothTags:
    def test_a_fallacy_found_by_both_paths_carries_both_tags(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _merge_fallacy_results,
        )

        wide = [
            {"taxonomy_pk": "pk_a", "type": "A", "confidence": 0.9},
            {"taxonomy_pk": "pk_b", "type": "B", "confidence": 0.8},
        ]
        per_arg = [
            {"taxonomy_pk": "pk_a", "type": "A", "confidence": 0.7},
            {"taxonomy_pk": "pk_c", "type": "C", "confidence": 0.6},
        ]
        merged = _merge_fallacy_results(wide, per_arg, document_site=_DESCENT)
        by_pk = {f["taxonomy_pk"]: f for f in merged}
        assert by_pk["pk_a"]["detection_paths"] == [_DESCENT, _PER_ARG], (
            "a fallacy both paths found carries both tags — the overlap is "
            "what lets each site state its own share"
        )
        assert by_pk["pk_b"]["detection_paths"] == [_DESCENT]
        assert by_pk["pk_c"]["detection_paths"] == [_PER_ARG]

    def test_the_one_shot_path_tags_as_one_shot(self):
        """The document path's result says its method: a one-shot result is
        tagged one-shot, everything else as the descent."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _merge_fallacy_results,
        )

        merged = _merge_fallacy_results(
            [{"taxonomy_pk": "pk_x", "type": "X"}], [], document_site=_ONE_SHOT
        )
        assert merged[0]["detection_paths"] == [_ONE_SHOT]


class TestTheStateCarriesTheTag:
    def test_the_writer_forwards_the_paths_to_the_state(self):
        from argumentation_analysis.core.shared_state import (
            UnifiedAnalysisState,
        )
        from argumentation_analysis.orchestration.state_writers import (
            _write_hierarchical_fallacy_to_state,
        )

        state = UnifiedAnalysisState("x" * 1000)
        _write_hierarchical_fallacy_to_state(
            {
                "fallacies": [
                    {
                        "type": "Appel à l'autorité",
                        "taxonomy_pk": "pk_a",
                        "detection_paths": [_DESCENT, _PER_ARG],
                    }
                ]
            },
            state,
            {},
        )
        entry = next(iter(state.identified_fallacies.values()))
        assert entry["detection_paths"] == [_DESCENT, _PER_ARG], (
            "a tag that stops at the merge never reaches the record — the "
            "record reads the state"
        )
