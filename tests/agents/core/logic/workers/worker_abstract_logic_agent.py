# -*- coding: utf-8 -*-
# tests/agents/core/logic/workers/worker_abstract_logic_agent.py
"""
Worker pour l'exécution des tests de AbstractLogicAgent dans un sous-processus JVM isolé.
"""

import pytest
import sys
import logging
import asyncio
from unittest.mock import MagicMock

# Configuration du logger
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] %(message)s", datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Assurer que le chemin du projet est dans le sys.path
import os

project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Imports originaux migrés
from semantic_kernel import Kernel
from semantic_kernel.functions import KernelArguments
from config.unified_config import UnifiedConfig, MockLevel
from argumentation_analysis.orchestration.service_manager import (
    OrchestrationServiceManager,
)
from argumentation_analysis.agents.core.abc.agent_bases import BaseLogicAgent
from argumentation_analysis.agents.core.logic.belief_set import BeliefSet
from argumentation_analysis.core.jvm_setup import JvmManager


class MockLogicAgent(BaseLogicAgent):
    """Classe concrète pour tester la classe abstraite AbstractLogicAgent."""

    def __init__(self, kernel: Kernel, agent_name: str):
        super().__init__(kernel, agent_name, "mock_logic")

    def setup_kernel(self, kernel_instance: Kernel):
        pass

    async def text_to_belief_set(self, text, context=None):
        return MagicMock(spec=BeliefSet), "Conversion réussie"

    async def generate_queries(self, text, belief_set, context=None):
        return ["query1", "query2"]

    def execute_query(self, belief_set, query):
        return True, "Requête exécutée avec succès"

    async def interpret_results(self, text, belief_set, queries, results):
        return "Interprétation des résultats"

    def _create_belief_set_from_data(self, belief_set_data):
        return MagicMock(spec=BeliefSet)

    def get_agent_capabilities(self):
        pass

    async def get_response(self, user_input: str, chat_history: any):
        pass

    async def invoke(self, input, context):
        pass

    def is_consistent(self, belief_set):
        return True, "Consistent"

    def setup_agent_components(self, config: "UnifiedConfig"):
        pass

    def validate_formula(self, formula: str, logic_type: str = "propositional"):
        return True, "Valid"

    async def invoke_single(self, *args, **kwargs):
        pass

    def validate_argument(self, argument, metadata):
        pass


@pytest.mark.llm_light
class TestAbstractLogicAgent:
    @pytest.fixture(autouse=True)
    async def setup_method(self):
        logger.info("Setting up test case for pytest in TestAbstractLogicAgent...")
        self.state_manager = OrchestrationServiceManager()

        self.config = UnifiedConfig()
        self.config.mock_level = MockLevel.NONE
        self.config.use_authentic_llm = True
        self.config.use_mock_llm = False

        self.kernel = self.config.get_kernel_with_gpt4o_mini()
        self.agent = MockLogicAgent(self.kernel, "TestAgent")

        self.initial_snapshot_data = {
            "raw_text": "Texte de test",
            "belief_sets": {
                "bs1": {"logic_type": "propositional", "content": "a => b"}
            },
        }

        self.state_manager.state.raw_text = self.initial_snapshot_data["raw_text"]
        self.state_manager.state.belief_sets = self.initial_snapshot_data[
            "belief_sets"
        ].copy()

        self.state_manager.get_current_state_snapshot = MagicMock(
            return_value=self.initial_snapshot_data
        )
        self.state_manager.add_answer = MagicMock()
        self.state_manager.add_belief_set = MagicMock(return_value="bs_mock_id")
        self.state_manager.log_query_result = MagicMock(return_value="log_mock_id")

    async def test_initialization(self):
        """Test de l'initialisation de l'agent."""
        assert self.agent.name == "TestAgent"
        assert self.agent.kernel is not None
        assert isinstance(self.agent.kernel, Kernel)

    async def test_process_task_unknown_task(self):
        """Test du traitement d'une tâche inconnue."""
        result = await self.agent.process_task(
            "task1", "Tâche inconnue", self.state_manager
        )
        assert result["status"] == "error"

    async def test_handle_translation_task(self):
        """Test du traitement d'une tâche de traduction."""
        task_description = (
            "Traduire le texte en Belief Set: Ceci est un texte pour la traduction."
        )
        self.state_manager.state.raw_text = "Ceci est un texte pour la traduction."
        result = await self.agent.process_task(
            "task_translation", task_description, self.state_manager
        )
        assert result["status"] == "success"

    async def test_handle_query_task(self):
        """Test du traitement d'une tâche d'exécution de requêtes."""
        self.state_manager.state.raw_text = "Texte de requête pour bs1."
        self.state_manager.state.belief_sets["bs1"] = {
            "logic_type": "propositional",
            "content": "a => b",
        }
        mock_bs_instance = MagicMock(spec=BeliefSet)
        self.agent._create_belief_set_from_data = lambda data_dict: mock_bs_instance
        result = await self.agent.process_task(
            "task_query",
            "Exécuter les Requêtes sur belief_set_id: bs1",
            self.state_manager,
        )
        assert result["status"] == "success"

    def test_extract_source_text_from_state(self):
        """Test de l'extraction du texte source depuis l'état."""
        text = self.agent._extract_source_text("", self.initial_snapshot_data)
        assert text == "Texte de test"

    def test_extract_source_text_from_description(self):
        """Test de l'extraction du texte source depuis la description."""
        text = self.agent._extract_source_text(
            "Analyser le texte: Ceci est un test", {"raw_text": ""}
        )
        assert text == "Ceci est un test"

    def test_extract_belief_set_id(self):
        """Test de l'extraction de l'ID de l'ensemble de croyances."""
        bs_id = self.agent._extract_belief_set_id("Requête sur belief_set_id: bs123")
        assert bs_id == "bs123"

    def test_extract_belief_set_id_not_found(self):
        """Test de l'extraction de l'ID de l'ensemble de croyances non trouvé."""
        bs_id = self.agent._extract_belief_set_id("Requête sans ID")
        assert bs_id is None


def main():
    """Point d'entrée principal pour l'exécution des tests."""
    logger.info("Démarrage du worker pour TestAbstractLogicAgent...")

    # Démarrer la JVM
    jvm_manager = JvmManager()
    try:
        jvm_manager.start_jvm()
        logger.info("JVM démarrée avec succès dans le worker.")

        # Exécuter les tests pytest
        # __file__ se réfère à ce fichier worker
        result = pytest.main(["-k", "TestAbstractLogicAgent", __file__])

        if result == pytest.ExitCode.OK:
            logger.info("Tests terminés avec succès dans le worker.")
            sys.exit(0)
        else:
            logger.error(
                f"Les tests ont échoué dans le worker avec le code de sortie: {result}"
            )
            sys.exit(int(result))

    except Exception as e:
        logger.critical(
            f"Une erreur critique est survenue dans le worker: {e}", exc_info=True
        )
        sys.exit(1)
    finally:
        # Assurer l'arrêt de la JVM même en cas d'erreur
        if jvm_manager.is_jvm_started():
            logger.info("Arrêt de la JVM dans le worker.")
            jvm_manager.shutdown_jvm()


if __name__ == "__main__":
    main()
