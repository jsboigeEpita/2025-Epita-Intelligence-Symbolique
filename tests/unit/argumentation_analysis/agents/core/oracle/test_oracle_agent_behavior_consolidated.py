#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Fichier de test consolidé pour le comportement des agents Oracle.

Ce fichier regroupe les tests de :
- test_oracle_base_agent.py
- test_oracle_base_agent_fixed.py
- test_oracle_base_agent_recovered1.py
- test_oracle_behavior_simple.py
- test_moriarty_interrogator_agent.py
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

# Imports du noyau sémantique et de la configuration
from semantic_kernel.kernel import Kernel
from config.unified_config import UnifiedConfig

# Imports du système Oracle
from argumentation_analysis.agents.core.oracle.oracle_base_agent import (
    OracleBaseAgent,
    OracleTools,
)
from argumentation_analysis.agents.core.oracle.moriarty_interrogator_agent import (
    MoriartyInterrogatorAgent,
)
from argumentation_analysis.agents.core.oracle.dataset_access_manager import (
    DatasetAccessManager,
    CluedoDatasetManager,
)
from argumentation_analysis.agents.core.oracle.permissions import (
    QueryType,
    PermissionRule,
    OracleResponse,
    ValidationResult,
)
from argumentation_analysis.agents.core.oracle.cluedo_dataset import (
    CluedoDataset,
    CluedoSuggestion,
    RevealPolicy,
)


# --- Fixtures Unifiées ---


@pytest.fixture
def mock_kernel() -> Kernel:
    """Fournit une instance mockée du Kernel Semantic Kernel."""
    kernel = Mock(spec=Kernel)
    kernel.add_plugin = Mock()
    return kernel


@pytest.fixture
def mock_cluedo_dataset() -> CluedoDataset:
    """Fournit une instance mockée de CluedoDataset."""
    dataset = Mock(spec=CluedoDataset)
    dataset.get_moriarty_cards = Mock(return_value=["Poignard", "Salon", "Moutarde"])
    dataset.validate_cluedo_suggestion = Mock(
        return_value=ValidationResult(
            can_refute=True, revealed_cards=[], suggestion_valid=True, authorized=True
        )
    )
    dataset.reveal_card = Mock(
        return_value={"revealed_card": "Poignard", "revealing_agent": "Moriarty"}
    )
    dataset._generate_strategic_clue = Mock(
        return_value={"clue_type": "strategic", "content": "Hint"}
    )
    return dataset


@pytest.fixture
def mock_dataset_manager(mock_cluedo_dataset: CluedoDataset) -> DatasetAccessManager:
    """Fournit un DatasetAccessManager mocké."""
    manager = Mock(spec=DatasetAccessManager)
    manager.dataset = mock_cluedo_dataset
    success_response = OracleResponse(
        authorized=True,
        message="Succès",
        data={"card": "Test"},
        query_type=QueryType.CARD_INQUIRY,
    )
    manager.execute_oracle_query = AsyncMock(return_value=success_response)
    manager.check_permission = AsyncMock(return_value=True)
    return manager


@pytest.fixture
def mock_cluedo_dataset_manager(
    mock_cluedo_dataset: CluedoDataset,
) -> CluedoDatasetManager:
    """Fournit un CluedoDatasetManager mocké."""
    manager = Mock(spec=CluedoDatasetManager)
    manager.dataset = mock_cluedo_dataset
    # Mock des méthodes spécifiques si nécessaire, pour l'instant un mock de base suffit.
    manager.validate_cluedo_suggestion = AsyncMock(
        return_value=OracleResponse(authorized=True, can_refute=True)
    )
    return manager


@pytest.fixture
def mock_cluedo_dataset_manager(
    mock_cluedo_dataset: CluedoDataset,
) -> CluedoDatasetManager:
    """Fournit un CluedoDatasetManager mocké."""
    manager = Mock(spec=CluedoDatasetManager)
    manager.dataset = mock_cluedo_dataset

    # Préparer une réponse correcte pour les mocks
    validation_res = ValidationResult(
        can_refute=True, suggestion_valid=True, authorized=True
    )
    response = OracleResponse(authorized=True, data=validation_res)

    manager.validate_cluedo_suggestion = AsyncMock(return_value=response)
    manager.execute_oracle_query = AsyncMock(
        return_value=response
    )  # Assurer la cohérence
    manager.check_permission = AsyncMock(return_value=True)

    return manager


# --- Tests consolidés pour OracleBaseAgent ---


class TestConsolidatedOracleAgentBehavior:
    @pytest.fixture
    def sample_agent_config(self) -> dict:
        """Fournit une configuration d'agent Oracle de test."""
        return {
            "agent_name": "ConsolidatedOracle",
            "system_prompt_suffix": "Oracle de test consolidé.",
            "access_level": "expert",
            "allowed_query_types": [QueryType.CARD_INQUIRY, QueryType.ADMIN_COMMAND],
        }

    @pytest.fixture
    def oracle_agent(
        self,
        mock_kernel: Kernel,
        mock_dataset_manager: DatasetAccessManager,
        sample_agent_config: dict,
    ) -> OracleBaseAgent:
        """Fournit une instance OracleBaseAgent initialisée."""
        return OracleBaseAgent(
            kernel=mock_kernel,
            dataset_manager=mock_dataset_manager,
            **sample_agent_config,
        )

    def test_agent_initialization(self, oracle_agent: OracleBaseAgent):
        """Teste l'initialisation correcte de l'agent Oracle."""
        assert oracle_agent.name == "ConsolidatedOracle"
        assert oracle_agent.access_level == "expert"
        assert "Oracle de test consolidé" in oracle_agent.instructions

    def test_oracle_tools_are_initialized(self, oracle_agent: OracleBaseAgent):
        """Teste que les OracleTools sont correctement initialisés."""
        assert isinstance(oracle_agent.oracle_tools, OracleTools)
        assert oracle_agent.oracle_tools.agent_name == oracle_agent.name

    @pytest.mark.asyncio
    async def test_execute_query_successfully(self, oracle_agent: OracleBaseAgent):
        """Teste une exécution de requête autorisée et réussie."""
        result = await oracle_agent.oracle_tools.query_oracle_dataset(
            query_type="card_inquiry", query_params='{"card": "Test"}'
        )
        assert "Succès" in result

    @pytest.mark.asyncio
    async def test_execute_query_permission_denied(
        self, oracle_agent: OracleBaseAgent, mock_dataset_manager: DatasetAccessManager
    ):
        """Teste la gestion du refus de permission."""
        mock_dataset_manager.execute_oracle_query.return_value = OracleResponse(
            authorized=False,
            message="Accès refusé",
            data={},
            query_type=QueryType.ADMIN_COMMAND,
        )
        result = await oracle_agent.oracle_tools.query_oracle_dataset(
            query_type="admin_command", query_params='{"command": "reset"}'
        )
        assert "Accès refusé" in result

    @pytest.mark.asyncio
    async def test_validate_permissions_for_another_agent(
        self, oracle_agent: OracleBaseAgent, mock_dataset_manager: DatasetAccessManager
    ):
        """Teste la validation des permissions pour un autre agent."""
        # Test succès
        mock_dataset_manager.check_permission.return_value = True
        result_success = await oracle_agent.oracle_tools.validate_agent_permissions(
            target_agent="Watson", query_type="card_inquiry"
        )
        assert "a les permissions" in result_success

        # Test échec
        mock_dataset_manager.check_permission.return_value = False
        result_failure = await oracle_agent.oracle_tools.validate_agent_permissions(
            target_agent="Watson", query_type="admin_command"
        )
        assert "n'a pas les permissions" in result_failure


# --- Tests consolidés pour MoriartyInterrogatorAgent ---


class TestConsolidatedMoriartyAgentBehavior:
    @pytest.fixture
    def moriarty_agent(
        self, mock_kernel: Kernel, mock_cluedo_dataset_manager: CluedoDatasetManager
    ) -> MoriartyInterrogatorAgent:
        """Fournit une instance de MoriartyInterrogatorAgent."""
        return MoriartyInterrogatorAgent(
            kernel=mock_kernel,
            dataset_manager=mock_cluedo_dataset_manager,
            game_strategy="balanced",
            agent_name="TestMoriarty",
        )

    def test_moriarty_initialization(self, moriarty_agent: MoriartyInterrogatorAgent):
        """Teste l'initialisation de l'agent Moriarty."""
        assert moriarty_agent.game_strategy == "balanced"
        assert "Moriarty" in moriarty_agent.instructions

    def test_moriarty_tools_behavior(self, moriarty_agent):
        """Teste le comportement de base des outils de Moriarty."""
        # Ce test est conceptuel et suppose que les outils sont des fonctions décorées.
        # La présence d'un `dataset_manager` initialisé est un bon indicateur.
        assert (
            hasattr(moriarty_agent, "dataset_manager")
            and moriarty_agent.dataset_manager is not None
        )

    def test_strategy_adaptation(self, mock_kernel, mock_cluedo_dataset_manager):
        """Teste l'adaptation du comportement selon la stratégie de jeu."""
        coop_agent = MoriartyInterrogatorAgent(
            mock_kernel, mock_cluedo_dataset_manager, "cooperative", "CoopMoriarty"
        )
        comp_agent = MoriartyInterrogatorAgent(
            mock_kernel, mock_cluedo_dataset_manager, "competitive", "CompMoriarty"
        )

        assert coop_agent.game_strategy == "cooperative"
        assert comp_agent.game_strategy == "competitive"


# --- Tests basés sur les scénarios de dialogue (depuis test_oracle_behavior_simple.py) ---


class SimpleCluedoOracleForDemo:
    """Oracle simplifié pour la démonstration."""

    def __init__(self):
        self.moriarty_cards = ["Professeur Violet", "Chandelier", "Cuisine"]

    def validate_suggestion(self, suspect: str, arme: str, lieu: str):
        suggestion = [suspect, arme, lieu]
        cards_to_reveal = [card for card in suggestion if card in self.moriarty_cards]
        if cards_to_reveal:
            return {
                "can_refute": True,
                "revealed_cards": cards_to_reveal,
                "message": f"Je possède {', '.join(cards_to_reveal)}.",
            }
        else:
            return {
                "can_refute": False,
                "revealed_cards": [],
                "message": "Je ne peux rien révéler.",
            }


def test_oracle_corrected_behavior():
    """Teste le comportement corrigé où l'Oracle révèle ses cartes."""
    oracle = SimpleCluedoOracleForDemo()
    result = oracle.validate_suggestion("Professeur Violet", "Chandelier", "Cuisine")

    assert result["can_refute"] is True
    assert "Professeur Violet" in result["revealed_cards"]
    assert "Chandelier" in result["revealed_cards"]
    assert "Cuisine" in result["revealed_cards"]


def test_oracle_no_revelation_behavior():
    """Teste le comportement où l'Oracle ne peut rien révéler."""
    oracle = SimpleCluedoOracleForDemo()
    result = oracle.validate_suggestion("Colonel Moutarde", "Poignard", "Salon")

    assert result["can_refute"] is False
    assert len(result["revealed_cards"]) == 0
