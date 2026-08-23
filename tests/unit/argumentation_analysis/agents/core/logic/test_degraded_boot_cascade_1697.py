"""#1697 — the jpype import cascade no longer blocks the degraded boot.

Pre-fix (measured on main ``86e2ba01``), importing the logic layer without
jpype raised ``ModuleNotFoundError`` at IMPORT time, via the cascade the
ticket names:

    web_api validation_service → web_api logic_service (:25 ``logic_factory``)
      → agents.core.logic.__init__ (eager agent imports)
        → propositional_logic_agent (:35) → tweety_initializer (:8)
        → jvm_setup (:5) / tweety_bridge (:17)  — bare ``import jpype``

so neither the MCP server nor the web API could boot degraded: the honest-absent
branch ("JVM unavailable ⇒ boot degraded, phase continues") was unreachable —
the same meta-pattern as #1677, one layer deeper.

The fix guards the three module-level bare ``import jpype`` nodes of the named
cascade (``tweety_bridge``, ``tweety_initializer``, ``jvm_setup`` — try/except
``ImportError`` binding ``jpype = None``) and defers the handler-class imports
to their point of use (``from __future__ import annotations`` + local imports
in the properties, the pattern ``qbf_handler`` already used): every handler
module bare-imports jpype, so importing them eagerly dragged the whole layer
in. This test does NOT lazy-import anything else — the ticket names this
cascade, not a global import policy.

**Why a subprocess, not a ``sys.modules`` fixture** (R772 / #1677 lesson): a
``sys.meta_path`` finder refusing jpype inside the main pytest session corrupts
the shared ``agents.core.logic`` module objects and makes later, unrelated
tests fail. The subprocess isolates the manipulation completely (exit =
teardown).

**Né-rouge**: on the pre-fix tree this same probe printed
``RAISED ModuleNotFoundError`` for every chain member (measured firsthand —
logic package, logic_factory, web_api logic_service, web_api validation_service
all red); post-fix every member imports and the bridge constructs degraded.

Privacy: no corpus content — pure boot-path guard, synthetic markers only.
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap

_PROBE = textwrap.dedent(
    """\
    import json, sys


    class _Blocker:
        def find_spec(self, name, path=None, target=None):
            if name == "jpype" or name.startswith("jpype."):
                raise ModuleNotFoundError(
                    "No module named '%s' (simulated jpype-less env, #1697)" % name
                )
            return None


    sys.meta_path.insert(0, _Blocker())

    # The DoD chain, import order matters: each member must import WITHOUT
    # raising. Pre-fix, the FIRST member already raised ModuleNotFoundError.
    import argumentation_analysis.agents.core.logic  # noqa: F401
    from argumentation_analysis.agents.core.logic.logic_factory import (  # noqa: F401
        LogicAgentFactory,
    )
    from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge
    from argumentation_analysis.services.web_api.services.logic_service import (  # noqa: F401
        LogicService,
    )
    from argumentation_analysis.services.web_api.services.validation_service import (  # noqa: F401
        ValidationService,
    )

    # Honest-absent END-TO-END, not just import: the bridge OBJECT is
    # constructible, reports the JVM as NOT ready (so downstream guards fire),
    # and initialize_jvm raises a clear RuntimeError — never a masked
    # AttributeError ('NoneType' has no attribute ...) from a None jpype.
    bridge = TweetyBridge()
    degraded_initializer = bridge._initializer is not None
    jvm_ready = bridge.initializer.is_jvm_ready()
    init_error = None
    try:
        bridge.initialize_jvm()
    except RuntimeError as e:
        init_error = str(e)
    except Exception as e:  # noqa: BLE001 — surfaced verbatim to the test
        init_error = "%s: %s" % (type(e).__name__, e)

    print("RETURNED " + json.dumps({
        "degraded_initializer": degraded_initializer,
        "jvm_ready": jvm_ready,
        "initialize_jvm_raised_runtimeerror": init_error is not None
        and "jpype is not installed" in init_error,
        "initialize_jvm_error": init_error,
    }))
"""
)


def _run_probe() -> dict:
    """Run the jpype-less cascade probe in a clean subprocess; parse its marker."""
    result = subprocess.run(
        [sys.executable, "-c", _PROBE],
        capture_output=True,
        text=True,
        timeout=180,
    )
    lines = [ln.strip() for ln in result.stdout.splitlines() if ln.strip()]
    marker = lines[-1] if lines else ""
    assert marker.startswith("RETURNED "), (
        "the degraded boot cascade is broken — the probe raised before "
        "finishing (expected every chain member to import without jpype):\n"
        "marker: " + (marker or "<none>") + "\nstderr:\n" + result.stderr[-2000:]
    )
    return json.loads(marker[len("RETURNED ") :])


def test_cascade_imports_degraded_without_jpype() -> None:
    """Every member of the #1697 cascade imports in a jpype-less subprocess.

    Red on the pre-fix tree (``ModuleNotFoundError: import of jpype`` raised by
    tweety_bridge/jvm_setup through the eager chain); green once the three
    module-level bare ``import jpype`` nodes are guarded and the handler
    imports deferred to point of use.
    """
    payload = _run_probe()  # the assert inside already proves the imports
    assert payload["degraded_initializer"] is True, (
        "jpype absent ⇒ the bridge must still construct with a degraded "
        "initializer, not a None one (downstream property guards would "
        "AttributeError instead of raising the honest RuntimeError)"
    )
    assert payload["jvm_ready"] is False, (
        "jpype absent ⇒ is_jvm_ready() must report False — the honest-absent "
        "signal every handler-property guard reads"
    )
    assert payload["initialize_jvm_raised_runtimeerror"] is True, (
        "jpype absent ⇒ initialize_jvm() must raise the explicit "
        "'jpype is not installed' RuntimeError, never a masked AttributeError "
        "(anti-R772: the cause stays named). Got: "
        + repr(payload["initialize_jvm_error"])
    )


def test_subprocess_inherits_pytest_env_marker() -> None:
    """The coordinator's warning, verified instead of assumed (#1697 dispatch).

    Since #1866, ``AppServices.__init__`` calls ``create_llm_service``, which
    returns a mock under pytest (``PYTEST_CURRENT_TEST`` in ``os.environ``,
    llm_service.py:114) and a real service otherwise. A boot probe spawned
    from a test inherits ``os.environ``, so the mock applies and the LLM key
    is NOT the next barrier measured. This test asserts the inheritance
    explicitly — if it ever breaks, the cascade probes above would silently
    measure the LLM-key barrier instead of jpype.
    """
    code = "import json, os; print(json.dumps('PYTEST_CURRENT_TEST' in os.environ))"
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.stdout.strip().endswith("true"), (
        "a subprocess spawned from pytest no longer inherits "
        "PYTEST_CURRENT_TEST — the degraded-boot probes would hit the real "
        "LLM factory (and the OPENAI_API_KEY barrier) instead of the jpype "
        "cascade; their verdicts would be measuring the wrong barrier"
    )
