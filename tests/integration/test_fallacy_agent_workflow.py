# Fichier : tests/integration/test_fallacy_agent_workflow.py
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from argumentation_analysis.agents.agent_factory import AgentFactory
from argumentation_analysis.agents.plugins.fallacy_workflow_plugin import FallacyWorkflowPlugin
from argumentation_analysis.agents.plugins.taxonomy_display_plugin import TaxonomyDisplayPlugin

from semantic_kernel.functions import KernelArguments
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.function_call_content import FunctionCallContent
from semantic_kernel.contents.function_result_content import FunctionResultContent
# from semantic_kernel.tools.function_view import FunctionView
from semantic_kernel.agents.chat_completion.chat_completion_agent import ChatCompletionAgent

from argumentation_analysis.agents.plugins.identification_plugin import IdentificationPlugin

# --- Mocks de Réponses du LLM ---

# Le LLM explore la racine, puis une branche, puis identifie.
MOCK_COMPLEX_WORKFLOW_RESPONSE = [
    [ChatMessageContent(role="assistant", content=None, tool_calls=[FunctionCallContent(id="call_1", name="explore_branch", arguments={'node_id': 'fallacy_root'})])],
    [ChatMessageContent(role="assistant", content=None, tool_calls=[FunctionCallContent(id="call_2", name="explore_branch", arguments={'node_id': 'relevance'})])],
    [ChatMessageContent(role="assistant", content=None, tool_calls=[FunctionCallContent(id="call_3", name="identify_fallacies", arguments=json.dumps({"fallacies": [{"fallacy_type": "Ad Hominem", "problematic_quote": "Ne l'écoutez pas...", "explanation": "Attaque la personne."}]}))])],
]

# Le LLM identifie directement le sophisme sans exploration.
MOCK_SIMPLE_WORKFLOW_RESPONSE = [
    [ChatMessageContent(role="assistant", content=None, tool_calls=[FunctionCallContent(id="call_1", name="identify_fallacies", arguments=json.dumps({"fallacies": [{"fallacy_type": "Ad Hominem", "problematic_quote": "Ne l'écoutez pas...", "explanation": "Attaque la personne."}]}))])],
]

@pytest.fixture(params=[
    ("complex_workflow", None, MOCK_COMPLEX_WORKFLOW_RESPONSE, 3),
    ("simple_workflow_only", ["identify_fallacies"], MOCK_SIMPLE_WORKFLOW_RESPONSE, 1),
])
def case_config(request):
    """Fixture paramétrée pour fournir les configurations de test."""
    return request.param

@pytest.fixture
def informal_fallacy_plugin(case_config):
    """Fixture pour le plugin, configuré selon le cas de test."""
    _, allowed_ops, _, _ = case_config
    return FallacyIdentificationPlugin(allowed_operations=allowed_ops)

@pytest.fixture
def mock_chat_completion_service(case_config):
    """Fixture pour le service de chat mocké, configuré avec les réponses attendues."""
    _, _, mock_responses, _ = case_config
    service = MagicMock()
    service.get_chat_message_contents = AsyncMock(side_effect=mock_responses)
    return service

@pytest.mark.asyncio
async def test_agent_workflow_with_different_configurations(
    informal_fallacy_plugin, mock_chat_completion_service, case_config
):
    """
    Teste si l'agent suit le bon workflow (simple ou complexe) en fonction
    de la configuration du plugin.
    """
    # --- Configuration du Test ---
    config_name, _, _, expected_call_count = case_config
    
    # --- Initialisation de l'Agent ---
    with patch("semantic_kernel.kernel.Kernel.add_plugin", return_value=None):
         agent = ChatCompletionAgent(
            service_id="test_service",
            kernel=MagicMock(),
            plugins=[informal_fallacy_plugin],
            instructions="Test instructions"
        )
         # On doit manuellement lier le service mocké car le kernel est mocké
         agent._chat_completion = mock_chat_completion_service


    # --- Exécution et Assertions ---
    chat_history = ChatHistory()
    chat_history.add_user_message("Analyse ce texte : Ne l'écoutez pas, c'est un idiot.")
    
    final_answer = []
    async for message in agent.invoke(chat_history):
        final_answer.append(message)
        
    # Vérifier que le service a été appelé le bon nombre de fois
    assert mock_chat_completion_service.get_chat_message_contents.call_count == expected_call_count, \
        f"Test case '{config_name}' failed: incorrect number of LLM calls."
    
    # Vérifier la dernière réponse qui doit être le résultat de la fonction
    last_message = final_answer[-1]
    assert isinstance(last_message, FunctionResultContent)
    assert last_message.name == "identify_fallacies"
    assert "Validation réussie" in last_message.result

# --- Tests pour le FallacyWorkflowPlugin ---
from argumentation_analysis.agents.plugins.fallacy_workflow_plugin import FallacyWorkflowPlugin


@pytest.mark.asyncio
async def test_parallel_exploration_workflow_unit():
    """
    Teste le workflow d'exploration parallèle en s'assurant que le plugin
    invoque correctement le kernel injecté (Test d'unité).
    """
    # 1. Configuration des Mocks
    mock_kernel = AsyncMock(spec=Kernel)
    
    # Simuler la recherche de la fonction par le plugin
    mock_display_function = MagicMock()
    # Le nom de la fonction est 'DisplayBranch' (majuscule) comme défini dans les prompts
    mock_kernel.plugins = {
        "TaxonomyDisplayPlugin": {"DisplayBranch": mock_display_function}
    }
    
    # Le kernel, quand il est invoqué, retourne un résultat simulé.
    # Le résultat est un `ChatMessageContent` donc on simule un objet avec un attribut `value`
    async def invoke_side_effect(*args, **kwargs):
        called_args = args[1]
        node_id = called_args['node_id']
        return MagicMock(value=f"Résultat pour le noeud {node_id}")
        
    mock_kernel.invoke.side_effect = invoke_side_effect

    # 2. Instanciation du Plugin à tester
    workflow_plugin = FallacyWorkflowPlugin(kernel=mock_kernel)

    # 3. Exécution de la méthode à tester
    result_json = await workflow_plugin.parallel_exploration(
        nodes=['relevance', 'clarity'],
        depth=2
    )
    
    # 4. Assertions
    assert mock_kernel.invoke.call_count == 2

    taxonomy_json = workflow_plugin.taxonomy.get_full_taxonomy_json()
    mock_kernel.invoke.assert_any_call(
        mock_display_function,
        KernelArguments(node_id='relevance', depth=2, taxonomy=taxonomy_json)
    )
    mock_kernel.invoke.assert_any_call(
        mock_display_function,
        KernelArguments(node_id='clarity', depth=2, taxonomy=taxonomy_json)
    )

    result_data = json.loads(result_json)
    assert result_data["branch_relevance"] == "Résultat pour le noeud relevance"
    assert result_data["branch_clarity"] == "Résultat pour le noeud clarity"

# --- Test d'Intégration de l'Agent avec le Workflow Parallèle ---

# Le LLM explore plusieurs branches, puis identifie.
MOCK_MULTI_EXPLORE_RESPONSE = [
    # Premier appel: le LLM décide de faire une exploration parallèle
    [ChatMessageContent(role="assistant", content=None, tool_calls=[
        FunctionCallContent(
            id="call_multi",
            name="parallel_exploration",
            arguments=json.dumps({'nodes': ['relevance', 'ambiguity']})
        )
    ])],
    # Deuxième appel: Le LLM a reçu les résultats et identifie le sophisme
    [ChatMessageContent(role="assistant", content=None, tool_calls=[
        FunctionCallContent(
            id="call_final",
            name="identify_fallacies",
            arguments=json.dumps({"fallacies": [{"fallacy_type": "Equivocation", "problematic_quote": "...", "explanation": "..."}]})
        )
    ])],
]

@pytest.mark.asyncio
async def test_informal_fallacy_agent_uses_parallel_exploration():
    """
    Teste si l'agent utilise le workflow d'exploration multiple de bout en bout.
    """
    # --- Configuration du Test ---
    mock_service = MagicMock()
    mock_service.get_chat_message_contents = AsyncMock(side_effect=MOCK_MULTI_EXPLORE_RESPONSE)

    # --- Initialisation de l'Agent ---
    # On a besoin des deux plugins pour ce workflow
    mock_kernel_for_plugin = MagicMock(spec=Kernel) # Kernel simple pour l'instanciation
    workflow_plugin = FallacyWorkflowPlugin(kernel=mock_kernel_for_plugin)
    identification_plugin = FallacyIdentificationPlugin()
    
    agent = ChatCompletionAgent(
        service_id="test_service",
        kernel=MagicMock(),
        plugins=[workflow_plugin, identification_plugin],
        instructions="Test instructions"
    )
    # On lie le service mocké qui simule les choix du LLM
    agent._chat_completion = mock_service

    # --- Exécution et Assertions ---
    chat_history = ChatHistory()
    chat_history.add_user_message("Compare les sophismes de pertinence et d'ambiguité.")
    
    final_answer = []
    async for message in agent.invoke(chat_history):
        # On simule ici la réponse de notre fonction `parallel_exploration`
        if isinstance(message, FunctionCallContent) and message.name == "parallel_exploration":
            result = FunctionResultContent(
                id=message.id,
                name=message.name,
                result='{"branch_relevance": "...", "branch_ambiguity": "..."}'
            )
            chat_history.add(result)
        final_answer.append(message)
        
    # Vérifier que le service a été appelé deux fois (1. explore, 2. identify)
    assert mock_service.get_chat_message_contents.call_count == 2
    
    # Vérifier que la première décision du LLM était bien d'explorer en parallèle
    first_call_content = mock_service.get_chat_message_contents.call_args_list[0].kwargs['chat_history']
    last_message = first_call_content[-1]
    assert isinstance(last_message, ChatMessageContent)
    assert last_message.tool_calls[0].name == "parallel_exploration"
    
    # Vérifier la réponse finale
    last_message = final_answer[-1]
    assert isinstance(last_message, FunctionResultContent)
    assert last_message.name == "identify_fallacies"

# --- Tests pour AgentFactory ---

@pytest.fixture
def kernel():
    """Crée un mock ou un kernel réel léger pour les tests."""
    from semantic_kernel.kernel import Kernel
    return Kernel()

@pytest.mark.parametrize(
    "config_name, expected_plugin_types",
    [
        ("simple", [FallacyIdentificationPlugin]),
        ("explore_only", [TaxonomyDisplayPlugin]),
        ("workflow_only", [FallacyWorkflowPlugin, TaxonomyDisplayPlugin]),
        ("full", [FallacyIdentificationPlugin, FallacyWorkflowPlugin, TaxonomyDisplayPlugin]),
    ],
)
def test_agent_factory_configurations(kernel, config_name, expected_plugin_types):
    """
    Vérifie que la factory crée des agents avec le bon ensemble de plugins pour chaque configuration.
    Ceci est une "Théorie" de test qui valide l'architecture configurable.
    """
    # --- Arrange ---
    factory = AgentFactory(kernel)

    # --- Act ---
    agent = factory.create_informal_fallacy_agent(config_name=config_name)
    
    # Récupère les types des plugins réellement chargés dans l'agent
    loaded_plugin_types = [type(p) for p in agent.plugins]

    # --- Assert ---
    assert len(loaded_plugin_types) == len(expected_plugin_types)
    
    # Vérifie que tous les plugins attendus (et uniquement ceux-là) sont présents
    for plugin_type in expected_plugin_types:
        assert plugin_type in loaded_plugin_types

    # Vérification inverse pour s'assurer qu'il n'y a pas de surplus
    for plugin_type in loaded_plugin_types:
        assert plugin_type in expected_plugin_types