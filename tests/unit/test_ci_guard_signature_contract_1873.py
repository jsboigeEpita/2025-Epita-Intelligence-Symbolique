"""#1873: the CI storm guard's signature contract is enforced, not commented.

The guard in `.github/workflows/ci.yml` counts skips whose message carries the
JVM token. Main counts **one** literal, "JVM n'est pas réellement démarrée";
#1641 had meanwhile split the conftest guard into three messages, and the one
main still reads is the *mildest* of the three. The severe half -- "l'initiali-
sation de la JVM a échoué dans pytest_sessionstart" -- landed in the blind spot,
so run 32706721429 printed ``0 / 15010 (0%) ✅ OK`` on a 15010-skip storm and
the job concluded ``success``.

The fix put the contract in a **comment**: "If you add a fourth, it must keep
that shape or widen $jvmPattern." A comment is exactly what failed the first
time -- nothing made #1641 keep the shape. These tests make the contract
executable, and they read the pattern **out of `ci.yml`** rather than restating
it, so the guard and its test cannot drift apart.

Failure scenario they close: someone adds ``pytest.skip("JVM indisponible: …")``
in October, the guard counts 0, the job prints ``✅ OK``, and nobody notices --
for the same reason as last time.
"""

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CI_YML = ROOT / ".github" / "workflows" / "ci.yml"
CONFTEST = ROOT / "tests" / "conftest.py"

# The guard's own line, so this file cannot assert against a stale copy.
PATTERN_LINE = re.compile(r"^\s*\$jvmPattern\s*=\s*'(?P<pat>.+)'\s*$", re.MULTILINE)


def _guard_pattern() -> str:
    """The regex the CI guard actually uses, read from the workflow."""
    text = CI_YML.read_text(encoding="utf-8")
    match = PATTERN_LINE.search(text)
    assert match, (
        "no `$jvmPattern = '...'` assignment found in ci.yml — the guard was "
        "renamed or removed, and this contract test is now measuring nothing"
    )
    return match.group("pat")


def _as_junit_skip(message: str) -> str:
    """The shape pytest writes into the junit report for `pytest.skip(message)`."""
    escaped = message.replace("&", "&amp;").replace("<", "&lt;").replace('"', "&quot;")
    return f'<skipped type="pytest.skip" message="{escaped}"/>'


def _skip_literals(path: Path, within: str | None = None) -> list[str]:
    """Every constant-string `pytest.skip(...)` argument in `path`.

    `within` restricts the harvest to one function definition. Only literal
    arguments are collected: an f-string message cannot be checked statically,
    and pretending otherwise would make the harvest look larger than its reach.
    """
    # `utf-8-sig`: several test files carry a UTF-8 BOM, and `ast.parse` refuses
    # a source starting with U+FEFF. Reading them as plain utf-8 would raise here
    # -- or, if the exception were swallowed, silently shrink the harvest, which
    # is how an instrument reports a comfortable zero.
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    scope = tree
    if within is not None:
        scope = next(
            (
                node
                for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == within
            ),
            None,
        )
        assert scope is not None, f"{path.name}: no function named {within!r}"

    found = []
    for node in ast.walk(scope):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        is_skip = (isinstance(func, ast.Attribute) and func.attr == "skip") or (
            isinstance(func, ast.Name) and func.id == "skip"
        )
        if is_skip and node.args and isinstance(node.args[0], ast.Constant):
            value = node.args[0].value
            if isinstance(value, str):
                found.append(value)
    return found


def test_the_conftest_session_guard_messages_are_all_counted():
    """The three messages #1641 split apart, plus any fourth added later."""
    pattern = _guard_pattern()
    messages = _skip_literals(CONFTEST, within="jvm_session")

    # Non-vacuity: an empty harvest would pass every assertion below while
    # measuring nothing -- the exact shape a zero from an unproven instrument has.
    assert len(messages) >= 3, (
        f"expected at least the three #1641 messages in jvm_session, harvested "
        f"{len(messages)}: {messages}"
    )

    unmatched = [m for m in messages if not re.search(pattern, _as_junit_skip(m))]
    assert not unmatched, (
        "these jvm_session skip messages are INVISIBLE to the CI storm guard, so a "
        f"storm made of them would print '0 / N (0%) ✅ OK' (#1873):\n  "
        + "\n  ".join(unmatched)
        + f"\nguard pattern: {pattern}"
    )


def test_every_jvm_skip_message_in_the_suite_is_counted():
    """The contract is about the *cause*, not about one file.

    Measured on the 206 `pytest.skip` literals under `tests/`: main's guard
    (`$jvmSignature = "JVM n'est pas réellement démarrée"`, injected through
    `[regex]::Escape`) matches exactly **one** of them. The current pattern
    matches 35, of which 32 sit outside conftest.

    Those 32 are preempted by the autouse `jvm_session` fixture today, so they
    are invisible -- until anything bypasses it (`--disable-jvm-session`,
    `is_e2e_session`), at which point a real storm counts zero.
    """
    pattern = _guard_pattern()
    harvested, unmatched = 0, []
    unparseable = []
    for path in (ROOT / "tests").rglob("*.py"):
        try:
            messages = _skip_literals(path)
        except SyntaxError as exc:  # named, never swallowed: see below
            unparseable.append(f"{path.relative_to(ROOT)}: {exc}")
            continue
        for message in messages:
            if "JVM" not in message.upper():
                continue
            harvested += 1
            if not re.search(pattern, _as_junit_skip(message)):
                unmatched.append(f"{path.relative_to(ROOT)}: {message!r}")

    # A file this harvest cannot read is a file whose JVM skips it cannot check.
    # Reporting the shortfall keeps the zero honest rather than comfortable.
    assert not unparseable, (
        f"{len(unparseable)} test file(s) could not be parsed, so their skip "
        "messages were never checked against the guard:\n  " + "\n  ".join(unparseable)
    )
    assert harvested >= 8, (
        f"harvest found only {harvested} JVM skip literals under tests/ — the "
        "instrument is not reaching the files it is supposed to read"
    )
    assert not unmatched, (
        f"{len(unmatched)} JVM-caused skip message(s) the CI guard cannot see:\n  "
        + "\n  ".join(unmatched)
        + f"\nguard pattern: {pattern}"
    )


@pytest.mark.parametrize(
    "message",
    [
        "needs USE_REAL_JPYPE=true (real Tweety, skipped in CI)",
        "set USE_REAL_JPYPE=true to exercise real Tweety parsing",
        "Orphan model without a provider (B-06 #810)",
        "optional dependency missing",
    ],
)
def test_legitimate_skips_stay_out_of_the_numerator(message):
    """Anti-pendulum, and it is the half that matters.

    Widening a storm guard is one edit away from becoming a raw skip-rate check,
    which reddens on the 244 legitimate skips a healthy run produces (measured on
    run 32744198742: 208 orphan-model + 27 USE_REAL_JPYPE + 9 optional deps).
    A guard that cries wolf on a healthy run gets disabled, and then the storm
    goes unseen again.
    """
    assert not re.search(_guard_pattern(), _as_junit_skip(message))


def test_a_failure_mentioning_the_jvm_is_not_a_skip():
    """The pattern is anchored on `<skipped …>`, which main's comment claims
    ("scoped to skip messages") without doing: main anchors on `message="`
    alone, so `<failure message="… JVM …">` counts too, inflating the numerator
    with tests that actually ran and failed."""
    failure = '<failure message="AssertionError: JVM classpath empty">trace</failure>'
    assert not re.search(_guard_pattern(), failure)
