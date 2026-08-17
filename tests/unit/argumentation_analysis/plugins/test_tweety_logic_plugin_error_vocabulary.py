"""#1774 — the 21 formal axes of TweetyLogicPlugin render a structured error
(not a verdict, not a naked exception) on an input they cannot parse.

Red control (DoD item 5): on main at branch time (`be719a69`), measured
firsthand on myia-po-2023, JVM up, one process:

* garbage / empty / wrongkeys -> SUCCESS-fabricated verdict for 11 functions
  (``is_consistent``, ``valid``, ``satisfiable``, ``extensions``, ``entailed``,
  ``ranking``, ``revised``, ...), RAISED for the rest (lazy-init #1775 raises,
  the ``analyze_adf`` dead cable, the ``rank_arguments`` AIOOBE) — i.e. 21/21
  fail the assertion below.
* the DeLP handler returned ``{"error": <parse msg>}`` on garbage — an error,
  but not the envelope convention (it does not name received/expected keys
  and only fires AFTER the program text reached the Java parser).

The scope follows the R820 triage written on the issue: the 8 lazy-init axes
(#1775, fixed independently in PR #1778) and the ``analyze_adf`` dead cable
keep their loud raises for VALID input — nothing here wraps them. The envelope
gate is uniform: unparsable input is rejected before any handler construction,
so garbage behaviour no longer depends on call position (the warm-order effect
observed when re-running the R819 table: ``check_modal_satisfiability`` and
friends fabricate instead of raising once earlier calls warmed
``_classes_loaded``).

This module requires the real JVM session (like test_conv_b_kernel_deciders):
under ``--disable-jvm-session`` the ``@_jvm_required`` short-circuit would make
every cell return ``{"error": "JVM not available"}`` and the precise assertion
below would correctly fail — run it JVM-up.
"""

import json

import pytest

from argumentation_analysis.plugins.tweety_logic_plugin import TweetyLogicPlugin

pytestmark = pytest.mark.tweety

GARBAGE = "@@@ ceci n'est pas du JSON @@@"
EMPTY = ""
WRONGKEYS = '{"zzz_unknown": [1, 2, 3]}'

UNPARSABLE_PAYLOADS = [("garbage", GARBAGE), ("empty", EMPTY), ("wrongkeys", WRONGKEYS)]

ALL_FUNCTIONS = [
    "analyze_dung_framework",
    "check_propositional_consistency",
    "check_fol_consistency",
    "check_modal_satisfiability",
    "rank_arguments",
    "analyze_bipolar_framework",
    "analyze_aba",
    "analyze_adf",
    "analyze_aspic",
    "revise_beliefs",
    "analyze_probabilistic",
    "execute_dialogue",
    "check_dl_consistency",
    "query_conditional_logic",
    "solve_sat",
    "analyze_setaf",
    "analyze_weighted_framework",
    "analyze_social_framework",
    "analyze_epistemic_framework",
    "analyze_delp",
    "check_qbf",
]

# Verdict keys of the fabrication half (#1774 §2): none of them may appear in
# the answer to an unparsable input.
VERDICT_KEYS = (
    "is_consistent",
    "consistent",
    "valid",
    "satisfiable",
    "extensions",
    "entailed",
    "ranking",
    "scores",
    "revised",
    "grounded_extension",
    "outcome",
    "acceptance_probabilities",
)


@pytest.fixture(scope="module")
def plugin() -> TweetyLogicPlugin:
    return TweetyLogicPlugin()


def _assert_structured_envelope_error(result_str: str) -> dict:
    """Assert the result is the #1773 envelope-error convention.

    The three shapes produced by ``parse_kernel_json_object`` are accepted —
    invalid JSON, non-object, missing required key(s) naming both sides — and
    nothing else: in particular NOT the ``@_jvm_required`` short-circuit (the
    JVM is up here, so seeing it means the tested branch is the wrong one)
    and not any verdict key.
    """
    assert isinstance(result_str, str), "kernel_function must return a JSON string"
    result = json.loads(result_str)
    assert isinstance(result, dict), f"expected a JSON object, got: {result}"
    assert (
        result.get("error") != "JVM not available"
    ), "JVM short-circuit: the real branch was not exercised"
    assert "error" in result, f"no structured error rendered: {result}"
    is_invalid_json = result.get("error") == "Invalid JSON input"
    is_shape_error = "received_type" in result
    is_missing_keys = "received_keys" in result and "expected_keys" in result
    assert (
        is_invalid_json or is_shape_error or is_missing_keys
    ), f"error does not follow the #1773 envelope convention: {result}"
    leaked = [k for k in VERDICT_KEYS if k in result]
    assert not leaked, f"fabricated formal verdict alongside the error: {result}"
    return result


class TestUnparsableInputRendersStructuredError:
    """DoD item 5: the 21 x 3 table of #1774 §1, as a parametrized test."""

    @pytest.mark.parametrize("payload_name,payload", UNPARSABLE_PAYLOADS)
    @pytest.mark.parametrize("function_name", ALL_FUNCTIONS)
    def test_unparsable_input_is_rejected(
        self,
        plugin: TweetyLogicPlugin,
        function_name: str,
        payload_name: str,
        payload: str,
    ):
        result = getattr(plugin, function_name)(payload)
        _assert_structured_envelope_error(result)

    def test_wrongkeys_error_names_both_sides(self, plugin: TweetyLogicPlugin):
        """DoD item 1: the error names the keys received AND expected."""
        result = json.loads(plugin.analyze_aba(WRONGKEYS))
        assert result["received_keys"] == ["zzz_unknown"]
        assert "assumptions" in result["error"]
        assert "rules" in result["error"]
        assert "assumptions" in result["expected_keys"]

    def test_plain_text_formula_is_no_longer_the_kb(self, plugin: TweetyLogicPlugin):
        """The undocumented plain-text affordance (``{"formulas": [input]}``
        default) is what turned prose into an asserted-consistent KB (#1774
        §2). A valid PL formula sent as bare text now converges by retry:
        envelope error naming 'formulas'."""
        result = json.loads(plugin.check_propositional_consistency("p && q"))
        assert result.get("error") == "Invalid JSON input"


class TestEmptyAndValidIsNotNonParse:
    """DoD item 4: an explicitly-empty framework parses and is analyzed
    honestly — the (a)/(b) distinction of #1774 §4.

    Only warm-order-independent, in-scope functions here: the lazy axes'
    behaviour on valid input depends on #1775 (PR #1778), not on this ticket.
    """

    def test_aba_explicitly_empty_framework_is_analyzed(self, plugin):
        result = json.loads(plugin.analyze_aba('{"assumptions": [], "rules": []}'))
        assert "error" not in result
        assert result["extensions"] == [[]]
        assert result["statistics"]["rules_count"] == 0

    def test_aspic_explicitly_empty_framework_is_analyzed(self, plugin):
        result = json.loads(
            plugin.analyze_aspic('{"strict_rules": [], "defeasible_rules": []}')
        )
        assert "error" not in result
        assert "extensions" in result

    def test_sat_explicitly_empty_formula_list_is_solved(self, plugin):
        result = json.loads(plugin.solve_sat('{"formulas": []}'))
        assert "error" not in result
        assert result["satisfiable"] is True

    def test_pl_explicitly_empty_kb_is_consistent(self, plugin):
        result = json.loads(plugin.check_propositional_consistency('{"formulas": []}'))
        assert "error" not in result
        assert result["is_consistent"] is True

    def test_revise_from_empty_base_is_a_revision(self, plugin):
        result = json.loads(
            plugin.revise_beliefs('{"belief_set": [], "new_belief": "p"}')
        )
        assert "error" not in result
        assert "revised" in result

    def test_cl_explicitly_empty_kb_constructs(self, plugin):
        result = json.loads(plugin.query_conditional_logic('{"conditionals": []}'))
        assert "error" not in result
        assert "message" in result


class TestRankArgumentsEmptyFramework:
    """#1774 item 2 (triage R820): the one RAISED that is a real input
    problem — the handler AIOOBEs on an empty framework — becomes a
    structured error, not a naked RuntimeError."""

    def test_empty_arguments_is_a_structured_error(self, plugin):
        result = json.loads(plugin.rank_arguments('{"arguments": [], "attacks": []}'))
        assert "error" in result
        assert "arguments" in result["error"]
        assert "received_keys" in result

    def test_nonempty_framework_still_ranks(self, plugin):
        result = json.loads(
            plugin.rank_arguments('{"arguments": ["a"], "attacks": []}')
        )
        assert "error" not in result
        assert result["method"] == "categorizer"


class TestValidInputStillDecides:
    """Regression guards: the gate must not degrade comprehended input."""

    def test_pl_consistency_decides(self, plugin):
        result = json.loads(
            plugin.check_propositional_consistency('{"formulas": ["p => q", "p"]}')
        )
        assert "error" not in result
        assert isinstance(result["is_consistent"], bool)

    def test_sat_solves(self, plugin):
        result = json.loads(plugin.solve_sat('{"formulas": ["p || q"]}'))
        assert "error" not in result
        assert result["satisfiable"] is True

    def test_aba_analyzes_real_framework(self, plugin):
        result = json.loads(plugin.analyze_aba('{"assumptions": ["a"], "rules": []}'))
        assert "error" not in result
        assert "extensions" in result
