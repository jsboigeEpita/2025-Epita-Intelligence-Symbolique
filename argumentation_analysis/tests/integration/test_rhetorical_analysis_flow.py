# -*- coding: utf-8 -*-
"""
Tests d'intégration pour le flux complet d'analyse rhétorique.

Ce module contient des tests d'intégration qui vérifient le flux complet
d'analyse rhétorique, de l'extraction à l'analyse informelle jusqu'à la conclusion.
"""

import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import semantic_kernel as sk
from semantic_kernel.contents import ChatMessageContent, AuthorRole

# Utiliser la fonction setup_import_paths pour résoudre les problèmes d'imports relatifs
from argumentation_analysis.tests import setup_import_paths
setup_import_paths()

from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
from argumentation_analysis.core.state_manager_plugin import StateManagerPlugin
from argumentation_analysis.core.strategies import BalancedParticipationStrategy
from argumentation_analysis.orchestration.analysis_runner import run_analysis_conversation
from argumentation_analysis.agents.core.extract.extract_agent import ExtractAgent
from argumentation_analysis.agents.core.pl.pl_definitions import setup_pl_kernel
from argumentation_analysis.agents.core.informal.informal_definitions import setup_informal_kernel
from argumentation_analysis.agents.core.pm.pm_definitions import setup_pm_kernel
from argumentation_analysis.tests.async_test_case import AsyncTestCase
from argumentation_analysis.agents.tools.analysis.contextual_fallacy_analyzer import ContextualFallacyAnalyzer
from argumentation_analysis.agents.tools.analysis.complex_fallacy_analyzer import ComplexFallacyAnalyzer


class TestRhetoricalAnalysisFlow(AsyncTestCase):
    """Tests d'intégration pour le flux complet d'analyse rhétorique."""

    def setUp(self):
        """Initialisation avant chaque test."""
        # Créer un texte de test
        self.test_text = """
        La Terre est plate car l'horizon semble plat quand on regarde au loin.
        De plus, si la Terre était ronde, les gens à l'autre bout tomberaient.
        Certains scientifiques affirment que la Terre est ronde, mais ils sont payés par la NASA.
        """
        
        # Créer un état partagé
        self.state = RhetoricalAnalysisState(self.test_text)
        
        # Créer un service LLM mock
        self.llm_service = MagicMock()
        self.llm_service.service_id = "test_service"
        
        # Créer un kernel
        self.kernel = sk.Kernel()
        
        # Ajouter le plugin StateManager
        self.state_manager = StateManagerPlugin(self.state)
        self.kernel.add_plugin(self.state_manager, "StateManager")
        
        # Créer des agents mock
        self.pm_agent = MagicMock()
        self.pm_agent.name = "ProjectManagerAgent"
        
        self.pl_agent = MagicMock()
        self.pl_agent.name = "PropositionalLogicAgent"
        
        self.informal_agent = MagicMock()
        self.informal_agent.name = "InformalAnalysisAgent"
        
        self.extract_agent = MagicMock()
        self.extract_agent.name = "ExtractAgent"
        
        self.agents = [self.pm_agent, self.pl_agent, self.informal_agent, self.extract_agent]
        
        # Créer la stratégie d'équilibrage
        self.balanced_strategy = BalancedParticipationStrategy(
            agents=self.agents,
            state=self.state,
            default_agent_name="ProjectManagerAgent"
        )
        
        # Créer des outils d'analyse
        self.contextual_fallacy_analyzer = ContextualFallacyAnalyzer()
        self.complex_fallacy_analyzer = MagicMock(spec=ComplexFallacyAnalyzer)

    async def test_complete_analysis_flow(self):
        """Teste le flux complet d'analyse rhétorique."""
        # Simuler le flux complet d'analyse rhétorique
        
        # 1. Phase d'extraction: L'agent d'extraction identifie les segments pertinents
        extract_id = self.state.add_extract("Extrait principal", self.test_text)
        
        # Vérifier que l'extrait a été ajouté correctement
        self.assertIn(extract_id, self.state.extracts)
        self.assertEqual(self.state.extracts[extract_id]["name"], "Extrait principal")
        self.assertEqual(self.state.extracts[extract_id]["content"], self.test_text)
        
        # 2. Phase d'analyse informelle: L'agent informel identifie les arguments
        arg1_id = self.state.add_argument("La Terre est plate car l'horizon semble plat")
        arg2_id = self.state.add_argument("Si la Terre était ronde, les gens tomberaient")
        arg3_id = self.state.add_argument("Les scientifiques sont payés par la NASA")
        
        # Vérifier que les arguments ont été ajoutés correctement
        self.assertEqual(len(self.state.identified_arguments), 3)
        self.assertIn(arg1_id, self.state.identified_arguments)
        self.assertIn(arg2_id, self.state.identified_arguments)
        self.assertIn(arg3_id, self.state.identified_arguments)
        
        # 3. Phase d'analyse des sophismes: L'agent informel identifie les sophismes
        # Configurer le mock pour l'analyseur de sophismes complexes
        self.complex_fallacy_analyzer.analyze_argument_chain.return_value = {
            "fallacies": [
                {
                    "fallacy_type": "Faux raisonnement",
                    "explanation": "Confusion entre apparence et réalité",
                    "severity": "high",
                    "argument_id": arg1_id
                },
                {
                    "fallacy_type": "Fausse analogie",
                    "explanation": "Mauvaise compréhension de la gravité",
                    "severity": "medium",
                    "argument_id": arg2_id
                }
            ],
            "overall_assessment": "Les arguments contiennent plusieurs sophismes graves."
        }
        
        # Ajouter les sophismes à l'état
        fallacy1_id = self.state.add_fallacy("Faux raisonnement", "Confusion entre apparence et réalité", arg1_id)
        fallacy2_id = self.state.add_fallacy("Fausse analogie", "Mauvaise compréhension de la gravité", arg2_id)
        fallacy3_id = self.state.add_fallacy("Ad hominem", "Attaque la crédibilité plutôt que l'argument", arg3_id)
        
        # Vérifier que les sophismes ont été ajoutés correctement
        self.assertEqual(len(self.state.identified_fallacies), 3)
        self.assertIn(fallacy1_id, self.state.identified_fallacies)
        self.assertIn(fallacy2_id, self.state.identified_fallacies)
        self.assertIn(fallacy3_id, self.state.identified_fallacies)
        
        # 4. Phase d'analyse contextuelle: Utiliser l'analyseur de sophismes contextuels
        # Patch pour la méthode analyze_context
        with patch.object(self.contextual_fallacy_analyzer, 'analyze_context') as mock_analyze_context:
            # Configurer le mock
            mock_analyze_context.return_value = {
                "context_type": "scientifique",
                "potential_fallacies_count": 3,
                "contextual_fallacies_count": 2,
                "contextual_fallacies": [
                    {
                        "fallacy_type": "Appel à l'autorité",
                        "keyword": "scientifiques",
                        "context_text": "Certains scientifiques affirment que la Terre est ronde",
                        "confidence": 0.8,
                        "contextual_relevance": "Élevée"
                    },
                    {
                        "fallacy_type": "Ad hominem",
                        "keyword": "payés",
                        "context_text": "ils sont payés par la NASA",
                        "confidence": 0.9,
                        "contextual_relevance": "Élevée"
                    }
                ]
            }
            
            # Analyser le contexte
            context = "Discussion scientifique sur la forme de la Terre"
            result = self.contextual_fallacy_analyzer.analyze_context(self.test_text, context)
            
            # Vérifier les résultats
            self.assertEqual(result["context_type"], "scientifique")
            self.assertEqual(result["contextual_fallacies_count"], 2)
            
            # Ajouter les sophismes contextuels à l'état
            for fallacy in result["contextual_fallacies"]:
                self.state.add_fallacy(
                    fallacy["fallacy_type"],
                    f"{fallacy['context_text']} (Confiance: {fallacy['confidence']})"
                )
        
        # 5. Phase de formalisation: L'agent PL formalise les arguments
        bs_id = self.state.add_belief_set("Propositional", """
        # Formalisation de l'argument 1
        horizon_plat => terre_plate  # Si l'horizon semble plat, alors la Terre est plate
        horizon_plat               # L'horizon semble plat
        
        # Formalisation de l'argument 2
        terre_ronde => gens_tombent  # Si la Terre est ronde, les gens tombent
        ~gens_tombent               # Les gens ne tombent pas
        """)
        
        # Vérifier que l'ensemble de croyances a été ajouté correctement
        self.assertIn(bs_id, self.state.belief_sets)
        
        # 6. Phase d'évaluation logique: L'agent PL évalue la validité des arguments
        log_id1 = self.state.log_query(bs_id, "horizon_plat => terre_plate", "ACCEPTED (True)")
        log_id2 = self.state.log_query(bs_id, "terre_plate", "UNKNOWN")
        log_id3 = self.state.log_query(bs_id, "~terre_ronde", "ACCEPTED (True)")
        
        # Vérifier que les requêtes ont été enregistrées correctement
        self.assertEqual(len(self.state.query_log), 3)
        
        # 7. Phase de conclusion: Le PM ajoute une conclusion
        conclusion = """
        L'analyse rhétorique du texte révèle plusieurs sophismes:
        1. Un faux raisonnement qui confond apparence et réalité
        2. Une fausse analogie qui montre une mauvaise compréhension de la gravité
        3. Un ad hominem qui attaque la crédibilité des scientifiques
        
        Ces sophismes invalident les arguments présentés en faveur de la théorie de la Terre plate.
        L'analyse formelle confirme que les arguments ne sont pas logiquement valides.
        """
        self.state.set_conclusion(conclusion)
        
        # Vérifier que la conclusion a été définie correctement
        self.assertIsNotNone(self.state.final_conclusion)
        self.assertIn("sophismes", self.state.final_conclusion)
        self.assertIn("invalident les arguments", self.state.final_conclusion)

    async def test_analysis_flow_with_errors(self):
        """Teste le flux d'analyse rhétorique avec gestion des erreurs."""
        # 1. Phase d'extraction: L'agent d'extraction rencontre une erreur
        self.state.log_error("ExtractAgent", "Erreur lors de l'extraction du texte")
        
        # Vérifier que l'erreur a été enregistrée correctement
        self.assertEqual(len(self.state.errors), 1)
        self.assertEqual(self.state.errors[0]["agent_name"], "ExtractAgent")
        
        # 2. Le PM ajoute une tâche pour contourner l'erreur
        task_id = self.state.add_task("Analyser directement le texte brut")
        
        # 3. L'agent informel identifie les arguments directement à partir du texte brut
        arg1_id = self.state.add_argument("La Terre est plate car l'horizon semble plat")
        
        # 4. L'agent informel identifie un sophisme
        fallacy_id = self.state.add_fallacy("Faux raisonnement", "Confusion entre apparence et réalité", arg1_id)
        
        # 5. L'agent informel ajoute une réponse à la tâche
        self.state.add_answer(
            task_id,
            "InformalAnalysisAgent",
            "J'ai identifié un argument et un sophisme dans le texte brut.",
            [arg1_id, fallacy_id]
        )
        
        # 6. Le PM ajoute une conclusion adaptée
        conclusion = """
        Malgré une erreur lors de la phase d'extraction, l'analyse a pu identifier
        un sophisme de faux raisonnement qui invalide l'argument principal.
        """
        self.state.set_conclusion(conclusion)
        
        # Vérifier que la conclusion a été définie correctement
        self.assertIsNotNone(self.state.final_conclusion)
        self.assertIn("Malgré une erreur", self.state.final_conclusion)
        self.assertIn("sophisme de faux raisonnement", self.state.final_conclusion)

    async def test_incremental_analysis_flow(self):
        """Teste le flux d'analyse rhétorique incrémental."""
        # Simuler un flux d'analyse incrémental où les agents travaillent par étapes
        
        # 1. Le PM définit les tâches d'analyse
        task1_id = self.state.add_task("Extraire les segments pertinents")
        task2_id = self.state.add_task("Identifier les arguments")
        task3_id = self.state.add_task("Analyser les sophismes")
        task4_id = self.state.add_task("Formaliser les arguments")
        task5_id = self.state.add_task("Évaluer la validité logique")
        
        # Vérifier que les tâches ont été ajoutées correctement
        self.assertEqual(len(self.state.analysis_tasks), 5)
        
        # 2. L'agent d'extraction traite la première tâche
        extract_id = self.state.add_extract("Extrait principal", self.test_text)
        self.state.add_answer(
            task1_id,
            "ExtractAgent",
            "J'ai extrait le texte complet pour analyse.",
            [extract_id]
        )
        
        # 3. L'agent informel traite la deuxième tâche
        arg1_id = self.state.add_argument("La Terre est plate car l'horizon semble plat")
        arg2_id = self.state.add_argument("Si la Terre était ronde, les gens tomberaient")
        self.state.add_answer(
            task2_id,
            "InformalAnalysisAgent",
            "J'ai identifié 2 arguments principaux dans le texte.",
            [arg1_id, arg2_id]
        )
        
        # 4. L'agent informel traite la troisième tâche
        fallacy1_id = self.state.add_fallacy("Faux raisonnement", "Confusion entre apparence et réalité", arg1_id)
        fallacy2_id = self.state.add_fallacy("Fausse analogie", "Mauvaise compréhension de la gravité", arg2_id)
        self.state.add_answer(
            task3_id,
            "InformalAnalysisAgent",
            "J'ai identifié 2 sophismes dans les arguments.",
            [fallacy1_id, fallacy2_id]
        )
        
        # 5. L'agent PL traite la quatrième tâche
        bs_id = self.state.add_belief_set("Propositional", """
        # Argument 1
        horizon_plat => terre_plate
        horizon_plat
        
        # Argument 2
        terre_ronde => gens_tombent
        ~gens_tombent
        """)
        self.state.add_answer(
            task4_id,
            "PropositionalLogicAgent",
            "J'ai formalisé les 2 arguments en logique propositionnelle.",
            [bs_id]
        )
        
        # 6. L'agent PL traite la cinquième tâche
        log_id1 = self.state.log_query(bs_id, "terre_plate", "ACCEPTED (True)")
        log_id2 = self.state.log_query(bs_id, "~terre_ronde", "ACCEPTED (True)")
        self.state.add_answer(
            task5_id,
            "PropositionalLogicAgent",
            "J'ai évalué la validité logique des arguments formalisés.",
            [log_id1, log_id2]
        )
        
        # 7. Le PM ajoute une conclusion basée sur toutes les réponses
        self.state.set_conclusion("""
        L'analyse rhétorique complète a identifié:
        - 2 arguments principaux
        - 2 sophismes qui invalident ces arguments
        - Une formalisation logique qui confirme les problèmes de raisonnement
        
        Conclusion: Les arguments en faveur de la théorie de la Terre plate sont invalides.
        """)
        
        # Vérifier l'état final
        self.assertEqual(len(self.state.analysis_tasks), 5)
        self.assertEqual(len(self.state.extracts), 1)
        self.assertEqual(len(self.state.identified_arguments), 2)
        self.assertEqual(len(self.state.identified_fallacies), 2)
        self.assertEqual(len(self.state.belief_sets), 1)
        self.assertEqual(len(self.state.query_log), 2)
        self.assertEqual(len(self.state.answers), 5)
        self.assertIsNotNone(self.state.final_conclusion)


if __name__ == "__main__":
    unittest.main()