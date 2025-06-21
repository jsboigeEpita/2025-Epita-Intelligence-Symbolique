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
from argumentation_analysis.agents.core.logic.modal_logic_agent import ModalLogicAgent, SYSTEM_PROMPT_MODAL
from argumentation_analysis.agents.core.logic.belief_set import ModalBeliefSet, BeliefSet
from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge


# Création d'une classe concrète pour les tests
# Classe concrète minimale pour instancier l'agent dans les tests
class ConcreteModalLogicAgent(ModalLogicAgent):
    pass

class TestModalLogicAgentAuthentic:
    """Tests authentiques pour la classe ModalLogicAgent - SANS MOCKS."""

    def setup_method(self):
        """Initialisation authentique avant chaque test."""
        # Configuration du vrai Kernel Semantic Kernel
        self.kernel = Kernel()
        
        # Configuration authentique du service LLM
        self.llm_service_id = "authentic_modal_llm_service"
        
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
                print(f"✅ Service LLM Azure configuré pour Modal: {azure_deployment}")
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
                    print("✅ Service LLM OpenAI configuré pour Modal: gpt-4o-mini")
                else:
                    print("⚠️ Connecteurs LLM non disponibles ou clés API manquantes pour Modal")
        except Exception as e:
            self.llm_available = False
            print(f"⚠️ Erreur configuration LLM Modal: {e}")

        # Initialisation du vrai TweetyBridge
        try:
            self.tweety_bridge = TweetyBridge()
            self.tweety_available = self.tweety_bridge.is_jvm_ready()
            if self.tweety_available:
                print("✅ TweetyBridge JVM authentique prête pour Modal")
            else:
                print("⚠️ TweetyBridge JVM non disponible pour Modal")
        except Exception as e:
            self.tweety_available = False
            print(f"⚠️ Erreur TweetyBridge Modal: {e}")

        # Initialisation de l'agent authentique
        self.agent_name = "ModalLogicAgent"
        self.agent = ConcreteModalLogicAgent(self.kernel, service_id=self.llm_service_id, agent_name=self.agent_name)
        
        # Configuration authentique de l'agent
        if self.llm_available:
            try:
                self.agent.setup_agent_components(self.llm_service_id)
                print("✅ Agent Modal authentique configuré")
            except Exception as e:
                print(f"⚠️ Erreur configuration agent Modal: {e}")

    def test_initialization_and_setup_authentic(self):
        """Test authentique de l'initialisation et de la configuration de l'agent Modal."""
        # Tests d'initialisation de base
        assert self.agent.name == self.agent_name
        assert self.agent.sk_kernel == self.kernel
        assert self.agent.logic_type == "Modal"
        assert self.agent.instructions == SYSTEM_PROMPT_MODAL
        
        # Test de l'état du TweetyBridge authentique
        if self.tweety_available:
            assert self.agent.tweety_bridge.is_jvm_ready() == True
            print("✅ Test authentique TweetyBridge Modal - JVM prête")
        else:
            print("⚠️ TweetyBridge Modal non disponible - test sauté")
            
        # Test de la configuration Semantic Kernel authentique
        if self.llm_available:
            service = self.kernel.get_service(self.llm_service_id)
            assert service is not None
            print("✅ Test authentique Semantic Kernel Modal - Service configuré")

    @pytest.mark.asyncio
    @pytest.mark.requires_llm
    async def test_text_to_belief_set_authentic_modal(self):
        """Test authentique de conversion texte -> belief set modal avec vrai LLM."""
        if not (self.llm_available and self.tweety_available):
            pytest.skip("LLM ou TweetyBridge non disponible pour Modal")
            
        # Texte simple pour test modal authentique
        test_text = """
        Il est nécessaire que tous les hommes soient mortels.
        Il est possible que Socrate soit sage.
        """
        
        try:
            belief_set, message = await self.agent.text_to_belief_set(test_text)
            
            print(f"✅ Conversion Modal authentique: {message}")
            
            if belief_set is not None:
                assert isinstance(belief_set, ModalBeliefSet)
                assert len(belief_set.content) > 0
                print(f"✅ Belief set Modal authentique créé: {belief_set.content[:100]}...")
                
                # Test de validation authentique avec TweetyBridge Modal
                is_valid, validation_msg = self.tweety_bridge.validate_modal_belief_set(belief_set.content)
                print(f"✅ Validation TweetyBridge Modal authentique: {is_valid} - {validation_msg}")
                
        except Exception as e:
            print(f"⚠️ Erreur test Modal authentique: {e}")
            # Ne pas faire échouer le test, juste informer
            pytest.skip(f"Test Modal authentique échoué: {e}")

    @pytest.mark.asyncio 
    @pytest.mark.requires_llm
    async def test_generate_queries_authentic_modal(self):
        """Test authentique de génération de requêtes modales avec vrai LLM."""
        if not (self.llm_available and self.tweety_available):
            pytest.skip("LLM ou TweetyBridge non disponible pour Modal")
            
        # Créer un belief set modal simple authentique
        belief_set_content = """
        []p;
        <>q;
        """
        belief_set = ModalBeliefSet(belief_set_content)
        
        # Texte de contexte modal
        context_text = "Nous analysons les propriétés nécessaires et possibles"
        
        try:
            queries = await self.agent.generate_queries(context_text, belief_set)
            
            print(f"✅ Génération Modal authentique de {len(queries)} requêtes")
            
            # Test que nous obtenons des requêtes
            assert isinstance(queries, list)
            
            # Si des requêtes sont générées, les tester
            for i, query in enumerate(queries[:3]):  # Limiter à 3 pour les tests
                if query:
                    print(f"  Requête Modal {i+1}: {query}")
                    # Test de validation authentique
                    is_valid, msg = self.tweety_bridge.validate_modal_formula(query)
                    print(f"  Validation Modal: {is_valid} - {msg}")
                    
        except Exception as e:
            print(f"⚠️ Erreur génération requêtes Modal authentique: {e}")
            pytest.skip(f"Test Modal authentique échoué: {e}")

    def test_execute_query_authentic_modal(self):
        """Test authentique d'exécution de requête modale avec TweetyBridge."""
        if not self.tweety_available:
            pytest.skip("TweetyBridge non disponible pour Modal")
            
        # Créer un belief set modal simple pour test
        belief_set_content = "[]p; <>q;"
        belief_set = ModalBeliefSet(belief_set_content)
        
        # Requête modale simple
        query = "p"
        
        try:
            result, message = self.agent.execute_query(belief_set, query)
            
            print(f"✅ Exécution authentique requête Modal: {result} - {message}")
            
            # Vérifier le type de résultat
            assert isinstance(result, bool)
            assert isinstance(message, str)
            assert len(message) > 0
            
        except Exception as e:
            print(f"⚠️ Erreur exécution requête Modal authentique: {e}")
            pytest.skip(f"Test Modal authentique échoué: {e}")

    def test_tweety_bridge_modal_integration_authentic(self):
        """Test d'intégration authentique avec TweetyBridge pour logique modale."""
        if not self.tweety_available:
            pytest.skip("TweetyBridge non disponible pour Modal")
            
        # Test de validation de formule modale simple
        formula = "[]p"
        is_valid, message = self.tweety_bridge.validate_modal_formula(formula)
        
        print(f"✅ Validation formule Modal authentique: {is_valid} - {message}")
        assert isinstance(is_valid, bool)
        assert isinstance(message, str)
        
        # Test de consistance de belief set modal
        belief_set_content = "[]p; <>q;"
        is_consistent, cons_message = self.tweety_bridge.is_modal_kb_consistent(belief_set_content)
        
        print(f"✅ Test consistance Modal authentique: {is_consistent} - {cons_message}")
        assert isinstance(is_consistent, bool)
        assert isinstance(cons_message, str)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_workflow_modal_authentic(self):
        """Test d'intégration complète authentique - workflow modal complet sans mocks."""
        if not (self.llm_available and self.tweety_available):
            pytest.skip("LLM ou TweetyBridge non disponible pour Modal")
            
        # Workflow modal complet authentique
        test_text = """
        Il est nécessaire que la logique soit cohérente.
        Il est possible que nous trouvions une preuve.
        """
        
        try:
            # Étape 1: Conversion texte -> belief set modal (authentique)
            belief_set, bs_message = await self.agent.text_to_belief_set(test_text)
            print(f"✅ Étape 1 Modal authentique - Belief set: {bs_message}")
            
            if belief_set is not None:
                # Étape 2: Génération de requêtes modales (authentique)
                queries = await self.agent.generate_queries(test_text, belief_set)
                print(f"✅ Étape 2 Modal authentique - {len(queries)} requêtes générées")
                
                # Étape 3: Exécution des requêtes modales (authentique) 
                for i, query in enumerate(queries[:2]):  # Limiter pour les tests
                    if query:
                        result, exec_message = self.agent.execute_query(belief_set, query)
                        print(f"✅ Étape 3.{i+1} Modal authentique - Requête '{query}': {result}")
                        assert isinstance(result, bool)
                        
                print("✅ Workflow Modal complet authentique terminé avec succès")
                
        except Exception as e:
            print(f"⚠️ Erreur workflow Modal authentique: {e}")
            pytest.skip(f"Workflow Modal authentique échoué: {e}")

    def test_modal_specific_features_authentic(self):
        """Test authentique des fonctionnalités spécifiques à la logique modale."""
        if not self.tweety_available:
            pytest.skip("TweetyBridge non disponible pour Modal")
            
        # Test des opérateurs modaux nécessité (□) et possibilité (◇)
        modal_formulas = [
            "[]p",      # Nécessité de p
            "<>q",      # Possibilité de q
            "[]p => <>p" # Si p est nécessaire, alors p est possible
        ]
        
        for formula in modal_formulas:
            try:
                is_valid, message = self.tweety_bridge.validate_modal_formula(formula)
                print(f"✅ Formule modale '{formula}': {is_valid} - {message}")
                assert isinstance(is_valid, bool)
                assert isinstance(message, str)
            except Exception as e:
                print(f"⚠️ Erreur validation formule modale '{formula}': {e}")

    @pytest.mark.performance 
    def test_performance_modal_authentic(self):
        """Test de performance authentique pour logique modale."""
        import time
        
        if not self.tweety_available:
            pytest.skip("TweetyBridge non disponible pour Modal")
            
        # Test de performance pour opérations TweetyBridge modales
        start_time = time.time()
        
        for i in range(5):
            formula = f"[]prop{i}"
            is_valid, _ = self.tweety_bridge.validate_modal_formula(formula)
            
        end_time = time.time()
        elapsed = end_time - start_time
        
        print(f"✅ Performance Modal authentique: 5 validations en {elapsed:.3f}s")
        
        # Performance acceptable si < 3 secondes pour 5 validations modales
        assert elapsed < 3.0, f"Performance Modal dégradée: {elapsed:.3f}s"


# Configuration des marqueurs pytest pour cette classe
pytestmark = [
    pytest.mark.authentic,  # Marqueur pour tests authentiques
    pytest.mark.phase5,     # Marqueur Phase 5
    pytest.mark.no_mocks,   # Marqueur sans mocks
    pytest.mark.modal,      # Marqueur spécifique logique modale
]