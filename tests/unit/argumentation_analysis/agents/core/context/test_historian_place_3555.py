"""#3555 — the historian's venue is confronted with the place the document states.

Measured at cycle 7 of the v1 panel (#3374): on one document the historian's
situation placed the speech somewhere the document says it was not, both
judge families kept the item on every pass, and nothing read the document's
own statement of where it was being given. The dating has had its
confrontation since #3479; the place had none.

What this file pins, synthetic-only (invented place names, invented text —
never a corpus venue, name or date):

- the deterministic reader of a document's venue: the deictic forms only
  (``cette ville de X``, ``this … city of X``, ``here in X``, ``ici à X``),
  with the place NAME's offset — the position a render can point at;
- the address form (``people of X``) is not a venue: measured on the cycle-7
  corpus it named audiences the speaker was not among, so it is excluded and
  the pull request says the reader does not catch it;
- a situation placing the speech elsewhere, while the document states its own
  venue, records the conflict in its own ``place`` field, named by the
  document's passage and offset;
- the venue is read from the WHOLE text: the passage sits outside the reading
  window the historian was given, and the conflict is recorded all the same;
- a situation that names the document's venue, one that names no place, and a
  document that states no venue all pass through unchanged — no ``place`` key
  anywhere;
- a region statement (``dans …``) is not a venue: it names the area that may
  contain the document's venue, and refuting it would refute a right
  situation;
- Acte I reads the field: the document's own statement is printed with its
  passage and position, and the situation is marked as naming a refuted place;
- the dating post-check still fires beside it (the positive control the issue
  asks for: the test reaches the post-checks).
"""

from __future__ import annotations

import json
from types import SimpleNamespace

from argumentation_analysis.agents.core.context import MODEL_KNOWLEDGE_BASIS
from argumentation_analysis.agents.core.context.historian import (
    build_historical_context,
)
from argumentation_analysis.core.reading_window import (
    LLM_EXTRACTION_WINDOW,
    WHOLE_TEXT_CALL_CAPACITY,
)

#: Neutral filler with no capitalised name and no venue cue: the document has
#: to be long enough that one extraction call cannot hold it (#3522's rule —
#: a fitting document is read whole, and then nothing would be left outside).
_FILLER = "Une phrase neutre de remplissage, sans aucun nom propre ni lieu. "

#: The document states its own venue deictically, once, far into the text.
_VENUE_NAME = "Port-Rouge"
_VENUE_SENTENCE = (
    "Le conférencier s'adresse à son auditoire : « je parle ici, dans cette "
    f"ville de {_VENUE_NAME}, comme je l'ai fait ailleurs »."
)
_LONG_TEXT = _FILLER * 60 + _VENUE_SENTENCE + _FILLER * 40
_VENUE_OFFSET = _LONG_TEXT.index(_VENUE_NAME)

#: The same shape with no venue statement at all.
_TEXT_WITHOUT_VENUE = _FILLER * 60 + _FILLER * 40

#: A document citing a past calendar date (#3479's post-check control).
_DATED_TEXT = (
    _FILLER * 60
    + _VENUE_SENTENCE
    + "Depuis la réforme du 14 mars 2019, les délégués suivent une autre "
    "méthode et chacun s'en souvient. " + _FILLER * 40
)

#: The stubbed historian replies. ``_REFUTED_PAYLOAD`` places the speech in a
#: town the document never names; the others are the controls.
_REFUTED_PLACE = "Valcourt"
_REFUTED_PAYLOAD = {
    "situation": (
        f"Il s'agit d'une allocution prononcée à {_REFUTED_PLACE}, devant une "
        "assemblée réunie pour débattre de la méthode."
    ),
    "blind_spot": "",
    "items": [{"claim": "Le cadre est parlementaire.", "confidence": 0.7}],
}
_CONSISTENT_PAYLOAD = {
    "situation": (
        f"Il s'agit d'une allocution prononcée à {_VENUE_NAME}, devant une "
        "assemblée réunie pour débattre de la méthode."
    ),
    "blind_spot": "",
    "items": [],
}
_NO_PLACE_PAYLOAD = {
    "situation": "Ce texte expose une méthode de travail, sans nommer aucun lieu.",
    "blind_spot": "",
    "items": [],
}
_REGION_PAYLOAD = {
    "situation": (
        "Il s'agit d'une allocution prononcée dans l'État de "
        f"{_VENUE_NAME}, devant une assemblée réunie pour débattre."
    ),
    "blind_spot": "",
    "items": [],
}
_DATING_PAYLOAD = {
    "situation": (
        f"Il s'agit d'une allocution prononcée à {_REFUTED_PLACE} en 2004, "
        "devant une assemblée réunie pour débattre de la méthode."
    ),
    "blind_spot": "",
    "items": [],
}


def _state(**fields):
    base = dict(
        raw_text=_LONG_TEXT,
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
# The deterministic reader of the document's own venue
# ============================================================================


class TestTheDocumentVenueReader:
    """The new symbols are imported INSIDE each test so the file still
    collects on ``main``: the feature tests redden on the missing symbol
    while the byte-identity controls stay green there — the born-red
    measurement keeps its control arm."""

    def test_the_deictic_cue_names_the_place_at_its_own_offset(self):
        from argumentation_analysis.agents.core.context.historian import (
            _document_venue_statements,
        )

        statements = _document_venue_statements(_LONG_TEXT)

        assert len(statements) == 1
        statement = statements[0]
        assert statement["name"] == _VENUE_NAME
        # The NAME's position, not the cue's: the position a render points at.
        assert statement["offset"] == _VENUE_OFFSET
        assert f"cette ville de {_VENUE_NAME}" in statement["quote"]

    def test_an_address_is_not_a_venue(self):
        from argumentation_analysis.agents.core.context.historian import (
            _document_venue_statements,
        )

        # Measured on the cycle-7 corpus: documents given at X addressed the
        # "people of" places they were not in. The reader must not take them.
        # The sentence below is invented (no real place names, rule 7).
        assert (
            _document_venue_statements(
                "I speak to the people of Valmont, and to the people of "
                "Norbury, about the union and its future."
            )
            == []
        )

    def test_the_kind_word_a_capture_ends_on_is_not_the_name(self):
        from argumentation_analysis.agents.core.context.historian import (
            _strip_generic_tail,
        )

        assert _strip_generic_tail("Port Neuf City") == "Port Neuf"
        assert _strip_generic_tail("Port Neuf") == "Port Neuf"


class TestTheSituationPlaceReader:
    def test_the_venitive_prepositions_name_the_place(self):
        from argumentation_analysis.agents.core.context.historian import (
            _situation_place_candidates,
        )

        assert _situation_place_candidates(_REFUTED_PAYLOAD["situation"]) == [
            _REFUTED_PLACE
        ]

    def test_a_region_statement_is_not_a_venue(self):
        from argumentation_analysis.agents.core.context.historian import (
            _situation_place_candidates,
        )

        # "dans l'État de X" names the area that may CONTAIN the venue — the
        # measured c10 shape. Reading it as a venue would refute a right
        # situation.
        assert _situation_place_candidates(_REGION_PAYLOAD["situation"]) == []

    def test_the_explicit_place_kind_form_is_a_venue(self):
        from argumentation_analysis.agents.core.context.historian import (
            _situation_place_candidates,
        )

        assert _situation_place_candidates(
            "Allocution prononcée dans la ville de Valcourt, devant l'assemblée."
        ) == ["Valcourt"]

    def test_names_that_can_be_the_same_place_are_treated_as_such(self):
        from argumentation_analysis.agents.core.context.historian import (
            _names_share,
        )

        # The cross-language class the reader cannot resolve by equality:
        # the same place written in two languages shares a long prefix.
        assert _names_share("Valbourg", "Waldborg") is False  # two towns
        assert _names_share("Valbourg", "Valburg") is True  # one town, two hands
        assert _names_share("Port", "Port Neuf") is True  # containment
        # Two different towns must not be merged by a loose prefix.
        assert _names_share("Brienne", "Brissac") is False


# ============================================================================
# Witness 1 — the refuted venue is recorded, named by the document
# ============================================================================


class TestARefutedVenueIsRecorded:
    async def test_the_state_carries_the_conflict_and_the_documents_passage(self):
        result = await build_historical_context(_state(), _llm(_REFUTED_PAYLOAD))

        payload = result.to_state()
        place = payload["place"]
        assert place["status"] == "refuted"
        assert place["model_places"] == [_REFUTED_PLACE]
        assert place["document"]["name"] == _VENUE_NAME
        assert place["document"]["offset"] == _VENUE_OFFSET
        assert f"cette ville de {_VENUE_NAME}" in place["document"]["quote"]
        assert place["document"]["statements"] == 1

    async def test_the_venue_is_read_from_the_whole_text_not_the_excerpt(self):
        """The measured mechanism: the statement sits outside the window."""
        from argumentation_analysis.agents.core.reading import defining_moves
        from argumentation_analysis.core.reading_window import persona_reading

        state = _state()
        excerpt, _selection, _extra = persona_reading(
            state.raw_text, defining_moves(state)
        )
        assert _VENUE_NAME not in excerpt
        assert len(_LONG_TEXT) > WHOLE_TEXT_CALL_CAPACITY
        assert _VENUE_OFFSET > LLM_EXTRACTION_WINDOW

        prompts = []
        result = await build_historical_context(
            state, _capturing_llm(_REFUTED_PAYLOAD, prompts)
        )

        assert _VENUE_NAME not in prompts[0]
        assert result.place_degraded is True

    async def test_the_pipeline_writer_persists_the_refutation(self):
        from argumentation_analysis.orchestration.state_writers import (
            _write_historical_context_to_state,
        )

        state = SimpleNamespace(historical_context={})
        _write_historical_context_to_state(
            {
                "situation": "Allocution prononcée à Valcourt.",
                "items": [],
                "status": "ok",
                "place": {
                    "status": "refuted",
                    "document": {
                        "name": _VENUE_NAME,
                        "quote": f"cette ville de {_VENUE_NAME}",
                        "offset": _VENUE_OFFSET,
                        "statements": 1,
                    },
                    "model_places": [_REFUTED_PLACE],
                },
            },
            state,
            {},
        )

        place = state.historical_context["place"]
        assert place["status"] == "refuted"
        assert place["model_places"] == [_REFUTED_PLACE]


# ============================================================================
# Witness 2 — the controls pass through unchanged
# ============================================================================


class TestCompatibleSituationsPassThroughByteIdentical:
    async def test_a_situation_that_names_the_documents_venue_is_unchanged(self):
        result = await build_historical_context(_state(), _llm(_CONSISTENT_PAYLOAD))

        assert "place" not in result.to_state()

    async def test_a_situation_that_names_no_place_is_unchanged(self):
        result = await build_historical_context(_state(), _llm(_NO_PLACE_PAYLOAD))

        assert "place" not in result.to_state()

    async def test_a_region_around_the_venue_is_not_a_conflict(self):
        result = await build_historical_context(_state(), _llm(_REGION_PAYLOAD))

        assert "place" not in result.to_state()

    async def test_a_document_that_states_no_venue_is_unchanged(self):
        result = await build_historical_context(
            _state(raw_text=_TEXT_WITHOUT_VENUE), _llm(_REFUTED_PAYLOAD)
        )

        assert "place" not in result.to_state()


# ============================================================================
# The dating post-check still fires beside it (the issue's positive control)
# ============================================================================


class TestThePostChecksRunTogether:
    async def test_the_dating_post_check_still_fires(self):
        result = await build_historical_context(
            _state(raw_text=_DATED_TEXT), _llm(_DATING_PAYLOAD)
        )

        assert result.dating_degraded is True
        # Same run, same producer: the venue is confronted too.
        assert result.place_degraded is True


# ============================================================================
# Acte I reads the field
# ============================================================================


class TestAct1ReadsTheField:
    def _state_payload(self):
        return {
            "situation": _REFUTED_PAYLOAD["situation"],
            "blind_spot": "",
            "items": [],
            "status": "ok",
            "basis": MODEL_KNOWLEDGE_BASIS,
            "place": {
                "status": "refuted",
                "document": {
                    "name": _VENUE_NAME,
                    "quote": f"je parle ici, dans cette ville de {_VENUE_NAME}",
                    "offset": _VENUE_OFFSET,
                    "statements": 1,
                },
                "model_places": [_REFUTED_PLACE],
            },
        }

    def test_the_documents_own_statement_is_printed_first_with_its_position(self):
        from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
            _format_historical_block,
        )

        block = _format_historical_block(self._state_payload())

        confrontation = block.split("\n", 1)[0]
        assert "Lieu CONFRONTÉ" in confrontation
        assert _VENUE_NAME in confrontation
        assert str(_VENUE_OFFSET) in confrontation
        assert _REFUTED_PLACE in confrontation
        assert "le document fait foi sur le lieu" in confrontation

    def test_the_situation_is_marked_as_naming_a_refuted_place(self):
        from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
            _format_historical_block,
        )

        block = _format_historical_block(self._state_payload())

        assert "Situation (lieu refuté — voir ci-dessus)" in block

    def test_a_consistent_read_renders_byte_identical(self):
        from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
            _format_historical_block,
        )

        assert _format_historical_block(
            {
                "situation": "Allocution prononcée à Valcourt.",
                "blind_spot": "",
                "items": [],
                "status": "ok",
                "basis": MODEL_KNOWLEDGE_BASIS,
            }
        ) == ("  Situation : Allocution prononcée à Valcourt.")
