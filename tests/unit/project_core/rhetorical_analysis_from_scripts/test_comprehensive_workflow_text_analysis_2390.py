# -*- coding: utf-8 -*-
"""
#2390 — né-rouge : l'analyse de texte du comprehensive workflow processor
échouait à chaque appel (quatre défauts empilés, chacun masquant les
suivants, plus un fantôme propre à la copie).

Sur l'arbre pristine, ces tests rougissent **en valeurs** :

- ``_analyze_text_content`` rend ``status="error"`` (``'WorkflowConfig'
  object has no attribute 'to_dict'`` — défaut 1 ; les défauts 2-4 — kwarg
  ``config`` inexistant exigeant ``kernel``, ``setup_agent_components()``
  sans son ``llm_service_id``, ``await`` sur cette méthode sync, ``analyze``
  fantôme — masqués derrière) ;
- ``_performance_text_analysis`` LÈVE ``AttributeError`` (``MockLevel.MINIMAL``,
  membre inexistant de l'enum) au lieu de mesurer ;
- le module porte DEUX constructions de ``InformalAnalysisAgent``.

Correctif mesuré ici : construction par le kernel du seam
``_make_analysis_kernel`` (route canonique ``create_llm_service``), setup
SYNC avec son ``llm_service_id``, ``analyze_text`` (l'entrée réelle de
l'agent), et un seul chemin de construction partagé par le scénario de
performance.

Textes fabriqués (aucun extrait du corpus chiffré). Zéro réseau : le
service factice archive les prompts rendus, il n'appelle aucun LLM.
"""

import json
from pathlib import Path
from typing import Any, List

import semantic_kernel as sk
from pydantic import Field
from semantic_kernel.connectors.ai.chat_completion_client_base import (
    ChatCompletionClientBase,
)
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent

from project_core.rhetorical_analysis_from_scripts import (
    comprehensive_workflow_processor as cwp,
)
from project_core.rhetorical_analysis_from_scripts.comprehensive_workflow_processor import (
    PipelineEngine,
    TestOrchestrator,
    WorkflowConfig,
)

# Argument entièrement fabriqué pour ce test — pas un extrait du dataset.
FABRICATED_TEXT = (
    "Le comité des fêtes de Saint-Cache-les-Roches refuse le nouveau "
    "dépôt de tribunes, car son rapporteur ne rédige que des pétitions "
    "circulaires signées de frettes."
)

SERVICE_ID = "fake_llm_2390"


class PromptCapturingChatCompletion(ChatCompletionClientBase):
    """Service factice qui archive chaque prompt rendu (harnais #2360/#2341).

    Il n'appelle aucun LLM : il enregistre le ``ChatHistory`` que Semantic
    Kernel a construit à partir du template rendu, puis retourne une
    réponse JSON minimale parsable par ``analyze_fallacies``.
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
            "Le service factice n'a capturé aucun prompt : la fonction "
            "sémantique n'a pas été invoquée. Le harnais est en cause."
        )
        return self.rendered_prompts[-1]


def _patch_seam(monkeypatch) -> PromptCapturingChatCompletion:
    kernel = sk.Kernel()
    service = PromptCapturingChatCompletion(
        ai_model_id="fake-model-2390", service_id=SERVICE_ID
    )
    kernel.add_service(service)
    # raising=False : sur pristine le seam n'existe pas — le test doit
    # rougir en valeurs sur le défaut du processeur, pas sur un échec de
    # patch d'un symbole neuf.
    monkeypatch.setattr(
        cwp, "_make_analysis_kernel", lambda: (kernel, SERVICE_ID), raising=False
    )
    return service


async def test_analyze_text_content_succeeds_and_text_reaches_the_prompt(
    monkeypatch,
):
    """NÉ-ROUGE (en valeurs) : le status doit être success, le prompt rendu
    doit porter le texte analysé."""
    service = _patch_seam(monkeypatch)
    engine = PipelineEngine(WorkflowConfig())

    result = await engine._analyze_text_content(FABRICATED_TEXT, WorkflowConfig())

    assert result["status"] == "success", (
        "l'analyse de texte du processeur doit réussir ; erreur rendue : "
        f"{result.get('error')}"
    )
    assert FABRICATED_TEXT in service.last_prompt, (
        "le texte analysé n'atteint pas le prompt rendu : la fonction "
        "sémantique n'a pas reçu l'argument."
    )


async def test_performance_scenario_measures_instead_of_raising(monkeypatch):
    """NÉ-ROUGE : le scénario de performance doit mesurer, pas lever.

    Sur pristine, ``MockLevel.MINIMAL`` (membre inexistant) lève
    ``AttributeError`` que l'``except ImportError`` ne rattrape pas.
    """
    _patch_seam(monkeypatch)
    orchestrator = TestOrchestrator(WorkflowConfig())

    # Ne doit pas lever — l'échec éventuel de l'analyse serait nommé par le
    # scénario lui-même (RuntimeError avec l'erreur), pas un fantôme d'enum.
    await orchestrator._performance_text_analysis()


def test_single_construction_path_in_the_module():
    """NÉ-ROUGE : le module porte deux constructions de l'agent (l'originale
    et sa copie dérivée) — un seul chemin après réparation (#2390 DoD 3)."""
    source = Path(cwp.__file__).read_text(encoding="utf-8-sig")
    assert source.count("InformalAnalysisAgent(") == 1, (
        "deux constructions d'InformalAnalysisAgent dans le module = deux "
        "chemins qui dérivent (la copie a déjà divergé : MockLevel.MINIMAL)"
    )


async def test_witness_canonical_construction_passes_the_same_harness():
    """Non-vacuité : le harnais mesure l'agent.

    La construction canonique (kernel + setup sync + ``analyze_text``),
    identique à celle d'``analysis_config._real_llm_analysis``, voit le
    texte dans le prompt rendu — AVANT et APRÈS la réparation. Si ce
    témoin rougit, le rouge des tests du processeur mesurerait le harnais,
    pas le défaut.
    """
    from argumentation_analysis.agents.core.informal.informal_agent import (
        InformalAnalysisAgent,
    )

    kernel = sk.Kernel()
    service = PromptCapturingChatCompletion(
        ai_model_id="fake-model-2390", service_id=SERVICE_ID
    )
    kernel.add_service(service)
    agent = InformalAnalysisAgent(kernel=kernel)
    agent.setup_agent_components(llm_service_id=SERVICE_ID)

    result = await agent.analyze_text(FABRICATED_TEXT)

    assert "error" not in result, f"l'analyse canonique en erreur : {result}"
    assert FABRICATED_TEXT in service.last_prompt
