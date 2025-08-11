
# Authentic gpt-4o-mini imports (replacing mocks)
import openai # Gardé pour l'instant, pourrait être utilisé par le kernel SK sous-jacent
from semantic_kernel.contents import ChatHistory # Utile si on fait des appels de type chat
from semantic_kernel.core_plugins import ConversationSummaryPlugin # Potentiellement utile
from config.unified_config import UnifiedConfig, MockLevel
# AuthenticSemanticKernel n'existe pas, on utilise le Kernel SK standard
from argumentation_analysis.orchestration.service_manager import OrchestrationServiceManager
import pytest
import logging
from unittest.mock import MagicMock
import asyncio # Ajout pour IsolatedAsyncioTestCase et asyncSetUp

# Configuration du logger
logger = logging.getLogger(__name__)
# Configuration du logger pour éviter les doublons si le module est rechargé
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


# -*- coding: utf-8 -*-
# tests/agents/core/logic/test_abstract_logic_agent.py
"""
Tests unitaires pour la classe AbstractLogicAgent.
"""

import unittest


from semantic_kernel import Kernel
from semantic_kernel.functions import KernelArguments # Assurer que KernelArguments est importé

from argumentation_analysis.agents.core.abc.agent_bases import BaseLogicAgent
from argumentation_analysis.agents.core.logic.belief_set import BeliefSet


class MockLogicAgent(BaseLogicAgent):
    """Classe concrète pour tester la classe abstraite AbstractLogicAgent."""
    
    def __init__(self, kernel: Kernel, agent_name: str):
        super().__init__(kernel, agent_name, "mock_logic")

    def setup_kernel(self, kernel_instance: Kernel): # Type hint ajouté
        """Implémentation de la méthode abstraite."""
        # Ici, on pourrait ajouter des plugins spécifiques au kernel si nécessaire pour l'agent
        pass
    
    async def text_to_belief_set(self, text, context=None):
        """Implémentation de la méthode abstraite."""
        return MagicMock(spec=BeliefSet), "Conversion réussie"
    
    async def generate_queries(self, text, belief_set, context=None):
        """Implémentation de la méthode abstraite."""
        return ["query1", "query2"]
    
    def execute_query(self, belief_set, query):
        """Implémentation de la méthode abstraite."""
        return True, "Requête exécutée avec succès"
    
    async def interpret_results(self, text, belief_set, queries, results):
        """Implémentation de la méthode abstraite."""
        return "Interprétation des résultats"
    
    def _create_belief_set_from_data(self, belief_set_data):
        """Implémentation de la méthode abstraite."""
        return MagicMock(spec=BeliefSet)

    def get_agent_capabilities(self):
        """Implémentation de la méthode abstraite."""
        pass

    async def get_response(self, user_input: str, chat_history: any):
        """Implémentation de la méthode abstraite."""
        pass

    async def invoke(self, input, context):
        """Implémentation de la méthode abstraite."""
        pass

    def is_consistent(self, belief_set):
        """Implémentation de la méthode abstraite."""
        return True, "Consistent"

    def setup_agent_components(self, config: "UnifiedConfig"):
        """Implémentation de la méthode abstraite."""
        pass

    def validate_formula(self, formula: str, logic_type: str = "propositional"):
        """Implémentation de la méthode abstraite."""
        return True, "Valid"

    async def invoke_single(self, *args, **kwargs):
        """Implémentation de la méthode abstraite."""
        pass

    def validate_argument(self, argument, metadata):
        """Implémentation de la méthode abstraite."""
        pass


@pytest.mark.no_mocks
@pytest.mark.requires_api_key
# @pytest.mark.usefixtures("jvm_session")  # Désactivé pour le débogage du crash JVM
class TestAbstractLogicAgent: # Supprime l'héritage de unittest

    @pytest.fixture(autouse=True)
    async def setup_method(self):
        """Fixture pytest pour l'initialisation avant chaque test."""
        logger.info("Setting up test case for pytest in TestAbstractLogicAgent...")
        self.state_manager = OrchestrationServiceManager()
        
        self.config = UnifiedConfig()
        self.config.mock_level = MockLevel.NONE
        self.config.use_authentic_llm = True
        self.config.use_mock_llm = False
        
        self.kernel = Kernel() # Utiliser un Kernel mocké pour les tests unitaires
        self.agent = MockLogicAgent(self.kernel, "TestAgent")

        self.initial_snapshot_data = {
            "raw_text": "Texte de test",
            "belief_sets": {
                "bs1": {"logic_type": "propositional", "content": "a => b"}
            }
        }

        # Réinitialiser l'état du state_manager
        self.state_manager.state.raw_text = self.initial_snapshot_data["raw_text"]
        self.state_manager.state.belief_sets = self.initial_snapshot_data["belief_sets"].copy()
        
        self.state_manager.get_current_state_snapshot = MagicMock(return_value=self.initial_snapshot_data)
        self.state_manager.add_answer = MagicMock()
        self.state_manager.add_belief_set = MagicMock(return_value="bs_mock_id")
        self.state_manager.log_query_result = MagicMock(return_value="log_mock_id")

    async def _create_authentic_kernel_instance(self) -> Kernel: # Renommé et corrigé
        """Crée une instance authentique du Kernel Semantic Kernel."""
        config = UnifiedConfig()
        config.mock_level = MockLevel.NONE
        config.use_authentic_llm = True
        config.use_mock_llm = False
        return config.get_kernel_with_gpt4o_mini()
        
    async def _make_authentic_llm_call(self, kernel: Kernel, prompt: str) -> str: # Prend kernel en argument
        """Fait un appel authentique à gpt-4o-mini via le kernel fourni."""
        # This test now uses the class-level state manager.
        # This method might need to be adapted if it depends on per-test setup.
        try:
            result = await kernel.invoke_prompt_async(prompt, arguments=KernelArguments())
            return str(result)
        except Exception as e:
            logger.error(f"Appel LLM authentique échoué: {e}", exc_info=True)
            return "Authentic LLM call failed"


    
    async def test_initialization(self):
        """Test de l'initialisation de l'agent."""
        assert self.agent.name == "TestAgent"
        assert self.agent._kernel is not None
        assert isinstance(self.agent._kernel, Kernel)

    async def test_process_task_unknown_task(self):
        """Test du traitement d'une tâche inconnue."""
        result = await self.agent.process_task("task1", "Tâche inconnue", self.state_manager)
        assert result["status"] == "error"

    async def test_handle_translation_task(self):
        """Test du traitement d'une tâche de traduction."""
        task_description = "Traduire le texte en Belief Set: Ceci est un texte pour la traduction."
        
        self.state_manager.state.raw_text = "Ceci est un texte pour la traduction."
        
        result = await self.agent.process_task("task_translation", task_description, self.state_manager)
        assert result["status"] == "success"

    async def test_handle_query_task(self):
        """Test du traitement d'une tâche d'exécution de requêtes."""
        self.state_manager.state.raw_text = "Texte de requête pour bs1."
        self.state_manager.state.belief_sets['bs1'] = {"logic_type": "propositional", "content": "a => b"}
        
        mock_bs_instance = MagicMock(spec=BeliefSet)
        self.agent._create_belief_set_from_data = lambda data_dict: mock_bs_instance

        result = await self.agent.process_task(
            "task_query",
            "Exécuter les Requêtes sur belief_set_id: bs1",
            self.state_manager
        )
        assert result["status"] == "success"

    async def test_extract_source_text_from_state(self):
        """Test de l'extraction du texte source depuis l'état."""
        text = self.agent._extract_source_text("", self.initial_snapshot_data)
        assert text == "Texte de test"
    
    def test_extract_source_text_from_description(self):
        """Test de l'extraction du texte source depuis la description."""
        text = self.agent._extract_source_text(
            "Analyser le texte: Ceci est un test", 
            {"raw_text": ""}
        )
        assert text == "Ceci est un test"
    
    def test_extract_belief_set_id(self):
        """Test de l'extraction de l'ID de l'ensemble de croyances."""
        bs_id = self.agent._extract_belief_set_id("Requête sur belief_set_id: bs123")
        assert bs_id == "bs123"
    
    def test_extract_belief_set_id_not_found(self):
        """Test de l'extraction de l'ID de l'ensemble de croyances non trouvé."""
        bs_id = self.agent._extract_belief_set_id("Requête sans ID")
        assert bs_id is None


if __name__ == "__main__":
    unittest.main()