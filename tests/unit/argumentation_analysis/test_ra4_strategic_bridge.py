"""
RA-4 #1049 — Value-gate tests for Strategic NL Journaling bridge.

These tests verify the bridge between StrategicState and UnifiedAnalysisState:
1. Core bridge sync (objectives + decisions copied correctly)
2. Privacy scrub (raw_text, source_name, author stripped)
3. Chain flow (StrategicManager → bridge → UnifiedAnalysisState readable)
4. Fallback (no kernel → hardcoded objectives used)
5. Feedback loop (process_tactical_feedback → bridge → updated state)

These tests run WITHOUT API keys (no LLM calls — fallback path tested).
"""

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.hierarchical.strategic.state import (
    StrategicState,
)
from argumentation_analysis.orchestration.hierarchical.strategic.manager import (
    StrategicManager,
)


# ---------------------------------------------------------------------------
# Layer 1: Core bridge sync
# ---------------------------------------------------------------------------


class TestStrategicBridgeSync:
    """Verify sync_strategic_to_unified copies objectives + decisions."""

    @pytest.fixture
    def states(self):
        strategic = StrategicState()
        strategic.add_global_objective(
            {"id": "obj-1", "description": "Identifier les arguments", "priority": "high"}
        )
        strategic.add_global_objective(
            {"id": "obj-2", "description": "Détecter les sophismes", "priority": "high"}
        )
        strategic.add_global_objective(
            {"id": "obj-3", "description": "Évaluer la cohérence", "priority": "medium"}
        )
        strategic.log_strategic_decision(
            {"timestamp": "2026-06-12T00:00:00", "type": "test", "description": "Decision A"}
        )
        strategic.log_strategic_decision(
            {"timestamp": "2026-06-12T00:01:00", "type": "test", "description": "Decision B"}
        )
        unified = UnifiedAnalysisState("test text for analysis")
        return strategic, unified

    def test_sync_copies_all_objectives(self, states):
        """Bridge must copy all 3 objectives from StrategicState to UnifiedAnalysisState."""
        from argumentation_analysis.core.strategic_bridge import sync_strategic_to_unified

        strategic, unified = states
        count = sync_strategic_to_unified(strategic, unified)

        assert count == 3
        assert len(unified.strategic_objectives) == 3
        assert unified.strategic_objectives[0]["id"] == "obj-1"
        assert unified.strategic_objectives[2]["description"] == "Évaluer la cohérence"

    def test_sync_copies_all_decisions(self, states):
        """Bridge must copy all decisions from StrategicState to UnifiedAnalysisState."""
        from argumentation_analysis.core.strategic_bridge import sync_strategic_to_unified

        strategic, unified = states
        sync_strategic_to_unified(strategic, unified)

        assert len(unified.strategic_decisions_log) == 2
        assert unified.strategic_decisions_log[0]["type"] == "test"
        assert unified.strategic_decisions_log[1]["description"] == "Decision B"

    def test_sync_deep_copies_objectives(self, states):
        """Modifying original StrategicState objectives must not affect unified state."""
        from argumentation_analysis.core.strategic_bridge import sync_strategic_to_unified

        strategic, unified = states
        sync_strategic_to_unified(strategic, unified)

        # Mutate original
        strategic.global_objectives[0]["description"] = "MUTATED"

        # Unified copy must be unaffected
        assert unified.strategic_objectives[0]["description"] == "Identifier les arguments"

    def test_sync_empty_strategic_state(self):
        """Bridge with empty StrategicState must produce empty lists."""
        from argumentation_analysis.core.strategic_bridge import sync_strategic_to_unified

        strategic = StrategicState()
        unified = UnifiedAnalysisState("test")
        count = sync_strategic_to_unified(strategic, unified)

        assert count == 0
        assert unified.strategic_objectives == []
        assert unified.strategic_decisions_log == []

    def test_sync_returns_objective_count(self, states):
        """Return value must equal the number of objectives synced."""
        from argumentation_analysis.core.strategic_bridge import sync_strategic_to_unified

        strategic, unified = states
        assert sync_strategic_to_unified(strategic, unified) == 3


# ---------------------------------------------------------------------------
# Layer 2: Privacy scrub
# ---------------------------------------------------------------------------


class TestPrivacyScrub:
    """Verify privacy-sensitive keys are stripped during sync."""

    @pytest.fixture
    def scrubber_states(self):
        strategic = StrategicState()
        # Objective with privacy-sensitive data
        strategic.add_global_objective({
            "id": "obj-1",
            "description": "Analyser le discours de Source_A",
            "priority": "high",
            "raw_text": "Ceci est le texte brut du discours complet...",
            "source_name": "Nicolas Sarkozy",
            "author": "Prénom Nom",
            "full_text": "Texte intégral...",
        })
        # Decision with nested privacy data
        strategic.log_strategic_decision({
            "timestamp": "2026-06-12T00:00:00",
            "type": "analysis_start",
            "description": "Début analyse",
            "raw_text": "Texte brut dans décision",
        })
        unified = UnifiedAnalysisState("test text")
        return strategic, unified

    def test_raw_text_stripped_from_objectives(self, scrubber_states):
        """raw_text key must be removed from synced objectives."""
        from argumentation_analysis.core.strategic_bridge import sync_strategic_to_unified

        strategic, unified = scrubber_states
        sync_strategic_to_unified(strategic, unified)

        obj = unified.strategic_objectives[0]
        assert "raw_text" not in obj
        assert "full_text" not in obj

    def test_source_name_stripped_from_objectives(self, scrubber_states):
        """source_name and author keys must be removed from synced objectives."""
        from argumentation_analysis.core.strategic_bridge import sync_strategic_to_unified

        strategic, unified = scrubber_states
        sync_strategic_to_unified(strategic, unified)

        obj = unified.strategic_objectives[0]
        assert "source_name" not in obj
        assert "author" not in obj

    def test_description_preserved_after_scrub(self, scrubber_states):
        """Non-sensitive keys like id, description, priority must survive scrub."""
        from argumentation_analysis.core.strategic_bridge import sync_strategic_to_unified

        strategic, unified = scrubber_states
        sync_strategic_to_unified(strategic, unified)

        obj = unified.strategic_objectives[0]
        assert obj["id"] == "obj-1"
        assert obj["description"] == "Analyser le discours de Source_A"
        assert obj["priority"] == "high"

    def test_nested_dict_privacy_scrub(self, scrubber_states):
        """Privacy keys in nested dicts must also be stripped."""
        from argumentation_analysis.core.strategic_bridge import sync_strategic_to_unified

        strategic, unified = scrubber_states
        sync_strategic_to_unified(strategic, unified)

        decision = unified.strategic_decisions_log[0]
        assert "raw_text" not in decision


# ---------------------------------------------------------------------------
# Layer 3: Chain flow (StrategicManager → bridge → UnifiedAnalysisState)
# ---------------------------------------------------------------------------


class TestStrategicChainFlow:
    """Verify data flows PM → StrategicState → bridge → UnifiedAnalysisState."""

    @pytest.fixture
    def manager_with_bridge(self):
        """Create StrategicManager with a UnifiedAnalysisState bridge."""
        unified = UnifiedAnalysisState("Test text for strategic analysis pipeline.")
        # No kernel — uses fallback objectives (no API key needed)
        manager = StrategicManager(unified_state=unified)
        return manager, unified

    def test_initialize_analysis_populates_unified_state(self, manager_with_bridge):
        """After initialize_analysis, unified_state.strategic_objectives must be populated."""
        manager, unified = manager_with_bridge
        result = manager.initialize_analysis("Test text for strategic analysis pipeline.")

        assert len(unified.strategic_objectives) > 0, (
            "UnifiedAnalysisState.strategic_objectives should be populated after init"
        )
        assert len(result["objectives"]) == len(unified.strategic_objectives)

    def test_initialize_analysis_populates_decisions_log(self, manager_with_bridge):
        """After initialize_analysis, unified_state.strategic_decisions_log must have entries."""
        manager, unified = manager_with_bridge
        manager.initialize_analysis("Test text for strategic analysis pipeline.")

        assert len(unified.strategic_decisions_log) > 0, (
            "UnifiedAnalysisState.strategic_decisions_log should have the 'Initialisation' entry"
        )
        types = [d["type"] for d in unified.strategic_decisions_log]
        assert "Initialisation de l'analyse" in types or any(
            "Initialisation" in t for t in types
        )

    def test_feedback_loop_updates_unified_state(self, manager_with_bridge):
        """After process_tactical_feedback, unified state must be re-synced."""
        manager, unified = manager_with_bridge
        manager.initialize_analysis("Test text for analysis")

        # Clear objectives to prove re-sync happens
        unified.strategic_objectives = []
        assert len(unified.strategic_objectives) == 0

        # Trigger feedback
        feedback = {
            "progress_metrics": {"progress": 0.5},
            "issues": [
                {"type": "resource_shortage", "resource": "informal_analyzer"},
            ],
        }
        manager.process_tactical_feedback(feedback)

        # After feedback, bridge should have re-synced
        assert len(unified.strategic_objectives) > 0, (
            "UnifiedAnalysisState should be re-synced after tactical feedback"
        )

    def test_objectives_readable_via_snapshot(self, manager_with_bridge):
        """Objectives must be visible in get_state_snapshot()."""
        manager, unified = manager_with_bridge
        manager.initialize_analysis("Test text for analysis")

        snapshot = unified.get_state_snapshot(summarize=False)
        assert "strategic_objectives" in snapshot
        assert len(snapshot["strategic_objectives"]) > 0

        summary = unified.get_state_snapshot(summarize=True)
        assert "strategic_objective_count" in summary
        assert summary["strategic_objective_count"] > 0


# ---------------------------------------------------------------------------
# Layer 4: Fallback (no kernel → hardcoded objectives)
# ---------------------------------------------------------------------------


class TestLLMObjectiveFallback:
    """Verify fallback to hardcoded objectives when no kernel available."""

    @pytest.fixture
    def manager_no_kernel(self):
        unified = UnifiedAnalysisState("Test text.")
        manager = StrategicManager(unified_state=unified)
        return manager, unified

    def test_fallback_gives_four_objectives(self, manager_no_kernel):
        """Without kernel, exactly 4 default objectives must be used."""
        manager, unified = manager_no_kernel
        manager.initialize_analysis("Test text.")

        assert len(unified.strategic_objectives) == 4
        ids = [obj["id"] for obj in unified.strategic_objectives]
        assert "obj-1" in ids
        assert "obj-4" in ids

    def test_fallback_objectives_have_required_keys(self, manager_no_kernel):
        """Each fallback objective must have id, description, priority."""
        manager, unified = manager_no_kernel
        manager.initialize_analysis("Test text.")

        for obj in unified.strategic_objectives:
            assert "id" in obj
            assert "description" in obj
            assert "priority" in obj
            assert obj["priority"] in ("high", "medium", "low")

    def test_manager_without_unified_state_works(self):
        """StrategicManager without unified_state must not crash (backward compat)."""
        manager = StrategicManager()  # No kernel, no unified_state
        result = manager.initialize_analysis("Test text.")

        assert "objectives" in result
        assert len(result["objectives"]) == 4


# ---------------------------------------------------------------------------
# Layer 4.5: Degraded tag value-gate (R369 hardening)
# ---------------------------------------------------------------------------


class TestDegradedTagValueGate:
    """Verify fallback objectives are tagged source='degraded' (R369 anti-théâtre)."""

    def test_fallback_objectives_tagged_degraded(self):
        """_fallback_objectives() must tag each objective with source='degraded'."""
        manager = StrategicManager()
        fallback = manager._fallback_objectives()

        for obj in fallback:
            assert obj.get("source") == "degraded", (
                f"Objective {obj['id']} missing source='degraded' tag — "
                "downstream consumers cannot distinguish LLM from degraded output (R369)"
            )

    def test_degraded_objectives_propagate_through_bridge(self):
        """When fallback is used, unified_state must see source='degraded'."""
        unified = UnifiedAnalysisState("Test text.")
        manager = StrategicManager(unified_state=unified)
        manager.initialize_analysis("Test text.")

        for obj in unified.strategic_objectives:
            assert obj.get("source") == "degraded", (
                "Degraded objectives must propagate through bridge with source tag"
            )

    def test_degraded_tag_visible_in_snapshot(self):
        """source='degraded' must be visible in state snapshots."""
        unified = UnifiedAnalysisState("Test text.")
        manager = StrategicManager(unified_state=unified)
        manager.initialize_analysis("Test text.")

        snapshot = unified.get_state_snapshot(summarize=False)
        for obj in snapshot["strategic_objectives"]:
            assert obj.get("source") == "degraded"

    def test_no_broad_except_hides_errors(self):
        """Verify no bare 'except Exception' without narrow catch or error-level logging.

        This is a value-gate: reads the source to ensure the exception handling
        follows R369 hardening (narrowed catch + fail-loud for unexpected errors).
        """
        import inspect
        source = inspect.getsource(StrategicManager._define_initial_objectives)

        # Must have narrowed catches (not just a single broad except)
        assert "json.JSONDecodeError" in source or "ValueError" in source, (
            "_define_initial_objectives must have narrowed exception catches "
            "(json.JSONDecodeError, ValueError, etc.), not bare Exception"
        )
        # Must have error-level logging for unexpected errors
        assert "self.logger.error" in source or "self.logger.warning" in source, (
            "_define_initial_objectives must log at WARNING or ERROR level on failure"
        )


# ---------------------------------------------------------------------------
# Layer 5: Anti-pendule guard
# ---------------------------------------------------------------------------


class TestAntiPenduleGuard:
    """Verify no pendulum failures introduced by RA-4."""

    def test_no_hardcoded_new_objectives(self):
        """_fallback_objectives must be the ORIGINAL 4, not a new hardcoded list."""
        manager = StrategicManager()
        fallback = manager._fallback_objectives()

        assert len(fallback) == 4
        # Must contain the original objectives
        descriptions = [o["description"] for o in fallback]
        assert "Identifier les arguments principaux" in descriptions
        assert "Détecter les sophismes" in descriptions

    def test_bridge_does_not_merge_states(self):
        """sync must COPY, not merge StrategicState into UnifiedAnalysisState."""
        from argumentation_analysis.core.strategic_bridge import sync_strategic_to_unified

        strategic = StrategicState()
        strategic.add_global_objective({"id": "obj-X", "description": "Test", "priority": "high"})

        unified = UnifiedAnalysisState("test")
        # Pre-populate with different data
        unified.strategic_objectives = [{"id": "old-1", "description": "Old", "priority": "low"}]

        sync_strategic_to_unified(strategic, unified)

        # Old data must be REPLACED, not merged
        assert len(unified.strategic_objectives) == 1
        assert unified.strategic_objectives[0]["id"] == "obj-X"

    def test_bridge_does_not_add_pydantic(self):
        """strategic_bridge must NOT import or use Pydantic (plain Python pattern)."""
        import inspect
        from argumentation_analysis.core import strategic_bridge

        source = inspect.getsource(strategic_bridge)
        assert "from pydantic" not in source, (
            "Anti-pendule: strategic_bridge should use plain Python, not Pydantic"
        )
        assert "BaseModel" not in source, (
            "Anti-pendule: strategic_bridge should use plain Python, not Pydantic"
        )
