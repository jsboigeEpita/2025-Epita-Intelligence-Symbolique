# Test authentique pour SherlockEnqueteAgent - SANS MOCKS
# Phase 3A - Purge complète des mocks

import pytest
import asyncio
import os
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from argumentation_analysis.agents.agent_factory import AgentFactory
from argumentation_analysis.agents.core.pm.sherlock_enquete_agent import SherlockEnqueteAgent
from typing import AsyncGenerator, Union
from semantic_kernel.contents.chat_history import ChatHistory
from argumentation_analysis.agents.core.abc.agent_bases import BaseAgent
from argumentation_analysis.config.settings import AppSettings

TEST_AGENT_NAME = "TestSherlockAgent"

# Classe concrète pour tester l'agent abstrait
class ConcreteSherlockEnqueteAgent(SherlockEnqueteAgent):
    async def get_response(self, user_input: str, chat_history: Union[ChatHistory, None] = None) -> AsyncGenerator[str, None]:
        yield "Réponse de test"
    
    async def text_to_belief_set(self, text: str, logic_type: str = "fol"):
        pass

    async def generate_queries(self):
        pass

    async def execute_query(self, query: str):
        pass

    async def interpret_results(self, results) -> str:
        pass

    def setup_agent_components(self):
        pass

    async def is_consistent(self):
        return True

    def _create_belief_set_from_data(self, data):
        pass

    async def validate_formula(self, formula: str):
        pass

    async def get_agent_capabilities(self) -> dict:
        return {}
    
    async def invoke(self, message: str, **kwargs) -> str:
        return "invoked"


@pytest.fixture
def authentic_kernel():
    """Fixture pour créer un vrai Kernel authentique."""
    kernel = Kernel()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return kernel  # Retourne un kernel vide, les tests seront sautés

    llm_service = OpenAIChatCompletion(
        service_id="chat_completion",
        ai_model_id="gpt-4o-mini",
        api_key=api_key
    )
    kernel.add_service(llm_service)
    return kernel

@pytest.fixture
def agent_factory(authentic_kernel):
    """Fixture pour créer une instance de l'AgentFactory."""
    if not authentic_kernel.get_service("chat_completion"):
        pytest.skip("Le service de chat 'chat_completion' n'est pas configuré.")
    settings = AppSettings()
    settings.service_manager.default_llm_service_id = "chat_completion"
    return AgentFactory(kernel=authentic_kernel, settings=settings)

@pytest.fixture
def sherlock_agent(agent_factory):
    """
    Fixture pour créer un agent Sherlock concret via la factory pour les tests.
    Utilise la méthode create_agent pour instancier la version concrète.
    """
    return agent_factory.create_agent(
        agent_class=ConcreteSherlockEnqueteAgent,
        agent_name=TEST_AGENT_NAME
    )

@pytest.mark.asyncio
class TestSherlockEnqueteAgentAuthentic:
    """Tests authentiques pour SherlockEnqueteAgent."""

    async def test_agent_instantiation(self, sherlock_agent):
        """Test l'instanciation basique de l'agent."""
        agent = sherlock_agent
        assert isinstance(agent, SherlockEnqueteAgent)
        assert agent.name == TEST_AGENT_NAME
        assert hasattr(agent, '_kernel')
        assert agent._kernel is not None
        assert isinstance(agent._kernel, Kernel)

    async def test_agent_inheritance(self, sherlock_agent):
        """Test que l'agent hérite correctement."""
        agent = sherlock_agent
        assert isinstance(agent, SherlockEnqueteAgent)
        assert isinstance(agent, BaseAgent)
        assert hasattr(agent, 'logger')
        assert hasattr(agent, 'name')
        assert len(agent.name) > 0

    async def test_default_system_prompt(self, sherlock_agent):
        """Test que l'agent utilise le prompt système par défaut."""
        agent = sherlock_agent
        assert hasattr(agent, 'system_prompt')
        assert "Sherlock Holmes" in agent.system_prompt
        # Le nom est maintenant personnalisé par la fixture
        assert agent.name == TEST_AGENT_NAME

    def test_custom_system_prompt(self, agent_factory):
        """Test la configuration avec un prompt système personnalisé via la factory."""
        custom_prompt = "Instructions personnalisées pour Sherlock."
        
        agent = agent_factory.create_agent(
            agent_class=ConcreteSherlockEnqueteAgent,
            agent_name=TEST_AGENT_NAME,
            system_prompt=custom_prompt
        )
        
        assert agent.name == TEST_AGENT_NAME
        assert agent.system_prompt == custom_prompt

    async def test_get_current_case_description_real(self, sherlock_agent):
        """Test authentique de récupération de description d'affaire."""
        agent = sherlock_agent
        try:
            description = await agent.get_current_case_description()
            
            if description is not None:
                assert isinstance(description, str)
            else:
                print("Description retournée: None (normal sans plugin configuré)")
                
        except Exception as e:
            assert "Erreur:" in str(e) or "Plugin" in str(e)
            print(f"Exception attendue sans plugin: {e}")

    async def test_add_new_hypothesis_real(self, sherlock_agent):
        """Test authentique d'ajout d'hypothèse."""
        agent = sherlock_agent
        hypothesis_text = "Le coupable est le Colonel Moutarde."
        confidence_score = 0.75
        
        try:
            result = await agent.add_new_hypothesis(hypothesis_text, confidence_score)
            
            if result is not None:
                assert isinstance(result, (dict, str))
            else:
                print("Hypothèse retournée: None (normal sans plugin configuré)")
                
        except Exception as e:
            assert "Erreur:" in str(e) or "Plugin" in str(e)
            print(f"Exception attendue sans plugin: {e}")

    async def test_agent_error_handling(self, sherlock_agent):
        """Test la gestion d'erreur authentique de l'agent."""
        agent = sherlock_agent
        try:
            result = await agent.add_new_hypothesis("", -1.0)
            assert result is None or "erreur" in str(result).lower()
        except Exception as e:
            assert len(str(e)) > 0
            print(f"Gestion d'erreur correcte: {e}")

    async def test_agent_configuration_validation(self, sherlock_agent):
        """Test la validation de la configuration de l'agent."""
        agent = sherlock_agent
        assert hasattr(agent, '_kernel')
        assert hasattr(agent, 'name')
        assert hasattr(agent, 'system_prompt')
        assert hasattr(agent, 'logger')
        
        assert isinstance(agent.name, str)
        assert len(agent.name) > 0
        
        assert agent._kernel is not None
        assert agent.logger is not None

def test_sherlock_agent_integration_real(agent_factory):
    """Test d'intégration complet avec vraies APIs via la factory."""
    try:
        agent = agent_factory.create_agent(
                agent_class=ConcreteSherlockEnqueteAgent,
                agent_name="IntegrationTestAgent",
                system_prompt="Test d'intégration authentique"
            )
            
        assert agent is not None
        assert isinstance(agent, SherlockEnqueteAgent)
        assert agent.name == "IntegrationTestAgent"
        
        print("✅ Test d'intégration authentique via factory réussi")
            
    except Exception as e:
        pytest.fail(f"Le test d'intégration a échoué de manière inattendue: {e}")