"""#3479 — the historian's dating is confronted with the dates the document states.

The panel measured (#3465 ask 4, cycle 3b) an analysis dating a speech EARLIER
than an event the document itself cites as already past: the historian persona
(#3377) brings what the model knows, but nothing read that knowledge against
the text's own dated references — the header carried no date, the situation's
precise day reached Acte I unchallenged, and the render inherited an
anachronism the text itself refutes.

What this file pins, synthetic-only (invented texts, invented years — never a
corpus date or name):

- the deterministic extraction: each explicit year with its quote and offset,
  projections ("d'ici 2088") excluded from the confrontation bound but still
  stated dates;
- the stated dates ride the historian's prompt BEFORE it writes a date;
- a situation dating the text earlier than a year it cites as past is degraded
  to an uncertain dating in the state, and Acte I names the quoted document
  reference with its position;
- a consistent dating passes through untouched — the state dict and the Acte I
  block are byte-identical to what #3377 produced;
- a text with no stated date changes nothing: no ``dating`` key anywhere, and
  the prompt stays byte-identical to the #3377 template's formatting.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

from argumentation_analysis.agents.core.context import MODEL_KNOWLEDGE_BASIS
from argumentation_analysis.agents.core.context.historian import (
    HISTORIAN_PROMPT,
    build_historical_context,
    build_historian_prompt,
)
from argumentation_analysis.core.metadata_prompt import NOT_RECORDED_IN_METADATA

#: A synthetic text citing ONE calendar date (month, day, year) as already
#: past — R1149: only a calendar date bounds the writing date. Opaque words,
#: invented date — nothing here comes from the corpus.
_TEXT_WITH_PAST_DATE = (
    "Un rappel ouvre le propos : depuis le congrès du 14 mars 2019, "
    "l'assemblée a changé de méthode, et chaque délégué s'en souvient. "
    + "Une prose neutre continue, sans chiffre ni année d'aucune sorte. " * 40
)
_OFFSET_2019 = _TEXT_WITH_PAST_DATE.index("2019")

#: The same shape of prose, with no stated date at all.
_TEXT_WITHOUT_DATE = (
    "Une prose sans aucun chiffre, seulement des mots et des virgules. " * 40
)

_EARLY_PAYLOAD = {
    "situation": "Ce texte a été rédigé autour de 2004, dans un cycle de réformes.",
    "blind_spot": "",
    "items": [{"claim": "Le cadre est parlementaire.", "confidence": 0.7}],
}
_CONSISTENT_PAYLOAD = {
    "situation": "Rédigé en 2024, au lendemain du congrès.",
    "blind_spot": "",
    "items": [{"claim": "Le cadre est parlementaire.", "confidence": 0.7}],
}


def _state(**fields):
    base = dict(
        raw_text=_TEXT_WITHOUT_DATE,
        source_metadata={"speaker": "Speaker_A", "venue": "assembly"},
        stakes_and_stakeholders={"stakes": [], "stakeholders": []},
    )
    base.update(fields)
    return SimpleNamespace(**base)


def _llm(payload):
    async def _call(prompt: str) -> str:
        return json.dumps(payload)

    return _call


def _capturing_llm(payload, sink):
    async def _call(prompt: str) -> str:
        sink.append(prompt)
        return json.dumps(payload)

    return _call


# ============================================================================
# The deterministic extraction — same text, same list, same offsets
# ============================================================================


class TestTheExtraction:
    """The new symbol is imported INSIDE each test so the file still collects
    on ``main``: the feature tests redden on the missing module while the
    byte-identity controls below stay green there — the born-red measurement
    keeps its control arm."""

    def test_each_stated_year_carries_its_quote_and_offset(self):
        from argumentation_analysis.agents.core.context.stated_dates import (
            extract_stated_dates,
        )

        stated = extract_stated_dates(_TEXT_WITH_PAST_DATE)

        assert [entry.year for entry in stated] == [2019]
        entry = stated[0]
        assert entry.offset == _OFFSET_2019
        assert "congrès du 14 mars 2019" in entry.quote
        assert entry.projected is False
        assert entry.calendar is True

    def test_the_bound_is_the_latest_year_cited_as_past(self):
        from argumentation_analysis.agents.core.context.stated_dates import (
            extract_stated_dates,
            past_cited_bound,
        )

        text = (
            "Le texte évoque l'accord du 3 avril 1904 puis, plus loin, "
            "l'accord du 12 mai 1955."
        )

        bound = past_cited_bound(extract_stated_dates(text))

        assert bound is not None
        assert bound.year == 1955
        assert bound.offset == text.index("1955")

    def test_a_projected_year_never_bounds_the_writing_date(self):
        from argumentation_analysis.agents.core.context.stated_dates import (
            extract_stated_dates,
            past_cited_bound,
        )

        text = (
            "Le plan annonce des objectifs d'ici 2088, mais rappelle aussi "
            "l'accord du 12 mai 1955."
        )

        stated = extract_stated_dates(text)

        assert [entry.year for entry in stated] == [2088, 1955]
        assert [entry.projected for entry in stated] == [True, False]
        assert past_cited_bound(stated).year == 1955

    def test_no_year_means_no_extraction_and_no_bound(self):
        from argumentation_analysis.agents.core.context.stated_dates import (
            extract_stated_dates,
            past_cited_bound,
        )

        assert extract_stated_dates(_TEXT_WITHOUT_DATE) == []
        assert past_cited_bound([]) is None


class TestAFloorIsAYear:
    """R1148 review — the measured false floor: a media timestamp inside a
    URL query parameter fired the degradation on a document whose dating
    nothing refutes. A false refutation is worse than a missed one, so every
    doubtful token falls on the side of NO floor. One witness per class,
    synthetic-only."""

    def test_a_year_inside_a_url_or_identifier_is_not_a_dated_reference(self):
        from argumentation_analysis.agents.core.context.stated_dates import (
            extract_stated_dates,
        )

        text = (
            "L'annexe visuelle est en ligne : "
            "https://example.test/archive?id=2019 pour le détail, "
            "et le code de dossier A?2019&B la référence."
        )

        assert extract_stated_dates(text) == []

    def test_a_decimal_number_is_not_a_dated_reference(self):
        from argumentation_analysis.agents.core.context.stated_dates import (
            extract_stated_dates,
        )

        text = (
            "La séquence dure 2019,5 secondes, et la note vaut 2019.5 " "sur l'échelle."
        )

        assert extract_stated_dates(text) == []

    def test_a_digit_grouped_quantity_is_not_a_dated_reference(self):
        from argumentation_analysis.agents.core.context.stated_dates import (
            extract_stated_dates,
        )

        text = "L'assemblée réunit 12 2019 délégués et 1,2019 million d'auditeurs."

        assert extract_stated_dates(text) == []

    def test_an_english_future_year_is_projected_even_without_french_markers(self):
        from argumentation_analysis.agents.core.context.stated_dates import (
            extract_stated_dates,
            past_cited_bound,
        )

        text = (
            "The roadmap binds nobody yet: the target will be met by 2088, "
            "and payments continue until 2090. Nothing else carries a year."
        )

        stated = extract_stated_dates(text)

        assert [entry.year for entry in stated] == [2088, 2090]
        assert all(entry.projected for entry in stated)
        assert past_cited_bound(stated) is None

    def test_a_real_year_beside_the_excluded_classes_still_bounds(self):
        """The filters remove the junk, never the dated reference beside it."""
        from argumentation_analysis.agents.core.context.stated_dates import (
            extract_stated_dates,
            past_cited_bound,
        )

        text = (
            "La séquence dure 2019,5 secondes ; le rappel ouvre pourtant sur "
            "le congrès du 14 mars 1955, cité comme déjà passé."
        )

        bound = past_cited_bound(extract_stated_dates(text))

        assert bound is not None
        assert bound.year == 1955


class TestAFloorIsACalendarDate:
    """R1149 review — the replay of the real check on the 20 recorded panel
    states measured the head firing on 4: only ONE was the true case, a
    citation dated to the day. The other three floors came from years a bare
    mention supplies — an unmarked legal clause ("may be amended after
    YYYY"), an announced event ("the YYYY <event>"). A year is a floor only
    when it sits in a CALENDAR DATE: a month name, French or English, within
    a short window before it (the corpus is not French-only). The error
    stays on the safe side: a doubtful year loses its floor and never gains
    one. One witness per class, synthetic-only."""

    def test_an_unmarked_legal_clause_is_not_a_dated_reference(self):
        from argumentation_analysis.agents.core.context.stated_dates import (
            extract_stated_dates,
            past_cited_bound,
        )

        text = (
            "The terms may be amended after 2025, and the parties accept "
            "this in advance. No month name carries the year."
        )

        assert past_cited_bound(extract_stated_dates(text)) is None

    def test_an_announced_event_is_not_a_dated_reference(self):
        from argumentation_analysis.agents.core.context.stated_dates import (
            extract_stated_dates,
            past_cited_bound,
        )

        text = (
            "The 2030 summit will gather the delegates, and nothing else "
            "carries a year."
        )

        assert past_cited_bound(extract_stated_dates(text)) is None

    def test_a_french_calendar_date_bounds_the_writing_date(self):
        from argumentation_analysis.agents.core.context.stated_dates import (
            extract_stated_dates,
            past_cited_bound,
        )

        text = "Le rappel ouvre sur le congrès du 14 mars 2019, déjà passé."

        bound = past_cited_bound(extract_stated_dates(text))

        assert bound is not None
        assert bound.year == 2019

    async def test_a_body_speech_dated_to_the_day_fires(self):
        """R1149's own witness shape: "speech of <month> <day>, YYYY" against
        a situation one year earlier — the measured true case."""
        text = (
            "The speaker answers the speech of January 15, 2019, and quotes "
            "it at length before disagreeing. "
            + "A neutral sentence follows, without any digit. " * 30
        )
        payload = {
            "situation": "Written in early 2018, before the answer.",
            "items": [],
        }

        result = await build_historical_context(_state(raw_text=text), _llm(payload))

        dating = result.to_state()["dating"]
        assert dating["refuted_by"]["year"] == 2019
        assert dating["model_year"] == 2018

    async def test_the_same_speech_with_a_situation_in_that_year_does_not_fire(
        self,
    ):
        text = (
            "The speaker answers the speech of January 15, 2019, and quotes "
            "it at length before disagreeing. "
            + "A neutral sentence follows, without any digit. " * 30
        )
        payload = {
            "situation": "Written in 2019, weeks after the speech.",
            "items": [],
        }

        result = await build_historical_context(_state(raw_text=text), _llm(payload))

        assert "dating" not in result.to_state()


# ============================================================================
# Item 1 — the document's own dates ride the prompt before the historian answers
# ============================================================================


class TestThePromptCarriesTheDocumentDates:
    async def test_the_stated_dates_ride_the_prompt(self):
        sink = []

        await build_historical_context(
            _state(raw_text=_TEXT_WITH_PAST_DATE),
            _capturing_llm(_EARLY_PAYLOAD, sink),
        )

        (prompt,) = sink
        assert "Dated references the document itself states" in prompt
        assert "congrès du 14 mars 2019" in prompt
        assert f"(offset {_OFFSET_2019})" in prompt
        assert (
            "a dating you assign it earlier than one of\nthem is impossible" in prompt
        )


# ============================================================================
# Item 2 — an impossible dating is degraded in the state, and named
# ============================================================================


class TestAnImpossibleDatingIsDegradedAndNamed:
    async def test_the_state_degrades_the_dating_and_names_the_reference(self):
        result = await build_historical_context(
            _state(raw_text=_TEXT_WITH_PAST_DATE), _llm(_EARLY_PAYLOAD)
        )

        dating = result.to_state()["dating"]
        assert dating["status"] == "uncertain"
        assert dating["model_year"] == 2004
        assert dating["refuted_by"]["year"] == 2019
        assert dating["refuted_by"]["offset"] == _OFFSET_2019
        assert "congrès du 14 mars 2019" in dating["refuted_by"]["quote"]

    async def test_a_range_situation_is_confronted_on_its_latest_year(self):
        """R1148: ``min`` fired as soon as the situation MENTIONED an earlier
        context event; ``max`` fires only when the whole situation predates
        the floor. The range 1904-2004 still predates 2019 — at its latest."""
        payload = {"situation": "Le texte couvre la période 1904-2004.", "items": []}

        result = await build_historical_context(
            _state(raw_text=_TEXT_WITH_PAST_DATE), _llm(payload)
        )

        assert result.to_state()["dating"]["model_year"] == 2004

    async def test_a_situation_naming_an_earlier_context_year_is_not_refuted(self):
        """R1148's measured shape: "ten years after the crisis of YYYY" — the
        situation's DATING is right; its earliest year is context, not the
        document's date. The confrontation must not fire."""
        payload = {
            "situation": "Rédigé en 2024, dix ans après la crise de 1914.",
            "items": [],
        }

        result = await build_historical_context(
            _state(raw_text=_TEXT_WITH_PAST_DATE), _llm(payload)
        )

        assert "dating" not in result.to_state()

    async def test_act1_names_the_quoted_reference_with_its_position(self):
        from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
            Act1Evidence,
            build_act1_prompt,
        )

        result = await build_historical_context(
            _state(raw_text=_TEXT_WITH_PAST_DATE), _llm(_EARLY_PAYLOAD)
        )
        evidence = Act1Evidence(historical_context=result.to_state())
        prompt = build_act1_prompt(evidence)

        assert "Datation DÉGRADÉE" in prompt
        assert "congrès du 14 mars 2019" in prompt
        assert f"position {_OFFSET_2019}" in prompt
        # R1148 wording nit: the check proves "at or after", never strictly
        # after — « au plus tôt de » says that, « postérieur à » does not.
        assert "au plus tôt de 2019" in prompt
        assert "postérieur à" not in prompt
        # Anti-pendulum: the refuted situation is still rendered — model
        # knowledge, reframed as uncertain, never silenced.
        assert "rédigé autour de 2004" in prompt

    async def test_a_situation_without_a_year_is_not_confronted(self):
        payload = {"situation": "Une transition institutionnelle.", "items": []}

        result = await build_historical_context(
            _state(raw_text=_TEXT_WITH_PAST_DATE), _llm(payload)
        )

        assert "dating" not in result.to_state()

    def test_the_pipeline_writer_persists_the_degradation(self):
        from argumentation_analysis.orchestration.state_writers import (
            _write_historical_context_to_state,
        )

        state = SimpleNamespace(historical_context={})
        _write_historical_context_to_state(
            {
                "situation": "Rédigé autour de 2004.",
                "items": [],
                "status": "ok",
                "dating": {
                    "status": "uncertain",
                    "model_year": 2004,
                    "refuted_by": {
                        "year": 2019,
                        "quote": "depuis le congrès du 14 mars 2019",
                        "offset": _OFFSET_2019,
                    },
                },
            },
            state,
            {},
        )

        dating = state.historical_context["dating"]
        assert dating["status"] == "uncertain"
        assert dating["refuted_by"]["year"] == 2019


# ============================================================================
# Witness 2 — a consistent dating passes through byte-identical
# ============================================================================


class TestAConsistentDatingPassesThroughByteIdentical:
    async def test_the_state_dict_is_unchanged(self):
        result = await build_historical_context(
            _state(raw_text=_TEXT_WITH_PAST_DATE), _llm(_CONSISTENT_PAYLOAD)
        )

        assert result.to_state() == {
            "situation": "Rédigé en 2024, au lendemain du congrès.",
            "blind_spot": "",
            "items": [
                {
                    "claim": "Le cadre est parlementaire.",
                    "confidence": 0.7,
                    "supports": "",
                    "basis": MODEL_KNOWLEDGE_BASIS,
                }
            ],
            "status": "ok",
            "basis": MODEL_KNOWLEDGE_BASIS,
        }

    async def test_the_act1_block_is_unchanged(self):
        from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
            _format_historical_block,
        )

        result = await build_historical_context(
            _state(raw_text=_TEXT_WITH_PAST_DATE), _llm(_CONSISTENT_PAYLOAD)
        )

        assert _format_historical_block(result.to_state()) == (
            "  Situation : Rédigé en 2024, au lendemain du congrès.\n"
            "  - Le cadre est parlementaire. (confiance 0.70)"
        )


# ============================================================================
# Witness 3 — a text with no stated date changes nothing
# ============================================================================


class TestATextWithoutStatedDateChangesNothing:
    async def test_a_dated_situation_on_a_dateless_text_writes_no_dating_key(self):
        payload = {"situation": "Un texte des années 1930.", "items": []}
        sink = []

        result = await build_historical_context(
            _state(raw_text=_TEXT_WITHOUT_DATE),
            _capturing_llm(payload, sink),
        )

        assert result.to_state() == {
            "situation": "Un texte des années 1930.",
            "blind_spot": "",
            "items": [],
            "status": "ok",
            "basis": MODEL_KNOWLEDGE_BASIS,
        }
        assert "Dated references" not in sink[0]

    def test_the_prompt_stays_byte_identical_to_the_3377_template(self):
        prompt = build_historian_prompt(_state(), "EXTRAIT FIXE")

        # ``dates_section=""`` is a no-op on BOTH sides of the change: the
        # #3377 template ignores the unused kwarg, the #3479 template renders
        # the empty section as nothing — the formatted prompt is the same
        # bytes either way. #3512 renders the three unrecorded fields
        # through the metadata helper, so the expected bytes carry the
        # not-recorded instruction where the template once showed
        # ``unknown``.
        assert prompt == HISTORIAN_PROMPT.format(
            speaker="Speaker_A",
            venue="assembly",
            topic=NOT_RECORDED_IN_METADATA,
            era=NOT_RECORDED_IN_METADATA,
            language=NOT_RECORDED_IN_METADATA,
            stakes_block="  (aucun enjeu extrait)",
            dates_section="",
            excerpt="EXTRAIT FIXE",
        )
