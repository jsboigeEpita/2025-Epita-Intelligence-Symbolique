# -*- coding: utf-8 -*-
"""
#2360 — le cycle de vie de FOLLogicAgent est sync comme sa famille, et ses
prompts parlent le dialecte de Semantic Kernel.

Deux défauts jumeaux, même conséquence : **le composant n'était jamais
configuré**.

Défaut A (cycle de vie) : `setup_agent_components` était `async` chez FOL
seul — la base (`BaseLogicAgent`, agent_bases.py) et les 8 autres agents la
définissent sync. L'API web (`logic_service.py`) l'appelle sans `await` :
l'appel rendait une coroutine jamais attendue, la configuration ne tournait
jamais, sans erreur visible. Et même sur le chemin awaited (l'appel interne
paresseux d'`analyze`), l'enregistrement mourait en silence : le corps
appelait `kernel.create_function_from_prompt`, qui **n'existe pas** sur le
kernel de ce dépôt (AttributeError avalée par le try/except de la def
vivante).

Défaut B (dialecte) : les templates portaient des slots Python `.format`
(`{text}`, `{formulas}`, `{context}`) mais étaient consommés par le moteur de
templates de Semantic Kernel, qui ne rend QUE `{{$nom}}`. Le LLM recevait la
consigne avec un `{text}` littéral — l'argument n'entrait jamais dans le
prompt (même famille que #2341).

Le contrôle mesure ce qui décide : **l'état réel du kernel après l'appel
sync** (A) et **le prompt effectivement rendu au service** (B). Un service
factice archive chaque prompt ; il n'appelle aucun LLM.

⚠ Non-vacuité : le même harnais doit passer sur l'agent propositionnel
(famille sync, héritage de la base) pour A, et sur une fonction sémantique
correctement liée (`{{$value}}`) pour B. Sans eux, un rouge mesurerait le
harnais, pas le défaut.

Les textes sont **fabriqués** (aucun extrait du corpus chiffré) et assez
singuliers pour ne pouvoir apparaître dans le prompt que par le slot.
"""

import inspect
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
from semantic_kernel.functions import KernelArguments

from argumentation_analysis.agents.core.logic.fol_logic_agent import FOLLogicAgent
from argumentation_analysis.agents.core.logic.logic_factory import LogicAgentFactory

# Argument entièrement fabriqué pour ce test — pas un extrait du dataset.
FABRICATED_TEXT = (
    "La commission des travaux de Saint-Rémy-sur-Cache doit refuser le "
    "nouveau dépôt de gravats, car son architecte dessine uniquement des "
    "restrictions circulaires."
)
FABRICATED_FORMULAS = "forall X: (Gravat(X) => Refus(X))"
FABRICATED_CONTEXT = (
    "Contexte fabriqué : le dépôt de Villeneuve-les-Cache est contesté par "
    "une pétition de frettes ferroviaires."
)
WITNESS_MARKER = "MARQUEUR_TEMOIN_2360"

SERVICE_ID = "default_logic_llm"


class PromptCapturingChatCompletion(ChatCompletionClientBase):
    """Service de complétion factice qui archive chaque prompt rendu.

    Il n'appelle aucun LLM : il enregistre le `ChatHistory` que Semantic Kernel
    a construit à partir du template rendu, puis retourne une réponse JSON
    minimale parsable par les appelants.
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
                content=json.dumps({"formulas": [FABRICATED_FORMULAS]}),
                ai_model_id=self.ai_model_id,
            )
        ]

    @property
    def last_prompt(self) -> str:
        assert self.rendered_prompts, (
            "Le service factice n'a capturé aucun prompt : la fonction "
            "sémantique n'a pas été invoquée. Le harnais est en cause, pas "
            "le binding."
        )
        return self.rendered_prompts[-1]


def _make_kernel_with_capture() -> tuple[sk.Kernel, PromptCapturingChatCompletion]:
    kernel = sk.Kernel()
    service = PromptCapturingChatCompletion(
        ai_model_id="fake-model-2360", service_id=SERVICE_ID
    )
    kernel.add_service(service)
    return kernel, service


# ---------------------------------------------------------------------------
# Défaut A — le cycle de vie
# ---------------------------------------------------------------------------


def test_web_service_sync_call_really_configures_the_agent():
    """NÉ-ROUGE (en valeurs) : l'appel sync de logic_service doit configurer.

    Construit l'agent par le chemin de production (`LogicAgentFactory`),
    appelle la configuration EXACTEMENT comme `logic_service.py` (sans
    `await`), puis asserte l'état réel du kernel : le plugin `fol_logic`
    doit exister et porter ses deux fonctions sémantiques. Sur main,
    l'appel sync rend une coroutine jamais attendue — le plugin est absent.
    """
    kernel, _service = _make_kernel_with_capture()
    agent = LogicAgentFactory.create_agent("first_order", kernel)
    assert agent is not None, "la factory n'a pas su créer l'agent FOL"

    agent.setup_agent_components(
        llm_service_id=SERVICE_ID
    )  # sync, comme logic_service.py

    plugin = kernel.plugins.get("fol_logic")
    assert plugin is not None, (
        "le plugin fol_logic n'est pas enregistré après l'appel sync : la "
        "configuration n'a jamais tourné (coroutine jamais attendue sur "
        "main, ou enregistrement mort dans le try/except)"
    )
    assert (
        "convert_to_fol" in plugin.functions
    ), f"convert_to_fol absente du plugin : {sorted(plugin.functions)}"
    assert (
        "analyze_fol" in plugin.functions
    ), f"analyze_fol absente du plugin : {sorted(plugin.functions)}"


def test_lifecycle_is_sync_like_the_base_and_the_eight_siblings():
    """Le contrat : la base et les 8 autres agents sont sync, FOL aussi."""
    assert not inspect.iscoroutinefunction(FOLLogicAgent.setup_agent_components), (
        "setup_agent_components est coroutine function : FOL diverge du "
        "contrat sync de BaseLogicAgent et de ses 8 frères"
    )


def test_propositional_witness_passes_the_same_harness():
    """Non-vacuité A : le harnais est vert là où le contrat est déjà tenu.

    L'agent propositionnel hérite de la def sync de la base. Le même appel
    sync doit passer SANS erreur ni coroutine — avant et après la
    réparation. S'il rougit, c'est le harnais (factory, kernel) qui est en
    cause et le rouge du premier test ne mesurerait rien.
    """
    kernel, _service = _make_kernel_with_capture()
    agent = LogicAgentFactory.create_agent("propositional", kernel)
    assert agent is not None, "la factory n'a pas su créer l'agent propositionnel"

    result = agent.setup_agent_components(llm_service_id=SERVICE_ID)

    assert not inspect.isawaitable(result), (
        "l'agent propositionnel (définition sync héritée) a rendu un "
        "awaitable — le harnais ne mesure pas ce qu'il prétend"
    )


# ---------------------------------------------------------------------------
# Défaut B — le dialecte des prompts
# ---------------------------------------------------------------------------


async def test_convert_to_fol_prompt_carries_the_text():
    """NÉ-ROUGE (en valeurs) : le texte analysé entre dans le prompt rendu.

    L'enregistrement est fait par le test via `add_function` (l'API qui
    existe) sur le prompt PRODUCTION de l'agent — c'est l'isolation du
    défaut B : sur main, le template porte `{text}` littéral, le moteur SK
    ne résout rien, et le service factice reçoit la consigne SANS l'argument
    à convertir. Après réparation, `{{$text}}` rend le texte.
    """
    kernel, service = _make_kernel_with_capture()
    agent = LogicAgentFactory.create_agent("first_order", kernel)
    assert agent is not None

    kernel.add_function(
        plugin_name="fol_logic",
        function_name="convert_to_fol",
        prompt=agent._conversion_prompt,
        description="Convertit du texte naturel en formules FOL",
    )

    # Le chemin d'invocation de production (_convert_to_fol, l.411) — le
    # kernel de ce dépôt exige des KernelArguments, un dict nu est rejeté.
    await kernel.invoke(
        function_name="convert_to_fol",
        plugin_name="fol_logic",
        arguments=KernelArguments(text=FABRICATED_TEXT, context="Aucun contexte"),
    )

    prompt = service.last_prompt
    assert FABRICATED_TEXT in prompt, (
        "Le prompt rendu de convert_to_fol ne contient pas le texte à "
        "convertir : le slot du template n'est pas en dialecte Semantic "
        f"Kernel (${{$nom}}). Prompt rendu :\n{prompt}"
    )


async def test_analyze_fol_prompt_carries_formulas_and_context():
    """NÉ-ROUGE (en valeurs) : formules ET contexte entrent dans le prompt.

    Même isolation que le test précédent, sur le template d'analyse : sur
    main, `{formulas}` et `{context}` restent littéraux.
    """
    kernel, service = _make_kernel_with_capture()
    agent = LogicAgentFactory.create_agent("first_order", kernel)
    assert agent is not None

    kernel.add_function(
        plugin_name="fol_logic",
        function_name="analyze_fol",
        prompt=agent._analysis_prompt,
        description="Analyse la cohérence et les inférences FOL",
    )

    # Le chemin d'invocation de production (_llm_enhanced_analysis, l.796).
    await kernel.invoke(
        function_name="analyze_fol",
        plugin_name="fol_logic",
        arguments=KernelArguments(
            formulas=FABRICATED_FORMULAS, context=FABRICATED_CONTEXT
        ),
    )

    prompt = service.last_prompt
    assert (
        FABRICATED_FORMULAS in prompt
    ), f"Les formules n'entrent pas dans le prompt rendu :\n{prompt}"
    assert (
        FABRICATED_CONTEXT in prompt
    ), f"Le contexte n'entre pas dans le prompt rendu :\n{prompt}"


async def test_slot_rendering_witness():
    """Non-vacuité B : le harnais rend correctement un slot bien lié.

    Une fonction sémantique correctement liée (`{{$value}}`) construite sur
    le MÊME kernel + service factice doit voir sa valeur entrer dans le
    prompt rendu — avant et après la réparation. Si ce témoin rougit, le
    rouge des deux tests précédents mesurerait le harnais, pas le dialecte.
    """
    kernel, service = _make_kernel_with_capture()

    kernel.add_function(
        plugin_name="witness_2360",
        function_name="render_value",
        prompt="Marqueur: {{$value}}",
        description="Témoin de rendu de slot",
    )
    await kernel.invoke(
        function_name="render_value",
        plugin_name="witness_2360",
        arguments=KernelArguments(value=WITNESS_MARKER),
    )

    assert WITNESS_MARKER in service.last_prompt, (
        "Témoin en échec : même un slot correctement lié ne fait pas entrer "
        f"la valeur dans le prompt rendu. Le harnais est en cause.\n"
        f"Prompt rendu :\n{service.last_prompt}"
    )
