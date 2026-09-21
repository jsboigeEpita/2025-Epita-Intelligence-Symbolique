# -*- coding: utf-8 -*-
"""
#2341 — `analyze_fallacies` doit faire entrer le texte analysé dans le prompt rendu.

Le template `prompt_analyze_fallacies_v3_tool_use` porte le slot `{{$input}}`.
`analyze_fallacies` construisait `KernelArguments(input=text)` dans une variable
morte, puis invoquait la fonction sémantique avec un second `KernelArguments`
portant le kwarg `text_to_analyze` — un nom que le template ne connaît pas. Le
slot restait non résolu : le LLM recevait la consigne d'analyse **sans**
l'argument à analyser, sans erreur ni dégradation nommée.

Le contrôle mesure la seule chose qui décide : **le prompt effectivement rendu et
envoyé au service**. Un service factice le capture ; l'assertion porte sur la
présence du texte analysé dans ce prompt.

⚠ Contrôle de non-vacuité (`test_identify_arguments_binding_is_the_witness`) :
le MÊME harnais doit passer sur `semantic_IdentifyArguments`, dont le binding est
correct (`input=text`, slot `{{$input}}`). Sans lui, un rouge mesurerait le
harnais — service mal branché, prompt jamais rendu — et non le défaut.

Le texte analysé est **fabriqué** (aucun extrait du corpus chiffré) et assez
singulier pour ne pouvoir apparaître dans le prompt autrement que par le slot.
"""

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

from argumentation_analysis.agents.core.informal.informal_agent import (
    InformalAnalysisAgent,
)

# Argument entièrement fabriqué pour ce test — pas un extrait du dataset.
FABRICATED_ARGUMENT = (
    "Le conseil municipal de Villeneuve-les-Tests doit rejeter le projet de "
    "passerelle piétonne, car son promoteur porte des chaussures jaunes."
)

SERVICE_ID = "test_prompt_capture_service"


class PromptCapturingChatCompletion(ChatCompletionClientBase):
    """Service de complétion factice qui archive chaque prompt rendu.

    Il n'appelle aucun LLM : il enregistre le `ChatHistory` que Semantic Kernel
    a construit à partir du template rendu, puis retourne une réponse JSON
    minimale que les appelants savent parser.
    """

    rendered_prompts: List[str] = Field(default_factory=list)

    async def _inner_get_chat_message_contents(
        self,
        chat_history: ChatHistory,
        settings: Any,
    ) -> List[ChatMessageContent]:
        self.rendered_prompts.append(
            "\n".join(str(message) for message in chat_history.messages)
        )
        return [
            ChatMessageContent(
                role="assistant",
                content=json.dumps({"sophismes": []}),
                ai_model_id=self.ai_model_id,
            )
        ]

    @property
    def last_prompt(self) -> str:
        assert self.rendered_prompts, (
            "Le service factice n'a capturé aucun prompt : la fonction sémantique "
            "n'a pas été invoquée. Le harnais est en cause, pas le binding."
        )
        return self.rendered_prompts[-1]


@pytest.fixture
def capturing_service() -> PromptCapturingChatCompletion:
    return PromptCapturingChatCompletion(
        ai_model_id="fake-model-2341", service_id=SERVICE_ID
    )


@pytest.fixture
def agent(capturing_service: PromptCapturingChatCompletion) -> InformalAnalysisAgent:
    """Agent câblé par le chemin de production (`setup_agent_components`)."""
    kernel = sk.Kernel()
    kernel.add_service(capturing_service)
    agent = InformalAnalysisAgent(kernel=kernel, agent_name="InformalAgent2341")
    agent.setup_agent_components(llm_service_id=SERVICE_ID)
    return agent


@pytest.mark.asyncio
async def test_analyze_fallacies_sends_the_text_in_the_rendered_prompt(
    agent: InformalAnalysisAgent,
    capturing_service: PromptCapturingChatCompletion,
):
    """Le texte à analyser doit figurer dans le prompt que le LLM reçoit."""
    await agent.analyze_fallacies(FABRICATED_ARGUMENT)

    prompt = capturing_service.last_prompt
    assert FABRICATED_ARGUMENT in prompt, (
        "Le prompt rendu de semantic_AnalyzeFallacies ne contient pas le texte à "
        "analyser : le slot {{$input}} du template n'a pas été résolu (kwarg passé "
        f"sous un nom que le template ignore). Prompt rendu :\n{prompt}"
    )


@pytest.mark.asyncio
async def test_identify_arguments_binding_is_the_witness(
    agent: InformalAnalysisAgent,
    capturing_service: PromptCapturingChatCompletion,
):
    """Contrôle de non-vacuité : le harnais passe là où le binding est correct.

    `identify_arguments` invoque `semantic_IdentifyArguments` avec `input=text`,
    le nom que `prompt_identify_args_v8` déclare. Ce test doit être VERT y
    compris avant la réparation de #2341 : s'il rougit, c'est le harnais (service
    factice, câblage du kernel, rendu du template) qui est en cause et le rouge
    du test précédent ne mesurerait rien.
    """
    await agent.identify_arguments(FABRICATED_ARGUMENT)

    prompt = capturing_service.last_prompt
    assert FABRICATED_ARGUMENT in prompt, (
        "Témoin en échec : même un binding correct ne fait pas entrer le texte "
        f"dans le prompt rendu. Le harnais est en cause.\nPrompt rendu :\n{prompt}"
    )
