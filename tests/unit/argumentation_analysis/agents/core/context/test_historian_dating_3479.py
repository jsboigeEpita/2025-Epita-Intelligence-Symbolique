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

#: A synthetic text citing ONE year as already past. Opaque words, invented
#: year — nothing here comes from the corpus.
_TEXT_WITH_PAST_DATE = (
    "Un rappel ouvre le propos : depuis le congrès de 2019, l'assemblée a "
    "changé de méthode, et chaque délégué s'en souvient. "
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
        assert "congrès de 2019" in entry.quote
        assert entry.projected is False

    def test_the_bound_is_the_latest_year_cited_as_past(self):
        from argumentation_analysis.agents.core.context.stated_dates import (
            extract_stated_dates,
            past_cited_bound,
        )

        text = "Le texte évoque 1904 puis, plus loin, l'accord de 1955."

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
            "l'accord de 1955."
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
        assert "congrès de 2019" in prompt
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
        assert "congrès de 2019" in dating["refuted_by"]["quote"]

    async def test_a_range_situation_is_confronted_on_its_earliest_year(self):
        payload = {"situation": "Le texte couvre la période 1904-2004.", "items": []}

        result = await build_historical_context(
            _state(raw_text=_TEXT_WITH_PAST_DATE), _llm(payload)
        )

        assert result.to_state()["dating"]["model_year"] == 1904

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
        assert "congrès de 2019" in prompt
        assert f"position {_OFFSET_2019}" in prompt
        assert "postérieur à 2019" in prompt
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
                        "quote": "depuis le congrès de 2019",
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
        # bytes either way.
        assert prompt == HISTORIAN_PROMPT.format(
            speaker="Speaker_A",
            venue="assembly",
            topic="unknown",
            era="unknown",
            language="unknown",
            stakes_block="  (aucun enjeu extrait)",
            dates_section="",
            excerpt="EXTRAIT FIXE",
        )
