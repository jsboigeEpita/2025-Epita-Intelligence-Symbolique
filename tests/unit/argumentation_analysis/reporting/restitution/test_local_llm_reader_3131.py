# -*- coding: utf-8 -*-
"""#3131 — the local tier's ledger record finally has a reader.

``state.local_llm_results`` has been written since #834, enriched since
#3113/#3124 (status, input mode, unit counts, served model), and read by
nothing: the R1238 triage measured the write-only census and decided
wire-not-retire — one deterministic line in the coverage record (the run's
reading bounds) for the presence side, one absence-ledger entry for the
skip/error side. These witnesses hold both channels to the record, and the
executor-failure father to the label map.

The record shapes below are the writer's own field vocabulary, verbatim
from ``invoke_callables._invoke_local_llm`` — never an invented key.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from argumentation_analysis.reporting.restitution.reading_record import (
    SITE_LABELS_FR,
    build_reading_record,
    format_reader_bounds_passage,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    _ABSENT_DIMENSION_LABELS,
    _collect_absent_dimensions,
)

DOC = "séquence." * 2000  # 18 000 chars — a real-length raw_text


def _state(records=None, raw_text=DOC):
    return SimpleNamespace(
        raw_text=raw_text,
        reading_window_status={},
        argument_provenance=None,
        local_llm_results=records if records is not None else [],
    )


_COMPLETED_UNITS = {
    "status": "completed",
    "response": "analyse locale…",
    "model": "alias-democratech",
    "served_model": "qwen3.6-35b",
    "finish_reason": "end_turn",
    "timeout_s": 120.0,
    "input_length": 1500,
    "input_mode": "selected_units",
    "input_units": 10,
    "input_units_total": 83,
}

_COMPLETED_WINDOW = {
    "status": "completed",
    "response": "analyse locale…",
    "model": "alias-democratech",
    "served_model": "qwen3.6-35b",
    "finish_reason": "end_turn",
    "timeout_s": 120.0,
    "input_length": 2000,
    "input_mode": "document_window",
    "input_truncated": True,
    "input_chars_total": 18_000,
}


class TestReadingLine:
    """The coverage-record side: the tier's one line in the bounds passage."""

    def test_completed_units_reading_reaches_the_bounds_passage(self):
        record = build_reading_record(_state([_COMPLETED_UNITS]))
        passage = format_reader_bounds_passage(record)
        assert SITE_LABELS_FR["local_llm"] in passage
        assert "10 unités sur 83" in passage
        # #3124's one extra fact: who actually answered (the hub serves an
        # alias with another model by design) — never what it answered.
        assert "modèle servi : qwen3.6-35b" in passage
        assert "alias-democratech" not in passage

    def test_completed_window_reading_states_the_bounded_head(self):
        record = build_reading_record(_state([_COMPLETED_WINDOW]))
        passage = format_reader_bounds_passage(record)
        assert SITE_LABELS_FR["local_llm"] in passage
        assert "lecture de 2000 des 18000 caractères" in passage

    def test_skip_not_configured_speaks_french_not_a_raw_token(self):
        record = build_reading_record(
            _state([{"status": "skipped: not_configured", "model": None}])
        )
        passage = format_reader_bounds_passage(record)
        assert "non évalué — aucun endpoint local configuré" in passage
        assert "not_configured" not in passage

    def test_skip_endpoint_unavailable_speaks_french(self):
        record = build_reading_record(
            _state([{"status": "skipped: endpoint_unavailable", "model": "x"}])
        )
        passage = format_reader_bounds_passage(record)
        assert "non évalué — endpoint local injoignable" in passage
        assert "endpoint_unavailable" not in passage

    def test_error_speaks_status_never_unit_counts(self):
        # Units were sent and nothing came back: a line claiming a reading
        # would overstate what the run holds.
        record = build_reading_record(
            _state(
                [
                    {
                        "status": "error",
                        "error": "ReadTimeout after 120s",
                        "model": "alias-democratech",
                        "timeout_s": 120.0,
                        "input_length": 1500,
                        "input_mode": "selected_units",
                        "input_units": 10,
                        "input_units_total": 83,
                    }
                ]
            )
        )
        passage = format_reader_bounds_passage(record)
        assert "non évalué — erreur d'appel" in passage
        assert "10 unités sur 83" not in passage

    def test_no_record_no_line_and_empty_list_no_line(self):
        for state in (_state(None), _state([])):
            record = build_reading_record(state)
            assert all(ln.site != "local_llm" for ln in record.lines)
            assert "palier local" not in format_reader_bounds_passage(record)


class TestAbsenceLedger:
    """The absence side: the skip/error files a lost dimension in Act III."""

    def test_skip_files_the_local_tier_as_a_lost_dimension(self):
        dims = _collect_absent_dimensions(
            _state([{"status": "skipped: not_configured", "model": None}])
        )
        tier = [d for d in dims if d.capability == "local_llm"]
        assert len(tier) == 1
        assert tier[0].label == _ABSENT_DIMENSION_LABELS["local_llm"]
        assert tier[0].status == "skipped: not_configured"
        assert "aucun endpoint local configuré" in tier[0].reason

    def test_unavailable_skip_files_with_its_own_reason(self):
        dims = _collect_absent_dimensions(
            _state([{"status": "skipped: endpoint_unavailable", "model": "x"}])
        )
        tier = [d for d in dims if d.capability == "local_llm"]
        assert len(tier) == 1
        assert "injoignable" in tier[0].reason

    def test_error_carries_the_producer_message_capped(self):
        dims = _collect_absent_dimensions(
            _state(
                [
                    {
                        "status": "error",
                        "error": "boom " * 200,
                        "model": "x",
                    }
                ]
            )
        )
        tier = [d for d in dims if d.capability == "local_llm"]
        assert len(tier) == 1
        assert tier[0].reason.startswith("boom")
        # _ABSENCE_REASON_CAP through the family's _truncate: cap chars
        # plus the " […]" marker, never more.
        assert len(tier[0].reason) <= 300 + len(" […]")
        assert tier[0].reason.endswith("[…]")

    def test_completed_or_empty_files_no_absence(self):
        for records in ([_COMPLETED_UNITS], [], None):
            dims = _collect_absent_dimensions(_state(records))
            assert not [d for d in dims if d.capability == "local_llm"]

    def test_the_label_map_carries_the_tier(self):
        # The map's keys are the ledger's membership table (#3087): this
        # entry is what makes the executor-failure father cover the phase.
        assert "local_llm" in _ABSENT_DIMENSION_LABELS


class TestExecutorFailureFather:
    """A phase-level death files through the label map, no second list."""

    @pytest.fixture()
    def real_state(self):
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        state = UnifiedAnalysisState(initial_text="texte initial du document.")
        state.raw_text = DOC
        return state

    def test_phase_failure_reaches_the_ledger_and_the_collector(self, real_state):
        from argumentation_analysis.orchestration.state_writers import (
            _record_phase_failed_status,
        )

        _record_phase_failed_status(real_state, "local_llm", "timeout after 180s")
        entry = real_state.structured_arg_status.get("local_llm")
        assert entry is not None and entry.get("degraded") is True
        dims = _collect_absent_dimensions(real_state)
        tier = [d for d in dims if d.capability == "local_llm"]
        assert len(tier) == 1
        assert "palier local" in tier[0].label
        assert "timeout after 180s" in tier[0].reason

    def test_phase_failure_merges_with_structured_losses(self, real_state):
        # The tier's absence joins the structured axes' in one sorted list —
        # the scope paragraph and the degraded entry name both, not one
        # absorbing the other.
        real_state.add_structured_arg_status(
            "aba_reasoning", "translator_failed", True, "translator raised", 0
        )
        from argumentation_analysis.orchestration.state_writers import (
            _record_phase_failed_status,
        )

        _record_phase_failed_status(real_state, "local_llm", "timeout after 180s")
        dims = _collect_absent_dimensions(real_state)
        capabilities = [d.capability for d in dims]
        assert "local_llm" in capabilities and "aba_reasoning" in capabilities
        labels = [d.label for d in dims]
        assert labels == sorted(labels)
