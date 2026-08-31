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

Synthetic framework: args a, b, c; attack a->b; support c->b. Since #1965 the
handler itself marks the support with ``Support.Type.EVIDENTIAL``, reduces via
``getAssociatedTheory(Support$Type)`` to a Dung framework, and queries the
grounded reasoner -- the non-vacuity assertion reads the handler's returned
model (pre-#1965 the test rebuilt the framework by hand because the handler
never queried it). The model must be non-empty -- an empty model would mean
the reasoner never ran, i.e. vacuously green.
"""

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

    # Exercise the production path end to end: loads, builds AND queries the
    # framework. #1965 closed the no-op -- the handler itself now reduces via
    # getAssociatedTheory(Support.Type.EVIDENTIAL) and returns the grounded
    # model, so the non-vacuity assertion holds through the real consumer
    # instead of a manual rebuild of the framework (pre-fix l.62-89 rebuilt
    # it because the handler never exposed a queried model).
    result = handler.analyze_bipolar_framework(
        ["a", "b", "c"], [["a", "b"]], [["c", "b"]], framework_type="evidential"
    )
    assert result["framework_type"] == "evidential"
    assert result["statistics"]["arguments_count"] == 3
    assert result["semantic"] == "grounded"
    assert result["model_size"] >= 1, (
        "the grounded Dung reasoner on the evidential theory, read through "
        "the handler, must produce a non-empty model -- a size-0 model means "
        "the reduction or the reasoner ran on a classpath with no real "
        "evidential classes (#1874, via handler since #1965)"
    )
    assert result["extensions"][0], "the model must contain at least one argument"
