"""Unit tests for Track A Tweety handlers (#55-#62).

Tests handler initialization and logic using mocked JPype/JVM classes.
Each handler is tested independently with mock Java objects.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
import sys

# --- Mock JPype setup ---
# Handlers import jpype at module level, so we mock it before importing.


def _make_mock_jpype():
    """Create a mock jpype module with JClass support."""
    mock_jpype = MagicMock()
    mock_jpype.JException = Exception

    # Track JClass calls so we can verify correct Java classes are loaded
    class_registry = {}

    def mock_jclass(class_name, loader=None):
        if class_name not in class_registry:
            cls = MagicMock(name=f"JClass({class_name})")
            # Make instances callable (constructors)
            instance = MagicMock(name=f"instance({class_name})")
            cls.return_value = instance
            class_registry[class_name] = cls
        return class_registry[class_name]

    mock_jpype.JClass = mock_jclass
    return mock_jpype, class_registry


# =====================================================================
# Ranking Handler Tests (#55)
# =====================================================================


class TestRankingHandler:
    """Test RankingHandler with mocked JVM."""

    def _make_handler(self):
        mock_jpype, registry = _make_mock_jpype()
        with patch.dict(sys.modules, {"jpype": mock_jpype}):
            # Force reimport
            from importlib import reload
            import argumentation_analysis.agents.core.logic.ranking_handler as mod

            reload(mod)

            handler = mod.RankingHandler()
            return handler, mock_jpype, registry

    def test_init_loads_dung_classes(self):
        handler, mock_jpype, registry = self._make_handler()
        assert "org.tweetyproject.arg.dung.syntax.DungTheory" in registry
        assert "org.tweetyproject.arg.dung.syntax.Argument" in registry
        assert "org.tweetyproject.arg.dung.syntax.Attack" in registry

    def test_rank_arguments_basic(self):
        handler, mock_jpype, registry = self._make_handler()

        # Setup mock ranking result
        mock_ranking = MagicMock()
        mock_ranking.isStrictlyMoreAcceptableThan.return_value = True

        reasoner_cls = registry.get(
            "org.tweetyproject.arg.rankings.reasoner.CategorizerRankingReasoner"
        )
        if reasoner_cls:
            reasoner_cls.return_value.getModel.return_value = mock_ranking

        result = handler.rank_arguments(
            arguments=["a", "b", "c"],
            attacks=[["b", "a"]],
            method="categorizer",
        )
        assert result["method"] == "categorizer"
        assert "a" in result["arguments"]
        assert "b" in result["arguments"]
        assert "c" in result["arguments"]
        assert result["statistics"]["arguments_count"] == 3
        assert result["statistics"]["attacks_count"] == 1

    def test_invalid_reasoner_raises(self):
        handler, _, _ = self._make_handler()
        with pytest.raises((ValueError, RuntimeError)):
            handler.rank_arguments(["a"], [], method="nonexistent")

    def test_available_reasoners(self):
        handler, _, _ = self._make_handler()
        expected = {
            "categorizer",
            "burden",
            "discussion",
            "counting",
            "tuples",
            "strategy",
            "propagation",
        }
        assert set(handler.REASONERS.keys()) == expected


# =====================================================================
# Bipolar Handler Tests (#60)
# =====================================================================


class TestBipolarHandler:
    """Test BipolarHandler with mocked JVM."""

    def _make_handler(self):
        mock_jpype, registry = _make_mock_jpype()
        with patch.dict(sys.modules, {"jpype": mock_jpype}):
            from importlib import reload
            import argumentation_analysis.agents.core.logic.bipolar_handler as mod

            reload(mod)
            return mod.BipolarHandler(), mock_jpype, registry

    def test_init_loads_bipolar_classes(self):
        handler, _, registry = self._make_handler()
        assert (
            "org.tweetyproject.arg.bipolar.syntax.NecessityArgumentationFramework"
            in registry
        )
        assert "org.tweetyproject.arg.bipolar.syntax.BArgument" in registry

    def test_analyze_necessity_framework(self):
        handler, _, _ = self._make_handler()
        result = handler.analyze_bipolar_framework(
            arguments=["a", "b", "c"],
            attacks=[["a", "b"]],
            supports=[["c", "a"]],
            framework_type="necessity",
        )
        assert result["framework_type"] == "necessity"
        assert result["statistics"]["arguments_count"] == 3
        assert result["statistics"]["attacks_count"] == 1
        assert result["statistics"]["supports_count"] == 1

    def test_analyze_evidential_framework(self):
        handler, _, _ = self._make_handler()
        result = handler.analyze_bipolar_framework(
            arguments=["x", "y"],
            attacks=[],
            supports=[["x", "y"]],
            framework_type="evidential",
        )
        assert result["framework_type"] == "evidential"
        assert result["statistics"]["supports_count"] == 1


# =====================================================================
# ABA Handler Tests (#58)
# =====================================================================


class TestABAHandler:
    """Test ABAHandler with mocked JVM."""

    def _make_handler(self):
        mock_jpype, registry = _make_mock_jpype()
        with patch.dict(sys.modules, {"jpype": mock_jpype}):
            from importlib import reload
            import argumentation_analysis.agents.core.logic.aba_handler as mod

            reload(mod)
            return mod.ABAHandler(), mock_jpype, registry

    def test_init_loads_aba_classes(self):
        handler, _, registry = self._make_handler()
        assert "org.tweetyproject.arg.aba.syntax.AbaTheory" in registry
        assert "org.tweetyproject.arg.aba.syntax.Assumption" in registry

    def test_analyze_aba_basic(self):
        handler, _, registry = self._make_handler()
        # Mock the reasoner to return empty extensions
        mock_extensions = []
        reasoner_cls = registry.get(
            "org.tweetyproject.arg.aba.reasoner.PreferredReasoner"
        )
        if reasoner_cls:
            reasoner_cls.return_value.getModels.return_value = mock_extensions

        result = handler.analyze_aba_framework(
            assumptions=["a", "b"],
            rules=[{"head": "c", "body": ["a", "b"]}],
            semantics="preferred",
        )
        assert result["semantics"] == "preferred"
        assert result["statistics"]["assumptions_count"] == 2
        assert result["statistics"]["rules_count"] == 1

    def test_available_semantics(self):
        handler, _, _ = self._make_handler()
        expected = {"preferred", "stable", "complete", "well_founded", "ideal", "flat"}
        assert set(handler.REASONERS.keys()) == expected

    def test_invalid_semantics_raises(self):
        handler, _, _ = self._make_handler()
        with pytest.raises((ValueError, RuntimeError)):
            handler.analyze_aba_framework(["a"], [], semantics="nonexistent")


# =====================================================================
# ADF Handler Tests (#61)
# =====================================================================


class TestADFHandler:
    """Test ADFHandler with mocked JVM."""

    def _make_handler(self):
        mock_jpype, registry = _make_mock_jpype()
        with patch.dict(sys.modules, {"jpype": mock_jpype}):
            from importlib import reload
            import argumentation_analysis.agents.core.logic.adf_handler as mod

            reload(mod)
            return mod.ADFHandler(), mock_jpype, registry

    def test_init_loads_adf_classes(self):
        handler, _, registry = self._make_handler()
        assert (
            "org.tweetyproject.arg.adf.syntax.adf.GraphAbstractDialecticalFramework"
            in registry
        )
        assert "org.tweetyproject.arg.adf.syntax.Argument" in registry

    def test_analyze_adf_basic(self):
        handler, _, registry = self._make_handler()
        # Mock builder pattern
        mock_builder = MagicMock()
        mock_adf = MagicMock()
        mock_builder.build.return_value = mock_adf

        adf_cls = registry.get(
            "org.tweetyproject.arg.adf.syntax.adf.GraphAbstractDialecticalFramework"
        )
        if adf_cls:
            adf_cls.builder.return_value = mock_builder

        # Mock reasoner
        reasoner_cls = registry.get("org.tweetyproject.arg.adf.reasoner.GroundReasoner")
        if reasoner_cls:
            reasoner_cls.return_value.getModels.return_value = []

        result = handler.analyze_adf(
            statements=["s1", "s2"],
            acceptance_conditions={"s1": "tautology", "s2": "negation:s1"},
            semantics="grounded",
        )
        assert result["semantics"] == "grounded"
        assert result["statistics"]["statements_count"] == 2

    def test_available_semantics(self):
        handler, _, _ = self._make_handler()
        expected = {
            "grounded",
            "complete",
            "preferred",
            "admissible",
            "model",
            "naive",
            "conflict_free",
        }
        assert set(handler.REASONERS.keys()) == expected


# =====================================================================
# ASPIC+ Handler Tests (#56)
# =====================================================================


class TestASPICHandler:
    """Test ASPICHandler with mocked JVM."""

    def _make_handler(self):
        mock_jpype, registry = _make_mock_jpype()
        with patch.dict(sys.modules, {"jpype": mock_jpype}):
            from importlib import reload
            import argumentation_analysis.agents.core.logic.aspic_handler as mod

            reload(mod)
            return mod.ASPICHandler(), mock_jpype, registry

    def test_init_loads_aspic_classes(self):
        handler, _, registry = self._make_handler()
        assert "org.tweetyproject.arg.aspic.syntax.AspicArgumentationTheory" in registry
        assert "org.tweetyproject.arg.aspic.syntax.StrictInferenceRule" in registry
        assert "org.tweetyproject.arg.aspic.syntax.DefeasibleInferenceRule" in registry

    def test_analyze_aspic_basic(self):
        handler, _, registry = self._make_handler()
        # Mock reasoner
        reasoner_cls = registry.get(
            "org.tweetyproject.arg.aspic.reasoner.SimpleAspicReasoner"
        )
        if reasoner_cls:
            reasoner_cls.return_value.getModels.return_value = []

        result = handler.analyze_aspic_framework(
            strict_rules=[{"head": "c", "body": ["a", "b"]}],
            defeasible_rules=[{"head": "d", "body": ["c"], "name": "r1"}],
            axioms=["a", "b"],
        )
        assert result["statistics"]["strict_rules_count"] == 1
        assert result["statistics"]["defeasible_rules_count"] == 1
        assert result["statistics"]["axioms_count"] == 2

    def test_directional_reasoner(self):
        handler, _, registry = self._make_handler()
        reasoner_cls = registry.get(
            "org.tweetyproject.arg.aspic.reasoner.DirectionalAspicReasoner"
        )
        if reasoner_cls:
            reasoner_cls.return_value.getModels.return_value = []

        result = handler.analyze_aspic_framework(
            strict_rules=[],
            defeasible_rules=[{"head": "a", "body": []}],
            reasoner_type="directional",
        )
        assert result["reasoner_type"] == "directional"


# =====================================================================
# Belief Revision Handler Tests (#57)
# =====================================================================


class TestBeliefRevisionHandler:
    """Test BeliefRevisionHandler with mocked JVM."""

    def _make_handler(self):
        mock_jpype, registry = _make_mock_jpype()
        with patch.dict(sys.modules, {"jpype": mock_jpype}):
            from importlib import reload
            import argumentation_analysis.agents.core.logic.belief_revision_handler as mod

            reload(mod)
            return mod.BeliefRevisionHandler(), mock_jpype, registry

    def test_init_loads_revision_classes(self):
        handler, _, registry = self._make_handler()
        assert "org.tweetyproject.logics.pl.syntax.PlBeliefSet" in registry
        assert "org.tweetyproject.beliefdynamics.revops.DalalRevision" in registry
        assert (
            "org.tweetyproject.beliefdynamics.kernels.KernelContractionOperator"
            in registry
        )

    def test_revise_dalal(self):
        handler, _, registry = self._make_handler()
        # Mock revision operator
        mock_revised = MagicMock()
        mock_revised.__iter__ = MagicMock(
            return_value=iter(
                [MagicMock(__str__=lambda s: "a"), MagicMock(__str__=lambda s: "b")]
            )
        )

        dalal = registry.get("org.tweetyproject.beliefdynamics.revops.DalalRevision")
        if dalal:
            dalal.return_value.revise.return_value = mock_revised

        result = handler.revise(
            belief_set=["a", "b"],
            new_belief="c",
            method="dalal",
        )
        assert result["method"] == "dalal"
        assert result["original"] == ["a", "b"]
        assert result["new_belief"] == "c"

    def test_revise_levi(self):
        handler, _, _ = self._make_handler()
        # Levi uses KernelContraction + DefaultExpansion internally
        result = handler.revise(
            belief_set=["p"],
            new_belief="q",
            method="levi",
        )
        assert result["method"] == "levi"

    def test_contract(self):
        handler, _, registry = self._make_handler()
        mock_contracted = MagicMock()
        mock_contracted.__iter__ = MagicMock(return_value=iter([]))

        kernel = registry.get(
            "org.tweetyproject.beliefdynamics.kernels.KernelContractionOperator"
        )
        if kernel:
            kernel.return_value.contract.return_value = mock_contracted

        result = handler.contract(
            belief_set=["a", "b"],
            formula_to_remove="a",
        )
        assert result["operation"] == "contraction"
        assert result["removed"] == "a"

    def test_revise_returns_statistics(self):
        handler, _, registry = self._make_handler()
        mock_revised = MagicMock()
        mock_revised.__iter__ = MagicMock(
            return_value=iter(
                [MagicMock(__str__=lambda s: "a"), MagicMock(__str__=lambda s: "b")]
            )
        )
        dalal = registry.get("org.tweetyproject.beliefdynamics.revops.DalalRevision")
        if dalal:
            dalal.return_value.revise.return_value = mock_revised

        result = handler.revise(["a"], "b", method="dalal")
        assert "statistics" in result
        assert result["statistics"]["original_size"] == 1
        assert result["statistics"]["revised_size"] == 2

    def test_contract_returns_statistics(self):
        handler, _, registry = self._make_handler()
        mock_contracted = MagicMock()
        mock_contracted.__iter__ = MagicMock(return_value=iter([]))
        kernel = registry.get(
            "org.tweetyproject.beliefdynamics.kernels.KernelContractionOperator"
        )
        if kernel:
            kernel.return_value.contract.return_value = mock_contracted

        result = handler.contract(["a", "b", "c"], "b")
        assert result["statistics"]["original_size"] == 3
        assert result["statistics"]["contracted_size"] == 0

    def test_revise_with_negated_formula(self):
        handler, _, registry = self._make_handler()
        mock_revised = MagicMock()
        mock_revised.__iter__ = MagicMock(
            return_value=iter([MagicMock(__str__=lambda s: "!a")])
        )
        dalal = registry.get("org.tweetyproject.beliefdynamics.revops.DalalRevision")
        if dalal:
            dalal.return_value.revise.return_value = mock_revised

        result = handler.revise(["a"], "!a", method="dalal")
        assert result["new_belief"] == "!a"

    def test_revise_empty_belief_set(self):
        handler, _, registry = self._make_handler()
        mock_revised = MagicMock()
        mock_revised.__iter__ = MagicMock(
            return_value=iter([MagicMock(__str__=lambda s: "p")])
        )
        dalal = registry.get("org.tweetyproject.beliefdynamics.revops.DalalRevision")
        if dalal:
            dalal.return_value.revise.return_value = mock_revised

        result = handler.revise([], "p", method="dalal")
        assert result["statistics"]["original_size"] == 0
        assert result["statistics"]["revised_size"] == 1

    def test_contract_single_formula(self):
        handler, _, registry = self._make_handler()
        mock_contracted = MagicMock()
        mock_contracted.__iter__ = MagicMock(return_value=iter([]))
        kernel = registry.get(
            "org.tweetyproject.beliefdynamics.kernels.KernelContractionOperator"
        )
        if kernel:
            kernel.return_value.contract.return_value = mock_contracted

        result = handler.contract(["x"], "x")
        assert result["removed"] == "x"
        assert result["statistics"]["contracted_size"] == 0

    def test_revise_dalal_vs_levi_different_results(self):
        """Both methods should work on the same input without errors."""
        handler, _, registry = self._make_handler()
        mock_revised_dalal = MagicMock()
        mock_revised_dalal.__iter__ = MagicMock(
            return_value=iter([MagicMock(__str__=lambda s: "a")])
        )
        dalal = registry.get("org.tweetyproject.beliefdynamics.revops.DalalRevision")
        if dalal:
            dalal.return_value.revise.return_value = mock_revised_dalal

        result_d = handler.revise(["a", "b"], "c", method="dalal")
        result_l = handler.revise(["a", "b"], "c", method="levi")
        assert result_d["method"] == "dalal"
        assert result_l["method"] == "levi"
        assert result_d["original"] == result_l["original"]

    def test_revised_formulas_are_sorted(self):
        handler, _, registry = self._make_handler()
        mock_revised = MagicMock()
        mock_revised.__iter__ = MagicMock(
            return_value=iter(
                [
                    MagicMock(__str__=lambda s: "c"),
                    MagicMock(__str__=lambda s: "a"),
                    MagicMock(__str__=lambda s: "b"),
                ]
            )
        )
        dalal = registry.get("org.tweetyproject.beliefdynamics.revops.DalalRevision")
        if dalal:
            dalal.return_value.revise.return_value = mock_revised

        result = handler.revise(["a"], "b", method="dalal")
        assert result["revised"] == sorted(result["revised"])


# =====================================================================
# Probabilistic Handler Tests (#59)
# =====================================================================


class TestProbabilisticHandler:
    """Test ProbabilisticHandler with mocked JVM."""

    def _make_handler(self):
        mock_jpype, registry = _make_mock_jpype()
        with patch.dict(sys.modules, {"jpype": mock_jpype}):
            from importlib import reload
            import argumentation_analysis.agents.core.logic.probabilistic_handler as mod

            reload(mod)
            return mod.ProbabilisticHandler(), mock_jpype, registry

    def test_init_loads_probability_classes(self):
        handler, _, registry = self._make_handler()
        assert "org.tweetyproject.arg.dung.syntax.DungTheory" in registry
        assert "org.tweetyproject.math.probability.Probability" in registry

    def test_analyze_basic(self):
        handler, _, registry = self._make_handler()
        # Mock grounded reasoner for subgraph computation
        grounded_cls = registry.get(
            "org.tweetyproject.arg.dung.reasoner.SimpleGroundedReasoner"
        )
        if grounded_cls:
            mock_ext = MagicMock()
            mock_ext.__iter__ = MagicMock(return_value=iter([]))
            grounded_cls.return_value.getModel.return_value = mock_ext

        result = handler.analyze_probabilistic_framework(
            arguments=["a", "b"],
            attacks=[["a", "b"]],
            probabilities={"a": 0.8, "b": 0.6},
        )
        assert result["statistics"]["arguments_count"] == 2
        assert result["statistics"]["attacks_count"] == 1
        assert "acceptance_probabilities" in result


# =====================================================================
# Dialogue Handler Tests (#62)
# =====================================================================


class TestDialogueHandler:
    """Test DialogueHandler with mocked JVM."""

    def _make_handler(self):
        mock_jpype, registry = _make_mock_jpype()
        with patch.dict(sys.modules, {"jpype": mock_jpype}):
            from importlib import reload
            import argumentation_analysis.agents.core.logic.dialogue_handler as mod

            reload(mod)
            return mod.DialogueHandler(), mock_jpype, registry

    def test_init_loads_dung_classes(self):
        handler, _, registry = self._make_handler()
        assert "org.tweetyproject.arg.dung.syntax.DungTheory" in registry
        assert "org.tweetyproject.arg.dung.reasoner.SimpleGroundedReasoner" in registry

    def test_execute_dialogue_basic(self):
        handler, _, registry = self._make_handler()
        # Mock grounded extension
        grounded_cls = registry.get(
            "org.tweetyproject.arg.dung.reasoner.SimpleGroundedReasoner"
        )
        if grounded_cls:
            mock_ext = MagicMock()
            mock_arg = MagicMock()
            mock_arg.getName.return_value = "a"
            mock_ext.__iter__ = MagicMock(return_value=iter([mock_arg]))
            grounded_cls.return_value.getModel.return_value = mock_ext

        result = handler.execute_dialogue(
            proponent_args=["a", "c"],
            proponent_attacks=[["c", "b"]],
            opponent_args=["b"],
            opponent_attacks=[["b", "a"]],
            topic="a",
            max_rounds=5,
        )
        assert result["topic"] == "a"
        assert result["outcome"] in ("accepted", "rejected")
        assert len(result["dialogue_trace"]) >= 1
        assert result["dialogue_trace"][0]["speaker"] == "proponent"
        assert result["statistics"]["total_arguments"] >= 2

    def test_empty_dialogue(self):
        handler, _, registry = self._make_handler()
        grounded_cls = registry.get(
            "org.tweetyproject.arg.dung.reasoner.SimpleGroundedReasoner"
        )
        if grounded_cls:
            mock_ext = MagicMock()
            mock_ext.__iter__ = MagicMock(return_value=iter([]))
            grounded_cls.return_value.getModel.return_value = mock_ext

        result = handler.execute_dialogue(
            proponent_args=["topic"],
            proponent_attacks=[],
            opponent_args=[],
            opponent_attacks=[],
            topic="topic",
        )
        assert result["statistics"]["total_arguments"] == 1
        assert result["statistics"]["total_attacks"] == 0


# =====================================================================
# Registry Integration Test
# =====================================================================


class TestTrackARegistration:
    """Test that Track A handlers are properly registered."""

    def test_tweety_slots_registered_as_services(self):
        """Verify _declare_tweety_slots registers services, not just slots."""
        from unittest.mock import MagicMock
        from argumentation_analysis.orchestration.unified_pipeline import (
            _declare_tweety_slots,
        )

        mock_registry = MagicMock()
        _declare_tweety_slots(mock_registry)

        # Should call register_service for each handler
        assert mock_registry.register_service.call_count == 16

        # Check capability names
        registered_caps = set()
        for call in mock_registry.register_service.call_args_list:
            _, kwargs = call
            for cap in kwargs["capabilities"]:
                registered_caps.add(cap)

        expected_caps = {
            "ranking_semantics",
            "bipolar_argumentation",
            "aba_reasoning",
            "adf_reasoning",
            "aspic_plus_reasoning",
            "belief_revision",
            "probabilistic_argumentation",
            "dialogue_protocols",
            "description_logic",
            "conditional_logic",
            "setaf_reasoning",
            "weighted_argumentation",
            "social_argumentation",
            "epistemic_argumentation",
            "defeasible_logic",
            "qbf_reasoning",
        }
        assert registered_caps == expected_caps

    def test_tweety_slots_have_invoke_functions(self):
        """Each registered handler has an invoke callable."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _declare_tweety_slots,
        )

        mock_registry = MagicMock()
        _declare_tweety_slots(mock_registry)

        for call in mock_registry.register_service.call_args_list:
            _, kwargs = call
            assert kwargs["invoke"] is not None
            assert callable(kwargs["invoke"])


# =====================================================================
# TweetyBridge Integration Test
# =====================================================================


class TestTweetyBridgeTrackA:
    """Test that TweetyBridge exposes Track A handler properties."""

    def test_bridge_has_all_handler_properties(self):
        """TweetyBridge class has properties for all 8 Track A handlers."""
        from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

        expected_properties = [
            "ranking_handler",
            "bipolar_handler",
            "aba_handler",
            "adf_handler",
            "aspic_handler",
            "belief_revision_handler",
            "probabilistic_handler",
            "dialogue_handler",
        ]
        for prop_name in expected_properties:
            assert hasattr(TweetyBridge, prop_name), f"Missing property: {prop_name}"
            # Verify it's a property descriptor
            assert isinstance(
                getattr(TweetyBridge, prop_name), property
            ), f"{prop_name} is not a property"
