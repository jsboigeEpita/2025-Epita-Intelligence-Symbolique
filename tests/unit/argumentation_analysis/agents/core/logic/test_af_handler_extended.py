"""Tests for extended Dung semantics in AFHandler.

Validates:
- All 11 supported semantics (preferred, grounded, stable, complete, admissible,
  conflict_free, semi_stable, stage, cf2, ideal, naive)
- Multi-semantics analysis
- Convenience methods (get_grounded_extension)
- Error handling (invalid semantics, unavailable reasoner)
- Framework building and extension conversion
"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock

from argumentation_analysis.agents.core.logic.af_handler import (
    AFHandler,
    SEMANTICS_REASONERS,
)
from argumentation_analysis.agents.core.logic.tweety_initializer import (
    TweetyInitializer,
)


@pytest.fixture
def mock_initializer():
    init = MagicMock(spec=TweetyInitializer)
    init.is_jvm_ready.return_value = True
    return init


@pytest.fixture
def mock_jpype():
    """Mock jpype to avoid JVM dependency."""
    with patch("argumentation_analysis.agents.core.logic.af_handler.jpype") as m:
        # Mock Java classes
        mock_dung_theory = MagicMock()
        mock_argument = MagicMock()
        mock_attack = MagicMock()
        mock_extension = MagicMock()
        mock_reasoner_cls = MagicMock()

        # Make Argument callable and track names
        def make_arg(name):
            arg = MagicMock()
            arg.getName.return_value = name
            return arg

        mock_argument_cls = MagicMock(side_effect=make_arg)

        # Make Attack a proper constructor that returns a mock attack object
        def make_attack(source, target):
            attack = MagicMock()
            attack.getAttacker.return_value = source
            attack.getAttacked.return_value = target
            return attack
        mock_attack_cls = MagicMock(side_effect=make_attack)

        def jclass_side_effect(class_name):
            if "DungTheory" in class_name:
                return MagicMock  # Constructor
            elif "Argument" in class_name and "syntax" in class_name:
                return mock_argument_cls
            elif "Attack" in class_name:
                return mock_attack_cls
            elif "Extension" in class_name:
                return mock_extension
            elif "Reasoner" in class_name:
                return mock_reasoner_cls
            return MagicMock()

        m.JClass.side_effect = jclass_side_effect
        m.JException = Exception

        yield m, mock_reasoner_cls


class TestSupportedSemantics:
    """Tests for semantics enumeration."""

    def test_supported_semantics_list(self):
        expected = [
            "preferred",
            "grounded",
            "stable",
            "complete",
            "admissible",
            "conflict_free",
            "semi_stable",
            "stage",
            "cf2",
            "ideal",
            "naive",
        ]
        assert AFHandler.supported_semantics() == expected

    def test_semantics_reasoners_mapping(self):
        assert len(SEMANTICS_REASONERS) == 11
        for sem, cls_path in SEMANTICS_REASONERS.items():
            assert "org.tweetyproject.arg.dung.reasoner" in cls_path


class TestAFHandlerExtended:
    """Tests for extended Dung semantics support."""

    def test_init_requires_jvm(self, mock_initializer, mock_jpype):
        mock_initializer.is_jvm_ready.return_value = False
        with pytest.raises(RuntimeError, match="JVM"):
            AFHandler(mock_initializer)

    def test_init_success(self, mock_initializer, mock_jpype):
        handler = AFHandler(mock_initializer)
        assert handler._initializer_instance == mock_initializer
        assert handler._reasoner_cache == {}

    def test_invalid_semantics_raises(self, mock_initializer, mock_jpype):
        handler = AFHandler(mock_initializer)
        with pytest.raises(ValueError, match="Unsupported semantics"):
            handler._get_reasoner("nonexistent")

    def test_reasoner_caching(self, mock_initializer, mock_jpype):
        _, mock_reasoner_cls = mock_jpype
        handler = AFHandler(mock_initializer)
        r1 = handler._get_reasoner("preferred")
        r2 = handler._get_reasoner("preferred")
        assert r1 is r2  # Same cached instance

    @pytest.mark.parametrize("semantics", SEMANTICS_REASONERS.keys())
    def test_all_semantics_dispatch(self, semantics, mock_initializer, mock_jpype):
        """Verify each semantics loads the correct reasoner class."""
        jpype_mock, mock_reasoner_cls = mock_jpype
        handler = AFHandler(mock_initializer)

        # Setup reasoner to return empty extensions
        mock_reasoner_instance = MagicMock()
        mock_reasoner_instance.getModels.return_value = []
        mock_reasoner_cls.return_value = mock_reasoner_instance

        result = handler.analyze_dung_framework(
            arguments=["a", "b"],
            attacks=[["a", "b"]],
            semantics=semantics,
        )

        assert result["semantics"] == semantics
        assert semantics in result["extensions"]
        assert result["statistics"]["arguments_count"] == 2
        assert result["statistics"]["attacks_count"] == 1

    def test_analyze_returns_sorted_extensions(self, mock_initializer, mock_jpype):
        _, mock_reasoner_cls = mock_jpype
        handler = AFHandler(mock_initializer)

        # Create mock extensions with arguments
        ext1 = MagicMock()
        arg_c = MagicMock()
        arg_c.getName.return_value = "c"
        arg_a = MagicMock()
        arg_a.getName.return_value = "a"
        ext1.__iter__ = MagicMock(return_value=iter([arg_c, arg_a]))

        ext2 = MagicMock()
        arg_b = MagicMock()
        arg_b.getName.return_value = "b"
        ext2.__iter__ = MagicMock(return_value=iter([arg_b]))

        mock_reasoner_instance = MagicMock()
        mock_reasoner_instance.getModels.return_value = [ext1, ext2]
        mock_reasoner_cls.return_value = mock_reasoner_instance

        result = handler.analyze_dung_framework(
            arguments=["a", "b", "c"],
            attacks=[["a", "b"]],
            semantics="preferred",
        )

        extensions = result["extensions"]["preferred"]
        # Each inner list should be sorted, outer list should be sorted
        assert extensions == [["a", "c"], ["b"]]

    def test_invalid_attack_skipped(self, mock_initializer, mock_jpype):
        _, mock_reasoner_cls = mock_jpype
        handler = AFHandler(mock_initializer)

        mock_reasoner_instance = MagicMock()
        mock_reasoner_instance.getModels.return_value = []
        mock_reasoner_cls.return_value = mock_reasoner_instance

        # Attack references non-existent argument "x"
        result = handler.analyze_dung_framework(
            arguments=["a", "b"],
            attacks=[["a", "x"]],
            semantics="grounded",
        )

        assert result["statistics"]["attacks_count"] == 1
        assert result["semantics"] == "grounded"

    def test_hyphen_to_underscore_normalization(self, mock_initializer, mock_jpype):
        _, mock_reasoner_cls = mock_jpype
        handler = AFHandler(mock_initializer)

        mock_reasoner_instance = MagicMock()
        mock_reasoner_instance.getModels.return_value = []
        mock_reasoner_cls.return_value = mock_reasoner_instance

        # "semi-stable" should normalize to "semi_stable"
        result = handler.analyze_dung_framework(
            arguments=["a"], attacks=[], semantics="semi-stable"
        )
        assert result["semantics"] == "semi_stable"


class TestMultiSemantics:
    """Tests for multi-semantics analysis."""

    def test_default_semantics(self, mock_initializer, mock_jpype):
        _, mock_reasoner_cls = mock_jpype
        handler = AFHandler(mock_initializer)

        mock_reasoner_instance = MagicMock()
        mock_reasoner_instance.getModels.return_value = []
        mock_reasoner_cls.return_value = mock_reasoner_instance

        result = handler.analyze_multi_semantics(
            arguments=["a", "b"], attacks=[["a", "b"]]
        )

        assert "grounded" in result["extensions"]
        assert "preferred" in result["extensions"]
        assert "stable" in result["extensions"]
        assert "complete" in result["extensions"]

    def test_custom_semantics_list(self, mock_initializer, mock_jpype):
        _, mock_reasoner_cls = mock_jpype
        handler = AFHandler(mock_initializer)

        mock_reasoner_instance = MagicMock()
        mock_reasoner_instance.getModels.return_value = []
        mock_reasoner_cls.return_value = mock_reasoner_instance

        result = handler.analyze_multi_semantics(
            arguments=["a"],
            attacks=[],
            semantics_list=["grounded", "naive", "cf2"],
        )

        assert set(result["extensions"].keys()) == {"grounded", "naive", "cf2"}

    def test_partial_failure_continues(self, mock_initializer, mock_jpype):
        _, mock_reasoner_cls = mock_jpype
        handler = AFHandler(mock_initializer)

        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:  # Fail on second semantics
                raise Exception("Reasoner unavailable")
            return []

        mock_reasoner_instance = MagicMock()
        mock_reasoner_instance.getModels.side_effect = side_effect
        mock_reasoner_cls.return_value = mock_reasoner_instance

        result = handler.analyze_multi_semantics(
            arguments=["a"],
            attacks=[],
            semantics_list=["grounded", "stable"],
        )

        # First should succeed, second should have error
        assert "grounded" in result["extensions"]
        assert "stable" in result["extensions"]


class TestGroundedConvenience:
    """Tests for get_grounded_extension convenience method."""

    def test_returns_single_extension(self, mock_initializer, mock_jpype):
        _, mock_reasoner_cls = mock_jpype
        handler = AFHandler(mock_initializer)

        ext = MagicMock()
        arg_a = MagicMock()
        arg_a.getName.return_value = "a"
        ext.__iter__ = MagicMock(return_value=iter([arg_a]))

        mock_reasoner_instance = MagicMock()
        mock_reasoner_instance.getModels.return_value = [ext]
        mock_reasoner_cls.return_value = mock_reasoner_instance

        result = handler.get_grounded_extension(
            arguments=["a", "b"], attacks=[["b", "a"]]
        )

        assert result == ["a"]

    def test_empty_framework_returns_empty(self, mock_initializer, mock_jpype):
        _, mock_reasoner_cls = mock_jpype
        handler = AFHandler(mock_initializer)

        mock_reasoner_instance = MagicMock()
        mock_reasoner_instance.getModels.return_value = []
        mock_reasoner_cls.return_value = mock_reasoner_instance

        result = handler.get_grounded_extension(arguments=[], attacks=[])
        assert result == []


class TestExtensionConversion:
    """Tests for _extensions_to_python helper."""

    def test_empty_extensions(self, mock_initializer, mock_jpype):
        handler = AFHandler(mock_initializer)
        assert handler._extensions_to_python([]) == []

    def test_single_extension(self, mock_initializer, mock_jpype):
        handler = AFHandler(mock_initializer)

        ext = MagicMock()
        arg_b = MagicMock()
        arg_b.getName.return_value = "b"
        arg_a = MagicMock()
        arg_a.getName.return_value = "a"
        ext.__iter__ = MagicMock(return_value=iter([arg_b, arg_a]))

        result = handler._extensions_to_python([ext])
        assert result == [["a", "b"]]  # Sorted

    def test_multiple_extensions_sorted(self, mock_initializer, mock_jpype):
        handler = AFHandler(mock_initializer)

        ext1 = MagicMock()
        arg_c = MagicMock()
        arg_c.getName.return_value = "c"
        ext1.__iter__ = MagicMock(return_value=iter([arg_c]))

        ext2 = MagicMock()
        arg_a = MagicMock()
        arg_a.getName.return_value = "a"
        ext2.__iter__ = MagicMock(return_value=iter([arg_a]))

        result = handler._extensions_to_python([ext1, ext2])
        assert result == [["a"], ["c"]]  # Outer list sorted
