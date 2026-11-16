"""#3589 — the dating confrontation reads cited DAYS, not only cited years.

The panel measured (cycle 13, gemini 6 of 6 on doc_B) a severe M2 the
delivered year channel (#3479) could not see: the document cites an earlier
speech as "month day" with NO year printed, the situation claims that very
day, and the year comparison passes because a later date in the same year
is possible at year granularity. The extraction read four-digit tokens
only, so the cited day never became a floor and never rode the prompt
either.

What this file pins, synthetic-only (invented texts, invented days — never
a corpus date or name):

- the deterministic month-day extraction: a full month name carrying a day
  number, French or English, day-first ("14 mars", "the 3rd of May") or
  month-first ("March 14"), quoted with its offset;
- a month-day is a floor only when a past-event cue carries it: the same
  error rule as the years, one shape finer — a doubtful token loses its
  floor, never gains one;
- a situation claiming the very cited day is degraded to an uncertain
  dating named by the quoted reference, and Acte I prints the refutation
  first; a situation naming several distinct days (it describes relations
  among events, not its own date) passes untouched (R1170);
- the cited month-days ride the historian's prompt beside the years;
- a situation dated later in the same month, a situation without a
  month-day, a document without a cue-carried month-day and the #3479 year
  channel all pass through untouched — byte-identically.
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

#: A synthetic text citing ONE earlier speech by month and day, no year —
#: the measured shape, invented words and day only.
_TEXT_WITH_PAST_DAY = (
    "Une prose neutre ouvre, sans aucun chiffre ni date. " * 20
    + "Le délégué rappelle le discours prononcé le 14 mars à Valmont, "
    "et le cite en exergue avant d'y répondre. "
    + "Une prose neutre continue, sans chiffre d'aucune sorte. " * 20
)
_OFFSET_14 = _TEXT_WITH_PAST_DAY.index("14 mars")

#: The same prose citing the day with NO past-event cue: an announcement, not
#: a delivered event — no floor (the years' own error rule, one shape finer).
_TEXT_WITH_BARE_DAY = (
    "Une prose neutre ouvre, sans aucun chiffre ni date. " * 20
    + "Nous nous reverrons le 14 mars, dit-il en conclusion du débat. "
    + "Une prose neutre continue, sans chiffre d'aucune sorte. " * 20
)

_SAME_DAY_PAYLOAD = {
    "situation": "Allocution prononcée le 14 mars, devant l'assemblée.",
    "blind_spot": "",
    "items": [],
}
_TWO_DAYS_PAYLOAD = {
    "situation": ("Allocution du 20 mars, en réponse au discours prononcé le 14 mars."),
    "blind_spot": "",
    "items": [],
}
_EARLIER_DAY_PAYLOAD = {
    "situation": "Allocution prononcée le 10 mars, devant l'assemblée.",
    "blind_spot": "",
    "items": [],
}
_LATER_DAY_PAYLOAD = {
    "situation": "Allocution prononcée le 20 mars, devant l'assemblée.",
    "blind_spot": "",
    "items": [],
}


def _state(**fields):
    base = dict(
        raw_text=_TEXT_WITH_PAST_DAY,
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
# The deterministic extraction — month-day shapes, floors only with a cue
# ============================================================================


class TestTheMonthDayExtraction:
    """The new symbols are imported INSIDE each test so the file still
    collects on ``main``: the feature tests redden on the missing symbol
    while the byte-identity controls stay green there — the born-red
    measurement keeps its control arm."""

    def test_a_cued_month_day_is_a_floor_with_its_quote_and_offset(self):
        from argumentation_analysis.agents.core.context.stated_dates import (
            extract_past_month_days,
        )

        floors = extract_past_month_days(_TEXT_WITH_PAST_DAY)

        assert [(f.month, f.day) for f in floors] == [(3, 14)]
        entry = floors[0]
        assert entry.offset == _OFFSET_14
        assert "discours prononcé le 14 mars" in entry.quote

    def test_the_french_shapes_read_days_first_and_ordinals(self):
        from argumentation_analysis.agents.core.context.stated_dates import (
            extract_past_month_days,
        )

        text = (
            "Le discours du 1er mai est cité, puis la venue du 3 juin, "
            "toutes deux déjà prononcées."
        )

        assert [(f.month, f.day) for f in extract_past_month_days(text)] == [
            (5, 1),
            (6, 3),
        ]

    def test_the_english_shapes_read_month_first_and_the_of_form(self):
        from argumentation_analysis.agents.core.context.stated_dates import (
            extract_past_month_days,
        )

        text = (
            "The speaker answers the speech of March 14, and recalls the "
            "delegate who came to Norbury on the 3rd of May."
        )

        assert [(f.month, f.day) for f in extract_past_month_days(text)] == [
            (3, 14),
            (5, 3),
        ]

    def test_a_month_day_no_cue_carries_is_not_a_floor(self):
        from argumentation_analysis.agents.core.context.stated_dates import (
            extract_past_month_days,
        )

        # The years' own error rule (R1148/R1149), one shape finer: a bare
        # month-day can announce a future meeting as well as cite a past
        # speech. Invented words, no corpus shape.
        assert extract_past_month_days(_TEXT_WITH_BARE_DAY) == []

    def test_a_day_in_words_or_an_impossible_day_is_not_read(self):
        from argumentation_analysis.agents.core.context.stated_dates import (
            stated_month_days,
        )

        assert stated_month_days("le quatorze mars, dit-il") == []
        assert [
            (c.month, c.day) for c in stated_month_days("le 31 février et le 30 avril")
        ] == [(4, 30)]

    def test_one_printed_reference_stays_one_entry(self):
        """R1170's nit: "14 mars 15" is one reference (3, 14), not two —
        the month-first pattern must not read "mars 15" inside it."""
        from argumentation_analysis.agents.core.context.stated_dates import (
            stated_month_days,
        )

        assert [(c.month, c.day) for c in stated_month_days("le 14 mars 15")] == [
            (3, 14)
        ]

    def test_the_situation_side_reads_every_claimed_month_day(self):
        from argumentation_analysis.agents.core.context.stated_dates import (
            stated_month_days,
        )

        claimed = stated_month_days(_SAME_DAY_PAYLOAD["situation"])

        assert [(c.month, c.day) for c in claimed] == [(3, 14)]


# ============================================================================
# Witness — the situation claiming the cited day is degraded and named
# ============================================================================


class TestAClaimedCitedDayIsDegradedAndNamed:
    async def test_the_state_degrades_the_dating_named_by_the_cited_day(self):
        result = await build_historical_context(_state(), _llm(_SAME_DAY_PAYLOAD))

        dating = result.to_state()["dating"]
        assert dating["status"] == "uncertain"
        refute = dating["refuted_by"]
        assert (refute["month"], refute["day"]) == (3, 14)
        assert refute["offset"] == _OFFSET_14
        assert "discours prononcé le 14 mars" in refute["quote"]
        # The year channel stays intact: no year key on this refutation, and
        # nothing but the reference itself (R1170 dropped the precede flag).
        assert set(refute) == {"month", "day", "quote", "offset"}

    async def test_a_situation_naming_two_distinct_days_is_not_confronted(self):
        """R1170's measured false positive: the situation correctly names
        the past speech it answers, plus its own day — that is a relation
        among events, not a claim that it happens on the cited day."""
        result = await build_historical_context(_state(), _llm(_TWO_DAYS_PAYLOAD))

        assert "dating" not in result.to_state()

    async def test_a_day_before_the_cited_day_no_longer_fires(self):
        """R1170 removed the precede clause: a day without a year places
        nothing within the claimed year (a winter speech cites the previous
        summer), so a situation dated ten days earlier passes untouched."""
        result = await build_historical_context(_state(), _llm(_EARLIER_DAY_PAYLOAD))

        assert "dating" not in result.to_state()

    async def test_act1_prints_the_refutation_first_and_keeps_the_situation(self):
        from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
            Act1Evidence,
            build_act1_prompt,
        )

        result = await build_historical_context(_state(), _llm(_SAME_DAY_PAYLOAD))
        prompt = build_act1_prompt(Act1Evidence(historical_context=result.to_state()))

        assert "Datation DÉGRADÉE" in prompt
        assert "discours prononcé le 14 mars" in prompt
        assert f"position {_OFFSET_14}" in prompt
        assert "ne peut" in prompt
        # R1170: the precede wording is gone from the Acte I sentence.
        assert "ni avant lui" not in prompt
        # Anti-pendulum: the situation still renders — model knowledge,
        # reframed as uncertain, never silenced.
        assert "prononcée le 14 mars" in prompt

    def test_the_pipeline_writer_persists_the_degradation(self):
        from argumentation_analysis.orchestration.state_writers import (
            _write_historical_context_to_state,
        )

        state = SimpleNamespace(historical_context={})
        _write_historical_context_to_state(
            {
                "situation": "Allocution prononcée le 14 mars.",
                "items": [],
                "status": "ok",
                "dating": {
                    "status": "uncertain",
                    "model_year": None,
                    "refuted_by": {
                        "month": 3,
                        "day": 14,
                        "quote": "discours prononcé le 14 mars à Valmont",
                        "offset": _OFFSET_14,
                    },
                },
            },
            state,
            {},
        )

        dating = state.historical_context["dating"]
        assert dating["refuted_by"]["day"] == 14


# ============================================================================
# The prompt carries the cited month-days beside the years
# ============================================================================


class TestThePromptCarriesTheCitedMonthDays:
    async def test_the_cited_month_day_rides_the_prompt(self):
        sink = []

        await build_historical_context(
            _state(), _capturing_llm(_SAME_DAY_PAYLOAD, sink)
        )

        (prompt,) = sink
        assert "Past month-day references" in prompt
        assert "discours prononcé le 14 mars" in prompt
        assert f"(offset {_OFFSET_14})" in prompt

    async def test_a_month_day_no_cue_carries_does_not_ride(self):
        sink = []

        await build_historical_context(
            _state(raw_text=_TEXT_WITH_BARE_DAY),
            _capturing_llm(_SAME_DAY_PAYLOAD, sink),
        )

        (prompt,) = sink
        assert "Past month-day references" not in prompt
        assert "Dated references" not in prompt


# ============================================================================
# The controls pass through byte-identically
# ============================================================================


class TestTheControlsPassThroughByteIdentical:
    async def test_a_later_day_in_the_same_month_writes_no_dating_key(self):
        """The issue's own control: a situation dated later in the floor's
        year stays untouched."""
        result = await build_historical_context(_state(), _llm(_LATER_DAY_PAYLOAD))

        assert result.to_state() == {
            "situation": "Allocution prononcée le 20 mars, devant l'assemblée.",
            "blind_spot": "",
            "items": [],
            "status": "ok",
            "basis": MODEL_KNOWLEDGE_BASIS,
        }

    async def test_a_situation_without_a_month_day_is_not_confronted(self):
        payload = {"situation": "Une transition institutionnelle.", "items": []}

        result = await build_historical_context(_state(), _llm(payload))

        assert "dating" not in result.to_state()

    async def test_a_day_no_cue_carries_refutes_nothing(self):
        """The cue rule's other arm: without a cue there is no floor, so the
        same claimed day on an announcement text stays untouched."""
        result = await build_historical_context(
            _state(raw_text=_TEXT_WITH_BARE_DAY), _llm(_SAME_DAY_PAYLOAD)
        )

        assert "dating" not in result.to_state()

    async def test_the_year_channel_still_fires_alone(self):
        """Positive control: the #3479 channel is intact — a situation a
        whole year earlier than a cited YEAR degrades on the year, and the
        day channel stays silent behind it."""
        text = (
            "Le rappel ouvre sur le congrès du 14 mars 2019, déjà passé. "
            + "Une prose neutre continue, sans chiffre. " * 30
        )
        payload = {"situation": "Rédigé autour de 2004.", "items": []}

        result = await build_historical_context(_state(raw_text=text), _llm(payload))

        dating = result.to_state()["dating"]
        assert dating["refuted_by"]["year"] == 2019
        assert "month" not in dating["refuted_by"]

    def test_the_prompt_stays_byte_identical_without_month_days(self):
        prompt = build_historian_prompt(_state(raw_text=_TEXT_WITH_BARE_DAY), "X")

        assert prompt == HISTORIAN_PROMPT.format(
            speaker="Speaker_A",
            venue="assembly",
            topic=NOT_RECORDED_IN_METADATA,
            era=NOT_RECORDED_IN_METADATA,
            language=NOT_RECORDED_IN_METADATA,
            stakes_block="  (aucun enjeu extrait)",
            dates_section="",
            excerpt="X",
        )
