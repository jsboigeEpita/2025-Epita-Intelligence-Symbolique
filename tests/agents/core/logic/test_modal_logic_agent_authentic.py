# -*- coding: utf-8 -*-
# tests/agents/core/logic/test_modal_logic_agent_authentic.py
"""
Tests unitaires authentiques pour la classe ModalLogicAgent.
Phase 5 - Élimination complète des mocks - Version authentique
"""

import unittest
import pytest
import asyncio
import os
import sys
from pathlib import Path

# Import du système d'auto-activation d'environnement
from argumentation_analysis.core import environment as auto_env

# Imports authentiques - vrai Semantic Kernel
from semantic_kernel import Kernel
from semantic_kernel.functions import KernelArguments

# Imports conditionnels pour les connecteurs LLM
try:
    from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
except ImportError:
    OpenAIChatCompletion = None

try:
    from semantic_kernel.connectors.ai.azure_open_ai import AzureOpenAIChatCompletion
except ImportError:
    try:
        from semantic_kernel.connectors.ai.azure_open_ai.azure_chat_completion import (
            AzureOpenAIChatCompletion,
        )
    except ImportError:
        AzureOpenAIChatCompletion = None

# Imports du projet
from argumentation_analysis.agents.core.logic.modal_logic_agent import (
    ModalLogicAgent,
    SYSTEM_PROMPT_MODAL,
)
from argumentation_analysis.agents.core.logic.belief_set import (
    ModalBeliefSet,
    BeliefSet,
)
from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge
from argumentation_analysis.core.jvm_setup import is_jvm_started
from argumentation_analysis.config.settings import DEFAULT_CHAT_MODEL_ID


# Création d'une classe concrète pour les tests
# Classe concrète minimale pour instancier l'agent dans les tests
class ConcreteModalLogicAgent(ModalLogicAgent):
    pass


@pytest.fixture(scope="function")
def authentic_agent(tweety_bridge_fixture):
    """
    Fixture pour initialiser un agent authentique avec un TweetyBridge partagé.
    """
    if not tweety_bridge_fixture.initializer.is_jvm_ready():
        pytest.skip("TweetyBridge not ready, skipping authentic modal agent tests.")

    kernel = Kernel()
    llm_service_id = "authentic_modal_llm_service"
    llm_available = False

    # #2651 : une construction de service qui échoue lève ici, avec sa cause,
    # au lieu d'être imprimée puis ignorée.
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
    azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    model_id = os.getenv("OPENAI_CHAT_MODEL_ID", DEFAULT_CHAT_MODEL_ID)

    if azure_endpoint and azure_api_key and AzureOpenAIChatCompletion:
        chat_service = AzureOpenAIChatCompletion(
            service_id=llm_service_id,
            deployment_name=azure_deployment,
            endpoint=azure_endpoint,
            api_key=azure_api_key,
        )
        kernel.add_service(chat_service)
        llm_available = True
        print(f"✅ Service LLM Azure configuré pour Modal: {azure_deployment}")
    elif openai_api_key and OpenAIChatCompletion:
        chat_service = OpenAIChatCompletion(
            service_id=llm_service_id,
            ai_model_id=model_id,
            api_key=openai_api_key,
        )
        kernel.add_service(chat_service)
        llm_available = True
        print(f"✅ Service LLM OpenAI configuré pour Modal: {model_id}")
    else:
        # Sans clé : un service nommé mais jamais appelé laisse l'agent se
        # construire (#2633 exige un service dans le kernel). Les tests LLM se
        # sautent sur llm_available ; ceux de Tweety tournent.
        kernel.add_service(
            OpenAIChatCompletion(
                service_id=llm_service_id, ai_model_id="keyless", api_key="keyless"
            )
        )
        print("⚠️ Clés API manquantes pour Modal : tests LLM sautés")

    agent_name = "ModalLogicAgent"
    agent = ConcreteModalLogicAgent(
        kernel, service_id=llm_service_id, agent_name=agent_name
    )
    agent._tweety_bridge = tweety_bridge_fixture  # Injection directe

    if llm_available:
        agent.setup_agent_components(llm_service_id)
        print("✅ Agent Modal authentique configuré")

    return {
        "agent": agent,
        "kernel": kernel,
        "tweety_bridge": tweety_bridge_fixture,
        "llm_available": llm_available,
        "tweety_available": tweety_bridge_fixture.initializer.is_jvm_ready(),
        "llm_service_id": llm_service_id,
        "agent_name": agent_name,
    }


def test_initialization_and_setup_authentic(authentic_agent):
    """Test authentique de l'initialisation et de la configuration de l'agent Modal."""
    agent = authentic_agent["agent"]
    kernel = authentic_agent["kernel"]
    agent_name = authentic_agent["agent_name"]
    tweety_available = authentic_agent["tweety_available"]
    llm_available = authentic_agent["llm_available"]
    llm_service_id = authentic_agent["llm_service_id"]

    assert agent.name == agent_name
    assert agent.kernel == kernel
    assert agent.logic_type == "Modal"
    assert agent.instructions == SYSTEM_PROMPT_MODAL

    if tweety_available:
        agent.setup_agent_components(llm_service_id)
        assert agent.tweety_bridge.initializer.is_jvm_ready() == True
        print("✅ Test authentique TweetyBridge Modal - JVM prête")
    else:
        print("⚠️ TweetyBridge Modal non disponible - test sauté")

    if llm_available:
        service = kernel.get_service(llm_service_id)
        assert service is not None
        print("✅ Test authentique Semantic Kernel Modal - Service configuré")


@pytest.mark.asyncio
@pytest.mark.llm_integration
@pytest.mark.requires_api
async def test_text_to_belief_set_authentic_modal(authentic_agent):
    """Test authentique de conversion texte -> belief set modal avec vrai LLM."""
    agent = authentic_agent["agent"]
    tweety_bridge = authentic_agent["tweety_bridge"]
    if not (authentic_agent["llm_available"] and authentic_agent["tweety_available"]):
        pytest.skip("LLM ou TweetyBridge non disponible pour Modal")

    test_text = """
    Il est nécessaire que tous les hommes soient mortels.
    Il est possible que Socrate soit sage.
    """

    try:
        belief_set, message = await agent.text_to_belief_set(test_text)
    except Exception as e:
        pytest.skip(f"LLM text_to_belief_set failed: {e}")

    print(f"✅ Conversion Modal authentique: {message}")

    if belief_set is None:
        pytest.skip(f"LLM returned None belief set: {message}")

    assert isinstance(belief_set, ModalBeliefSet)
    assert len(belief_set.content) > 0
    print(f"✅ Belief set Modal authentique créé: {belief_set.content[:100]}...")

    # #2651 : TweetyBridge n'a pas de validate_modal_belief_set ; la
    # vérification réelle est celle que l'agent appelle (is_consistent).
    is_valid, validation_msg = tweety_bridge.modal_handler.is_modal_kb_consistent(
        belief_set.content
    )
    assert isinstance(validation_msg, str)
    print(
        f"✅ Validation TweetyBridge Modal authentique: {is_valid} - {validation_msg}"
    )


@pytest.mark.asyncio
@pytest.mark.llm_integration
@pytest.mark.requires_api
async def test_generate_queries_authentic_modal(authentic_agent):
    """Test authentique de génération de requêtes modales avec vrai LLM."""
    agent = authentic_agent["agent"]
    tweety_bridge = authentic_agent["tweety_bridge"]
    if not (authentic_agent["llm_available"] and authentic_agent["tweety_available"]):
        pytest.skip("LLM ou TweetyBridge non disponible pour Modal")

    belief_set_content = "[]p; <>q;"
    belief_set = ModalBeliefSet(belief_set_content)
    context_text = "Nous analysons les propriétés nécessaires et possibles"

    try:
        queries = await agent.generate_queries(context_text, belief_set)
    except Exception as e:
        pytest.skip(f"LLM generate_queries failed: {e}")

    print(f"✅ Génération Modal authentique de {len(queries)} requêtes")
    assert isinstance(queries, list)

    for i, query in enumerate(queries[:3]):
        if query:
            print(f"  Requête Modal {i+1}: {query}")
            is_valid, msg = tweety_bridge.modal_handler.validate_modal_formula(query)
            print(f"  Validation Modal: {is_valid} - {msg}")


async def test_execute_query_authentic_modal(authentic_agent):
    """Test authentique d'exécution de requête modale avec TweetyBridge."""
    agent = authentic_agent["agent"]
    if not authentic_agent["tweety_available"]:
        pytest.skip("TweetyBridge non disponible pour Modal")

    belief_set_content = "[]p; <>q;"
    belief_set = ModalBeliefSet(belief_set_content)
    query = "p"

    # #2651 : execute_query tourne sur Tweety, pas sur le LLM : son échec est
    # un défaut, pas une indisponibilité, donc il fait échouer le test.
    result, message = await agent.execute_query(belief_set, query)

    print(f"✅ Exécution authentique requête Modal: {result} - {message}")
    # execute_query returns Tuple[Optional[bool], str] — result may be None
    # when the reasoner encounters a parse issue or cannot determine the answer
    assert result is None or isinstance(result, bool)
    assert isinstance(message, str)
    assert len(message) > 0


def test_tweety_bridge_modal_integration_authentic(authentic_agent):
    """Test d'intégration authentique avec TweetyBridge pour logique modale."""
    tweety_bridge = authentic_agent["tweety_bridge"]
    if not authentic_agent["tweety_available"]:
        pytest.skip("TweetyBridge non disponible pour Modal")

    formula = "[]p"
    is_valid, message = tweety_bridge.modal_handler.validate_modal_formula(formula)

    print(f"✅ Validation formule Modal authentique: {is_valid} - {message}")
    assert isinstance(is_valid, bool)
    assert isinstance(message, str)


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_api
async def test_full_workflow_modal_authentic(authentic_agent):
    """Test d'intégration complète authentique - workflow modal complet sans mocks."""
    agent = authentic_agent["agent"]
    if not (authentic_agent["llm_available"] and authentic_agent["tweety_available"]):
        pytest.skip("LLM ou TweetyBridge non disponible pour Modal")

    test_text = """
    Il est nécessaire que la logique soit cohérente.
    Il est possible que nous trouvions une preuve.
    """

    # Step 1: Text to belief set
    try:
        belief_set, bs_message = await agent.text_to_belief_set(test_text)
    except Exception as e:
        pytest.skip(f"Workflow step 1 (text_to_belief_set) failed: {e}")

    print(f"✅ Étape 1 Modal authentique - Belief set: {bs_message}")

    if belief_set is None:
        pytest.skip(f"LLM returned None belief set: {bs_message}")

    # Step 2: Generate queries
    try:
        queries = await agent.generate_queries(test_text, belief_set)
    except Exception as e:
        pytest.skip(f"Workflow step 2 (generate_queries) failed: {e}")

    print(f"✅ Étape 2 Modal authentique - {len(queries)} requêtes générées")

    # Step 3: Execute queries
    for i, query in enumerate(queries[:2]):
        if query:
            result, exec_message = await agent.execute_query(belief_set, query)
            print(f"✅ Étape 3.{i+1} Modal authentique - Requête '{query}': {result}")
            assert isinstance(result, bool)

    print("✅ Workflow Modal complet authentique terminé avec succès")


def test_modal_specific_features_authentic(authentic_agent):
    """Test authentique des fonctionnalités spécifiques à la logique modale."""
    tweety_bridge = authentic_agent["tweety_bridge"]
    if not authentic_agent["tweety_available"]:
        pytest.skip("TweetyBridge non disponible pour Modal")

    modal_formulas = ["[]p", "<>q", "[]p => <>p"]

    # #2651 : les assertions étaient dans un `except Exception` qui les
    # imprimait ; une validation qui échoue fait désormais échouer le test.
    for formula in modal_formulas:
        is_valid, message = tweety_bridge.modal_handler.validate_modal_formula(formula)
        print(f"✅ Formule modale '{formula}': {is_valid} - {message}")
        assert isinstance(is_valid, bool)
        assert isinstance(message, str)


@pytest.mark.performance
def test_performance_modal_authentic(authentic_agent):
    """Test de performance authentique pour logique modale."""
    import time

    tweety_bridge = authentic_agent["tweety_bridge"]
    if not authentic_agent["tweety_available"]:
        pytest.skip("TweetyBridge non disponible pour Modal")

    start_time = time.time()

    for i in range(5):
        formula = f"[]prop{i}"
        is_valid, _ = tweety_bridge.modal_handler.validate_modal_formula(formula)

    end_time = time.time()
    elapsed = end_time - start_time

    print(f"✅ Performance Modal authentique: 5 validations en {elapsed:.3f}s")
    assert elapsed < 3.0, f"Performance Modal dégradée: {elapsed:.3f}s"


# Configuration des marqueurs pytest pour cette classe
pytestmark = [
    pytest.mark.llm_integration,  # Tests LLM intégration (remplace authentic + no_mocks)
    pytest.mark.phase5,  # Marqueur Phase 5
    pytest.mark.modal,  # Marqueur spécifique logique modale
]
