"""#1874 phase 1 (DoD): a non-vacuity control for the Maven assembly.

This test is the discriminating control: it loads the evidential path through
the real consumer (``BipolarHandler``) and runs a reasoner on a genuine
framework. If the assembly fails to deliver the bipolar classes or the Dung
reasoner, this test reddens -- a JVM that "boots" but lacks the classes is
not a live deployment.

.. warning:: Reddening here does NOT mean "restore the pin" (#1959). 1.31 did
   not delete the evidential family: ``Support$Type`` still carries
   ``EVIDENTIAL`` and ``BipolarArgumentationFramework.getAssociatedTheory(Support$Type)``
   reduces it to a Dung theory. What 1.31 removes is wider than those two AF
   classes: the bipolar module falls to 16 classes, dropping the seven
   dedicated ``reasoner.evidential`` classes AND the whole argument/edge
   vocabulary (``BArgument``, ``BinaryAttack``, ``BinarySupport``, bipolar's
   ``Attack``), which Dung's now replaces -- so on a 1.31 bump this test is
   *migrated* to the unified API (build a ``BipolarArgumentationFramework``,
   mark the support ``EVIDENTIAL``, reduce with ``getAssociatedTheory``, run a
   Dung reasoner), keeping the same non-vacuity property. Re-pinning would
   retain a version whose only remaining benefit is that this file has not
   been rewritten yet.

Synthetic framework: args a, b, c; attack a->b; support c->b. We mark the
support with ``Support.Type.EVIDENTIAL``, reduce via
``getAssociatedTheory(Support$Type)`` to a Dung framework, and query the
grounded reasoner. The model must be non-empty -- an empty model would mean
the reasoner never ran, i.e. vacuously green.

The framework construction mirrors ``BipolarHandler.analyze_bipolar_framework``
using the 1.31 API (``dung.syntax.Argument``, ``dung.syntax.Attack``,
``bipolar.syntax.Support(Argument, Argument)``). Synthetic atoms only (a, b, c);
the jpype/tweety markers mirror test_native_sat_decides_1798 so the gate still
runs this when jars are present.
"""

import jpype
import pytest

from argumentation_analysis.agents.core.logic.bipolar_handler import BipolarHandler
from argumentation_analysis.core.jvm_setup import initialize_jvm

pytestmark = [pytest.mark.jpype, pytest.mark.tweety]


@pytest.fixture(scope="module", autouse=True)
def _jvm():
    """Idempotent: the session conftest normally started it already."""
    initialize_jvm()


def test_evidential_framework_loaded_and_reasoner_produces_model():
    # The real consumer loads BipolarArgumentationFramework at construction.
    handler = BipolarHandler()

    # Exercise the production build path (loads + builds the framework with the casts).
    result = handler.analyze_bipolar_framework(
        ["a", "b", "c"], [["a", "b"]], [["c", "b"]], framework_type="evidential"
    )
    assert result["framework_type"] == "evidential"
    assert result["statistics"]["arguments_count"] == 3

    # analyze_bipolar_framework does not expose the framework, so rebuild it to run a
    # reasoner. Same construction + cast idiom as the handler, using the 1.31 API:
    #   Argument  -> dung.syntax.Argument
    #   Attack    -> dung.syntax.Attack (inherited by BipolarArgumentationFramework)
    #   Support   -> bipolar.syntax.Support(Argument, Argument)
    framework = handler.BipolarAF()
    arg_map = {name: handler.Argument(name) for name in ["a", "b", "c"]}
    for arg in arg_map.values():
        framework.add(arg)
    framework.add(handler.Attack(arg_map["a"], arg_map["b"]))
    framework.add(handler.Support(arg_map["c"], arg_map["b"]))

    # #1959 (1.31 migration): evidential reasoner family was retired in 1.31.
    # Reduce the bipolar framework to a Dung theory via getAssociatedTheory,
    # parameterised by Support.Type.EVIDENTIAL, then run the grounded Dung
    # reasoner. The model must remain non-empty -- a size-0 model means the
    # reasoner ran on a classpath with no real evidential classes (#1874).
    support_type = handler.Support.Type
    dung_framework = framework.getAssociatedTheory(support_type.EVIDENTIAL)
    grounded = jpype.JClass(
        "org.tweetyproject.arg.dung.reasoner.SimpleGroundedReasoner"
    )()
    model = grounded.getModel(dung_framework)
    assert model.size() >= 1, (
        "the grounded Dung reasoner on the evidential theory must produce "
        "at least one extension -- a size-0 model means the reasoner ran on "
        "a classpath with no real evidential classes (#1874)"
    )