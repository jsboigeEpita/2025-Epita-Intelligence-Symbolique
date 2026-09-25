# -*- coding: utf-8 -*-
"""#2664: ``tweety_bridge_fixture`` leaves the ``TweetyBridge`` singleton as
it found it.

``TweetyBridge`` is a process-wide singleton. The fixture built it and never
removed it, so the next test's ``TweetyBridge.get_instance()`` returned that
real bridge, whose handlers were built before the test's patches.
``TestTweetyBridge`` then saw its handler mocks never called, only after a
real-JVM test had run in the same process. The probe runs the two shapes in
that order, in a session of its own.
"""

from tests.nested_pytest import both, run_probe

_PROBE = """
from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

SEEN = {}


def test_the_fixture_gives_the_singleton(tweety_bridge_fixture):
    assert TweetyBridge._instance is tweety_bridge_fixture
    SEEN["bridge"] = tweety_bridge_fixture


def test_the_next_test_does_not_inherit_it():
    assert "bridge" in SEEN, "the fixture test did not run"
    assert TweetyBridge._instance is None, TweetyBridge._instance
"""

_BEFORE = """
from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge


def pytest_runtest_setup(item):
    if item.name == "test_the_fixture_gives_the_singleton":
        assert TweetyBridge._instance is None, "a singleton existed before the fixture"
"""


def test_the_fixture_leaves_no_singleton_behind():
    code, out, err = run_probe(
        "2664", {"probe_2664.py": _PROBE, "conftest.py": _BEFORE}, "-p", "no:randomly"
    )
    assert code == 0, both(out, err)
    assert "2 passed" in out, both(out, err)
