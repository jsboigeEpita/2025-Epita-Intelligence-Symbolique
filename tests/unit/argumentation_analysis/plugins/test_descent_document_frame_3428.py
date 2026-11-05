"""#3428 — the descent reads the unit as the document frames it.

Panel cycle 2 measured the M2 contresens with one producer: a fallacy found
by the per-unit hierarchical descent whose justification makes a claim about
the document that the document refutes — 13 of the 27 M2 items, four shapes:

* a direct, ironic assertion read as a « suggested association » (amalgam);
* a « can » with explicit premises read as a mechanical repetition (the
  unit was extracted as a paraphrase that stripped the modality);
* an alternative whose second branch is a strawman read as a closed dilemma
* a conditional (« would be an act that no one could... ») read as an
  actual accusation.

The fix is evidence, not a new rule: the descent is shown the document's
LOCAL frame around the unit's provenance offset — the sentence before, the
sentence after, and the verbatim passage a paraphrase restates — and asked
to judge the claim AS STATED. Deterministic, local, no second call.

Anti-pendulum, pinned here as controls: the fallacy rate does not move (a
fake model that confirms whatever it is asked confirms through the frame
— the instruction is a question, not a veto), and a unit whose provenance
carries no offset gets NO window: every prompt stays byte-identical to the
pre-#3428 path (the #3416 convention).

Privacy: invented filler, opaque ids, no corpus text. Deterministic: no JVM,
no LLM, no network.
"""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, create_autospec

import pytest
from semantic_kernel import Kernel
from semantic_kernel.contents import FunctionCallContent

from argumentation_analysis.plugins.exploration_plugin import ExplorationPlugin

# --- fixtures: one synthetic document per measured row ----------------------
#
# Each row: a document (invented filler), the unit the descent reads, and a
# UNIQUE marker that exists only inside the frame the fix hands over — the
# fake model keys on it (never on call counts, #2850 lot 10's retry lesson).

#: row 1 — a direct, ironic assertion the frameless descent reads as an
#: association: the irony marker sits in the sentence BEFORE the unit.
DOC_A = (
    "Un remplissage quelconque ouvre le document. "
    "Et c'est là l'ironie complète : le directeur en personne saisit les "
    "terrains communaux. Une phrase suit pour fermer."
)
UNIT_A = "le directeur en personne saisit les terrains communaux"
MARKER_A = "l'ironie complète"
LEAF_A_PK = "411"  # Amalgame par association

#: row 2 — a paraphrase that stripped the « peut »: the verbatim source
#: quote (which carries the modality) and the premise sit in the frame.
DOC_B = (
    "Si la trempe tient l'épreuve, l'acier rouillé peut être réemployé "
    "pour la charpente. Le bureau validera le protocole."
)
SOURCE_QUOTE_B = "l'acier rouillé peut être réemployé pour la charpente"
UNIT_B = "l'acier rouillé est réemployé sans fin"  # the paraphrase (the unit)
MARKER_B = "peut être réemployé"  # in the source quote, never in the unit
LEAF_B_PK = "412"  # Répétition mécanique

#: row 3 — an alternative whose second branch is refused in the sentence
#: AFTER the unit: the denial is not a defence of the other branch.
DOC_C = (
    "Une phrase d'ouverture banale. Soit l'usine ferme, soit elle continue "
    "de rejeter. Refuser la fermeture n'est pas défendre le rejet : la "
    "filière capture les effluents."
)
UNIT_C = "Soit l'usine ferme, soit elle continue de rejeter"
MARKER_C = "n'est pas défendre le rejet"
LEAF_C_PK = "421"  # Faux dilemme

#: row 4 — a conditional the frameless descent reads as an accusation: the
#: hypothetical frame sits in the sentence BEFORE the unit.
DOC_D = (
    "À supposer que le texte passe la commission, ce serait un acte de "
    "censure que personne ne pourrait cautionner. Le dossier suit son cours."
)
UNIT_D = "ce serait un acte de censure que personne ne pourrait cautionner"
MARKER_D = "À supposer que le texte passe la commission"
LEAF_D_PK = "422"  # Interprétation excessive

_ROWS = {
    "a": (DOC_A, UNIT_A, MARKER_A, LEAF_A_PK, None),
    "b": (DOC_B, UNIT_B, MARKER_B, LEAF_B_PK, SOURCE_QUOTE_B),
    "c": (DOC_C, UNIT_C, MARKER_C, LEAF_C_PK, None),
    "d": (DOC_D, UNIT_D, MARKER_D, LEAF_D_PK, None),
}


def _row(key):
    doc, unit, marker, leaf_pk, source_quote = _ROWS[key]
    offset = doc.index(source_quote if source_quote else unit)
    return doc, unit, marker, leaf_pk, offset, source_quote


def _frame_for(key):
    """The REAL producer's frame for one row (lazy import: born-red on the
    pre-fix tree must fail at the call, not at collection)."""
    from argumentation_analysis.agents.core.reading.first_reading import (
        document_frame_for_unit,
    )

    doc, unit, marker, leaf_pk, offset, source_quote = _row(key)
    state = SimpleNamespace(raw_text=doc)
    return document_frame_for_unit(
        state, unit_text=unit, offset=offset, source_quote=source_quote
    )


#: The misread justification each row's descent produced when it saw the
#: unit alone — the shape of the measured M2 items, not their words.
_MISREAD_JUSTIFICATIONS = {
    "a": "le texte suggère une association entre le directeur et la saisie",
    "b": "répétition mécanique du procédé, aucune prémisse énoncée",
    "c": "l'alternative est fermée et le locuteur défend l'un des deux bords",
    "d": "le locuteur accuse la commission d'un acte de censure",
}

_REFUSAL_JUSTIFICATIONS = {
    "a": "l'ironie affichée dit une assertion directe, pas une association",
    "b": "le document dit « peut », sous la prémisse qu'il énonce avant",
    "c": "le refus de la fermeture n'est pas la défense du rejet",
    "d": "le cadre est conditionnel : une hypothèse, pas une accusation",
}


def _taxonomy():
    """Two branches, four leaves — one per measured row."""
    rows = [
        (1, "4", "4", "Erreur de raisonnement", "root"),
        (2, "4.1", "41", "Association", "sub"),
        (
            3,
            "4.1.1",
            LEAF_A_PK,
            "Amalgame par association",
            "Une association suggérée.",
        ),
        (
            3,
            "4.1.2",
            LEAF_B_PK,
            "Répétition mécanique",
            "Une répétition sans prémisse.",
        ),
        (2, "4.2", "42", "Structure", "sub"),
        (3, "4.2.1", LEAF_C_PK, "Faux dilemme", "Une alternative fermée."),
        (
            3,
            "4.2.2",
            LEAF_D_PK,
            "Interprétation excessive",
            "Lire plus que ce qui est dit.",
        ),
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


def _slave_kernel_stub():
    class _FakePlugin:
        def __contains__(self, name):
            return True

        def __getitem__(self, name):
            return MagicMock()

    kernel = create_autospec(Kernel, instance=True)
    kernel.plugins = {"Exploration": _FakePlugin()}
    return kernel


def _msg_with_items(*items):
    return [SimpleNamespace(items=list(items))]


def _confirm_call(node_pk, matches=True, justification="", **extra):
    args = {
        "node_pk": node_pk,
        "justification": justification,
        "confidence": "high",
        "matches": matches,
    }
    args.update(extra)
    return FunctionCallContent(name="confirm_fallacy", arguments=json.dumps(args))


def _conclude_call(reason="pas ce sophisme"):
    return FunctionCallContent(
        name="conclude_no_fallacy", arguments=json.dumps({"reason": reason})
    )


def _install_llm_keyed_on_frame(marker, misread, refusal, seen):
    """Script the descent's LLM on the PROMPT'S CONTENT and snapshot prompts.

    The contract is the measured defect, not a count: a model that sees no
    window reads the unit the way the panel measured (the misread
    confirmation); shown the frame, it refuses citing it. Keying on the
    marker makes the witness insensitive to retries and to prompt order.
    """

    async def _call(chat_history=None, settings=None, kernel=None, **kwargs):
        # The last message is the user prompt the model is shown (the
        # history also carries the system message — #3416's snapshot rule).
        prompt = chat_history.messages[-1].content or ""
        seen.append(prompt)
        if marker not in prompt:
            return _msg_with_items(misread)
        return _msg_with_items(refusal)

    return _call


# --- the producer: the frame is located, never invented ---------------------


class TestTheFrameIsLocated:
    """``first_reading.document_frame_for_unit`` — one window per row."""

    def test_row_a_carries_the_irony_frame_before_the_unit(self):
        frame = _frame_for("a")
        assert MARKER_A in frame["before"]
        assert "source_quote" not in frame  # verbatim segment: no paraphrase

    def test_row_a_carries_the_next_sentence_after_the_unit(self):
        frame = _frame_for("a")
        assert "Une phrase suit pour fermer" in frame["after"]

    def test_row_b_carries_the_verbatim_quote_a_paraphrase_restates(self):
        frame = _frame_for("b")
        assert frame["source_quote"] == SOURCE_QUOTE_B
        assert "peut" in frame["source_quote"]
        assert "Si la trempe" in frame["before"]  # the premise, before the quote

    def test_row_c_carries_the_denial_after_the_unit(self):
        frame = _frame_for("c")
        assert MARKER_C in frame["after"]

    def test_row_d_carries_the_conditional_frame_before_the_unit(self):
        frame = _frame_for("d")
        assert MARKER_D in frame["before"]

    def test_no_offset_or_no_text_means_no_window(self):
        from argumentation_analysis.agents.core.reading.first_reading import (
            document_frame_for_unit,
        )

        doc, unit, marker, leaf_pk, offset, source_quote = _row("a")
        state = SimpleNamespace(raw_text=doc)
        assert document_frame_for_unit(state, unit_text=unit, offset=None) == {}
        assert (
            document_frame_for_unit(
                SimpleNamespace(raw_text=""), unit_text=unit, offset=offset
            )
            == {}
        )
        assert document_frame_for_unit(state, unit_text=unit, offset=len(doc) + 5) == {}
        # a bool is not an offset (#1019 tri-state rule)
        assert document_frame_for_unit(state, unit_text=unit, offset=True) == {}

    def test_a_document_without_boundaries_keeps_a_bounded_frame(self):
        """A « sentence » that runs for pages must not ride whole: the cap
        keeps the side ADJACENT to the unit (FRAME_CONTEXT_MAX_CHARS)."""
        from argumentation_analysis.agents.core.reading.first_reading import (
            FRAME_CONTEXT_MAX_CHARS,
            document_frame_for_unit,
        )

        long_prefix = "mot " * 400  # no punctuation, ~1600 chars
        doc = long_prefix + "Et c'est là l'ironie complète : " + UNIT_A + ". Fin."
        offset = doc.index(UNIT_A)
        frame = document_frame_for_unit(
            SimpleNamespace(raw_text=doc), unit_text=UNIT_A, offset=offset
        )
        assert len(frame["before"]) <= FRAME_CONTEXT_MAX_CHARS
        assert len(frame["before"]) < len(
            doc[:offset].strip()
        ), "the unbounded « sentence » rode whole — the cap did not cut it"
        # the side ADJACENT to the unit is kept (the cap keeps the tail)
        assert frame["before"].endswith("l'ironie complète :")


# --- the wrapper: provenance decides, never a text search --------------------


class TestTheWrapperReadsProvenance:
    """``invoke_callables._document_frame_for_unit`` — offsets and the
    source quote come from ``argument_provenance``."""

    def _wrapper(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _document_frame_for_unit,
        )

        return _document_frame_for_unit

    def _state(self, entry=None):
        return SimpleNamespace(raw_text=DOC_B, argument_provenance=entry or {})

    def test_the_paraphrase_unit_gets_its_frame(self):
        doc, unit, marker, leaf_pk, offset, source_quote = _row("b")
        wrapper = self._wrapper()
        state = SimpleNamespace(
            raw_text=doc,
            argument_provenance={
                "arg_6": {
                    "producer": "llm_extract",
                    "offset": offset,
                    "source_quote": source_quote,
                }
            },
        )
        frame = wrapper(state, "arg_6", unit)
        assert frame["source_quote"] == source_quote
        assert "Si la trempe" in frame["before"]

    def test_no_state_no_provenance_no_offset_is_no_window(self):
        wrapper = self._wrapper()
        doc, unit, marker, leaf_pk, offset, source_quote = _row("b")
        assert wrapper(None, "arg_6", unit) == {}
        assert wrapper(self._state(), "arg_6", unit) == {}
        # an entry without an offset is named, never defaulted to 0
        state = self._state({"arg_6": {"producer": "llm_extract"}})
        assert wrapper(state, "arg_6", unit) == {}

    def test_a_verbatim_unit_still_gets_before_and_after(self):
        wrapper = self._wrapper()
        doc, unit, marker, leaf_pk, offset, source_quote = _row("a")
        state = SimpleNamespace(
            raw_text=doc, argument_provenance={"arg_4": {"offset": offset}}
        )
        frame = wrapper(state, "arg_4", unit)
        assert MARKER_A in frame["before"]
        assert "source_quote" not in frame


# --- the descent: one witness pair per measured row --------------------------


class TestTheDescentReadsTheFrame:
    """The real descent, LLM dependency mocked (#1097).

    Each row is a PAIR: the « without the window » companion runs on the
    pre-fix tree and documents the measured misread (the fake model
    confirms the very justification the panel counted as M2); the
    « with the window » witness is born red on the pre-fix tree (the
    ``document_frame`` argument does not exist there) and green once the
    frame and the as-stated instruction ride. Same fake, same unit — only
    the window differs.
    """

    def _run_descent(self, key, with_frame, seen):
        plugin = _plugin()
        doc, unit, marker, leaf_pk, offset, source_quote = _row(key)
        plugin.llm_service.get_chat_message_contents = _install_llm_keyed_on_frame(
            marker,
            _confirm_call(
                leaf_pk, matches=True, justification=_MISREAD_JUSTIFICATIONS[key]
            ),
            _confirm_call(
                leaf_pk, matches=False, justification=_REFUSAL_JUSTIFICATIONS[key]
            ),
            seen,
        )
        kwargs = {}
        if with_frame:
            kwargs["document_frame"] = _frame_for(key)
        return plugin._explore_single_branch(
            argument_text=unit,
            start_pk=leaf_pk,
            slave_kernel=_slave_kernel_stub(),
            slave_settings=MagicMock(),
            **kwargs,
        )

    # row 1 — amalgam: the grammatical subject

    @pytest.mark.asyncio
    async def test_row_a_with_the_window_the_association_is_refused(self):
        seen = []
        result = await self._run_descent("a", with_frame=True, seen=seen)
        assert MARKER_A in seen[-1], "the irony frame did not reach the prompt"
        assert "AS-STATED JUDGMENT" in seen[-1]
        assert result is None, "the misread attribution was confirmed through the frame"

    @pytest.mark.asyncio
    async def test_row_a_without_the_window_the_fake_model_misreads(self):
        """Companion, green before AND after the fix: the same fake model,
        shown no window, confirms the association — the flip is the window's,
        not the fake's."""
        seen = []
        result = await self._run_descent("a", with_frame=False, seen=seen)
        assert MARKER_A not in seen[-1]
        assert result is not None and result.taxonomy_pk == LEAF_A_PK
        assert "association" in result.explanation

    # row 2 — the modality a paraphrase stripped

    @pytest.mark.asyncio
    async def test_row_b_with_the_window_the_mechanism_is_not_mechanical(self):
        seen = []
        result = await self._run_descent("b", with_frame=True, seen=seen)
        assert MARKER_B in seen[-1], "the verbatim « peut » did not reach the prompt"
        assert result is None

    @pytest.mark.asyncio
    async def test_row_b_without_the_window_the_fake_model_misreads(self):
        seen = []
        result = await self._run_descent("b", with_frame=False, seen=seen)
        assert result is not None and result.taxonomy_pk == LEAF_B_PK

    # row 3 — the structure of the alternative

    @pytest.mark.asyncio
    async def test_row_c_with_the_window_the_dilemma_is_not_closed(self):
        seen = []
        result = await self._run_descent("c", with_frame=True, seen=seen)
        assert MARKER_C in seen[-1], "the denial sentence did not reach the prompt"
        assert result is None

    @pytest.mark.asyncio
    async def test_row_c_without_the_window_the_fake_model_misreads(self):
        seen = []
        result = await self._run_descent("c", with_frame=False, seen=seen)
        assert result is not None and result.taxonomy_pk == LEAF_C_PK

    # row 4 — the conditional frame

    @pytest.mark.asyncio
    async def test_row_d_with_the_window_the_conditional_is_not_an_accusation(self):
        seen = []
        result = await self._run_descent("d", with_frame=True, seen=seen)
        assert MARKER_D in seen[-1], "the conditional frame did not reach the prompt"
        assert result is None

    @pytest.mark.asyncio
    async def test_row_d_without_the_window_the_fake_model_misreads(self):
        seen = []
        result = await self._run_descent("d", with_frame=False, seen=seen)
        assert result is not None and result.taxonomy_pk == LEAF_D_PK


# --- the descent's other prompts, and the fallback ---------------------------


class TestEveryPromptCarriesTheSameFrame:
    """The leaf, the navigation and the one-shot fallback — one contract
    (#3416's rule: a unit must not get a different window because the
    descent took another path)."""

    @pytest.mark.asyncio
    async def test_the_navigation_prompt_carries_the_frame_too(self):
        plugin = _plugin()
        seen = []

        async def _call(chat_history=None, settings=None, kernel=None, **kwargs):
            seen.append("\n".join(m.content or "" for m in chat_history.messages))
            return _msg_with_items(_conclude_call())

        plugin.llm_service.get_chat_message_contents = _call
        await plugin._explore_single_branch(
            argument_text=UNIT_A,
            start_pk="41",  # a node WITH children: the first call navigates
            slave_kernel=_slave_kernel_stub(),
            slave_settings=MagicMock(),
            document_frame=_frame_for("a"),
        )
        assert MARKER_A in seen[0]
        assert "AS-STATED JUDGMENT" in seen[0]

    @pytest.mark.asyncio
    async def test_the_one_shot_prompt_carries_the_frame_too(self):
        plugin = _plugin()
        seen = []

        async def _call_content(
            chat_history=None, settings=None, kernel=None, **kwargs
        ):
            seen.append("\n".join(m.content or "" for m in chat_history.messages))
            return json.dumps(
                {"fallacy_name": "", "explanation": "rien"}, ensure_ascii=False
            )

        plugin.llm_service.get_chat_message_content = _call_content
        await plugin._run_one_shot(UNIT_A, [], document_frame=_frame_for("a"))
        assert MARKER_A in seen[0]
        assert "AS-STATED JUDGMENT" in seen[0]

    @pytest.mark.asyncio
    async def test_no_frame_leaves_the_leaf_prompt_byte_identical(self):
        """The DoD control, byte for byte: with no frame (None, an empty
        record, a blank one) the leaf prompt is the pre-#3428 string — same
        prefix, no block, no instruction — and the three absences are
        identical to each other."""
        captured = []
        for frame in (None, {}, {"before": "   ", "after": "", "source_quote": " "}):
            plugin = _plugin()
            seen = []
            plugin.llm_service.get_chat_message_contents = _install_llm_keyed_on_frame(
                MARKER_A, _confirm_call(LEAF_A_PK), _conclude_call(), seen
            )
            await plugin._explore_single_branch(
                argument_text=UNIT_A,
                start_pk=LEAF_A_PK,
                slave_kernel=_slave_kernel_stub(),
                slave_settings=MagicMock(),
                document_frame=frame,
            )
            captured.append(seen[-1])
        for prompt in captured:
            assert prompt.startswith(
                f'Text to analyze: "{UNIT_A}"\n\n'
                "You reached a LEAF node in the fallacy taxonomy.\n"
            ), "the no-frame prompt no longer opens with the pre-#3428 text"
            assert "THE DOCUMENT AROUND THIS UNIT" not in prompt
            assert "AS-STATED JUDGMENT" not in prompt
        assert captured[0] == captured[1] == captured[2], (
            "an empty or blank frame changed the prompt — absence must be "
            "byte-identical to no argument at all"
        )

    @pytest.mark.asyncio
    async def test_no_frame_leaves_the_one_shot_prompt_byte_identical(self):
        captured = []
        for frame in (None, {}):
            plugin = _plugin()
            seen = []

            async def _call_content(
                chat_history=None, settings=None, kernel=None, **kwargs
            ):
                seen.append("\n".join(m.content or "" for m in chat_history.messages))
                return json.dumps({"fallacy_name": ""}, ensure_ascii=False)

            plugin.llm_service.get_chat_message_content = _call_content
            await plugin._run_one_shot(UNIT_A, [], document_frame=frame)
            captured.append(seen[0])
        assert captured[0] == captured[1]
        assert "THE DOCUMENT AROUND THIS UNIT" not in captured[0]
        assert "AS-STATED JUDGMENT" not in captured[0]


class TestTheFrameIsAQuestionNotAVeto:
    """Anti-pendulum: the fallacy rate is not bought down. A model that
    confirms whatever it is asked confirms THROUGH the frame — the
    instruction asks for the as-stated judgment, it does not refuse on the
    frame's behalf."""

    @pytest.mark.asyncio
    async def test_a_confirmation_stands_through_an_irrelevant_frame(self):
        plugin = _plugin()

        async def _call(chat_history=None, settings=None, kernel=None, **kwargs):
            return _msg_with_items(
                _confirm_call(
                    LEAF_A_PK,
                    matches=True,
                    justification="une association suggérée par la texte même",
                )
            )

        plugin.llm_service.get_chat_message_contents = _call
        result = await plugin._explore_single_branch(
            argument_text=UNIT_A,
            start_pk=LEAF_A_PK,
            slave_kernel=_slave_kernel_stub(),
            slave_settings=MagicMock(),
            document_frame=_frame_for("a"),
        )
        assert result is not None and result.taxonomy_pk == LEAF_A_PK

    @pytest.mark.asyncio
    async def test_a_real_fallacy_on_a_modal_claim_stays_a_fallacy(self):
        """The instruction's own negative case: a justification that NAMES
        the modality while confirming is the honest outcome, not a refusal
        to be forced by the plumbing."""
        plugin = _plugin()

        async def _call(chat_history=None, settings=None, kernel=None, **kwargs):
            return _msg_with_items(
                _confirm_call(
                    LEAF_B_PK,
                    matches=True,
                    justification="répétition affirmée sans prémisse même "
                    "possibilité gardée — le document dit « peut » et la "
                    "répétition porte quand même",
                )
            )

        plugin.llm_service.get_chat_message_contents = _call
        result = await plugin._explore_single_branch(
            argument_text=UNIT_B,
            start_pk=LEAF_B_PK,
            slave_kernel=_slave_kernel_stub(),
            slave_settings=MagicMock(),
            document_frame=_frame_for("b"),
        )
        assert result is not None and result.taxonomy_pk == LEAF_B_PK
