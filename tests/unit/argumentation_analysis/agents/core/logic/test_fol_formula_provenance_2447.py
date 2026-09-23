# -*- coding: utf-8 -*-
"""
#2447 (items 4, 7 and 8) — what ``FOLLogicAgent.analyze()`` reports is named
by where it came from.

On ``main``:

- item 4: when the LLM conversion failed, ``_basic_fol_conversion`` produced
  placeholder formulas (``P0(a)``, ``forall X: (P0(X) => Q0(X))``…) and the
  solver's verdict on them was reported as the verdict on the text. Nothing
  in the result said the formulas were not a translation;
- item 7: the ``analyze_fol`` step merged the model's ``inferences``,
  ``interpretations`` and ``errors`` into the solver's fields, unlabelled,
  and raised ``confidence_score`` to the model's self-rating (a ``max``);
- item 8: the LLM's formulas went to the solver without the sort and
  predicate declarations the FOL parser needs, so no LLM conversion was ever
  checked (measured with the real solver: "Illegal characters in sort
  definition").

No LLM is called: the kernel holds a fake chat service. No JVM: the bridge is
a double. The real-solver check of item 8 is in
``tests/integration/workers/test_worker_fol_tweety.py``.
"""

import json
from typing import Any, List

import semantic_kernel as sk
from semantic_kernel.connectors.ai.chat_completion_client_base import (
    ChatCompletionClientBase,
)
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent

from argumentation_analysis.agents.core.logic.fol_logic_agent import FOLLogicAgent

SERVICE_ID = "fol_provenance_2447"
TEXT = "Tous les hommes sont mortels. Socrate est un homme."
LLM_FORMULAS = ["forall X: (Homme(X) => Mortel(X))", "Homme(socrate)"]

# What the model answers to the ``analyze_fol`` prompt, in the format that
# prompt asks for. Every value differs from what the solver double says.
MODEL_ASSESSMENT = {
    "consistency": False,
    "inferences": ["Inférence du modèle"],
    "interpretations": [{"description": "Modèle du modèle"}],
    "errors": ["Erreur signalée par le modèle"],
    "confidence": 0.99,
    "reasoning_steps": ["Étape du modèle"],
}


class _FakeChat(ChatCompletionClientBase):
    """Answers the conversion prompt with ``conversion`` and the analysis
    prompt with ``analysis``. Calls no LLM."""

    conversion: Any = None
    analysis: Any = None

    async def _inner_get_chat_message_contents(
        self, chat_history: ChatHistory, settings: Any
    ) -> List[ChatMessageContent]:
        prompt = str(chat_history)
        answer = self.conversion if "Convertis" in prompt else self.analysis
        return [
            ChatMessageContent(
                role="assistant", content=answer, ai_model_id=self.ai_model_id
            )
        ]


class _Bridge:
    """A bridge double answering one fixed consistency verdict."""

    def __init__(self, verdict):
        self.verdict = verdict
        self.calls = []

    def check_consistency(self, content: str, logic_type: str):
        self.calls.append((content, logic_type))
        return self.verdict


def _agent(bridge, conversion, analysis=MODEL_ASSESSMENT) -> FOLLogicAgent:
    kernel = sk.Kernel()
    kernel.add_service(
        _FakeChat(
            ai_model_id="fake-2447",
            service_id=SERVICE_ID,
            conversion=conversion,
            analysis=json.dumps(analysis),
        )
    )
    return FOLLogicAgent(kernel=kernel, service_id=SERVICE_ID, tweety_bridge=bridge)


# ---------------------------------------------------------------------------
# Item 4 — the heuristic's formulas
# ---------------------------------------------------------------------------


async def test_heuristic_formulas_are_named_and_get_no_verdict():
    """The model answers the conversion in prose, so ``json.loads`` raises and
    the heuristic takes over. Its formulas are not sent to the solver."""
    bridge = _Bridge((True, "consistent"))
    result = await _agent(bridge, conversion="Voici les formules : …").analyze(TEXT)

    assert result.formulas, "the heuristic produced no formula"
    assert bridge.calls == [], "placeholder formulas were sent to the solver"
    assert result.consistency_check is None
    assert result.formulas_source == "heuristic"
    assert "JSONDecodeError" in result.conversion_message
    assert "heuristiques" in result.consistency_message
    assert "heuristique" in result.reasoning_steps[0]


# ---------------------------------------------------------------------------
# Item 8 — the LLM's formulas reach the solver with their signature
# ---------------------------------------------------------------------------


async def test_llm_formulas_reach_the_solver_with_their_signature():
    bridge = _Bridge((True, "consistent"))
    result = await _agent(
        bridge, conversion=json.dumps({"formulas": LLM_FORMULAS})
    ).analyze(TEXT)

    assert bridge.calls == [
        (
            "thing = {socrate}\n"
            "type(Homme(thing))\n"
            "type(Mortel(thing))\n"
            "\n"
            "forall X: (Homme(X) => Mortel(X))\n"
            "Homme(socrate)",
            "first_order",
        )
    ]
    assert result.consistency_check is True
    assert result.formulas == LLM_FORMULAS, "the result keeps the bare formulas"
    assert result.formulas_source == "llm"


# ---------------------------------------------------------------------------
# Item 7 — the model's answer writes none of the solver's fields
# ---------------------------------------------------------------------------


async def test_the_model_answer_writes_no_solver_field():
    bridge = _Bridge((True, "consistent"))
    result = await _agent(
        bridge, conversion=json.dumps({"formulas": LLM_FORMULAS})
    ).analyze(TEXT)

    # The solver's fields hold what the solver double said, and only that.
    assert result.consistency_check is True
    assert result.inferences == []
    assert result.interpretations == []
    assert result.validation_errors == []
    assert result.confidence_score == 0.8, "the model's 0.99 replaced the score"
    assert "Étape du modèle" not in result.reasoning_steps

    # The model's answer is kept as it came, and one step labels it.
    assert result.llm_assessment == MODEL_ASSESSMENT
    labelled = [s for s in result.reasoning_steps if "non vérifié par un solveur" in s]
    assert labelled == [
        "Avis du LLM (non vérifié par un solveur) : cohérence=False, "
        "1 inférence(s), 1 erreur(s) signalée(s)"
    ]


async def test_a_model_answer_that_is_not_an_object_is_kept_raw():
    bridge = _Bridge((True, "consistent"))
    result = await _agent(
        bridge,
        conversion=json.dumps({"formulas": LLM_FORMULAS}),
        analysis=["pas", "un", "objet"],
    ).analyze(TEXT)

    assert any("non vérifié par un solveur" in s for s in result.reasoning_steps)
    assert result.llm_assessment == {"raw": ["pas", "un", "objet"]}
    assert result.consistency_check is True
