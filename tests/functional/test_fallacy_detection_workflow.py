# -*- coding: utf-8 -*-
"""
Tests fonctionnels pour le workflow de détection de sophismes.

Ce module contient des tests fonctionnels qui vérifient le workflow complet
de détection de sophismes, y compris l'interaction entre les différents
analyseurs de sophismes (contextuel, complexe, évaluation de la gravité).
"""

import unittest
import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import semantic_kernel as sk # Importation inutilisée ?
from semantic_kernel.contents import ChatMessageContent, AuthorRole # Importations inutilisées ?
from semantic_kernel.agents import Agent, AgentGroupChat # Importations inutilisées ?

# Ajouter le répertoire racine au chemin Python pour pouvoir importer les modules
import sys
import os
# project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# if project_root not in sys.path:
#    sys.path.insert(0, project_root)
# Commenté car conftest.py et pytest.ini devraient gérer cela.

from argumentation_analysis.core.shared_state import RhetoricalAnalysisState # Importation inutilisée ?
from argumentation_analysis.core.state_manager_plugin import StateManagerPlugin # Importation inutilisée ?
from argumentation_analysis.core.strategies import BalancedParticipationStrategy, SimpleTerminationStrategy # Importations inutilisées ?
from argumentation_analysis.orchestration.analysis_runner import run_analysis_conversation # Importation inutilisée ?
from argumentation_analysis.agents.core.extract.extract_agent import ExtractAgent # Importation inutilisée ?
from argumentation_analysis.agents.core.pl.pl_definitions import setup_pl_kernel # Importation inutilisée ?
from argumentation_analysis.agents.core.informal.informal_definitions import setup_informal_kernel # Importation inutilisée ?
from argumentation_analysis.agents.core.pm.pm_definitions import setup_pm_kernel # Importation inutilisée ?
from tests.async_test_case import AsyncTestCase

# Imports spécifiques pour ce test
from argumentation_analysis.agents.tools.analysis.enhanced.complex_fallacy_analyzer import EnhancedComplexFallacyAnalyzer as ComplexFallacyAnalyzer # Alias pour compatibilité
from argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer import EnhancedContextualFallacyAnalyzer
from argumentation_analysis.agents.tools.analysis.enhanced.fallacy_severity_evaluator import EnhancedFallacySeverityEvaluator


class TestFallacyDetectionWorkflow(AsyncTestCase):
    """Tests fonctionnels pour le workflow de détection de sophismes."""

    def setUp(self):
        """Initialisation avant chaque test."""
        self.complex_analyzer = ComplexFallacyAnalyzer()
        self.contextual_analyzer = EnhancedContextualFallacyAnalyzer()
        self.severity_evaluator = EnhancedFallacySeverityEvaluator()

        self.sample_text_with_fallacies = """
        Argument 1: Tous les chats sont des animaux. Socrate est un animal. Donc Socrate est un chat. (Sophisme de type A)
        Argument 2: Si nous autorisons les enfants à choisir leur heure de coucher, ils ne dormiront jamais. (Sophisme de type B)
        Argument 3: Mon médecin m'a dit que ce médicament est efficace, donc il doit l'être. (Sophisme de type C)
        Argument 4: Beaucoup de gens croient aux fantômes, donc ils doivent exister. (Sophisme de type D)
        """
        self.sample_context = "Débat public sur la logique et la persuasion."

    @pytest.mark.asyncio
    async def test_full_fallacy_detection_workflow(self):
        """Teste le workflow complet de détection de sophismes."""
        
        # 1. Analyse contextuelle pour identifier les sophismes potentiels
        # Utiliser directement identify_contextual_fallacies qui appelle analyze_context en interne
        contextual_fallacies = self.contextual_analyzer.identify_contextual_fallacies(
            self.sample_text_with_fallacies, 
            self.sample_context
        )
        
        self.assertIsNotNone(contextual_fallacies)
        # S'attendre à ce que des sophismes soient détectés (même si ce sont des mocks pour l'instant)
        # Le nombre exact dépendra de l'implémentation réelle et des mocks
        
        # Préparer les arguments pour l'analyseur complexe
        # Dans un vrai scénario, les arguments seraient extraits du texte
        # Ici, nous utilisons le texte entier comme un seul "argument" pour simplifier
        arguments_for_complex_analysis = [self.sample_text_with_fallacies]

        # 2. Analyse complexe pour identifier les sophismes composés et les structures
        complex_analysis_results = self.complex_analyzer.detect_composite_fallacies(
            arguments_for_complex_analysis, 
            self.sample_context
        )
        
        self.assertIsNotNone(complex_analysis_results)
        self.assertIn("individual_fallacies_count", complex_analysis_results)
        self.assertIn("basic_combinations", complex_analysis_results)
        self.assertIn("advanced_combinations", complex_analysis_results)
        self.assertIn("composite_severity", complex_analysis_results)
        
        # Récupérer tous les sophismes identifiés (individuels et composés)
        all_identified_fallacies = []
        # Supposons que contextual_fallacies est une liste de dictionnaires de sophismes
        if isinstance(contextual_fallacies, list):
            all_identified_fallacies.extend(contextual_fallacies)
        
        # Ajouter les sophismes des combinaisons (simplification)
        if isinstance(complex_analysis_results.get("basic_combinations"), list):
             for combo in complex_analysis_results["basic_combinations"]:
                # Supposer que chaque combo a une description et une sévérité
                all_identified_fallacies.append({
                    "fallacy_type": combo.get("combination_name", "Combinaison de base"),
                    "description": combo.get("description"),
                    "confidence": combo.get("severity", 0.5) # Utiliser la sévérité comme confiance
                })

        if isinstance(complex_analysis_results.get("advanced_combinations"), list):
            for combo in complex_analysis_results["advanced_combinations"]:
                all_identified_fallacies.append({
                    "fallacy_type": combo.get("combination_name", "Combinaison avancée"),
                    "description": combo.get("description"),
                    "confidence": combo.get("severity", 0.7) 
                })
        
        # 3. Évaluation de la gravité des sophismes identifiés
        if all_identified_fallacies:
            severity_results = self.severity_evaluator.evaluate_fallacies_severity(
                all_identified_fallacies, 
                self.sample_context
            )
            
            self.assertIsNotNone(severity_results)
            self.assertIsInstance(severity_results, list)
            if severity_results: # S'assurer que la liste n'est pas vide
                self.assertIn("fallacy_type", severity_results[0])
                self.assertIn("original_confidence", severity_results[0])
                self.assertIn("contextual_adjustment", severity_results[0])
                self.assertIn("final_severity_score", severity_results[0])
                self.assertIn("severity_level", severity_results[0])
        else:
            # Si aucun sophisme n'a été identifié par les étapes précédentes,
            # severity_results sera probablement vide ou non appelé.
            # On peut ajouter une assertion pour ce cas si nécessaire.
            pass 

        # Vérifications supplémentaires sur les interactions (si les analyseurs se parlent)
        # Pour l'instant, ils sont appelés séquentiellement.

if __name__ == '__main__':
    pytest.main(['-xvs', __file__])