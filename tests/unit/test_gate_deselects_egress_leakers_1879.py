"""Guard #1879: the gate filter must deselect the cluedo LLM orchestrator, and
must NOT deselect the tweety_fallbacks chain tests.

The #1872 post-fix positional measurement (local, real key) attributed 14 more
watched-LLM POSTs to two files the widened argv admitted:

- ``test_cluedo_orchestration_integration.py::test_real_group_chat_orchestration``
  fires 1 real POST to api.openai.com. The test's PURPOSE is the real
  AgentGroupChat orchestration, so the fix is ``requires_api`` (a mock would
  gut it), not a translator short-circuit.
- ``test_tweety_fallbacks.py`` — 13 tests firing 1 POST each to
  openrouter.ai. Those tests validate the fallback CHAIN, not the translation,
  so the fix is the R846/#1836 caller-context short-circuit (see the *_CTX
  constants and TestNoTranslatorEgressGuard in that file) — and they must stay
  runnable under the gate filter. Blanket-marking the module ``requires_api``
  would "fix" the leak by deselecting 13 chain tests that need no API: this
  guard reddens against that pendulum too.

Decisive, not static: the guard re-applies the actual gate filter
(``--collect-only -m "not slow and not requires_api"``) over both files and
asserts both directions. ``--disable-jvm-session`` keeps collection fast
without changing what the filter admits. Collect-only runs no test, so no LLM
call is made and no egress cost is paid here.
"""

import re
import subprocess
import sys

CLUEDO_FILE = "tests/integration/triage/test_cluedo_orchestration_integration.py"
FALLBACKS_FILE = "tests/integration/triage/test_tweety_fallbacks.py"

LEAKER_NODEID = (
    f"{CLUEDO_FILE}::TestCluedoOrchestrationRealIntegration::"
    "test_real_group_chat_orchestration"
)

# The 13 chain tests + the in-file sentinel guard must remain ADMITTED — they
# validate the fallback chain and need no API. If any shows up as deselected,
# someone blanket-marked the module (#1879 anti-pendulum leg).
MUST_STAY_ADMITTED_PREFIX = (
    f"{FALLBACKS_FILE}::TestInvokeAspicFallback",
    f"{FALLBACKS_FILE}::TestInvokeBipolarFallback",
    f"{FALLBACKS_FILE}::TestInvokeAbaFallback",
    f"{FALLBACKS_FILE}::TestInvokeProbabilisticFallback",
    f"{FALLBACKS_FILE}::TestNoTranslatorEgressGuard",
)

_NODEID_RE = re.compile(r"^\S+::\S+$")


def _admitted_nodeids(out: str):
    return {line.strip() for line in out.splitlines() if _NODEID_RE.match(line.strip())}


def _collect(*paths, marker=None):
    """Collect `paths`, optionally under a marker expression."""
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "--collect-only",
        "--disable-jvm-session",
        "-q",
    ]
    if marker is not None:
        cmd += ["-m", marker]
    cmd += list(paths)
    proc = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    return proc, _admitted_nodeids(proc.stdout)


def test_gate_filter_deselects_cluedo_and_keeps_chain_admitted():
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "--collect-only",
        "--disable-jvm-session",
        "-q",
        "-m",
        "not slow and not requires_api",
        CLUEDO_FILE,
        FALLBACKS_FILE,
    ]
    proc = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    admitted = _admitted_nodeids(proc.stdout)

    assert "tests collected" in proc.stdout, (
        f"#1879: collect-only did not complete (rc={proc.returncode}); "
        "cannot verify the leaker's deselection.\n"
        f"stderr tail:\n{proc.stderr[-1500:]}"
    )
    # Positive control on the instrument, read BEFORE its zero. LEAKER_NODEID
    # is a frozen string: rename the class, move the file, or rename the method
    # and `LEAKER_NODEID not in admitted` becomes true *vacuously*, forever --
    # and it disarms exactly when someone next drops the marker. Measured on a
    # mutation that renamed the class AND removed requires_api: this file stayed
    # green while the leaker was admitted by the gate filter. So: the nodeid
    # must first be shown to EXIST in an unfiltered collect. A zero from an
    # instrument that never saw a one is not a measurement.
    _, unfiltered = _collect(CLUEDO_FILE)
    assert LEAKER_NODEID in unfiltered, (
        "#1879: the leaker nodeid no longer exists, so the deselection "
        "assertion below can only pass vacuously. The test was renamed or "
        "moved -- point LEAKER_NODEID at its new nodeid rather than deleting "
        "this control. Admitted unfiltered: "
        + repr(sorted(nid for nid in unfiltered if "Cluedo" in nid))
    )

    assert LEAKER_NODEID not in admitted, (
        "#1879: test_real_group_chat_orchestration is ADMITTED by the gate "
        "filter — its requires_api marker was likely removed, and it fires a "
        "real api.openai.com POST per admitted run (measured #1872 post-fix)."
    )
    blanket_deselected = []
    for prefix in MUST_STAY_ADMITTED_PREFIX:
        if not any(nid.startswith(prefix) for nid in admitted):
            blanket_deselected.append(prefix.split("::")[-1])
    assert not blanket_deselected, (
        "#1879 anti-pendulum: fallback-chain classes are NO LONGER admitted "
        "by the gate filter — the leak was 'fixed' by blanket-marking instead "
        f"of the translator short-circuit. Missing: {blanket_deselected}"
    )

    # The prefix check above only demands ONE admitted test per class, while
    # the defect it guards -- a marker on a method -- is per TEST. Marking 12
    # of 13 and leaving one survivor per class kept it green: the granularity
    # of the discriminator was coarser than the granularity of the defect.
    # The chain tests need no API, so the honest invariant is that the gate
    # filter deselects NONE of them. Measured on this branch: 62 collected
    # unfiltered, 62 admitted under the gate filter, 0 deselected.
    #
    # If a chain test ever legitimately earns `slow`, this reddens -- which is
    # the point: that is a decision to take on purpose, not to discover later
    # from an egress bill.
    _, chain_unfiltered = _collect(FALLBACKS_FILE)
    dropped = sorted(
        nid
        for nid in chain_unfiltered
        if nid not in admitted and nid.startswith(FALLBACKS_FILE)
    )
    assert (
        not dropped
    ), "#1879 anti-pendulum (per-test): the gate filter deselects " + str(
        len(dropped)
    ) + " of the " + str(
        len(chain_unfiltered)
    ) + " fallback-chain tests. They need no API key, so a marker was added " "somewhere it does not belong: " + repr(
        [nid.split("::", 1)[-1] for nid in dropped[:8]]
    )
