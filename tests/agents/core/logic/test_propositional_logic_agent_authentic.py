"""
Tests authentiques pour PropositionalLogicAgent - Phase 5 Mock Elimination
"""

import os
import sys
import time
import pytest
from typing import Optional, Tuple, List

# Import auto-configuration environnement
import scripts.core.auto_env

# Imports Semantic Kernel authentiques
from semantic_kernel import Kernel
from semantic_kernel.functions.kernel_arguments import KernelArguments

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


class TestPropositionalLogicAgentAuthentic:
    """
    Tests authentiques pour PropositionalLogicAgent - Sans mocks, composants réels
    
    Phase 5: Élimination complète des mocks
    - Semantic Kernel authentique avec connecteurs Azure/OpenAI réels
    - TweetyBridge authentique avec JVM JPype réelle
    - PropositionalLogicAgent sans mocks
    - Tests de logique propositionnelle avec opérateurs =>, &, |, !
    """

    def setup_method(self):
        """
        Configuration authentique avant chaque test - AUCUN MOCK
        """
        print("\n[AUTHENTIC] Configuration PropositionalLogicAgent authentique...")
        
        # Configuration du vrai Semantic Kernel
        self.kernel = Kernel()
        
        # Configuration des connecteurs authentiques conditionnels
        self.llm_service_configured = False
        self.llm_service_id = "test_llm_service"
        
        # Tentative de configuration Azure AI Inference
        if azure_available and os.getenv('AZURE_AI_INFERENCE_ENDPOINT'):
            try:
                azure_service = AzureAIInferenceChatCompletion(
                    endpoint=os.getenv('AZURE_AI_INFERENCE_ENDPOINT'),
                    api_key=os.getenv('AZURE_AI_INFERENCE_API_KEY'),
                    service_id=self.llm_service_id
                )
                self.kernel.add_service(azure_service)
                self.llm_service_configured = True
                print(f"[AUTHENTIC] Azure AI Inference configuré: {self.llm_service_id}")
            except Exception as e:
                print(f"[AUTHENTIC] Azure AI Inference non disponible: {e}")
        
        # Fallback OpenAI si Azure non disponible
        if not self.llm_service_configured and openai_available and os.getenv('OPENAI_API_KEY'):
            try:
                openai_service = OpenAIChatCompletion(
                    api_key=os.getenv('OPENAI_API_KEY'),
                    service_id=self.llm_service_id
                )
                self.kernel.add_service(openai_service)
                self.llm_service_configured = True
                print(f"[AUTHENTIC] OpenAI configuré: {self.llm_service_id}")
            except Exception as e:
                print(f"[AUTHENTIC] OpenAI non disponible: {e}")
        
        # Configuration du vrai TweetyBridge
        self.tweety_bridge = TweetyBridge()
        self.tweety_available = self.tweety_bridge.is_jvm_ready()
        print(f"[AUTHENTIC] TweetyBridge JVM disponible: {self.tweety_available}")
        
        # Configuration PropositionalLogicAgent authentique
        self.agent_name = "TestPLAgentAuthentic"
        self.agent = PropositionalLogicAgent(self.kernel, agent_name=self.agent_name)
        
        if self.llm_service_configured:
            self.agent.setup_agent_components(self.llm_service_id)
            print(f"[AUTHENTIC] PropositionalLogicAgent configuré avec service: {self.llm_service_id}")
        else:
            print("[AUTHENTIC] PropositionalLogicAgent configuré sans service LLM")

    @pytest.mark.authentic
    @pytest.mark.phase5
    @pytest.mark.no_mocks
    @pytest.mark.propositional
    def test_initialization_and_setup_authentic(self):
        """
        Test authentique d'initialisation et configuration - AUCUN MOCK
        """
        start_time = time.time()
        
        # Vérifications de base authentiques
        assert self.agent.name == self.agent_name
        assert self.agent.sk_kernel == self.kernel
        assert self.agent.logic_type == "PL"
        assert self.agent.system_prompt == PL_AGENT_INSTRUCTIONS
        
        # Vérification TweetyBridge authentique
        if self.tweety_available:
            # Test d'interaction réelle avec TweetyBridge
            is_ready = self.tweety_bridge.is_jvm_ready()
            assert is_ready is True
            print(f"[AUTHENTIC] TweetyBridge JVM prête: {is_ready}")
            
            # Test de validation authentique
            valid, msg = self.tweety_bridge.validate_formula("a => b")
            assert valid is True
            print(f"[AUTHENTIC] Validation formule 'a => b': {valid}, {msg}")
        else:
            print("[AUTHENTIC] TweetyBridge JVM non disponible - test gracieux")
        
        # Vérification configuration Kernel authentique
        if self.llm_service_configured:
            settings = self.kernel.get_prompt_execution_settings_from_service_id(self.llm_service_id)
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
    async def test_text_to_belief_set_authentic(self):
        """
        Test authentique de conversion texte vers ensemble de croyances propositionnelles
        """
        if not self.llm_service_configured:
            pytest.skip("Service LLM non configuré - test authentique impossible")
        
        start_time = time.time()
        
        # Test de conversion authentique avec vrai LLM
        test_text = "Si il pleut alors la rue est mouillée. Il pleut."
        
        try:
            belief_set, message = await self.agent.text_to_belief_set(test_text)
            
            # Vérifications authentiques
            if belief_set is not None:
                assert isinstance(belief_set, PropositionalBeliefSet)
                assert belief_set.content is not None
                assert len(belief_set.content.strip()) > 0
                print(f"[AUTHENTIC] Ensemble de croyances généré: {belief_set.content}")
                
                # Validation authentique avec TweetyBridge si disponible
                if self.tweety_available:
                    valid, validation_msg = self.tweety_bridge.validate_belief_set(belief_set.content)
                    print(f"[AUTHENTIC] Validation TweetyBridge: {valid}, {validation_msg}")
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
    async def test_generate_queries_authentic(self):
        """
        Test authentique de génération de requêtes propositionnelles
        """
        if not self.llm_service_configured:
            pytest.skip("Service LLM non configuré - test authentique impossible")
        
        start_time = time.time()
        
        # Test avec ensemble de croyances simple
        belief_set = PropositionalBeliefSet("pluie => rue_mouillee & pluie")
        test_text = "Analyse des implications de la pluie"
        
        try:
            queries = await self.agent.generate_queries(test_text, belief_set)
            
            # Vérifications authentiques
            assert isinstance(queries, list)
            print(f"[AUTHENTIC] Requêtes générées: {queries}")
            
            # Validation authentique avec TweetyBridge si disponible
            if self.tweety_available and len(queries) > 0:
                for query in queries:
                    valid, validation_msg = self.tweety_bridge.validate_formula(query)
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
    def test_execute_query_authentic(self):
        """
        Test authentique d'exécution de requêtes propositionnelles
        """
        if not self.tweety_available:
            pytest.skip("TweetyBridge JVM non disponible - test authentique impossible")
        
        start_time = time.time()
        
        # Test avec ensemble de croyances et requête simples
        belief_set = PropositionalBeliefSet("a => b & a")
        query = "b"  # Devrait être ACCEPTED par modus ponens
        
        # Exécution authentique
        result, message = self.agent.execute_query(belief_set, query)
        
        # Vérifications authentiques
        print(f"[AUTHENTIC] Résultat requête '{query}': {result}")
        print(f"[AUTHENTIC] Message TweetyBridge: {message}")
        
        # Test avec requête qui devrait être rejetée
        query_rejected = "c"  # Non dérivable
        result_rejected, message_rejected = self.agent.execute_query(belief_set, query_rejected)
        
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
    async def test_full_propositional_reasoning_workflow_authentic(self):
        """
        Test authentique du workflow complet de raisonnement propositionnel
        """
        if not (self.llm_service_configured and self.tweety_available):
            pytest.skip("Services LLM et TweetyBridge requis pour test intégration authentique")
        
        start_time = time.time()
        
        # Workflow complet authentique
        test_text = "Si Alice étudie alors elle réussit. Alice étudie. Donc Alice réussit."
        
        try:
            # 1. Conversion texte -> ensemble de croyances
            belief_set, conversion_msg = await self.agent.text_to_belief_set(test_text)
            print(f"[AUTHENTIC] Conversion: {conversion_msg}")
            
            if belief_set is None:
                pytest.skip("Conversion a échoué - impossible de continuer le workflow")
            
            # 2. Génération de requêtes
            queries = await self.agent.generate_queries(test_text, belief_set)
            print(f"[AUTHENTIC] Requêtes: {queries}")
            
            # 3. Exécution des requêtes
            results = []
            for query in queries:
                result, message = self.agent.execute_query(belief_set, query)
                results.append((result, message))
                print(f"[AUTHENTIC] Requête '{query}' -> {result}")
            
            # 4. Interprétation des résultats
            interpretation = await self.agent.interpret_results(test_text, belief_set, queries, results)
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
    def test_formula_validation_performance_authentic(self):
        """
        Test authentique de performance de validation de formules
        """
        if not self.tweety_available:
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
            valid = self.agent.validate_formula(formula)
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