"""#1874 phase 1 (DoD): a non-vacuity control for the Maven assembly.

...``bipolar`` must stay pinned at 1.30 (the only evidential-capable release). This
test is the discriminating control: it loads the evidential family through the real
consumer (``BipolarHandler``) and runs a reasoner on a genuine framework. If someone
re-aligns ``arg:bipolar`` to 1.31, the
``EvidentialArgumentationFramework`` class load fails loudly at construction and this
test reddens — a JVM that "boots" but lacks the evidential classes is not a live
deployment.

.. warning:: Reddening here does NOT mean "restore the pin" (#1959). 1.31 did not
   delete the evidential family: ``Support$Type`` still carries ``EVIDENTIAL`` and
   ``BipolarArgumentationFramework.getAssociatedTheory(Support$Type)`` reduces it to
   a Dung theory. What 1.31 removes is the two concrete syntax classes and the seven
   dedicated ``reasoner.evidential`` classes -- so on a 1.31 bump this test is
   *migrated* to the unified API (build a ``BipolarArgumentationFramework``, mark the
   support ``EVIDENTIAL``, reduce with ``getAssociatedTheory``, run a Dung reasoner),
   keeping the same non-vacuity property. Re-pinning would retain a version whose
   only remaining benefit is that this file has not been rewritten yet.

The framework construction mirrors ``BipolarHandler.analyze_bipolar_framework`` with the
same JPype most-specific-overload cast idiom (edge cast to Attack/Support). Synthetic
atoms only (a, b, c); the jpype/tweety markers mirror test_native_sat_decides_1798 so the
gate still runs this when jars are present.

Synthetic framework: args a, b, c; attack a->b; support c->b. The evidential
GroundedReasoner computes the defensible extension, which for this small framework is
non-empty — an empty extension would mean the reasoner never ran, i.e. vacuously green.
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
    # The real consumer loads EvidentialArgumentationFramework at construction — if
    # bipolar is re-aligned to 1.31 this raises (that class is gone) and the test
    # reddens. See the module docstring: the fix is to migrate, not to re-pin.
    #
    # The two assertions below are echoes of this call's own arguments, so they cannot
    # tell a working handler from one that computes nothing. Not hypothetical:
    # analyze_bipolar_framework builds the framework and discards it, which is why the
    # reasoner check further down has to rebuild it by hand. The reasoning proven here
    # is Tweety's, not ours (#1959).
    handler = BipolarHandler()

    # Exercise the production build path (loads + builds the framework with the casts).
    result = handler.analyze_bipolar_framework(
        ["a", "b", "c"], [["a", "b"]], [["c", "b"]], framework_type="evidential"
    )
    assert result["framework_type"] == "evidential"
    assert result["statistics"]["arguments_count"] == 3

    # analyze_bipolar_framework does not expose the framework, so rebuild it to run a
    # reasoner. Same construction + cast idiom as the handler.
    framework = handler.EvidentialAF()
    arg_map = {name: handler.BArgument(name) for name in ["a", "b", "c"]}
    for arg in arg_map.values():
        framework.add(arg)
    framework.add(
        jpype.JObject(handler.BinaryAttack(arg_map["a"], arg_map["b"]), handler.Attack)
    )
    framework.add(
        jpype.JObject(
            handler.BinarySupport(arg_map["c"], arg_map["b"]), handler.Support
        )
    )

    grounded = jpype.JClass(
        "org.tweetyproject.arg.bipolar.reasoner.evidential.GroundedReasoner"
    )()
    model = grounded.getModel(framework)
    assert model.size() >= 1, (
        "the evidential GroundedReasoner must produce at least one extension "
        "— a size-0 model means the reasoner ran on a classpath with no real "
        "evidential classes (#1874)"
    )
