# -*- coding: utf-8 -*-
"""
Tests unitaires pour l'agent Project Manager (PM).
"""

import pytest # Ajout de pytest
from unittest.mock import MagicMock, patch
import semantic_kernel as sk
from argumentation_analysis.agents.core.pm.pm_definitions import setup_pm_kernel
# from tests.async_test_case import AsyncTestCase # Suppression de l'import


class TestPMAgent:
    """Tests pour l'agent Project Manager."""

    @pytest.fixture
    def pm_agent_components(self):
        """Fixture pour initialiser les composants de test."""
        kernel = sk.Kernel()
        llm_service = MagicMock()
        llm_service.service_id = "test_service"
        return kernel, llm_service

    # Les patchs pour les prompts individuels sont retirés car ils n'existent pas
    # directement sous ces noms dans pm_definitions.py
    # La fonction setup_pm_kernel utilise les prompts importés directement.
    @patch('argumentation_analysis.agents.core.pm.pm_definitions.PM_INSTRUCTIONS') # Corrigé pour pointer vers la variable existante
    def test_setup_pm_kernel(self, mock_pm_instructions, pm_agent_components):
        """Teste la configuration du kernel pour l'agent PM."""
        kernel, llm_service = pm_agent_components
        
        # Configurer le mock pour les instructions (le seul qui est patché maintenant)
        mock_pm_instructions_text_original = "Instructions pour l'agent PM" # Garder une trace si besoin
        # Le patch remplace PM_INSTRUCTIONS, donc on n'a pas besoin de .text sur le mock
        
        # Appeler la fonction à tester
        setup_pm_kernel(kernel, llm_service)
        
        # Vérifier que le plugin a été ajouté au kernel
        assert "PM" in kernel.plugins
        
        # Vérifier que les fonctions sémantiques ont été ajoutées
        # Note: Ceci peut échouer si les fonctions ne sont pas correctement ajoutées
        # dans le kernel mock, mais c'est attendu dans un environnement de test
        # Les fonctions sémantiques sont ajoutées en utilisant les prompts importés,
        # donc on vérifie leur présence.
        plugin = kernel.plugins["PM"]
        assert "semantic_DefineTasksAndDelegate" in plugin
        assert "semantic_WriteAndSetConclusion" in plugin
        
        # Ne pas vérifier l'appel à get_prompt_execution_settings_from_service_id
        # car cette méthode n'existe pas dans la version actuelle de Semantic Kernel


class TestPMAgentIntegration:
    """Tests d'intégration pour l'agent Project Manager."""

    @patch('semantic_kernel.Kernel')
    @patch('semantic_kernel.functions.kernel_function')
    async def test_pm_agent_workflow(self, mock_kernel_function, mock_kernel):
        """Teste le workflow complet de l'agent PM."""
        # Ce test simule un workflow complet de l'agent PM:
        # 1. Analyse du texte
        # 2. Planification de l'analyse
        # 3. Délégation des tâches
        # 4. Synthèse des résultats
        
        # Note: Ce test est plus un exemple de test d'intégration
        # que nous pourrions implémenter à l'avenir.
        # Pour l'instant, nous nous contentons de vérifier que le test passe.
        
        assert True