# Fichier : tests/integration/test_fallacy_agent_workflow.py
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
import importlib
from argumentation_analysis.agents.factory import AgentFactory, AgentType
from argumentation_analysis.agents.plugins.taxonomy_display_plugin import (
    TaxonomyDisplayPlugin,
)
from argumentation_analysis.config.settings import AppSettings

from semantic_kernel.kernel import Kernel
from semantic_kernel.functions.kernel_arguments import KernelArguments
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.function_call_content import FunctionCallContent
from semantic_kernel.contents.function_result_content import FunctionResultContent

# from semantic_kernel.tools.function_view import FunctionView
from semantic_kernel.agents.chat_completion.chat_completion_agent import (
    ChatCompletionAgent,
    AgentResponseItem,
)
from semantic_kernel.connectors.ai.chat_completion_client_base import (
    ChatCompletionClientBase,
)
from semantic_kernel.connectors.ai.prompt_execution_settings import (
    PromptExecutionSettings,
)

from argumentation_analysis.agents.tools.analysis.complex_fallacy_analyzer import (
    ComplexFallacyAnalyzer,
)

# L'alias 'as IdentificationPlugin' est supprimé pour plus de clarté,
# la classe sera référencée par son vrai nom ci-dessous.

# --- Mocks de Réponses du LLM ---

# Le LLM explore la racine, puis une branche, puis identifie.
MOCK_COMPLEX_WORKFLOW_RESPONSE = [
    [
        ChatMessageContent(
            role="assistant",
            content=None,
            tool_calls=[
                FunctionCallContent(
                    id="call_1",
                    name="explore_branch",
                    arguments={"node_id": "fallacy_root"},
                )
            ],
        )
    ],
    [
        ChatMessageContent(
            role="assistant",
            content=None,
            tool_calls=[
                FunctionCallContent(
                    id="call_2",
                    name="explore_branch",
                    arguments={"node_id": "relevance"},
                )
            ],
        )
    ],
    [
        ChatMessageContent(
            role="assistant",
            content=None,
            tool_calls=[
                FunctionCallContent(
                    id="call_3",
                    name="identify_fallacies",
                    arguments=json.dumps(
                        {
                            "fallacies": [
                                {
                                    "fallacy_type": "Ad Hominem",
                                    "problematic_quote": "Ne l'écoutez pas...",
                                    "explanation": "Attaque la personne.",
                                }
                            ]
                        }
                    ),
                )
            ],
        )
    ],
]

# Le LLM identifie directement le sophisme sans exploration.
MOCK_SIMPLE_WORKFLOW_RESPONSE = [
    [
        ChatMessageContent(
            role="assistant",
            content=None,
            tool_calls=[
                FunctionCallContent(
                    id="call_1",
                    name="identify_fallacies",
                    arguments=json.dumps(
                        {
                            "fallacies": [
                                {
                                    "fallacy_type": "Ad Hominem",
                                    "problematic_quote": "Ne l'écoutez pas...",
                                    "explanation": "Attaque la personne.",
                                }
                            ]
                        }
                    ),
                )
            ],
        )
    ],
]


@pytest.fixture(
    params=[
        ("complex_workflow", None, MOCK_COMPLEX_WORKFLOW_RESPONSE, 3),
        (
            "simple_workflow_only",
            ["identify_fallacies"],
            MOCK_SIMPLE_WORKFLOW_RESPONSE,
            1,
        ),
    ]
)
def case_config(request):
    """Fixture paramétrée pour fournir les configurations de test."""
    return request.param


@pytest.fixture
def informal_fallacy_plugin(case_config):
    """Fixture pour le plugin, configuré selon le cas de test."""
    _, allowed_ops, _, _ = case_config
    return ComplexFallacyAnalyzer()  # Pas d'allowed_operations dans le constructeur


@pytest.fixture
def mock_chat_completion_service(case_config):
    """Fixture pour le service de chat mocké, configuré avec les réponses attendues."""
    _, _, mock_responses, _ = case_config
    # Créer un mock qui respecte le type attendu par Pydantic
    service = MagicMock(spec=ChatCompletionClientBase)
    service.get_chat_message_contents = AsyncMock(side_effect=mock_responses)
    # Correction pour la validation interne du kernel
    service.get_prompt_execution_settings_class.return_value = PromptExecutionSettings
    # L'id du service est maintenant géré par le kernel, mais on peut le garder pour la fixture
    service.service_id = "test_service"
    return service


# ARCHIVED: 3 tests removed (2026-02-17)
# - test_agent_workflow_with_different_configurations: ComplexFallacyAnalyzer API refactored
# - test_parallel_exploration_workflow_unit: parallel_exploration method removed
# - test_informal_fallacy_agent_uses_parallel_exploration: parallel_exploration method removed


# --- Tests pour AgentFactory ---


@pytest.fixture
def kernel():
    """
    Crée un kernel réel léger avec un service de chat mocké,
    prêt pour les tests de la factory.
    """
    kernel = Kernel()
    mock_service = MagicMock(spec=ChatCompletionClientBase)

    # Correction pour la validation interne du kernel
    mock_service.get_prompt_execution_settings_class.return_value = (
        PromptExecutionSettings
    )

    # CRUCIAL: L'attribut 'service_id' doit exister sur le mock AVANT de l'ajouter au kernel.
    # Le kernel l'utilise comme clé.
    mock_service.service_id = "test_service"

    # Correction de l'API: plus de 'service_id' dans l'appel
    kernel.add_service(mock_service)

    return kernel


@pytest.mark.parametrize(
    "config_name, expected_plugin_names",
    [
        ("simple", ["FallacyIdentificationPlugin"]),
        ("explore_only", ["TaxonomyDisplayPlugin"]),
        ("workflow_only", ["FallacyWorkflowPlugin", "TaxonomyDisplayPlugin"]),
        (
            "full",
            [
                "FallacyIdentificationPlugin",
                "FallacyWorkflowPlugin",
                "TaxonomyDisplayPlugin",
            ],
        ),
    ],
)
def test_agent_factory_configurations(kernel, config_name, expected_plugin_names):
    """
    Vérifie que la factory crée des agents avec le bon ensemble de plugins pour chaque configuration.
    Ceci est une "Théorie" de test qui valide l'architecture configurable.
    """
    # --- Arrange ---
    settings = AppSettings()
    settings.service_manager.default_llm_service_id = "test_service"
    factory = AgentFactory(kernel, settings)

    # --- Act ---
    agent = factory.create_agent(AgentType.INFORMAL_FALLACY, config_name=config_name)

    # Récupère les types des plugins réellement chargés dans le kernel de l'agent
    # L'API a changé, les plugins sont maintenant dans le kernel
    # On vérifie les NOMS des plugins enregistrés dans le kernel de l'agent
    loaded_plugin_names = list(agent.kernel.plugins.keys())

    # --- Assert ---
    # Utiliser un set pour comparer l'égalité sans se soucier de l'ordre
    assert set(loaded_plugin_names) == set(expected_plugin_names), (
        f"Mismatch in plugins for config '{config_name}'.\n"
        f"Expected: {sorted(expected_plugin_names)}\n"
        f"Got:      {sorted(loaded_plugin_names)}"
    )
