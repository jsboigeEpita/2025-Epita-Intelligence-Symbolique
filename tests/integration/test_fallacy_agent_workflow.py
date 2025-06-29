# Fichier : tests/integration/test_fallacy_agent_workflow.py
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from semantic_kernel.functions.kernel_arguments import KernelArguments
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.function_call_content import FunctionCallContent
from semantic_kernel.contents.function_result_content import FunctionResultContent
from semantic_kernel.tools.function_view import FunctionView
from semantic_kernel.agents.chat_completion.chat_completion_agent import ChatCompletionAgent

from argumentation_analysis.agents.plugins.fallacy_identification_plugin import FallacyIdentificationPlugin

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

@pytest.mark.asyncio
async def test_parallel_exploration_workflow():
    """
    Teste le workflow d'exploration parallèle en s'assurant que le plugin
    invoque correctement le kernel injecté.
    """
    # 1. Configuration des Mocks
    mock_kernel = AsyncMock(spec=Kernel)
    
    # Simuler la recherche de la fonction par le plugin
    mock_display_function = MagicMock()
    mock_kernel.plugins = {
        "TaxonomyDisplayPlugin": {"display_branch": mock_display_function}
    }
    
    # Le kernel, quand il est invoqué, retourne un résultat simulé.
    async def invoke_side_effect(*args, **kwargs):
        # Le premier argument de invoke est la fonction, le deuxième les arguments.
        # On peut simuler des retours différents selon les arguments si besoin.
        called_args = args[1]
        return f"Résultat pour le noeud {called_args['node_id']}"
        
    mock_kernel.invoke.side_effect = invoke_side_effect

    # 2. Instanciation du Plugin à tester
    workflow_plugin = FallacyWorkflowPlugin(kernel=mock_kernel)

    # 3. Exécution de la méthode à tester
    # C'est un test d'unité sur le plugin, on appelle la méthode directement.
    result_json = await workflow_plugin.parallel_exploration(
        nodes=['relevance', 'clarity'],
        depth=2
    )
    
    # 4. Assertions
    # Vérifier que le kernel a été appelé deux fois
    assert mock_kernel.invoke.call_count == 2

    # Vérifier que les appels ont été faits avec les bons arguments
    mock_kernel.invoke.assert_any_call(
        mock_display_function,
        KernelArguments(node_id='relevance', depth=2, taxonomy=workflow_plugin.taxonomy.get_full_taxonomy_json())
    )
    mock_kernel.invoke.assert_any_call(
        mock_display_function,
        KernelArguments(node_id='clarity', depth=2, taxonomy=workflow_plugin.taxonomy.get_full_taxonomy_json())
    )

    # Vérifier que le résultat est correctement agrégé
    result_data = json.loads(result_json)
    assert result_data["branch_relevance"] == "Résultat pour le noeud relevance"
    assert result_data["branch_clarity"] == "Résultat pour le noeud clarity"