# -*- coding: utf-8 -*-
# tests/agents/core/logic/test_logic_factory.py
"""
Tests unitaires pour la classe LogicAgentFactory.
"""

import unittest
from unittest.mock import MagicMock, patch

from semantic_kernel import Kernel

from argumentation_analysis.agents.core.logic.logic_factory import LogicAgentFactory
from argumentation_analysis.agents.core.logic.abstract_logic_agent import AbstractLogicAgent
from argumentation_analysis.agents.core.logic.propositional_logic_agent import PropositionalLogicAgent
from argumentation_analysis.agents.core.logic.first_order_logic_agent import FirstOrderLogicAgent
from argumentation_analysis.agents.core.logic.modal_logic_agent import ModalLogicAgent


class TestLogicAgentFactory(unittest.TestCase):
    """Tests pour la classe LogicAgentFactory."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        # Mock du kernel
        self.kernel = MagicMock(spec=Kernel)
        
        # Mock du kernel
        self.kernel = MagicMock(spec=Kernel)

        # Mocks pour les classes d'agents et leurs instances
        self.mock_propositional_agent = MagicMock(spec=PropositionalLogicAgent)
        self.mock_first_order_agent = MagicMock(spec=FirstOrderLogicAgent)
        self.mock_modal_agent = MagicMock(spec=ModalLogicAgent)

        self.mock_propositional_agent_class = MagicMock(spec=PropositionalLogicAgent, return_value=self.mock_propositional_agent)
        self.mock_first_order_agent_class = MagicMock(spec=FirstOrderLogicAgent, return_value=self.mock_first_order_agent)
        self.mock_modal_agent_class = MagicMock(spec=ModalLogicAgent, return_value=self.mock_modal_agent)

        # Patcher le dictionnaire _agent_classes de la factory
        # Conserver une copie de l'original pour la restauration si nécessaire, bien que patch.dict gère cela.
        # self.original_agent_classes = LogicAgentFactory._agent_classes.copy()

        self.agent_classes_patcher = patch.dict(LogicAgentFactory._agent_classes, {
            "propositional": self.mock_propositional_agent_class,
            "first_order": self.mock_first_order_agent_class,
            "modal": self.mock_modal_agent_class
        }, clear=False) # clear=False pour ne pas affecter d'autres types potentiellement enregistrés
        
        self.agent_classes_patcher.start()
        self.addCleanup(self.agent_classes_patcher.stop)

    def tearDown(self):
        """Nettoyage après chaque test."""
        # addCleanup s'occupe de self.agent_classes_patcher.stop()
        pass
    
    def test_create_propositional_agent(self):
        """Test de la création d'un agent de logique propositionnelle."""
        agent = LogicAgentFactory.create_agent("propositional", self.kernel)
        
        # Vérifier que la classe d'agent a été appelée
        self.mock_propositional_agent_class.assert_called_once_with(self.kernel)
        
        # Vérifier que l'agent a été configuré
        self.mock_propositional_agent.setup_kernel.assert_not_called()
        
        # Vérifier le résultat
        self.assertEqual(agent, self.mock_propositional_agent)
    
    def test_create_first_order_agent(self):
        """Test de la création d'un agent de logique du premier ordre."""
        agent = LogicAgentFactory.create_agent("first_order", self.kernel)
        
        # Vérifier que la classe d'agent a été appelée
        self.mock_first_order_agent_class.assert_called_once_with(self.kernel)
        
        # Vérifier que l'agent a été configuré
        self.mock_first_order_agent.setup_kernel.assert_not_called()
        
        # Vérifier le résultat
        self.assertEqual(agent, self.mock_first_order_agent)
    
    def test_create_modal_agent(self):
        """Test de la création d'un agent de logique modale."""
        agent = LogicAgentFactory.create_agent("modal", self.kernel)
        
        # Vérifier que la classe d'agent a été appelée
        self.mock_modal_agent_class.assert_called_once_with(self.kernel)
        
        # Vérifier que l'agent a été configuré
        self.mock_modal_agent.setup_kernel.assert_not_called()
        
        # Vérifier le résultat
        self.assertEqual(agent, self.mock_modal_agent)
    
    def test_create_agent_with_llm_service(self):
        """Test de la création d'un agent avec un service LLM."""
        llm_service = MagicMock()
        
        agent = LogicAgentFactory.create_agent("propositional", self.kernel, llm_service)
        
        # Vérifier que la classe d'agent a été appelée
        self.mock_propositional_agent_class.assert_called_once_with(self.kernel)
        
        # Vérifier que l'agent a été configuré
        self.mock_propositional_agent.setup_kernel.assert_called_once_with(llm_service)
        
        # Vérifier le résultat
        self.assertEqual(agent, self.mock_propositional_agent)
    
    def test_create_agent_unsupported_type(self):
        """Test de la création d'un agent avec un type non supporté."""
        agent = LogicAgentFactory.create_agent("unsupported", self.kernel)
        
        # Vérifier que les classes d'agents n'ont pas été appelées
        self.mock_propositional_agent_class.assert_not_called()
        self.mock_first_order_agent_class.assert_not_called()
        self.mock_modal_agent_class.assert_not_called()
        
        # Vérifier le résultat
        self.assertIsNone(agent)
    
    def test_create_agent_exception(self):
        """Test de la création d'un agent avec une exception."""
        # Configurer le mock pour lever une exception
        self.mock_propositional_agent_class.side_effect = Exception("Test exception")
        
        agent = LogicAgentFactory.create_agent("propositional", self.kernel)
        
        # Vérifier que la classe d'agent a été appelée
        self.mock_propositional_agent_class.assert_called_once_with(self.kernel)
        
        # Vérifier le résultat
        self.assertIsNone(agent)
    
    def test_register_agent_class(self):
        """Test de l'enregistrement d'une nouvelle classe d'agent."""
        # Créer une classe d'agent de test (sa définition réelle n'importe pas tant pour le mock)
        class TestLogicAgent(AbstractLogicAgent):
            def setup_kernel(self, llm_service): pass
            def text_to_belief_set(self, text): pass
            def generate_queries(self, text, belief_set): pass
            def execute_query(self, belief_set, query): pass
            def interpret_results(self, text, belief_set, queries, results): pass
            def _create_belief_set_from_data(self, belief_set_data): pass

        test_logic_type = f"test_agent_type_{id(self)}"

        # Mock pour simuler le constructeur de TestLogicAgent et l'instance retournée
        mock_test_agent_instance = MagicMock(spec=TestLogicAgent)
        # Ce mock représente la classe TestLogicAgent elle-même (son constructeur)
        mock_test_agent_constructor = MagicMock(return_value=mock_test_agent_instance)
        mock_test_agent_constructor.__name__ = "MockedTestLogicAgent" # Pour satisfaire le logger dans register_agent_class

        # Enregistrer notre mock constructeur au lieu de la vraie classe TestLogicAgent
        LogicAgentFactory.register_agent_class(test_logic_type, mock_test_agent_constructor)
        # S'assurer que cette clé de test est retirée après le test pour ne pas polluer les autres tests
        self.addCleanup(LogicAgentFactory._agent_classes.pop, test_logic_type, None)
        
        # Vérifier que la classe a été enregistrée
        self.assertIn(test_logic_type, LogicAgentFactory.get_supported_logic_types())
        
        # Créer un agent avec le nouveau type
        agent = LogicAgentFactory.create_agent(test_logic_type, self.kernel)
        
        # Vérifier que notre mock constructeur (qui simule la classe) a été appelé
        mock_test_agent_constructor.assert_called_once_with(self.kernel)
        
        # Vérifier le résultat
        self.assertEqual(agent, mock_test_agent_instance)
    
    def test_get_supported_logic_types(self):
        """Test de la récupération des types de logique supportés."""
        types = LogicAgentFactory.get_supported_logic_types()
        
        # Vérifier que les types de base sont présents
        self.assertIn("propositional", types)
        self.assertIn("first_order", types)
        self.assertIn("modal", types)


if __name__ == "__main__":
    unittest.main()