# tests/unit/argumentation_analysis/core/test_cluedo_oracle_state_extended.py
"""
Comprehensive tests for OrchestrationTracer and CluedoOracleState.

Tests TWO classes from argumentation_analysis/core/cluedo_oracle_state.py:
  - OrchestrationTracer (~15 tests)
  - CluedoOracleState (~45 tests)

All tests are self-contained: no real LLM, no real JVM, no API keys.
External dependencies (CluedoDataset, get_default_cluedo_permissions,
extend_oracle_state_phase_d, CluedoDatasetManager) are mocked.
"""

import pytest
import time
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch, PropertyMock

# ─────────────────────────────────────────────────────────────────────────────
# Imports under test  (real imports — no mocking of the module itself)
# ─────────────────────────────────────────────────────────────────────────────
from argumentation_analysis.core.cluedo_oracle_state import (
    OrchestrationTracer,
    CluedoOracleState,
)
from argumentation_analysis.agents.core.oracle.permissions import (
    QueryType,
    OracleResponse,
    QueryResult,
)

# ═════════════════════════════════════════════════════════════════════════════
# SHARED FIXTURES
# ═════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def cluedo_elements():
    return {
        "suspects": ["Colonel Mustard", "Miss Scarlet", "Professor Plum"],
        "armes": ["Candlestick", "Knife", "Revolver"],
        "lieux": ["Kitchen", "Library", "Ballroom"],
    }


@pytest.fixture
def mock_cluedo_dataset():
    dataset = MagicMock()
    dataset.get_moriarty_cards.return_value = ["Miss Scarlet", "Knife"]
    dataset.get_autres_joueurs_cards.return_value = ["Professor Plum", "Library"]
    dataset.get_revealed_cards_to_agent.return_value = []
    dataset.get_statistics.return_value = {"total_queries": 0}
    dataset.is_game_solvable_by_elimination.return_value = False
    dataset.reveal_policy = None
    return dataset


def _make_oracle_state(cluedo_elements, oracle_strategy="balanced"):
    """
    Helper that creates a CluedoOracleState with all external deps mocked.
    Returns (state, mock_dataset_instance).

    Notes on patching strategy:
    - CluedoDataset, get_default_cluedo_permissions, extend_oracle_state_phase_d
      are imported at module-level in cluedo_oracle_state.py -> patch there.
    - RevealPolicy is imported inside __init__ via a local import from permissions
      -> patch at its real location.
    - CluedoDatasetManager is imported inside __init__ via a local import
      -> patch at its real module location.
    """
    mock_dataset_instance = MagicMock()
    mock_dataset_instance.get_moriarty_cards.return_value = [
        "Miss Scarlet",
        "Knife",
    ]
    mock_dataset_instance.get_autres_joueurs_cards.return_value = [
        "Professor Plum",
        "Library",
    ]
    mock_dataset_instance.get_revealed_cards_to_agent.return_value = []
    mock_dataset_instance.get_statistics.return_value = {"total_queries": 0}
    mock_dataset_instance.is_game_solvable_by_elimination.return_value = False
    mock_dataset_instance.reveal_policy = None

    with patch(
        "argumentation_analysis.core.cluedo_oracle_state.CluedoDataset",
        return_value=mock_dataset_instance,
    ), patch(
        "argumentation_analysis.core.cluedo_oracle_state.get_default_cluedo_permissions",
        return_value={
            "SherlockEnqueteAgent": MagicMock(),
            "WatsonLogicAssistant": MagicMock(),
        },
    ), patch(
        "argumentation_analysis.core.cluedo_oracle_state.extend_oracle_state_phase_d"
    ), patch(
        # CluedoDatasetManager is imported locally inside __init__,
        # so patch at the source module where it is defined.
        "argumentation_analysis.agents.core.oracle.dataset_access_manager.CluedoDatasetManager",
        return_value=MagicMock(),
    ):
        state = CluedoOracleState(
            nom_enquete_cluedo="Test Enquête",
            elements_jeu_cluedo=cluedo_elements,
            description_cas="Test case description",
            initial_context={"lieu_initial": "Kitchen"},
            solution_secrete_cluedo={
                "suspect": "Colonel Mustard",
                "arme": "Candlestick",
                "lieu": "Kitchen",
            },
            oracle_strategy=oracle_strategy,
        )
        # Replace dataset with fully controlled mock after construction
        state.cluedo_dataset = mock_dataset_instance
        return state, mock_dataset_instance


@pytest.fixture
def oracle_state(cluedo_elements):
    state, _ = _make_oracle_state(cluedo_elements)
    return state


@pytest.fixture
def oracle_state_with_dataset(cluedo_elements):
    state, ds = _make_oracle_state(cluedo_elements)
    return state, ds


# ═════════════════════════════════════════════════════════════════════════════
# ─────────────────────────────────────────────────────────────────────────────
# PART 1: OrchestrationTracer Tests
# ─────────────────────────────────────────────────────────────────────────────
# ═════════════════════════════════════════════════════════════════════════════


class TestOrchestrationTracerInit:
    def test_init_trace_has_test_info(self):
        tracer = OrchestrationTracer()
        assert "test_info" in tracer.trace
        assert "start_time" in tracer.trace["test_info"]
        assert tracer.trace["test_info"]["end_time"] is None
        assert tracer.trace["test_info"]["total_duration_seconds"] == 0

    def test_init_trace_has_conversation_trace(self):
        tracer = OrchestrationTracer()
        assert "conversation_trace" in tracer.trace
        assert isinstance(tracer.trace["conversation_trace"], list)
        assert len(tracer.trace["conversation_trace"]) == 0

    def test_init_trace_has_tool_usage_trace(self):
        tracer = OrchestrationTracer()
        assert "tool_usage_trace" in tracer.trace
        assert isinstance(tracer.trace["tool_usage_trace"], list)

    def test_init_trace_has_shared_state_trace(self):
        tracer = OrchestrationTracer()
        assert "shared_state_trace" in tracer.trace
        assert isinstance(tracer.trace["shared_state_trace"], list)

    def test_init_metrics_start_at_zero(self):
        tracer = OrchestrationTracer()
        metrics = tracer.trace["metrics"]
        assert metrics["total_messages"] == 0
        assert metrics["total_tool_calls"] == 0
        assert metrics["state_updates"] == 0

    def test_init_start_time_is_iso_string(self):
        tracer = OrchestrationTracer()
        start_time = tracer.trace["test_info"]["start_time"]
        # Must parse without exception
        parsed = datetime.fromisoformat(start_time)
        assert isinstance(parsed, datetime)


class TestOrchestrationTracerLogMessage:
    def test_log_message_appends_to_conversation_trace(self):
        tracer = OrchestrationTracer()
        tracer.log_message("Sherlock", "hypothesis", "The suspect is Mustard")
        assert len(tracer.trace["conversation_trace"]) == 1

    def test_log_message_entry_has_correct_fields(self):
        tracer = OrchestrationTracer()
        tracer.log_message("Watson", "analysis", "Evidence is strong")
        entry = tracer.trace["conversation_trace"][0]
        assert entry["agent_name"] == "Watson"
        assert entry["message_type"] == "analysis"
        assert entry["content"] == "Evidence is strong"
        assert "timestamp" in entry

    def test_log_message_increments_total_messages(self):
        tracer = OrchestrationTracer()
        tracer.log_message("Sherlock", "t1", "msg1")
        assert tracer.trace["metrics"]["total_messages"] == 1

    def test_log_message_multiple_increments_counter_correctly(self):
        tracer = OrchestrationTracer()
        for i in range(5):
            tracer.log_message("Agent", "type", f"content_{i}")
        assert tracer.trace["metrics"]["total_messages"] == 5
        assert len(tracer.trace["conversation_trace"]) == 5

    def test_log_message_does_not_affect_tool_calls_or_state_updates(self):
        tracer = OrchestrationTracer()
        tracer.log_message("Sherlock", "t", "c")
        assert tracer.trace["metrics"]["total_tool_calls"] == 0
        assert tracer.trace["metrics"]["state_updates"] == 0


class TestOrchestrationTracerLogToolUsage:
    def test_log_tool_usage_appends_to_tool_usage_trace(self):
        tracer = OrchestrationTracer()
        tracer.log_tool_usage("Sherlock", "search_db", {"query": "test"}, {"result": 1})
        assert len(tracer.trace["tool_usage_trace"]) == 1

    def test_log_tool_usage_increments_total_tool_calls(self):
        tracer = OrchestrationTracer()
        tracer.log_tool_usage("Watson", "verify", "input", "output")
        assert tracer.trace["metrics"]["total_tool_calls"] == 1

    def test_log_tool_usage_input_output_are_stringified(self):
        tracer = OrchestrationTracer()
        tracer.log_tool_usage("Agent", "tool", {"key": "val"}, [1, 2, 3])
        entry = tracer.trace["tool_usage_trace"][0]
        assert isinstance(entry["input"], str)
        assert isinstance(entry["output"], str)

    def test_log_tool_usage_entry_has_correct_fields(self):
        tracer = OrchestrationTracer()
        tracer.log_tool_usage("Moriarty", "reveal_card", "card_name", "Knife")
        entry = tracer.trace["tool_usage_trace"][0]
        assert entry["agent_name"] == "Moriarty"
        assert entry["tool_name"] == "reveal_card"
        assert "timestamp" in entry


class TestOrchestrationTracerLogSharedState:
    def test_log_shared_state_appends_to_shared_state_trace(self):
        tracer = OrchestrationTracer()
        tracer.log_shared_state("game_phase", "investigation")
        assert len(tracer.trace["shared_state_trace"]) == 1

    def test_log_shared_state_increments_state_updates(self):
        tracer = OrchestrationTracer()
        tracer.log_shared_state("oracle_queries", 3)
        assert tracer.trace["metrics"]["state_updates"] == 1

    def test_log_shared_state_entry_has_correct_fields(self):
        tracer = OrchestrationTracer()
        tracer.log_shared_state("turn_count", 7)
        entry = tracer.trace["shared_state_trace"][0]
        assert entry["state_key"] == "turn_count"
        assert entry["state_value"] == 7
        assert "timestamp" in entry


class TestOrchestrationTracerGenerateReport:
    def test_generate_report_sets_end_time(self):
        tracer = OrchestrationTracer()
        report = tracer.generate_report()
        assert report["test_info"]["end_time"] is not None
        # Must parse without exception
        datetime.fromisoformat(report["test_info"]["end_time"])

    def test_generate_report_calculates_duration(self):
        tracer = OrchestrationTracer()
        time.sleep(0.05)  # small sleep to ensure non-zero duration
        report = tracer.generate_report()
        assert report["test_info"]["total_duration_seconds"] >= 0

    def test_generate_report_returns_trace(self):
        tracer = OrchestrationTracer()
        report = tracer.generate_report()
        assert report is tracer.trace

    def test_generate_report_after_operations_reflects_all_logged(self):
        tracer = OrchestrationTracer()
        tracer.log_message("A", "t", "c1")
        tracer.log_message("A", "t", "c2")
        tracer.log_tool_usage("A", "tool", "in", "out")
        tracer.log_shared_state("k", "v")
        report = tracer.generate_report()
        assert report["metrics"]["total_messages"] == 2
        assert report["metrics"]["total_tool_calls"] == 1
        assert report["metrics"]["state_updates"] == 1

    def test_generate_report_fresh_tracer_has_zero_metrics(self):
        tracer = OrchestrationTracer()
        report = tracer.generate_report()
        assert report["metrics"]["total_messages"] == 0
        assert report["metrics"]["total_tool_calls"] == 0
        assert report["metrics"]["state_updates"] == 0


# ═════════════════════════════════════════════════════════════════════════════
# ─────────────────────────────────────────────────────────────────────────────
# PART 2: CluedoOracleState Tests
# ─────────────────────────────────────────────────────────────────────────────
# ═════════════════════════════════════════════════════════════════════════════


class TestCluedoOracleStateInit:
    def test_init_default_strategy_is_balanced(self, cluedo_elements):
        state, _ = _make_oracle_state(cluedo_elements, oracle_strategy="balanced")
        assert state.oracle_strategy == "balanced"

    def test_init_cooperative_strategy(self, cluedo_elements):
        state, _ = _make_oracle_state(cluedo_elements, oracle_strategy="cooperative")
        assert state.oracle_strategy == "cooperative"

    def test_init_workflow_id_generated_as_uuid(self, cluedo_elements):
        state, _ = _make_oracle_state(cluedo_elements)
        import uuid

        # Should parse without raising
        parsed = uuid.UUID(state.workflow_id)
        assert str(parsed) == state.workflow_id

    def test_init_agent_ids_contain_workflow_id(self, cluedo_elements):
        state, _ = _make_oracle_state(cluedo_elements)
        assert state.workflow_id in state.moriarty_agent_id
        assert state.workflow_id in state.sherlock_agent_id
        assert state.workflow_id in state.watson_agent_id

    def test_init_empty_revelations_log(self, oracle_state):
        assert len(oracle_state.revelations_log) == 0

    def test_init_empty_oracle_queries_log(self, oracle_state):
        assert len(oracle_state.oracle_queries_log) == 0

    def test_init_workflow_metrics_initialized_with_zeros(self, oracle_state):
        metrics = oracle_state.workflow_metrics
        assert metrics["total_turns"] == 0
        assert metrics["oracle_interactions"] == 0
        assert metrics["cards_revealed"] == 0
        assert metrics["suggestions_count"] == 0

    def test_init_permissions_has_sherlock_and_watson(self, oracle_state):
        perms = oracle_state.agent_permissions
        assert "SherlockEnqueteAgent" in perms or "Sherlock" in perms
        assert "WatsonLogicAssistant" in perms or "Watson" in perms


class TestCluedoOracleStateProperties:
    def test_nom_enquete_property_returns_nom_enquete_cluedo(self, oracle_state):
        assert oracle_state.nom_enquete == oracle_state.nom_enquete_cluedo
        assert oracle_state.nom_enquete == "Test Enquête"

    def test_hypotheses_property_returns_hypotheses_enquete(self, oracle_state):
        assert oracle_state.hypotheses is oracle_state.hypotheses_enquete


class TestCluedoOracleStateCardDistribution:
    def test_distribute_cards_excludes_solution(self, cluedo_elements):
        state, _ = _make_oracle_state(cluedo_elements)
        solution = state.solution_secrete_cluedo
        solution_values = set(solution.values())
        all_distributed = state.cartes_distribuees.get(
            "Moriarty", []
        ) + state.cartes_distribuees.get("AutresJoueurs", [])
        for card in all_distributed:
            assert (
                card not in solution_values
            ), f"Solution card '{card}' should not be in distribution"

    def test_distribute_cards_moriarty_gets_approx_third(self, cluedo_elements):
        state, _ = _make_oracle_state(cluedo_elements)
        moriarty_cards = state.cartes_distribuees.get("Moriarty", [])
        autres_cards = state.cartes_distribuees.get("AutresJoueurs", [])
        total = len(moriarty_cards) + len(autres_cards)
        if total > 0:
            # Moriarty gets at least 1 card (max(1, total//3))
            assert len(moriarty_cards) >= 1

    def test_distribute_cards_custom_skips_auto_distribution(self, cluedo_elements):
        custom_distribution = {
            "Moriarty": ["Miss Scarlet"],
            "AutresJoueurs": ["Professor Plum"],
        }
        mock_ds = MagicMock()
        mock_ds.get_moriarty_cards.return_value = ["Miss Scarlet"]
        mock_ds.get_autres_joueurs_cards.return_value = ["Professor Plum"]
        mock_ds.get_revealed_cards_to_agent.return_value = []
        mock_ds.get_statistics.return_value = {}
        mock_ds.is_game_solvable_by_elimination.return_value = False
        mock_ds.reveal_policy = None

        with patch(
            "argumentation_analysis.core.cluedo_oracle_state.CluedoDataset",
            return_value=mock_ds,
        ), patch(
            "argumentation_analysis.core.cluedo_oracle_state.get_default_cluedo_permissions",
            return_value={},
        ), patch(
            "argumentation_analysis.core.cluedo_oracle_state.extend_oracle_state_phase_d"
        ), patch(
            "argumentation_analysis.agents.core.oracle.dataset_access_manager.CluedoDatasetManager",
            return_value=MagicMock(),
        ):
            state = CluedoOracleState(
                nom_enquete_cluedo="Test",
                elements_jeu_cluedo=cluedo_elements,
                description_cas="desc",
                initial_context={},
                cartes_distribuees=custom_distribution,
                solution_secrete_cluedo={
                    "suspect": "Colonel Mustard",
                    "arme": "Candlestick",
                    "lieu": "Kitchen",
                },
            )
        assert state.cartes_distribuees == custom_distribution

    def test_distribute_cards_minimal_game_allows_empty_distribution(self):
        """With only 3 elements (all solution), distribution can be empty."""
        minimal_elements = {
            "suspects": ["Colonel Mustard"],
            "armes": ["Candlestick"],
            "lieux": ["Kitchen"],
        }
        mock_ds = MagicMock()
        mock_ds.get_moriarty_cards.return_value = []
        mock_ds.get_autres_joueurs_cards.return_value = []
        mock_ds.get_revealed_cards_to_agent.return_value = []
        mock_ds.get_statistics.return_value = {}
        mock_ds.is_game_solvable_by_elimination.return_value = False
        mock_ds.reveal_policy = None

        with patch(
            "argumentation_analysis.core.cluedo_oracle_state.CluedoDataset",
            return_value=mock_ds,
        ), patch(
            "argumentation_analysis.core.cluedo_oracle_state.get_default_cluedo_permissions",
            return_value={},
        ), patch(
            "argumentation_analysis.core.cluedo_oracle_state.extend_oracle_state_phase_d"
        ), patch(
            "argumentation_analysis.agents.core.oracle.dataset_access_manager.CluedoDatasetManager",
            return_value=MagicMock(),
        ):
            state = CluedoOracleState(
                nom_enquete_cluedo="Minimal",
                elements_jeu_cluedo=minimal_elements,
                description_cas="desc",
                initial_context={},
                solution_secrete_cluedo={
                    "suspect": "Colonel Mustard",
                    "arme": "Candlestick",
                    "lieu": "Kitchen",
                },
            )
        assert state.cartes_distribuees["Moriarty"] == []
        assert state.cartes_distribuees["AutresJoueurs"] == []


class TestCluedoOracleStatePermissions:
    def test_agent_can_query_oracle_sherlock_suggestion_validation(self, oracle_state):
        """Sherlock has suggestion_validation in allowed_query_types."""
        result = oracle_state._agent_can_query_oracle(
            "Sherlock", QueryType.SUGGESTION_VALIDATION
        )
        assert result is True

    def test_agent_can_query_oracle_sherlock_clue_request(self, oracle_state):
        """Sherlock has clue_request in allowed_query_types."""
        result = oracle_state._agent_can_query_oracle(
            "Sherlock", QueryType.CLUE_REQUEST
        )
        assert result is True

    def test_agent_can_query_oracle_watson_logical_validation(self, oracle_state):
        """Watson has logical_validation in allowed_query_types."""
        result = oracle_state._agent_can_query_oracle(
            "Watson", QueryType.LOGICAL_VALIDATION
        )
        assert result is True

    def test_agent_can_query_oracle_unknown_agent_denied(self, oracle_state):
        """Unknown agent should be denied."""
        result = oracle_state._agent_can_query_oracle(
            "UnknownAgent", QueryType.CARD_INQUIRY
        )
        assert result is False

    def test_agent_can_query_oracle_wrong_type_denied(self, oracle_state):
        """Watson cannot use ADMIN_COMMAND."""
        result = oracle_state._agent_can_query_oracle("Watson", QueryType.ADMIN_COMMAND)
        assert result is False

    def test_moriarty_has_is_oracle_flag(self, oracle_state):
        """MoriartyInterrogatorAgent entry has is_oracle=True."""
        moriarty_perms = oracle_state.agent_permissions.get("MoriartyInterrogatorAgent")
        assert moriarty_perms is not None
        assert moriarty_perms.get("is_oracle") is True

    def test_moriarty_alias_has_is_oracle_flag(self, oracle_state):
        """Moriarty alias also has is_oracle=True."""
        moriarty_perms = oracle_state.agent_permissions.get("Moriarty")
        assert moriarty_perms is not None
        assert moriarty_perms.get("is_oracle") is True


class TestCluedoOracleStateQueryOracle:
    async def test_query_oracle_invalid_type_returns_unauthorized(
        self, oracle_state_with_dataset
    ):
        state, _ = oracle_state_with_dataset
        response = await state.query_oracle(
            agent_name="Sherlock",
            query_type="completely_invalid_type_xyz",
            query_params={},
        )
        assert response.authorized is False
        assert (
            "invalide" in response.message.lower()
            or "invalid" in response.message.lower()
        )

    async def test_query_oracle_permission_denied_returns_unauthorized(
        self, oracle_state_with_dataset
    ):
        state, _ = oracle_state_with_dataset
        # UnknownAgent has no permissions
        response = await state.query_oracle(
            agent_name="UnknownAgent",
            query_type="card_inquiry",
            query_params={},
        )
        assert response.authorized is False

    async def test_query_oracle_successful_query_returns_response(
        self, oracle_state_with_dataset
    ):
        state, mock_dataset = oracle_state_with_dataset
        # Setup mock to return a successful QueryResult
        mock_result = QueryResult(
            success=True,
            data={"card": "Knife"},
            message="Card found",
            metadata={},
        )
        mock_dataset.process_query = AsyncMock(return_value=mock_result)

        response = await state.query_oracle(
            agent_name="Sherlock",
            query_type="card_inquiry",
            query_params={"card": "Knife"},
        )
        assert isinstance(response, OracleResponse)
        assert response.authorized is True

    async def test_query_oracle_increments_counters(self, oracle_state_with_dataset):
        state, mock_dataset = oracle_state_with_dataset
        mock_result = QueryResult(success=True, data={}, message="OK", metadata={})
        mock_dataset.process_query = AsyncMock(return_value=mock_result)

        initial_count = state.oracle_queries_count
        initial_interactions = state.oracle_interactions
        initial_metrics = state.workflow_metrics["oracle_interactions"]

        await state.query_oracle(
            agent_name="Sherlock",
            query_type="suggestion_validation",
            query_params={},
        )

        assert state.oracle_queries_count == initial_count + 1
        assert state.oracle_interactions == initial_interactions + 1
        assert state.workflow_metrics["oracle_interactions"] == initial_metrics + 1

    async def test_query_oracle_error_handling_returns_error_response(
        self, oracle_state_with_dataset
    ):
        state, mock_dataset = oracle_state_with_dataset
        mock_dataset.process_query = AsyncMock(
            side_effect=RuntimeError("Dataset unavailable")
        )

        response = await state.query_oracle(
            agent_name="Sherlock",
            query_type="card_inquiry",
            query_params={},
        )
        assert response.authorized is False
        assert (
            "erreur" in response.message.lower() or "error" in response.message.lower()
        )


class TestCluedoOracleStateRecordAgentTurn:
    def test_record_agent_turn_adds_to_interaction_pattern(self, oracle_state):
        oracle_state.record_agent_turn("Sherlock", "suggestion")
        assert "Sherlock" in oracle_state.interaction_pattern

    def test_record_agent_turn_increments_total_turns(self, oracle_state):
        initial = oracle_state.workflow_metrics["total_turns"]
        oracle_state.record_agent_turn("Watson", "validation")
        assert oracle_state.workflow_metrics["total_turns"] == initial + 1

    def test_record_agent_turn_multiple_turns_tracked_correctly(self, oracle_state):
        oracle_state.record_agent_turn("Sherlock", "suggestion")
        oracle_state.record_agent_turn("Watson", "validation")
        oracle_state.record_agent_turn("Moriarty", "revelation")
        assert oracle_state.workflow_metrics["total_turns"] == 3
        assert len(oracle_state.interaction_pattern) == 3

    def test_record_agent_turn_new_agent_initializes_dict_entry(self, oracle_state):
        assert "NewAgent" not in oracle_state.agent_turns
        oracle_state.record_agent_turn("NewAgent", "test_action")
        assert "NewAgent" in oracle_state.agent_turns
        assert oracle_state.agent_turns["NewAgent"]["total_turns"] == 1

    def test_record_agent_turn_existing_agent_increments_turns(self, oracle_state):
        oracle_state.record_agent_turn("Sherlock", "suggestion")
        oracle_state.record_agent_turn("Sherlock", "deduction")
        assert oracle_state.agent_turns["Sherlock"]["total_turns"] == 2


class TestCluedoOracleStateGetCurrentTurnInfo:
    def test_get_current_turn_info_returns_correct_dict(self, oracle_state):
        oracle_state.record_agent_turn("Sherlock", "suggestion")
        info = oracle_state.get_current_turn_info()
        assert info["turn_number"] == 1
        assert info["last_agent"] == "Sherlock"
        assert "total_oracle_queries" in info
        assert "cards_revealed_count" in info
        assert "suggestions_count" in info

    def test_get_current_turn_info_empty_state_returns_turn_zero(self, oracle_state):
        info = oracle_state.get_current_turn_info()
        assert info["turn_number"] == 0
        assert info["last_agent"] is None

    def test_get_current_turn_info_after_multiple_turns(self, oracle_state):
        oracle_state.record_agent_turn("Sherlock", "s1")
        oracle_state.record_agent_turn("Watson", "s2")
        oracle_state.record_agent_turn("Moriarty", "s3")
        info = oracle_state.get_current_turn_info()
        assert info["turn_number"] == 3
        assert info["last_agent"] == "Moriarty"


class TestCluedoOracleStateReset:
    def test_reset_oracle_state_clears_all_logs(self, oracle_state):
        # Add some data first
        oracle_state.record_agent_turn("Sherlock", "suggestion")
        oracle_state.oracle_queries_count = 5

        oracle_state.reset_oracle_state()

        assert len(oracle_state.revelations_log) == 0
        assert len(oracle_state.oracle_queries_log) == 0
        assert len(oracle_state.interaction_pattern) == 0
        assert oracle_state.oracle_queries_count == 0

    def test_reset_oracle_state_preserves_oracle_strategy(self, cluedo_elements):
        state, _ = _make_oracle_state(cluedo_elements, oracle_strategy="cooperative")
        state.reset_oracle_state()
        assert state.oracle_strategy == "cooperative"

    def test_reset_oracle_state_preserves_permissions(self, oracle_state):
        original_perms = oracle_state.agent_permissions.copy()
        oracle_state.reset_oracle_state()
        # Permissions dict should still have the same keys
        for key in original_perms:
            assert key in oracle_state.agent_permissions

    def test_reset_oracle_state_resets_solution_flags(self, oracle_state):
        oracle_state.is_solution_proposed = True
        oracle_state.final_solution = {"suspect": "X", "arme": "Y", "lieu": "Z"}

        oracle_state.reset_oracle_state()

        assert oracle_state.is_solution_proposed is False
        assert oracle_state.final_solution is None

    def test_reset_oracle_state_resets_workflow_metrics(self, oracle_state):
        oracle_state.record_agent_turn("Sherlock", "s")
        oracle_state.reset_oracle_state()
        assert oracle_state.workflow_metrics["total_turns"] == 0
        assert oracle_state.workflow_metrics["oracle_interactions"] == 0
        assert oracle_state.workflow_metrics["cards_revealed"] == 0


class TestCluedoOracleStateConversation:
    def test_add_conversation_message_appends_to_history(self, oracle_state):
        oracle_state.add_conversation_message("Sherlock", "I deduce the suspect is X")
        assert len(oracle_state.conversation_history) == 1

    def test_add_conversation_message_entry_has_correct_fields(self, oracle_state):
        oracle_state.add_conversation_message(
            "Watson", "Agreed, the evidence supports it", "analysis"
        )
        entry = oracle_state.conversation_history[0]
        assert entry["agent_name"] == "Watson"
        assert entry["content"] == "Agreed, the evidence supports it"
        assert entry["message_type"] == "analysis"
        assert "timestamp" in entry
        assert "turn_number" in entry

    def test_add_conversation_message_long_content_has_preview_truncated(
        self, oracle_state
    ):
        long_content = "A" * 200
        oracle_state.add_conversation_message("Sherlock", long_content)
        entry = oracle_state.conversation_history[0]
        assert len(entry["content_preview"]) <= 103  # 100 chars + "..."

    def test_add_conversation_message_short_content_no_truncation(self, oracle_state):
        short_content = "Short message"
        oracle_state.add_conversation_message("Sherlock", short_content)
        entry = oracle_state.conversation_history[0]
        assert entry["content_preview"] == short_content

    def test_get_recent_context_empty_returns_empty_list(self, oracle_state):
        result = oracle_state.get_recent_context()
        assert result == []

    def test_get_recent_context_fewer_messages_returns_all(self, oracle_state):
        oracle_state.add_conversation_message("Sherlock", "msg1")
        oracle_state.add_conversation_message("Watson", "msg2")
        result = oracle_state.get_recent_context(5)
        assert len(result) == 2

    def test_get_recent_context_returns_requested_count(self, oracle_state):
        for i in range(10):
            oracle_state.add_conversation_message("Sherlock", f"message {i}")
        result = oracle_state.get_recent_context(3)
        assert len(result) == 3

    def test_get_recent_context_messages_have_context_info(self, oracle_state):
        oracle_state.add_conversation_message("Sherlock", "A normal deduction")
        result = oracle_state.get_recent_context(1)
        assert len(result) == 1
        assert "context_info" in result[0]
        assert "is_revelation" in result[0]["context_info"]
        assert "is_suggestion" in result[0]["context_info"]
        assert "agent_role" in result[0]["context_info"]

    def test_record_contextual_reference_appends_to_references(self, oracle_state):
        oracle_state.record_contextual_reference(
            "Watson", 1, "response_to", "Sherlock's last deduction"
        )
        assert len(oracle_state.contextual_references) == 1

    def test_record_contextual_reference_entry_has_correct_fields(self, oracle_state):
        oracle_state.record_contextual_reference(
            "Moriarty", 2, "building_on", "The card revelation"
        )
        entry = oracle_state.contextual_references[0]
        assert entry["source_agent"] == "Moriarty"
        assert entry["target_turn"] == 2
        assert entry["reference_type"] == "building_on"
        assert entry["reference_content"] == "The card revelation"

    def test_record_emotional_reaction_appends_to_reactions(self, oracle_state):
        oracle_state.record_emotional_reaction(
            "Watson", "Sherlock", "Brilliant deduction!", "approval", "Indeed!"
        )
        assert len(oracle_state.emotional_reactions) == 1

    def test_record_emotional_reaction_long_trigger_content_truncated(
        self, oracle_state
    ):
        long_trigger = "X" * 200
        oracle_state.record_emotional_reaction(
            "Watson", "Sherlock", long_trigger, "surprise", "Wow!"
        )
        entry = oracle_state.emotional_reactions[0]
        assert len(entry["trigger_content"]) <= 103  # 100 + "..."

    def test_record_emotional_reaction_entry_has_correct_fields(self, oracle_state):
        oracle_state.record_emotional_reaction(
            "Watson", "Moriarty", "Card revealed!", "excitement", "Aha!"
        )
        entry = oracle_state.emotional_reactions[0]
        assert entry["reacting_agent"] == "Watson"
        assert entry["trigger_agent"] == "Moriarty"
        assert entry["reaction_type"] == "excitement"
        assert entry["reaction_content"] == "Aha!"


class TestCluedoOracleStateStatistics:
    def test_get_oracle_statistics_returns_complete_stats_dict(self, oracle_state):
        stats = oracle_state.get_oracle_statistics()
        assert "workflow_id" in stats
        assert "oracle_strategy" in stats
        assert "workflow_metrics" in stats
        assert "agent_interactions" in stats
        assert "cards_distribution" in stats
        assert "dataset_statistics" in stats

    def test_get_oracle_statistics_workflow_id_matches(self, oracle_state):
        stats = oracle_state.get_oracle_statistics()
        assert stats["workflow_id"] == oracle_state.workflow_id

    def test_get_oracle_statistics_oracle_strategy_matches(self, oracle_state):
        stats = oracle_state.get_oracle_statistics()
        assert stats["oracle_strategy"] == oracle_state.oracle_strategy

    def test_get_game_progress_summary_returns_all_fields(self, oracle_state):
        summary = oracle_state.get_game_progress_summary()
        assert "workflow_id" in summary
        assert "oracle_strategy" in summary
        assert "turns_completed" in summary
        assert "oracle_queries" in summary
        assert "cards_revealed" in summary
        assert "suggestions_made" in summary
        assert "solution_proposed" in summary
        assert "moriarty_cards_count" in summary

    def test_get_game_progress_summary_solution_proposed_false_initially(
        self, oracle_state
    ):
        summary = oracle_state.get_game_progress_summary()
        assert summary["solution_proposed"] is False

    def test_has_solution_proposed_false_initially(self, oracle_state):
        assert oracle_state.has_solution_proposed() is False

    def test_has_solution_proposed_true_after_setting(self, oracle_state):
        oracle_state.is_solution_proposed = True
        assert oracle_state.has_solution_proposed() is True


class TestCluedoOracleStateCompatibility:
    def test_get_proposed_solution_returns_none_initially(self, oracle_state):
        assert oracle_state.get_proposed_solution() is None

    def test_get_proposed_solution_returns_final_solution(self, oracle_state):
        solution = {"suspect": "Miss Scarlet", "arme": "Knife", "lieu": "Library"}
        oracle_state.final_solution = solution
        assert oracle_state.get_proposed_solution() == solution

    def test_validate_suggestion_raises_on_invalid_params(self, oracle_state):
        """validate_suggestion_with_oracle raises ValueError when params are invalid."""
        import asyncio

        async def _run():
            # Neither (suggestion+requesting_agent) nor (suspect+arme+lieu+suggesting_agent)
            with pytest.raises((ValueError, TypeError)):
                await oracle_state.validate_suggestion_with_oracle()

        asyncio.get_event_loop().run_until_complete(_run())

    def test_nom_enquete_cluedo_stored_correctly(self, oracle_state):
        assert oracle_state.nom_enquete_cluedo == "Test Enquête"

    def test_elements_jeu_stored_correctly(self, oracle_state, cluedo_elements):
        assert oracle_state.elements_jeu_cluedo == cluedo_elements

    def test_description_cas_stored_correctly(self, oracle_state):
        assert oracle_state.description_cas == "Test case description"

    def test_solution_secrete_stored_correctly(self, oracle_state):
        sol = oracle_state.solution_secrete_cluedo
        assert sol["suspect"] == "Colonel Mustard"
        assert sol["arme"] == "Candlestick"
        assert sol["lieu"] == "Kitchen"

    def test_oracle_queries_count_starts_at_zero(self, oracle_state):
        assert oracle_state.oracle_queries_count == 0

    def test_oracle_interactions_starts_at_zero(self, oracle_state):
        assert oracle_state.oracle_interactions == 0

    def test_cards_revealed_starts_at_zero(self, oracle_state):
        assert oracle_state.cards_revealed == 0

    def test_agent_turns_empty_initially(self, oracle_state):
        assert oracle_state.agent_turns == {}

    def test_suggestions_historique_empty_initially(self, oracle_state):
        assert oracle_state.suggestions_historique == []

    def test_is_game_solvable_by_elimination_delegates_to_dataset(
        self, oracle_state_with_dataset
    ):
        state, mock_dataset = oracle_state_with_dataset
        mock_dataset.is_game_solvable_by_elimination.return_value = True
        assert state.is_game_solvable_by_elimination() is True
        mock_dataset.is_game_solvable_by_elimination.return_value = False
        assert state.is_game_solvable_by_elimination() is False

    def test_get_moriarty_cards_delegates_to_dataset(self, oracle_state_with_dataset):
        state, mock_dataset = oracle_state_with_dataset
        mock_dataset.get_moriarty_cards.return_value = ["Knife", "Revolver"]
        result = state.get_moriarty_cards()
        assert result == ["Knife", "Revolver"]

    def test_get_autres_joueurs_cards_delegates_to_dataset(
        self, oracle_state_with_dataset
    ):
        state, mock_dataset = oracle_state_with_dataset
        mock_dataset.get_autres_joueurs_cards.return_value = ["Professor Plum"]
        result = state.get_autres_joueurs_cards()
        assert result == ["Professor Plum"]

    def test_get_revealed_cards_to_agent_delegates_to_dataset(
        self, oracle_state_with_dataset
    ):
        state, mock_dataset = oracle_state_with_dataset
        mock_dataset.get_revealed_cards_to_agent.return_value = ["Library"]
        result = state.get_revealed_cards_to_agent("Sherlock")
        mock_dataset.get_revealed_cards_to_agent.assert_called_once_with("Sherlock")
        assert result == ["Library"]
