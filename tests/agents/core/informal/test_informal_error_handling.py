#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour la gestion des erreurs des agents informels.
"""

import unittest # Ajouté
import pytest 
from unittest.mock import MagicMock, patch
import json # Ajouté pour les mocks de retour SK
from semantic_kernel.exceptions import FunctionNotFoundError # Pour simuler des erreurs SK

# La configuration du logging et les imports conditionnels de numpy/pandas
# sont maintenant gérés globalement dans tests/conftest.py

# Import des fixtures (certaines seront appelées dans setUp)
from .fixtures import (
    mock_fallacy_detector, # Utilisé conceptuellement
    mock_rhetorical_analyzer, # Utilisé conceptuellement
    mock_contextual_analyzer, # Utilisé conceptuellement
    informal_agent_instance, # Non utilisé directement si on a setUp
    sample_test_text, # Peut être utilisé
    mock_semantic_kernel_instance # Pour setUp
)

# Import du module à tester
from argumentation_analysis.agents.core.informal.informal_agent import InformalAnalysisAgent as InformalAgent
from argumentation_analysis.agents.core.informal.informal_agent import InformalAnalysisPlugin # Pour spec dans patch


class TestInformalErrorHandling(unittest.TestCase): # Héritage de unittest.TestCase
    """Tests unitaires pour la gestion des erreurs des agents informels."""

    def setUp(self):
        """Initialisation avant chaque test."""
        self.mock_sk_kernel = mock_semantic_kernel_instance() 
        self.agent_name = "test_error_handling_agent"

        self.plugin_patcher = patch('argumentation_analysis.agents.core.informal.informal_agent.InformalAnalysisPlugin')
        mock_plugin_class = self.plugin_patcher.start()
        self.mock_informal_plugin_instance = MagicMock(spec=InformalAnalysisPlugin)
        mock_plugin_class.return_value = self.mock_informal_plugin_instance

        self.agent = InformalAgent(kernel=self.mock_sk_kernel, agent_name=self.agent_name)
        # Ne pas appeler setup_agent_components ici pour certains tests d'init, ou le faire sélectivement.
        # Pour les tests qui supposent un agent fonctionnel, on l'appellera.
        # Pour l'instant, on le laisse commenté et on l'appelle dans les tests si besoin.
        # self.agent.setup_agent_components(llm_service_id="test_llm_service_errors")
        self.agent.mocked_informal_plugin = self.mock_informal_plugin_instance
        self.sample_text = sample_test_text()

    def tearDown(self):
        self.plugin_patcher.stop()

    def _ensure_agent_setup(self):
        # Méthode utilitaire pour s'assurer que setup_agent_components est appelé
        # si ce n'est pas déjà fait ou si on veut forcer une configuration spécifique.
        # Pour la plupart des tests ici, on suppose que l'agent est déjà configuré
        # ou que le test se concentre sur un état avant/pendant la configuration.
        if not hasattr(self.agent, '_llm_service_id') or not self.agent._llm_service_id:
             self.agent.setup_agent_components(llm_service_id="test_llm_service_errors")


    def test_handle_empty_text(self):
        """Teste la gestion d'un texte vide."""
        self._ensure_agent_setup()
        agent = self.agent
        
        # Mocker la méthode analyze_text pour simuler le comportement attendu
        # car la logique interne de l'agent pour texte vide est ce qu'on teste.
        # La vraie méthode devrait retourner cela.
        # Pour ce test, on va supposer que la méthode existe et fait la bonne chose.
        # Si elle n'existe pas, le test échouera à l'appel.
        
        # On ne mocke pas agent.analyze_text ici, on teste son comportement réel.
        # On s'attend à ce que l'agent lui-même gère le texte vide.

        result = agent.analyze_text("")
        
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Le texte est vide")
        self.assertIn("fallacies", result) # La clé "fallacies" doit être présente
        self.assertEqual(result["fallacies"], [])
        # Vérifier que le kernel n'a pas été appelé inutilement
        self.agent.mocked_informal_plugin.analyze_fallacies_sk_function.assert_not_called()


    def test_handle_none_text(self):
        """Teste la gestion d'un texte None."""
        self._ensure_agent_setup()
        agent = self.agent
        result = agent.analyze_text(None)
        
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Le texte est vide")
        self.assertIn("fallacies", result)
        self.assertEqual(result["fallacies"], [])
        self.agent.mocked_informal_plugin.analyze_fallacies_sk_function.assert_not_called()
    
    def test_handle_fallacy_detector_exception(self):
        """Teste la gestion d'une exception du détecteur de sophismes (fonction SK)."""
        self._ensure_agent_setup()
        agent = self.agent
        text_to_analyze = self.sample_text
        
        # Simuler une erreur lors de l'appel à la fonction sémantique des sophismes
        self.agent.mocked_informal_plugin.analyze_fallacies_sk_function = MagicMock(
            side_effect=Exception("Erreur SK du détecteur de sophismes")
        )
        
        result = agent.analyze_text(text_to_analyze)
        
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        # Le message d'erreur exact dépendra de la gestion dans agent.analyze_text
        self.assertIn("Erreur lors de l'analyse du texte", result["error"]) 
        self.assertIn("Erreur SK du détecteur de sophismes", result["error"])
        self.assertIn("fallacies", result)
        self.assertEqual(result["fallacies"], [])

    # ... (Adapter les autres tests de manière similaire) ...

    def test_handle_missing_required_tool(self):
        """
        Teste la gestion d'un "outil" requis manquant (fonction sémantique essentielle).
        Par exemple, si le plugin ne peut pas charger la fonction d'analyse des sophismes.
        """
        agent_no_setup = InformalAnalysisAgent(kernel=self.mock_sk_kernel, agent_name="test_missing_func")
        
        # Simuler que le plugin ne peut pas enregistrer une fonction essentielle
        # ou que setup_agent_components échoue à cause de cela.
        # Ici, on va mocker add_function pour lever une exception si une fonction clé est manquante.
        
        def mock_add_function_side_effect(plugin_name, function_name, prompt, prompt_execution_settings):
            if function_name == "analyze_fallacies": # Supposons que c'est une fonction clé
                raise ValueError(f"Fonction sémantique essentielle '{function_name}' manquante pour le plugin '{plugin_name}'.")
            return MagicMock() # Pour les autres fonctions

        self.mock_sk_kernel.add_function = MagicMock(side_effect=mock_add_function_side_effect)

        with self.assertRaises(ValueError) as context:
            agent_no_setup.setup_agent_components(llm_service_id="test_llm")
        
        self.assertIn("Fonction sémantique essentielle 'analyze_fallacies' manquante", str(context.exception))

# Les autres tests de ce fichier nécessitent une adaptation similaire.
# if __name__ == "__main__":
#     unittest.main()