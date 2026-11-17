"""#3557 — the frame carries the turn's speaker tag, wherever it sits.

Cycle 7 of the panel measured the residue #3428 left: on a dialogue whose
turns are marked by speaker tags, the frame's sentence-bounded window (one
sentence before, two ends after — #3452) can hold NO tag at all. On the
severe unit the turn's tag sat 185 characters before the unit while the
frame's ``before`` reached back 92 — the descent read a reply with no idea
who speaks it, attributed it to the addressed party, and Act II printed
the misattribution verbatim.

The fix is evidence again, not a new call: the producer scans the
sentence starts BACKWARD from the unit's own sentence for the first
sentence that opens on a speaker tag (the #3623 form the splitter already
reads — ``NOM:`` + its reply governs its own turn; a bare ``NOM.`` opens
the FOLLOWING one), and FORWARD for the answering turn's tag. The two
tags ride as their own short parts; the sentence window itself is NOT
widened (#3428's own lesson: a wider cut only moves the problem). The
as-stated instruction gains the attribution case, appended only when a
tag rides — a document no tag rule fires on keeps the pre-#3557 prompt
byte for byte (#3416).

Born red on ``main`` at the assertions, not at collection: the
``document_frame`` argument exists there (#3428); what does not exist is
the tag in the frame and the attribution in the prompt.

Privacy: invented filler, invented speaker names, opaque ids, no corpus
text. Deterministic: no JVM, no LLM call (the descent's LLM dependency is
mocked, #1097), no network.
"""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, create_autospec

import pytest
from semantic_kernel import Kernel
from semantic_kernel.contents import FunctionCallContent

from argumentation_analysis.plugins.exploration_plugin import ExplorationPlugin

# --- fixtures: a dialogue whose tags sit OUTSIDE the sentence window ---------

#: A four-sentence turn: the unit is the turn's FOURTH sentence, so the
#: #3452 window (one sentence before) starts at the third — the tag that
#: opened the turn is OUTSIDE it, the measured shape of the cycle-7 unit
#: (tag 185 characters before the unit, window reaching 92 back).
TAG_A = "PREMIER ORATEUR:"
TAG_B = "SECOND ORATEUR:"
DOC_DIALOGUE = (
    "PREMIER ORATEUR: La première phrase de la réplique ouvre le tour et "
    "annonce la couleur du débat. La deuxième phrase développe l'argument "
    "en l'étayant d'un exemple que personne ne conteste. La troisième "
    "phrase conclut la réplique en répétant l'accusation sans preuve. "
    "La quatrième phrase porte l'unité lue par la descente, collée au "
    "reste du tour. "
    "SECOND ORATEUR: La réplique qui répond refuse l'accusation et en "
    "nomme l'auteur par son titre dans la phrase même."
)
UNIT_DIALOGUE = "La quatrième phrase porte l'unité lue par la descente"
THIRD_SENTENCE = (
    "La troisième phrase conclut la réplique en répétant l'accusation sans preuve."
)

#: The byte-for-byte control: a document no tag rule fires on (#3416).
DOC_MONOLOGUE = (
    "Une phrase d'ouverture sans étiquette aucune. La phrase suivante "
    "porte l'unité lue par la descente, dans le fil du monologue. Une "
    "dernière phrase referme le document sans répondre à personne."
)
UNIT_MONOLOGUE = "La phrase suivante porte l'unité lue par la descente"

LEAF_PK = "431"  # Appel à l'autorité (any leaf serves: the frame rides for all)


def _frame_for(doc: str, unit: str):
    """The REAL producer's frame (lazy import: the witness reads the
    production code, not a copy of its output)."""
    from argumentation_analysis.agents.core.reading.first_reading import (
        document_frame_for_unit,
    )

    return document_frame_for_unit(
        SimpleNamespace(raw_text=doc), unit_text=unit, offset=doc.index(unit)
    )


# --- the producer: the tag rides, the window does not move -------------------


class TestTheFrameCarriesTheTurnTags:
    """``document_frame_for_unit`` — the tags ride as their own parts."""

    def test_the_units_own_speaker_tag_rides_outside_the_window(self):
        """Born red on ``main``: the tag sat outside the sentence window
        and no part carried it — the measured defect."""
        frame = _frame_for(DOC_DIALOGUE, UNIT_DIALOGUE)
        assert frame.get("speaker") == TAG_A, (
            "the turn's speaker tag did not ride: the descent reads the "
            "unit with no idea who speaks it"
        )
        # the window itself is NOT widened: the tag reached by the fix is
        # still absent from the before part (it rode as its own part).
        assert TAG_A not in frame.get("before", "")

    def test_the_answering_turns_tag_rides_too(self):
        frame = _frame_for(DOC_DIALOGUE, UNIT_DIALOGUE)
        assert frame.get("next_speaker") == TAG_B

    def test_the_sentence_window_stands_as_it_was(self):
        """The #3452 window keeps its rule — the fix did not widen the
        cut (#3428's own lesson: a wider window only moves the problem)."""
        frame = _frame_for(DOC_DIALOGUE, UNIT_DIALOGUE)
        assert (
            frame["before"] == THIRD_SENTENCE
        ), "the before part changed: the window moved, not just the tags"

    def test_a_monologue_keeps_the_pre_3557_parts_byte_for_byte(self):
        """The #3416 convention: a document no tag rule fires on changes
        nothing — the parts are the pre-#3557 ones and nothing else."""
        frame = _frame_for(DOC_MONOLOGUE, UNIT_MONOLOGUE)
        assert set(frame.keys()) == {"before", "after"}

    def test_no_offset_still_means_no_frame(self):
        from argumentation_analysis.agents.core.reading.first_reading import (
            document_frame_for_unit,
        )

        assert (
            document_frame_for_unit(
                SimpleNamespace(raw_text=DOC_DIALOGUE),
                unit_text=UNIT_DIALOGUE,
                offset=None,
            )
            == {}
        )


# --- the descent's prompt: the tag block and the attribution rule ------------


def _taxonomy():
    """One leaf — the frame rides on every node, the family is irrelevant."""
    data = []
    for depth, path, pk, text_fr, desc in [
        (1, "4", "4", "Erreur de raisonnement", "root"),
        (2, "4.3", "43", "Autorité", "sub"),
        (3, "4.3.1", LEAF_PK, "Appel à l'autorité", "Invoquer qui parle."),
    ]:
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


def _capture_llm(seen):
    """Snapshot every prompt; the model concludes — the witness reads the
    prompt, not the verdict."""

    async def _call(chat_history=None, settings=None, kernel=None, **kwargs):
        seen.append("\n".join(m.content or "" for m in chat_history.messages))
        return [
            SimpleNamespace(
                items=[
                    FunctionCallContent(
                        name="conclude_no_fallacy",
                        arguments=json.dumps({"reason": "rien à confirmer"}),
                    )
                ]
            )
        ]

    return _call


class TestTheDescentPromptSettlesAttribution:
    """The leaf prompt carries the tags and the attribution case."""

    @pytest.mark.asyncio
    async def test_the_leaf_prompt_carries_the_tag_and_the_rule(self):
        """Born red on ``main``: the frame argument exists, but the tag
        lines and the SPEAKER ATTRIBUTION clause do not."""
        plugin = _plugin()
        seen = []
        plugin.llm_service.get_chat_message_contents = _capture_llm(seen)
        await plugin._explore_single_branch(
            argument_text=UNIT_DIALOGUE,
            start_pk=LEAF_PK,
            slave_kernel=_slave_kernel_stub(),
            slave_settings=MagicMock(),
            document_frame=_frame_for(DOC_DIALOGUE, UNIT_DIALOGUE),
        )
        prompt = seen[-1]
        assert (
            f"« {TAG_A} »" in prompt
        ), "the unit's own speaker tag did not reach the prompt"
        assert (
            f"« {TAG_B} »" in prompt
        ), "the answering turn's tag did not reach the prompt"
        assert (
            "SPEAKER ATTRIBUTION" in prompt
        ), "the as-stated instruction carries no attribution case"
        assert "AS-STATED JUDGMENT" in prompt  # the #3428 rule stands unchanged

    @pytest.mark.asyncio
    async def test_a_monologue_prompt_keeps_the_pre_3557_instruction(self):
        """The #3416 convention, byte for byte: a document no tag rule
        fires on keeps the pre-#3557 instruction — the attribution clause
        is appended ONLY when a tag rides."""
        plugin = _plugin()
        seen = []
        plugin.llm_service.get_chat_message_contents = _capture_llm(seen)
        await plugin._explore_single_branch(
            argument_text=UNIT_MONOLOGUE,
            start_pk=LEAF_PK,
            slave_kernel=_slave_kernel_stub(),
            slave_settings=MagicMock(),
            document_frame=_frame_for(DOC_MONOLOGUE, UNIT_MONOLOGUE),
        )
        prompt = seen[-1]
        assert "AS-STATED JUDGMENT" in prompt  # the frame still rides
        assert "SPEAKER ATTRIBUTION" not in prompt
        assert "speaker tag of the turn" not in prompt

    @pytest.mark.asyncio
    async def test_the_one_shot_prompt_carries_the_tag_too(self):
        """Same contract on the one-shot fallback (#3416: one frame, every
        path)."""
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
        await plugin._run_one_shot(
            UNIT_DIALOGUE, [], document_frame=_frame_for(DOC_DIALOGUE, UNIT_DIALOGUE)
        )
        prompt = seen[0]
        assert f"« {TAG_A} »" in prompt
        assert "SPEAKER ATTRIBUTION" in prompt


class TestTheInstructionIsAQuestionNotAVeto:
    """Anti-pendulum (#3428's, restated by the issue): no lower fallacy
    rate. A model that confirms through the tag-carrying frame keeps its
    confirmation — the attribution rule asks for the as-stated judgment,
    it does not refuse on the frame's behalf."""

    @pytest.mark.asyncio
    async def test_a_confirmation_stands_through_the_tag_carrying_frame(self):
        plugin = _plugin()

        async def _call(chat_history=None, settings=None, kernel=None, **kwargs):
            return [
                SimpleNamespace(
                    items=[
                        FunctionCallContent(
                            name="confirm_fallacy",
                            arguments=json.dumps(
                                {
                                    "node_pk": LEAF_PK,
                                    "justification": "l'autorité est invoquée par "
                                    "PREMIER ORATEUR lui-même, confirmation maintenue",
                                    "confidence": "high",
                                    "matches": True,
                                }
                            ),
                        )
                    ]
                )
            ]

        plugin.llm_service.get_chat_message_contents = _call
        result = await plugin._explore_single_branch(
            argument_text=UNIT_DIALOGUE,
            start_pk=LEAF_PK,
            slave_kernel=_slave_kernel_stub(),
            slave_settings=MagicMock(),
            document_frame=_frame_for(DOC_DIALOGUE, UNIT_DIALOGUE),
        )
        assert result is not None and result.taxonomy_pk == LEAF_PK

    @pytest.mark.asyncio
    async def test_a_refusal_names_the_attribution(self):
        """The honest outcome ask 2 names: the justification says WHO the
        frame gives the words to — the plumbing must carry such a refusal,
        not force or drop it."""
        plugin = _plugin()

        async def _call(chat_history=None, settings=None, kernel=None, **kwargs):
            return [
                SimpleNamespace(
                    items=[
                        FunctionCallContent(
                            name="confirm_fallacy",
                            arguments=json.dumps(
                                {
                                    "node_pk": LEAF_PK,
                                    "justification": "les mots sont ceux de "
                                    "PREMIER ORATEUR, pas de la partie interpellée",
                                    "confidence": "high",
                                    "matches": False,
                                }
                            ),
                        )
                    ]
                )
            ]

        plugin.llm_service.get_chat_message_contents = _call
        result = await plugin._explore_single_branch(
            argument_text=UNIT_DIALOGUE,
            start_pk=LEAF_PK,
            slave_kernel=_slave_kernel_stub(),
            slave_settings=MagicMock(),
            document_frame=_frame_for(DOC_DIALOGUE, UNIT_DIALOGUE),
        )
        assert result is None, "a refusal that names the attribution was dropped"
