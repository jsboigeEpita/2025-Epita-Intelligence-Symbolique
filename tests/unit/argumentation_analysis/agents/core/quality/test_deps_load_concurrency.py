"""The quality evaluator's dependency load is safe under concurrent units.

The defect, measured on ``26bcf9a0`` by the #2353 render: the quality phase
evaluates its units in concurrent threads (#2331, ``asyncio.to_thread`` under
a bound of 6). ``_load_deps`` sets ``_DEPS_ATTEMPTED`` BEFORE importing spaCy
(seconds, cold) and ``_DEPS_AVAILABLE`` only after. A sibling unit reaching
``evaluate()``'s fail-loud gate during that window read "attempted, not
available" and raised ``Cannot evaluate quality ... (First load failure:
cause not recorded)`` — while the load it was reading was about to SUCCEED
(the loader's own warning landed in the same log, after the raise). A load in
progress was reported as a failed load, with no cause because none existed.

Serialising the load exposed a second window behind it: textstat reaches
NLTK's cmudict through a ``LazyCorpusLoader`` that is not thread-safe on first
use, and concurrent units recorded ``clarte`` UNAVAILABLE on a cold process.
The load now performs that first use under its lock.

Pinned here, with the load held open by the test so the window is certain
rather than a matter of timing (the cmudict window behind it: with the lock
but without the first-use call, the UNAVAILABLE assertion reddened 3 runs out
of 3 on a cold process):

1. a unit arriving during an in-progress load waits for it and is evaluated,
   and none of its detectors is recorded UNAVAILABLE on the way;
2. witness: a load that really failed still fails loud, WITH its cause, for
   every later unit (the #1019 / #2320 contract is untouched).
"""

import threading

import pytest

from argumentation_analysis.agents.core.quality import quality_evaluator as qe

_TEXT = (
    "Il faut investir dans les transports publics, car ils réduisent la "
    "pollution. En effet, chaque bus remplace plusieurs voitures. Certains "
    "objectent que le coût est élevé ; pourtant, les économies de santé le "
    "compensent."
)


@pytest.fixture
def cold_deps(monkeypatch):
    """The process state before any unit has loaded the dependencies."""
    monkeypatch.setattr(qe, "_DEPS_ATTEMPTED", False)
    monkeypatch.setattr(qe, "_DEPS_AVAILABLE", False)
    monkeypatch.setattr(qe, "_LAST_LOAD_ERROR", None)


def _evaluate_into(results: list, errors: list) -> None:
    try:
        results.append(qe.ArgumentQualityEvaluator().evaluate(_TEXT))
    except Exception as exc:  # recorded, asserted by the test
        errors.append(exc)


def test_a_unit_arriving_during_the_load_waits_for_it(monkeypatch, cold_deps):
    entered, release = threading.Event(), threading.Event()
    real_neutralize = qe._neutralize_faulty_torch

    def held_load():
        entered.set()
        release.wait(10)
        real_neutralize()

    monkeypatch.setattr(qe, "_neutralize_faulty_torch", held_load)
    results: list = []
    errors: list = []

    first = threading.Thread(target=_evaluate_into, args=(results, errors))
    first.start()
    assert entered.wait(10), "the first unit never started the load"

    sibling = threading.Thread(target=_evaluate_into, args=(results, errors))
    sibling.start()
    # The window: the sibling reaches the gate while the load is held open.
    sibling.join(1.0)
    release.set()
    first.join(60)
    sibling.join(60)

    assert not errors, f"a unit failed on a load that was in progress: {errors!r}"
    assert len(results) == 2
    assert qe._DEPS_AVAILABLE is True
    # Second symptom of the same window: a detector reaching ``_load_deps``
    # mid-load was recorded UNAVAILABLE — an outage that never happened.
    for result in results:
        unavailable = [
            v
            for v, status in result["statuts_par_vertu"].items()
            if status == qe.VirtueStatus.UNAVAILABLE
        ]
        assert not unavailable, (unavailable, result["rapport_detaille"])


def test_witness_a_failed_load_still_fails_loud_with_its_cause(monkeypatch, cold_deps):
    def broken_load():
        raise ImportError("textstat introuvable (témoin)")

    monkeypatch.setattr(qe, "_neutralize_faulty_torch", broken_load)
    evaluator = qe.ArgumentQualityEvaluator()

    # The first unit records the outage per detector, with the cause...
    first = evaluator.evaluate(_TEXT)
    assert qe.VirtueStatus.UNAVAILABLE in first["statuts_par_vertu"].values()
    assert "textstat introuvable" in " ".join(first["rapport_detaille"].values())
    # ...and every later unit hits the gate, which carries that first cause.
    with pytest.raises(RuntimeError, match="First load failure: ImportError"):
        evaluator.evaluate(_TEXT)
