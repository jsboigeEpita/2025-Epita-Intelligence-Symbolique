# -*- coding: utf-8 -*-
"""Né-rouge #2649 — le ServiceManager nomme le composant qu'il n'a pas configuré.

``initialize()`` enveloppait l'installation du plugin informel dans deux
``except`` qui journalisaient puis continuaient. Depuis #2632/#2650,
``setup_informal_kernel`` lève ``SemanticSetupError`` quand les settings de son
service sont introuvables : le manager transformait ce message en ligne de log,
son kernel repartait sans ``InformalAnalyzer``, et la panne ne se voyait qu'à
l'invocation suivante.

La décision que #2649 tranche : un manager **keyless** n'a pas de plugin
informel — les trois fonctions sémantiques lisent les settings d'un service LLM.
Ce n'est pas un incident, c'est le cas nominal sans clé, et il se dit dans
``setup_failures``, exposé par ``get_status()``. Le manager ne refuse pas de
démarrer : le refus casserait la flotte de tests sans clé.

Fixtures synthétiques : clés factices, service de chat doublure, aucun egress.
"""

import types

from pydantic import SecretStr
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.chat_completion_client_base import (
    ChatCompletionClientBase,
)
from semantic_kernel.contents.chat_message_content import ChatMessageContent

SM_MODULE = "argumentation_analysis.orchestration.service_manager"


class _FakeChat(ChatCompletionClientBase):
    """Le service LLM que ``create_llm_service`` rendrait ; jamais appelé."""

    async def _inner_get_chat_message_contents(self, chat_history, settings):
        return [
            ChatMessageContent(
                role="assistant", content="{}", ai_model_id=self.ai_model_id
            )
        ]


def _settings(api_key):
    return types.SimpleNamespace(
        openai=types.SimpleNamespace(api_key=api_key),
        service_manager=types.SimpleNamespace(
            default_llm_service_id="fake-2649",
            enable_communication_middleware=False,
            enable_hierarchical=False,
            enable_specialized_orchestrators=False,
        ),
    )


def _manager():
    import argumentation_analysis.orchestration.service_manager as sm

    return sm.OrchestrationServiceManager(enable_logging=False)


async def test_a_keyless_manager_names_the_plugin_it_does_not_have(monkeypatch):
    """Sans clé : pas de service LLM, donc pas de plugin informel — nommé.

    Né-rouge sur ``main`` : rien dans l'état, seulement une ligne de log.
    Contre-pendule : l'initialisation keyless aboutit toujours.
    """
    import argumentation_analysis.orchestration.service_manager as sm

    monkeypatch.setattr(sm, "settings", _settings(None))
    monkeypatch.setattr(sm, "initialize_project_environment", lambda: object())

    manager = _manager()
    assert await manager.initialize() is True, "l'initialisation keyless continue"

    reason = manager.setup_failures.get("informal_plugin")
    assert reason is not None, manager.setup_failures
    assert "clé" in reason.lower(), reason
    assert "InformalAnalyzer" in reason, reason

    status = await manager.get_status()
    assert status["setup_failures"]["informal_plugin"] == reason


async def test_a_failed_setup_reaches_the_state_and_the_status(monkeypatch):
    """Un setup qui lève nomme sa cause dans l'état, pas seulement dans le log.

    Né-rouge sur ``main`` : ``logger.error`` puis continuation, kernel sans
    ``InformalAnalyzer``. Contre-pendule : l'initialisation aboutit toujours —
    cette ligne-là est un composant absent, pas un démarrage refusé.
    """
    import argumentation_analysis.orchestration.service_manager as sm
    from argumentation_analysis.agents.core.informal import informal_definitions
    from argumentation_analysis.agents.core.semantic_setup import SemanticSetupError

    service = _FakeChat(ai_model_id="fake-2649", service_id="fake-2649")

    monkeypatch.setattr(
        sm, "settings", _settings(SecretStr("sk-test-not-a-real-key-2649"))
    )
    monkeypatch.setattr(sm, "initialize_project_environment", lambda: object())
    monkeypatch.setattr(sm, "create_llm_service", lambda **kwargs: service)

    def _boom(**kwargs):
        raise SemanticSetupError(
            "InformalAnalyzer : settings du service LLM 'fake-2649' introuvables"
        )

    monkeypatch.setattr(informal_definitions, "setup_informal_kernel", _boom)

    manager = _manager()
    assert await manager.initialize() is True

    reason = manager.setup_failures.get("informal_plugin")
    assert reason is not None, manager.setup_failures
    assert "SemanticSetupError" in reason, reason
    assert "introuvables" in reason, reason

    status = await manager.get_status()
    assert status["setup_failures"]["informal_plugin"] == reason


async def test_a_re_initialisation_does_not_keep_the_previous_failure(monkeypatch):
    """Une reprise réussie efface l'échec de la tentative précédente.

    Un état qui nomme un composant absent alors qu'il est là est le défaut même
    que #2649 répare. La première tentative échoue **après** avoir enregistré
    l'absence du plugin (middleware indisponible) ; la seconde, avec le service
    présent, doit repartir de zéro.

    Né-rouge sur ``main`` : ``setup_failures`` n'existe pas — il n'y avait rien
    à périmer, rien à lire, et donc rien à reprendre.
    """
    import argumentation_analysis.orchestration.service_manager as sm
    from argumentation_analysis.agents.core.informal import informal_definitions

    async def _boom(*args, **kwargs):
        raise RuntimeError("middleware indisponible")

    monkeypatch.setattr(sm, "initialize_project_environment", lambda: object())

    # Première tentative : keyless, elle échoue APRÈS le bloc informel.
    first = _settings(None)
    first.service_manager.enable_communication_middleware = True
    monkeypatch.setattr(sm, "settings", first)

    manager = _manager()
    manager.initialize_middleware = _boom
    assert await manager.initialize() is False
    assert "informal_plugin" in manager.setup_failures

    # Reprise : le service est là, et l'échec précédent ne doit pas survivre.
    monkeypatch.setattr(
        sm, "settings", _settings(SecretStr("sk-test-not-a-real-key-2649"))
    )
    monkeypatch.setattr(
        sm,
        "create_llm_service",
        lambda **kwargs: _FakeChat(ai_model_id="fake-2649", service_id="fake-2649"),
    )
    monkeypatch.setattr(
        informal_definitions, "setup_informal_kernel", lambda **kw: None
    )

    assert await manager.initialize() is True
    assert manager.setup_failures == {}, manager.setup_failures


async def test_the_kernel_api_the_manager_uses_exists():
    """La prémisse du chemin keyless, re-mesurée : ``add_service`` puis
    ``get_service`` sur un ``Kernel`` réel rend bien le service enregistré.

    Sans elle, le manager pourrait classer « keyless » un service présent.
    """
    kernel = Kernel()
    service = _FakeChat(ai_model_id="fake-2649", service_id="fake-2649")
    kernel.add_service(service)

    assert kernel.get_service("fake-2649") is service
