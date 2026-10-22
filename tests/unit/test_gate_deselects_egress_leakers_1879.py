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
from pathlib import Path

import pytest

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


def _assert_child_completed(proc, what):
    """#3160: a child that failed to collect is its own failure.

    Measured (this seat, and issue #3160 on the R1107 union red): a module
    that fails to import next to CLUEDO_FILE still ends its stdout with
    "5/7 tests collected (2 deselected), 1 error" and exits rc=2 -- so the
    "tests collected" completion check passes, the five classes read as
    blanket-marking, and the child's output is thrown away with nothing
    left to diagnose. rc=5 is a COMPLETED collect that selected nothing
    ("no tests collected (62 deselected)", measured) -- the maximal
    blanket-marking case, which the assertions below judge, not this check.
    """
    assert proc.returncode in (0, 5), (
        f"#3160: {what} exited rc={proc.returncode} -- the child did not "
        "finish collecting (rc=2: a module failed to collect -- import "
        "error, poisoned env; rc=4: usage error, e.g. a missing path). "
        "This is NOT blanket-marking evidence.\n"
        f"stdout tail:\n{proc.stdout[-1500:]}\n"
        f"stderr tail:\n{proc.stderr[-1500:]}"
    )


def _collect(*paths, marker=None, what="collect-only child"):
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
    _assert_child_completed(proc, what)
    return proc, _admitted_nodeids(proc.stdout)


def test_gate_filter_deselects_cluedo_and_keeps_chain_admitted():
    proc, admitted = _collect(
        CLUEDO_FILE,
        FALLBACKS_FILE,
        marker="not slow and not requires_api",
        what="the gate-filtered collect (cluedo + fallbacks)",
    )

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
    _, unfiltered = _collect(
        CLUEDO_FILE, what="the unfiltered cluedo collect (leaker control)"
    )
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
    # #3160: the blanket accusation must stand on its OWN evidence -- the
    # classes exist unfiltered and vanish only under the filter. The
    # unfiltered collect is shared with the per-test check at the end.
    _, chain_unfiltered = _collect(
        FALLBACKS_FILE, what="the unfiltered fallbacks collect"
    )
    blanket_deselected = []
    not_collected_unfiltered = []
    for prefix in MUST_STAY_ADMITTED_PREFIX:
        if any(nid.startswith(prefix) for nid in admitted):
            continue
        name = prefix.split("::")[-1]
        if any(nid.startswith(prefix) for nid in chain_unfiltered):
            blanket_deselected.append(name)
        else:
            not_collected_unfiltered.append(name)
    assert not blanket_deselected, (
        "#1879 anti-pendulum: fallback-chain classes are NO LONGER admitted "
        "by the gate filter — the leak was 'fixed' by blanket-marking instead "
        f"of the translator short-circuit. Missing: {blanket_deselected}"
    )
    assert not not_collected_unfiltered, (
        "#3160: fallback-chain classes are missing from the UNFILTERED "
        "collect too -- test_tweety_fallbacks no longer collects them "
        "(renamed, moved, or a dead import), so their absence under the "
        "gate filter is not blanket-marking evidence. Missing unfiltered: "
        f"{not_collected_unfiltered}"
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


def test_child_collection_error_is_its_own_failure(monkeypatch):
    # #3160 witness, born red: FALLBACKS_FILE pointed at a module that
    # fails to import. The filtered child then exits rc=2 while its stdout
    # still ends with "N/M tests collected (K deselected), 1 error" -- so
    # the old guard walked past its completion check and accused blanket-
    # marking (the unreproduced R1107 union red). The fix makes the child's
    # collection error its OWN failure, carrying the child's output.
    repo_root = Path(__file__).resolve().parents[2]
    broken = repo_root / ".tmp" / "test_broken_import_3160_witness.py"
    broken.parent.mkdir(parents=True, exist_ok=True)
    broken.write_text(
        "import module_absent_3160_witness  # noqa: F401 -- unresolvable by design\n",
        encoding="utf-8",
    )
    try:
        monkeypatch.setattr(sys.modules[__name__], "FALLBACKS_FILE", str(broken))
        with pytest.raises(AssertionError) as excinfo:
            test_gate_filter_deselects_cluedo_and_keeps_chain_admitted()
        msg = str(excinfo.value)
        assert "rc=2" in msg, (
            "#3160: the failure must name the child's collection error "
            f"(rc=2), not a marker story. Got:\n{msg[:800]}"
        )
        assert "test_broken_import_3160_witness" in msg, (
            "#3160: the failure must carry the child's error line (the "
            f"module that failed to collect). Got:\n{msg[:800]}"
        )
        assert "NO LONGER admitted" not in msg, (
            "#3160: a child collection error was read as blanket-marking "
            "-- the exact false accusation of the R1107 union red. Got:\n"
            f"{msg[:800]}"
        )
    finally:
        broken.unlink(missing_ok=True)
