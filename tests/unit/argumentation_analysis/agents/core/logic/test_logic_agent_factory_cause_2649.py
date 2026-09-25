# -*- coding: utf-8 -*-
"""Né-rouge #2649 — une exception de constructeur atteint l'appelant.

``LogicAgentFactory.create_agent`` enveloppait l'instanciation dans un
``try/except Exception`` : il journalisait puis rendait ``None``. Depuis
#2632/#2650, un constructeur lève ``SemanticSetupError`` quand il ne peut pas
enregistrer ses fonctions sémantiques ou résoudre les settings de son service.
La fabrique transformait ce message en ``None``, et chaque site d'appel levait
ou enregistrait sa propre formule générique : « returned None », « Impossible de
créer l'agent logique », ou un agent silencieusement absent.

Ces témoins font lever un **vrai** constructeur — la classe enregistrée dans la
table de la fabrique — jamais la fabrique elle-même : patcher ``create_agent``
mesurerait la doublure, pas le code de ``main``.

Fixtures synthétiques : aucune clé, aucun JVM, aucune requête LLM.
"""

import pytest
import semantic_kernel as sk
from semantic_kernel.connectors.ai.chat_completion_client_base import (
    ChatCompletionClientBase,
)
from semantic_kernel.contents.chat_message_content import ChatMessageContent

from argumentation_analysis.agents.core.logic.logic_factory import LogicAgentFactory
from argumentation_analysis.agents.core.semantic_setup import SemanticSetupError

CAUSE = "settings du service LLM 'fake-2649' introuvables"


class _ExplodingAgent:
    """Un constructeur d'agent qui échoue comme le font les vrais (#2632)."""

    def __init__(self, **kwargs):
        raise SemanticSetupError(f"Agent logique : {CAUSE}")


class _FakeChat(ChatCompletionClientBase):
    """Le seul service dont le kernel a besoin ; il n'est jamais appelé."""

    async def _inner_get_chat_message_contents(self, chat_history, settings):
        return [
            ChatMessageContent(
                role="assistant", content="{}", ai_model_id=self.ai_model_id
            )
        ]


def _kernel() -> sk.Kernel:
    kernel = sk.Kernel()
    kernel.add_service(_FakeChat(ai_model_id="fake-2649", service_id="fake-2649"))
    return kernel


def test_a_constructor_failure_propagates_with_its_type_and_message(monkeypatch):
    """La cause sort de la fabrique, avec son type.

    Né-rouge sur ``main`` : ``create_agent`` rend ``None``, et le message de
    ``SemanticSetupError`` ne survit que dans une ligne de log.
    """
    monkeypatch.setitem(
        LogicAgentFactory._agent_classes, "propositional", _ExplodingAgent
    )

    with pytest.raises(SemanticSetupError) as excinfo:
        LogicAgentFactory.create_agent("propositional", _kernel())

    assert CAUSE in str(excinfo.value)


def test_an_unsupported_type_raises_and_names_what_the_factory_builds():
    """Un type inconnu lève, et le message dit ce que la fabrique sait faire.

    Né-rouge sur ``main`` : ``None``, donc l'appelant ne pouvait nommer que le
    type qu'il avait passé, jamais ceux qui sont disponibles.
    """
    with pytest.raises(ValueError) as excinfo:
        LogicAgentFactory.create_agent("quantum_logic", _kernel())

    message = str(excinfo.value)
    assert "quantum_logic" in message
    assert "propositional" in message
    assert "first_order" in message


def test_the_error_names_only_types_this_factory_can_instantiate():
    """Contre-pendule : ``get_supported_logic_types`` liste aussi des types sans
    agent (``_handler_types``). Le message d'erreur ne doit pas les proposer —
    ``create_agent`` les refuserait à leur tour."""
    with pytest.raises(ValueError) as excinfo:
        LogicAgentFactory.create_agent("quantum_logic", _kernel())

    message = str(excinfo.value)
    for handler_only in ("description_logic", "conditional_logic", "sat"):
        assert handler_only not in message, message


def test_the_orchestrator_caller_records_the_cause(monkeypatch):
    """Le site d'appel du mode réel enregistre la cause dans son état.

    Né-rouge sur ``main`` : ``real_agent_setup_failures["fol_logic"]`` portait
    ``RuntimeError: … returned None`` — le nom du symptôme, pas la cause.
    """
    from argumentation_analysis.orchestration.conversation_orchestrator import (
        ConversationOrchestrator,
    )

    monkeypatch.setitem(
        LogicAgentFactory._agent_classes, "first_order", _ExplodingAgent
    )

    orchestrator = ConversationOrchestrator(mode="real", kernel=_kernel())

    failure = orchestrator.real_agent_setup_failures.get("fol_logic", "")
    assert "SemanticSetupError" in failure, failure
    assert CAUSE in failure, failure
    assert "returned None" not in failure, failure


async def test_the_pipeline_reason_carries_the_cause(monkeypatch):
    """La raison du pipeline formel porte le texte de l'exception.

    Né-rouge sur ``main`` : ``status`` valait ``Failed`` avec la formule
    « Impossible de créer l'agent logique », et la cause restait dans le log.
    La raison est le message de l'exception (``str(e)``), pas son type : les
    messages de la fabrique nomment déjà ce qui a échoué.
    """
    from argumentation_analysis.pipelines.unified_text_analysis import (
        UnifiedAnalysisConfig,
        UnifiedTextAnalysisPipeline,
    )

    monkeypatch.setitem(
        LogicAgentFactory._agent_classes, "propositional", _ExplodingAgent
    )

    pipeline = UnifiedTextAnalysisPipeline(
        UnifiedAnalysisConfig(logic_type="propositional")
    )
    pipeline.jvm_ready = True
    pipeline.llm_service = _FakeChat(ai_model_id="fake-2649", service_id="fake-2649")

    formal_results = await pipeline._perform_formal_analysis("texte synthétique")

    assert formal_results["status"] == "Error", formal_results
    assert CAUSE in formal_results["reason"], formal_results
    assert "Impossible de créer" not in formal_results["reason"], formal_results
