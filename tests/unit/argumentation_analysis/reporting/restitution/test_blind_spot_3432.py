"""#3432 (ask 2) — the thesis's blind spot is a reading, wired to Acte III.

The panel measured the gap against the same-model zero-shot (#2841): the
pipeline reconstructs what the thesis SAYS with ever more instruments, and
never says what it LEAVES OUT — the absent actor, the cost the framing makes
invisible. The zero-shot names it in a sentence; the render cannot.

The design (coordinator's dispatch): the blind spot is a READING, not a move —
it belongs to the two personas (#3377), labelled ``model_knowledge``, never in
the first reading, never a citation (it is not in the text by construction).
One named field per persona, carried by the persona's own read dict, rendered
by Acte III in both states (#1941 discipline).

What this file pins, end to end:

* the personas' prompts ASK the question (a field nobody asks for is a field
  nobody returns), and an empty string is a legitimate answer — an invented
  omission would render as knowledge;
* the producer parses it, caps it (``BLIND_SPOT_CAP``), carries it through
  ``to_state()`` — inside the dict whose ``basis`` is already stamped
  ``model_knowledge``, so the label rides the existing guarantee;
* BOTH orchestration writers persist it (a field the writer drops dies in the
  act that produced it — the exact defect of #3432 ask 3's cousin);
* Acte III READS it from the state and renders one block, one line per
  persona, labelled connaissance du modèle, in both states — the honest
  absence renders per persona, so a persona that named nothing cannot be
  silently filled by the writer.

Born-red discipline: every symbol born in this PR is imported INSIDE its
test. Everything is synthetic — no LLM, no JVM, no network.

Anti-pendulum, pinned as controls: the blind spot is never presented as read
in the text (the consigne forbids citing the text to support it), and the
first-reading surface is untouched.
"""

import json
from types import SimpleNamespace

from argumentation_analysis.agents.core.context.historian import (
    build_historical_context,
)
from argumentation_analysis.agents.core.context.strategist import (
    build_strategic_read,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_evidence,
    build_act3_prompt,
)

_EXCERPT = ("une phrase de contexte, avec des virgules; et une autre clause. " * 80)[
    :4000
]


def _state(**fields):
    base = dict(
        raw_text=_EXCERPT,
        source_metadata={"speaker": "Speaker_A", "venue": "assembly"},
        stakes_and_stakeholders={"stakes": [], "stakeholders": []},
    )
    base.update(fields)
    return SimpleNamespace(**base)


def _llm(payload):
    async def _call(prompt: str) -> str:
        return json.dumps(payload)

    return _call


# ============================================================================
# Producer side — the question is asked, the answer is carried
# ============================================================================


class TestThePromptsAskTheQuestion:
    def test_the_historian_prompt_names_the_field_and_the_empty_answer(self):
        from argumentation_analysis.agents.core.context.historian import (
            build_historian_prompt,
        )

        prompt = build_historian_prompt(_state(), _EXCERPT)
        assert (
            '"blind_spot"' in prompt
        ), "a JSON field nobody asks for is a field nobody returns"
        assert "empty string if none" in prompt, (
            "the prompt must say that naming nothing is legitimate — an "
            "invented omission would render as knowledge"
        )

    def test_the_strategist_prompt_names_the_field_and_the_empty_answer(self):
        from argumentation_analysis.agents.core.context.strategist import (
            build_strategist_prompt,
        )

        prompt = build_strategist_prompt(_state(), _EXCERPT)
        assert '"blind_spot"' in prompt
        assert "empty string if none" in prompt

    def test_both_prompts_say_it_is_model_knowledge_never_a_quote(self):
        from argumentation_analysis.agents.core.context.historian import (
            HISTORIAN_PROMPT,
        )
        from argumentation_analysis.agents.core.context.strategist import (
            STRATEGIST_PROMPT,
        )

        for prompt in (HISTORIAN_PROMPT, STRATEGIST_PROMPT):
            assert "model knowledge" in prompt.lower(), (
                "the blind spot rides the personas' existing guarantee: the "
                "model_knowledge label"
            )
            assert "never a quote" in prompt.lower(), (
                "the omission is not in the text by construction — a quote "
                "would make it look textual"
            )


class TestTheProducerCarriesTheField:
    async def test_historian_parses_and_carries_the_blind_spot(self):
        payload = {
            "situation": "Une transition institutionnelle.",
            "blind_spot": "L'absent du récit est l'assemblée qui a voté la réforme.",
            "items": [],
        }
        result = await build_historical_context(_state(), _llm(payload))

        assert result.status == "ok"
        assert result.blind_spot.startswith("L'absent du récit"), result.blind_spot
        state = result.to_state()
        assert (
            state["blind_spot"] == result.blind_spot
        ), "the carrier is the read dict the writer persists"
        assert (
            state["basis"] == "model_knowledge"
        ), "the field rides the dict-level label — that IS its labelling"

    async def test_strategist_parses_and_carries_the_blind_spot(self):
        payload = {
            "players": [
                {"name": "P1", "role": "orateur", "stance": "for"},
            ],
            "options": ["A", "B"],
            "preferences": {"P1": ["A", "B"]},
            "blind_spot": "Le coût pour les joueurs absents du cadre.",
            "reading": "Une lecture.",
        }
        result = await build_strategic_read(_state(), _llm(payload))

        assert result.status == "ok"
        assert result.blind_spot.startswith("Le coût"), result.blind_spot
        assert result.to_state()["blind_spot"] == result.blind_spot

    async def test_an_absent_field_is_the_honest_empty_string(self):
        """The model did not name an omission: the honest answer is "", never
        a fabricated one — and never a crash either."""
        historian = await build_historical_context(
            _state(), _llm({"situation": "Une situation.", "items": []})
        )
        strategist = await build_strategic_read(
            _state(),
            _llm(
                {
                    "players": [{"name": "P1", "role": "r", "stance": "for"}],
                    "options": ["A", "B"],
                    "preferences": {"P1": ["A", "B"]},
                    "reading": "Une lecture.",
                }
            ),
        )

        assert historian.blind_spot == ""
        assert historian.to_state()["blind_spot"] == ""
        assert strategist.blind_spot == ""
        assert strategist.to_state()["blind_spot"] == ""

    async def test_no_llm_names_no_blind_spot(self):
        historian = await build_historical_context(_state(), None)
        strategist = await build_strategic_read(_state(), None)

        assert historian.blind_spot == "", "no model, no omission named"
        assert strategist.blind_spot == ""

    async def test_the_answer_is_capped_at_the_named_bound(self):
        from argumentation_analysis.agents.core.context.historian import (
            BLIND_SPOT_CAP as HISTORIAN_CAP,
        )
        from argumentation_analysis.agents.core.context.strategist import (
            BLIND_SPOT_CAP as STRATEGIST_CAP,
        )

        assert (
            HISTORIAN_CAP == STRATEGIST_CAP
        ), "one bound for the two personas — they ride the same prompt"
        long_answer = "x" * (HISTORIAN_CAP + 50)
        historian = await build_historical_context(
            _state(), _llm({"situation": "", "blind_spot": long_answer, "items": []})
        )
        strategist = await build_strategic_read(
            _state(),
            _llm(
                {
                    "players": [],
                    "options": [],
                    "preferences": {},
                    "blind_spot": long_answer,
                    "reading": "",
                }
            ),
        )

        assert len(historian.blind_spot) == HISTORIAN_CAP, (
            "the cap is applied at the producer: an uncapped sentence would "
            "crowd the Acte III prompt it rides"
        )
        assert len(strategist.blind_spot) == STRATEGIST_CAP


# ============================================================================
# The carrier — both writers persist what the producer wrote
# ============================================================================


def test_pipeline_writer_persists_the_historian_blind_spot():
    from argumentation_analysis.orchestration.state_writers import (
        _write_historical_context_to_state,
    )

    state = SimpleNamespace(historical_context={})
    _write_historical_context_to_state(
        {
            "situation": "Une situation.",
            "blind_spot": "L'absent du récit.",
            "items": [],
            "status": "ok",
            "basis": "model_knowledge",
        },
        state,
        {},
    )
    assert (
        state.historical_context["blind_spot"] == "L'absent du récit."
    ), "#3432: a field the writer drops dies in the act that produced it"


def test_pipeline_writer_persists_the_strategist_blind_spot():
    from argumentation_analysis.orchestration.state_writers import (
        _write_strategic_read_to_state,
    )

    state = SimpleNamespace(strategic_read={})
    _write_strategic_read_to_state(
        {
            "players": [],
            "options": [],
            "preferences": {},
            "blind_spot": "Le coût invisible.",
            "reading": "",
            "game": {},
            "status": "ok",
            "basis": "model_knowledge",
        },
        state,
        {},
    )
    assert state.strategic_read["blind_spot"] == "Le coût invisible."


def test_an_absent_key_is_an_honest_absence_never_fabricated():
    from argumentation_analysis.orchestration.state_writers import (
        _write_historical_context_to_state,
        _write_strategic_read_to_state,
    )

    state = SimpleNamespace(historical_context={})
    _write_historical_context_to_state(
        {"situation": "Une situation.", "items": [], "status": "ok"}, state, {}
    )
    assert (
        state.historical_context["blind_spot"] == ""
    ), "an absent key is the honest absence, never a fabricated entry"

    state = SimpleNamespace(strategic_read={})
    _write_strategic_read_to_state(
        {"players": [], "options": [], "status": "ok", "game": {}}, state, {}
    )
    assert state.strategic_read["blind_spot"] == ""


# ============================================================================
# Acte III — the block renders, labelled, in both states
# ============================================================================


def _act3_state(**fields: object) -> SimpleNamespace:
    base = dict(
        identified_arguments={"arg_1": "these A"},
        identified_fallacies={},
        argument_quality_scores={},
        counter_arguments=[],
        jtms_beliefs={},
        dung_frameworks={},
        propositional_analysis_results=[],
        fol_analysis_results=[],
        modal_analysis_results=[],
        workflow_results={},
        interpretive_question="",
        announced_checks=[],
        historical_context={},
        strategic_read={},
    )
    base.update(fields)
    return SimpleNamespace(**base)


def test_act3_evidence_reads_both_blind_spots_from_the_state():
    evidence = build_act3_evidence(
        _act3_state(
            historical_context={"blind_spot": "L'absent du récit."},
            strategic_read={"blind_spot": "Le coût invisible."},
        )
    )
    assert evidence.historical_blind_spot == "L'absent du récit."
    assert evidence.strategic_blind_spot == "Le coût invisible."


def test_act3_prompt_renders_one_line_per_persona_labelled():
    prompt = build_act3_prompt(
        build_act3_evidence(
            _act3_state(
                historical_context={"blind_spot": "L'absent du récit."},
                strategic_read={"blind_spot": "Le coût invisible."},
            )
        )
    )
    assert "CE QUE LA THÈSE LAISSE DE CÔTÉ" in prompt, "the block must be labelled"
    assert "connaissance du modèle" in prompt, (
        "the block header carries the label — this is model knowledge, never "
        "the text's content"
    )
    assert "l'historien : L'absent du récit." in prompt
    assert "le stratège : Le coût invisible." in prompt, (
        "each line carries its persona: the reader must be able to tell a "
        "historian's omission from a strategist's"
    )


def test_the_honest_absence_renders_per_persona():
    """#1941 discipline: the block renders in BOTH states. A persona that
    named nothing renders its own absence line — a missing line would let the
    writer fill the gap with the text's own content, the exact confusion the
    model_knowledge label exists to prevent."""
    prompt = build_act3_prompt(build_act3_evidence(_act3_state()))
    assert "CE QUE LA THÈSE LAISSE DE CÔTÉ" in prompt
    assert "l'historien : (aucune tache aveugle nommée" in prompt
    assert "le stratège : (aucune tache aveugle nommée" in prompt
    assert "n'en invente pas une" in prompt


def test_one_persona_s_absence_renders_next_to_the_other_s_answer():
    prompt = build_act3_prompt(
        build_act3_evidence(
            _act3_state(
                historical_context={"blind_spot": "L'absent du récit."},
                strategic_read={"blind_spot": ""},
            )
        )
    )
    assert "l'historien : L'absent du récit." in prompt
    assert "le stratège : (aucune tache aveugle nommée" in prompt


def test_a_different_blind_spot_produces_a_different_prompt():
    one = build_act3_prompt(
        build_act3_evidence(
            _act3_state(historical_context={"blind_spot": "L'absent du récit."})
        )
    )
    two = build_act3_prompt(
        build_act3_evidence(
            _act3_state(historical_context={"blind_spot": "La période éludée."})
        )
    )
    assert "L'absent du récit." in one and "L'absent du récit." not in two
    assert "La période éludée." in two and "La période éludée." not in one


def test_the_consigne_binds_the_label_and_forbids_the_quote():
    """Anti-pendulum, writer side: the omission is model knowledge — the
    consigne forbids presenting it as the text's content, and forbids citing
    the text to support it (the omission is not IN the text)."""
    prompt = build_act3_prompt(
        build_act3_evidence(
            _act3_state(historical_context={"blind_spot": "L'absent du récit."})
        )
    )
    flattened = " ".join(prompt.split())
    assert (
        "CONNAISSANCE DU MODÈLE" in flattened
    ), "the consigne must name the label the state already carries"
    assert "sans citer le texte à l'appui" in flattened, (
        "a quote would make the omission look textual — it is not, by " "construction"
    )
    assert "sans le présenter comme une extraction" in flattened or (
        "jamais un contenu du texte" in flattened
    )


# ============================================================================
# Controls — what this change must NOT do
# ============================================================================


def test_the_first_reading_surface_is_untouched():
    """The dispatch pins the design: the blind spot is a persona's read, NOT
    a first-reading product. The first-reading plugin must not know the
    field."""
    from argumentation_analysis.core import reading_window

    source = open(reading_window.__file__, encoding="utf-8").read()
    assert "blind_spot" not in source, (
        "the first reading names what the text SAYS; the blind spot is what "
        "it leaves out — a persona's read, never a reading-window product"
    )


def test_a_non_dict_read_does_not_crash_the_evidence():
    """Defensive twin: a state whose persona field is not a dict (None from a
    degraded lane) must yield the honest empty string, not a crash."""
    evidence = build_act3_evidence(
        _act3_state(historical_context=None, strategic_read=None)
    )
    assert evidence.historical_blind_spot == ""
    assert evidence.strategic_blind_spot == ""
