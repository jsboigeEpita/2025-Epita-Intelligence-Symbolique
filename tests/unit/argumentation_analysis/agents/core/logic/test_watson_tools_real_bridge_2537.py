"""#2537 — Watson's formal tools must call the real bridge/handler surface.

Born-red on main: `WatsonTools.validate_formula`/`execute_query` call
`TweetyBridge.validate_formula`/`perform_pl_query`, methods removed in 2025-06
(`2db24f6f8`) — and a `MagicMock` double certified that phantom path green
(tests/agents/core/logic/test_watson_logic_assistant.py). These tests pin the
double to the real class (`create_autospec`), then go further: the last class
drives a REAL JVM through `WatsonTools` end-to-end (the #2595 repair of the
constants branch was covered by mocked jpype only, which cannot see the missing
Java overload — measured on main: `PlParser` has no
`parseFormula(String, PlSignature)`).

CI lane: `automated-tests` (ci.yml) collects `tests/unit/` with
`-m "not slow and not requires_api"` — neither `jpype` nor `tweety` is
deselected, so the real-JVM class runs there (skips when JVM/Tweety
unavailable).
"""

from unittest.mock import create_autospec

import pytest

from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge
from argumentation_analysis.agents.core.logic.watson_logic_assistant import WatsonTools

PROMPT_EXAMPLE = "(A && B) => !C"
MODUS_KB = "A\nB\n(A && B) => !C"
CONSTANTS = ["A", "B", "C"]


def _autospec_bridge() -> TweetyBridge:
    """A test double that can only expose what the real TweetyBridge exposes."""
    return create_autospec(TweetyBridge, instance=True)


class TestWatsonToolsOnTheRealSurface:
    """Constrained double: the phantom methods no longer exist to be called."""

    def test_validate_formula_parses_via_pl_handler(self):
        bridge = _autospec_bridge()
        bridge.pl_handler.parse_pl_formula.return_value = object()  # truthy parsed
        tools = WatsonTools(tweety_bridge=bridge, constants=list(CONSTANTS))

        assert tools.validate_formula(PROMPT_EXAMPLE) is True
        bridge.pl_handler.parse_pl_formula.assert_called_once_with(
            PROMPT_EXAMPLE, constants=CONSTANTS
        )

    def test_invalid_formula_is_a_parser_verdict(self):
        bridge = _autospec_bridge()
        bridge.pl_handler.parse_pl_formula.side_effect = ValueError("syntax")
        tools = WatsonTools(tweety_bridge=bridge, constants=[])

        assert tools.validate_formula("(A") is False

    def test_execute_query_goes_through_pl_handler_pl_query(self):
        bridge = _autospec_bridge()
        bridge.pl_handler.parse_pl_formula.return_value = object()
        bridge.pl_handler.pl_query.return_value = True
        tools = WatsonTools(tweety_bridge=bridge, constants=list(CONSTANTS))

        result = tools.execute_query(MODUS_KB, "!C")

        assert "Résultat de l'inférence: True" in result
        bridge.pl_handler.pl_query.assert_called_once_with(
            MODUS_KB, "!C", constants=CONSTANTS
        )

    def test_execute_query_names_an_invalid_query(self):
        bridge = _autospec_bridge()
        bridge.pl_handler.parse_pl_formula.side_effect = ValueError("syntax")
        tools = WatsonTools(tweety_bridge=bridge, constants=[])

        result = tools.execute_query(MODUS_KB, "(A")

        assert result.startswith("ERREUR:")
        bridge.pl_handler.pl_query.assert_not_called()

    def test_formula_reaches_the_handler_unchanged(self):
        """The implication must survive: no Watson-side normalizer drops `=>`."""
        bridge = _autospec_bridge()
        bridge.pl_handler.parse_pl_formula.return_value = object()
        tools = WatsonTools(
            tweety_bridge=bridge,
            constants=["ColonelMoutardeEstCoupable", "LieuEstLeSalon"],
        )

        sent = "ColonelMoutardeEstCoupable => LieuEstLeSalon"
        assert tools.validate_formula(sent) is True
        call = bridge.pl_handler.parse_pl_formula.call_args
        assert call is not None, "the formula never reached the real parser"
        assert call.args[0] == sent
        assert "=>" in call.args[0]

    def test_tool_failure_is_not_an_invalid_verdict(self):
        """A bridge/handler crash must NOT be swallowed into `False` (the mask)."""
        bridge = _autospec_bridge()
        bridge.pl_handler.parse_pl_formula.side_effect = RuntimeError("JVM down")
        tools = WatsonTools(tweety_bridge=bridge, constants=[])

        with pytest.raises(RuntimeError):
            tools.validate_formula(PROMPT_EXAMPLE)


def _jvm_ready_marker() -> bool:
    try:
        from argumentation_analysis.core import jvm_setup

        jvm_setup.initialize_jvm()
        from argumentation_analysis.agents.core.logic.tweety_initializer import (
            TweetyInitializer,
        )

        init = TweetyInitializer()
        init.ensure_jvm_and_components_are_ready()
        return bool(init.is_jvm_ready())
    except Exception:
        return False


@pytest.fixture(scope="module")
def jvm():
    if not _jvm_ready_marker():
        pytest.skip("JVM/Tweety unavailable — real-jpype contract test skipped")
    from argumentation_analysis.agents.core.logic.tweety_initializer import (
        TweetyInitializer,
    )

    init = TweetyInitializer()
    init.ensure_jvm_and_components_are_ready()
    return init


pytestmark = [pytest.mark.jpype, pytest.mark.tweety]


class TestWatsonToolsOnARealJVM:
    """End-to-end: Watson's tools through the real bridge, real Tweety (#2537)."""

    def test_prompt_example_valid_and_entailed(self, jvm):
        tools = WatsonTools(constants=list(CONSTANTS))

        # DoD: the prompt's own "FORMULE VALIDE" example validates on the real
        # parser, with A, B, C declared — the implication survives.
        assert tools.validate_formula(PROMPT_EXAMPLE) is True

        # DoD: {A, B, (A && B) => !C} entails !C.
        result = tools.execute_query(MODUS_KB, "!C")
        assert "Résultat de l'inférence: True" in result

    def test_negatives_stay_negative(self, jvm):
        tools = WatsonTools(constants=list(CONSTANTS))

        # Unbalanced formula: the parser rejects it, the tool says False.
        assert tools.validate_formula("(A") is False

        # {A} does not entail B.
        result = tools.execute_query("A", "B")
        assert "Résultat de l'inférence: False" in result

    def test_undeclared_atom_is_rejected(self, jvm):
        """The declared vocabulary is honored: an unknown atom is invalid."""
        tools = WatsonTools(constants=list(CONSTANTS))

        assert tools.validate_formula("(A && B) => D") is False


class TestParsePlFormulaConstantsBranch:
    """The `constants` branch must reach the real Java API (#2537).

    Measured on main: `PlParser.parseFormula(String, PlSignature)` does not
    exist in this Tweety — every parse with constants raised TypeError (the
    #2595 JString repair was covered by mocked jpype, which cannot see a
    missing overload).
    """

    def test_declared_constants_parse(self, jvm):
        parsed = TweetyBridge.get_instance().pl_handler.parse_pl_formula(
            PROMPT_EXAMPLE, constants=CONSTANTS
        )
        assert parsed is not None

    def test_undeclared_constant_raises_value_error(self, jvm):
        with pytest.raises(ValueError):
            TweetyBridge.get_instance().pl_handler.parse_pl_formula(
                "(A && B) => D", constants=CONSTANTS
            )
