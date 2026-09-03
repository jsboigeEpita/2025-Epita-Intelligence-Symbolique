"""#2021 — the local skip-storm signal is tied to the CI guard, not a second opinion.

Three agents hit the same shape in one round: a pytest session returning in
under a second having skipped everything it collected, with exit code 0. The
CI workflow already fails loud on that (``ci.yml`` #1385/#1873) — but the
cluster's verification discipline (born-red, suite runs) executes LOCALLY,
where the storm looked benign. ``tests/jvm_skip_storm_signal.py`` is the
local twin, wired from ``tests/conftest.py``.

The tests here close three holes in that deliverable:

1. **Drift.** The signal and the CI pwsh guard are two implementations of
   one rule; these tests replay BOTH on the real population of skip
   literals harvested from ``tests/`` (the #1873 harvest, reused, not
   re-invented) and on the CI guard's own 12-case discriminant, and assert
   they always agree. Neither definition can silently drift from the other.
2. **Wolves.** The legitimate-skip population (opt-in USE_REAL_JPYPE,
   orphan-model, optional dependency) stays out of the numerator, and the
   threshold is strictly-greater — a guard that cries on a healthy run gets
   disabled, and then the storm goes unseen again (#1873 anti-pendulum).
3. **Extraction.** The reason is matched, never the file path — a test
   FILE named ``..._jvm_...`` is not a JVM skip, exactly as the CI pattern
   is anchored on ``<skipped ... message="`` so that ``<failure>`` lines
   never count.

Tests are fixture-free on purpose (hand-rolled loops, no pytest.mark, no
fixtures): the local session this guard exists for skips wholesale when the
JVM cannot start, so these must be runnable by direct invocation too.
"""

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.jvm_skip_storm_signal import (  # noqa: E402
    JVM_REASON_RE,
    STORM_THRESHOLD,
    SkipStormCounter,
    skip_reason,
    storm_verdict,
    ventilate,
)
from tests.unit.test_ci_guard_signature_contract_1873 import (  # noqa: E402
    CONFTEST,
    _as_junit_skip,
    _guard_pattern,
    _skip_literals,
)

# The CI guard's own negative population: the four parametrized legitimate
# skips of test_ci_guard_signature_contract_1873 plus the <failure> line.
# These carry no JVM token in their reason and must stay out of the
# numerator in BOTH definitions.
LEGITIMATE_NON_MATCHES = [
    "needs USE_REAL_JPYPE=true (real Tweety, skipped in CI)",
    "set USE_REAL_JPYPE=true to exercise real Tweety parsing",
    "Orphan model without a provider (B-06 #810)",
    "optional dependency missing",
]
FAILURE_LINE = '<failure message="AssertionError: JVM classpath empty">trace</failure>'


class _FakeReport:
    def __init__(self, nodeid, outcome, longrepr):
        self.nodeid = nodeid
        self.outcome = outcome
        self.longrepr = longrepr


# --- 1. one rule, two implementations, always the same verdict --------------


def test_signal_and_ci_guard_agree_on_the_real_population():
    """Every skip literal in tests/ must get the SAME verdict from the local
    signal (reason regex) and the CI guard (ci.yml pattern on the
    junit-escaped form) — the #1873 harvest, replayed on both.

    The agreement is asserted on the WHOLE literal population, not only the
    JVM-bearing ones: widening the local family (the pendulum — "Real Tweety
    not available" entering the numerator) only diverges on literals that
    carry no JVM token, so a JVM-only population could not see it.
    """
    ci_pattern = re.compile(_guard_pattern())
    disagreements = []
    jvm_signed = 0
    for path in (ROOT / "tests").rglob("*.py"):
        for message in _skip_literals(path):
            local = bool(JVM_REASON_RE.search(message))
            ci = bool(ci_pattern.search(_as_junit_skip(message)))
            if local:
                jvm_signed += 1
            if local != ci:
                disagreements.append(
                    f"{path.relative_to(ROOT)}: local={local} ci={ci}: {message!r}"
                )
    assert jvm_signed >= 8, (
        f"harvest found only {jvm_signed} JVM-signature skip literals — the "
        "instrument is not reaching the files it is supposed to read"
    )
    assert not disagreements, (
        "the local signal and the CI guard disagree on these literals, so one "
        "of the two definitions has drifted:\n  " + "\n  ".join(disagreements)
    )


def test_the_ci_guards_negative_population_stays_out():
    """The legitimate skips and the failure line are invisible to the signal,
    not just to the CI guard (a local signal that cries wolf gets disabled,
    and then the storm goes unseen again)."""
    for message in LEGITIMATE_NON_MATCHES:
        assert not JVM_REASON_RE.search(message), message
        assert (
            skip_reason(
                _FakeReport("x", "skipped", ("some/path.py", 1, f"Skipped: {message}"))
            )
            == message
        )
    # A failed test mentioning the JVM is not a skip: the signal reads
    # report.longrepr only when outcome == "skipped".
    assert skip_reason(_FakeReport("x", "failed", FAILURE_LINE)) is None


def test_the_three_conftest_signatures_are_counted():
    """The three #1641 messages (harvested from conftest, not restated) are
    inside the family, in both definitions."""
    messages = _skip_literals(CONFTEST, within="jvm_session")
    assert len(messages) >= 3, f"expected the three #1641 messages, got {messages}"
    ci_pattern = re.compile(_guard_pattern())
    for message in messages:
        assert JVM_REASON_RE.search(message), message
        assert ci_pattern.search(_as_junit_skip(message)), message


# --- 2. the verdict: fail-loud on vacuity, silent on health -----------------


def test_verdict_shouts_on_a_wholesale_storm():
    # The shape the issue was opened on: 7 of 7 skipped in 0.67s, exit 0.
    shout, message = storm_verdict(7, 7)
    assert shout and "7 of 7" in message and "decided nothing" in message


def test_verdict_is_strictly_greater_than_the_threshold():
    assert STORM_THRESHOLD == 0.5
    assert not storm_verdict(100, 50)[0]  # exactly 50%: silent, like ci.yml -gt 0.5
    assert storm_verdict(100, 51)[0]


def test_verdict_is_silent_on_a_healthy_run():
    # CI baseline shape: ~15k collected, hundreds of legitimate skips that
    # carry no JVM token — the numerator stays 0.
    shout, message = storm_verdict(15463, 0)
    assert not shout


def test_verdict_shouts_on_an_empty_collection():
    # The #1556 hole: a session that collected nothing is not a success.
    shout, message = storm_verdict(0, 0)
    assert shout and "#1556" in message


# --- 3. extraction: the reason, never the path ------------------------------


def test_a_file_name_containing_jvm_is_not_a_signature():
    report = _FakeReport(
        "tests/unit/argumentation_analysis/core/test_jvm_classpath_1874.py::test_x",
        "skipped",
        (
            "tests/unit/argumentation_analysis/core/test_jvm_classpath_1874.py",
            7,
            "Skipped: optional dependency missing",
        ),
    )
    counter = SkipStormCounter()
    counter.add(report)
    assert counter.total_skips == 1
    assert counter.jvm_signature_reasons() == []


def test_counter_dedupes_per_nodeid():
    counter = SkipStormCounter()
    reason = "Saut du test car la JVM n'est pas réellement démarrée (jpype.isJVMStarted() = False)."
    counter.add(_FakeReport("a::t", "skipped", ("p", 1, f"Skipped: {reason}")))
    counter.add(_FakeReport("a::t", "skipped", ("p", 1, f"Skipped: {reason}")))
    assert counter.total_skips == 1
    assert len(counter.jvm_signature_reasons()) == 1
    counter.reset()
    assert counter.total_skips == 0
    assert counter.jvm_signature_reasons() == []


def test_ventilation_names_the_dominant_cause():
    reasons = [
        "Saut du test car l'initialisation de la JVM a échoué dans pytest_sessionstart.",
        "Saut du test car la JVM n'est pas réellement démarrée (jpype.isJVMStarted() = False).",
        "Saut du test car la JVM est démarrée mais non fonctionnelle (JClass health check échoué).",
        "JVM not started — cannot exercise real Tweety reasoning",
    ]
    text = ventilate(reasons)
    assert "decided init failure" in text
    assert "not actually started" in text
    assert "unhealthy" in text
    assert "outside the three conftest signatures" in text
    assert "1 x" in text  # the fourth reason is ventilated as outside


# --- 4. the wiring: conftest actually consults the signal --------------------


def test_conftest_wires_the_signal():
    """If the hooks stop feeding/consulting the counter, the signal is dead
    code and the local storm is benign-looking again — this reddens first."""
    source = (ROOT / "tests" / "conftest.py").read_text(encoding="utf-8-sig")
    tree = ast.parse(source)
    functions = {
        node.name: node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
    }

    def _mentions(func_name, name):
        for n in ast.walk(functions[func_name]):
            if isinstance(n, ast.Attribute) and n.attr == name:
                return True
            if isinstance(n, ast.Name) and n.id == name:
                return True
        return False

    assert "pytest_runtest_logreport" in functions, "the logreport hook is gone"
    assert _mentions(
        "pytest_runtest_logreport", "add"
    ), "pytest_runtest_logreport no longer feeds the skip-storm counter"
    assert "pytest_sessionfinish" in functions
    assert _mentions(
        "pytest_sessionfinish", "_skip_storm_signal"
    ), "pytest_sessionfinish no longer consults the skip-storm signal"
    assert "_skip_storm_signal" in functions
    signal_src = ast.dump(functions["_skip_storm_signal"])
    for needle in ("jvm_signature_reasons", "exit"):
        assert needle in signal_src, (
            f"_skip_storm_signal lost its {needle!r} — read it before trusting "
            "the wiring test"
        )
