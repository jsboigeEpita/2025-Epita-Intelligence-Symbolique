# -*- coding: utf-8 -*-
"""#2132 — les capacités de l'adaptateur se dérivent des plugins montés, pas d'une table.

`InformalAgentAdapter.get_capabilities()` dupliquait la correspondance
config→plugins de `InformalFallacyAgent._add_plugins_from_config` dans une
table locale, avec un `return []` silencieux pour un config inconnu — la forme
exacte retirée de l'agent en #2121. Ces tests tiennent les trois cases de la
DoD :

1. né-rouge — plus de `[]` silencieux sans agent : fail-loud ;
2. dérivation — un adaptateur dont le `config_name` et l'agent réel monté
   **divergent** rend les capacités de l'agent, pas celles du nom de config ;
3. garde anti-dérive — pour chaque config acceptée, les capacités rendues sont
   exactement la traduction des plugins effectivement montés (la table de
   traduction est répliquée ici exprès : si le pont source change de
   vocabulaire sans que la chaîne de délégation le suive, ça rougit).

L'agent est toujours RÉEL (`InformalFallacyAgent` sur un kernel vivant avec un
service chat moqué) — un MagicMock fabriquerait `get_agent_capabilities`.
"""

import logging

import pytest
from unittest.mock import MagicMock

from semantic_kernel.kernel import Kernel
from semantic_kernel.connectors.ai.chat_completion_client_base import (
    ChatCompletionClientBase,
)
from semantic_kernel.connectors.ai.prompt_execution_settings import (
    PromptExecutionSettings,
)

from argumentation_analysis.agents.concrete_agents.informal_fallacy_agent import (
    INFORMAL_AGENT_CONFIGS,
    InformalFallacyAgent,
)
from argumentation_analysis.orchestration.hierarchical.operational.adapters.informal_agent_adapter import (
    InformalAgentAdapter,
)

#: Traduction répliquée à dessein (garde n°3) : le vocabulaire que la chaîne de
#: délégation demande — cf. tactical/coordinator.py ("fallacy_detection").
EXPECTED_PLUGIN_TO_CAPABILITY = {
    "FallacyIdentificationPlugin": "fallacy_detection",
    "TaxonomyDisplayPlugin": "taxonomy_exploration",
    "FallacyWorkflowPlugin": "fallacy_analysis_workflow",
}


@pytest.fixture
def kernel():
    """Kernel réel avec un service chat moqué — suffisant pour les portes de plugins."""
    kernel = Kernel()
    mock_service = MagicMock(spec=ChatCompletionClientBase)
    mock_service.get_prompt_execution_settings_class.return_value = (
        PromptExecutionSettings
    )
    mock_service.service_id = "test_service"
    kernel.add_service(mock_service)
    return kernel


def _real_agent(kernel, config_name: str) -> InformalFallacyAgent:
    return InformalFallacyAgent(
        kernel=kernel, config_name=config_name, llm_service_id="test_service"
    )


def _mounted_plugins(agent: InformalFallacyAgent) -> list:
    return agent.get_agent_capabilities()["plugins"]


class TestNoSilentEmptyList:
    def test_get_capabilities_without_agent_raises(self):
        """Né-rouge (#2132 case 2) : avant, `return []` silencieux.

        Un adaptateur jamais initialisé, ou dont l'initialisation a échoué
        (config inconnu → ValueError attrapée dans initialize() depuis #2121),
        ne doit pas passer pour un agent sans capacités : il doit dire qu'il
        n'a pas d'agent.
        """
        adapter = InformalAgentAdapter(config_name="bogus")
        with pytest.raises(RuntimeError, match="avant initialize"):
            adapter.get_capabilities()

    async def test_initialize_with_unknown_config_fails_loud(self, kernel):
        """Le config inconnu est déjà refusé à la construction (#2121) ;
        l'adaptateur ne doit pas le ressusciter en « agent vide »."""
        adapter = InformalAgentAdapter(config_name="default_with_plugins")
        ok = await adapter.initialize(kernel, "test_service", None)
        assert ok is False
        assert adapter.agent is None
        with pytest.raises(RuntimeError, match="avant initialize"):
            adapter.get_capabilities()


class TestDerivedFromMountedPlugins:
    def test_capabilities_follow_the_agent_not_the_config_name(self, kernel):
        """Case 1 de la DoD : dérivation depuis le registre réel.

        Situation de dérive construite exprès : `config_name="simple"` mais
        l'agent réellement monté est un `full` (3 plugins). La table d'origine
        rendait les capacités de « simple » ; la dérivation rend celles de
        l'agent effectivement présent.
        """
        adapter = InformalAgentAdapter(config_name="simple")
        adapter.agent = _real_agent(kernel, "full")
        adapter.initialized = True

        capabilities = adapter.get_capabilities()

        assert capabilities == [
            "fallacy_analysis_workflow",
            "fallacy_detection",
            "taxonomy_exploration",
        ]

    def test_every_accepted_config_translates_its_mounted_plugins(self, kernel):
        """Case 3 de la DoD : la garde anti-dérive, pour chaque config acceptée."""
        for config_name in INFORMAL_AGENT_CONFIGS:
            adapter = InformalAgentAdapter(config_name=config_name)
            adapter.agent = _real_agent(kernel, config_name)
            adapter.initialized = True

            mounted = _mounted_plugins(adapter.agent)
            expected = sorted(
                {
                    EXPECTED_PLUGIN_TO_CAPABILITY[p]
                    for p in mounted
                    if p in EXPECTED_PLUGIN_TO_CAPABILITY
                }
            )
            assert adapter.get_capabilities() == expected, (
                f"config {config_name!r} : monté {mounted} mais capacités "
                f"{adapter.get_capabilities()} != traduction {expected}"
            )

    def test_unmapped_plugin_warns_and_is_excluded(self, kernel, caplog):
        """Un plugin monté sans entrée au pont ne disparaît pas en silence."""
        adapter = InformalAgentAdapter(config_name="simple")
        adapter.agent = _real_agent(kernel, "simple")
        adapter.initialized = True
        adapter.agent._configured_plugins.append("MysteryPlugin")

        with caplog.at_level(logging.WARNING, logger=adapter.logger.name):
            capabilities = adapter.get_capabilities()

        assert capabilities == ["fallacy_detection"]
        assert "MysteryPlugin" in caplog.text
        assert "PLUGIN_TO_CAPABILITY" in caplog.text


class TestCanProcessTask:
    def test_matches_production_capability_vocabulary(self, kernel):
        """`fallacy_detection` est une valeur émise en production
        (tactical/coordinator.py) : la correspondance doit tenir."""
        adapter = InformalAgentAdapter(config_name="simple")
        adapter.agent = _real_agent(kernel, "simple")
        adapter.initialized = True

        assert adapter.can_process_task(
            {"required_capabilities": ["fallacy_detection"]}
        )
        assert not adapter.can_process_task(
            {"required_capabilities": ["taxonomy_exploration"]}
        )
