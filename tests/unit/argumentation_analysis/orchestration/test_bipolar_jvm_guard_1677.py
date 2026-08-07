"""#1677 — the bipolar honest-absent branch must be reachable without jpype.

``_invoke_bipolar`` gained an honest-absent branch in #1670 (PR #1670): *« JVM
absente ⇒ dict dégradé, la phase continue »*. The coordinator measured
firsthand (#1677) that this branch was **unreachable** in a jpype-less
environment: ``jvm_setup`` imports ``jpype`` at module level, and the line
``from ...jvm_setup import is_jvm_started`` sat *before* the ``try`` — so in a
jpype-less env that very import raised ``ImportError`` uncaught, and the
degraded branch (the exact env it targets) never fired.

The fix (this PR) guards the JVM-state resolution with ``try/except
ImportError`` so a missing jpype/jvm_setup resolves to ``jvm_up = False``; the
``try``'s ``bipolar_handler`` import then raises the same ``ImportError``, is
caught, and the honest-absent dict fires.

This test reproduces the jpype-less environment faithfully (a ``sys.meta_path``
finder that refuses ``jpype``) and asserts the contract: the degraded dict is
returned, not an uncaught ``ImportError``. **Differential**: revert the guard
and this test fails with ``ModuleNotFoundError`` instead of asserting the dict.

Privacy: synthetic atoms only (``prop_1``, ``prop_2``) — no corpus content.
"""

from __future__ import annotations

import sys

import pytest

import argumentation_analysis.orchestration.invoke_callables as mod

_LONG_TEXT = "A sufficiently long synthetic source text for the phases. " * 6


class _JpypeBlocker:
    """A sys.meta_path finder that refuses to import ``jpype``.

    Simulates a jpype-less environment for the duration of one call. Inserted
    at ``meta_path[0]`` so it wins over the real finders.
    """

    def find_spec(self, name, path=None, target=None):  # noqa: D401, ANN001
        if name == "jpype" or name.startswith("jpype."):
            raise ModuleNotFoundError(
                f"No module named '{name}' (simulated jpype-less env, #1677)"
            )
        return None


@pytest.fixture
def jpype_absent():
    """Block jpype and evict the modules that import it, for one test.

    Snapshots every evicted module and restores them in teardown so the rest
    of the session sees the real jpype/jvm_setup/bipolar_handler again.
    """
    blocker = _JpypeBlocker()
    evicted: dict[str, object] = {}
    for mname in list(sys.modules):
        if (
            mname == "jpype"
            or mname.startswith("jpype.")
            or mname.endswith("jvm_setup")
            or mname.endswith("bipolar_handler")
            or mname.endswith("agents.core.logic")
        ):
            evicted[mname] = sys.modules.pop(mname)
    sys.meta_path.insert(0, blocker)
    try:
        yield
    finally:
        if blocker in sys.meta_path:
            sys.meta_path.remove(blocker)
        # Restore the exact module objects the session had before, so later
        # tests re-acquire the real (already-imported) jpype-backed modules.
        sys.modules.update(evicted)


def test_honest_absent_reachable_without_jpype(jpype_absent) -> None:
    """A jpype-less env reaches the honest-absent dict, never an uncaught raise.

    Mirrors the coordinator's firsthand probe (#1677): 1 synthetic support
    pair, jpype blocked on meta_path. Pre-fix this raised ModuleNotFoundError
    from the unguarded ``from ...jvm_setup import is_jvm_started``; post-fix
    the guard routes it to ``jvm_up = False`` and the honest-absent dict fires.
    """
    import asyncio

    ctx = {
        "arguments": ["prop_1", "prop_2"],
        "supports": [["prop_1", "prop_2"]],
        "attacks": [],
    }
    out = asyncio.new_event_loop().run_until_complete(
        mod._invoke_bipolar(_LONG_TEXT, ctx)
    )
    assert out["degraded"] is True
    assert out["absent_reason"] == "jvm_not_started"
    # tri-state: None = not computed (JVM absent), never a fabricated empty set
    assert out["extensions"] is None
    # the translator-established support is echoed, not zeroed
    assert out["supports"] == [["prop_1", "prop_2"]]
    assert out["statistics"]["backend"] == "jvm-unavailable"
