"""#3584 — a segment with no proposition is not an argument unit.

The panel measured it on doc_D: a bracketed scene line (a heading naming an
event and a place) stays an argument unit on every recorded cycle, the
per-argument fallacy pass files it at 0.98-0.99 — sometimes under the
taxonomy's root family, once under a node literally meaning "empty
argument" — and the record's OWN justification says the passage holds
"ni proposition argumentative ni raisonnement". The verdict then travels
into counters, JTMS and Act II, which opens a section claiming the document
opens on that line. The zero-shot does not.

The repair is by FORM, as a class (#3584): a scene line, a speaker tag, an
audience reaction standing alone, a timestamp hold no proposition and are
not minted as argument units — at BOTH producers (llm_extract and
kb_heuristic). Never corpus words, never a length threshold: a unit that
opens on a bracket but carries the speaker's sentence after it STAYS
(measured: 9 such units on one panel document), and a short real sentence
STAYS. The one-shot fallback gains the abstention its contract lacked
(the descent already had no-fallacy terminals).

Privacy: invented filler throughout, opaque ids, no corpus text.
Deterministic: no JVM, no network. The LLM is a stub where the one-shot is
exercised.
"""

import json
from unittest.mock import AsyncMock, MagicMock, create_autospec

import pytest
from semantic_kernel import Kernel

from argumentation_analysis.core.shared_state import UnifiedAnalysisState

# --- invented filler (the SHAPE of the measured class, never its words) -----

#: A scene line: an event and a place, entirely bracketed.
SCENE_LINE = "[Une rencontre, une ville industrielle.]"

#: The same, after the extractor mangled the closing bracket into a period
#: (measured storage form).
SCENE_LINE_MANGLED = "[Une rencontre, une ville industrielle."

#: A speaker tag alone (play/transcript convention).
SPEAKER_TAG = "PREMIER ORATEUR:"

#: A transcript timestamp alone.
TIMESTAMP = "00:12:34"

#: A bracket opened but the speaker's own sentence follows — STAYS a unit.
BRACKET_THEN_SENTENCE = (
    "[Applaudissements.] Voilà pourquoi la mesure doit être maintenue."
)

#: A short real sentence — STAYS a unit (no length threshold, #3584 ask 2).
SHORT_SENTENCE = "Il faut agir."

#: A question keeps its force (#3491) — STAYS a unit.
QUESTION_UNIT = "Pourquoi attendrions-nous encore ?"


def _taxonomy():
    """One guarded leaf and one plain leaf — enough for the one-shot."""
    rows = [
        (1, "4", "4", "Erreur de raisonnement", "root"),
        (2, "4.1", "41", "Faux raisonnement", "sub"),
        (
            3,
            "4.1.1",
            "411",
            "Argument circulaire",
            "La conclusion revient comme prémisse.",
        ),
        (2, "4.2", "42", "Pertinence", "sub"),
        (3, "4.2.1", "421", "Appel à l'autorité", "Une autorité tient lieu de preuve."),
    ]
    data = []
    for depth, path, pk, text_fr, desc in rows:
        data.append(
            {
                "PK": pk,
                "path": path,
                "depth": str(depth),
                "text_fr": text_fr,
                "text_en": text_fr,
                "desc_fr": desc,
                "desc_en": desc,
                "Famille": "test",
                "Sous-Famille": text_fr,
                "nom_vulgarisé": text_fr,
                "example_fr": "",
                "example_en": "",
            }
        )
    return data


def _plugin():
    from argumentation_analysis.plugins.fallacy_workflow_plugin import (
        FallacyWorkflowPlugin,
    )

    return FallacyWorkflowPlugin(
        master_kernel=create_autospec(Kernel, instance=True),
        llm_service=MagicMock(),
        taxonomy_data=_taxonomy(),
    )


# --- the form class ----------------------------------------------------------


class TestTheFormClass:
    """The class test reads the FORM only — no corpus word, no length."""

    def _form(self, text):
        from argumentation_analysis.core.shared_state import non_propositional_form

        return non_propositional_form(text)

    def test_a_scene_line_wholly_bracketed_is_bracket_only(self):
        assert self._form(SCENE_LINE) == "bracket_only"

    def test_the_mangled_closing_bracket_still_reads_bracket_only(self):
        """Measured storage form: the extractor turned ']' into '.'. The
        restoration is a form fact, not a content guess."""
        assert self._form(SCENE_LINE_MANGLED) == "bracket_only"

    def test_a_speaker_tag_alone_is_speaker_tag_only(self):
        assert self._form(SPEAKER_TAG) == "speaker_tag_only"

    def test_a_timestamp_alone_is_timestamp_only(self):
        assert self._form(TIMESTAMP) == "timestamp_only"

    def test_a_bracketed_timestamp_is_bracket_only(self):
        assert self._form(f"[{TIMESTAMP}]") == "bracket_only"

    def test_a_short_real_sentence_stays_a_unit(self):
        assert self._form(SHORT_SENTENCE) == ""

    def test_a_bracket_followed_by_the_speakers_sentence_stays(self):
        """The doc_B/doc_H population: the reaction is followed by the
        speaker's own sentence in the SAME unit — it carries a proposition."""
        assert self._form(BRACKET_THEN_SENTENCE) == ""

    def test_a_question_stays_a_unit(self):
        assert self._form(QUESTION_UNIT) == ""


# --- the llm_extract writer gate --------------------------------------------


class TestTheExtractWriterRefusesToMintThem:
    """A non-propositional segment never becomes an argument unit, and the
    refusal is recorded by class — nothing silently dropped."""

    def _write(self):
        from argumentation_analysis.orchestration.state_writers import (
            _write_fact_extraction_to_state,
        )

        state = UnifiedAnalysisState("un texte quelconque pour le test.")
        output = {
            "arguments": [
                # The measured class: a scene line (mangled bracket), with
                # the verbatim quote the extractor carried.
                {"text": SCENE_LINE_MANGLED, "source_quote": SCENE_LINE},
                # A short real sentence: minted.
                {"text": SHORT_SENTENCE, "source_quote": SHORT_SENTENCE},
                # A speaker tag alone (bare-string shape): refused.
                SPEAKER_TAG,
                # A bracket followed by the speaker's sentence: minted.
                {"text": BRACKET_THEN_SENTENCE, "source_quote": BRACKET_THEN_SENTENCE},
                # A timestamp alone: refused.
                {"text": TIMESTAMP},
            ],
            "extraction_status": "ok",
        }
        _write_fact_extraction_to_state(output, state, {})
        return state

    def test_only_the_propositional_units_are_minted(self):
        state = self._write()
        texts = list(state.identified_arguments.values())
        assert (
            len(texts) == 2
        ), f"expected the 2 propositional units, got {len(texts)}: {texts}"
        assert any(SHORT_SENTENCE in t for t in texts)
        assert any(BRACKET_THEN_SENTENCE.split("]")[1].strip() in t for t in texts)

    def test_the_scene_line_never_becomes_a_unit(self):
        state = self._write()
        joined = " ".join(state.identified_arguments.values())
        assert "rencontre" not in joined, "the scene line was minted as a unit"
        assert "ORATEUR" not in joined, "the speaker tag was minted as a unit"
        assert TIMESTAMP not in joined, "the timestamp was minted as a unit"

    def test_the_refusal_is_recorded_by_class(self):
        state = self._write()
        tasks = " ".join(str(t) for t in state.analysis_tasks.values())
        assert "[extraction_refused]" in tasks, "the refusal is silent"
        assert "3 unit(s)" in tasks
        assert "bracket_only=1" in tasks
        assert "speaker_tag_only=1" in tasks
        assert "timestamp_only=1" in tasks

    def test_no_scene_line_reaches_the_argument_provenance(self):
        state = self._write()
        assert set(state.argument_provenance) == set(state.identified_arguments)


class TestTheExtractWriterControlOnMain:
    """Green on main AND on the branch: propositional units are minted with
    their provenance, quotes and status, exactly as before."""

    def test_propositional_units_are_minted_as_before(self):
        from argumentation_analysis.orchestration.state_writers import (
            _write_fact_extraction_to_state,
        )

        state = UnifiedAnalysisState("un texte quelconque pour le test.")
        output = {
            "arguments": [
                {"text": SHORT_SENTENCE, "source_quote": SHORT_SENTENCE},
                {"text": BRACKET_THEN_SENTENCE, "source_quote": BRACKET_THEN_SENTENCE},
            ],
            "extraction_status": "ok",
        }
        _write_fact_extraction_to_state(output, state, {})
        assert len(state.identified_arguments) == 2
        assert all(
            p.get("producer") == "llm_extract"
            for p in state.argument_provenance.values()
        )
        assert any(
            "[extraction_status] ok" in str(t) for t in state.analysis_tasks.values()
        )


# --- the kb_heuristic writer gate -------------------------------------------


class TestTheKbHeuristicWriterRefusesThemToo:
    """The second producer mints whole-text paragraph splits: a chunk that is
    entirely a scene line holds no proposition either, whoever split it."""

    def _write(self):
        from argumentation_analysis.orchestration.state_writers import (
            _write_text_to_kb_to_state,
        )

        state = UnifiedAnalysisState(
            "Première phrase du texte. " + SCENE_LINE + " Dernière phrase du texte."
        )
        output = {
            "arguments": [
                {"text": SCENE_LINE, "text_offset": 27},
                {"text": "Dernière phrase du texte.", "text_offset": 55},
            ],
            "belief_candidates": [],
        }
        _write_text_to_kb_to_state(output, state, {})
        return state

    def test_only_the_propositional_chunk_is_minted(self):
        state = self._write()
        assert len(state.identified_arguments) == 1
        assert "Dernière phrase" in " ".join(state.identified_arguments.values())

    def test_the_refusal_is_recorded_with_the_producer_named(self):
        state = self._write()
        tasks = " ".join(str(t) for t in state.analysis_tasks.values())
        assert "[extraction_refused]" in tasks
        assert "kb_heuristic" in tasks
        assert "bracket_only=1" in tasks


# --- the one-shot abstention -------------------------------------------------


class TestTheOneShotAbstention:
    """#3584 ask 3: the one-shot contract offered no abstention — the model
    HAD to name a fallacy whatever the passage held. The descent already had
    no-fallacy terminals (#3376); this repairs the missing side."""

    def _reply(self, **fields):
        payload = {
            "fallacy_name": "none",
            "taxonomy_pk": "",
            "explanation": "une didascalie ne porte aucune proposition",
            "confidence": 0.0,
        }
        payload.update(fields)
        return json.dumps(payload, ensure_ascii=False)

    @pytest.mark.asyncio
    async def test_a_none_answer_records_no_detection(self):
        plugin = _plugin()
        plugin.llm_service.get_chat_message_content = AsyncMock(
            return_value=self._reply()
        )
        result = json.loads(await plugin._run_one_shot(SCENE_LINE, None))
        assert result["fallacies"] == []
        assert result["exploration_method"] == "one_shot_no_proposition"
        assert result["no_proposition_reason"].startswith("une didascalie")

    @pytest.mark.asyncio
    async def test_the_french_none_answers_the_same(self):
        plugin = _plugin()
        plugin.llm_service.get_chat_message_content = AsyncMock(
            return_value=self._reply(fallacy_name="aucune")
        )
        result = json.loads(await plugin._run_one_shot(SCENE_LINE, None))
        assert result["fallacies"] == []
        assert result["exploration_method"] == "one_shot_no_proposition"

    @pytest.mark.asyncio
    async def test_the_prompt_offers_the_abstention(self):
        plugin = _plugin()
        plugin.llm_service.get_chat_message_content = AsyncMock(
            return_value=self._reply()
        )
        await plugin._run_one_shot(SCENE_LINE, None)
        history = plugin.llm_service.get_chat_message_content.call_args.kwargs.get(
            "chat_history"
        )
        messages = [m.content for m in history.messages]
        served = " ".join(str(m) for m in messages)
        assert (
            "no proposition at all" in served
        ), "the served prompt never offers the abstention"

    @pytest.mark.asyncio
    async def test_a_real_fallacy_still_files(self):
        """Control, green on main AND branch: the abstention does not loosen
        the judge — a named fallacy is parsed and returned as before."""
        plugin = _plugin()
        plugin.llm_service.get_chat_message_content = AsyncMock(
            return_value=self._reply(
                fallacy_name="Argument circulaire",
                taxonomy_pk="411",
                explanation="la conclusion revient comme prémisse",
                confidence=0.7,
            )
        )
        result = json.loads(
            await plugin._run_one_shot("La thèse se prouve par elle-même.", None)
        )
        assert len(result["fallacies"]) == 1
        assert result["fallacies"][0]["fallacy_type"] == "Argument circulaire"
