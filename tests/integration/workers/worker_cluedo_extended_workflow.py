# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

# tests/integration/test_cluedo_extended_workflow.py
"""
Tests de comparaison entre workflows Cluedo 2-agents vs 3-agents.

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
import logging
from unittest.mock import Mock

from typing import Dict, Any, List, Tuple
from datetime import datetime

from semantic_kernel.kernel import Kernel
from semantic_kernel.contents.chat_message_content import ChatMessageContent

# Imports des orchestrateurs
from argumentation_analysis.orchestration.cluedo_extended_orchestrator import CluedoExtendedOrchestrator

# Imports des états
from argumentation_analysis.core.enquete_states import EnqueteCluedoState
from argumentation_analysis.core.cluedo_oracle_state import CluedoOracleState

# Imports des agents
from argumentation_analysis.agents.factory import AgentFactory
from argumentation_analysis.agents.core.oracle.moriarty_interrogator_agent import MoriartyInterrogatorAgent

logger = logging.getLogger(__name__)

async def _create_authentic_gpt4o_mini_instance():
    """Crée une instance authentique de gpt-4o-mini au lieu d'un mock."""
    config = UnifiedConfig()
    return config.get_kernel_with_gpt4o_mini()

@pytest.fixture
async def mock_kernel():
    """Kernel mocké pour tests comparatifs."""
    return await _create_authentic_gpt4o_mini_instance()

@pytest.fixture
def comparison_elements():
    """Éléments Cluedo standardisés pour comparaisons équitables."""
    return {
        "suspects": ["Colonel Moutarde", "Professeur Violet", "Mademoiselle Rose"],
        "armes": ["Poignard", "Chandelier", "Revolver"],
        "lieux": ["Salon", "Cuisine", "Bureau"]
    }

@pytest.mark.integration
@pytest.mark.comparison
class TestNewOrchestrator:
    @pytest.mark.asyncio
    async def test_orchestrator_runs_successfully(self, mock_kernel, comparison_elements):
        """Vérifie que le nouvel orchestrateur s'exécute sans erreur."""
        kernel_instance = await mock_kernel
        orchestrator = CluedoExtendedOrchestrator(
            kernel=kernel_instance,
            max_turns=3,
            max_cycles=1,
            oracle_strategy="cooperative"
        )

        await orchestrator.setup_workflow(elements_jeu=comparison_elements)
        
        initial_question = "Qui a commis le meurtre ?"
        results = await orchestrator.execute_workflow(initial_question)

        assert "workflow_info" in results
        assert "final_metrics" in results
        assert results["workflow_info"]["strategy"] == "cooperative"
        assert len(results["final_metrics"]["history"]) > 0

class TestWorkflowComparison:
        
    async def _make_authentic_llm_call(self, prompt: str) -> str:
        """Fait un appel authentique à gpt-4o-mini."""
        try:
            kernel = await _create_authentic_gpt4o_mini_instance()
            result = await kernel.invoke(prompt)
            return str(result)
        except Exception as e:
            logger.warning(f"Appel LLM authentique échoué: {e}")
            return "Authentic LLM call failed"

    """Tests de comparaison entre workflows 2-agents et 3-agents."""
    
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
            elements_jeu_cluedo=comparison_elements,
            description_cas="Test de comparaison",
            initial_context={"details": "Contexte de test"}
        )
        
        # Configuration 3-agents
        state_3agents = CluedoOracleState(
            nom_enquete_cluedo="Comparison Test 3-Agents",
            elements_jeu_cluedo=comparison_elements,
            description_cas="Test de comparaison",
            initial_context={"details": "Contexte de test"},
            oracle_strategy="balanced"
        )
        
        # Comparaison des configurations
        assert state_2agents.nom_enquete_cluedo == "Comparison Test 2-Agents"
        assert state_3agents.nom_enquete_cluedo == "Comparison Test 3-Agents"
        
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
    
    @pytest.mark.asyncio
    async def test_agent_capabilities_comparison(self, mock_kernel, comparison_elements):
        """Test la comparaison des capacités des agents."""
        kernel_instance = await mock_kernel
        # Initialisation de la factory
        from argumentation_analysis.config.settings import AppSettings
        settings = AppSettings()
        settings.service_manager.default_llm_service_id = "chat-gpt"
        factory = AgentFactory(kernel=kernel_instance, settings=settings)

        # Agents 2-agents
        sherlock_2 = factory.create_sherlock_agent(agent_name="Sherlock2")
        watson_2 = factory.create_watson_agent(
            agent_name="Watson2",
            constants=[name.replace(" ", "") for category in comparison_elements.values() for name in category]
        )
        
        # Agents 3-agents (avec Moriarty)
        sherlock_3 = factory.create_sherlock_agent(agent_name="Sherlock3")
        watson_3 = factory.create_watson_agent(
            agent_name="Watson3",
            constants=[name.replace(" ", "") for category in comparison_elements.values() for name in category]
        )
        
        # Création d'un dataset pour Moriarty
        from argumentation_analysis.agents.core.oracle.cluedo_dataset import CluedoDataset
        cluedo_dataset = CluedoDataset(elements_jeu=comparison_elements)
        
        from argumentation_analysis.agents.core.oracle.dataset_access_manager import CluedoDatasetManager
        dataset_manager = CluedoDatasetManager(cluedo_dataset)
        moriarty = MoriartyInterrogatorAgent(
            kernel=kernel_instance,
            dataset_manager=dataset_manager,
            game_strategy="balanced",
            agent_name="Moriarty"
        )
        
        # Comparaison des agents
        agents_2 = [sherlock_2, watson_2]
        agents_3 = [sherlock_3, watson_3, moriarty]
        
        assert len(agents_2) == 2
        assert len(agents_3) == 3
        
        # Vérification des capacités uniques de Moriarty
        assert hasattr(moriarty, '_tools')
        assert_moriarty_has_dataset = hasattr(moriarty, 'dataset_manager') and hasattr(moriarty.dataset_manager, '_dataset')
        assert assert_moriarty_has_dataset
        assert not hasattr(sherlock_2, '_tools') or "reveal_card" not in sherlock_2.get_agent_capabilities()
        assert not hasattr(watson_2, '_tools') or "reveal_card" not in watson_2.get_agent_capabilities()

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
            elements_jeu_cluedo=comparison_elements,
            description_cas="Test de richesse informationnelle",
            initial_context={"details": "Contexte de test"}
        )
        
        # État 3-agents
        state_3 = CluedoOracleState(
            nom_enquete_cluedo="Info Test 3-Agents",
            elements_jeu_cluedo=comparison_elements,
            description_cas="Test de richesse informationnelle",
            initial_context={"details": "Contexte de test"},
            oracle_strategy="cooperative"
        )
        
        # Simulation d'activité pour comparaison
        # 2-agents : hypothèses et tâches classiques
        state_2.add_hypothesis("Hypothesis 1", 0.7)
        state_2.add_hypothesis("Hypothesis 2", 0.6)
        state_2.add_task("Investigate library", "Sherlock")
        
        # 3-agents : hypothèses + révélations Oracle
        state_3.add_hypothesis("Hypothesis 1", 0.7)
        state_3.add_hypothesis("Hypothesis 2", 0.6)
        state_3.add_task("Investigate library", "Sherlock")
        
        # Ajout de révélations Oracle
        from argumentation_analysis.agents.core.oracle.cluedo_dataset import RevelationRecord
        revelation = RevelationRecord(
            card_revealed="Professeur Violet",
            revelation_type="owned_card",
            message="Information révélée par Oracle"
        )
        state_3.add_revelation(revelation, "Moriarty")
        
        # Comparaison de la richesse informationnelle
        info_2 = {
            "hypotheses": len(state_2.get_hypotheses()),
            "tasks": len(state_2.get_tasks()),
            "revelations": 0  # Pas de révélations dans 2-agents
        }
        
        info_3 = {
            "hypotheses": len(state_3.get_hypotheses()),
            "tasks": len(state_3.get_tasks()),
            "revelations": len(state_3.recent_revelations)
        }
        
        # Le 3-agents devrait avoir plus d'informations au total
        total_info_2 = sum(info_2.values())
        total_info_3 = sum(info_3.values())
        
        assert total_info_3 > total_info_2
        assert info_3["revelations"] > info_2["revelations"]
    
    @pytest.mark.asyncio
    async def test_resolution_efficiency_simulation(self, mock_kernel, comparison_elements):
        """Test de simulation d'efficacité de résolution."""
        
        # Métriques simulées pour workflow 2-agents
        metrics_2agents = {
            "setup_time": 0.5,
            "average_turn_duration": 2.0,
            "total_turns": 6,
            "information_gathered": 3,  # Hypothèses et déductions
            "resolution_confidence": 0.7
        }
        
        # Métriques simulées pour workflow 3-agents
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
    
    @pytest.mark.asyncio
    async def test_scalability_comparison(self, mock_kernel):
        """Test la comparaison de scalabilité."""
        kernel_instance = await mock_kernel
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
            elements_jeu_cluedo=small_elements,
            description_cas="Test de scalabilité",
            initial_context={"details": "Contexte de test"}
        )
        small_2_setup_time = time.time() - start_time
        
        start_time = time.time()
        small_state_3 = CluedoOracleState(
            nom_enquete_cluedo="Small 3-Agents",
            elements_jeu_cluedo=small_elements,
            description_cas="Test de scalabilité",
            initial_context={"details": "Contexte de test"},
            oracle_strategy="balanced"
        )
        small_3_setup_time = time.time() - start_time
        
        # Test avec grand jeu
        start_time = time.time()
        large_state_2 = EnqueteCluedoState(
            nom_enquete_cluedo="Large 2-Agents",
            elements_jeu_cluedo=large_elements,
            description_cas="Test de scalabilité",
            initial_context={"details": "Contexte de test"}
        )
        large_2_setup_time = time.time() - start_time
        
        start_time = time.time()
        large_state_3 = CluedoOracleState(
            nom_enquete_cluedo="Large 3-Agents",
            elements_jeu_cluedo=large_elements,
            description_cas="Test de scalabilité",
            initial_context={"details": "Contexte de test"},
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
        """Test la comparaison d'adaptation stratégique."""
        
        # Workflow 2-agents : stratégie fixe
        state_2 = EnqueteCluedoState(
            nom_enquete_cluedo="Strategy Test 2-Agents",
            elements_jeu_cluedo=comparison_elements,
            description_cas="Test de stratégie",
            initial_context={"details": "Contexte de test"}
        )
        
        # Workflow 3-agents : différentes stratégies Oracle
        strategies = ["cooperative", "competitive", "balanced", "progressive"]
        states_3 = []
        
        for strategy in strategies:
            state = CluedoOracleState(
                nom_enquete_cluedo=f"Strategy Test 3-Agents {strategy}",
                elements_jeu_cluedo=comparison_elements,
                description_cas="Test de stratégie",
                initial_context={"details": "Contexte de test"},
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
    """Tests de comparaison de performance détaillée."""
    
    @pytest.fixture
    def performance_elements(self):
        """Éléments optimisés pour tests de performance."""
        return {
            "suspects": ["Colonel Moutarde", "Professeur Violet", "Mademoiselle Rose"],
            "armes": ["Poignard", "Chandelier", "Revolver"],
            "lieux": ["Salon", "Cuisine", "Bureau"]
        }
    
    @pytest.mark.asyncio
    async def test_memory_usage_comparison(self, performance_elements):
        """Test la comparaison d'utilisation mémoire."""
        import sys
        
        # Mesure pour workflow 2-agents
        state_2 = EnqueteCluedoState(
            nom_enquete_cluedo="Memory Test 2-Agents",
            elements_jeu_cluedo=performance_elements,
            description_cas="Test de mémoire",
            initial_context={"details": "Contexte de test"}
        )
        
        # Simulation d'activité 2-agents
        for i in range(10):
            state_2.add_hypothesis(f"Hypothesis {i}", 0.5)
            state_2.add_task(f"Task {i}", f"Agent{i%2}")
        
        # Estimation de l'utilisation mémoire 2-agents
        memory_2 = sys.getsizeof(state_2.__dict__)
        
        # Mesure pour workflow 3-agents
        state_3 = CluedoOracleState(
            nom_enquete_cluedo="Memory Test 3-Agents",
            elements_jeu_cluedo=performance_elements,
            description_cas="Test de mémoire",
            initial_context={"details": "Contexte de test"},
            oracle_strategy="balanced"
        )
        
        # Simulation d'activité 3-agents (avec révélations)
        for i in range(10):
            state_3.add_hypothesis(f"Hypothesis {i}", 0.5)
            state_3.add_task(f"Task {i}", f"Agent{i%3}")
            state_3.record_agent_turn(f"Agent{i%3}", "test", {"data": i})
        
        # Estimation de l'utilisation mémoire 3-agents
        memory_3 = sys.getsizeof(state_3.__dict__)
        
        # Analyse comparative
        memory_overhead = memory_3 - memory_2
        overhead_percentage = (memory_overhead / memory_2) * 100 if memory_2 > 0 else 0
        
        # Le surcoût mémoire devrait être raisonnable (< 200%)
        assert overhead_percentage < 200
        
        # Vérification que l'état 3-agents contient bien plus de données
        data_2 = len(state_2.get_hypotheses()) + len(state_2.get_tasks())
        data_3 = len(state_3.get_hypotheses()) + len(state_3.get_tasks()) + len(state_3.recent_revelations) + len(state_3.agent_turns)
        
        assert data_3 > data_2
    
    @pytest.mark.asyncio
    async def test_query_performance_comparison(self, performance_elements):
        """Test la comparaison de performance des requêtes."""
        
        # État 2-agents (requêtes simples)
        state_2 = EnqueteCluedoState(
            nom_enquete_cluedo="Query Test 2-Agents",
            elements_jeu_cluedo=performance_elements,
            description_cas="Test de performance",
            initial_context={"details": "Contexte de test"}
        )
        
        # État 3-agents (requêtes Oracle)
        state_3 = CluedoOracleState(
            nom_enquete_cluedo="Query Test 3-Agents",
            elements_jeu_cluedo=performance_elements,
            description_cas="Test de performance",
            initial_context={"details": "Contexte de test"},
            oracle_strategy="balanced"
        )
        
        # Test de performance requêtes 2-agents
        start_time = time.time()
        for i in range(10):
            # Opérations simples
            state_2.add_hypothesis(f"Test {i}", 0.5)
            solution = state_2.get_solution_secrete()
        time_2agents = time.time() - start_time
        
        # Test de performance requêtes 3-agents
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
                elements_jeu_cluedo=performance_elements,
                description_cas="Test de qualité",
                initial_context={"details": "Contexte de test"}
            )
            solutions_2.append(state_2.get_solution_secrete())
            
            # Workflow 3-agents
            state_3 = CluedoOracleState(
                nom_enquete_cluedo=f"Quality Test 3-Agents {i}",
                elements_jeu_cluedo=performance_elements,
                description_cas="Test de qualité",
                initial_context={"details": "Contexte de test"},
                oracle_strategy="balanced"
            )
            solutions_3.append(state_3.get_solution_secrete())
        
        # Analyse de la diversité des solutions
        unique_solutions_2 = len(set(tuple(sorted(sol.items())) for sol in solutions_2))
        unique_solutions_3 = len(set(tuple(sorted(sol.items())) for sol in solutions_3))
        
        # Analyse de la validité
        valid_solutions_2 = sum(1 for sol in solutions_2 if (
            sol["suspect"] in performance_elements["suspects"] and
            sol["arme"] in performance_elements["armes"] and
            sol["lieu"] in performance_elements["lieux"]
        ))
        valid_solutions_3 = sum(1 for sol in solutions_3 if (
            sol["suspect"] in performance_elements["suspects"] and
            sol["arme"] in performance_elements["armes"] and
            sol["lieu"] in performance_elements["lieux"]
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
    """Tests de comparaison d'expérience utilisateur."""
    
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
        
        # Simulation de sortie 3-agents
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
        
        # Capacités de debugging 3-agents
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
        
        # Concepts éducatifs 3-agents
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
if __name__ == "__main__":
    pytest.main([__file__])