"""#3491 — a rhetorical question keeps its FORCE, never its bare content.

Measured defect (issue #3491, `5075cd82/arg_3`): the document asks a
rhetorical question and answers it with an explicit negative right after
the ``?``. The extractor's unit is a declarative paraphrase of the
question's CONTENT (the inverted claim), the stored ``source_quote``
stops at the ``?`` so the answer sits outside it, and the inverted unit
feeds ~80 downstream fields (descent, JTMS, Dung/ASPIC, ranking, bipolar,
NL-to-logic, counter-arguments, Acts II/III) — Act III listed among the
speaker's certainties a proposition he explicitly DENIES. Census on the
10 c4b states (1406 units): 38 units with ``?`` in the verbatim source,
38/38 restated as declarative unit texts; 1 carries the explicit answer.

The fix has a deterministic half (the writer decides FROM THE QUOTE —
``ends_as_question`` decides that the quote is a question, and
``extend_question_quote`` carries the short answer into the stored
provenance, #3428's courtesy applied at the extractor) and a model half
(``_QUESTION_FORCE_INSTRUCTION``: the position stated is the ANSWER's
polarity when the text answers, else the item stays a question).

#3499 — the first version of the window crossed speech turns: 15 of the 27
extensions on the panel carried, as the speaker's answer, the NEXT speaker's
line (12) or a stage direction or audience reaction (3). The window is now
bounded at the turn boundary, and the ``form`` field of the first version is
gone: it had no reader, the extended citation is the mark.

These witnesses are synthetic (invented prose, no dataset content, no
paid call — the measurement on the 38 census units is the coordinator's).
Three contracts:

1. ``TestInstructionReachesTheWire`` — the instruction is threaded into
   the production system prompt (1745 wire-pin pattern) and carries the
   turn rule, not a ``form`` field.
2. ``TestQuestionForceAtTheWriter`` — the deterministic half: an answered
   question in the SAME turn → extended quote; a turn boundary → quote
   untouched; a declarative unit → byte-identical to today, no extra key.
3. ``TestTurnBoundary`` / ``TestQuestionHelpers`` — the boundary rule and
   the window's edge cases.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argumentation_analysis.core.shared_state import (
    UnifiedAnalysisState,
    _is_speaker_designation,
    _turn_boundary_offset,
    ends_as_question,
    extend_question_quote,
)
from argumentation_analysis.orchestration.invoke_callables import (
    _invoke_fact_extraction,
)
from argumentation_analysis.orchestration.state_writers import (
    _write_fact_extraction_to_state,
)

INVOKE_PATH = "argumentation_analysis.orchestration.invoke_callables"

# Invented document (no dataset content). The measured shape: a question
# whose explicit answer ("Non !") sits right after the ``?``.
_DOC_ANSWERED = (
    "Le rapport annonce une renaissance économique. Est-ce que ce "
    "programme a réellement créé des emplois durables ? Non ! Les "
    "chiffres additionnent des transferts d'hôtels existants. La ville "
    "voit les conséquences depuis deux hivers."
)

# The verbatim question the extractor would return as source_quote.
_Q_ANSWERED = "Est-ce que ce programme a réellement créé des emplois durables ?"
_A_ANSWERED = "Non !"


def _resp(content: str) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


def _write_one_argument(state: UnifiedAnalysisState, arg: dict) -> str:
    """Drive the writer with one argument item; return the arg_id."""
    _write_fact_extraction_to_state(
        {"arguments": [arg], "claims": [], "summary": "s"},
        state,
        {},
    )
    return sorted(state.identified_arguments)[-1]


class TestInstructionReachesTheWire:
    """Contract 1 — the #3491 instruction is on the deployed wire."""

    def test_instruction_reaches_the_wire(self):
        import argumentation_analysis.orchestration.invoke_callables as mod

        assert mod._QUESTION_FORCE_INSTRUCTION.strip(), (
            "_QUESTION_FORCE_INSTRUCTION is empty — the #3491 geste is " "not deployed"
        )
        valid_json = (
            '{"arguments": [{"text": "x", "source_quote": "x"}], '
            '"claims": [], "summary": "ok"}'
        )
        with (
            patch(
                f"{INVOKE_PATH}._get_openai_client",
                return_value=(MagicMock(), "m"),
            ),
            patch(
                f"{INVOKE_PATH}._guarded_chat_completion",
                new=AsyncMock(return_value=_resp(valid_json)),
            ) as mock_call,
            patch(f"{INVOKE_PATH}._get_determinism_params", return_value={}),
        ):
            asyncio.new_event_loop().run_until_complete(
                _invoke_fact_extraction("some text", {"_state_object": None})
            )
        system_message = mock_call.call_args.kwargs["messages"][0]["content"]
        assert mod._QUESTION_FORCE_INSTRUCTION in system_message, (
            "the #3491 instruction is not threaded into the extraction " "system prompt"
        )

    def test_the_instruction_bounds_the_answer_to_the_same_turn(self):
        """#3499 — the model is told what the writer enforces.

        The first version asked for a ``form`` field with no reader; the
        instruction now names the boundary the window applies.
        """
        import argumentation_analysis.orchestration.invoke_callables as mod

        instruction = mod._QUESTION_FORCE_INSTRUCTION
        assert "SAME speaker's" in instruction
        assert "same speech turn" in instruction
        assert "stage direction" in instruction
        assert "'form'" not in instruction


class TestQuestionForceAtTheWriter:
    """Contract 2 — the deterministic half, decided from the QUOTE.

    The model's own statement is not consulted: when the quote is a question,
    the writer extends it with the short answer of the SAME turn (census:
    38/38 declarative restatements — trusting the model here is trusting the
    defect), and never invents anything when the turn ends.
    """

    def test_answered_question_quote_carries_the_answer(self):
        state = UnifiedAnalysisState(_DOC_ANSWERED)
        arg_id = _write_one_argument(
            state,
            {
                "text": "Le locuteur demande si le programme a créé des emplois durables",
                "source_quote": _Q_ANSWERED,
                "move_author": "speaker",
            },
        )
        prov = state.argument_provenance[arg_id]
        # The stored quote now CONTAINS the explicit answer that the bare
        # question stopped in front of (the measured defect).
        assert prov["source_quote"].startswith(_Q_ANSWERED)
        assert _A_ANSWERED in prov["source_quote"]

    def test_the_declarative_restatement_is_carried_by_the_quote_alone(self):
        """The census shape: the model ALREADY restated the question as a
        declarative unit — the quote still carries the answer, and no
        ``form`` key is written (it had no reader, #3499)."""
        state = UnifiedAnalysisState(_DOC_ANSWERED)
        arg_id = _write_one_argument(
            state,
            {
                "text": "Le programme a créé des emplois durables",
                "source_quote": _Q_ANSWERED,
            },
        )
        prov = state.argument_provenance[arg_id]
        assert _A_ANSWERED in prov["source_quote"]
        assert "form" not in prov

    def test_the_next_speakers_line_is_never_carried(self):
        """#3499, leaked class 1 — measured on 12 of the 27 extensions."""
        doc = "Qui paie la facture ?\nJean Dupont : Nous la paierons tous."
        state = UnifiedAnalysisState(doc)
        arg_id = _write_one_argument(
            state,
            {
                "text": "Question sur le payeur",
                "source_quote": "Qui paie la facture ?",
            },
        )
        prov = state.argument_provenance[arg_id]
        assert prov["source_quote"] == "Qui paie la facture ?"

    def test_a_stage_direction_is_never_carried(self):
        """#3499, leaked class 2 — measured on 3 of the 27 extensions."""
        doc = "Qui paie la facture ? (Applaudissements nourris.) La séance continue."
        state = UnifiedAnalysisState(doc)
        arg_id = _write_one_argument(
            state,
            {
                "text": "Question sur le payeur",
                "source_quote": "Qui paie la facture ?",
            },
        )
        assert state.argument_provenance[arg_id]["source_quote"] == (
            "Qui paie la facture ?"
        )

    def test_an_audience_reaction_is_never_carried(self):
        doc = "Qui paie la facture ? [Rires dans la salle.] La séance continue."
        state = UnifiedAnalysisState(doc)
        arg_id = _write_one_argument(
            state,
            {
                "text": "Question sur le payeur",
                "source_quote": "Qui paie la facture ?",
            },
        )
        assert state.argument_provenance[arg_id]["source_quote"] == (
            "Qui paie la facture ?"
        )

    def test_a_dialogue_dash_line_is_never_carried(self):
        doc = "Qui paie la facture ?\n— Nous tous, évidemment."
        state = UnifiedAnalysisState(doc)
        arg_id = _write_one_argument(
            state,
            {
                "text": "Question sur le payeur",
                "source_quote": "Qui paie la facture ?",
            },
        )
        assert state.argument_provenance[arg_id]["source_quote"] == (
            "Qui paie la facture ?"
        )

    def test_a_blank_line_ends_the_turn(self):
        """One panel document separates its turns this way — alone it is not
        enough, hence the two label witnesses above."""
        doc = "Qui paie la facture ?\n\nNous la paierons tous."
        state = UnifiedAnalysisState(doc)
        arg_id = _write_one_argument(
            state,
            {
                "text": "Question sur le payeur",
                "source_quote": "Qui paie la facture ?",
            },
        )
        assert state.argument_provenance[arg_id]["source_quote"] == (
            "Qui paie la facture ?"
        )

    def test_second_question_is_not_an_answer(self):
        doc = (
            "Est-ce que le programme a tenu ses promesses ? Est-ce que la "
            "moindre de ses promesses a été tenue ? Le conseil refuse de "
            "répondre."
        )
        state = UnifiedAnalysisState(doc)
        arg_id = _write_one_argument(
            state,
            {
                "text": "Double question rhétorique sur les promesses",
                "source_quote": "Est-ce que le programme a tenu ses promesses ?",
            },
        )
        prov = state.argument_provenance[arg_id]
        # A second question is not an answer: the quote stays the question.
        assert prov["source_quote"] == "Est-ce que le programme a tenu ses promesses ?"

    def test_question_at_end_of_text_keeps_its_quote(self):
        doc = "Le rapport s'achève sur une question. Qui paie la prochaine facture ?"
        state = UnifiedAnalysisState(doc)
        arg_id = _write_one_argument(
            state,
            {
                "text": "La question finale reste sans réponse",
                "source_quote": "Qui paie la prochaine facture ?",
            },
        )
        prov = state.argument_provenance[arg_id]
        assert prov["source_quote"] == "Qui paie la prochaine facture ?"

    def test_long_continuation_is_not_a_short_answer(self):
        long_tail = (
            " Le comité a publié, après deux ans d'études et trois "
            "révisions successives du protocole de mesure, un résumé de "
            "quatre-vingts pages dont personne n'a encore lu la conclusion "
            "jusqu'au bout."
        )
        doc = "Le programme a-t-il tenu ses promesses ?" + long_tail
        state = UnifiedAnalysisState(doc)
        arg_id = _write_one_argument(
            state,
            {
                "text": "Question sur les promesses du programme",
                "source_quote": "Le programme a-t-il tenu ses promesses ?",
            },
        )
        prov = state.argument_provenance[arg_id]
        # > max_answer_chars: not a short answer, the quote is untouched.
        assert prov["source_quote"] == "Le programme a-t-il tenu ses promesses ?"

    def test_unlocatable_quote_quote_untouched(self):
        doc = "Un texte sans la question citée."
        state = UnifiedAnalysisState(doc)
        arg_id = _write_one_argument(
            state,
            {
                "text": "Question absente du document",
                "source_quote": "Où sont passés les millions annoncés ?",
            },
        )
        prov = state.argument_provenance[arg_id]
        assert prov["source_quote"] == "Où sont passés les millions annoncés ?"

    def test_declarative_unit_is_byte_identical_to_before(self):
        state = UnifiedAnalysisState(_DOC_ANSWERED)
        quote = "Les chiffres additionnent des transferts d'hôtels existants."
        arg_id = _write_one_argument(
            state,
            {
                "text": "Les emplois annoncés sont des transferts",
                "source_quote": quote,
            },
        )
        # No extra key, and the stored text keeps the exact pre-#3491 format.
        assert "form" not in state.argument_provenance[arg_id]
        assert state.identified_arguments[arg_id] == (
            "Les emplois annoncés sont des transferts " f'[quote: "{quote}"]'
        )

    def test_no_quote_no_window(self):
        state = UnifiedAnalysisState(_DOC_ANSWERED)
        arg_id = _write_one_argument(state, {"text": "Une unité sans citation"})
        assert "form" not in state.argument_provenance[arg_id]
        assert "source_quote" not in state.argument_provenance[arg_id]


class TestTheFormFieldIsGone:
    """Contract 3a — #3499: the field had no reader, so it is removed."""

    def test_add_argument_takes_no_form_keyword(self):
        state = UnifiedAnalysisState("Qui paie ? Non !")
        with pytest.raises(TypeError):
            state.add_argument(  # type: ignore[call-arg]
                "d", producer="llm_extract", form="rhetorical_question"
            )


class TestTurnBoundary:
    """Contract 3b — the boundary rule, on its own."""

    def test_a_speaker_designation_is_recognised(self):
        assert _is_speaker_designation("Jean Dupont")
        assert _is_speaker_designation("Le Maire")
        assert _is_speaker_designation("M. Dupont")

    def test_a_sentence_with_a_colon_is_not_a_designation(self):
        assert not _is_speaker_designation("les trois taux")
        assert not _is_speaker_designation("Il dit")
        assert not _is_speaker_designation("Vraiment, oui")
        assert not _is_speaker_designation(
            "Un libellé beaucoup trop long pour être une désignation de locuteur"
        )
        assert not _is_speaker_designation("")

    def test_the_boundary_is_the_first_marker_only(self):
        window = " Oui, absolument. Jean Dupont : autre chose."
        # The label is INSIDE the first sentence's prose, not at a line start:
        # the boundary rule reads line openings, so it reports the next line.
        assert _turn_boundary_offset(window) is None

    @pytest.mark.parametrize(
        "window",
        [
            "\nJean Dupont : Oui.",
            "\n\nOui.",
            " (Applaudissements.)",
            " [Rires.]",
            "\n— Oui.",
        ],
    )
    def test_each_marker_bounds_the_window(self, window):
        assert _turn_boundary_offset(window) is not None


class TestQuestionHelpers:
    """Contract 3c — the predicates on their own."""

    def test_ends_as_question_shapes(self):
        assert ends_as_question("Qui paie ?")
        assert ends_as_question("Qui paie ? ")
        assert ends_as_question("« Qui paie ? »")
        assert not ends_as_question("Personne ne paie.")
        assert not ends_as_question("")

    def test_extend_carries_short_answer(self):
        doc = "Qui paie ? Non ! Suite du texte."
        assert extend_question_quote("Qui paie ?", doc) == "Qui paie ? Non !"

    def test_extend_through_closing_gillemets(self):
        doc = "Il demande « Qui paie ? » Non !"
        assert extend_question_quote("« Qui paie ? »", doc) == "« Qui paie ? » Non !"

    def test_extend_refuses_second_question(self):
        doc = "Qui paie ? Qui décide ? Personne."
        assert extend_question_quote("Qui paie ?", doc) == "Qui paie ?"

    def test_extend_refuses_unlocatable(self):
        assert extend_question_quote("Qui paie ?", "Aucun rapport.") == "Qui paie ?"

    def test_extend_refuses_no_sentence_end_in_window(self):
        doc = "Qui paie ? et puis plus jamais aucune ponctuation pour finir"
        assert extend_question_quote("Qui paie ?", doc) == "Qui paie ?"
