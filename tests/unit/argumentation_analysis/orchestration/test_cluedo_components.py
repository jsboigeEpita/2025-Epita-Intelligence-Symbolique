"""
Unit tests for argumentation_analysis/orchestration/cluedo_components/

Covers 6 modules at 0% coverage:
- cluedo_plugins.py
- dialogue_analyzer.py
- enhanced_logic.py
- logging_handler.py
- metrics_collector.py
- suggestion_handler.py
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta

# ============================================================================
# TestCluedoInvestigatorPlugin
# ============================================================================


class TestCluedoInvestigatorPlugin:
    """Tests for CluedoInvestigatorPlugin (cluedo_plugins.py)."""

    def _make_plugin(self, handler=None):
        from argumentation_analysis.orchestration.cluedo_components.cluedo_plugins import (
            CluedoInvestigatorPlugin,
        )

        if handler is None:
            handler = MagicMock()
            handler.force_moriarty_oracle_revelation = AsyncMock()
        return CluedoInvestigatorPlugin(suggestion_handler=handler), handler

    def test_construction(self):
        plugin, handler = self._make_plugin()
        assert plugin._suggestion_handler is handler

    async def test_make_suggestion_returns_oracle_content(self):
        plugin, handler = self._make_plugin()
        handler.force_moriarty_oracle_revelation.return_value = {
            "content": "Je possede le Chandelier!"
        }
        result = await plugin.make_suggestion(
            suspect="Colonel Moutarde", arme="Chandelier", lieu="Salon"
        )
        assert result == "Je possede le Chandelier!"
        handler.force_moriarty_oracle_revelation.assert_awaited_once()
        call_args = handler.force_moriarty_oracle_revelation.call_args
        assert call_args[0][0] == {
            "suspect": "Colonel Moutarde",
            "arme": "Chandelier",
            "lieu": "Salon",
        }
        assert call_args[0][1] == "Sherlock"

    async def test_make_suggestion_empty_oracle_response(self):
        plugin, handler = self._make_plugin()
        handler.force_moriarty_oracle_revelation.return_value = {"content": ""}
        result = await plugin.make_suggestion(
            suspect="Rose", arme="Poignard", lieu="Cuisine"
        )
        assert result == "Moriarty n'a rien à ajouter."

    async def test_make_suggestion_none_oracle_response(self):
        plugin, handler = self._make_plugin()
        handler.force_moriarty_oracle_revelation.return_value = None
        result = await plugin.make_suggestion(
            suspect="Rose", arme="Poignard", lieu="Cuisine"
        )
        assert result == "Moriarty n'a rien à ajouter."

    async def test_make_suggestion_exception_handled(self):
        plugin, handler = self._make_plugin()
        handler.force_moriarty_oracle_revelation.side_effect = RuntimeError(
            "Network error"
        )
        result = await plugin.make_suggestion(
            suspect="Rose", arme="Poignard", lieu="Cuisine"
        )
        assert "erreur" in result.lower() or "Network error" in result


# ============================================================================
# TestDialogueAnalyzer
# ============================================================================


class TestDialogueAnalyzer:
    """Tests for DialogueAnalyzer (dialogue_analyzer.py)."""

    def _make_analyzer(self):
        from argumentation_analysis.orchestration.cluedo_components.dialogue_analyzer import (
            DialogueAnalyzer,
        )

        oracle_state = MagicMock()
        oracle_state.record_contextual_reference = MagicMock()
        oracle_state.record_emotional_reaction = MagicMock()
        return DialogueAnalyzer(oracle_state=oracle_state), oracle_state

    # -- detect_message_type --

    def test_detect_revelation(self):
        analyzer, _ = self._make_analyzer()
        assert analyzer.detect_message_type("Je révèle ma carte") == "revelation"
        assert analyzer.detect_message_type("J'ai le poignard") == "revelation"
        assert analyzer.detect_message_type("Il possède la carte") == "revelation"

    def test_detect_suggestion(self):
        analyzer, _ = self._make_analyzer()
        assert (
            analyzer.detect_message_type("Je suggère Colonel Moutarde") == "suggestion"
        )
        assert analyzer.detect_message_type("Le suspect est Rose") == "suggestion"
        assert (
            analyzer.detect_message_type("L'arme utilisée est le poignard")
            == "suggestion"
        )

    def test_detect_analysis(self):
        analyzer, _ = self._make_analyzer()
        assert analyzer.detect_message_type("Mon analyse montre que...") == "analysis"
        assert analyzer.detect_message_type("Ma déduction est claire") == "analysis"
        assert analyzer.detect_message_type("Donc, le coupable est...") == "analysis"

    def test_detect_reaction(self):
        analyzer, _ = self._make_analyzer()
        assert analyzer.detect_message_type("Brillant, Watson !") == "reaction"
        assert analyzer.detect_message_type("C'est intéressant") == "reaction"
        assert analyzer.detect_message_type("Aha, c'est magistral") == "reaction"

    def test_detect_generic_message(self):
        analyzer, _ = self._make_analyzer()
        assert analyzer.detect_message_type("Bonjour tout le monde") == "message"
        assert analyzer.detect_message_type("") == "message"

    # -- analyze_contextual_elements --

    def test_contextual_reference_detected(self):
        analyzer, state = self._make_analyzer()
        history = [MagicMock(), MagicMock()]  # len > 1
        analyzer.analyze_contextual_elements(
            "Watson", "Suite à votre remarque, je pense que...", history
        )
        state.record_contextual_reference.assert_called_once()
        call_kwargs = state.record_contextual_reference.call_args[1]
        assert call_kwargs["source_agent"] == "Watson"
        assert call_kwargs["reference_type"] == "building_on"

    def test_no_contextual_reference_short_history(self):
        analyzer, state = self._make_analyzer()
        history = [MagicMock()]  # len <= 1
        analyzer.analyze_contextual_elements(
            "Watson", "Suite à votre remarque...", history
        )
        state.record_contextual_reference.assert_not_called()

    def test_no_contextual_reference_no_indicator(self):
        analyzer, state = self._make_analyzer()
        history = [MagicMock(), MagicMock()]
        analyzer.analyze_contextual_elements(
            "Watson", "Bonjour, je suis Watson", history
        )
        state.record_contextual_reference.assert_not_called()

    # -- _detect_emotional_reactions --

    def test_emotional_reaction_watson_approval(self):
        analyzer, _ = self._make_analyzer()
        # history[-2] is the trigger message (the one before current agent's turn)
        trigger_msg = MagicMock()
        trigger_msg.author_name = "Sherlock"
        trigger_msg.content = "Voici mon hypothese"
        current_msg = MagicMock()
        current_msg.author_name = "Watson"
        current_msg.content = "C'est brillant!"
        history = [trigger_msg, current_msg]
        reactions = analyzer._detect_emotional_reactions(
            "Watson", "C'est brillant, Sherlock!", history
        )
        assert len(reactions) == 1
        assert reactions[0]["reaction_type"] == "approval"
        assert reactions[0]["trigger_agent"] == "Sherlock"

    def test_emotional_reaction_moriarty_correction(self):
        analyzer, _ = self._make_analyzer()
        trigger_msg = MagicMock()
        trigger_msg.author_name = "Sherlock"
        trigger_msg.content = "C'est le Colonel"
        current_msg = MagicMock()
        current_msg.author_name = "Moriarty"
        current_msg.content = "Pas tout à fait"
        history = [trigger_msg, current_msg]
        reactions = analyzer._detect_emotional_reactions(
            "Moriarty", "Pas tout à fait, mon cher...", history
        )
        assert len(reactions) == 1
        assert reactions[0]["reaction_type"] == "correction"

    def test_emotional_reaction_empty_history(self):
        analyzer, _ = self._make_analyzer()
        reactions = analyzer._detect_emotional_reactions("Watson", "Brillant!", [])
        assert reactions == []

    def test_emotional_reaction_unknown_agent(self):
        analyzer, _ = self._make_analyzer()
        prev_msg = MagicMock()
        prev_msg.author_name = "Other"
        prev_msg.content = "test"
        history = [MagicMock(), prev_msg]
        reactions = analyzer._detect_emotional_reactions(
            "UnknownAgent", "brillant!", history
        )
        assert reactions == []

    def test_emotional_reaction_fallback_to_role(self):
        """When author_name is missing on trigger msg, falls back to role attribute."""
        analyzer, _ = self._make_analyzer()

        # history[-2] is the trigger; give it no author_name so getattr falls back to role
        class _MinimalMsg:
            def __init__(self, role, content):
                self.role = role
                self.content = content

        trigger_msg = _MinimalMsg(role="assistant", content="Some message")
        current_msg = MagicMock()
        current_msg.author_name = "Watson"
        current_msg.content = "brillant!"
        history = [trigger_msg, current_msg]
        reactions = analyzer._detect_emotional_reactions("Watson", "brillant!", history)
        assert len(reactions) == 1
        assert reactions[0]["trigger_agent"] == "assistant"


# ============================================================================
# TestEnhancedLogicHandler
# ============================================================================


class TestEnhancedLogicHandler:
    """Tests for EnhancedLogicHandler (enhanced_logic.py)."""

    def _make_handler(self, oracle_state=None, strategy="enhanced_auto_reveal"):
        from argumentation_analysis.orchestration.cluedo_components.enhanced_logic import (
            EnhancedLogicHandler,
        )

        return EnhancedLogicHandler(oracle_state=oracle_state, oracle_strategy=strategy)

    # -- analyze_suggestion_quality --

    def test_suggestion_too_short(self):
        handler = self._make_handler()
        result = handler.analyze_suggestion_quality("short")
        assert result["is_trivial"] is True
        assert result["reason"] == "suggestion_too_short"

    def test_suggestion_empty(self):
        handler = self._make_handler()
        result = handler.analyze_suggestion_quality("")
        assert result["is_trivial"] is True

    def test_suggestion_none(self):
        handler = self._make_handler()
        result = handler.analyze_suggestion_quality(None)
        assert result["is_trivial"] is True

    def test_suggestion_trivial_keyword(self):
        handler = self._make_handler()
        result = handler.analyze_suggestion_quality(
            "Je ne sais pas qui c'est, c'est difficile"
        )
        assert result["is_trivial"] is True
        assert "trivial_keyword_detected" in result["reason"]

    def test_suggestion_substantive(self):
        handler = self._make_handler()
        result = handler.analyze_suggestion_quality(
            "Colonel Moutarde dans le Salon avec le Chandelier"
        )
        assert result["is_trivial"] is False
        assert result["reason"] == "substantive_suggestion"

    # -- trigger_auto_revelation --

    def test_auto_revelation_no_oracle_state(self):
        handler = self._make_handler(oracle_state=None)
        result = handler.trigger_auto_revelation("stalled", "no progress")
        assert result["success"] is False
        assert result["reason"] == "oracle_state_not_available"

    def test_auto_revelation_no_cards(self):
        state = MagicMock()
        state.get_moriarty_cards.return_value = []
        handler = self._make_handler(oracle_state=state)
        result = handler.trigger_auto_revelation("stalled", "no progress")
        assert result["success"] is False
        assert result["reason"] == "no_cards_available"

    def test_auto_revelation_success(self):
        state = MagicMock()
        state.get_moriarty_cards.return_value = ["Chandelier", "Salon"]
        state.add_revelation = MagicMock()
        handler = self._make_handler(
            oracle_state=state, strategy="enhanced_auto_reveal"
        )
        result = handler.trigger_auto_revelation("stalled", "test context")
        assert result["success"] is True
        assert result["revealed_card"] == "Chandelier"
        assert "Chandelier" in result["revelation_text"]
        assert result["auto_triggered"] is True
        assert result["oracle_strategy"] == "enhanced_auto_reveal"
        state.add_revelation.assert_called_once()

    # -- handle_enhanced_state_transition --

    def test_state_transition_valid(self):
        handler = self._make_handler()
        result = handler.handle_enhanced_state_transition(
            "idle", "investigation_active", {"elements_jeu": {"a": 1, "b": 2}}
        )
        assert result["success"] is True
        assert result["new_state"] == "investigation_active"
        assert "auto_clue_generation" in result["enhanced_features_active"]
        assert result["context_elements"] == 2

    def test_state_transition_invalid_target(self):
        handler = self._make_handler()
        result = handler.handle_enhanced_state_transition("idle", "invalid_state", {})
        assert result["success"] is False
        assert result["new_state"] == "idle"  # stays at current
        assert "Invalid target state" in result["error"]

    def test_state_transition_idle_features(self):
        handler = self._make_handler()
        result = handler.handle_enhanced_state_transition("x", "idle", {})
        assert result["success"] is True
        assert result["enhanced_features_active"] == []

    def test_state_transition_solution_approaching(self):
        handler = self._make_handler()
        result = handler.handle_enhanced_state_transition(
            "investigation_active", "solution_approaching", {}
        )
        assert "final_hint_mode" in result["enhanced_features_active"]

    # -- execute_optimized_agent_turn --

    async def test_optimized_turn_sherlock(self):
        handler = self._make_handler()
        result = await handler.execute_optimized_agent_turn(
            "Sherlock", 1, "enhanced_cluedo"
        )
        assert result["role"] == "investigator"
        assert result["success"] is True
        assert result["performance"]["context_awareness"] == 0.75
        assert result["performance"]["efficiency"] <= 1.0

    async def test_optimized_turn_watson(self):
        handler = self._make_handler()
        result = await handler.execute_optimized_agent_turn("Watson", 2, "standard")
        assert result["role"] == "analyzer"
        assert result["performance"]["context_awareness"] == 0.60

    async def test_optimized_turn_moriarty(self):
        handler = self._make_handler()
        result = await handler.execute_optimized_agent_turn(
            "Moriarty", 0, "enhanced_cluedo"
        )
        assert result["role"] == "oracle_revealer"

    async def test_optimized_turn_unknown_agent(self):
        handler = self._make_handler()
        result = await handler.execute_optimized_agent_turn("Unknown", 1, "test")
        assert result["role"] == "generic"

    async def test_optimized_turn_efficiency_capped(self):
        """High turn number should cap efficiency at 1.0."""
        handler = self._make_handler()
        result = await handler.execute_optimized_agent_turn("Sherlock", 100, "test")
        assert result["performance"]["efficiency"] == 1.0


# ============================================================================
# TestToolCallLoggingHandler
# ============================================================================


class TestToolCallLoggingHandler:
    """Tests for ToolCallLoggingHandler (logging_handler.py)."""

    def _make_handler(self):
        from argumentation_analysis.orchestration.cluedo_components.logging_handler import (
            ToolCallLoggingHandler,
        )

        return ToolCallLoggingHandler()

    def test_construction(self):
        handler = self._make_handler()
        assert callable(handler)

    async def test_call_logs_and_invokes_next(self):
        handler = self._make_handler()

        # Build mock context
        context = MagicMock()
        context.function.metadata.plugin_name = "TestPlugin"
        context.function.metadata.name = "test_func"
        context.arguments = {"arg1": "value1", "arg2": "value2"}
        context.result = None  # No result after next

        next_fn = AsyncMock()

        await handler(context, next_fn)
        next_fn.assert_awaited_once_with(context)

    async def test_call_with_exception_in_result(self):
        handler = self._make_handler()

        context = MagicMock()
        context.function.metadata.plugin_name = "P"
        context.function.metadata.name = "f"
        context.arguments = {}
        context.result.metadata = {"exception": "SomeError"}

        next_fn = AsyncMock()
        # Should not raise
        await handler(context, next_fn)

    async def test_call_with_list_result(self):
        handler = self._make_handler()

        context = MagicMock()
        context.function.metadata.plugin_name = "P"
        context.function.metadata.name = "f"
        context.arguments = {}
        context.result.metadata = {}
        context.result.value = ["a", "b", "c", "d"]

        next_fn = AsyncMock()
        await handler(context, next_fn)

    async def test_call_with_string_result(self):
        handler = self._make_handler()

        context = MagicMock()
        context.function.metadata.plugin_name = "P"
        context.function.metadata.name = "f"
        context.arguments = {"key": "x" * 200}  # long arg, gets truncated in log
        context.result.metadata = {}
        context.result.value = "simple string result"

        next_fn = AsyncMock()
        await handler(context, next_fn)


# ============================================================================
# TestMetricsCollector
# ============================================================================


class TestMetricsCollector:
    """Tests for MetricsCollector (metrics_collector.py)."""

    def _make_collector(
        self,
        start_time=None,
        end_time=None,
        history=None,
        strategy="enhanced_auto_reveal",
        is_solution_proposed=False,
        final_solution=None,
    ):
        from argumentation_analysis.orchestration.cluedo_components.metrics_collector import (
            MetricsCollector,
        )

        oracle_state = MagicMock()
        oracle_state.is_solution_proposed = is_solution_proposed
        oracle_state.final_solution = final_solution
        oracle_state.get_solution_secrete.return_value = {
            "suspect": "Colonel Moutarde",
            "arme": "Chandelier",
            "lieu": "Salon",
        }
        oracle_state.is_game_solvable_by_elimination.return_value = False
        oracle_state.get_oracle_statistics.return_value = {
            "agent_interactions": {"total_turns": 10},
            "workflow_metrics": {
                "oracle_interactions": 3,
                "cards_revealed": 2,
            },
            "recent_revelations": [{"card": "test"}],
            "dataset_statistics": {"total_queries": 5},
        }
        oracle_state.get_fluidity_metrics.return_value = {"score": 0.8}

        if start_time is None:
            start_time = datetime(2025, 1, 1, 12, 0, 0)
        if end_time is None:
            end_time = datetime(2025, 1, 1, 12, 5, 0)  # 5 minutes
        if history is None:
            msg1 = MagicMock()
            msg1.author_name = "Sherlock"
            msg1.role = "assistant"
            msg1.content = "I suspect Colonel Moutarde"
            msg2 = MagicMock()
            msg2.author_name = "system"
            msg2.role = "system"
            msg2.content = "System message"
            history = [msg1, msg2]

        collector = MetricsCollector(
            oracle_state=oracle_state,
            start_time=start_time,
            end_time=end_time,
            history=history,
            strategy=strategy,
        )
        return collector, oracle_state

    def test_construction(self):
        collector, _ = self._make_collector()
        assert collector.strategy == "enhanced_auto_reveal"
        assert collector._auto_revelations_triggered == []
        assert collector._suggestion_quality_scores == []

    def test_collect_final_metrics_structure(self):
        collector, _ = self._make_collector()
        metrics = collector.collect_final_metrics()
        assert "solution_analysis" in metrics
        assert "conversation_history" in metrics
        assert "oracle_statistics" in metrics
        assert "performance_metrics" in metrics
        assert "phase_c_fluidity_metrics" in metrics
        assert "enhanced_metrics" in metrics
        assert "final_state" in metrics

    def test_collect_final_metrics_filters_system_messages(self):
        collector, _ = self._make_collector()
        metrics = collector.collect_final_metrics()
        senders = [m["sender"] for m in metrics["conversation_history"]]
        assert "system" not in senders

    def test_evaluate_solution_not_proposed(self):
        collector, _ = self._make_collector(is_solution_proposed=False)
        result = collector._evaluate_solution_success()
        assert result["success"] is False
        assert "Aucune solution" in result["reason"]

    def test_evaluate_solution_correct(self):
        correct = {"suspect": "Colonel Moutarde", "arme": "Chandelier", "lieu": "Salon"}
        collector, state = self._make_collector(
            is_solution_proposed=True, final_solution=correct
        )
        state.get_solution_secrete.return_value = correct
        result = collector._evaluate_solution_success()
        assert result["success"] is True
        assert result["partial_matches"]["suspect"] is True

    def test_evaluate_solution_incorrect(self):
        wrong = {"suspect": "Rose", "arme": "Poignard", "lieu": "Cuisine"}
        correct = {"suspect": "Colonel Moutarde", "arme": "Chandelier", "lieu": "Salon"}
        collector, state = self._make_collector(
            is_solution_proposed=True, final_solution=wrong
        )
        state.get_solution_secrete.return_value = correct
        result = collector._evaluate_solution_success()
        assert result["success"] is False
        assert result["partial_matches"]["suspect"] is False

    def test_no_times_gives_zero_execution(self):
        collector, _ = self._make_collector(start_time=None, end_time=None)
        # Override after construction since _make_collector sets defaults
        collector.start_time = None
        collector.end_time = None
        metrics = collector.collect_final_metrics()
        perf = metrics["performance_metrics"]
        assert perf["efficiency"]["turns_per_minute"] == 0

    def test_agent_balance_zero_turns(self):
        collector, _ = self._make_collector()
        result = collector._calculate_agent_balance({"total_turns": 0})
        assert result["sherlock"] == 0.0
        assert result["watson"] == 0.0

    def test_agent_balance_nonzero_turns(self):
        collector, _ = self._make_collector()
        result = collector._calculate_agent_balance({"total_turns": 9})
        assert result["expected_turns_per_agent"] == 3.0
        assert result["balance_score"] == 1.0

    def test_enhanced_metrics_with_scores(self):
        collector, _ = self._make_collector(strategy="enhanced_auto_reveal")
        collector._suggestion_quality_scores = [0.8, 0.6, 0.9]
        collector._auto_revelations_triggered = ["r1", "r2", "r3", "r4"]
        metrics = collector._calculate_enhanced_metrics(
            {"dataset_statistics": {"total_queries": 5}}
        )
        assert metrics["auto_revelations_count"] == 4
        assert metrics["average_suggestion_quality"] == pytest.approx(0.7667, abs=0.01)
        assert metrics["enhanced_strategy_active"] is True
        # 4/5 = 0.8 > 0.7 => high_efficiency
        assert metrics["workflow_optimization_level"] == "high_efficiency"

    def test_enhanced_metrics_medium_efficiency(self):
        collector, _ = self._make_collector(strategy="enhanced_auto_reveal")
        collector._auto_revelations_triggered = ["r1", "r2", "r3"]
        metrics = collector._calculate_enhanced_metrics(
            {"dataset_statistics": {"total_queries": 5}}
        )
        # 3/5 = 0.6 > 0.4 => medium_efficiency
        assert metrics["workflow_optimization_level"] == "medium_efficiency"

    def test_enhanced_metrics_low_efficiency(self):
        collector, _ = self._make_collector(strategy="enhanced_auto_reveal")
        collector._auto_revelations_triggered = ["r1"]
        metrics = collector._calculate_enhanced_metrics(
            {"dataset_statistics": {"total_queries": 5}}
        )
        # 1/5 = 0.2 < 0.4 => low_efficiency
        assert metrics["workflow_optimization_level"] == "low_efficiency"

    def test_enhanced_metrics_baseline(self):
        collector, _ = self._make_collector(strategy="enhanced_auto_reveal")
        metrics = collector._calculate_enhanced_metrics(
            {"dataset_statistics": {"total_queries": 0}}
        )
        assert metrics["workflow_optimization_level"] == "baseline_efficiency"

    def test_enhanced_metrics_non_enhanced_strategy(self):
        collector, _ = self._make_collector(strategy="standard")
        metrics = collector._calculate_enhanced_metrics({})
        assert metrics["enhanced_strategy_active"] is False
        assert metrics["workflow_optimization_level"] == "enhanced_auto_reveal"

    def test_enhanced_metrics_empty_scores(self):
        collector, _ = self._make_collector()
        metrics = collector._calculate_enhanced_metrics({})
        assert metrics["average_suggestion_quality"] == 0.0


# ============================================================================
# TestSuggestionHandler
# ============================================================================


class TestSuggestionHandler:
    """Tests for SuggestionHandler (suggestion_handler.py)."""

    def _make_handler(self, moriarty=None):
        from argumentation_analysis.orchestration.cluedo_components.suggestion_handler import (
            SuggestionHandler,
        )

        if moriarty is None:
            moriarty = MagicMock()
            moriarty.validate_suggestion_cluedo = AsyncMock()
        return SuggestionHandler(moriarty_agent=moriarty), moriarty

    def test_construction(self):
        handler, moriarty = self._make_handler()
        assert handler.moriarty_agent is moriarty

    async def test_force_revelation_can_refute_with_cards(self):
        handler, moriarty = self._make_handler()
        oracle_result = MagicMock()
        oracle_result.authorized = True
        oracle_result.data.can_refute = True
        oracle_result.revealed_information = ["Chandelier"]
        moriarty.validate_suggestion_cluedo.return_value = oracle_result

        result = await handler.force_moriarty_oracle_revelation(
            {"suspect": "Rose", "arme": "Chandelier", "lieu": "Salon"},
            "Sherlock",
        )
        assert result["type"] == "oracle_revelation"
        assert result["can_refute"] is True
        assert "Chandelier" in result["revealed_cards"]
        assert "Chandelier" in result["content"]

    async def test_force_revelation_can_refute_no_cards(self):
        handler, moriarty = self._make_handler()
        oracle_result = MagicMock()
        oracle_result.authorized = True
        oracle_result.data.can_refute = True
        oracle_result.revealed_information = []
        moriarty.validate_suggestion_cluedo.return_value = oracle_result

        result = await handler.force_moriarty_oracle_revelation(
            {"suspect": "Rose", "arme": "Poignard", "lieu": "Salon"},
            "Watson",
        )
        assert result["type"] == "oracle_no_refutation"
        assert result["can_refute"] is False
        assert "warning" in result

    async def test_force_revelation_cannot_refute(self):
        handler, moriarty = self._make_handler()
        oracle_result = MagicMock()
        oracle_result.authorized = True
        oracle_result.data.can_refute = False
        moriarty.validate_suggestion_cluedo.return_value = oracle_result

        result = await handler.force_moriarty_oracle_revelation(
            {"suspect": "Rose", "arme": "Poignard", "lieu": "Salon"},
            "Sherlock",
        )
        assert result["type"] == "oracle_no_refutation"
        assert result["can_refute"] is False
        assert "correcte" in result.get("warning", "").lower() or "warning" in result

    async def test_force_revelation_not_authorized(self):
        handler, moriarty = self._make_handler()
        oracle_result = MagicMock()
        oracle_result.authorized = False
        oracle_result.data = None
        moriarty.validate_suggestion_cluedo.return_value = oracle_result

        result = await handler.force_moriarty_oracle_revelation(
            {"suspect": "Rose", "arme": "Poignard", "lieu": "Salon"},
            "Sherlock",
        )
        assert result["type"] == "oracle_no_refutation"
        assert result["can_refute"] is False

    async def test_force_revelation_exception(self):
        handler, moriarty = self._make_handler()
        moriarty.validate_suggestion_cluedo.side_effect = RuntimeError("DB error")

        result = await handler.force_moriarty_oracle_revelation(
            {"suspect": "Rose", "arme": "Poignard", "lieu": "Salon"},
            "Sherlock",
        )
        assert result["type"] == "oracle_error"
        assert result["can_refute"] is False
        assert "DB error" in result["error"]

    async def test_force_revelation_suggestion_fields(self):
        """Verify the suggestion dict is passed through to oracle validation."""
        handler, moriarty = self._make_handler()
        oracle_result = MagicMock()
        oracle_result.authorized = False
        oracle_result.data = None
        moriarty.validate_suggestion_cluedo.return_value = oracle_result

        suggestion = {"suspect": "Violet", "arme": "Corde", "lieu": "Bureau"}
        await handler.force_moriarty_oracle_revelation(suggestion, "Watson")

        moriarty.validate_suggestion_cluedo.assert_awaited_once_with(
            suspect="Violet",
            arme="Corde",
            lieu="Bureau",
            suggesting_agent="Watson",
        )
