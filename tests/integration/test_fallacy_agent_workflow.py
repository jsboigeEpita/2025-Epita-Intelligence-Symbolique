# Fichier : tests/integration/test_fallacy_agent_workflow.py
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from argumentation_analysis.agents.factory import AgentFactory, AgentType
from argumentation_analysis.agents.plugins.fallacy_workflow_plugin import FallacyWorkflowPlugin
from argumentation_analysis.agents.plugins.taxonomy_display_plugin import TaxonomyDisplayPlugin

from semantic_kernel.kernel import Kernel
from semantic_kernel.functions.kernel_arguments import KernelArguments
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.function_call_content import FunctionCallContent
from semantic_kernel.contents.function_result_content import FunctionResultContent
# from semantic_kernel.tools.function_view import FunctionView
from semantic_kernel.agents.chat_completion.chat_completion_agent import ChatCompletionAgent, AgentResponseItem
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.connectors.ai.prompt_execution_settings import PromptExecutionSettings

from argumentation_analysis.agents.tools.analysis.complex_fallacy_analyzer import ComplexFallacyAnalyzer as IdentificationPlugin

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
    return IdentificationPlugin(allowed_operations=allowed_ops)

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
    # Pour que la validation Pydantic fonctionne, on doit créer un vrai Kernel
    # et y attacher le service mocké.
    kernel = Kernel()
    kernel.add_service(mock_chat_completion_service)

    agent = ChatCompletionAgent(
        kernel=kernel,
        service=mock_chat_completion_service, # On passe le service explicitement
        plugins=[informal_fallacy_plugin],
        instructions="Test instructions"
    )


    # --- Exécution et Assertions ---
    chat_history = ChatHistory()
    chat_history.add_user_message("Analyse ce texte : Ne l'écoutez pas, c'est un idiot.")
    
    final_answer = []
    # L'agent invoke retourne une boucle. On doit simuler le retour des appels de fonction
    # pour que l'agent continue son exécution jusqu'à la fin.
    async for message_item in agent.invoke(chat_history):
        final_answer.append(message_item)
        inner_content = message_item.message
        # Si le LLM demande un appel de fonction, on le simule et on ajoute le résultat à l'historique
        if inner_content.tool_calls:
            for tool_call in inner_content.tool_calls:
                # Dans ce test, on se contente de valider que les fonctions sont appelées.
                # On fournit un résultat générique pour que l'agent puisse continuer.
                result = FunctionResultContent(
                    id=tool_call.id,
                    name=tool_call.name,
                    result='{"status": "Function call simulated by test."}'
                )
                chat_history.add_message(result)


    # Vérifier que le service a été appelé le bon nombre de fois
    assert mock_chat_completion_service.get_chat_message_contents.call_count == expected_call_count, \
        f"Test case '{config_name}' failed: incorrect number of LLM calls."
    
    # La dernière réponse de l'agent n'est plus un FunctionResultContent directement
    # mais un ChatMessageContent de l'assistant après avoir traité la dernière fonction.
    # On vérifie ici la dernière interaction.
    last_agent_message = final_answer[-1].message
    assert last_agent_message.role == "assistant"
    # La dernière interaction du LLM est de faire un appel à la fonction `identify_fallacies`
    assert len(last_agent_message.tool_calls) > 0
    assert last_agent_message.tool_calls[0].name == "identify_fallacies"

# --- Tests pour le FallacyWorkflowPlugin ---
from argumentation_analysis.agents.plugins.fallacy_workflow_plugin import FallacyWorkflowPlugin


@pytest.mark.asyncio
async def test_parallel_exploration_workflow_unit():
    """
    Teste le workflow d'exploration parallèle en s'assurant que le plugin
    invoque correctement le kernel injecté (Test d'unité).
    Version corrigée pour éviter les problèmes de patch sur un objet Pydantic (Kernel).
    """
    # 1. Configuration des Mocks
    # On mocke entièrement le kernel pour ne pas dépendre de son implémentation Pydantic.
    mock_kernel = MagicMock(spec=Kernel)
    
    # Préparer le mock de la fonction noyau qui sera retournée
    mock_display_function = MagicMock()

    # Le kernel doit retourner notre fonction mockée lorsqu'on la recherche
    mock_kernel.plugins.get_function.return_value = mock_display_function

    # Définir le comportement du mock pour la méthode invoke
    async def invoke_side_effect(func, arguments):
        # La fonction passée devrait être celle que nous avons mockée.
        assert func == mock_display_function
        node_id = arguments['node_id']
        # On simule le retour de l'invocation du kernel
        return MagicMock(value=f"Résultat pour le noeud {node_id}")
    
    # Attacher l'AsyncMock directement au mock du kernel
    mock_kernel.invoke = AsyncMock(side_effect=invoke_side_effect)

    # 2. Instanciation du Plugin à tester
    workflow_plugin = FallacyWorkflowPlugin(kernel=mock_kernel)

    # 3. Exécution de la méthode à tester
    result_json = await workflow_plugin.parallel_exploration(
        nodes=['relevance', 'clarity'],
        depth=2
    )
    
    # 4. Assertions
    assert mock_kernel.invoke.call_count == 2
    assert mock_kernel.plugins.get_function.call_count == 2 # Doit chercher la fonction à chaque fois

    taxonomy_json = workflow_plugin.taxonomy.get_full_taxonomy_json()
    
    # Arguments attendus pour chaque appel
    relevance_args = KernelArguments(node_id='relevance', depth=2, taxonomy=taxonomy_json)
    clarity_args = KernelArguments(node_id='clarity', depth=2, taxonomy=taxonomy_json)

    # Vérification des appels
    mock_kernel.invoke.assert_any_call(mock_display_function, relevance_args)
    mock_kernel.invoke.assert_any_call(mock_display_function, clarity_args)

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
    mock_service = MagicMock(spec=ChatCompletionClientBase)
    mock_service.get_chat_message_contents = AsyncMock(side_effect=MOCK_MULTI_EXPLORE_RESPONSE)
    # Nécessaire pour la validation Pydantic interne
    mock_service.get_prompt_execution_settings_class.return_value = PromptExecutionSettings
    mock_service.service_id = "test_service"

    # --- Initialisation de l'Agent ---
    # On utilise la même approche que pour le premier test pour la validation Pydantic
    kernel = Kernel()
    kernel.add_service(mock_service)
    
    # On a besoin des deux plugins pour ce workflow
    workflow_plugin = FallacyWorkflowPlugin(kernel=kernel)
    identification_plugin = IdentificationPlugin()
    
    agent = ChatCompletionAgent(
        kernel=kernel,
        service=mock_service,
        plugins=[workflow_plugin, identification_plugin],
        instructions="Test instructions"
    )

    # --- Exécution et Assertions ---
    chat_history = ChatHistory()
    chat_history.add_user_message("Compare les sophismes de pertinence et d'ambiguité.")
    
    final_answer = []
    all_messages = []
    async for message in agent.invoke(chat_history):
        all_messages.append(message)
        inner_content = message.message
        # Si le LLM demande un appel de fonction (tool_call), on le simule et on ajoute le résultat à l'historique
        if inner_content.tool_calls:
            for tool_call in inner_content.tool_calls:
                # Simuler le résultat de la fonction `parallel_exploration`
                if tool_call.name == "parallel_exploration":
                    result_content = '{"branch_relevance": "...", "branch_ambiguity": "..."}'
                else:
                    result_content = '{"status": "Function call simulated."}'
                
                result = FunctionResultContent(
                    id=tool_call.id,
                    name=tool_call.name,
                    result=result_content
                )
                chat_history.add_message(result)
        
    # Vérifier que le service a été appelé deux fois (1. explore, 2. identify)
    assert mock_service.get_chat_message_contents.call_count == 2
    
    # Vérifier que la première décision du LLM était bien d'explorer en parallèle
    first_call_content = mock_service.get_chat_message_contents.call_args_list[0].kwargs['chat_history']
    last_message = first_call_content[-1]
    assert isinstance(last_message, ChatMessageContent)
    assert last_message.tool_calls[0].name == "parallel_exploration"
    
    # Vérifier la réponse finale
    final_tool_call = all_messages[-1].message.tool_calls[0]
    assert final_tool_call.name == "identify_fallacies"

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
    mock_service.get_prompt_execution_settings_class.return_value = PromptExecutionSettings
    
    # CRUCIAL: L'attribut 'service_id' doit exister sur le mock AVANT de l'ajouter au kernel.
    # Le kernel l'utilise comme clé.
    mock_service.service_id = "test_service"

    # Correction de l'API: plus de 'service_id' dans l'appel
    kernel.add_service(mock_service)
    
    return kernel

@pytest.mark.parametrize(
    "config_name, expected_plugin_types",
    [
        ("simple", [IdentificationPlugin]),
        ("explore_only", [TaxonomyDisplayPlugin]),
        ("workflow_only", [FallacyWorkflowPlugin, TaxonomyDisplayPlugin]),
        ("full", [IdentificationPlugin, FallacyWorkflowPlugin, TaxonomyDisplayPlugin]),
    ],
)
def test_agent_factory_configurations(kernel, config_name, expected_plugin_types):
    """
    Vérifie que la factory crée des agents avec le bon ensemble de plugins pour chaque configuration.
    Ceci est une "Théorie" de test qui valide l'architecture configurable.
    """
    # --- Arrange ---
    factory = AgentFactory(kernel, llm_service_id="test_service")

    # --- Act ---
    agent = factory.create_agent(AgentType.INFORMAL_FALLACY, config_name=config_name)
    
    # Récupère les types des plugins réellement chargés dans le kernel de l'agent
    # L'API a changé, les plugins sont maintenant dans le kernel
    loaded_plugin_types = [type(p) for p in agent.kernel.plugins]

    # --- Assert ---
    assert len(loaded_plugin_types) == len(expected_plugin_types)
    
    # Vérifie que tous les plugins attendus (et uniquement ceux-là) sont présents
    for plugin_type in expected_plugin_types:
        assert plugin_type in loaded_plugin_types

    # Vérification inverse pour s'assurer qu'il n'y a pas de surplus
    for plugin_type in loaded_plugin_types:
        assert plugin_type in expected_plugin_types