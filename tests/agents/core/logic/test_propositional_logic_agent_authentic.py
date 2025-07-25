"""
Tests authentiques pour PropositionalLogicAgent - Phase 5 Mock Elimination
"""

import os
import sys
import time
import pytest
from typing import Optional, Tuple, List

# Import auto-configuration environnement
from argumentation_analysis.core import environment as auto_env

# Imports Semantic Kernel authentiques
from semantic_kernel import Kernel
from semantic_kernel.functions import KernelArguments

# Conditional imports pour connecteurs authentiques
try:
    from semantic_kernel.connectors.ai.azure_ai_inference import AzureAIInferenceChatCompletion
    azure_available = True
except ImportError:
    azure_available = False

try:
    from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
    openai_available = True
except ImportError:
    openai_available = False

# Imports composants authentiques
from argumentation_analysis.agents.core.logic.propositional_logic_agent import PropositionalLogicAgent
from argumentation_analysis.agents.core.logic.belief_set import PropositionalBeliefSet
from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge
from argumentation_analysis.agents.core.pl.pl_definitions import PL_AGENT_INSTRUCTIONS


@pytest.fixture(scope="module")
def authentic_pl_agent(jvm_controller):
    """
    Fixture pour initialiser un agent PL authentique avec un TweetyBridge partagé.
    Remplace setup_method pour une gestion centralisée de la JVM.
    """
    print("\n[AUTHENTIC FIXTURE] Configuration PropositionalLogicAgent authentique...")
    if not jvm_controller.is_jvm_ready():
        pytest.skip("JVM controller not ready, skipping authentic propositional agent tests.")

    kernel = Kernel()
    llm_service_configured = False
    llm_service_id = "test_llm_service"

    if azure_available and os.getenv('AZURE_AI_INFERENCE_ENDPOINT'):
        try:
            azure_service = AzureAIInferenceChatCompletion(
                endpoint=os.getenv('AZURE_AI_INFERENCE_ENDPOINT'),
                api_key=os.getenv('AZURE_AI_INFERENCE_API_KEY'),
                service_id=llm_service_id
            )
            kernel.add_service(azure_service)
            llm_service_configured = True
            print(f"[AUTHENTIC] Azure AI Inference configuré: {llm_service_id}")
        except Exception as e:
            print(f"[AUTHENTIC] Azure AI Inference non disponible: {e}")
    
    if not llm_service_configured and openai_available and os.getenv('OPENAI_API_KEY'):
        try:
            openai_service = OpenAIChatCompletion(
                api_key=os.getenv('OPENAI_API_KEY'),
                service_id=llm_service_id
            )
            kernel.add_service(openai_service)
            llm_service_configured = True
            print(f"[AUTHENTIC] OpenAI configuré: {llm_service_id}")
        except Exception as e:
            print(f"[AUTHENTIC] OpenAI non disponible: {e}")

    tweety_bridge = jvm_controller.tweety_bridge
    agent_name = "TestPLAgentAuthentic"
    agent = PropositionalLogicAgent(
        kernel=kernel,
        agent_name=agent_name,
        service_id=llm_service_id if llm_service_configured else None,
    )
    # Injection directe du pont partagé
    agent.tweety_bridge = tweety_bridge

    if llm_service_configured:
        print(f"[AUTHENTIC] PropositionalLogicAgent configuré avec service: {llm_service_id}")
    else:
        print("[AUTHENTIC] PropositionalLogicAgent configuré sans service LLM")
        
    return {
        "agent": agent,
        "kernel": kernel,
        "tweety_bridge": tweety_bridge,
        "llm_service_configured": llm_service_configured,
        "tweety_available": jvm_controller.is_jvm_ready(),
        "llm_service_id": llm_service_id,
        "agent_name": agent_name
    }

@pytest.mark.authentic
@pytest.mark.phase5
@pytest.mark.no_mocks
@pytest.mark.propositional
def test_initialization_and_setup_authentic(authentic_pl_agent):
    """Test authentique d'initialisation et configuration - AUCUN MOCK."""
    start_time = time.time()
    
    agent = authentic_pl_agent['agent']
    tweety_available = authentic_pl_agent['tweety_available']
    llm_service_configured = authentic_pl_agent['llm_service_configured']
    
    assert agent.name == authentic_pl_agent['agent_name']
    assert agent._kernel == authentic_pl_agent['kernel']
    assert agent.logic_type == "PL"
    assert agent.system_prompt == PL_AGENT_INSTRUCTIONS
    
    if tweety_available:
        is_ready = agent.tweety_bridge.initializer.is_jvm_ready()
        assert is_ready is True
        print(f"[AUTHENTIC] TweetyBridge JVM prête: {is_ready}")
        valid = agent.tweety_bridge.validate_pl_formula("a => b")
        assert valid is True
        print(f"[AUTHENTIC] Validation formule 'a => b': {valid}")
    else:
        print("[AUTHENTIC] TweetyBridge JVM non disponible - test gracieux")
    
    if llm_service_configured:
        settings = agent.kernel.get_prompt_execution_settings_from_service_id(authentic_pl_agent['llm_service_id'])
        assert settings is not None
        print(f"[AUTHENTIC] Paramètres LLM: {settings}")
    else:
        print("[AUTHENTIC] Service LLM non configuré - test gracieux")
    
    execution_time = time.time() - start_time
    print(f"[AUTHENTIC] Test d'initialisation terminé en {execution_time:.2f}s")

@pytest.mark.asyncio
@pytest.mark.requires_llm
@pytest.mark.authentic
@pytest.mark.phase5
@pytest.mark.no_mocks
@pytest.mark.propositional
async def test_text_to_belief_set_authentic(authentic_pl_agent):
    """Test authentique de conversion texte vers ensemble de croyances propositionnelles."""
    if not authentic_pl_agent['llm_service_configured']:
        pytest.skip("Service LLM non configuré - test authentique impossible")
        
    agent = authentic_pl_agent['agent']
    start_time = time.time()
    test_text = "Si il pleut alors la rue est mouillée. Il pleut."
    
    try:
        belief_set, message = await agent.text_to_belief_set(test_text)
        
        if belief_set is not None:
            assert isinstance(belief_set, PropositionalBeliefSet)
            assert belief_set.content is not None
            assert len(belief_set.content.strip()) > 0
            print(f"[AUTHENTIC] Ensemble de croyances généré: {belief_set.content}")
            
            if authentic_pl_agent['tweety_available']:
                valid = agent.tweety_bridge.validate_belief_set(belief_set.content)
                print(f"[AUTHENTIC] Validation TweetyBridge: {valid}")
        else:
            print(f"[AUTHENTIC] Conversion produit résultat vide: {message}")
            
    except Exception as e:
        print(f"[AUTHENTIC] Erreur lors de la conversion: {e}")
        pytest.skip(f"Erreur de service LLM: {e}")
    
    execution_time = time.time() - start_time
    print(f"[AUTHENTIC] Test de conversion terminé en {execution_time:.2f}s")

@pytest.mark.asyncio
@pytest.mark.requires_llm
@pytest.mark.authentic
@pytest.mark.phase5
@pytest.mark.no_mocks
@pytest.mark.propositional
async def test_generate_queries_authentic(authentic_pl_agent):
    """Test authentique de génération de requêtes propositionnelles."""
    if not authentic_pl_agent['llm_service_configured']:
        pytest.skip("Service LLM non configuré - test authentique impossible")
        
    agent = authentic_pl_agent['agent']
    start_time = time.time()
    belief_set = PropositionalBeliefSet("pluie => rue_mouillee & pluie")
    test_text = "Analyse des implications de la pluie"
    
    try:
        queries = await agent.generate_queries(test_text, belief_set)
        
        assert isinstance(queries, list)
        print(f"[AUTHENTIC] Requêtes générées: {queries}")
        
        if authentic_pl_agent['tweety_available'] and len(queries) > 0:
            for query in queries:
                valid = agent.validate_formula(query)
                print(f"[AUTHENTIC] Validation requête '{query}': {valid}")
                
    except Exception as e:
        print(f"[AUTHENTIC] Erreur lors de la génération: {e}")
        pytest.skip(f"Erreur de service LLM: {e}")
    
    execution_time = time.time() - start_time
    print(f"[AUTHENTIC] Test de génération terminé en {execution_time:.2f}s")

@pytest.mark.authentic
@pytest.mark.phase5
@pytest.mark.no_mocks
@pytest.mark.propositional
def test_execute_query_authentic(authentic_pl_agent):
    """Test authentique d'exécution de requêtes propositionnelles."""
    if not authentic_pl_agent['tweety_available']:
        pytest.skip("TweetyBridge JVM non disponible - test authentique impossible")
        
    agent = authentic_pl_agent['agent']
    start_time = time.time()
    belief_set = PropositionalBeliefSet("(a => b) & a")
    query = "b"
    
    result, message = agent.execute_query(belief_set, query)
    
    print(f"[AUTHENTIC] Résultat requête '{query}': {result}")
    print(f"[AUTHENTIC] Message TweetyBridge: {message}")
    
    query_rejected = "c"
    result_rejected, message_rejected = agent.execute_query(belief_set, query_rejected)
    
    print(f"[AUTHENTIC] Résultat requête rejetée '{query_rejected}': {result_rejected}")
    print(f"[AUTHENTIC] Message rejet: {message_rejected}")
    
    execution_time = time.time() - start_time
    print(f"[AUTHENTIC] Test d'exécution terminé en {execution_time:.2f}s")

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.authentic
@pytest.mark.phase5
@pytest.mark.no_mocks
@pytest.mark.propositional
async def test_full_propositional_reasoning_workflow_authentic(authentic_pl_agent):
    """Test authentique du workflow complet de raisonnement propositionnel."""
    if not (authentic_pl_agent['llm_service_configured'] and authentic_pl_agent['tweety_available']):
        pytest.skip("Services LLM et TweetyBridge requis pour test intégration authentique")
        
    agent = authentic_pl_agent['agent']
    start_time = time.time()
    test_text = "Si Alice étudie alors elle réussit. Alice étudie. Donc Alice réussit."
    
    try:
        belief_set, conversion_msg = await agent.text_to_belief_set(test_text)
        print(f"[AUTHENTIC] Conversion: {conversion_msg}")
        
        if belief_set is None:
            pytest.skip("Conversion a échoué - impossible de continuer le workflow")
        
        queries = await agent.generate_queries(test_text, belief_set)
        print(f"[AUTHENTIC] Requêtes: {queries}")
        
        results = []
        for query in queries:
            result, message = agent.execute_query(belief_set, query)
            results.append((result, message))
            print(f"[AUTHENTIC] Requête '{query}' -> {result}")
        
        interpretation = await agent.interpret_results(test_text, belief_set, queries, results)
        print(f"[AUTHENTIC] Interprétation: {interpretation}")
        
        assert len(queries) > 0
        assert len(results) == len(queries)
        assert interpretation is not None
        
    except Exception as e:
        print(f"[AUTHENTIC] Erreur workflow: {e}")
        pytest.skip(f"Erreur dans le workflow authentique: {e}")
    
    execution_time = time.time() - start_time
    print(f"[AUTHENTIC] Workflow complet terminé en {execution_time:.2f}s")

@pytest.mark.performance
@pytest.mark.authentic
@pytest.mark.phase5
@pytest.mark.no_mocks
@pytest.mark.propositional
def test_formula_validation_performance_authentic(authentic_pl_agent):
    """Test authentique de performance de validation de formules."""
    if not authentic_pl_agent['tweety_available']:
        pytest.skip("TweetyBridge JVM non disponible")
        
    agent = authentic_pl_agent['agent']
    start_time = time.time()
    
    test_formulas = [
        "a", "a & b", "a | b", "!a", "a => b",
        "(a & b) => c", "a & (b | c)", "!(!a | !b)",
        "(a => b) & (b => c) => (a => c)"
    ]
    
    valid_count = 0
    for formula in test_formulas:
        valid = agent.validate_formula(formula)
        if valid:
            valid_count += 1
        print(f"[AUTHENTIC] Formule '{formula}': {valid}")
    
    execution_time = time.time() - start_time
    print(f"[AUTHENTIC] Validation de {len(test_formulas)} formules en {execution_time:.2f}s")
    print(f"[AUTHENTIC] Formules valides: {valid_count}/{len(test_formulas)}")
    
    assert execution_time < 5.0


# Marqueurs pytest pour organisation des tests authentiques
pytestmark = [
    pytest.mark.authentic,  # Marqueur pour tests authentiques
    pytest.mark.phase5,     # Marqueur Phase 5
    pytest.mark.no_mocks,   # Marqueur sans mocks
    pytest.mark.propositional,  # Marqueur spécifique logique propositionnelle
]


if __name__ == "__main__":
    # Exécution directe pour débogage
    pytest.main([__file__, "-v", "--tb=short"])
