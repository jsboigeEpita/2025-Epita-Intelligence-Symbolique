"""#2850 lot 8 — the reader-facing surfaces of the stratified extraction read.

The mechanics live in ``orchestration`` (the k windows, the union payload);
these witnesses pin what the READER receives: the reading record's line says
the union and the window count (« 9000 des 56430 caractères en 3 fenêtres »),
and Act I's coverage sentence carries the extraction's own bound as a clause
pre-built from the record — one producer, one sentence, never a figure the
writer could restate (the woven restatement is withdrawn by the act's union
detector, pinned here too).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
    act1_restated_sentences,
    coverage_range_sentence,
    extraction_reading_clause,
    _number_free_act1,
)
from argumentation_analysis.reporting.restitution.reading_record import (
    ReadingLine,
    build_reading_record,
    format_reading_line,
)


def _state(**entry: Any) -> SimpleNamespace:
    return SimpleNamespace(
        raw_text="x" * 56430,
        reading_window_status={
            "fact_extraction": {
                "status": "selected",
                "offset": 0,
                "window": 3000,
                **entry,
            }
        },
    )


class TestReadingRecordLine:
    def test_the_line_names_the_union_and_the_window_count(self) -> None:
        line = ReadingLine(
            site="fact_extraction",
            status="selected",
            window=3000,
            windows=3,
            chars_read=9000,
        )
        rendered = format_reading_line(line, 56430)
        assert rendered.startswith(
            "« extraction des unités » : lecture de 9000 des 56430 "
            "caractères en 3 fenêtres"
        ), rendered

    def test_a_tiled_whole_read_says_whole_honestly(self) -> None:
        """Never « tout le texte » unless true — and when the union DID cover
        the document, the line says whole, with its window count."""
        line = ReadingLine(
            site="fact_extraction",
            status="selected",
            window=3000,
            windows=3,
            chars_read=9000,
        )
        rendered = format_reading_line(line, 9000)
        assert "document lu en entier" in rendered, rendered
        assert "en 3 fenêtres" in rendered, rendered

    def test_one_window_keeps_the_lot6_form(self) -> None:
        line = ReadingLine(site="fact_extraction", status="selected", window=3000)
        rendered = format_reading_line(line, 56430)
        assert rendered.startswith(
            "« extraction des unités » : lecture de 3000 des 56430 caractères"
        ), rendered

    def test_build_reads_the_extras_from_the_state(self) -> None:
        record = build_reading_record(_state(windows=3, chars_read=9000))
        line = next(ln for ln in record.lines if ln.site == "fact_extraction")
        assert line.windows == 3
        assert line.chars_read == 9000


class TestAct1CoverageClause:
    def test_clause_built_from_the_record(self) -> None:
        clause = extraction_reading_clause(_state(windows=3, chars_read=9000))
        assert clause == (
            " L'extraction LLM a lu 9000 des 56430 caractères (3 fenêtres)."
        )

    def test_clause_rides_the_coverage_sentence(self) -> None:
        sentence = coverage_range_sentence(
            {"quality": {"k": 5}},
            0,
            extraction_reading_clause(_state(windows=3, chars_read=9000)),
        )
        assert sentence.endswith(
            "L'extraction LLM a lu 9000 des 56430 caractères (3 fenêtres)."
        ), sentence

    def test_no_clause_when_one_window(self) -> None:
        assert extraction_reading_clause(_state(windows=1)) == ""

    def test_no_clause_when_the_union_covered_the_document(self) -> None:
        assert extraction_reading_clause(_state(windows=3, chars_read=56430)) == ""

    def test_no_clause_without_a_record_entry(self) -> None:
        assert extraction_reading_clause(SimpleNamespace(raw_text="x")) == ""


class TestAct1RestatementWithdrawal:
    """The clause grafts a NEW numeric figure into Act I — a woven copy of it
    must be withdrawn, exactly as a coverage-range copy already is."""

    def test_a_woven_extraction_bound_is_caught(self) -> None:
        prose = (
            "Le cadrage pose le texte. L'extraction LLM a lu 9000 des 56430 "
            "caractères pour fonder ce premier acte. La suite du rapport "
            "s'appuie sur ces unités."
        )
        caught = act1_restated_sentences(prose)
        assert any("9000 des 56430" in s for s in caught), caught

    def test_the_bound_is_withdrawn_not_the_sentence_when_anaphora_follows(
        self,
    ) -> None:
        sentence = "L'extraction LLM a lu 9000 des 56430 caractères pour fonder l'acte."
        rewritten = _number_free_act1(sentence)
        assert rewritten is not None
        assert "9000" not in rewritten
        assert "une partie du texte" in rewritten
