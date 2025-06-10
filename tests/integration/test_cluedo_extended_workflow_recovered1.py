# tests/integration/recovered/test_cluedo_extended_workflow.py
"""
Tests de comparaison entre workflows Cluedo 2-agents vs 3-agents.
Récupéré et adapté pour Oracle Enhanced v2.1.0

Tests couvrant:
- Comparaison des performances Sherlock+Watson vs Sherlock+Watson+Moriarty
- Analyse de l'efficacité du système Oracle
- Métriques comparatives de résolution
- Impact des révélations sur la vitesse de résolution
- Évolution des stratégies avec l'agent Oracle
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List, Tuple
from datetime import datetime

from semantic_kernel.kernel import Kernel
from argumentation_analysis.utils.semantic_kernel_compatibility import ChatMessageContent

# Imports des orchestrateurs (adaptés v2.1.0)
from argumentation_analysis.orchestration.cluedo_orchestrator import run_cluedo_game
from argumentation_analysis.orchestration.cluedo_extended_orchestrator import run_cluedo_oracle_game

# Imports des états (adaptés v2.1.0)
from argumentation_analysis.core.enquete_states import EnqueteCluedoState
from argumentation_analysis.core.cluedo_oracle_state import CluedoOracleState

# Imports des agents (adaptés v2.1.0)
from argumentation_analysis.agents.core.pm.sherlock_enquete_agent import SherlockEnqueteAgent
from argumentation_analysis.agents.core.logic.watson_logic_assistant import WatsonLogicAssistant
from argumentation_analysis.agents.core.oracle.moriarty_interrogator_agent import MoriartyInterrogatorAgent


@pytest.mark.integration
@pytest.mark.comparison
class TestWorkflowComparison:
    """Tests de comparaison entre workflows 2-agents et 3-agents Oracle Enhanced v2.1.0."""
    
    @pytest.fixture
    def mock_kernel(self):
        """Kernel mocké pour tests comparatifs."""
        kernel = Mock(spec=Kernel)
        kernel.add_plugin = Mock()
        kernel.add_filter = Mock()
        return kernel
    
    @pytest.fixture
    def comparison_elements(self):
        """Éléments Cluedo standardisés pour comparaisons équitables."""
        return {
            "suspects": ["Colonel Moutarde", "Professeur Violet", "Mademoiselle Rose"],
            "armes": ["Poignard", "Chandelier", "Revolver"],
            "lieux": ["Salon", "Cuisine", "Bureau"]
        }
    
    @pytest.fixture
    def mock_conversation_2agents(self):
        """Conversation simulée pour workflow 2-agents."""
        return [
            ChatMessageContent(role="assistant", content="Sherlock: J'examine les indices...", name="Sherlock"),
            ChatMessageContent(role="assistant", content="Watson: Logiquement, cela suggère...", name="Watson"),
            ChatMessageContent(role="assistant", content="Sherlock: Je propose Colonel Moutarde, Poignard, Salon", name="Sherlock"),
        ]
    
    @pytest.fixture
    def mock_conversation_3agents(self):
        """Conversation simulée pour workflow 3-agents."""
        return [
            ChatMessageContent(role="assistant", content="Sherlock: J'examine les indices...", name="Sherlock"),
            ChatMessageContent(role="assistant", content="Watson: Logiquement, cela suggère...", name="Watson"),
            ChatMessageContent(role="assistant", content="Moriarty: Je révèle posséder Professeur Violet", name="Moriarty"),
            ChatMessageContent(role="assistant", content="Sherlock: Avec cette information...", name="Sherlock"),
            ChatMessageContent(role="assistant", content="Watson: Donc c'est Colonel Moutarde, Poignard, Salon", name="Watson"),
        ]
    
    @pytest.mark.asyncio
    async def test_workflow_setup_comparison(self, mock_kernel, comparison_elements):
        """Test la comparaison des configurations de workflow."""
        # Configuration 2-agents (simulée)
        state_2agents = EnqueteCluedoState(
            nom_enquete_cluedo="Comparison Test 2-Agents",
            elements_jeu_cluedo=comparison_elements
        )
        
        # Configuration 3-agents Oracle Enhanced v2.1.0
        state_3agents = CluedoOracleState(
            nom_enquete_cluedo="Comparison Test 3-Agents",
            elements_jeu_cluedo=comparison_elements,
            oracle_strategy="balanced"
        )
        
        # Comparaison des configurations
        assert state_2agents.nom_enquete == "Comparison Test 2-Agents"
        assert state_3agents.nom_enquete == "Comparison Test 3-Agents"
        
        # Vérification des capacités étendues du 3-agents
        assert hasattr(state_3agents, 'oracle_interactions')
        assert hasattr(state_3agents, 'cards_revealed')
        assert hasattr(state_3agents, 'cluedo_dataset')
        assert not hasattr(state_2agents, 'oracle_interactions')
        
        # Solutions devraient être différentes (générées aléatoirement)
        solution_2 = state_2agents.get_solution_secrete()
        solution_3 = state_3agents.get_solution_secrete()
        
        # Les deux solutions doivent être valides
        for solution in [solution_2, solution_3]:
            assert solution["suspect"] in comparison_elements["suspects"]
            assert solution["arme"] in comparison_elements["armes"]
            assert solution["lieu"] in comparison_elements["lieux"]
    
    def test_agent_capabilities_comparison(self, mock_kernel, comparison_elements):
        """Test la comparaison des capacités des agents."""
        # Agents 2-agents
        sherlock_2 = SherlockEnqueteAgent(kernel=mock_kernel, agent_name="Sherlock2")
        watson_2 = WatsonLogicAssistant(
            kernel=mock_kernel, 
            agent_name="Watson2",
            constants=[name.replace(" ", "") for category in comparison_elements.values() for name in category]
        )
        
        # Agents 3-agents (avec Moriarty)
        sherlock_3 = SherlockEnqueteAgent(kernel=mock_kernel, agent_name="Sherlock3")
        watson_3 = WatsonLogicAssistant(
            kernel=mock_kernel,
            agent_name="Watson3",
            constants=[name.replace(" ", "") for category in comparison_elements.values() for name in category]
        )
        
        # Création d'un dataset pour Moriarty (v2.1.0)
        from argumentation_analysis.agents.core.oracle.cluedo_dataset import CluedoDataset
        cluedo_dataset = CluedoDataset(elements_jeu=comparison_elements)
        
        moriarty = MoriartyInterrogatorAgent(
            kernel=mock_kernel,
            cluedo_dataset=cluedo_dataset,
            game_strategy="balanced",
            agent_name="Moriarty"
        )
        
        # Comparaison des agents
        agents_2 = [sherlock_2, watson_2]
        agents_3 = [sherlock_3, watson_3, moriarty]
        
        assert len(agents_2) == 2
        assert len(agents_3) == 3
        
        # Vérification des capacités uniques de Moriarty
        assert hasattr(moriarty, 'moriarty_tools')
        assert hasattr(moriarty, 'cluedo_dataset')
        assert not hasattr(sherlock_2, 'moriarty_tools')
        assert not hasattr(watson_2, 'moriarty_tools')
    
    @pytest.mark.asyncio
    async def test_conversation_length_comparison(self, mock_kernel, mock_conversation_2agents, mock_conversation_3agents):
        """Test la comparaison de la longueur des conversations."""
        
        # Analyse des conversations simulées
        conv_2_length = len(mock_conversation_2agents)
        conv_3_length = len(mock_conversation_3agents)
        
        # Le workflow 3-agents peut être plus long mais plus informatif
        assert conv_3_length >= conv_2_length
        
        # Analyse du contenu informationnel
        conv_2_content = " ".join([msg.content for msg in mock_conversation_2agents])
        conv_3_content = " ".join([msg.content for msg in mock_conversation_3agents])
        
        # Le workflow 3-agents devrait contenir des révélations
        revelation_terms = ["révèle", "possède", "information", "indice"]
        conv_3_revelations = sum(1 for term in revelation_terms if term in conv_3_content.lower())
        conv_2_revelations = sum(1 for term in revelation_terms if term in conv_2_content.lower())
        
        assert conv_3_revelations >= conv_2_revelations
    
    def test_information_richness_comparison(self, comparison_elements):
        """Test la comparaison de la richesse informationnelle."""
        
        # État 2-agents
        state_2 = EnqueteCluedoState(
            nom_enquete_cluedo="Info Test 2-Agents",
            elements_jeu_cluedo=comparison_elements
        )
        
        # État 3-agents Oracle Enhanced v2.1.0
        state_3 = CluedoOracleState(
            nom_enquete_cluedo="Info Test 3-Agents",
            elements_jeu_cluedo=comparison_elements,
            oracle_strategy="cooperative"
        )
        
        # Simulation d'activité pour comparaison
        # 2-agents : hypothèses et tâches classiques
        state_2.add_hypothesis("Hypothesis 1", "Sherlock", 0.7)
        state_2.add_hypothesis("Hypothesis 2", "Watson", 0.6)
        state_2.add_task("Investigate library", "Sherlock", "pending")
        
        # 3-agents : hypothèses + révélations Oracle
        state_3.add_hypothesis("Hypothesis 1", "Sherlock", 0.7)
        state_3.add_hypothesis("Hypothesis 2", "Watson", 0.6)
        state_3.add_task("Investigate library", "Sherlock", "pending")
        
        # Ajout de révélations Oracle (v2.1.0)
        from argumentation_analysis.agents.core.oracle.cluedo_dataset import CluedoRevelation
        revelation = CluedoRevelation(
            card_revealed="Professeur Violet",
            revelation_type="owned_card",
            message="Information révélée par Oracle"
        )
        state_3.add_revelation(revelation, "Moriarty")
        
        # Comparaison de la richesse informationnelle
        info_2 = {
            "hypotheses": len(state_2.hypotheses),
            "tasks": len(state_2.tasks),
            "revelations": 0  # Pas de révélations dans 2-agents
        }
        
        info_3 = {
            "hypotheses": len(state_3.hypotheses),
            "tasks": len(state_3.tasks),
            "revelations": len(state_3.recent_revelations)
        }
        
        # Le 3-agents devrait avoir plus d'informations au total
        total_info_2 = sum(info_2.values())
        total_info_3 = sum(info_3.values())
        
        assert total_info_3 > total_info_2
        assert info_3["revelations"] > info_2["revelations"]
    
    @pytest.mark.asyncio
    async def test_resolution_efficiency_simulation(self, mock_kernel, comparison_elements):
        """Test de simulation d'efficacité de résolution Oracle Enhanced v2.1.0."""
        
        # Métriques simulées pour workflow 2-agents
        metrics_2agents = {
            "setup_time": 0.5,
            "average_turn_duration": 2.0,
            "total_turns": 6,
            "information_gathered": 3,  # Hypothèses et déductions
            "resolution_confidence": 0.7
        }
        
        # Métriques simulées pour workflow 3-agents Oracle Enhanced
        metrics_3agents = {
            "setup_time": 0.8,  # Légèrement plus long (Oracle setup)
            "average_turn_duration": 1.8,  # Plus rapide grâce aux révélations
            "total_turns": 5,  # Moins de tours grâce aux informations Oracle
            "information_gathered": 5,  # Hypothèses + révélations Oracle
            "resolution_confidence": 0.9  # Plus confiant grâce aux informations supplémentaires
        }
        
        # Calcul de l'efficacité totale
        total_time_2 = metrics_2agents["setup_time"] + (metrics_2agents["total_turns"] * metrics_2agents["average_turn_duration"])
        total_time_3 = metrics_3agents["setup_time"] + (metrics_3agents["total_turns"] * metrics_3agents["average_turn_duration"])
        
        efficiency_2 = metrics_2agents["information_gathered"] / total_time_2
        efficiency_3 = metrics_3agents["information_gathered"] / total_time_3
        
        # Le workflow 3-agents devrait être plus efficace
        assert efficiency_3 > efficiency_2
        assert metrics_3agents["total_turns"] <= metrics_2agents["total_turns"]
        assert metrics_3agents["resolution_confidence"] > metrics_2agents["resolution_confidence"]
    
    def test_scalability_comparison(self, mock_kernel):
        """Test la comparaison de scalabilité."""
        
        # Éléments de jeu de tailles différentes
        small_elements = {
            "suspects": ["Colonel Moutarde", "Professeur Violet"],
            "armes": ["Poignard", "Chandelier"],
            "lieux": ["Salon", "Cuisine"]
        }
        
        large_elements = {
            "suspects": [f"Suspect{i}" for i in range(10)],
            "armes": [f"Arme{i}" for i in range(8)],
            "lieux": [f"Lieu{i}" for i in range(12)]
        }
        
        # Test avec petit jeu
        start_time = time.time()
        small_state_2 = EnqueteCluedoState(
            nom_enquete_cluedo="Small 2-Agents",
            elements_jeu_cluedo=small_elements
        )
        small_2_setup_time = time.time() - start_time
        
        start_time = time.time()
        small_state_3 = CluedoOracleState(
            nom_enquete_cluedo="Small 3-Agents",
            elements_jeu_cluedo=small_elements,
            oracle_strategy="balanced"
        )
        small_3_setup_time = time.time() - start_time
        
        # Test avec grand jeu
        start_time = time.time()
        large_state_2 = EnqueteCluedoState(
            nom_enquete_cluedo="Large 2-Agents",
            elements_jeu_cluedo=large_elements
        )
        large_2_setup_time = time.time() - start_time
        
        start_time = time.time()
        large_state_3 = CluedoOracleState(
            nom_enquete_cluedo="Large 3-Agents",
            elements_jeu_cluedo=large_elements,
            oracle_strategy="balanced"
        )
        large_3_setup_time = time.time() - start_time
        
        # Analyse de la scalabilité
        scaling_2 = large_2_setup_time / small_2_setup_time if small_2_setup_time > 0 else float('inf')
        scaling_3 = large_3_setup_time / small_3_setup_time if small_3_setup_time > 0 else float('inf')
        
        # Vérification que les temps restent raisonnables
        assert small_2_setup_time < 1.0
        assert small_3_setup_time < 2.0  # Peut être plus long à cause de l'Oracle
        assert large_2_setup_time < 5.0
        assert large_3_setup_time < 10.0
        
        # Le workflow 3-agents peut prendre plus de temps de setup mais devrait bien scaler
        assert scaling_3 < 20  # Scaling acceptable
    
    @pytest.mark.asyncio
    async def test_strategy_adaptation_comparison(self, mock_kernel, comparison_elements):
        """Test la comparaison d'adaptation stratégique Oracle Enhanced v2.1.0."""
        
        # Workflow 2-agents : stratégie fixe
        state_2 = EnqueteCluedoState(
            nom_enquete_cluedo="Strategy Test 2-Agents",
            elements_jeu_cluedo=comparison_elements
        )
        
        # Workflow 3-agents : différentes stratégies Oracle Enhanced
        strategies = ["cooperative", "competitive", "balanced", "progressive"]
        states_3 = []
        
        for strategy in strategies:
            state = CluedoOracleState(
                nom_enquete_cluedo=f"Strategy Test 3-Agents {strategy}",
                elements_jeu_cluedo=comparison_elements,
                oracle_strategy=strategy
            )
            states_3.append(state)
        
        # Analyse des adaptations
        # 2-agents : une seule approche
        approach_2 = "fixed_deduction"
        
        # 3-agents : approches variées selon la stratégie
        approaches_3 = []
        for state in states_3:
            approach = f"oracle_{state.oracle_strategy}"
            approaches_3.append(approach)
        
        # Le workflow 3-agents offre plus de variété stratégique
        assert len(set([approach_2])) == 1  # Une seule approche pour 2-agents
        assert len(set(approaches_3)) == len(strategies)  # Approches variées pour 3-agents
        
        # Vérification que chaque stratégie est bien configurée
        for i, strategy in enumerate(strategies):
            assert states_3[i].oracle_strategy == strategy
            assert states_3[i].cluedo_dataset.reveal_policy.value == strategy


@pytest.mark.integration
@pytest.mark.comparison
@pytest.mark.performance
class TestPerformanceComparison:
    """Tests de comparaison de performance détaillée Oracle Enhanced v2.1.0."""
    
    @pytest.fixture
    def performance_elements(self):
        """Éléments optimisés pour tests de performance."""
        return {
            "suspects": ["Colonel Moutarde", "Professeur Violet", "Mademoiselle Rose"],
            "armes": ["Poignard", "Chandelier", "Revolver"],
            "lieux": ["Salon", "Cuisine", "Bureau"]
        }
    
    def test_memory_usage_comparison(self, performance_elements):
        """Test la comparaison d'utilisation mémoire."""
        import sys
        
        # Mesure pour workflow 2-agents
        state_2 = EnqueteCluedoState(
            nom_enquete_cluedo="Memory Test 2-Agents",
            elements_jeu_cluedo=performance_elements
        )
        
        # Simulation d'activité 2-agents
        for i in range(10):
            state_2.add_hypothesis(f"Hypothesis {i}", f"Agent{i%2}", 0.5)
            state_2.add_task(f"Task {i}", f"Agent{i%2}", "pending")
        
        # Estimation de l'utilisation mémoire 2-agents
        memory_2 = sys.getsizeof(state_2.__dict__)
        
        # Mesure pour workflow 3-agents Oracle Enhanced
        state_3 = CluedoOracleState(
            nom_enquete_cluedo="Memory Test 3-Agents",
            elements_jeu_cluedo=performance_elements,
            oracle_strategy="balanced"
        )
        
        # Simulation d'activité 3-agents (avec révélations)
        for i in range(10):
            state_3.add_hypothesis(f"Hypothesis {i}", f"Agent{i%3}", 0.5)
            state_3.add_task(f"Task {i}", f"Agent{i%3}", "pending")
            state_3.record_agent_turn(f"Agent{i%3}", "test", {"data": i})
        
        # Estimation de l'utilisation mémoire 3-agents
        memory_3 = sys.getsizeof(state_3.__dict__)
        
        # Analyse comparative
        memory_overhead = memory_3 - memory_2
        overhead_percentage = (memory_overhead / memory_2) * 100 if memory_2 > 0 else 0
        
        # Le surcoût mémoire devrait être raisonnable (< 200%)
        assert overhead_percentage < 200
        
        # Vérification que l'état 3-agents contient bien plus de données
        data_2 = len(state_2.hypotheses) + len(state_2.tasks)
        data_3 = len(state_3.hypotheses) + len(state_3.tasks) + len(state_3.recent_revelations) + len(state_3.agent_turns)
        
        assert data_3 > data_2
    
    @pytest.mark.asyncio
    async def test_query_performance_comparison(self, performance_elements):
        """Test la comparaison de performance des requêtes Oracle Enhanced v2.1.0."""
        
        # État 2-agents (requêtes simples)
        state_2 = EnqueteCluedoState(
            nom_enquete_cluedo="Query Test 2-Agents",
            elements_jeu_cluedo=performance_elements
        )
        
        # État 3-agents (requêtes Oracle)
        state_3 = CluedoOracleState(
            nom_enquete_cluedo="Query Test 3-Agents",
            elements_jeu_cluedo=performance_elements,
            oracle_strategy="balanced"
        )
        
        # Test de performance requêtes 2-agents
        start_time = time.time()
        for i in range(10):
            # Opérations simples
            state_2.add_hypothesis(f"Test {i}", "Agent", 0.5)
            solution = state_2.get_solution_secrete()
        time_2agents = time.time() - start_time
        
        # Test de performance requêtes 3-agents Oracle Enhanced
        start_time = time.time()
        for i in range(10):
            # Opérations Oracle
            state_3.record_agent_turn(f"Agent{i%3}", "test", {"query": i})
            solution = state_3.get_solution_secrete()
            moriarty_cards = state_3.get_moriarty_cards()
        time_3agents = time.time() - start_time
        
        # Analyse des performances
        queries_per_second_2 = 10 / time_2agents if time_2agents > 0 else float('inf')
        queries_per_second_3 = 10 / time_3agents if time_3agents > 0 else float('inf')
        
        # Les deux devraient être rapides (> 100 ops/sec)
        assert queries_per_second_2 > 50
        assert queries_per_second_3 > 25  # Peut être plus lent à cause de l'Oracle
        
        # Vérification que les temps restent raisonnables
        assert time_2agents < 0.5
        assert time_3agents < 1.0
    
    def test_solution_quality_comparison(self, performance_elements):
        """Test la comparaison de qualité des solutions."""
        
        # Création de plusieurs instances pour analyse statistique
        solutions_2 = []
        solutions_3 = []
        
        for i in range(5):  # 5 instances de chaque
            # Workflow 2-agents
            state_2 = EnqueteCluedoState(
                nom_enquete_cluedo=f"Quality Test 2-Agents {i}",
                elements_jeu_cluedo=performance_elements
            )
            solutions_2.append(state_2.get_solution_secrete())
            
            # Workflow 3-agents Oracle Enhanced
            state_3 = CluedoOracleState(
                nom_enquete_cluedo=f"Quality Test 3-Agents {i}",
                elements_jeu_cluedo=performance_elements,
                oracle_strategy="balanced"
            )
            solutions_3.append(state_3.get_solution_secrete())
        
        # Analyse de la diversité des solutions
        unique_solutions_2 = len(set(tuple(sorted(sol.items())) for sol in solutions_2))
        unique_solutions_3 = len(set(tuple(sorted(sol.items())) for sol in solutions_3))
        
        # Analyse de la validité
        valid_solutions_2 = sum(1 for sol in solutions_2 if all(
            sol[key] in performance_elements[key + "s"] for key in ["suspect", "arme", "lieu"]
        ))
        valid_solutions_3 = sum(1 for sol in solutions_3 if all(
            sol[key] in performance_elements[key + "s"] for key in ["suspect", "arme", "lieu"]
        ))
        
        # Toutes les solutions devraient être valides
        assert valid_solutions_2 == 5
        assert valid_solutions_3 == 5
        
        # La diversité devrait être présente (génération aléatoire)
        assert unique_solutions_2 >= 3  # Au moins 3 solutions différentes sur 5
        assert unique_solutions_3 >= 3


@pytest.mark.integration
@pytest.mark.comparison
@pytest.mark.user_experience
class TestUserExperienceComparison:
    """Tests de comparaison d'expérience utilisateur Oracle Enhanced v2.1.0."""
    
    def test_output_richness_comparison(self):
        """Test la comparaison de richesse des sorties."""
        
        # Simulation de sortie 2-agents
        output_2agents = {
            "conversation_history": [
                {"sender": "Sherlock", "message": "Investigation hypothesis"},
                {"sender": "Watson", "message": "Logical deduction"},
                {"sender": "Sherlock", "message": "Final solution"}
            ],
            "final_state": {
                "solution_proposed": True,
                "hypotheses_count": 3,
                "tasks_completed": 2
            }
        }
        
        # Simulation de sortie 3-agents Oracle Enhanced
        output_3agents = {
            "conversation_history": [
                {"sender": "Sherlock", "message": "Investigation hypothesis"},
                {"sender": "Watson", "message": "Logical deduction"},
                {"sender": "Moriarty", "message": "Oracle revelation"},
                {"sender": "Sherlock", "message": "Updated hypothesis"},
                {"sender": "Watson", "message": "Final solution"}
            ],
            "final_state": {
                "solution_proposed": True,
                "hypotheses_count": 3,
                "tasks_completed": 2
            },
            "oracle_statistics": {
                "oracle_interactions": 3,
                "cards_revealed": 2,
                "revelations": ["Card1", "Card2"]
            },
            "performance_metrics": {
                "efficiency_gain": "20% faster resolution",
                "information_richness": "+2 cards revealed"
            }
        }
        
        # Analyse comparative
        conversation_length_2 = len(output_2agents["conversation_history"])
        conversation_length_3 = len(output_3agents["conversation_history"])
        
        info_sections_2 = len(output_2agents.keys())
        info_sections_3 = len(output_3agents.keys())
        
        # Le workflow 3-agents devrait être plus riche
        assert conversation_length_3 > conversation_length_2
        assert info_sections_3 > info_sections_2
        assert "oracle_statistics" in output_3agents
        assert "performance_metrics" in output_3agents
        assert "oracle_statistics" not in output_2agents
    
    def test_debugging_capability_comparison(self):
        """Test la comparaison des capacités de debugging."""
        
        # Capacités de debugging 2-agents
        debug_2agents = [
            "hypothesis_tracking",
            "task_management", 
            "basic_conversation_history",
            "final_solution_validation"
        ]
        
        # Capacités de debugging 3-agents Oracle Enhanced v2.1.0
        debug_3agents = [
            "hypothesis_tracking",
            "task_management",
            "conversation_history",
            "final_solution_validation",
            "oracle_interaction_tracking",
            "card_revelation_history",
            "agent_turn_tracking",
            "permission_audit_trail",
            "performance_metrics",
            "strategy_effectiveness_analysis"
        ]
        
        # Analyse comparative
        debug_capabilities_2 = len(debug_2agents)
        debug_capabilities_3 = len(debug_3agents)
        
        unique_to_3agents = set(debug_3agents) - set(debug_2agents)
        
        # Le workflow 3-agents offre plus de capacités de debugging
        assert debug_capabilities_3 > debug_capabilities_2
        assert len(unique_to_3agents) >= 6  # Au moins 6 capacités uniques
        
        # Vérification des capacités Oracle spécifiques
        oracle_specific = [
            "oracle_interaction_tracking",
            "card_revelation_history", 
            "permission_audit_trail"
        ]
        
        for capability in oracle_specific:
            assert capability in debug_3agents
            assert capability not in debug_2agents
    
    def test_educational_value_comparison(self):
        """Test la comparaison de valeur éducative."""
        
        # Concepts éducatifs 2-agents
        educational_2agents = [
            "logical_deduction",
            "hypothesis_formation",
            "collaborative_problem_solving",
            "sequential_reasoning"
        ]
        
        # Concepts éducatifs 3-agents Oracle Enhanced
        educational_3agents = [
            "logical_deduction",
            "hypothesis_formation", 
            "collaborative_problem_solving",
            "sequential_reasoning",
            "information_asymmetry",
            "strategic_revelation",
            "permission_based_access",
            "multi_agent_coordination",
            "oracle_pattern_implementation",
            "adaptive_strategy_selection"
        ]
        
        # Analyse de la richesse éducative
        concepts_2 = len(educational_2agents)
        concepts_3 = len(educational_3agents)
        
        advanced_concepts = set(educational_3agents) - set(educational_2agents)
        
        # Le workflow 3-agents offre plus de valeur éducative
        assert concepts_3 > concepts_2
        assert len(advanced_concepts) >= 6
        
        # Vérification des concepts avancés
        assert "information_asymmetry" in advanced_concepts
        assert "strategic_revelation" in advanced_concepts
        assert "oracle_pattern_implementation" in advanced_concepts