# -*- coding: utf-8 -*-
"""#2158 — la garde porte sur l'effet, jamais sur l'annonce.

Le bloc ``taxonomy_path_instance`` (résolution, log « obtained for
AgentFactory », ``try/except``) est mort depuis #2156 : la transmission vit
dans ``get_taxonomy_source_for_regime``, qui rappelle ``get_taxonomy_path()``
pour son propre compte sous ``funnel``. #2158 supprime ce bloc et son
magasin mort ``app_settings`` ; ces tests gardent l'**effet** du câblage —
ce que le plugin monté reçoit réellement — sans épingler aucune ligne de
log (épingler l'annonce re-signerait le défaut qu'elle décrivait).

L'agent est construit par le VRAI site : ``AnalysisService`` avec un service
chat moqué, kernel vivant, plugins réels. Un espion sur ``Kernel.add_plugin``
enregistre l'instance ``FallacyWorkflowPlugin`` sans rien court-circuiter —
la chaîne de production reste entière.
"""

import pytest
from unittest.mock import MagicMock

import semantic_kernel as sk
from semantic_kernel.connectors.ai.chat_completion_client_base import (
    ChatCompletionClientBase,
)
from semantic_kernel.connectors.ai.prompt_execution_settings import (
    PromptExecutionSettings,
)

from argumentation_analysis.plugins.fallacy_workflow_plugin import (
    FallacyWorkflowPlugin,
)
from argumentation_analysis.services.web_api.services.analysis_service import (
    AnalysisService,
)


@pytest.fixture
def llm_service():
    mock = MagicMock(spec=ChatCompletionClientBase)
    mock.get_prompt_execution_settings_class.return_value = PromptExecutionSettings
    mock.service_id = "test_service"
    return mock


@pytest.fixture
def mounted_plugins(llm_service, monkeypatch):
    """Espionne ``Kernel.add_plugin`` : la chaîne reste réelle, l'instance
    du plugin monté est enregistrée pour l'assertion d'effet."""
    captured = {}
    original_add_plugin = sk.Kernel.add_plugin

    def spying_add_plugin(kernel_self, plugin, plugin_name=None, **kwargs):
        if plugin_name:
            captured[plugin_name] = plugin
        return original_add_plugin(
            kernel_self, plugin, plugin_name=plugin_name, **kwargs
        )

    monkeypatch.setattr(sk.Kernel, "add_plugin", spying_add_plugin)
    return captured


def _build_service(llm_service) -> AnalysisService:
    return AnalysisService(llm_service=llm_service)


def _funnel_plugin(mounted) -> FallacyWorkflowPlugin:
    plugin = mounted.get("FallacyWorkflowPlugin")
    assert isinstance(
        plugin, FallacyWorkflowPlugin
    ), f"le site doit monter un FallacyWorkflowPlugin réel, reçu : {plugin!r}"
    return plugin


class TestFunnelReceivesTheSource:
    def test_funnel_regime_mounts_a_loaded_navigator(
        self, llm_service, mounted_plugins, monkeypatch
    ):
        """À ``funnel``, l'effet est mesurable chez le consommateur : le
        plugin monté a reçu une source non nulle et son navigateur a des
        racines (``taxonomy_state == "loaded"``)."""
        monkeypatch.setenv("TAXONOMY_REGIME", "funnel")

        service = _build_service(llm_service)

        assert service.informal_agent is not None
        plugin = _funnel_plugin(mounted_plugins)
        assert plugin.taxonomy_state == "loaded"
        assert plugin.taxonomy_navigator.get_root_nodes()


class TestOneShotReceivesNothing:
    def test_one_shot_regime_mounts_an_empty_navigator(
        self, llm_service, mounted_plugins, monkeypatch
    ):
        """À ``one_shot``, aucune source n'est transmise : le navigateur est
        vide **par construction** (``taxonomy_state == "none"`` — aucun
        chargement tenté), pas en échec."""
        monkeypatch.setenv("TAXONOMY_REGIME", "one_shot")

        service = _build_service(llm_service)

        assert service.informal_agent is not None
        plugin = _funnel_plugin(mounted_plugins)
        assert plugin.taxonomy_state == "none"
        assert not plugin.taxonomy_navigator.get_root_nodes()

    def test_default_regime_is_one_shot(
        self, llm_service, mounted_plugins, monkeypatch
    ):
        """Le régime par défaut (variable d'environnement absente) reste
        ``one_shot`` — décision user inchangée par #2158."""
        monkeypatch.delenv("TAXONOMY_REGIME", raising=False)

        service = _build_service(llm_service)

        plugin = _funnel_plugin(mounted_plugins)
        assert plugin.taxonomy_state == "none"
