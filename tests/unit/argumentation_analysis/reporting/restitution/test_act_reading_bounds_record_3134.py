"""#3134 — a bound that reaches the reader is the record's, for its own site.

The R1105b render (Sonnet) closed Act III on the reading bounds with a
sentence that merged three distinct fallacy lines — wide net 8000,
one-shot fallback 8000, descent 500 — into one "initial fallacy
detection" carrying the SMALLEST bound. Haiku (R1104) had the bounds
right; Opus (R1105c) quoted none. A bound that depends on which model
paraphrases the record is not a bound the pipeline guarantees.

The repair is deterministic: the numbers the reader receives come from
the record's own lines (``format_reading_line``), grafted as a closing
passage after the woven prose; the weaving rule forbids restating a
numeric bound in the prose; and any woven sentence that restates one is
removed before the passage is grafted (the #1605 enforcement shape —
the record's sentence replaces the woven one, the event is logged, the
reader gets the passage, never a repair note).

Everything here is offline: real ``UnifiedAnalysisState`` objects, an
async LLM stub returning recorded synthetic prose, no network.
"""

from __future__ import annotations

import asyncio

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_narrative,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_conclusion,
)

_SOURCE_CHARS = 12_000

# The R1105b shape: three fallacy lines fused into one "initial detection"
# carrying the descent's 500 — synthetic words, no corpus text.
_MISBOUND_SENTENCE = (
    "La détection initiale de sophismes a lu 500 des 12000 caractères, "
    "la lecture par argument 10 unités sur 91, et les traductions "
    "logiques 4000 caractères."
)

_WOVEN_MISBOUND = (
    "### Ce que le discours dit vraiment\n\n"
    "Le locuteur défend une lecture ordonnée de ses engagements.\n\n"
    "### Ce qui tient et ce qui ne tient pas\n\n"
    "La position résiste à l'examen croisé des axes.\n\n"
    "### Comment se faire son avis\n\n"
    f"Prudence sur les bornes. {_MISBOUND_SENTENCE} "
    "Le reste du jugement tient sans elles."
)

_WOVEN_CLEAN = (
    "### Ce que le discours dit vraiment\n\n"
    "Le locuteur défend une lecture ordonnée de ses engagements.\n\n"
    "### Ce qui tient et ce qui ne tient pas\n\n"
    "La position résiste à l'examen croisé des axes.\n\n"
    "### Comment se faire son avis\n\n"
    "Les bornes de lecture sont portées par le passage qui suit ce récit."
)


def _stub_llm(text: str):
    async def _call(_prompt: str) -> str:
        return text

    return _call


def _state() -> UnifiedAnalysisState:
    state = UnifiedAnalysisState("x" * _SOURCE_CHARS)
    state.add_argument("Le locuteur disqualifie l'adversaire.")
    state.add_argument("Une revendication défendue par un raisonnement causal.")
    state.reading_window_status = {
        "fact_extraction": {"status": "selected", "offset": 0, "window": 3000},
        "fallacy_widenet": {"status": "selected", "offset": 0, "window": 8000},
        "fallacy_one_shot": {"status": "selected", "offset": 0, "window": 8000},
        "fallacy_descent": {"status": "selected", "offset": 0, "window": 500},
        "fallacy_per_argument": {
            "status": "selected",
            "offset": 0,
            "window": 0,
            "units": 10,
            "unit_total": 91,
            "span_lo": 0,
            "span_hi": 0,
        },
    }
    return state


def _act3(state, woven: str):
    return asyncio.run(build_act3_conclusion(state, llm_callable=_stub_llm(woven)))


def _act2(state, woven: str):
    return asyncio.run(build_act2_narrative(state, llm_callable=_stub_llm(woven)))


class TestActThree:
    def test_a_woven_misbound_sentence_does_not_reach_the_reader(self):
        # On main the fused sentence passes unseen; here it must be gone
        # from the woven prose — the record's passage carries the bounds.
        result = _act3(_state(), _WOVEN_MISBOUND)
        assert "détection initiale de sophismes" not in result.narrative

    def test_the_reader_passage_carries_every_site_under_its_own_label(self):
        result = _act3(_state(), _WOVEN_MISBOUND)
        narrative = result.narrative
        assert "Bornes de lecture du run" in narrative
        # The wide net — the bound the render omitted — says its 8000.
        assert "détection de sophismes — large filet" in narrative
        assert "lecture de 8000 des 12000 caractères" in narrative
        # The descent keeps its own 500, under its own label.
        assert "détection de sophismes — descente" in narrative
        assert "lecture de 500 des 12000 caractères" in narrative
        # The per-argument reading speaks in units, the extraction in chars.
        assert "10 unités sur 91 lues" in narrative
        assert "lecture de 3000 des 12000 caractères" in narrative

    def test_the_passage_follows_the_woven_prose(self):
        result = _act3(_state(), _WOVEN_CLEAN)
        assert result.narrative.startswith(_WOVEN_CLEAN.split("### Comment")[0])
        assert "Bornes de lecture du run" in result.narrative

    def test_clean_prose_loses_no_sentence(self):
        # Positive control: prose that restates no bound is untouched —
        # only the passage is appended.
        result = _act3(_state(), _WOVEN_CLEAN)
        assert "Le locuteur défend une lecture ordonnée" in result.narrative
        assert (
            "Les bornes de lecture sont portées par le passage qui suit ce récit."
            in result.narrative
        )

    def test_a_record_with_no_lines_grafts_no_passage(self):
        state = _state()
        state.reading_window_status = {}
        result = _act3(state, _WOVEN_CLEAN)
        assert "Bornes de lecture du run" not in result.narrative


class TestActTwo:
    def test_a_woven_misbound_sentence_does_not_reach_the_reader(self):
        result = _act2(_state(), _WOVEN_MISBOUND)
        assert "détection initiale de sophismes" not in result.narrative
        assert "lecture de 8000 des 12000 caractères" in result.narrative


class TestRestatedBoundSentences:
    """The deterministic guard behind the removal — unit level."""

    @staticmethod
    def _guard():
        from argumentation_analysis.reporting.restitution.reading_record import (
            restated_bound_sentences,
        )

        return restated_bound_sentences

    def test_the_r1105b_fusion_is_caught(self):
        caught = self._guard()(_WOVEN_MISBOUND)
        assert len(caught) == 1
        assert "détection initiale de sophismes" in caught[0]

    def test_a_document_length_is_not_a_reading_bound(self):
        # "un discours de 12000 caractères" names the document, not a
        # bounded reading — the guard must not touch it.
        caught = self._guard()("Un discours de 12000 caractères, dense et suivi.")
        assert caught == []

    def test_a_result_count_is_not_a_reading_bound(self):
        caught = self._guard()("La détection a retenu 3 sophismes, tous confirmés.")
        assert caught == []

    def test_a_units_bound_is_caught(self):
        caught = self._guard()(
            "La lecture par argument a couvert 10 unités sur 91 du corpus."
        )
        assert len(caught) == 1


class TestReaderBoundsPassage:
    def test_the_passage_is_the_records_own_lines(self):
        from argumentation_analysis.reporting.restitution.reading_record import (
            build_reading_record,
            format_reader_bounds_passage,
        )

        passage = format_reader_bounds_passage(build_reading_record(_state()))
        assert passage.startswith("**Bornes de lecture du run")
        assert "« détection de sophismes — large filet »" in passage
        assert "« détection de sophismes — descente »" in passage
        assert "BASE DU RUN" in passage

    def test_no_lines_no_passage(self):
        from argumentation_analysis.reporting.restitution.reading_record import (
            build_reading_record,
            format_reader_bounds_passage,
        )

        state = _state()
        state.reading_window_status = {}
        assert format_reader_bounds_passage(build_reading_record(state)) == ""
