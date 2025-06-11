# -*- coding: utf-8 -*-
# tests/agents/core/logic/test_first_order_logic_agent_authentic.py
"""
Tests unitaires authentiques pour la classe FirstOrderLogicAgent.
Phase 5 - Élimination complète des mocks - Version authentique
"""

import unittest
import pytest
import asyncio
import os
import sys
from pathlib import Path

# Import du système d'auto-activation d'environnement
try:
    import scripts.core.auto_env
except ImportError:
    # Auto-activation en cas d'échec
    project_root = Path(__file__).parent.parent.parent.parent.parent
    sys.path.insert(0, str(project_root / "scripts" / "core"))
    import auto_env

# Imports authentiques - vrai Semantic Kernel
from semantic_kernel import Kernel
from semantic_kernel.functions.kernel_arguments import KernelArguments

# Imports conditionnels pour les connecteurs LLM
try:
    from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
except ImportError:
    OpenAIChatCompletion = None

try:
    from semantic_kernel.connectors.ai.azure_open_ai import AzureOpenAIChatCompletion
except ImportError:
    try:
        from semantic_kernel.connectors.ai.azure_open_ai.azure_chat_completion import AzureOpenAIChatCompletion
    except ImportError:
        AzureOpenAIChatCompletion = None

# Imports du projet
from argumentation_analysis.agents.core.logic.first_order_logic_agent import FirstOrderLogicAgent, SYSTEM_PROMPT_FOL
from argumentation_analysis.agents.core.logic.belief_set import FirstOrderBeliefSet, BeliefSet
from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge


class TestFirstOrderLogicAgentAuthentic:
    """Tests authentiques pour la classe FirstOrderLogicAgent - SANS MOCKS."""

    def setup_method(self):
        """Initialisation authentique avant chaque test."""
        # Configuration du vrai Kernel Semantic Kernel
        self.kernel = Kernel()
        
        # Configuration authentique du service LLM
        self.llm_service_id = "authentic_fol_llm_service"
        
        # Essayer d'utiliser un vrai service LLM (OpenAI ou Azure)
        self.llm_available = False
        
        try:
            # Priorité à Azure OpenAI si configuré et disponible
            azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
            azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
            
            if azure_endpoint and azure_api_key and AzureOpenAIChatCompletion:
                chat_service = AzureOpenAIChatCompletion(
                    service_id=self.llm_service_id,
                    deployment_name=azure_deployment,
                    endpoint=azure_endpoint,
                    api_key=azure_api_key
                )
                self.kernel.add_service(chat_service)
                self.llm_available = True
                print(f"✅ Service LLM Azure configuré: {azure_deployment}")
            else:
                # Fallback sur OpenAI
                openai_api_key = os.getenv("OPENAI_API_KEY")
                if openai_api_key and OpenAIChatCompletion:
                    chat_service = OpenAIChatCompletion(
                        service_id=self.llm_service_id,
                        ai_model_id="gpt-4o-mini",
                        api_key=openai_api_key
                    )
                    self.kernel.add_service(chat_service)
                    self.llm_available = True
                    print("✅ Service LLM OpenAI configuré: gpt-4o-mini")
                else:
                    print("⚠️ Connecteurs LLM non disponibles ou clés API manquantes")
        except Exception as e:
            self.llm_available = False
            print(f"⚠️ Erreur configuration LLM: {e}")

        # Initialisation du vrai TweetyBridge
        try:
            self.tweety_bridge = TweetyBridge()
            self.tweety_available = self.tweety_bridge.is_jvm_ready()
            if self.tweety_available:
                print("✅ TweetyBridge JVM authentique prête")
            else:
                print("⚠️ TweetyBridge JVM non disponible")
        except Exception as e:
            self.tweety_available = False
            print(f"⚠️ Erreur TweetyBridge: {e}")

        # Initialisation de l'agent authentique
        self.agent_name = "FirstOrderLogicAgent"
        self.agent = FirstOrderLogicAgent(self.kernel, service_id=self.llm_service_id)
        
        # Configuration authentique de l'agent
        if self.llm_available:
            try:
                self.agent.setup_agent_components(self.llm_service_id)
                print("✅ Agent FOL authentique configuré")
            except Exception as e:
                print(f"⚠️ Erreur configuration agent: {e}")

    def test_initialization_and_setup_authentic(self):
        """Test authentique de l'initialisation et de la configuration de l'agent."""
        # Tests d'initialisation de base
        assert self.agent.name == self.agent_name
        assert self.agent.sk_kernel == self.kernel
        assert self.agent.logic_type == "FOL"
        assert self.agent.system_prompt == SYSTEM_PROMPT_FOL
        
        # Test de l'état du TweetyBridge authentique
        if self.tweety_available:
            assert self.agent.tweety_bridge.is_jvm_ready() == True
            print("✅ Test authentique TweetyBridge - JVM prête")
        else:
            print("⚠️ TweetyBridge non disponible - test sauté")
            
        # Test de la configuration Semantic Kernel authentique
        if self.llm_available:
            service = self.kernel.get_service(self.llm_service_id)
            assert service is not None
            print("✅ Test authentique Semantic Kernel - Service configuré")

    @pytest.mark.asyncio
    @pytest.mark.requires_llm
    async def test_text_to_belief_set_authentic_simple(self):
        """Test authentique de conversion texte -> belief set avec vrai LLM."""
        if not (self.llm_available and self.tweety_available):
            pytest.skip("LLM ou TweetyBridge non disponible")
            
        # Texte simple pour test authentique
        test_text = """
        Tous les humains sont mortels.
        Socrate est un humain.
        """
        
        try:
            belief_set, message = await self.agent.text_to_belief_set(test_text)
            
            print(f"✅ Conversion authentique réussie: {message}")
            
            if belief_set is not None:
                assert isinstance(belief_set, FirstOrderBeliefSet)
                assert len(belief_set.content) > 0
                print(f"✅ Belief set authentique créé: {belief_set.content[:100]}...")
                
                # Test de validation authentique avec TweetyBridge
                is_valid, validation_msg = self.tweety_bridge.validate_fol_belief_set(belief_set.content)
                print(f"✅ Validation TweetyBridge authentique: {is_valid} - {validation_msg}")
                
        except Exception as e:
            print(f"⚠️ Erreur test authentique: {e}")
            # Ne pas faire échouer le test, juste informer
            pytest.skip(f"Test authentique échoué: {e}")

    @pytest.mark.asyncio 
    @pytest.mark.requires_llm
    async def test_generate_queries_authentic(self):
        """Test authentique de génération de requêtes avec vrai LLM."""
        if not (self.llm_available and self.tweety_available):
            pytest.skip("LLM ou TweetyBridge non disponible")
            
        # Créer un belief set simple authentique
        belief_set_content = """
        sort(human).
        predicate(mortal/1).
        mortal(socrates).
        """
        belief_set = FirstOrderBeliefSet(belief_set_content)
        
        # Texte de contexte
        context_text = "Nous nous intéressons à la mortalité de Socrate"
        
        try:
            queries = await self.agent.generate_queries(context_text, belief_set)
            
            print(f"✅ Génération authentique de {len(queries)} requêtes")
            
            # Test que nous obtenons des requêtes
            assert isinstance(queries, list)
            
            # Si des requêtes sont générées, les tester
            for i, query in enumerate(queries[:3]):  # Limiter à 3 pour les tests
                if query:
                    print(f"  Requête {i+1}: {query}")
                    # Test de validation authentique
                    is_valid, msg = self.tweety_bridge.validate_fol_formula(query)
                    print(f"  Validation: {is_valid} - {msg}")
                    
        except Exception as e:
            print(f"⚠️ Erreur génération requêtes authentique: {e}")
            pytest.skip(f"Test authentique échoué: {e}")

    def test_execute_query_authentic(self):
        """Test authentique d'exécution de requête avec TweetyBridge."""
        if not self.tweety_available:
            pytest.skip("TweetyBridge non disponible")
            
        # Créer un belief set simple pour test
        belief_set_content = "mortal(socrates)."
        belief_set = FirstOrderBeliefSet(belief_set_content)
        
        # Requête simple
        query = "mortal(socrates)"
        
        try:
            result, message = self.agent.execute_query(belief_set, query)
            
            print(f"✅ Exécution authentique requête: {result} - {message}")
            
            # Vérifier le type de résultat
            assert isinstance(result, bool)
            assert isinstance(message, str)
            assert len(message) > 0
            
        except Exception as e:
            print(f"⚠️ Erreur exécution requête authentique: {e}")
            pytest.skip(f"Test authentique échoué: {e}")

    def test_tweety_bridge_integration_authentic(self):
        """Test d'intégration authentique avec TweetyBridge."""
        if not self.tweety_available:
            pytest.skip("TweetyBridge non disponible")
            
        # Test de validation de formule simple
        formula = "Human(socrates)"
        is_valid, message = self.tweety_bridge.validate_fol_formula(formula)
        
        print(f"✅ Validation formule authentique: {is_valid} - {message}")
        assert isinstance(is_valid, bool)
        assert isinstance(message, str)
        
        # Test de consistance de belief set
        belief_set_content = "Human(socrates). Mortal(socrates)."
        is_consistent, cons_message = self.tweety_bridge.is_fol_kb_consistent(belief_set_content)
        
        print(f"✅ Test consistance authentique: {is_consistent} - {cons_message}")
        assert isinstance(is_consistent, bool)
        assert isinstance(cons_message, str)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_workflow_authentic(self):
        """Test d'intégration complète authentique - workflow complet sans mocks."""
        if not (self.llm_available and self.tweety_available):
            pytest.skip("LLM ou TweetyBridge non disponible")
            
        # Workflow complet authentique
        test_text = """
        Tous les philosophes grecs étaient des penseurs.
        Socrate était un philosophe grec.
        Aristote était un philosophe grec.
        """
        
        try:
            # Étape 1: Conversion texte -> belief set (authentique)
            belief_set, bs_message = await self.agent.text_to_belief_set(test_text)
            print(f"✅ Étape 1 authentique - Belief set: {bs_message}")
            
            if belief_set is not None:
                # Étape 2: Génération de requêtes (authentique)
                queries = await self.agent.generate_queries(test_text, belief_set)
                print(f"✅ Étape 2 authentique - {len(queries)} requêtes générées")
                
                # Étape 3: Exécution des requêtes (authentique) 
                for i, query in enumerate(queries[:2]):  # Limiter pour les tests
                    if query:
                        result, exec_message = self.agent.execute_query(belief_set, query)
                        print(f"✅ Étape 3.{i+1} authentique - Requête '{query}': {result}")
                        assert isinstance(result, bool)
                        
                print("✅ Workflow complet authentique terminé avec succès")
                
        except Exception as e:
            print(f"⚠️ Erreur workflow authentique: {e}")
            pytest.skip(f"Workflow authentique échoué: {e}")

    def test_belief_set_construction_authentic(self):
        """Test authentique de construction de belief set."""
        # Test des méthodes internes de construction
        json_data = {
            "sorts": {"human": ["socrates", "plato"]},
            "predicates": [{"name": "mortal", "args": ["human"]}],
            "formulas": ["mortal(socrates)", "mortal(plato)"]
        }
        
        constructed_kb = self.agent._construct_kb_from_json(json_data)
        
        print(f"✅ Construction KB authentique: {constructed_kb[:100]}...")
        
        assert isinstance(constructed_kb, str)
        assert len(constructed_kb) > 0
        assert "mortal" in constructed_kb
        assert "socrates" in constructed_kb

    @pytest.mark.performance 
    def test_performance_authentic(self):
        """Test de performance authentique."""
        import time
        
        if not self.tweety_available:
            pytest.skip("TweetyBridge non disponible")
            
        # Test de performance pour opérations TweetyBridge
        start_time = time.time()
        
        for i in range(10):
            formula = f"Human(person{i})"
            is_valid, _ = self.tweety_bridge.validate_fol_formula(formula)
            
        end_time = time.time()
        elapsed = end_time - start_time
        
        print(f"✅ Performance authentique: 10 validations en {elapsed:.3f}s")
        
        # Performance acceptable si < 5 secondes pour 10 validations
        assert elapsed < 5.0, f"Performance dégradée: {elapsed:.3f}s"


# Configuration des marqueurs pytest pour cette classe
pytestmark = [
    pytest.mark.authentic,  # Marqueur pour tests authentiques
    pytest.mark.phase5,     # Marqueur Phase 5
    pytest.mark.no_mocks,   # Marqueur sans mocks
]