"""#1677 — the bipolar honest-absent branch must be reachable without jpype.

``_invoke_bipolar`` gained an honest-absent branch in #1670 (PR #1670): *« JVM
absente ⇒ dict dégradé, la phase continue »*. The coordinator measured
firsthand (#1677) that this branch was **unreachable in a jpype-less
environment**: ``jvm_setup`` imports ``jpype`` at module level, and the line
``from ...jvm_setup import is_jvm_started`` sat *before* the ``try`` — so in a
jpype-less env that very import raised ``ImportError`` uncaught, and the
degraded branch (the exact env it targets) never fired.

The fix (this PR) guards the JVM-state resolution with ``try/except
ImportError`` so a missing jpype/jvm_setup resolves to ``jvm_up = False``; the
``try``'s ``bipolar_handler`` import then raises the same ``ImportError``, is
caught, and the honest-absent dict fires.

**Why a subprocess, not a ``sys.modules`` fixture**: the only faithful way to
simulate "jpype not importable" is a ``sys.meta_path`` finder that refuses
``jpype``. Doing that inside the main pytest session corrupts the shared
``agents.core.logic`` / ``jvm_setup`` module objects and makes *later,
unrelated* tests fail (AttributeError in ``__init__.py``) — the exact CI
regression this test caused in its first revision (8 downstream failures in
``test_dung_aspic_wiring``). A subprocess isolates the meta_path manipulation
completely: it starts clean, the blocker never touches the main session, and
teardown is "the process exits".

Privacy: synthetic atoms only (``prop_1``, ``prop_2``) — no corpus content.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap

# A self-contained probe that simulates a jpype-less environment. It installs
# a ``sys.meta_path`` finder refusing ``jpype`` BEFORE importing anything from
# the project, then calls ``_invoke_bipolar`` with one synthetic support pair
# and prints a single machine-parseable marker line describing the outcome.
# ``RETURNED <json-ish>`` on the degraded dict, ``RAISED <type>: <msg>`` if the
# unguarded import leaked through. The main session asserts on that marker.
_PROBE = textwrap.dedent("""
    import asyncio, json, sys


    class _Blocker:
        def find_spec(self, name, path=None, target=None):
            if name == "jpype" or name.startswith("jpype."):
                raise ModuleNotFoundError("No module named '%s' (simulated jpype-less env, #1677)" % name)
            return None


    sys.meta_path.insert(0, _Blocker())

    import argumentation_analysis.orchestration.invoke_callables as mod

    ctx = {
        "arguments": ["prop_1", "prop_2"],
        "supports": [["prop_1", "prop_2"]],
        "attacks": [],
    }
    try:
        out = asyncio.new_event_loop().run_until_complete(
            mod._invoke_bipolar("synthetic probe text", ctx)
        )
        print("RETURNED " + json.dumps({
            "degraded": out.get("degraded"),
            "absent_reason": out.get("absent_reason"),
            "extensions": out.get("extensions"),
            "supports": out.get("supports"),
            "backend": out.get("statistics", {}).get("backend"),
        }))
    except Exception as e:
        print("RAISED %s: %s" % (type(e).__name__, e))
    """)


def _run_probe() -> str:
    """Run the jpype-less probe in a clean subprocess; return its last stdout line."""
    result = subprocess.run(
        [sys.executable, "-c", _PROBE],
        capture_output=True,
        text=True,
        timeout=180,
    )
    lines = [ln.strip() for ln in result.stdout.splitlines() if ln.strip()]
    if not lines:
        # No marker line means the probe crashed before printing one.
        raise AssertionError(
            "probe produced no marker line.\\nstderr:\\n" + result.stderr[-2000:]
        )
    return lines[-1]


def test_honest_absent_reachable_without_jpype() -> None:
    """A jpype-less env reaches the honest-absent dict, never an uncaught raise.

    Pre-fix this raised ``ModuleNotFoundError`` from the unguarded
    ``from ...jvm_setup import is_jvm_started``; post-fix the guard routes it
    to ``jvm_up = False`` and the honest-absent dict fires. Run in a subprocess
    so the meta_path blocker never pollutes the main pytest session.
    """
    marker = _run_probe()
    assert marker.startswith("RETURNED "), (
        "expected the honest-absent dict, but the probe " + marker
    )
    # The marker's payload follows the word RETURNED; re-parse the JSON object.
    import json

    payload = json.loads(marker[len("RETURNED ") :])
    assert payload["degraded"] is True
    assert payload["absent_reason"] == "jvm_not_started"
    # tri-state: None = not computed (JVM absent), never a fabricated empty set
    assert payload["extensions"] is None
    # the translator-established support is echoed, not zeroed
    assert payload["supports"] == [["prop_1", "prop_2"]]
    assert payload["backend"] == "jvm-unavailable"
