# -*- coding: utf-8 -*-
# tests/integration/test_logic_api_integration.py
"""
Tests d'intégration pour l'API Web avec les agents logiques.
"""

import os
import sys

# Ajouter le répertoire racine du projet au PYTHONPATH
# Cela permet aux tests d'importer les modules du projet correctement
# Assurons-nous que le répertoire racine est bien celui attendu
# project_root devrait être 'd:/Dev/2025-Epita-Intelligence-Symbolique'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
import unittest
import json
from unittest.mock import MagicMock, patch
import uuid

from semantic_kernel import Kernel

from argumentation_analysis.agents.core.logic.logic_factory import LogicAgentFactory
from argumentation_analysis.agents.core.logic.propositional_logic_agent import PropositionalLogicAgent
from argumentation_analysis.agents.core.logic.first_order_logic_agent import FirstOrderLogicAgent
from argumentation_analysis.agents.core.logic.modal_logic_agent import ModalLogicAgent
from argumentation_analysis.agents.core.logic.belief_set import (
    PropositionalBeliefSet, FirstOrderBeliefSet, ModalBeliefSet
)

from libs.web_api.app import app
from argumentation_analysis.services.web_api.services.logic_service import LogicService
from argumentation_analysis.services.web_api.models.request_models import (
    LogicBeliefSetRequest, LogicQueryRequest, LogicGenerateQueriesRequest
)
from argumentation_analysis.services.web_api.models.response_models import (
    LogicBeliefSetResponse, LogicQueryResponse, LogicGenerateQueriesResponse
)


class TestLogicApiIntegration(unittest.TestCase):
    """Tests d'intégration pour l'API Web avec les agents logiques."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        # Configurer l'application Flask pour les tests
        app.config['TESTING'] = True
        self.client = app.test_client()
        
        # Patcher LogicService
        self.logic_service_patcher = patch('libs.web_api.app.logic_service')
        self.mock_logic_service = self.logic_service_patcher.start()
        
        # Patcher LogicAgentFactory
        self.logic_factory_patcher = patch('libs.web_api.services.logic_service.LogicAgentFactory')
        self.mock_logic_factory = self.logic_factory_patcher.start()
        
        # Patcher Kernel
        self.kernel_patcher = patch('libs.web_api.services.logic_service.Kernel')
        self.mock_kernel_class = self.kernel_patcher.start()
        self.mock_kernel = MagicMock(spec=Kernel)
        self.mock_kernel_class.return_value = self.mock_kernel
        
        # Configurer les mocks des agents
        self.mock_pl_agent = MagicMock(spec=PropositionalLogicAgent)
        self.mock_fol_agent = MagicMock(spec=FirstOrderLogicAgent)
        self.mock_modal_agent = MagicMock(spec=ModalLogicAgent)
        
        # Configurer le mock de LogicAgentFactory
        self.mock_logic_factory.create_agent.side_effect = lambda logic_type, kernel: {
            "propositional": self.mock_pl_agent,
            "first_order": self.mock_fol_agent,
            "modal": self.mock_modal_agent
        }.get(logic_type)
        
        # Configurer les mocks des méthodes des agents
        self.mock_pl_agent.text_to_belief_set.return_value = (PropositionalBeliefSet("a => b"), "Conversion réussie")
        self.mock_pl_agent.generate_queries.return_value = ["a", "b", "a => b"]
        self.mock_pl_agent.execute_query.return_value = (True, "Tweety Result: Query 'a => b' is ACCEPTED (True).")
        self.mock_pl_agent.interpret_results.return_value = "Interprétation des résultats PL"
        
        self.mock_fol_agent.text_to_belief_set.return_value = (FirstOrderBeliefSet("forall X: (P(X) => Q(X))"), "Conversion réussie")
        self.mock_fol_agent.generate_queries.return_value = ["P(a)", "Q(b)", "forall X: (P(X) => Q(X))"]
        self.mock_fol_agent.execute_query.return_value = (True, "Tweety Result: FOL Query 'forall X: (P(X) => Q(X))' is ACCEPTED (True).")
        self.mock_fol_agent.interpret_results.return_value = "Interprétation des résultats FOL"
        
        self.mock_modal_agent.text_to_belief_set.return_value = (ModalBeliefSet("[]p => <>q"), "Conversion réussie")
        self.mock_modal_agent.generate_queries.return_value = ["p", "[]p", "<>q"]
        self.mock_modal_agent.execute_query.return_value = (True, "Tweety Result: Modal Query '[]p => <>q' is ACCEPTED (True).")
        self.mock_modal_agent.interpret_results.return_value = "Interprétation des résultats modaux"
        
        # Configurer le mock de LogicService
        self.mock_belief_set_id = str(uuid.uuid4())
        
        # Mock pour text_to_belief_set
        self.mock_logic_service.text_to_belief_set.return_value = LogicBeliefSetResponse(
            success=True,
            belief_set={
                "id": self.mock_belief_set_id,
                "logic_type": "propositional",
                "content": "a => b",
                "source_text": "Si a alors b"
            },
            processing_time=0.1
        )
        
        # Mock pour execute_query
        self.mock_logic_service.execute_query.return_value = LogicQueryResponse(
            success=True,
            belief_set_id=self.mock_belief_set_id,
            logic_type="propositional",
            result={
                "query": "a => b",
                "result": True,
                "formatted_result": "Tweety Result: Query 'a => b' is ACCEPTED (True).",
                "explanation": "La requête 'a => b' est acceptée par l'ensemble de croyances."
            },
            processing_time=0.1
        )
        
        # Mock pour generate_queries
        self.mock_logic_service.generate_queries.return_value = LogicGenerateQueriesResponse(
            success=True,
            belief_set_id=self.mock_belief_set_id,
            logic_type="propositional",
            queries=["a", "b", "a => b"],
            processing_time=0.1
        )
        
        # Mock pour is_healthy
        self.mock_logic_service.is_healthy.return_value = True
    
    def tearDown(self):
        """Nettoyage après chaque test."""
        self.logic_service_patcher.stop()
        self.logic_factory_patcher.stop()
        self.kernel_patcher.stop()
    
    def test_health_check(self):
        """Test du endpoint /api/health."""
        response = self.client.get('/api/health')
        
        # Vérifier le code de statut
        self.assertEqual(response.status_code, 200)
        
        # Vérifier le contenu de la réponse
        data = json.loads(response.data)
        self.assertEqual(data["status"], "healthy")
        self.assertTrue(data["services"]["logic"])
    
    def test_create_belief_set(self):
        """Test du endpoint /api/logic/belief-set."""
        # Préparer les données de la requête
        request_data = {
            "text": "Si a alors b",
            "logic_type": "propositional",
            "options": {
                "include_explanation": True,
                "max_queries": 5
            }
        }
        
        # Envoyer la requête
        response = self.client.post(
            '/api/logic/belief-set',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        # Vérifier le code de statut
        self.assertEqual(response.status_code, 200)
        
        # Vérifier que le service a été appelé
        self.mock_logic_service.text_to_belief_set.assert_called_once()
        
        # Vérifier le contenu de la réponse
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["belief_set"]["id"], self.mock_belief_set_id)
        self.assertEqual(data["belief_set"]["logic_type"], "propositional")
        self.assertEqual(data["belief_set"]["content"], "a => b")
    
    def test_execute_query(self):
        """Test du endpoint /api/logic/query."""
        # Préparer les données de la requête
        request_data = {
            "belief_set_id": self.mock_belief_set_id,
            "query": "a => b",
            "logic_type": "propositional",
            "options": {
                "include_explanation": True
            }
        }
        
        # Envoyer la requête
        response = self.client.post(
            '/api/logic/query',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        # Vérifier le code de statut
        self.assertEqual(response.status_code, 200)
        
        # Vérifier que le service a été appelé
        self.mock_logic_service.execute_query.assert_called_once()
        
        # Vérifier le contenu de la réponse
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["belief_set_id"], self.mock_belief_set_id)
        self.assertEqual(data["logic_type"], "propositional")
        self.assertTrue(data["result"]["result"])
        self.assertEqual(data["result"]["query"], "a => b")
    
    def test_generate_queries(self):
        """Test du endpoint /api/logic/generate-queries."""
        # Préparer les données de la requête
        request_data = {
            "belief_set_id": self.mock_belief_set_id,
            "text": "Si a alors b",
            "logic_type": "propositional",
            "options": {
                "max_queries": 5
            }
        }
        
        # Envoyer la requête
        response = self.client.post(
            '/api/logic/generate-queries',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        # Vérifier le code de statut
        self.assertEqual(response.status_code, 200)
        
        # Vérifier que le service a été appelé
        self.mock_logic_service.generate_queries.assert_called_once()
        
        # Vérifier le contenu de la réponse
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["belief_set_id"], self.mock_belief_set_id)
        self.assertEqual(data["logic_type"], "propositional")
        self.assertEqual(data["queries"], ["a", "b", "a => b"])
    
    def test_invalid_request_format(self):
        """Test de la validation des requêtes."""
        # Préparer les données de la requête (manque le champ logic_type)
        request_data = {
            "text": "Si a alors b"
        }
        
        # Envoyer la requête
        response = self.client.post(
            '/api/logic/belief-set',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        # Vérifier le code de statut
        self.assertEqual(response.status_code, 400)
        
        # Vérifier le contenu de la réponse
        data = json.loads(response.data)
        self.assertEqual(data["error"], "Données invalides")
    
    def test_service_error(self):
        """Test de la gestion des erreurs du service."""
        # Configurer le mock pour lever une exception
        self.mock_logic_service.text_to_belief_set.side_effect = ValueError("Erreur de test")
        
        # Préparer les données de la requête
        request_data = {
            "text": "Si a alors b",
            "logic_type": "propositional"
        }
        
        # Envoyer la requête
        response = self.client.post(
            '/api/logic/belief-set',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        # Vérifier le code de statut
        self.assertEqual(response.status_code, 500)
        
        # Vérifier le contenu de la réponse
        data = json.loads(response.data)
        self.assertEqual(data["error"], "Erreur de conversion")
        self.assertEqual(data["message"], "Erreur de test")


class TestLogicServiceIntegration(unittest.TestCase):
    """Tests d'intégration pour le service LogicService."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        # Patcher LogicAgentFactory
        self.logic_factory_patcher = patch('libs.web_api.services.logic_service.LogicAgentFactory')
        self.mock_logic_factory = self.logic_factory_patcher.start()
        
        # Patcher Kernel
        self.kernel_patcher = patch('libs.web_api.services.logic_service.Kernel')
        self.mock_kernel_class = self.kernel_patcher.start()
        self.mock_kernel = MagicMock(spec=Kernel)
        self.mock_kernel_class.return_value = self.mock_kernel
        
        # Configurer les mocks des agents
        self.mock_pl_agent = MagicMock(spec=PropositionalLogicAgent)
        self.mock_fol_agent = MagicMock(spec=FirstOrderLogicAgent)
        self.mock_modal_agent = MagicMock(spec=ModalLogicAgent)
        
        # Configurer le mock de LogicAgentFactory
        self.mock_logic_factory.create_agent.side_effect = lambda logic_type, kernel: {
            "propositional": self.mock_pl_agent,
            "first_order": self.mock_fol_agent,
            "modal": self.mock_modal_agent
        }.get(logic_type)
        
        # Configurer les mocks des méthodes des agents
        self.mock_pl_agent.text_to_belief_set.return_value = (PropositionalBeliefSet("a => b"), "Conversion réussie")
        self.mock_pl_agent.generate_queries.return_value = ["a", "b", "a => b"]
        self.mock_pl_agent.execute_query.return_value = (True, "Tweety Result: Query 'a => b' is ACCEPTED (True).")
        self.mock_pl_agent.interpret_results.return_value = "Interprétation des résultats PL"
        
        # Créer le service
        self.logic_service = LogicService()
    
    def tearDown(self):
        """Nettoyage après chaque test."""
        self.logic_factory_patcher.stop()
        self.kernel_patcher.stop()
    
    def test_text_to_belief_set(self):
        """Test de la méthode text_to_belief_set."""
        # Créer la requête
        request = LogicBeliefSetRequest(
            text="Si a alors b",
            logic_type="propositional"
        )
        
        # Appeler la méthode
        response = self.logic_service.text_to_belief_set(request)
        
        # Vérifier que l'agent a été créé
        self.mock_logic_factory.create_agent.assert_called_once_with("propositional", self.mock_kernel)
        
        # Vérifier que la méthode de l'agent a été appelée
        self.mock_pl_agent.text_to_belief_set.assert_called_once_with("Si a alors b")
        
        # Vérifier la réponse
        self.assertTrue(response.success)
        self.assertEqual(response.belief_set.logic_type, "propositional")
        self.assertEqual(response.belief_set.content, "a => b")
        self.assertEqual(response.belief_set.source_text, "Si a alors b")
    
    def test_execute_query(self):
        """Test de la méthode execute_query."""
        # Créer un ensemble de croyances
        belief_set_request = LogicBeliefSetRequest(
            text="Si a alors b",
            logic_type="propositional"
        )
        belief_set_response = self.logic_service.text_to_belief_set(belief_set_request)
        belief_set_id = belief_set_response.belief_set.id
        
        # Créer la requête
        request = LogicQueryRequest(
            belief_set_id=belief_set_id,
            query="a => b",
            logic_type="propositional"
        )
        
        # Appeler la méthode
        response = self.logic_service.execute_query(request)
        
        # Vérifier que l'agent a été créé
        self.assertEqual(self.mock_logic_factory.create_agent.call_count, 2)
        
        # Vérifier que la méthode de l'agent a été appelée
        self.mock_pl_agent.execute_query.assert_called_once()
        
        # Vérifier la réponse
        self.assertTrue(response.success)
        self.assertEqual(response.belief_set_id, belief_set_id)
        self.assertEqual(response.logic_type, "propositional")
        self.assertEqual(response.result.query, "a => b")
        self.assertTrue(response.result.result)
    
    def test_generate_queries(self):
        """Test de la méthode generate_queries."""
        # Créer un ensemble de croyances
        belief_set_request = LogicBeliefSetRequest(
            text="Si a alors b",
            logic_type="propositional"
        )
        belief_set_response = self.logic_service.text_to_belief_set(belief_set_request)
        belief_set_id = belief_set_response.belief_set.id
        
        # Créer la requête
        request = LogicGenerateQueriesRequest(
            belief_set_id=belief_set_id,
            text="Si a alors b",
            logic_type="propositional"
        )
        
        # Appeler la méthode
        response = self.logic_service.generate_queries(request)
        
        # Vérifier que l'agent a été créé
        self.assertEqual(self.mock_logic_factory.create_agent.call_count, 2)
        
        # Vérifier que la méthode de l'agent a été appelée
        self.mock_pl_agent.generate_queries.assert_called_once()
        
        # Vérifier la réponse
        self.assertTrue(response.success)
        self.assertEqual(response.belief_set_id, belief_set_id)
        self.assertEqual(response.logic_type, "propositional")
        self.assertEqual(response.queries, ["a", "b", "a => b"])


if __name__ == "__main__":
    unittest.main()