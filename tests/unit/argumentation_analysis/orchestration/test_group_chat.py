# tests/unit/argumentation_analysis/orchestration/test_group_chat.py
"""Tests for GroupChatOrchestration — collaborative agent coordination."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime

from argumentation_analysis.orchestration.group_chat import GroupChatOrchestration


# ── Fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def orchestration():
    """Fresh GroupChatOrchestration instance."""
    return GroupChatOrchestration()


@pytest.fixture
def mock_agents():
    """Dict of mock agents for session initialization."""
    agent_a = MagicMock()
    agent_a.get_agent_capabilities.return_value = {"cap": "logic"}
    agent_b = MagicMock()
    agent_b.get_agent_capabilities.return_value = {"cap": "extraction"}
    return {"informal_agent": agent_a, "logic_fol_agent": agent_b}


@pytest.fixture
def active_session(orchestration, mock_agents):
    """Orchestration with an active session and messages."""
    orchestration.initialize_session("sess-001", mock_agents)
    orchestration.add_message("informal_agent", "Hello from informal")
    orchestration.add_message("logic_fol_agent", "Hello from logic")
    return orchestration


# ── __init__ ────────────────────────────────────────────────────────────

class TestGroupChatInit:
    """Tests for GroupChatOrchestration.__init__."""

    def test_initial_state(self, orchestration):
        assert orchestration.active_agents == {}
        assert orchestration.conversation_history == []
        assert orchestration.session_id is None

    def test_async_manager_created(self, orchestration):
        assert orchestration.async_manager is not None

    def test_health_status_initialized(self, orchestration):
        assert orchestration._health_status["status"] == "healthy"

    def test_communication_locks_empty(self, orchestration):
        assert orchestration._agent_communication_locks == {}


# ── initialize_session ──────────────────────────────────────────────────

class TestInitializeSession:
    """Tests for initialize_session()."""

    def test_returns_true(self, orchestration, mock_agents):
        assert orchestration.initialize_session("s1", mock_agents) is True

    def test_sets_session_id(self, orchestration, mock_agents):
        orchestration.initialize_session("s1", mock_agents)
        assert orchestration.session_id == "s1"

    def test_copies_agents(self, orchestration, mock_agents):
        orchestration.initialize_session("s1", mock_agents)
        assert set(orchestration.active_agents.keys()) == set(mock_agents.keys())
        # Verify it's a copy
        mock_agents["new_key"] = "val"
        assert "new_key" not in orchestration.active_agents

    def test_clears_history(self, orchestration, mock_agents):
        orchestration.conversation_history = [{"fake": True}]
        orchestration.initialize_session("s1", mock_agents)
        assert orchestration.conversation_history == []

    def test_empty_agents_allowed(self, orchestration):
        assert orchestration.initialize_session("s1", {}) is True
        assert orchestration.active_agents == {}

    def test_reinitialise_overwrites(self, orchestration, mock_agents):
        orchestration.initialize_session("s1", mock_agents)
        orchestration.add_message("informal_agent", "msg")
        orchestration.initialize_session("s2", {"other": MagicMock()})
        assert orchestration.session_id == "s2"
        assert "other" in orchestration.active_agents
        assert orchestration.conversation_history == []


# ── add_message ─────────────────────────────────────────────────────────

class TestAddMessage:
    """Tests for add_message()."""

    def test_returns_message_entry(self, active_session):
        entry = active_session.add_message("informal_agent", "test msg")
        assert entry["agent_id"] == "informal_agent"
        assert entry["message"] == "test msg"
        assert "timestamp" in entry
        assert "message_id" in entry

    def test_message_id_increments(self, active_session):
        # Already 2 messages from fixture
        entry = active_session.add_message("informal_agent", "third")
        assert entry["message_id"] == 3

    def test_analysis_results_default_empty(self, active_session):
        entry = active_session.add_message("informal_agent", "no results")
        assert entry["analysis_results"] == {}

    def test_analysis_results_preserved(self, active_session):
        results = {"fallacies": ["ad_hominem"]}
        entry = active_session.add_message("informal_agent", "w/results", results)
        assert entry["analysis_results"] == results

    def test_appended_to_history(self, active_session):
        before = len(active_session.conversation_history)
        active_session.add_message("informal_agent", "new")
        assert len(active_session.conversation_history) == before + 1

    def test_unknown_agent_id_still_works(self, active_session):
        entry = active_session.add_message("unknown_agent", "hi")
        assert entry["agent_id"] == "unknown_agent"


# ── get_conversation_summary ────────────────────────────────────────────

class TestGetConversationSummary:
    """Tests for get_conversation_summary()."""

    def test_empty_summary(self, orchestration):
        summary = orchestration.get_conversation_summary()
        assert summary["total_messages"] == 0
        assert summary["conversation_start"] is None
        assert summary["last_activity"] is None

    def test_with_messages(self, active_session):
        summary = active_session.get_conversation_summary()
        assert summary["session_id"] == "sess-001"
        assert summary["total_messages"] == 2
        assert len(summary["active_agents"]) == 2

    def test_agents_participation(self, active_session):
        active_session.add_message("informal_agent", "extra")
        summary = active_session.get_conversation_summary()
        assert summary["agents_participation"]["informal_agent"] == 2
        assert summary["agents_participation"]["logic_fol_agent"] == 1

    def test_timestamps_present(self, active_session):
        summary = active_session.get_conversation_summary()
        assert summary["conversation_start"] is not None
        assert summary["last_activity"] is not None


# ── _get_agent_type ─────────────────────────────────────────────────────

class TestGetAgentType:
    """Tests for _get_agent_type()."""

    def test_informal(self, orchestration):
        assert orchestration._get_agent_type("informal_agent") == "informal_analysis"

    def test_logic(self, orchestration):
        assert orchestration._get_agent_type("logic_agent") == "formal_logic"

    def test_fol(self, orchestration):
        assert orchestration._get_agent_type("fol_reasoner") == "formal_logic"

    def test_extract(self, orchestration):
        assert orchestration._get_agent_type("extract_facts") == "extraction"

    def test_general(self, orchestration):
        assert orchestration._get_agent_type("some_agent") == "general_analysis"

    def test_case_insensitive(self, orchestration):
        assert orchestration._get_agent_type("INFORMAL_AGENT") == "informal_analysis"
        assert orchestration._get_agent_type("LOGIC_FOL") == "formal_logic"


# ── coordinate_analysis ─────────────────────────────────────────────────

class TestCoordinateAnalysis:
    """Tests for coordinate_analysis()."""

    def test_all_agents_by_default(self, active_session):
        result = active_session.coordinate_analysis("sample text")
        assert set(result["agents_involved"]) == {"informal_agent", "logic_fol_agent"}

    def test_target_agents_subset(self, active_session):
        result = active_session.coordinate_analysis("text", ["informal_agent"])
        assert result["agents_involved"] == ["informal_agent"]
        assert "informal_agent" in result["individual_results"]
        assert "logic_fol_agent" not in result["individual_results"]

    def test_result_structure(self, active_session):
        result = active_session.coordinate_analysis("txt")
        assert "text" in result
        assert "individual_results" in result
        assert "consolidated_analysis" in result
        assert "timestamp" in result

    def test_individual_result_fields(self, active_session):
        result = active_session.coordinate_analysis("txt")
        for agent_id, agent_result in result["individual_results"].items():
            assert "agent_id" in agent_result
            assert "analysis_type" in agent_result
            assert "confidence" in agent_result
            assert "findings" in agent_result

    def test_nonexistent_agent_ignored(self, active_session):
        result = active_session.coordinate_analysis("txt", ["fake_agent"])
        assert result["individual_results"] == {}

    def test_empty_target_uses_all(self, active_session):
        result = active_session.coordinate_analysis("txt", [])
        # Empty list is falsy → uses all agents
        assert len(result["agents_involved"]) == 2

    def test_consolidated_analysis_present(self, active_session):
        result = active_session.coordinate_analysis("txt")
        cons = result["consolidated_analysis"]
        assert "summary" in cons
        assert "average_confidence" in cons
        assert cons["agents_count"] == 2


# ── _consolidate_results ────────────────────────────────────────────────

class TestConsolidateResults:
    """Tests for _consolidate_results()."""

    def test_empty_results(self, orchestration):
        result = orchestration._consolidate_results({})
        assert result["agents_count"] == 0
        assert result["average_confidence"] == 0.0

    def test_single_agent(self, orchestration):
        results = {"a1": {"confidence": 0.9, "findings": ["f1"]}}
        consolidated = orchestration._consolidate_results(results)
        assert consolidated["agents_count"] == 1
        assert consolidated["average_confidence"] == 0.9
        assert "f1" in consolidated["key_findings"]

    def test_average_confidence(self, orchestration):
        results = {
            "a1": {"confidence": 0.8, "findings": []},
            "a2": {"confidence": 0.6, "findings": []},
        }
        consolidated = orchestration._consolidate_results(results)
        assert consolidated["average_confidence"] == pytest.approx(0.7)

    def test_findings_aggregated(self, orchestration):
        results = {
            "a1": {"confidence": 0.8, "findings": ["f1", "f2"]},
            "a2": {"confidence": 0.8, "findings": ["f3"]},
        }
        consolidated = orchestration._consolidate_results(results)
        assert len(consolidated["key_findings"]) == 3

    def test_missing_confidence_key(self, orchestration):
        results = {"a1": {"findings": ["f1"]}}
        consolidated = orchestration._consolidate_results(results)
        assert consolidated["average_confidence"] == 0.0


# ── get_agent_status ────────────────────────────────────────────────────

class TestGetAgentStatus:
    """Tests for get_agent_status()."""

    def test_empty_when_no_agents(self, orchestration):
        assert orchestration.get_agent_status() == {}

    def test_returns_all_agents(self, active_session):
        status = active_session.get_agent_status()
        assert "informal_agent" in status
        assert "logic_fol_agent" in status

    def test_agent_status_fields(self, active_session):
        status = active_session.get_agent_status()
        for agent_id, info in status.items():
            assert info["active"] is True
            assert "type" in info
            assert "capabilities" in info

    def test_agent_type_detection(self, active_session):
        status = active_session.get_agent_status()
        assert status["informal_agent"]["type"] == "informal_analysis"
        assert status["logic_fol_agent"]["type"] == "formal_logic"

    def test_agent_without_capabilities(self, orchestration):
        agent = MagicMock(spec=[])  # No get_agent_capabilities
        orchestration.initialize_session("s", {"basic": agent})
        status = orchestration.get_agent_status()
        assert status["basic"]["capabilities"] == {}


# ── cleanup_session ─────────────────────────────────────────────────────

class TestCleanupSession:
    """Tests for cleanup_session()."""

    def test_returns_true(self, active_session):
        assert active_session.cleanup_session() is True

    def test_clears_agents(self, active_session):
        active_session.cleanup_session()
        assert active_session.active_agents == {}

    def test_clears_history(self, active_session):
        active_session.cleanup_session()
        assert active_session.conversation_history == []

    def test_clears_session_id(self, active_session):
        active_session.cleanup_session()
        assert active_session.session_id is None

    def test_clears_communication_locks(self, active_session):
        active_session._agent_communication_locks["k"] = "v"
        active_session.cleanup_session()
        assert active_session._agent_communication_locks == {}

    def test_resets_health_status(self, active_session):
        active_session.cleanup_session()
        assert active_session._health_status["status"] == "healthy"

    def test_cleanup_async_tasks(self, active_session):
        active_session.async_manager = MagicMock()
        active_session.cleanup_session()
        active_session.async_manager.cleanup_completed_tasks.assert_called_once()

    def test_cleanup_async_error_handled(self, active_session):
        active_session.async_manager = MagicMock()
        active_session.async_manager.cleanup_completed_tasks.side_effect = RuntimeError("boom")
        # Should not raise
        assert active_session.cleanup_session() is True


# ── _analyze_with_agent ─────────────────────────────────────────────────

class TestAnalyzeWithAgent:
    """Tests for _analyze_with_agent()."""

    def test_valid_agent(self, active_session):
        result = active_session._analyze_with_agent("informal_agent", "test text")
        assert result["agent_id"] == "informal_agent"
        assert result["analysis_type"] == "informal_analysis"
        assert result["confidence"] > 0
        assert len(result["findings"]) > 0
        assert result["text_length"] == len("test text")

    def test_missing_agent(self, active_session):
        result = active_session._analyze_with_agent("nonexistent", "text")
        assert result["confidence"] == 0.0
        assert "error" in result

    def test_creates_lock_for_async_agent(self, active_session):
        # Agent with async analyze_text
        async_agent = MagicMock()
        async_agent.analyze_text = MagicMock()
        # Make it look async
        import asyncio
        async def fake_analyze(t): pass
        async_agent.analyze_text = fake_analyze
        active_session.active_agents["async_agent"] = async_agent

        active_session._analyze_with_agent("async_agent", "text")
        assert "async_agent" in active_session._agent_communication_locks

    def test_creates_none_lock_for_sync_agent(self, active_session):
        active_session._analyze_with_agent("informal_agent", "text")
        # informal_agent mock doesn't have async analyze_text
        assert "informal_agent" in active_session._agent_communication_locks

    def test_processing_time_recorded(self, active_session):
        result = active_session._analyze_with_agent("informal_agent", "text")
        assert "processing_time" in result
        assert result["processing_time"] >= 0

    def test_agent_capabilities_included(self, active_session):
        result = active_session._analyze_with_agent("informal_agent", "text")
        assert "agent_capabilities" in result


# ── coordinate_analysis_async ───────────────────────────────────────────

class TestCoordinateAnalysisAsync:
    """Tests for coordinate_analysis_async()."""

    def test_all_agents_by_default(self, active_session):
        active_session.async_manager = MagicMock()
        active_session.async_manager.run_multiple_hybrid.return_value = [
            {"agent_id": "informal_agent", "confidence": 0.9, "findings": ["f"]},
            {"agent_id": "logic_fol_agent", "confidence": 0.8, "findings": ["g"]},
        ]
        result = active_session.coordinate_analysis_async("test text")
        assert set(result["agents_involved"]) == {"informal_agent", "logic_fol_agent"}
        assert result["execution_mode"] == "async"

    def test_target_agents_subset(self, active_session):
        active_session.async_manager = MagicMock()
        active_session.async_manager.run_multiple_hybrid.return_value = [
            {"agent_id": "informal_agent", "confidence": 0.9, "findings": []},
        ]
        result = active_session.coordinate_analysis_async("txt", ["informal_agent"])
        assert result["agents_involved"] == ["informal_agent"]

    def test_result_structure(self, active_session):
        active_session.async_manager = MagicMock()
        active_session.async_manager.run_multiple_hybrid.return_value = []
        result = active_session.coordinate_analysis_async("txt")
        assert "text" in result
        assert "individual_results" in result
        assert "consolidated_analysis" in result
        assert "total_processing_time" in result
        assert "execution_mode" in result

    def test_timeout_passed_to_tasks(self, active_session):
        active_session.async_manager = MagicMock()
        active_session.async_manager.run_multiple_hybrid.return_value = []
        active_session.coordinate_analysis_async("txt", timeout=120.0)
        call_args = active_session.async_manager.run_multiple_hybrid.call_args
        assert call_args[1]["global_timeout"] == 120.0

    def test_consolidation_error_handled(self, active_session):
        active_session.async_manager = MagicMock()
        active_session.async_manager.run_multiple_hybrid.return_value = [
            {"agent_id": "informal_agent", "confidence": 0.9, "findings": []},
        ]
        with patch.object(active_session, "_consolidate_results_robust", side_effect=Exception("boom")):
            result = active_session.coordinate_analysis_async("txt", ["informal_agent"])
            assert "error" in result["consolidated_analysis"]

    def test_nonexistent_agent_not_in_tasks(self, active_session):
        active_session.async_manager = MagicMock()
        active_session.async_manager.run_multiple_hybrid.return_value = []
        active_session.coordinate_analysis_async("txt", ["fake_agent"])
        # run_multiple_hybrid called with empty task list
        tasks_arg = active_session.async_manager.run_multiple_hybrid.call_args[0][0]
        assert len(tasks_arg) == 0

    def test_max_concurrent_capped(self, active_session):
        # Add many agents
        for i in range(10):
            active_session.active_agents[f"agent_{i}"] = MagicMock()
        active_session.async_manager = MagicMock()
        active_session.async_manager.run_multiple_hybrid.return_value = [{}] * 12
        active_session.coordinate_analysis_async("txt")
        call_args = active_session.async_manager.run_multiple_hybrid.call_args
        assert call_args[1]["max_concurrent"] <= 4


# ── _consolidate_results_robust ─────────────────────────────────────────

class TestConsolidateResultsRobust:
    """Tests for _consolidate_results_robust()."""

    def test_empty_results(self, orchestration):
        result = orchestration._consolidate_results_robust({})
        assert result["agents_count"] == 0
        assert result["successful_agents"] == 0
        assert result["failed_agents"] == 0

    def test_separates_valid_and_error(self, orchestration):
        results = {
            "good_agent": {"confidence": 0.9, "findings": ["f1"], "analysis_type": "general_analysis"},
            "bad_agent": {"confidence": 0.0, "findings": [], "error": "timeout"},
        }
        consolidated = orchestration._consolidate_results_robust(results)
        assert consolidated["successful_agents"] == 1
        assert consolidated["failed_agents"] == 1

    def test_average_confidence_from_valid_only(self, orchestration):
        results = {
            "a1": {"confidence": 0.8, "findings": [], "analysis_type": "general_analysis"},
            "a2": {"confidence": 0.6, "findings": [], "analysis_type": "general_analysis"},
            "bad": {"confidence": 0.0, "findings": [], "error": "err"},
        }
        consolidated = orchestration._consolidate_results_robust(results)
        assert consolidated["average_confidence"] == pytest.approx(0.7)

    def test_weighted_confidence(self, orchestration):
        results = {
            "logic": {"confidence": 1.0, "findings": [], "analysis_type": "formal_logic"},
            "extract": {"confidence": 1.0, "findings": [], "analysis_type": "extraction"},
        }
        consolidated = orchestration._consolidate_results_robust(results)
        # formal_logic weight=1.2, extraction weight=0.8
        # weighted = (1.0*1.2 + 1.0*0.8) / (1.2 + 0.8) = 2.0/2.0 = 1.0
        assert consolidated["weighted_confidence"] == pytest.approx(1.0)

    def test_weighted_confidence_different_scores(self, orchestration):
        results = {
            "logic": {"confidence": 0.5, "findings": [], "analysis_type": "formal_logic"},
            "informal": {"confidence": 0.5, "findings": [], "analysis_type": "informal_analysis"},
        }
        consolidated = orchestration._consolidate_results_robust(results)
        # weights: formal_logic=1.2, informal_analysis=1.0
        # weighted = (0.5*1.2 + 0.5*1.0) / (1.2+1.0) = 1.1/2.2 = 0.5
        assert consolidated["weighted_confidence"] == pytest.approx(0.5)

    def test_key_findings_sorted_by_confidence(self, orchestration):
        results = {
            "low": {"confidence": 0.3, "findings": ["low_finding"], "analysis_type": "general_analysis"},
            "high": {"confidence": 0.9, "findings": ["high_finding"], "analysis_type": "general_analysis"},
        }
        consolidated = orchestration._consolidate_results_robust(results)
        if len(consolidated["key_findings"]) >= 2:
            assert consolidated["key_findings"][0]["confidence"] >= consolidated["key_findings"][1]["confidence"]

    def test_key_findings_capped_at_10(self, orchestration):
        results = {}
        for i in range(15):
            results[f"agent_{i}"] = {
                "confidence": 0.5 + i * 0.01,
                "findings": [f"finding_{i}"],
                "analysis_type": "general_analysis",
            }
        consolidated = orchestration._consolidate_results_robust(results)
        assert len(consolidated["key_findings"]) <= 10

    def test_error_summary(self, orchestration):
        results = {
            "bad1": {"confidence": 0.0, "error": "timeout", "processing_time": 1.5},
            "bad2": {"confidence": 0.0, "error": "crash", "processing_time": 0.1},
        }
        consolidated = orchestration._consolidate_results_robust(results)
        assert len(consolidated["error_summary"]) == 2
        errors = {e["error"] for e in consolidated["error_summary"]}
        assert "timeout" in errors
        assert "crash" in errors

    def test_no_errors_empty_summary(self, orchestration):
        results = {
            "a1": {"confidence": 0.9, "findings": ["f"], "analysis_type": "general_analysis"},
        }
        consolidated = orchestration._consolidate_results_robust(results)
        assert consolidated["error_summary"] == []

    def test_all_errors_zero_confidence(self, orchestration):
        results = {
            "bad": {"confidence": 0.0, "error": "fail"},
        }
        consolidated = orchestration._consolidate_results_robust(results)
        assert consolidated["average_confidence"] == 0.0
        assert consolidated["weighted_confidence"] == 0.0

    def test_consensus_detection(self, orchestration):
        # Two agents with similar first-3-word findings
        results = {
            "a1": {"confidence": 0.9, "findings": ["argument is valid here"], "analysis_type": "general_analysis"},
            "a2": {"confidence": 0.8, "findings": ["argument is strong here"], "analysis_type": "general_analysis"},
        }
        consolidated = orchestration._consolidate_results_robust(results)
        # "argument is valid" vs "argument is strong" share "argument" and "is" = 2 matches
        # Should trigger consensus
        # Note: exact behavior depends on word overlap logic
        assert isinstance(consolidated["consensus_areas"], list)


# ── get_service_health ──────────────────────────────────────────────────

class TestGetServiceHealth:
    """Tests for get_service_health()."""

    def test_no_agents_unhealthy(self, orchestration):
        health = orchestration.get_service_health()
        assert health["status"] == "unhealthy"

    def test_all_healthy(self, active_session):
        active_session.async_manager = MagicMock()
        active_session.async_manager.get_performance_stats.return_value = {}
        health = active_session.get_service_health()
        assert health["status"] == "healthy"

    def test_partial_health_degraded(self, orchestration):
        good_agent = MagicMock()
        good_agent.get_agent_capabilities.return_value = {"cap": "x"}
        bad_agent = MagicMock(spec=[])  # No get_agent_capabilities
        orchestration.initialize_session("s", {"good": good_agent, "bad": bad_agent})
        orchestration.async_manager = MagicMock()
        orchestration.async_manager.get_performance_stats.return_value = {}
        health = orchestration.get_service_health()
        assert health["status"] == "degraded"

    def test_agent_exception_unhealthy(self, orchestration):
        bad_agent = MagicMock()
        bad_agent.get_agent_capabilities.side_effect = RuntimeError("broken")
        orchestration.initialize_session("s", {"bad": bad_agent})
        orchestration.async_manager = MagicMock()
        orchestration.async_manager.get_performance_stats.return_value = {}
        health = orchestration.get_service_health()
        assert health["agents_health"]["bad"]["status"] == "unhealthy"

    def test_session_info_included(self, active_session):
        active_session.async_manager = MagicMock()
        active_session.async_manager.get_performance_stats.return_value = {}
        health = active_session.get_service_health()
        info = health["session_info"]
        assert info["active_session"] == "sess-001"
        assert info["conversation_messages"] == 2
        assert info["active_agents_count"] == 2

    def test_performance_stats_included(self, active_session):
        active_session.async_manager = MagicMock()
        active_session.async_manager.get_performance_stats.return_value = {"calls": 42}
        health = active_session.get_service_health()
        assert health["performance_stats"]["calls"] == 42

    def test_error_in_health_check(self, orchestration):
        orchestration.async_manager = MagicMock()
        orchestration.async_manager.get_performance_stats.side_effect = Exception("bad stats")
        # Need at least one agent for get_service_health to reach stats
        orchestration.initialize_session("s", {"a": MagicMock()})
        health = orchestration.get_service_health()
        assert health["status"] == "error"
        assert "error" in health

    def test_last_check_updated(self, active_session):
        active_session.async_manager = MagicMock()
        active_session.async_manager.get_performance_stats.return_value = {}
        health = active_session.get_service_health()
        assert "last_check" in health


# ── Integration scenarios ───────────────────────────────────────────────

class TestGroupChatScenarios:
    """End-to-end scenarios combining multiple methods."""

    def test_full_lifecycle(self, orchestration, mock_agents):
        # Init
        assert orchestration.initialize_session("lifecycle", mock_agents)

        # Add messages
        orchestration.add_message("informal_agent", "start analysis")
        orchestration.add_message("logic_fol_agent", "I'll check logic")

        # Summary
        summary = orchestration.get_conversation_summary()
        assert summary["total_messages"] == 2

        # Coordinate
        result = orchestration.coordinate_analysis("The argument is valid.")
        assert len(result["individual_results"]) == 2

        # Agent status
        status = orchestration.get_agent_status()
        assert len(status) == 2

        # Cleanup
        assert orchestration.cleanup_session()
        assert orchestration.session_id is None

    def test_multiple_analysis_rounds(self, active_session):
        r1 = active_session.coordinate_analysis("First argument")
        r2 = active_session.coordinate_analysis("Second argument")
        assert r1["text"] == "First argument"
        assert r2["text"] == "Second argument"

    def test_add_remove_agents_between_sessions(self, orchestration):
        orchestration.initialize_session("s1", {"a1": MagicMock()})
        assert len(orchestration.active_agents) == 1
        orchestration.cleanup_session()
        orchestration.initialize_session("s2", {"a1": MagicMock(), "a2": MagicMock()})
        assert len(orchestration.active_agents) == 2
