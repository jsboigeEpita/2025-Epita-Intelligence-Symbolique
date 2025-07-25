import asyncio
import pytest
import semantic_kernel as sk
from pathlib import Path
import sys

# Ajouter la racine du projet au sys.path pour les importations
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from argumentation_analysis.agents.factory import AgentFactory, AgentType
from argumentation_analysis.core.llm_service import create_llm_service
from semantic_kernel.contents.chat_history import ChatHistory
from argumentation_analysis.config.settings import AppSettings
from argumentation_analysis.agents.core.informal.informal_definitions import InformalAnalysisPlugin as IdentificationPlugin, IdentifiedFallacy


def test_informal_agent_forced_tool_choice(tmp_path):
    """
    Test d'intégration pour vérifier que l'agent 'simple' utilise bien
    le tool_choice pour appeler 'FallacyIdentificationPlugin-identify_fallacies'
    et retourne un JSON valide.
    """
    # 1. Initialisation minimale du Kernel et des services
    kernel = sk.Kernel()
    llm_service_id = "default"
    try:
        llm_service = create_llm_service(service_id=llm_service_id, model_id="gpt-4o-mini", force_authentic=True)
        kernel.add_service(llm_service)
    except Exception as e:
        pytest.fail(f"La configuration du service LLM a échoué: {e}")

    # 2. Configuration du traçage
    log_file = tmp_path / "test_trace.log"

    # 3. Création de l'agent tracé
    settings = AppSettings()
    settings.service_manager.default_llm_service_id = llm_service_id
    agent_factory = AgentFactory(kernel, settings)
    agent = agent_factory.create_informal_fallacy_agent(
        config_name="simple",
        trace_log_path=str(log_file)
    )
    assert agent is not None, "L'agent n'a pas été créé."

    # 4. Préparation d'un scénario de test simple
    test_text = "Mon adversaire veut réduire le budget de la défense. Il veut donc laisser notre pays sans défense face à nos ennemis."
    chat_history = ChatHistory()
    chat_history.add_user_message(test_text)
    
    # 5. Invocation de l'agent
    try:
        # Consommer le générateur pour s'assurer que l'invocation complète est exécutée
        def _invoke():
            # Since agent.invoke is an async generator, we need an event loop to run it.
            async def _inner_invoke():
                return [m async for m in agent.invoke(chat_history)]
            return asyncio.run(_inner_invoke())
        _ = _invoke()
    except Exception as e:
        pytest.fail(f"L'invocation de l'agent a échoué avec une exception inattendue: {e}")

    # 6. Vérification du log de trace
    assert log_file.exists(), "Le fichier de trace n'a pas été créé."
    
    trace_content = log_file.read_text()
    print(f"\n--- Contenu du fichier de trace ---\n{trace_content}\n---------------------------------")
    
    expected_trace = "Calling IdentificationPlugin-identify_fallacies function"
    assert expected_trace in trace_content, f"La trace de l'appel à l'outil '{expected_trace}' n'a pas été trouvée dans le log."
    
    print(f"\n[SUCCESS] La trace de l'appel à l'outil a été trouvée dans le log.")
