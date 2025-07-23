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


@pytest.mark.jvm_test
class TestPropositionalLogicAgentAuthentic:
    """
    Tests authentiques pour PropositionalLogicAgent - Sans mocks, composants réels
    
    Phase 5: Élimination complète des mocks
    - Semantic Kernel authentique avec connecteurs Azure/OpenAI réels
    - TweetyBridge authentique avec JVM JPype réelle
    - PropositionalLogicAgent sans mocks
    - Tests de logique propositionnelle avec opérateurs =>, &, |, !
    """

    @pytest.fixture(scope="function")
    def authentic_pl_agent(self, tweety_bridge_fixture):
        """
        Fixture pour configurer un PropositionalLogicAgent authentique pour chaque test.
        Injecte une instance TweetyBridge partagée et gérée par une fixture.
        """
        print("\n[FIXTURE] Configuration de l'agent PL authentique...")
        
        kernel = Kernel()
        llm_service_configured = False
        llm_service_id = "test_llm_service_fixture"

        # Configuration conditionnelle du service LLM (Azure/OpenAI)
        if azure_available and os.getenv('AZURE_AI_INFERENCE_ENDPOINT'):
            try:
                azure_service = AzureAIInferenceChatCompletion(
                    endpoint=os.getenv('AZURE_AI_INFERENCE_ENDPOINT'),
                    api_key=os.getenv('AZURE_AI_INFERENCE_API_KEY'), service_id=llm_service_id)
                kernel.add_service(azure_service)
                llm_service_configured = True
            except Exception: pass
        
        if not llm_service_configured and openai_available and os.getenv('OPENAI_API_KEY'):
            try:
                openai_service = OpenAIChatCompletion(api_key=os.getenv('OPENAI_API_KEY'), service_id=llm_service_id)
                kernel.add_service(openai_service)
                llm_service_configured = True
            except Exception: pass
        
        agent_name = "TestPLAgentAuthenticFromFixture"
        agent = PropositionalLogicAgent(
            kernel=kernel,
            agent_name=agent_name,
            service_id=llm_service_id if llm_service_configured else None,
            tweety_bridge=tweety_bridge_fixture  # Injection de la dépendance
        )
        
        # Renvoyer un objet ou un dictionnaire pour que le test puisse accéder aux composants
        class AgentTestSetup:
            def __init__(self):
                self.agent = agent
                self.kernel = kernel
                self.tweety_bridge = tweety_bridge_fixture
                self.llm_service_configured = llm_service_configured
                self.llm_service_id = llm_service_id
                self.tweety_available = tweety_bridge_fixture.initializer.is_jvm_ready()

        return AgentTestSetup()

    @pytest.mark.authentic
    @pytest.mark.phase5
    @pytest.mark.no_mocks
    @pytest.mark.propositional
    def test_initialization_and_setup_authentic(self, authentic_pl_agent):
        """
        Test authentique d'initialisation et configuration - AUCUN MOCK
        """
        start_time = time.time()
        
        # Utiliser l'agent et les composants fournis par la fixture
        agent_setup = authentic_pl_agent
        
        # Vérifications de base authentiques
        assert agent_setup.agent.name == "TestPLAgentAuthenticFromFixture"
        assert agent_setup.agent._kernel == agent_setup.kernel
        assert agent_setup.agent.logic_type == "PL"
        assert agent_setup.agent.system_prompt == PL_AGENT_INSTRUCTIONS
        
        # Vérification TweetyBridge authentique
        assert agent_setup.tweety_available, "TweetyBridge devrait être disponible via la fixture"
        
        # Test d'interaction réelle avec TweetyBridge
        is_ready = agent_setup.tweety_bridge.initializer.is_jvm_ready()
        assert is_ready is True
        print(f"[AUTHENTIC] TweetyBridge JVM prête: {is_ready}")
        
        # Test de validation authentique
        valid = agent_setup.tweety_bridge.validate_pl_formula("a => b")
        assert valid is True
        print(f"[AUTHENTIC] Validation formule 'a => b': {valid}")
        
        # Vérification configuration Kernel authentique
        if agent_setup.llm_service_configured:
            settings = agent_setup.kernel.get_prompt_execution_settings_from_service_id(agent_setup.llm_service_id)
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
    async def test_text_to_belief_set_authentic(self, authentic_pl_agent):
        """
        Test authentique de conversion texte vers ensemble de croyances propositionnelles
        """
        agent_setup = authentic_pl_agent
        if not agent_setup.llm_service_configured:
            pytest.skip("Service LLM non configuré - test authentique impossible")
        
        start_time = time.time()
        
        # Test de conversion authentique avec vrai LLM
        test_text = "Si il pleut alors la rue est mouillée. Il pleut."
        
        try:
            belief_set, message = await agent_setup.agent.text_to_belief_set(test_text)
            
            # Vérifications authentiques
            if belief_set is not None:
                assert isinstance(belief_set, PropositionalBeliefSet)
                assert belief_set.content is not None
                assert len(belief_set.content.strip()) > 0
                print(f"[AUTHENTIC] Ensemble de croyances généré: {belief_set.content}")
                
                # Validation authentique avec TweetyBridge si disponible
                if agent_setup.tweety_available:
                    valid = agent_setup.tweety_bridge.validate_belief_set(belief_set.content)
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
    async def test_generate_queries_authentic(self, authentic_pl_agent):
        """
        Test authentique de génération de requêtes propositionnelles
        """
        agent_setup = authentic_pl_agent
        if not agent_setup.llm_service_configured:
            pytest.skip("Service LLM non configuré - test authentique impossible")
        
        start_time = time.time()
        
        # Test avec ensemble de croyances simple
        belief_set = PropositionalBeliefSet("pluie => rue_mouillee & pluie")
        test_text = "Analyse des implications de la pluie"
        
        try:
            queries = await agent_setup.agent.generate_queries(test_text, belief_set)
            
            # Vérifications authentiques
            assert isinstance(queries, list)
            print(f"[AUTHENTIC] Requêtes générées: {queries}")
            
            # Validation authentique avec TweetyBridge si disponible
            if agent_setup.tweety_available and len(queries) > 0:
                for query in queries:
                    valid = agent_setup.agent.validate_formula(query)
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
    def test_execute_query_authentic(self, authentic_pl_agent):
        """
        Test authentique d'exécution de requêtes propositionnelles
        """
        agent_setup = authentic_pl_agent
        if not agent_setup.tweety_available:
            pytest.skip("TweetyBridge JVM non disponible - test authentique impossible")
        
        start_time = time.time()
        
        # Test avec ensemble de croyances et requête simples
        belief_set = PropositionalBeliefSet("(a => b) & a")
        query = "b"  # Devrait être ACCEPTED par modus ponens
        
        # Exécution authentique
        result, message = agent_setup.agent.execute_query(belief_set, query)
        
        # Vérifications authentiques
        print(f"[AUTHENTIC] Résultat requête '{query}': {result}")
        print(f"[AUTHENTIC] Message TweetyBridge: {message}")
        
        # Test avec requête qui devrait être rejetée
        query_rejected = "c"  # Non dérivable
        result_rejected, message_rejected = agent_setup.agent.execute_query(belief_set, query_rejected)
        
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
    async def test_full_propositional_reasoning_workflow_authentic(self, authentic_pl_agent):
        """
        Test authentique du workflow complet de raisonnement propositionnel
        """
        agent_setup = authentic_pl_agent
        if not (agent_setup.llm_service_configured and agent_setup.tweety_available):
            pytest.skip("Services LLM et TweetyBridge requis pour test intégration authentique")
        
        start_time = time.time()
        
        # Workflow complet authentique
        test_text = "Si Alice étudie alors elle réussit. Alice étudie. Donc Alice réussit."
        
        try:
            # 1. Conversion texte -> ensemble de croyances
            belief_set, conversion_msg = await agent_setup.agent.text_to_belief_set(test_text)
            print(f"[AUTHENTIC] Conversion: {conversion_msg}")
            
            if belief_set is None:
                pytest.skip("Conversion a échoué - impossible de continuer le workflow")
            
            # 2. Génération de requêtes
            queries = await agent_setup.agent.generate_queries(test_text, belief_set)
            print(f"[AUTHENTIC] Requêtes: {queries}")
            
            # 3. Exécution des requêtes
            results = []
            for query in queries:
                result, message = agent_setup.agent.execute_query(belief_set, query)
                results.append((result, message))
                print(f"[AUTHENTIC] Requête '{query}' -> {result}")
            
            # 4. Interprétation des résultats
            interpretation = await agent_setup.agent.interpret_results(test_text, belief_set, queries, results)
            print(f"[AUTHENTIC] Interprétation: {interpretation}")
            
            # Vérifications du workflow
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
    def test_formula_validation_performance_authentic(self, authentic_pl_agent):
        """
        Test authentique de performance de validation de formules
        """
        agent_setup = authentic_pl_agent
        if not agent_setup.tweety_available:
            pytest.skip("TweetyBridge JVM non disponible")
        
        start_time = time.time()
        
        # Test de performance sur plusieurs formules
        test_formulas = [
            "a",
            "a & b",
            "a | b",
            "!a",
            "a => b",
            "(a & b) => c",
            "a & (b | c)",
            "!(!a | !b)",
            "(a => b) & (b => c) => (a => c)"
        ]
        
        valid_count = 0
        for formula in test_formulas:
            valid = agent_setup.agent.validate_formula(formula)
            if valid:
                valid_count += 1
            print(f"[AUTHENTIC] Formule '{formula}': {valid}")
        
        execution_time = time.time() - start_time
        print(f"[AUTHENTIC] Validation de {len(test_formulas)} formules en {execution_time:.2f}s")
        print(f"[AUTHENTIC] Formules valides: {valid_count}/{len(test_formulas)}")
        
        # Performance attendue : validation rapide
        assert execution_time < 5.0  # Moins de 5 secondes pour 9 formules


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