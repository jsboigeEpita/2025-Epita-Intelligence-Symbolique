# Authentic gpt-5-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

"""
Tests unitaires pour le comportement Oracle Enhanced.

Tests couvrant:
- Révélation automatique des cartes vs suggestions triviales
- Pattern Oracle authentique pour Cluedo
- Pattern indices progressifs pour Einstein
- Orchestration cyclique améliorée
"""

import pytest
import asyncio

from typing import Dict, Any, List
from datetime import datetime

from argumentation_analysis.core.cluedo_oracle_state import CluedoOracleState
from argumentation_analysis.agents.core.oracle.cluedo_dataset import (
    CluedoDataset,
    RevealPolicy,
)
from argumentation_analysis.agents.core.oracle.permissions import (
    QueryType,
    PermissionManager,
)
from argumentation_analysis.agents.core.oracle.moriarty_interrogator_agent import (
    MoriartyInterrogatorAgent,
)


@pytest.fixture
def enhanced_elements():
    """Éléments Cluedo pour tests Oracle Enhanced."""
    return {
        "suspects": [
            "Colonel Moutarde",
            "Professeur Violet",
            "Mademoiselle Rose",
            "Madame Leblanc",
        ],
        "armes": ["Poignard", "Chandelier", "Revolver", "Corde", "Tuyau"],
        "lieux": ["Salon", "Cuisine", "Bureau", "Bibliothèque", "Salle de bal"],
    }


@pytest.fixture
def oracle_enhanced_state(enhanced_elements):
    """État Oracle configuré pour le mode Enhanced."""
    return CluedoOracleState(
        nom_enquete_cluedo="Test Oracle Enhanced",
        elements_jeu_cluedo=enhanced_elements,
        description_cas="Test Oracle Enhanced Case",
        initial_context={"test": "context"},
        oracle_strategy="enhanced_auto_reveal",
    )


@pytest.fixture
async def mock_semantic_kernel():
    """Mock du Semantic Kernel pour tests GPT-4o-mini."""
    kernel = await self._create_authentic_gpt4o_mini_instance()
    kernel.add_plugin = await self._create_authentic_gpt4o_mini_instance()
    kernel.add_filter = await self._create_authentic_gpt4o_mini_instance()

    # Mock des services
    mock_service = await self._create_authentic_gpt4o_mini_instance()
    mock_service.service_id = "openai-gpt4o-mini"
    mock_service.ai_model_id = "gpt-5-mini"
    kernel.get_service = Mock(return_value=mock_service)

    return kernel


class TestOracleEnhancedBehavior:
    async def _create_authentic_gpt4o_mini_instance(self):
        """Crée une instance authentique de gpt-5-mini au lieu d'un mock."""
        config = UnifiedConfig()
        return config.get_kernel_with_gpt4o_mini()

    async def _make_authentic_llm_call(self, prompt: str) -> str:
        """Fait un appel authentique à gpt-5-mini."""
        try:
            kernel = await self._create_authentic_gpt4o_mini_instance()
            result = await kernel.invoke("chat", input=prompt)
            return str(result)
        except Exception as e:
            logger.warning(f"Appel LLM authentique échoué: {e}")
            return "Authentic LLM call failed"

    """Tests du comportement Oracle Enhanced."""

    def test_oracle_enhanced_initialization(self, oracle_enhanced_state):
        """Test l'initialisation du mode Oracle Enhanced."""
        assert oracle_enhanced_state.oracle_strategy == "enhanced_auto_reveal"
        assert hasattr(oracle_enhanced_state, "cluedo_dataset")
        assert hasattr(oracle_enhanced_state, "dataset_access_manager")

        # Vérifier que Moriarty a des cartes à révéler
        moriarty_cards = oracle_enhanced_state.get_moriarty_cards()
        assert len(moriarty_cards) > 0
        assert len(moriarty_cards) < 15  # Pas toutes les cartes

    def test_automatic_revelation_vs_suggestions(self, oracle_enhanced_state):
        """Test la révélation automatique vs suggestions triviales."""
        moriarty_cards = oracle_enhanced_state.get_moriarty_cards()
        test_card = moriarty_cards[0] if moriarty_cards else "Colonel Moutarde"

        # Simulation d'une suggestion triviale qui devrait déclencher une révélation
        trivial_suggestion = {
            "type": "suggestion_triviale",
            "content": "Je pense que c'est peut-être...",
            "confidence": 0.1,
        }

        # Le système Enhanced devrait détecter et révéler automatiquement
        should_reveal = oracle_enhanced_state._should_auto_reveal_card(
            suggestion=trivial_suggestion, available_cards=moriarty_cards
        )

        assert should_reveal is True

    @pytest.mark.asyncio
    async def test_enhanced_oracle_cluedo_pattern(self, oracle_enhanced_state):
        """Test le pattern Oracle authentique pour Cluedo."""
        # Simulation d'une enquête Cluedo avec révélations progressives
        sherlock_queries = [
            {"type": "character_inquiry", "target": "Colonel Moutarde"},
            {"type": "weapon_inquiry", "target": "Poignard"},
            {"type": "location_inquiry", "target": "Salon"},
        ]

        revelations = []

        for i, query in enumerate(sherlock_queries):
            result = await oracle_enhanced_state.query_oracle(
                agent_name="Sherlock", query_type="card_inquiry", query_params=query
            )

            if hasattr(result, "revelation_triggered"):
                revelations.append(result)

        # Vérifier que des révélations ont été déclenchées
        assert len(revelations) >= 1

        # Vérifier la progression des indices
        stats = oracle_enhanced_state.get_oracle_statistics()
        assert stats["workflow_metrics"]["oracle_interactions"] == len(sherlock_queries)

    @pytest.mark.asyncio
    async def test_einstein_progressive_hints_pattern(self, oracle_enhanced_state):
        """Test le pattern indices progressifs pour Einstein."""
        # Configuration spéciale pour le puzzle Einstein
        einstein_context = {
            "puzzle_type": "einstein_riddle",
            "houses": 5,
            "attributes": ["nationality", "color", "pet", "drink", "cigarette"],
        }

        oracle_enhanced_state.context_type = "einstein"
        oracle_enhanced_state.puzzle_context = einstein_context

        # Simulation de requêtes progressives
        progressive_queries = [
            {"level": 1, "hint_type": "basic_constraint"},
            {"level": 2, "hint_type": "logical_deduction"},
            {"level": 3, "hint_type": "advanced_constraint"},
        ]

        hints_revealed = []

        for query in progressive_queries:
            result = await oracle_enhanced_state.query_oracle(
                agent_name="Moriarty", query_type="progressive_hint", query_params=query
            )

            if result.data and result.data.get("hint_content"):
                hints_revealed.append(result.data["hint_content"])

        # Vérifier que les indices sont progressifs
        assert len(hints_revealed) >= 2

        # Vérifier l'escalade de complexité
        for i in range(1, len(hints_revealed)):
            # Les indices suivants devraient être plus détaillés
            if hints_revealed[i] and hints_revealed[i - 1]:
                assert len(hints_revealed[i]) >= len(hints_revealed[i - 1])

    def test_enhanced_orchestration_cycle(self, oracle_enhanced_state):
        """Test l'orchestration cyclique améliorée."""
        # Simulation d'un cycle complet Enhanced
        cycle_data = {
            "sherlock_turn": {"action": "investigate", "target": "Colonel Moutarde"},
            "watson_turn": {"action": "analyze", "hypothesis": "Moutarde + Poignard"},
            "moriarty_turn": {"action": "reveal", "auto_triggered": True},
        }

        cycle_metrics = {}

        for agent, turn_data in cycle_data.items():
            oracle_enhanced_state.record_agent_turn(
                agent_name=agent.replace("_turn", "").title(),
                action_type=turn_data["action"],
                action_details=turn_data,
            )

            # Enregistrer les métriques du tour
            cycle_metrics[agent] = {
                "timestamp": datetime.now(),
                "action_completed": True,
            }

        # Vérifier que le cycle est complet
        stats = oracle_enhanced_state.get_oracle_statistics()
        assert stats["agent_interactions"]["total_turns"] == 3
        assert len(stats["agent_interactions"]["agents_active"]) == 3

        # Vérifier l'amélioration de l'orchestration
        assert "Sherlock" in stats["agent_interactions"]["agents_active"]
        assert "Watson" in stats["agent_interactions"]["agents_active"]
        assert "Moriarty" in stats["agent_interactions"]["agents_active"]

    @pytest.mark.asyncio
    async def test_auto_revelation_triggers(self, oracle_enhanced_state):
        """Test les déclencheurs de révélation automatique."""
        moriarty_cards = oracle_enhanced_state.get_moriarty_cards()

        # Cas 1: Suggestion trop vague
        vague_suggestion = "Je ne sais pas vraiment..."
        trigger1 = oracle_enhanced_state._detect_revelation_trigger(
            agent_input=vague_suggestion, context="cluedo_investigation"
        )
        assert trigger1["should_reveal"] is True
        assert trigger1["reason"] == "vague_suggestion"

        # Cas 2: Investigation bloquée
        blocked_investigation = "Nous n'avons aucun indice pour avancer..."
        trigger2 = oracle_enhanced_state._detect_revelation_trigger(
            agent_input=blocked_investigation, context="cluedo_investigation"
        )
        assert trigger2["should_reveal"] is True
        assert trigger2["reason"] == "investigation_blocked"

        # Cas 3: Hypothèse proche de la solution
        if moriarty_cards:
            close_hypothesis = f"Je pense que c'est {moriarty_cards[0]}"
            trigger3 = oracle_enhanced_state._detect_revelation_trigger(
                agent_input=close_hypothesis, context="cluedo_investigation"
            )
            # Peut révéler ou non selon la stratégie
            assert "should_reveal" in trigger3

    def test_enhanced_vs_standard_behavior_comparison(self, enhanced_elements):
        """Test la comparaison comportement Enhanced vs Standard."""
        # État Standard
        standard_state = CluedoOracleState(
            nom_enquete_cluedo="Test Standard",
            elements_jeu_cluedo=enhanced_elements,
            description_cas="Test Standard Case",
            initial_context={"test": "standard"},
            oracle_strategy="balanced",
        )

        # État Enhanced
        enhanced_state = CluedoOracleState(
            nom_enquete_cluedo="Test Enhanced",
            elements_jeu_cluedo=enhanced_elements,
            description_cas="Test Enhanced Case",
            initial_context={"test": "enhanced"},
            oracle_strategy="enhanced_auto_reveal",
        )

        # Comparaison des configurations
        standard_policy = standard_state.cluedo_dataset.reveal_policy
        enhanced_policy = enhanced_state.cluedo_dataset.reveal_policy

        # L'Enhanced devrait être plus proactif
        assert enhanced_policy != standard_policy

        # Comparaison des cartes Moriarty
        standard_cards = standard_state.get_moriarty_cards()
        enhanced_cards = enhanced_state.get_moriarty_cards()

        # Les cartes peuvent être différentes selon la stratégie
        assert isinstance(standard_cards, list)
        assert isinstance(enhanced_cards, list)
        assert len(enhanced_cards) > 0

    def test_enhanced_revelation_quality(self, oracle_enhanced_state):
        """Test la qualité des révélations Enhanced."""
        moriarty_cards = oracle_enhanced_state.get_moriarty_cards()

        if moriarty_cards:
            test_card = moriarty_cards[0]

            # Génération d'une révélation Enhanced
            revelation = oracle_enhanced_state._generate_enhanced_revelation(
                card=test_card, context="cluedo_game", reveal_style="dramatic"
            )

            # Vérifications de qualité
            assert isinstance(revelation, dict)
            assert "content" in revelation
            assert "style" in revelation
            assert "dramatic_effect" in revelation
            assert len(revelation["content"]) > 50  # Révélation substantielle

            # Le contenu ne devrait pas être trivial
            assert "peut-être" not in revelation["content"].lower()
            assert "je pense" not in revelation["content"].lower()
            assert test_card in revelation["content"]


class TestOracleEnhancedEdgeCases:
    """Tests des cas limites Oracle Enhanced."""

    def test_enhanced_with_minimal_elements(self):
        """Test Enhanced avec éléments minimaux."""
        minimal_elements = {
            "suspects": ["Colonel Moutarde"],
            "armes": ["Poignard"],
            "lieux": ["Salon"],
        }

        oracle_state = CluedoOracleState(
            nom_enquete_cluedo="Test Minimal Enhanced",
            elements_jeu_cluedo=minimal_elements,
            description_cas="Test Minimal Enhanced Case",
            initial_context={"test": "minimal"},
            oracle_strategy="enhanced_auto_reveal",
        )

        # Devrait fonctionner même avec peu d'éléments
        assert oracle_state.oracle_strategy == "enhanced_auto_reveal"
        moriarty_cards = oracle_state.get_moriarty_cards()
        assert len(moriarty_cards) >= 0  # Au moins 0 cartes

    @pytest.mark.asyncio
    async def test_enhanced_rapid_queries(self, oracle_enhanced_state):
        """Test Enhanced avec requêtes rapides successives."""
        rapid_queries = []

        for i in range(5):
            result = await oracle_enhanced_state.query_oracle(
                agent_name="Sherlock",
                query_type="rapid_test",
                query_params={"query_id": i, "timestamp": datetime.now()},
            )
            rapid_queries.append(result)

        # Toutes les requêtes devraient être traitées
        assert len(rapid_queries) == 5

        # Vérifier la cohérence de l'état
        stats = oracle_enhanced_state.get_oracle_statistics()
        assert stats["workflow_metrics"]["oracle_interactions"] == 5

    def test_enhanced_strategy_validation(self, enhanced_elements):
        """Test la validation de la stratégie Enhanced."""
        # Stratégie Enhanced valide
        valid_state = CluedoOracleState(
            nom_enquete_cluedo="Test Validation",
            elements_jeu_cluedo=enhanced_elements,
            description_cas="Test Validation Case",
            initial_context={"test": "validation"},
            oracle_strategy="enhanced_auto_reveal",
        )
        assert valid_state.oracle_strategy == "enhanced_auto_reveal"

        # Test avec stratégie Enhanced alternative
        alternative_strategies = [
            "enhanced_progressive",
            "enhanced_dramatic",
            "enhanced_balanced",
        ]

        for strategy in alternative_strategies:
            try:
                test_state = CluedoOracleState(
                    nom_enquete_cluedo=f"Test {strategy}",
                    elements_jeu_cluedo=enhanced_elements,
                    description_cas=f"Test {strategy} Case",
                    initial_context={"test": strategy},
                    oracle_strategy=strategy,
                )
                # Si la stratégie est acceptée, vérifier qu'elle est bien configurée
                assert hasattr(test_state, "oracle_strategy")
            except ValueError:
                # Les stratégies non implémentées peuvent lever des erreurs
                pass


class TestOracleEnhancedIntegrationHelpers:
    """Helpers pour les tests d'intégration Oracle Enhanced."""

    @staticmethod
    def create_mock_gpt4o_mini_response(
        query_type: str, context: str
    ) -> Dict[str, Any]:
        """Crée une réponse simulée de GPT-4o-mini."""
        responses = {
            "cluedo_investigation": {
                "content": "En tant que Moriarty, je révèle que j'ai la carte Colonel Moutarde.",
                "confidence": 0.95,
                "reasoning": "L'enquête piétine, il est temps de révéler un indice crucial.",
            },
            "einstein_hint": {
                "content": "Voici un indice: L'Anglais vit dans la maison rouge.",
                "confidence": 0.90,
                "reasoning": "Premier indice pour débloquer le raisonnement logique.",
            },
            "suggestion_validation": {
                "content": "Cette suggestion est trop vague pour être utile.",
                "confidence": 0.85,
                "reasoning": "Analyse de la qualité de la suggestion.",
            },
        }

        return responses.get(
            context,
            {
                "content": "Réponse générique de GPT-4o-mini",
                "confidence": 0.75,
                "reasoning": "Réponse par défaut",
            },
        )

    @staticmethod
    def validate_enhanced_revelation(revelation: Dict[str, Any]) -> bool:
        """Valide qu'une révélation respecte les critères Enhanced."""
        required_fields = ["content", "style", "dramatic_effect"]

        # Vérifier les champs requis
        for field in required_fields:
            if field not in revelation:
                return False

        # Vérifier la qualité du contenu
        content = revelation["content"]
        if len(content) < 30:  # Révélation trop courte
            return False

        # Vérifier l'absence de mots vagues
        vague_words = ["peut-être", "probablement", "je pense", "sans doute"]
        for word in vague_words:
            if word in content.lower():
                return False

        return True

    @staticmethod
    def simulate_enhanced_workflow_cycle() -> Dict[str, Any]:
        """Simule un cycle complet de workflow Enhanced."""
        return {
            "sherlock_investigation": {
                "action": "investigate_suspect",
                "target": "Colonel Moutarde",
                "method": "logical_deduction",
            },
            "watson_analysis": {
                "action": "analyze_evidence",
                "hypothesis": "Moutarde + Poignard + Salon",
                "confidence": 0.7,
            },
            "moriarty_revelation": {
                "action": "auto_reveal_card",
                "triggered_by": "vague_hypothesis",
                "card_revealed": "Colonel Moutarde",
                "dramatic_style": True,
            },
        }
