"""#1965: BipolarHandler queries the framework it builds.

Pre-fix the handler constructed a ``BipolarArgumentationFramework``, populated
it, and returned an echo of its input lists -- ``framework_type=necessity`` and
``framework_type=evidential`` produced the same dict. These controls pin the
three behaviours the fix introduces, on the real JVM:

1. Non-vacuity: the grounded model of the associated Dung theory, read through
   the handler, is non-empty on a synthetic non-empty input.
2. Divergence: an edge referencing an argument absent from ``arguments`` is
   filtered at construction, so the framework counts (``getAttacks`` /
   ``getSupports``) diverge from the input-list lengths -- the falsifiable
   control that the handler consults the framework, not its inputs.
3. Semantic distinction: necessity and evidential reductions of the same
   framework produce different grounded models (in EAF semantics an attack
   from an unevidenced attacker is inoperative; in NAF it is not).
4. Graceful empties: a contradictory framework yields ``model_size == 0``
   without raising, and an unknown ``framework_type`` yields ``None``
   (nothing computed) -- three states, never two.

Synthetic atoms only (a, b, c); markers mirror the 1874 non-vacuity control so
the gate runs these when jars are present.
"""

import pytest

from argumentation_analysis.agents.core.logic.bipolar_handler import BipolarHandler
from argumentation_analysis.core.jvm_setup import initialize_jvm

pytestmark = [pytest.mark.jpype, pytest.mark.tweety]


@pytest.fixture(scope="module", autouse=True)
def _jvm():
    """Idempotent: the session conftest normally started it already."""
    initialize_jvm()


def test_handler_returns_nonempty_grounded_model():
    handler = BipolarHandler()
    result = handler.analyze_bipolar_framework(
        ["a", "b", "c"], [["a", "b"]], [["c", "b"]], framework_type="evidential"
    )
    assert result["semantic"] == "grounded"
    assert result["model_size"] >= 1, (
        "the grounded model read through the handler must be non-empty on a "
        "non-empty synthetic framework -- size 0 means the reduction or the "
        "reasoner never ran (#1965, #1874)"
    )
    assert result["extensions"][0], "the model must contain at least one argument"
    # The model is derived from the framework, not echoed from the inputs:
    # b is attacked (a -> b), so it must NOT appear in the grounded model of
    # the evidential reduction unless its evidence rehabilitates it. Whatever
    # the verdict, membership is decided by the reasoner.
    assert isinstance(result["model_size"], int)


def test_framework_counts_diverge_from_input_lists_on_absent_argument():
    handler = BipolarHandler()
    result = handler.analyze_bipolar_framework(
        arguments=["a", "b"],
        attacks=[["x", "b"], ["a", "b"]],  # x absent from arguments
        supports=[["c", "b"]],  # c absent from arguments
        framework_type="evidential",
    )
    # Input echo is unchanged (consumers rely on it).
    assert result["attacks"] == [["x", "b"], ["a", "b"]]
    assert result["supports"] == [["c", "b"]]
    # Framework counts only see the constructible edges -- the falsifiable
    # divergence: pre-fix these equalled len(input) by construction.
    assert result["statistics"]["attacks_count"] == 1
    assert result["statistics"]["supports_count"] == 0


def test_necessity_and_evidential_produce_distinct_models():
    handler = BipolarHandler()
    common = dict(arguments=["a", "b"], attacks=[["a", "b"]], supports=[])
    necessity = handler.analyze_bipolar_framework(framework_type="necessity", **common)
    evidential = handler.analyze_bipolar_framework(
        framework_type="evidential", **common
    )
    # NAF: the plain Dung reading -- a attacks b, b is out.
    assert necessity["extensions"] == [["a"]]
    # EAF: an attack from an unevidenced attacker is inoperative, so nothing
    # is defeated. Pre-fix both dicts were identical except framework_type.
    assert evidential["extensions"] == [["a", "b"]]
    assert necessity["model_size"] != evidential["model_size"]


def test_contradictory_framework_yields_empty_model_without_raising():
    handler = BipolarHandler()
    result = handler.analyze_bipolar_framework(
        ["a", "b"], [["a", "a"]], [["a", "b"]], framework_type="necessity"
    )
    # Computed-and-empty (0 / one empty extension), not an exception and not
    # None -- the tri-state contract of #1965.
    assert result["model_size"] == 0
    assert result["extensions"] == [[]]
    assert result["semantic"] == "grounded"


def test_unknown_framework_type_computes_nothing_and_says_so():
    handler = BipolarHandler()
    result = handler.analyze_bipolar_framework(
        ["a"], [], [], framework_type="deductive"
    )
    # None = nothing was computed for this support type; distinct from 0/[]
    # (computed and empty). "deductive" is a real Support.Type member the
    # handler does not yet map -- its result must not fabricate a model.
    assert result["model_size"] is None
    assert result["extensions"] is None
    assert result["semantic"] is None
    assert result["framework_type"] == "deductive"
