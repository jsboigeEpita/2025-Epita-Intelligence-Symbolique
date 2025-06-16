
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
    
    def text_to_belief_set(self, text):
        """Implémentation de la méthode abstraite."""
        return MagicMock(spec=BeliefSet), "Conversion réussie"
    
    def generate_queries(self, text, belief_set):
        """Implémentation de la méthode abstraite."""
        return ["query1", "query2"]
    
    def execute_query(self, belief_set, query):
        """Implémentation de la méthode abstraite."""
        return True, "Requête exécutée avec succès"
    
    def interpret_results(self, text, belief_set, queries, results):
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

@pytest.mark.no_mocks
@pytest.mark.requires_api_key
class TestAbstractLogicAgent(unittest.IsolatedAsyncioTestCase): # Changé en IsolatedAsyncioTestCase
    
    async def _create_authentic_kernel_instance(self) -> Kernel: # Renommé et corrigé
        """Crée une instance authentique du Kernel Semantic Kernel."""
        config = UnifiedConfig()
        # S'assurer que la configuration est pour l'authenticité
        config.mock_level = MockLevel.NONE
        config.use_authentic_llm = True
        config.use_mock_llm = False # Explicitement False
        # Les autres flags d'authenticité sont gérés par _apply_authenticity_constraints dans UnifiedConfig
        return config.get_kernel_with_gpt4o_mini()
        
    async def _make_authentic_llm_call(self, kernel: Kernel, prompt: str) -> str: # Prend kernel en argument
        """Fait un appel authentique à gpt-4o-mini via le kernel fourni."""
        try:
            # Utilisation de invoke_prompt_async pour un simple prompt.
            result = await kernel.invoke_prompt_async(prompt, arguments=KernelArguments())
            return str(result)
        except Exception as e:
            logger.error(f"Appel LLM authentique échoué: {e}", exc_info=True)
            return "Authentic LLM call failed"

    """Tests pour la classe AbstractLogicAgent."""
    
    async def asyncSetUp(self): # Changé en asyncSetUp
        """Initialisation avant chaque test."""
        self.config = UnifiedConfig()
        # S'assurer que la config est pour l'authenticité pour le kernel de l'agent
        self.config.mock_level = MockLevel.NONE
        self.config.use_authentic_llm = True
        self.config.use_mock_llm = False
        
        self.kernel = self.config.get_kernel_with_gpt4o_mini()
        self.agent = MockLogicAgent(self.kernel, "TestAgent")
        
        self.state_manager = OrchestrationServiceManager()
        await self.state_manager.initialize() # Initialisation de OrchestrationServiceManager

        self.initial_snapshot_data = {
            "raw_text": "Texte de test",
            "belief_sets": {
                "bs1": {
                    "logic_type": "propositional",
                    "content": "a => b"
                }
            }
        }
        # Comment initialiser l'état dans OrchestrationServiceManager pour les tests ?
        # Pour l'instant, on va supposer que les méthodes de l'agent (comme process_task)
        # interagissent avec le state_manager d'une manière qui construit l'état nécessaire,
        # ou que le state_manager est pré-populé d'une manière ou d'une autre.
        # Exemple:
        if hasattr(self.state_manager.state, 'raw_text'): # Accès direct à l'attribut state de l'OSM
            self.state_manager.state.raw_text = self.initial_snapshot_data["raw_text"]
        if hasattr(self.state_manager.state, 'belief_sets'):
             self.state_manager.state.belief_sets = self.initial_snapshot_data["belief_sets"].copy()

        # Mock des méthodes manquantes sur OrchestrationServiceManager
        self.state_manager.get_current_state_snapshot = MagicMock(return_value=self.initial_snapshot_data)
        self.state_manager.add_answer = MagicMock()
        self.state_manager.add_belief_set = MagicMock(return_value="bs_mock_id")
        self.state_manager.log_query_result = MagicMock(return_value="log_mock_id")


    
    async def test_initialization(self):
        """Test de l'initialisation de l'agent."""
        self.assertEqual(self.agent.name, "TestAgent")
        self.assertIsNotNone(self.agent.sk_kernel)
        self.assertIsInstance(self.agent.sk_kernel, Kernel)

    async def test_process_task_unknown_task(self):
        """Test du traitement d'une tâche inconnue."""
        result = self.agent.process_task("task1", "Tâche inconnue", self.state_manager)
        self.assertEqual(result["status"], "error")
        # TODO: Vérifier l'état de self.state_manager pour confirmer qu'une réponse d'erreur a été enregistrée.
        # Par exemple, si OrchestrationServiceManager stocke les réponses par task_id:
        # task_info = self.state_manager.get_task_info("task1") # Méthode hypothétique
        # self.assertEqual(task_info.status, "error")
        # self.assertIn("Tâche inconnue non gérée", task_info.messages[-1])

    async def test_handle_translation_task(self):
        """Test du traitement d'une tâche de traduction."""
        task_description = "Traduire le texte en Belief Set: Ceci est un texte pour la traduction."
        
        # Assurer que le state_manager a le raw_text si l'agent en dépend avant process_task
        if hasattr(self.state_manager.state, 'raw_text'):
            self.state_manager.state.raw_text = "Ceci est un texte pour la traduction."
        
        result = self.agent.process_task("task_translation", task_description, self.state_manager)
        self.assertEqual(result["status"], "success")
        
        # TODO: Vérifier l'état de self.state_manager.
        # Par exemple, si les belief sets sont stockés dans self.state_manager.state.service_states['belief_sets']
        # ou via une méthode self.state_manager.get_all_belief_sets()
        # created_belief_set = self.state_manager.get_belief_set_by_task_id("task_translation") # Méthode hypothétique
        # self.assertIsNotNone(created_belief_set)
        # task_info = self.state_manager.get_task_info("task_translation")
        # self.assertEqual(task_info.status, "success")

    async def test_handle_query_task(self):
        """Test du traitement d'une tâche d'exécution de requêtes."""
        # Pré-condition: un belief set 'bs1' doit exister ou être créable par l'agent.
        # On met le raw_text dans le state_manager, et les données pour 'bs1'
        # pour que _extract_belief_set puisse potentiellement le trouver et le créer.
        if hasattr(self.state_manager.state, 'raw_text'):
            self.state_manager.state.raw_text = "Texte de requête pour bs1."
        if hasattr(self.state_manager.state, 'belief_sets'):
            self.state_manager.state.belief_sets['bs1'] = {"logic_type": "propositional", "content": "a => b"}
        
        # S'assurer que MockLogicAgent peut créer un mock BeliefSet à partir de ces données
        mock_bs_instance = MagicMock(spec=BeliefSet)
        self.agent._create_belief_set_from_data = lambda data_dict: mock_bs_instance

        result = self.agent.process_task(
            "task_query",
            "Exécuter les Requêtes sur belief_set_id: bs1",
            self.state_manager
        )
        self.assertEqual(result["status"], "success")

        # TODO: Vérifier l'état de self.state_manager.
        # Par exemple, vérifier les logs de requête ou les résultats associés à "task_query" / "bs1".
        # query_logs = self.state_manager.get_query_logs("task_query", "bs1") # Méthode hypothétique
        # self.assertTrue(len(query_logs) > 0)
        # task_info = self.state_manager.get_task_info("task_query")
        # self.assertEqual(task_info.status, "success")

    async def test_extract_source_text_from_state(self): # Devient async car utilise self.initial_snapshot_data potentiellement lié à asyncSetUp
        """Test de l'extraction du texte source depuis l'état."""
        text = self.agent._extract_source_text("", self.initial_snapshot_data)
        self.assertEqual(text, "Texte de test")
    
    def test_extract_source_text_from_description(self):
        """Test de l'extraction du texte source depuis la description."""
        text = self.agent._extract_source_text(
            "Analyser le texte: Ceci est un test", 
            {"raw_text": ""}
        )
        self.assertEqual(text, "Ceci est un test")
    
    def test_extract_belief_set_id(self):
        """Test de l'extraction de l'ID de l'ensemble de croyances."""
        bs_id = self.agent._extract_belief_set_id("Requête sur belief_set_id: bs123")
        self.assertEqual(bs_id, "bs123")
    
    def test_extract_belief_set_id_not_found(self):
        """Test de l'extraction de l'ID de l'ensemble de croyances non trouvé."""
        bs_id = self.agent._extract_belief_set_id("Requête sans ID")
        self.assertIsNone(bs_id)


if __name__ == "__main__":
    unittest.main()