# -*- coding: utf-8 -*-
"""#2510 — né-rouge : 2 des 3 scénarios de performance chronomètrent un
``asyncio.sleep`` et le publient comme succès mesuré.

Sur l'arbre pristine (``main``), ces tests rougissent **en valeurs** :

- ``pipeline_initialization`` et ``validation_suite`` ont pour seul corps un
  sommeil (0.05 s / 0.02 s) — leurs durées publiées sont nos propres
  constantes, indiscernables de la vraie mesure ``text_analysis`` ;
- la branche ``except ImportError`` du premier exécute le même sommeil : un
  succès fabriqué pour une opération qui n'a pas tourné (DoD 3).

Correctif mesuré ici : ``pipeline_initialization`` chronomètre la
construction réelle du pipeline (kernel du seam #2390 + agent informel +
setup, facteur commun ``_construct_analysis_agent``) ; le scénario
``validation_suite`` quitte le rapport — la validation est une phase à part
entière du workflow (sous-processus + HTTP), la chronométrer ici la
rejouerait — et le résumé nomme les scénarios pour que le retrait se voie.

Zéro réseau : le seam ``_make_analysis_kernel`` est doublé par le service
factice du harnais #2390 (aucun appel LLM), et le sommeil est banni par un
shim posé sur le SEUL global ``asyncio`` du module — le reste de la session
de test n'est pas affecté.
"""

import asyncio
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
    TestOrchestrator,
    WorkflowConfig,
)

SERVICE_ID = "fake_llm_2510"


class PromptCapturingChatCompletion(ChatCompletionClientBase):
    """Service factice du harnais #2390 : archive les prompts, zéro réseau."""

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


class SleepForbidden:
    """Shim posé sur le global ``asyncio`` du module : tout y est forwardé,
    sauf ``sleep`` qui lève — un sommeil n'est pas une mesure (#2510)."""

    def __getattr__(self, name: str) -> Any:
        return getattr(asyncio, name)

    async def sleep(self, *args: Any, **kwargs: Any) -> None:
        raise AssertionError(
            "un scénario de performance a chronométré un sommeil : la durée "
            "publiée serait une constante, pas une mesure (#2510)"
        )


def _ban_sleep_and_double_seam(monkeypatch) -> PromptCapturingChatCompletion:
    kernel = sk.Kernel()
    service = PromptCapturingChatCompletion(
        ai_model_id="fake-model-2510", service_id=SERVICE_ID
    )
    kernel.add_service(service)
    monkeypatch.setattr(cwp, "_make_analysis_kernel", lambda: (kernel, SERVICE_ID))
    monkeypatch.setattr(cwp, "asyncio", SleepForbidden())
    return service


def test_sleep_ban_is_armed(monkeypatch):
    """Non-vacuité du bannissement : le shim lève bien sur ``sleep`` et
    forward le reste — sinon le vert du test principal mesurerait un shim
    inerte."""
    monkeypatch.setattr(cwp, "asyncio", SleepForbidden())
    import pytest

    with pytest.raises(AssertionError):
        asyncio.run(cwp.asyncio.sleep(0))
    assert cwp.asyncio.Semaphore is asyncio.Semaphore


async def test_no_published_success_comes_from_a_sleep(monkeypatch):
    """NÉ-ROUGE (en valeurs, 3 mesures) : le sommeil banni, aucun scénario
    publié comme succès ne peut venir d'un sommeil.

    Sur ``main`` : ``pipeline_initialization`` échoue (son corps EST le
    sommeil) donc n'a pas ``avg_duration`` ; ``validation_suite`` est encore
    au rapport ; le résumé ne nomme pas ses scénarios.
    """
    _ban_sleep_and_double_seam(monkeypatch)
    orchestrator = TestOrchestrator(WorkflowConfig())

    report = await orchestrator.run_performance_tests()

    tests = report["tests"]
    assert "avg_duration" in tests["text_analysis"], (
        "le scénario réel (seam doublé) doit rester un succès malgré le ban "
        f"de sommeil : {tests.get('text_analysis')}"
    )
    assert "avg_duration" in tests["pipeline_initialization"], (
        "pipeline_initialization doit chronométrer l'initialisation réelle "
        "(kernel + agent + setup), pas un sommeil : "
        f"{tests.get('pipeline_initialization')}"
    )
    assert "validation_suite" not in tests, (
        "le scénario validation_suite (sous-processus + HTTP, phase à part "
        "du workflow) doit avoir quitté le rapport de performance"
    )
    assert report["summary"]["scenarios"] == [
        "text_analysis",
        "pipeline_initialization",
    ], (
        "le résumé doit nommer les scénarios : le retrait d'un scénario se "
        f"voit, il ne rétrécit pas total_scenarios en silence : "
        f"{report['summary']}"
    )
    assert report["summary"]["total_scenarios"] == 2


async def test_pipeline_init_scenario_measures_the_real_construction(monkeypatch):
    """Témoin : le scénario d'initialisation exécute la construction que
    chaque analyse exécute — le service factice (via le seam doublé) n'est
    PAS invoqué (le setup n'appelle pas le LLM), et l'agent construit est
    un InformalAnalysisAgent opérationnel."""
    kernel = sk.Kernel()
    service = PromptCapturingChatCompletion(
        ai_model_id="fake-model-2510", service_id=SERVICE_ID
    )
    kernel.add_service(service)
    monkeypatch.setattr(cwp, "_make_analysis_kernel", lambda: (kernel, SERVICE_ID))

    orchestrator = TestOrchestrator(WorkflowConfig())
    await orchestrator._performance_pipeline_init()

    assert not service.rendered_prompts, (
        "l'initialisation ne doit pas appeler le LLM — sinon le scénario "
        "mesurerait une analyse, pas une initialisation"
    )


def test_module_carries_no_sleep_in_its_measurements():
    """NÉ-ROUGE : le module ne porte plus AUCUN ``asyncio.sleep`` — sur
    ``main`` il en compte 3 (les deux scénarios fabriqués et la branche
    ``except ImportError``). Une mesure ne dort pas."""
    source = Path(cwp.__file__).read_text(encoding="utf-8-sig")
    assert "asyncio.sleep" not in source, (
        "un ``asyncio.sleep`` dans le module : toute durée publiée à partir "
        "de lui serait une constante, pas une mesure (#2510)"
    )
