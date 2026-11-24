# -*- coding: utf-8 -*-
"""#3679 item 40b — a fenced or prefixed FOL answer still reaches the formulas.

The band's first record run on the named Anthropic route (run 45351057154)
failed on ``test_worker_fol_tweety.py::TestFOLErrorHandling::test_fol_syntax_error_recovery``
with ``JSONDecodeError: Expecting value: line 1 column 1 (char 0)``.

Root cause, read on the code:

- ``FOLLogicAgent._convert_to_fol`` parsed the LLM answer with
  ``json.loads(str(result))`` (``fol_logic_agent.py:449``), and
  ``_llm_enhanced_analysis`` the same way (``:994``).
- Its modal and propositional siblings first go through
  ``_extract_json_block`` (``modal_logic_agent.py:387``,
  ``propositional_logic_agent.py:390``).
- The route sends **no JSON mode** (#3600 / #3096 family), so nothing forces
  the model to emit a bare object: a Haiku answer arrives fenced in a
  ```json block or preceded by a sentence, and the raw ``json.loads`` dies on
  its first character. The caller then reports the failed-conversion message
  instead of the real answer.

The fix applies the **common base** of the two sibling extractors — a fenced
```json block, else the first ``{`` .. last ``}``, else the whole string — at
both FOL sites. The siblings are **not** modified: the modal extractor also
repairs truncations (it counts braces and completes an unclosed
``modal_formulas`` array), the propositional one does not, so they are not
equivalent and this item does not merge them. The difference is documented
in ``_extract_json_block`` of the FOL agent.

Witnesses are born red on the pre-fix head: with a fenced or prefixed answer,
the conversion must still return the model's formulas with ``reason is None``
(the LLM path), and the analysis must still record its assessment. A bare
JSON answer is the green control, before and after.

**No LLM, no JVM, no network, no corpus.** A real ``sk.Kernel``, a real agent
built by ``LogicAgentFactory``, and a fake chat-completion service that
answers a fabricated string. All texts are made up for this file; none comes
from the encrypted dataset, and no refused cassette string is reproduced
here.
"""

from __future__ import annotations

import json
from typing import Any, List

import pytest
import semantic_kernel as sk
from pydantic import Field
from semantic_kernel.connectors.ai.chat_completion_client_base import (
    ChatCompletionClientBase,
)
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent

from argumentation_analysis.agents.core.logic.fol_logic_agent import FOLLogicAgent
from argumentation_analysis.agents.core.logic.logic_factory import LogicAgentFactory

SERVICE_ID = "default_logic_llm_3679_40b"

# Fabricated formulas — no corpus text, no cassette content.
FORMULA_1 = "forall X: (Gravat(X) => Refus(X))"
FORMULA_2 = "Gravat(depot_nord)"

# The five answer shapes a route without JSON mode can produce.
BARE = json.dumps({"formulas": [FORMULA_1, FORMULA_2]})
FENCED = f"```json\n{BARE}\n```"
FENCED_NO_LANG = f"```\n{BARE}\n```"
PREFIXED = f"Voici la conversion demandée.\n{BARE}"
PREFIXED_AND_FENCED = f"Voici la conversion demandée.\n{FENCED}"

CONVERSION_SHAPES = {
    "fenced": FENCED,
    "fenced_no_lang": FENCED_NO_LANG,
    "prefixed": PREFIXED,
    "prefixed_and_fenced": PREFIXED_AND_FENCED,
}


class ScriptedChatCompletion(ChatCompletionClientBase):
    """Fake chat service: answers a scripted string, records every prompt.

    No LLM is called. ``answer`` is what the model would have returned on a
    route that sends no JSON mode.
    """

    answer: str = BARE
    rendered_prompts: List[str] = Field(default_factory=list)

    async def _inner_get_chat_message_contents(
        self, chat_history: ChatHistory, settings: Any
    ) -> List[ChatMessageContent]:
        self.rendered_prompts.append(
            "\n".join(str(message) for message in chat_history.messages)
        )
        return [
            ChatMessageContent(
                role="assistant",
                content=self.answer,
                ai_model_id=self.ai_model_id,
            )
        ]


def _agent_with_answer(answer: str) -> tuple[FOLLogicAgent, ScriptedChatCompletion]:
    """A real FOL agent, configured through its own sync setup, on a fake
    service that will answer ``answer``."""
    kernel = sk.Kernel()
    service = ScriptedChatCompletion(
        ai_model_id="fake-model-3679-40b", service_id=SERVICE_ID, answer=answer
    )
    kernel.add_service(service)
    agent = LogicAgentFactory.create_agent("first_order", kernel)
    assert agent is not None, "the factory could not build the FOL agent"
    agent.setup_agent_components(llm_service_id=SERVICE_ID)
    plugin = kernel.plugins.get("fol_logic")
    assert plugin is not None, "the sync setup did not register the fol_logic plugin"
    return agent, service


class TestConversionReachesTheFormulas:
    """Born red: a fenced or prefixed conversion answer must not fall back to
    the heuristic converter."""

    @pytest.mark.parametrize("shape", sorted(CONVERSION_SHAPES))
    async def test_a_decorated_answer_still_yields_the_llm_formulas(
        self, shape: str
    ) -> None:
        agent, _service = _agent_with_answer(CONVERSION_SHAPES[shape])
        formulas, reason = await agent._convert_to_fol(
            "La commission refuse le dépôt de gravats."
        )
        assert reason is None, (
            f"[{shape}] the LLM conversion was abandoned: {reason!r} — the raw "
            "json.loads died on the decoration and the heuristic converter "
            "took over"
        )
        assert (
            FORMULA_1 in formulas
        ), f"[{shape}] the model's formula did not survive: {formulas!r}"
        assert len(formulas) == 2, f"[{shape}] unexpected formulas: {formulas!r}"

    async def test_a_bare_answer_is_the_green_control(self) -> None:
        """Non-vacuity: the same harness passes on a bare JSON answer, before
        and after the fix. If this is red, the harness is at fault, not the
        extraction."""
        agent, _service = _agent_with_answer(BARE)
        formulas, reason = await agent._convert_to_fol(
            "La commission refuse le dépôt de gravats."
        )
        assert reason is None, f"control failed: {reason!r}"
        assert formulas == [FORMULA_1, FORMULA_2]

    async def test_the_fenced_answer_keeps_its_unicode_conversion(self) -> None:
        """The extracted formulas still go through the Tweety ASCII dialect:
        extracting a block must not bypass ``unicode_to_ascii_fol``."""
        answer = (
            "Voici les formules.\n```json\n"
            + json.dumps({"formulas": ["∀X: (Homme(X) → Mortel(X))"]})
            + "\n```"
        )
        agent, _service = _agent_with_answer(answer)
        formulas, reason = await agent._convert_to_fol("Tous les hommes sont mortels.")
        assert reason is None, f"the conversion was abandoned: {reason!r}"
        assert formulas == ["forall X: (Homme(X) => Mortel(X))"], formulas


class TestAnalysisReachesItsAssessment:
    """The second raw ``json.loads`` (``:994``) has the same defect: a fenced
    analysis answer must still land in ``llm_assessment``."""

    @pytest.mark.parametrize(
        "shape,answer",
        [
            (
                "fenced",
                "```json\n"
                + json.dumps({"consistency": True, "inferences": ["Mortel(socrate)"]})
                + "\n```",
            ),
            (
                "prefixed",
                "Analyse terminée.\n"
                + json.dumps({"consistency": True, "inferences": ["Mortel(socrate)"]}),
            ),
        ],
    )
    async def test_a_decorated_analysis_is_recorded(
        self, shape: str, answer: str
    ) -> None:
        agent, _service = _agent_with_answer(answer)
        # A real result object built the way the module builds it.
        from argumentation_analysis.agents.core.logic.fol_logic_agent import (
            FOLAnalysisResult,
        )

        result = FOLAnalysisResult(formulas=[FORMULA_1])
        outcome = await agent._llm_enhanced_analysis(
            result, "Tous les hommes sont mortels."
        )
        assert outcome is not None, (
            f"[{shape}] the analysis was dropped: the raw json.loads died on "
            "the decoration and the except returned None"
        )
        assessment = outcome.llm_assessment or {}
        assert assessment.get("consistency") is True, (
            f"[{shape}] the model's assessment did not reach the record: "
            f"{assessment!r}"
        )


class TestTheExtractorItself:
    """Unit witnesses on the common base, including the two limits that must
    stay honest: a truncated object is not silently repaired (that is the
    modal sibling's behaviour, not this base's), and a brace-less answer is
    handed over whole so ``json.loads`` reports it."""

    def test_fenced_block_is_preferred_over_a_brace_in_the_prose(self) -> None:
        agent, _service = _agent_with_answer(BARE)
        answer = "Le délimiteur { n'est pas du JSON.\n```json\n" + BARE + "\n```"
        block = agent._extract_json_block(answer)
        assert json.loads(block)["formulas"] == [FORMULA_1, FORMULA_2]

    def test_a_brace_less_answer_is_returned_whole(self) -> None:
        agent, _service = _agent_with_answer(BARE)
        answer = "Aucune formule n'a pu être produite."
        assert agent._extract_json_block(answer) == answer

    def test_a_truncated_object_is_not_silently_completed(self) -> None:
        """The base does not invent the missing tail: it hands over what is
        there, and ``json.loads`` stays the one that decides. The modal
        sibling's repair is a different contract, deliberately not copied."""
        agent, _service = _agent_with_answer(BARE)
        truncated = '{"formulas": ["forall X: (P(X)"'
        block = agent._extract_json_block(truncated)
        with pytest.raises(json.JSONDecodeError):
            json.loads(block)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
