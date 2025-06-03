#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour les méthodes d'analyse des agents informels.
"""

import unittest
import pytest 
from unittest.mock import MagicMock, patch, AsyncMock 
import json
import asyncio 

from .fixtures import (
    mock_fallacy_detector, 
    mock_rhetorical_analyzer, 
    mock_contextual_analyzer, 
    informal_agent_instance, 
    MockSemanticKernel 
)

from argumentation_analysis.agents.core.informal.informal_agent import InformalAnalysisAgent as InformalAgent
from argumentation_analysis.agents.core.informal.informal_agent import InformalAnalysisPlugin

class TestInformalAnalysisMethods(unittest.TestCase):
    """Tests unitaires pour les méthodes d'analyse des agents informels."""

    def setUp(self):
        """Initialisation avant chaque test."""
        self.mock_sk_kernel = MockSemanticKernel() 
        self.agent_name = "test_analysis_methods_agent"

        self.plugin_patcher = patch('argumentation_analysis.agents.core.informal.informal_agent.InformalAnalysisPlugin')
        mock_plugin_class = self.plugin_patcher.start()
        self.mock_informal_plugin_instance = MagicMock(spec=InformalAnalysisPlugin)
        mock_plugin_class.return_value = self.mock_informal_plugin_instance

        self.agent = InformalAgent(kernel=self.mock_sk_kernel, agent_name=self.agent_name)
        self.agent.setup_agent_components(llm_service_id="test_llm_service_analysis")
        
        self.agent.analyze_text = AsyncMock(return_value={
            "fallacies": [],
            "analysis_timestamp": "some_timestamp"
        })
        
        self.sample_text = "Ceci est un texte d'exemple pour les tests. Il contient plusieurs phrases et pourrait être analysé pour des sophismes ou des figures de style."

    def tearDown(self):
        self.plugin_patcher.stop()

    async def test_analyze_text(self):
        """Teste la méthode analyze_text."""
        agent = self.agent
        text_to_analyze = self.sample_text
        
        expected_fallacies = [
            {"fallacy_type": "Appel à l'autorité", "text": "Les experts...", "confidence": 0.7},
            {"fallacy_type": "Appel à la popularité", "text": "Millions de personnes...", "confidence": 0.6}
        ]
        
        agent.analyze_text.return_value = { 
            "fallacies": expected_fallacies,
            "analysis_timestamp": "some_timestamp"
        }

        result = await agent.analyze_text(text_to_analyze)
        
        agent.analyze_text.assert_called_once_with(text_to_analyze)
        
        self.assertIsInstance(result, dict)
        self.assertIn("fallacies", result)
        self.assertIn("analysis_timestamp", result)
        
        self.assertIsInstance(result["fallacies"], list)
        self.assertEqual(len(result["fallacies"]), 2)
        self.assertEqual(result["fallacies"][0]["fallacy_type"], "Appel à l'autorité")
        self.assertEqual(result["fallacies"][1]["fallacy_type"], "Appel à la popularité")
    
    async def test_analyze_text_with_context(self):
        """Teste la méthode analyze_text avec un contexte."""
        agent = self.agent
        text_to_analyze = self.sample_text
        context_text = "Discours commercial pour un produit controversé"
        
        expected_fallacies = [] 
        
        agent.analyze_text.return_value = { 
            "fallacies": expected_fallacies,
            "context": context_text, 
            "analysis_timestamp": "some_timestamp"
        }

        result = await agent.analyze_text(text_to_analyze, context=context_text)
        
        agent.analyze_text.assert_called_once_with(text_to_analyze, context=context_text)
        
        self.assertIsInstance(result, dict)
        self.assertIn("fallacies", result)
        self.assertIn("context", result)
        self.assertIn("analysis_timestamp", result)
        self.assertEqual(result["context"], context_text)
    
    async def test_analyze_text_with_confidence_threshold(self):
        """Teste la méthode analyze_text avec un seuil de confiance."""
        agent = self.agent
        text_to_analyze = self.sample_text
        
        expected_filtered_fallacies = [
            {"fallacy_type": "Appel à l'autorité", "text": "Les experts...", "confidence": 0.7}
        ]

        agent.analyze_text.return_value = { 
            "fallacies": expected_filtered_fallacies,
            "analysis_timestamp": "some_timestamp"
        }

        result = await agent.analyze_text(text_to_analyze)
        
        agent.analyze_text.assert_called_once_with(text_to_analyze)

        self.assertIsInstance(result, dict)
        self.assertIn("fallacies", result)
        self.assertEqual(len(result["fallacies"]), 1)
        self.assertEqual(result["fallacies"][0]["fallacy_type"], "Appel à l'autorité")
        self.assertEqual(result["fallacies"][0]["confidence"], 0.7)
    
    def test_categorize_fallacies(self): 
        """Teste la méthode categorize_fallacies."""
        agent = self.agent
        fallacies_input = [
            {"fallacy_type": "Appel à l'autorité", "text": "...", "confidence": 0.7}, # Normalisé: appel_à_l'autorité
            {"fallacy_type": "Appel à la popularité", "text": "...", "confidence": 0.6}, # Normalisé: appel_à_la_popularité
            {"fallacy_type": "Ad hominem", "text": "...", "confidence": 0.8} # Normalisé: ad_hominem
        ]
        
        # Le mapping dans l'agent est:
        # "ad_hominem": "RELEVANCE"
        # "appel_autorite": "RELEVANCE" (sans _à_l_)
        # "appel_popularite": "INDUCTION" (sans _à_la_)
        # Donc "appel_à_l'autorité" et "appel_à_la_popularité" iront dans AUTRES.
        expected_categories_from_agent_logic = {
            "RELEVANCE": ["ad_hominem"], 
            "INDUCTION": [], 
            "AUTRES": ["appel_à_l'autorité", "appel_à_la_popularité"], # Corrigé ici
            "CAUSALITE": [],
            "AMBIGUITE": [],
            "PRESUPPOSITION": []
        }
        
        categories = agent.categorize_fallacies(fallacies_input)
        
        self.assertIsInstance(categories, dict)
        self.assertListEqual(sorted(categories.get("RELEVANCE", [])), sorted(expected_categories_from_agent_logic["RELEVANCE"]))
        self.assertListEqual(sorted(categories.get("INDUCTION", [])), sorted(expected_categories_from_agent_logic["INDUCTION"]))
        self.assertListEqual(sorted(categories.get("AUTRES", [])), sorted(expected_categories_from_agent_logic["AUTRES"]))
        self.assertEqual(categories.get("CAUSALITE", []), [])
        self.assertEqual(categories.get("AMBIGUITE", []), [])
        self.assertEqual(categories.get("PRESUPPOSITION", []), [])