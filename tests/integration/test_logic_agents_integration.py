# -*- coding: utf-8 -*-
# tests/integration/test_logic_agents_integration.py
"""
Tests d'intégration pour les agents logiques.
"""

import unittest
from unittest.mock import MagicMock, patch

from semantic_kernel import Kernel

from argumentation_analysis.agents.core.logic.first_order_logic_agent_adapter import LogicAgentFactory
from argumentation_analysis.agents.core.logic.belief_set import (
    PropositionalBeliefSet, FirstOrderBeliefSet, ModalBeliefSet
)


class TestLogicAgentsIntegration(unittest.TestCase):
    """Tests d'intégration pour les agents logiques."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        # Mock du kernel
        self.kernel = MagicMock(spec=Kernel)
        self.kernel.plugins = {}
        
        # Mock des fonctions du kernel pour la logique propositionnelle
        self.text_to_pl_function = MagicMock()
        self.text_to_pl_function.invoke.return_value = MagicMock(result="a => b")
        
        self.generate_pl_queries_function = MagicMock()
        self.generate_pl_queries_function.invoke.return_value = MagicMock(result="a\nb\na => b")
        
        self.interpret_pl_function = MagicMock()
        self.interpret_pl_function.invoke.return_value = MagicMock(result="Interprétation des résultats PL")
        
        self.execute_pl_query_function = MagicMock()
        self.execute_pl_query_function.invoke.return_value = MagicMock(
            result="Tweety Result: Query 'a => b' is ACCEPTED (True)."
        )
        
        # Mock des fonctions du kernel pour la logique du premier ordre
        self.text_to_fol_function = MagicMock()
        self.text_to_fol_function.invoke.return_value = MagicMock(result="forall X: (P(X) => Q(X))")
        
        self.generate_fol_queries_function = MagicMock()
        self.generate_fol_queries_function.invoke.return_value = MagicMock(result="P(a)\nQ(b)\nforall X: (P(X) => Q(X))")
        
        self.interpret_fol_function = MagicMock()
        self.interpret_fol_function.invoke.return_value = MagicMock(result="Interprétation des résultats FOL")
        
        self.execute_fol_query_function = MagicMock()
        self.execute_fol_query_function.invoke.return_value = MagicMock(
            result="Tweety Result: FOL Query 'forall X: (P(X) => Q(X))' is ACCEPTED (True)."
        )
        
        # Mock des fonctions du kernel pour la logique modale
        self.text_to_modal_function = MagicMock()
        self.text_to_modal_function.invoke.return_value = MagicMock(result="[]p => <>q")
        
        self.generate_modal_queries_function = MagicMock()
        self.generate_modal_queries_function.invoke.return_value = MagicMock(result="p\n[]p\n<>q")
        
        self.interpret_modal_function = MagicMock()
        self.interpret_modal_function.invoke.return_value = MagicMock(result="Interprétation des résultats modaux")
        
        self.execute_modal_query_function = MagicMock()
        self.execute_modal_query_function.invoke.return_value = MagicMock(
            result="Tweety Result: Modal Query '[]p => <>q' is ACCEPTED (True)."
        )
        
        # Configuration du mock du plugin pour la logique propositionnelle
        self.kernel.plugins["PLAnalyzer"] = {
            "semantic_TextToPLBeliefSet": self.text_to_pl_function,
            "semantic_GeneratePLQueries": self.generate_pl_queries_function,
            "semantic_InterpretPLResult": self.interpret_pl_function,
            "execute_pl_query": self.execute_pl_query_function
        }
        
        # Configuration du mock du plugin pour la logique du premier ordre
        self.kernel.plugins["FOLAnalyzer"] = {
            "semantic_TextToFOLBeliefSet": self.text_to_fol_function,
            "semantic_GenerateFOLQueries": self.generate_fol_queries_function,
            "semantic_InterpretFOLResult": self.interpret_fol_function,
            "execute_fol_query": self.execute_fol_query_function
        }
        
        # Configuration du mock du plugin pour la logique modale
        self.kernel.plugins["ModalAnalyzer"] = {
            "semantic_TextToModalBeliefSet": self.text_to_modal_function,
            "semantic_GenerateModalQueries": self.generate_modal_queries_function,
            "semantic_InterpretModalResult": self.interpret_modal_function,
            "execute_modal_query": self.execute_modal_query_function
        }
        
        # Patcher TweetyBridge
        self.tweety_bridge_patcher = patch('argumentation_analysis.agents.core.logic.tweety_bridge.TweetyBridge')
        self.mock_tweety_bridge_class = self.tweety_bridge_patcher.start()
        self.mock_tweety_bridge = MagicMock()
        self.mock_tweety_bridge_class.return_value = self.mock_tweety_bridge
        
        # Configurer le mock de TweetyBridge
        self.mock_tweety_bridge.is_jvm_ready.return_value = True
        self.mock_tweety_bridge.validate_belief_set.return_value = (True, "Ensemble de croyances valide")
        self.mock_tweety_bridge.validate_formula.return_value = (True, "Formule valide")
        self.mock_tweety_bridge.validate_fol_belief_set.return_value = (True, "Ensemble de croyances FOL valide")
        self.mock_tweety_bridge.validate_fol_formula.return_value = (True, "Formule FOL valide")
        self.mock_tweety_bridge.validate_modal_belief_set.return_value = (True, "Ensemble de croyances modal valide")
        self.mock_tweety_bridge.validate_modal_formula.return_value = (True, "Formule modale valide")
    
    def tearDown(self):
        """Nettoyage après chaque test."""
        self.tweety_bridge_patcher.stop()
    
    def test_factory_creates_appropriate_agent(self):
        """Test que la factory crée l'agent approprié en fonction du type de logique."""
        # Créer les agents
        pl_agent = LogicAgentFactory.create_agent("propositional", self.kernel)
        fol_agent = LogicAgentFactory.create_agent("first_order", self.kernel)
        modal_agent = LogicAgentFactory.create_agent("modal", self.kernel)
        
        # Vérifier les types d'agents
        self.assertEqual(pl_agent.name, "PropositionalLogicAgent")
        self.assertEqual(fol_agent.name, "FirstOrderLogicAgent")
        self.assertEqual(modal_agent.name, "ModalLogicAgent")
    
    def test_propositional_to_first_order_integration(self):
        """Test d'intégration entre les agents de logique propositionnelle et du premier ordre."""
        # Créer les agents
        pl_agent = LogicAgentFactory.create_agent("propositional", self.kernel)
        fol_agent = LogicAgentFactory.create_agent("first_order", self.kernel)
        
        # Convertir un texte en ensemble de croyances propositionnelles
        pl_belief_set, _ = pl_agent.text_to_belief_set("Texte de test")
        
        # Vérifier que l'ensemble de croyances a été créé correctement
        self.assertIsInstance(pl_belief_set, PropositionalBeliefSet)
        self.assertEqual(pl_belief_set.content, "a => b")
        
        # Générer des requêtes pour l'ensemble de croyances propositionnelles
        pl_queries = pl_agent.generate_queries("Texte de test", pl_belief_set)
        
        # Vérifier que les requêtes ont été générées correctement
        self.assertEqual(pl_queries, ["a", "b", "a => b"])
        
        # Convertir un texte en ensemble de croyances du premier ordre
        fol_belief_set, _ = fol_agent.text_to_belief_set("Texte de test")
        
        # Vérifier que l'ensemble de croyances a été créé correctement
        self.assertIsInstance(fol_belief_set, FirstOrderBeliefSet)
        self.assertEqual(fol_belief_set.content, "forall X: (P(X) => Q(X))")
        
        # Générer des requêtes pour l'ensemble de croyances du premier ordre
        fol_queries = fol_agent.generate_queries("Texte de test", fol_belief_set)
        
        # Vérifier que les requêtes ont été générées correctement
        self.assertEqual(fol_queries, ["P(a)", "Q(b)", "forall X: (P(X) => Q(X))"])
        
        # Exécuter une requête propositionnelle
        pl_result, pl_message = pl_agent.execute_query(pl_belief_set, "a => b")
        
        # Vérifier le résultat
        self.assertTrue(pl_result)
        self.assertEqual(pl_message, "Tweety Result: Query 'a => b' is ACCEPTED (True).")
        
        # Exécuter une requête du premier ordre
        fol_result, fol_message = fol_agent.execute_query(fol_belief_set, "forall X: (P(X) => Q(X))")
        
        # Vérifier le résultat
        self.assertTrue(fol_result)
        self.assertEqual(fol_message, "Tweety Result: FOL Query 'forall X: (P(X) => Q(X))' is ACCEPTED (True).")
    
    def test_first_order_to_modal_integration(self):
        """Test d'intégration entre les agents de logique du premier ordre et modale."""
        # Créer les agents
        fol_agent = LogicAgentFactory.create_agent("first_order", self.kernel)
        modal_agent = LogicAgentFactory.create_agent("modal", self.kernel)
        
        # Convertir un texte en ensemble de croyances du premier ordre
        fol_belief_set, _ = fol_agent.text_to_belief_set("Texte de test")
        
        # Vérifier que l'ensemble de croyances a été créé correctement
        self.assertIsInstance(fol_belief_set, FirstOrderBeliefSet)
        self.assertEqual(fol_belief_set.content, "forall X: (P(X) => Q(X))")
        
        # Générer des requêtes pour l'ensemble de croyances du premier ordre
        fol_queries = fol_agent.generate_queries("Texte de test", fol_belief_set)
        
        # Vérifier que les requêtes ont été générées correctement
        self.assertEqual(fol_queries, ["P(a)", "Q(b)", "forall X: (P(X) => Q(X))"])
        
        # Convertir un texte en ensemble de croyances modales
        modal_belief_set, _ = modal_agent.text_to_belief_set("Texte de test")
        
        # Vérifier que l'ensemble de croyances a été créé correctement
        self.assertIsInstance(modal_belief_set, ModalBeliefSet)
        self.assertEqual(modal_belief_set.content, "[]p => <>q")
        
        # Générer des requêtes pour l'ensemble de croyances modales
        modal_queries = modal_agent.generate_queries("Texte de test", modal_belief_set)
        
        # Vérifier que les requêtes ont été générées correctement
        self.assertEqual(modal_queries, ["p", "[]p", "<>q"])
        
        # Exécuter une requête du premier ordre
        fol_result, fol_message = fol_agent.execute_query(fol_belief_set, "forall X: (P(X) => Q(X))")
        
        # Vérifier le résultat
        self.assertTrue(fol_result)
        self.assertEqual(fol_message, "Tweety Result: FOL Query 'forall X: (P(X) => Q(X))' is ACCEPTED (True).")
        
        # Exécuter une requête modale
        modal_result, modal_message = modal_agent.execute_query(modal_belief_set, "[]p => <>q")
        
        # Vérifier le résultat
        self.assertTrue(modal_result)
        self.assertEqual(modal_message, "Tweety Result: Modal Query '[]p => <>q' is ACCEPTED (True).")
    
    def test_complete_workflow_integration(self):
        """Test d'intégration du flux de travail complet avec les trois types d'agents."""
        # Créer les agents
        pl_agent = LogicAgentFactory.create_agent("propositional", self.kernel)
        fol_agent = LogicAgentFactory.create_agent("first_order", self.kernel)
        modal_agent = LogicAgentFactory.create_agent("modal", self.kernel)
        
        # Texte source
        text = "Si p est vrai, alors q est vrai. Tous les X qui ont la propriété P ont aussi la propriété Q. Si p est nécessairement vrai, alors q est possiblement vrai."
        
        # Convertir le texte en ensembles de croyances
        pl_belief_set, _ = pl_agent.text_to_belief_set(text)
        fol_belief_set, _ = fol_agent.text_to_belief_set(text)
        modal_belief_set, _ = modal_agent.text_to_belief_set(text)
        
        # Générer des requêtes pour chaque ensemble de croyances
        pl_queries = pl_agent.generate_queries(text, pl_belief_set)
        fol_queries = fol_agent.generate_queries(text, fol_belief_set)
        modal_queries = modal_agent.generate_queries(text, modal_belief_set)
        
        # Exécuter les requêtes
        pl_results = []
        for query in pl_queries:
            result, message = pl_agent.execute_query(pl_belief_set, query)
            pl_results.append(message)
        
        fol_results = []
        for query in fol_queries:
            result, message = fol_agent.execute_query(fol_belief_set, query)
            fol_results.append(message)
        
        modal_results = []
        for query in modal_queries:
            result, message = modal_agent.execute_query(modal_belief_set, query)
            modal_results.append(message)
        
        # Interpréter les résultats
        pl_interpretation = pl_agent.interpret_results(text, pl_belief_set, pl_queries, pl_results)
        fol_interpretation = fol_agent.interpret_results(text, fol_belief_set, fol_queries, fol_results)
        modal_interpretation = modal_agent.interpret_results(text, modal_belief_set, modal_queries, modal_results)
        
        # Vérifier les interprétations
        self.assertEqual(pl_interpretation, "Interprétation des résultats PL")
        self.assertEqual(fol_interpretation, "Interprétation des résultats FOL")
        self.assertEqual(modal_interpretation, "Interprétation des résultats modaux")


if __name__ == "__main__":
    unittest.main()