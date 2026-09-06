"""#1914 (Acte I slice) — the interpretive question Acte III answers.

Issue contract (Acte I): "State the discourse's central rhetorical problem
and the interpretive question the analysis will answer." The Acte III slice
(#1941) built the answer beat — hierarchy P1→P3, four orders of judgment,
zero-shot surplus — but nothing in the report POSES the question: the
restitution answers a question nobody poses.

This slice wires the question end to end:

* Acte I's prompt instructs the LLM to CLOSE the framing with a final
  delimited line ``QUESTION INTERPRÉTATIVE : <question>``, derived from
  THIS document's verified evidence (genre, enjeux, parties engagées,
  spectre) — a reusable template question is the named failure mode.
* :func:`build_act1_framing` extracts that line into
  ``Act1Result.interpretive_question`` (honest absence when the LLM emits
  no marker / no LLM at all — never a fabricated question).
* The carrier is the STATE (``interpretive_question``), persisted by both
  orchestration lanes (pipeline state writer + conversational adapter) and
  READ by :func:`build_act3_evidence` — the Acte III prompt carries a
  [QUESTION DE L'ACTE I] block and a consigne binding the response beat
  (battement 2) to answer THAT question explicitly.

Born-red discipline (sister of ``test_act3_salience_channel_nered_1914``):
imports only modules present on main long before this PR; the
conversational helper is imported lazily inside its test so the file never
fails wholesale on ``ImportError``. Pre-fix this reddens on
``AttributeError`` (no ``interpretive_question`` anywhere) and on the
missing prompt sections — red for the RIGHT reason.
"""

from __future__ import annotations

import re
from types import SimpleNamespace

from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
    build_act1_evidence,
    build_act1_framing,
    build_act1_prompt,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_evidence,
    build_act3_prompt,
)

# --- state stubs (mirror test_act1_framing_plugin conventions) ---------------


def _state(**fields: object) -> SimpleNamespace:
    base = dict(
        source_metadata={},
        stakes_and_stakeholders={
            "stakes": [],
            "stakeholders": [],
            "rhetorical_register": "",
            "discursive_arena": "",
        },
        identified_arguments={},
    )
    base.update(fields)
    return SimpleNamespace(**base)


def _political_state() -> SimpleNamespace:
    return _state(
        source_metadata={
            "genre": "discours politique",
            "speaker_role": "locuteur en autorité",
            "channel": "arène publique",
        },
        stakes_and_stakeholders={
            "rhetorical_register": "délibératif",
            "discursive_arena": "politique",
            "stakes": [
                {
                    "stake_type": "décision",
                    "description": "Mobiliser l'auditoire sur une décision controversée.",
                },
            ],
            "stakeholders": [
                {"role": "locuteur", "interest": "Faire adopter la décision."},
                {"role": "adversaire", "interest": "Bloquer la décision."},
            ],
        },
        identified_arguments={"arg_1": "thèse", "arg_2": "support"},
    )


def _scientific_state() -> SimpleNamespace:
    return _state(
        source_metadata={
            "genre": "publication scientifique",
            "speaker_role": "chercheur",
            "channel": "revue",
        },
        stakes_and_stakeholders={
            "rhetorical_register": "démonstratif",
            "discursive_arena": "scientifique",
            "stakes": [
                {
                    "stake_type": "crédibilité",
                    "description": "Faire accepter une interprétation des données.",
                },
            ],
            "stakeholders": [
                {"role": "auteur", "interest": "Faire accepter l'interprétation."},
                {"role": "pairs", "interest": "Éprouver l'interprétation."},
            ],
        },
        identified_arguments={"arg_1": "hypothèse", "arg_2": "donnée"},
    )


# --- LLM stubs ----------------------------------------------------------------


def _stub_llm(return_value: str):
    async def _call(_prompt: str) -> str:
        return return_value

    return _call


def _genre_echo_llm():
    """A conductor stub that FOLLOWS the prompt: reads the genre the prompt
    itself carries (document data → question) and closes with a question
    embedding it. Two contrasted states therefore produce two different
    questions — the document-specificity the issue demands."""

    async def _call(prompt: str) -> str:
        m = re.search(r"Spectre : DÉRIVÉ du genre « (.+?) »", prompt)
        genre = m.group(1) if m else "genre inconnu"
        return (
            "### Le texte\n\nProse de cadrage pour ce document.\n\n"
            "### Les enjeux\n\nCe qui se joue ici.\n\n"
            "### Le spectre attendu\n\nAntipation ancrée.\n\n"
            "### La lecture game-theoretic\n\nLecture stratégique.\n\n"
            f"QUESTION INTERPRÉTATIVE : Ce discours {genre} survit-il à "
            "l'examen argumentatif de ses propres engagements ?"
        )

    return _call


# --- Acte I: the question is instructed, posed, extracted ---------------------


def test_act1_prompt_demands_a_document_specific_question():
    prompt = build_act1_prompt(build_act1_evidence(_political_state()))
    assert "QUESTION INTERPRÉTATIVE" in prompt, (
        "#1914: the Acte I prompt must instruct the LLM to close the "
        "framing with the interpretive question"
    )
    # The directive must bind the question to THIS document's verified data
    # (anti-template) and forbid inventing context (#1906/#1910 frontier).
    directive_zone = prompt[prompt.index("QUESTION INTERPRÉTATIVE") :]
    assert (
        "vérifiée" in directive_zone or "vérifié" in directive_zone
    ), "the question directive must anchor the question in verified data"
    assert (
        "n'invente" in directive_zone or "JAMAIS" in directive_zone
    ), "the question directive must forbid invented context"


def test_woven_result_carries_the_extracted_question():
    narrative_with_question = (
        "### Le texte\n\nCadrage.\n\n### Les enjeux\n\nEnjeux.\n\n"
        "### Le spectre attendu\n\nAnticipation.\n\n"
        "### La lecture game-theoretic\n\nLecture.\n\n"
        "QUESTION INTERPRÉTATIVE : La décision promue résiste-t-elle à "
        "l'examen de ses appuis factuels ?"
    )
    import asyncio

    result = asyncio.run(
        build_act1_framing(
            _political_state(), llm_callable=_stub_llm(narrative_with_question)
        )
    )
    assert result.status == "woven"
    assert result.interpretive_question == (
        "La décision promue résiste-t-elle à l'examen de ses appuis factuels ?"
    ), "#1914: the marker line must be extracted into the structured carrier"


def test_honest_absence_when_no_marker_line():
    narrative_without_question = (
        "### Le texte\n\nCadrage.\n\n### Les enjeux\n\nEnjeux.\n\n"
        "### Le spectre attendu\n\nAnticipation.\n\n"
        "### La lecture game-theoretic\n\nLecture."
    )
    import asyncio

    result = asyncio.run(
        build_act1_framing(
            _political_state(), llm_callable=_stub_llm(narrative_without_question)
        )
    )
    assert result.interpretive_question == "", (
        "no marker line in the narrative → no question (honest absence, "
        "never a fabricated one)"
    )


def test_no_llm_no_question():
    import asyncio

    result = asyncio.run(build_act1_framing(_political_state(), llm_callable=None))
    assert result.status == "unavailable"
    assert result.interpretive_question == ""


def test_two_contrasted_states_pose_two_different_questions():
    """DoD: two contrasted synthetic states → two different questions. The
    stub derives its question from the genre the PROMPT carries, so this
    measures the full chain: evidence varies → prompt varies → question
    varies → carrier transmits."""
    import asyncio

    q_political = asyncio.run(
        build_act1_framing(_political_state(), llm_callable=_genre_echo_llm())
    ).interpretive_question
    q_scientific = asyncio.run(
        build_act1_framing(_scientific_state(), llm_callable=_genre_echo_llm())
    ).interpretive_question
    assert q_political and q_scientific, "both states must pose a question"
    assert q_political != q_scientific, (
        f"#1914: contrasted documents must pose different questions, got "
        f"the same: {q_political!r}"
    )


# --- the carrier: state field, both lanes persist it --------------------------


def test_pipeline_writer_persists_the_question():
    from argumentation_analysis.orchestration.state_writers import (
        _write_act1_framing_to_state,
    )

    state = _state()
    state.act1_framing = ""
    state.interpretive_question = ""
    _write_act1_framing_to_state(
        {"act1_framing": "narrative", "interpretive_question": "Q du document"},
        state,
        {},
    )
    assert state.interpretive_question == "Q du document", (
        "#1914: the pipeline lane must persist the question onto the state "
        "for Acte III to read"
    )


def test_conversational_lane_persists_the_question():
    # Lazy import: the helper is born in this PR — a module-level import
    # would redden the whole file on ImportError (né-rouge discipline).
    from argumentation_analysis.reporting.restitution.conversational_adapter import (
        _persist_interpretive_question,
    )

    state = _state()
    state.interpretive_question = ""
    _persist_interpretive_question(state, "Q du document")
    assert state.interpretive_question == "Q du document", (
        "#1914: the conversational lane must persist the question too — "
        "the two lanes must agree on the carrier"
    )
    # Defensive twin of _persist_act: a state without the attribute is
    # skipped (logged), never crashed.
    bare = SimpleNamespace()
    _persist_interpretive_question(bare, "Q")  # must not raise


# --- Acte III: the question is READ and the response beat binds to it ---------


def _act3_state(**fields: object) -> SimpleNamespace:
    base = dict(
        identified_arguments={"arg_1": "these A", "arg_9": "these C"},
        identified_fallacies={},
        argument_quality_scores={},
        counter_arguments=[],
        jtms_beliefs={},
        dung_frameworks={},
        propositional_analysis_results=[],
        fol_analysis_results=[{"consistent": False, "message": "incoherent"}],
        modal_analysis_results=[],
        workflow_results={},
        interpretive_question="",
    )
    base.update(fields)
    return SimpleNamespace(**base)


def test_act3_evidence_reads_the_question_from_state():
    evidence = build_act3_evidence(_act3_state(interpretive_question="Q1"))
    assert evidence.interpretive_question == "Q1", (
        "#1914: the conclusion evidence must READ the question from the "
        "state — written by Acte I, read by Acte III"
    )


def test_act3_prompt_carries_and_distinguishes_the_question():
    """DoD wiring, MEASURED: changing the question in the state changes the
    Acte III prompt. With the question unwired this reddens (the block
    never carries the question text)."""
    prompt_q1 = build_act3_prompt(
        build_act3_evidence(
            _act3_state(interpretive_question="La thèse centrale tient-elle ?")
        )
    )
    assert "QUESTION DE L'ACTE I" in prompt_q1
    assert (
        "La thèse centrale tient-elle ?" in prompt_q1
    ), "the question posed in Acte I must ride into the Acte III prompt"
    prompt_q2 = build_act3_prompt(
        build_act3_evidence(
            _act3_state(
                interpretive_question="L'asymétrie d'information a-t-elle servi le propos ?"
            )
        )
    )
    assert "L'asymétrie d'information a-t-elle servi le propos ?" in prompt_q2
    assert (
        "La thèse centrale tient-elle ?" not in prompt_q2
    ), "a different question must produce a different Acte III render"


def test_act3_prompt_without_question_renders_honest_absence():
    """#1941 discipline: the block renders in BOTH states so a silence is
    never misread — when no question was posed, the honest-absence wording
    renders and the consigne forbids a retroactive question. No placeholder
    question is ever fabricated."""
    prompt = build_act3_prompt(
        build_act3_evidence(_act3_state(interpretive_question=""))
    )
    assert "QUESTION DE L'ACTE I" in prompt, "the block renders in both states"
    lowered = prompt.lower()
    assert (
        "aucune question" in lowered
    ), "honest absence must be named when Acte I posed no question"


# --- #1906/#1910 frontier: metadata-absent state ------------------------------


def test_metadata_absent_state_keeps_the_question_grounded():
    """The negative control: an empty state (no metadata, no stakes) still
    gets the question directive, the directive forbids invention, and the
    honest-absence channel stays open when nothing is woven."""
    empty = _state()
    prompt = build_act1_prompt(build_act1_evidence(empty))
    # Genre unknown → general spectrum (pre-existing honesty, unchanged).
    assert "GÉNÉRAL" in prompt
    # The question directive is still instructed — the question may anchor
    # on verified claims/spectrum — but must not lean on invented context.
    directive_zone = prompt[prompt.index("QUESTION INTERPRÉTATIVE") :]
    assert "n'invente" in directive_zone or "JAMAIS" in directive_zone
