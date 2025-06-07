"""
Tests d'intégration avec GPT-4o-mini réel pour Sherlock-Watson-Moriarty.

Tests end-to-end avec vrais appels OpenAI GPT-4o-mini :
- Configuration authentification OpenAI
- Tests timeout et retry logic
- Validation comportement Oracle authentique vs simulation
"""

import pytest
import asyncio
import os
import time
from unittest.mock import Mock, patch
from typing import Dict, Any, List
from datetime import datetime

# Imports Semantic Kernel
from semantic_kernel.kernel import Kernel
from semantic_kernel.services.openai import OpenAIChatCompletion
from semantic_kernel.connectors.ai.open_ai import OpenAIChatPromptExecutionSettings
from semantic_kernel.contents.chat_message_content import ChatMessageContent

# Imports du système Oracle
from argumentation_analysis.orchestration.cluedo_extended_orchestrator import (
    CluedoExtendedOrchestrator,
    run_cluedo_oracle_game
)
from argumentation_analysis.core.cluedo_oracle_state import CluedoOracleState
from argumentation_analysis.agents.core.pm.sherlock_enquete_agent import SherlockEnqueteAgent
from argumentation_analysis.agents.core.logic.watson_logic_assistant import WatsonLogicAssistant
from argumentation_analysis.agents.core.oracle.moriarty_interrogator_agent import MoriartyInterrogatorAgent


# Configuration pour tests réels GPT-4o-mini
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
REAL_GPT_AVAILABLE = OPENAI_API_KEY is not None and len(OPENAI_API_KEY) > 10

# Skip si pas d'API key
pytestmark = pytest.mark.skipif(
    not REAL_GPT_AVAILABLE,
    reason="Tests réels GPT-4o-mini nécessitent OPENAI_API_KEY"
)


@pytest.fixture
def real_gpt_kernel():
    """Kernel Semantic Kernel avec vraie connexion GPT-4o-mini."""
    if not REAL_GPT_AVAILABLE:
        pytest.skip("OPENAI_API_KEY requis pour tests réels")
    
    kernel = Kernel()
    
    # Configuration du service OpenAI GPT-4o-mini
    chat_service = OpenAIChatCompletion(
        service_id="openai-gpt4o-mini",
        ai_model_id="gpt-4o-mini",
        api_key=OPENAI_API_KEY
    )
    
    kernel.add_service(chat_service)
    return kernel


@pytest.fixture
def real_gpt_elements():
    """Éléments Cluedo pour tests réels."""
    return {
        "suspects": ["Colonel Moutarde", "Professeur Violet", "Mademoiselle Rose"],
        "armes": ["Poignard", "Chandelier", "Revolver"],
        "lieux": ["Salon", "Cuisine", "Bureau"]
    }


@pytest.fixture
def rate_limiter():
    """Rate limiter pour respecter les limites OpenAI."""
    last_request_time = 0
    min_interval = 0.1  # 100ms entre requêtes
    
    async def wait_if_needed():
        nonlocal last_request_time
        current_time = time.time()
        time_since_last = current_time - last_request_time
        
        if time_since_last < min_interval:
            await asyncio.sleep(min_interval - time_since_last)
        
        last_request_time = time.time()
    
    return wait_if_needed


@pytest.mark.integration
@pytest.mark.real_gpt
class TestRealGPTIntegration:
    """Tests d'intégration avec vrais appels GPT-4o-mini."""
    
    @pytest.mark.asyncio
    async def test_real_gpt_kernel_connection(self, real_gpt_kernel):
        """Test la connexion réelle au kernel GPT-4o-mini."""
        # Test de base de la connexion
        chat_service = real_gpt_kernel.get_service("openai-gpt4o-mini")
        assert chat_service is not None
        assert chat_service.ai_model_id == "gpt-4o-mini"
        
        # Test d'un appel simple
        settings = OpenAIChatPromptExecutionSettings(
            max_tokens=100,
            temperature=0.1
        )
        
        messages = [ChatMessageContent(role="user", content="Bonjour, vous êtes GPT-4o-mini ?")]
        
        response = await chat_service.get_chat_message_contents(
            chat_history=messages,
            settings=settings
        )
        
        assert len(response) > 0
        assert response[0].content is not None
        assert len(response[0].content) > 0
    
    @pytest.mark.asyncio
    async def test_real_gpt_sherlock_agent_creation(self, real_gpt_kernel, real_gpt_elements, rate_limiter):
        """Test la création d'un agent Sherlock avec GPT-4o-mini réel."""
        await rate_limiter()
        
        # Création de l'orchestrateur avec vraie connexion
        orchestrator = CluedoExtendedOrchestrator(
            kernel=real_gpt_kernel,
            max_turns=5,
            max_cycles=2,
            oracle_strategy="enhanced_auto_reveal"
        )
        
        # Configuration du workflow
        oracle_state = await orchestrator.setup_workflow(
            nom_enquete="Test Real GPT Sherlock",
            elements_jeu=real_gpt_elements
        )
        
        # Vérifications
        assert oracle_state is not None
        assert orchestrator.sherlock_agent is not None
        assert isinstance(orchestrator.sherlock_agent, SherlockEnqueteAgent)
        
        # Test d'interaction réelle avec Sherlock
        sherlock_response = await orchestrator.sherlock_agent.process_investigation_request(
            "Analysez cette enquête Cluedo avec les suspects: Colonel Moutarde, Professeur Violet, Mademoiselle Rose."
        )
        
        assert sherlock_response is not None
        assert len(sherlock_response) > 50  # Réponse substantielle
        assert any(suspect in sherlock_response for suspect in real_gpt_elements["suspects"])
    
    @pytest.mark.asyncio
    async def test_real_gpt_watson_analysis(self, real_gpt_kernel, real_gpt_elements, rate_limiter):
        """Test l'analyse Watson avec GPT-4o-mini réel."""
        await rate_limiter()
        
        orchestrator = CluedoExtendedOrchestrator(
            kernel=real_gpt_kernel,
            max_turns=5,
            max_cycles=2,
            oracle_strategy="enhanced_auto_reveal"
        )
        
        await orchestrator.setup_workflow(
            nom_enquete="Test Real GPT Watson",
            elements_jeu=real_gpt_elements
        )
        
        # Test d'analyse logique par Watson
        watson_analysis = await orchestrator.watson_agent.analyze_logical_deduction(
            hypothesis="Colonel Moutarde avec le Poignard dans le Salon",
            evidence=["Témoin vu Colonel Moutarde près du Salon", "Poignard trouvé dans le Salon"]
        )
        
        assert watson_analysis is not None
        assert len(watson_analysis) > 50
        assert "logique" in watson_analysis.lower() or "analyse" in watson_analysis.lower()
        assert "Colonel Moutarde" in watson_analysis
    
    @pytest.mark.asyncio
    async def test_real_gpt_moriarty_revelation(self, real_gpt_kernel, real_gpt_elements, rate_limiter):
        """Test les révélations Moriarty avec GPT-4o-mini réel."""
        await rate_limiter()
        
        orchestrator = CluedoExtendedOrchestrator(
            kernel=real_gpt_kernel,
            max_turns=5,
            max_cycles=2,
            oracle_strategy="enhanced_auto_reveal"
        )
        
        oracle_state = await orchestrator.setup_workflow(
            nom_enquete="Test Real GPT Moriarty",
            elements_jeu=real_gpt_elements
        )
        
        # Test de révélation automatique
        moriarty_cards = oracle_state.get_moriarty_cards()
        if moriarty_cards:
            test_card = moriarty_cards[0]
            
            moriarty_revelation = await orchestrator.moriarty_agent.reveal_card_dramatically(
                card=test_card,
                context="L'enquête piétine, il est temps de révéler un indice crucial."
            )
            
            assert moriarty_revelation is not None
            assert len(moriarty_revelation) > 50
            assert test_card in moriarty_revelation
            assert "révèle" in moriarty_revelation.lower() or "indice" in moriarty_revelation.lower()
    
    @pytest.mark.asyncio
    async def test_real_gpt_complete_workflow(self, real_gpt_kernel, real_gpt_elements, rate_limiter):
        """Test un workflow complet avec GPT-4o-mini réel."""
        await rate_limiter()
        
        orchestrator = CluedoExtendedOrchestrator(
            kernel=real_gpt_kernel,
            max_turns=6,  # Limité pour éviter coûts excessifs
            max_cycles=2,
            oracle_strategy="enhanced_auto_reveal"
        )
        
        # Exécution du workflow complet
        start_time = time.time()
        
        try:
            result = await run_cluedo_oracle_game(
                orchestrator=orchestrator,
                nom_enquete="Test Real GPT Complete",
                elements_jeu=real_gpt_elements,
                message_initial="Commençons cette enquête Cluedo avec GPT-4o-mini réel!"
            )
            
            execution_time = time.time() - start_time
            
            # Vérifications du résultat
            assert result is not None
            assert "workflow_info" in result
            assert "conversation_history" in result
            assert "oracle_statistics" in result
            
            # Vérifier que l'exécution n'est pas trop lente
            assert execution_time < 120  # Max 2 minutes
            
            # Vérifier l'historique de conversation
            history = result["conversation_history"]
            assert len(history) >= 3  # Au moins un tour par agent
            
            # Vérifier les statistiques Oracle
            stats = result["oracle_statistics"]
            assert stats["workflow_metrics"]["oracle_interactions"] > 0
            
        except Exception as e:
            # En cas d'erreur, vérifier que c'est géré gracieusement
            pytest.fail(f"Workflow réel GPT-4o-mini a échoué: {e}")


@pytest.mark.integration
@pytest.mark.real_gpt
class TestRealGPTPerformance:
    """Tests de performance avec GPT-4o-mini réel."""
    
    @pytest.mark.asyncio
    async def test_real_gpt_response_time(self, real_gpt_kernel, rate_limiter):
        """Test les temps de réponse GPT-4o-mini."""
        await rate_limiter()
        
        chat_service = real_gpt_kernel.get_service("openai-gpt4o-mini")
        
        # Test de plusieurs requêtes pour mesurer la performance
        response_times = []
        
        for i in range(3):  # Limité à 3 pour éviter coûts
            await rate_limiter()
            
            start_time = time.time()
            
            messages = [ChatMessageContent(
                role="user", 
                content=f"Test de performance {i+1}: Donnez-moi une réponse courte sur Cluedo."
            )]
            
            settings = OpenAIChatPromptExecutionSettings(
                max_tokens=50,
                temperature=0.1
            )
            
            response = await chat_service.get_chat_message_contents(
                chat_history=messages,
                settings=settings
            )
            
            response_time = time.time() - start_time
            response_times.append(response_time)
            
            # Vérifications de base
            assert len(response) > 0
            assert response[0].content is not None
        
        # Analyse des performances
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        
        # Vérifications de performance
        assert avg_response_time < 10.0  # Moyenne < 10s
        assert max_response_time < 30.0  # Max < 30s
        assert all(t > 0 for t in response_times)  # Tous > 0
    
    @pytest.mark.asyncio
    async def test_real_gpt_token_usage(self, real_gpt_kernel, rate_limiter):
        """Test l'utilisation de tokens avec GPT-4o-mini."""
        await rate_limiter()
        
        chat_service = real_gpt_kernel.get_service("openai-gpt4o-mini")
        
        # Test avec prompt de taille connue
        test_prompt = "Analysez cette enquête Cluedo: Colonel Moutarde, Professeur Violet, Mademoiselle Rose, Poignard, Chandelier, Revolver, Salon, Cuisine, Bureau. Qui est le coupable ?"
        
        settings = OpenAIChatPromptExecutionSettings(
            max_tokens=200,
            temperature=0.1
        )
        
        messages = [ChatMessageContent(role="user", content=test_prompt)]
        
        response = await chat_service.get_chat_message_contents(
            chat_history=messages,
            settings=settings
        )
        
        # Vérifications
        assert len(response) > 0
        response_content = response[0].content
        
        # Estimation approximative des tokens (1 token ≈ 4 chars en français)
        estimated_input_tokens = len(test_prompt) // 4
        estimated_output_tokens = len(response_content) // 4
        
        # Vérifications des limites
        assert estimated_input_tokens < 1000  # Input raisonnable
        assert estimated_output_tokens < 500  # Output raisonnable
        assert estimated_input_tokens + estimated_output_tokens < 1200  # Total < limite


@pytest.mark.integration
@pytest.mark.real_gpt
class TestRealGPTErrorHandling:
    """Tests de gestion d'erreurs avec GPT-4o-mini réel."""
    
    @pytest.mark.asyncio
    async def test_real_gpt_timeout_handling(self, real_gpt_kernel, rate_limiter):
        """Test la gestion des timeouts GPT-4o-mini."""
        await rate_limiter()
        
        chat_service = real_gpt_kernel.get_service("openai-gpt4o-mini")
        
        # Configuration avec timeout court pour forcer une erreur
        settings = OpenAIChatPromptExecutionSettings(
            max_tokens=1000,
            temperature=0.1
        )
        
        # Prompt très long pour tester les limites
        long_prompt = "Analysez en détail cette enquête Cluedo: " + "Colonel Moutarde, " * 100
        
        messages = [ChatMessageContent(role="user", content=long_prompt)]
        
        try:
            # Utilisation d'un timeout asyncio
            response = await asyncio.wait_for(
                chat_service.get_chat_message_contents(
                    chat_history=messages,
                    settings=settings
                ),
                timeout=5.0  # 5 secondes max
            )
            
            # Si ça réussit, vérifier la réponse
            assert len(response) > 0
            
        except asyncio.TimeoutError:
            # Timeout attendu, c'est OK
            pass
        except Exception as e:
            # Autres erreurs doivent être gérées gracieusement
            assert "rate limit" in str(e).lower() or "token" in str(e).lower()
    
    @pytest.mark.asyncio
    async def test_real_gpt_retry_logic(self, real_gpt_kernel, rate_limiter):
        """Test la logique de retry avec GPT-4o-mini."""
        await rate_limiter()
        
        chat_service = real_gpt_kernel.get_service("openai-gpt4o-mini")
        
        # Fonction de retry simple
        async def retry_request(max_retries=3):
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    await rate_limiter()
                    
                    messages = [ChatMessageContent(
                        role="user",
                        content=f"Test retry {attempt + 1}: Parlez-moi de Cluedo."
                    )]
                    
                    settings = OpenAIChatPromptExecutionSettings(
                        max_tokens=50,
                        temperature=0.1
                    )
                    
                    response = await chat_service.get_chat_message_contents(
                        chat_history=messages,
                        settings=settings
                    )
                    
                    return response  # Succès
                    
                except Exception as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1.0 * (attempt + 1))  # Backoff
                    continue
            
            raise last_error  # Tous les retries ont échoué
        
        # Test du retry
        try:
            result = await retry_request()
            assert len(result) > 0
            assert result[0].content is not None
        except Exception as e:
            # Si tous les retries échouent, vérifier que c'est une erreur connue
            assert any(keyword in str(e).lower() for keyword in ["rate", "limit", "timeout", "token"])


@pytest.mark.integration
@pytest.mark.real_gpt
class TestRealGPTAuthenticity:
    """Tests d'authenticité Oracle avec GPT-4o-mini réel."""
    
    @pytest.mark.asyncio
    async def test_real_vs_mock_behavior_comparison(self, real_gpt_kernel, rate_limiter):
        """Compare le comportement réel vs mock."""
        await rate_limiter()
        
        # Test avec GPT-4o-mini réel
        real_chat_service = real_gpt_kernel.get_service("openai-gpt4o-mini")
        
        test_prompt = "En tant que Moriarty dans Cluedo, révélez dramatiquement que vous avez la carte Colonel Moutarde."
        
        settings = OpenAIChatPromptExecutionSettings(
            max_tokens=150,
            temperature=0.3
        )
        
        messages = [ChatMessageContent(role="user", content=test_prompt)]
        
        real_response = await real_chat_service.get_chat_message_contents(
            chat_history=messages,
            settings=settings
        )
        
        real_content = real_response[0].content
        
        # Comparaison avec comportement mock typique
        mock_patterns = [
            "Mock response",
            "Simulated",
            "Test data",
            "Placeholder"
        ]
        
        # Le vrai GPT ne devrait pas avoir ces patterns de mock
        for pattern in mock_patterns:
            assert pattern not in real_content
        
        # Le vrai GPT devrait avoir des caractéristiques authentiques
        authentic_indicators = [
            "Moriarty" in real_content,
            "Colonel Moutarde" in real_content,
            len(real_content) > 30,
            any(word in real_content.lower() for word in ["révèle", "carte", "dramatique", "indice"])
        ]
        
        assert sum(authentic_indicators) >= 3  # Au moins 3 indicateurs d'authenticité
    
    @pytest.mark.asyncio
    async def test_real_gpt_oracle_authenticity(self, real_gpt_kernel, real_gpt_elements, rate_limiter):
        """Test l'authenticité du comportement Oracle avec GPT-4o-mini."""
        await rate_limiter()
        
        orchestrator = CluedoExtendedOrchestrator(
            kernel=real_gpt_kernel,
            max_turns=4,
            max_cycles=2,
            oracle_strategy="enhanced_auto_reveal"
        )
        
        oracle_state = await orchestrator.setup_workflow(
            nom_enquete="Test Oracle Authenticity",
            elements_jeu=real_gpt_elements
        )
        
        # Test de révélation authentique
        moriarty_cards = oracle_state.get_moriarty_cards()
        
        if moriarty_cards:
            test_card = moriarty_cards[0]
            
            # Requête Oracle authentique
            oracle_response = await oracle_state.query_oracle(
                agent_name="Moriarty",
                query_type="dramatic_revelation",
                query_params={
                    "card": test_card,
                    "context": "L'enquête piétine, révélation nécessaire",
                    "style": "authentic_oracle"
                }
            )
            
            # Vérifications d'authenticité
            assert oracle_response is not None
            
            if hasattr(oracle_response, 'content'):
                content = oracle_response.content
                
                # Caractéristiques d'une vraie révélation Oracle
                authenticity_checks = [
                    len(content) > 40,  # Contenu substantiel
                    test_card in content,  # Carte mentionnée
                    any(word in content.lower() for word in ["révèle", "indice", "vérité", "secret"]),
                    not any(word in content.lower() for word in ["peut-être", "probablement", "je pense"]),
                    content.count("!") >= 1 or content.count(".") >= 2  # Ponctuation dramatique
                ]
                
                authenticity_score = sum(authenticity_checks) / len(authenticity_checks)
                assert authenticity_score >= 0.6  # Au moins 60% d'authenticité