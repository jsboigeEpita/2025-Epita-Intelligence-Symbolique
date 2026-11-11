# -*- coding: utf-8 -*-
"""#3512 — an unrecorded speaker never reaches a prompt as ``speaker=unknown``.

Cycle 5 measured the chain: the corpus metadata carries the literal
``unknown``, three prompts format it verbatim, the stakes extractor copies it
as a stakeholder name, and every act then tells the reader « la source ne
documente pas le locuteur » — a sentence that says more than was measured (the
metadata does not record a speaker, and the reading identified none; whether
the source names one was never checked).

What this file pins, all synthetic (no LLM answer, no corpus token):

* ONE helper renders a metadata field the corpus did not record: the prompt
  line says the field is not recorded and asks for it to be identified from
  the text if the text names it, empty otherwise;
* none of the three prompt fathers (stakes extractor, historian, strategist)
  formats the literal ``unknown`` any more;
* the absent-case naming rule hands the writer the measured sentence, never
  a claim about what the source documents.

Born-red discipline: the helper is imported INSIDE its test, so the pre-fix
run fails on the behaviour (the literal in the prompts, the over-claiming
sentence), not on a module-level import error collection.
"""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

_EXCERPT = "un extrait synthétique, assez long pour être un extrait." * 20
_NOT_RECORDED = (
    "not recorded in the corpus metadata — identify it from the text if the "
    "text names it, empty otherwise"
)
_MEASURED_ABSENCE = (
    "la métadonnée n'enregistre pas de locuteur et la lecture n'en identifie aucun"
)


def _state(metadata=None):
    state = SimpleNamespace()
    state.source_metadata = dict(metadata or {})
    state.stakes_and_stakeholders = {"stakes": [], "stakeholders": []}
    return state


def _json_client(payload: dict) -> MagicMock:
    choice = MagicMock()
    choice.message.content = json.dumps(payload)
    response = MagicMock()
    response.choices = [choice]
    client = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=response)
    return client


def test_one_helper_renders_the_unrecorded_case():
    from argumentation_analysis.core.metadata_prompt import metadata_prompt_value

    assert metadata_prompt_value({"speaker": "Nom_syncretique"}, "speaker") == (
        "Nom_syncretique"
    ), "a recorded value passes through unchanged"
    for metadata in ({}, {"speaker": ""}, {"speaker": "unknown"}):
        assert (
            metadata_prompt_value(metadata, "speaker") == _NOT_RECORDED
        ), "the corpus's literal placeholder must never ride a prompt"


def test_the_historian_prompt_never_formats_the_literal_unknown():
    from argumentation_analysis.agents.core.context.historian import (
        build_historian_prompt,
    )

    for metadata in ({"speaker": "unknown"}, {}):
        prompt = build_historian_prompt(_state(metadata), _EXCERPT)
        assert "speaker=unknown" not in prompt
        assert _NOT_RECORDED in prompt


def test_the_strategist_prompt_never_formats_the_literal_unknown():
    from argumentation_analysis.agents.core.context.strategist import (
        build_strategist_prompt,
    )

    for metadata in ({"speaker": "unknown"}, {}):
        prompt = build_strategist_prompt(_state(metadata), _EXCERPT)
        assert "speaker=unknown" not in prompt
        assert _NOT_RECORDED in prompt


async def test_the_stakes_extractor_prompt_never_formats_the_literal_unknown():
    from argumentation_analysis.agents.core.political.stakes_extractor import (
        StakesExtractor,
    )

    client = _json_client({"stakes": [], "stakeholders": []})
    result = await StakesExtractor().extract(
        arguments=[{"text": "un argument synthétique"}],
        source_metadata={"speaker": "unknown"},
        raw_text=_EXCERPT,
        llm_client=client,
    )
    assert result["extraction_status"] == "ok"
    prompt = client.chat.completions.create.call_args.kwargs["messages"][0]["content"]
    assert "speaker=unknown" not in prompt
    assert _NOT_RECORDED in prompt


def test_the_absent_case_rule_states_what_was_measured():
    from argumentation_analysis.reporting.restitution.speaker_record import (
        SPEAKER_NAMING_RULE,
    )

    assert "la source ne documente pas le locuteur" not in SPEAKER_NAMING_RULE
    assert _MEASURED_ABSENCE in SPEAKER_NAMING_RULE
