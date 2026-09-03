"""Local fail-loud signal for JVM-signature skip storms (#2021).

The CI workflow carries a fail-loud guard against JVM-startup skip storms
(``.github/workflows/ci.yml``, #1385 hardened by #1873) — but it only runs
in CI. The cluster's verification discipline (born-red before a fix, suite
runs before a report) executes LOCALLY, where the same storm renders as a
small, plausible ``7 skipped ... in 0.67s`` and exit code 0. Three agents
hit that shape independently in one round (issue #2021); at least one was a
born-red that "passed" without executing anything.

This module is the local twin of that guard, wired from ``tests/conftest.py``
(``pytest_runtest_logreport`` feeds it, ``pytest_sessionfinish`` consults
it). Because it is a pytest hook it also runs in CI, so ONE definition
serves both environments. The CI pwsh guard stays untouched (its file is a
user-decision surface); ``tests/unit/test_local_skip_storm_signal_2021.py``
ties the two definitions together on the real population of skip literals,
the same way ``test_ci_guard_signature_contract_1873.py`` ties the CI guard
to the suite — so neither can drift from the other silently.

Same shape as the CI guard, on purpose:

- the numerator counts skips whose REASON carries the JVM token (any case),
  never the raw skip rate — the legitimate buckets (opt-in USE_REAL_JPYPE,
  orphan-model, optional-dependency, requires_api) stay out, because a guard
  that cries wolf on a healthy run gets disabled (#1873 anti-pendulum);
- the threshold is the same strictly-greater-than 50% of collected tests;
- a session that collected nothing is not a success either (#1556);
- the three #1641 conftest signatures are ventilated, because the remedy
  for a decided failure and for a transient one are OPPOSITE.

Anti-pendulum (#2021): this signal never makes the conftest fail instead of
skip when the JVM is unavailable. A legitimately JVM-less environment must
still be able to run the non-JVM suite — sessions running with
``--disable-jvm-session`` or classified E2E are exempt by design (JVM-less
is a choice there, not a lost measurement). The defect being closed is that
a vacuous run is SILENT, not that it skips.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Pattern, Tuple

# The JVM token in any case — the family the CI guard matches with
# ``$jvmPattern = '<skipped[^>]*message="[^"]*[Jj][Vv][Mm]'``. Applied here
# to the skip REASON (pre-junit-escape form), not to the XML: same
# membership over real literals, without a second escaping hazard.
JVM_REASON_RE: Pattern[str] = re.compile(r"[Jj][Vv][Mm]")

# Same threshold as the CI guard (``-gt 0.5``: exactly 50% does NOT shout).
STORM_THRESHOLD = 0.5

# The three #1641 conftest signatures — the same ventilation family the CI
# guard reports, for the same reason: a decided failure (fix the config)
# and a transient one (re-run) have opposite remedies.
VENTILATION_PATTERNS: Tuple[Tuple[str, Pattern[str]], ...] = (
    (
        "decided init failure (pytest_sessionstart)",
        re.compile(r"Saut du test car l.initialisation de la JVM"),
    ),
    (
        "JVM not actually started (isJVMStarted() = False)",
        re.compile(r"Saut du test car la JVM n.est pas"),
    ),
    (
        "JVM started but unhealthy (JClass health check)",
        re.compile(r"Saut du test car la JVM est d"),
    ),
)


def skip_reason(report) -> Optional[str]:
    """The reason string of a skipped report, or ``None``.

    A skip raised from a fixture or a test body lands in
    ``report.longrepr`` as ``(path, lineno, "Skipped: <reason>")``. Only the
    third component is returned, so a FILE NAME containing the token
    (``test_jvm_classpath_1874.py``) can never count as a signature — the
    local twin of the CI guard's ``<skipped ... message="`` anchoring,
    which exists so that ``<failure message="... JVM ...">`` does not count.
    """
    if getattr(report, "outcome", None) != "skipped":
        return None
    longrepr = report.longrepr
    if isinstance(longrepr, tuple) and len(longrepr) >= 3:
        info = str(longrepr[2])
    else:
        info = str(longrepr)
    marker = "Skipped: "
    return info[len(marker) :] if info.startswith(marker) else info


class SkipStormCounter:
    """Accumulates one skip reason per nodeid across logreport calls.

    Keyed by nodeid (a skipped setup leaves no call report to double count)
    and resettable, so a hypothetical second session in one process cannot
    inherit the first one's reasons.
    """

    def __init__(self) -> None:
        self._reasons: Dict[str, str] = {}

    def add(self, report) -> None:
        reason = skip_reason(report)
        if reason is not None and report.nodeid not in self._reasons:
            self._reasons[report.nodeid] = reason

    @property
    def total_skips(self) -> int:
        return len(self._reasons)

    def jvm_signature_reasons(self) -> List[str]:
        return [r for r in self._reasons.values() if JVM_REASON_RE.search(r)]

    def reset(self) -> None:
        self._reasons.clear()


# Module-level singleton: conftest feeds it, pytest_sessionfinish reads it.
COUNTER = SkipStormCounter()


def storm_verdict(collected_total: int, jvm_skips: int) -> Tuple[bool, str]:
    """``(should_shout, one-line diagnosis)`` — the CI guard's two failures.

    Both are fail-loud on purpose: an exit-0 session that measured nothing
    is the mask, whatever its shape (empty collection #1556, wholesale JVM
    skip storm #1385).
    """
    if collected_total <= 0:
        return True, (
            f"FAIL-LOUD (#2021): {collected_total} test(s) collected — the session "
            "measured nothing. Exit 0 on an empty collection is the #1556 hole."
        )
    share = jvm_skips / collected_total
    if share > STORM_THRESHOLD:
        return True, (
            f"FAIL-LOUD (#2021): {jvm_skips} of {collected_total} collected tests "
            f"({round(100 * share)}%) were skipped with a JVM signature — the run "
            "decided nothing. A born-red or a suite report built on this session "
            "is vacuous; do not merge on it."
        )
    return False, (
        f"skip-storm signal (#2021): {jvm_skips} / {collected_total} "
        f"JVM-signature skips ({round(100 * share)}%) — under threshold."
    )


def ventilate(jvm_reasons: List[str]) -> str:
    """Name the dominant cause, exactly like the CI guard's ventilation.

    Telling a decided failure (fix the config, re-running burns CI minutes)
    from a transient one (re-run) is the whole point — #1873.
    """
    lines = []
    counted = 0
    for label, pattern in VENTILATION_PATTERNS:
        n = sum(1 for r in jvm_reasons if pattern.search(r))
        if n:
            lines.append(f"  - {n} x {label}")
            counted += n
    if jvm_reasons and counted < len(jvm_reasons):
        lines.append(
            f"  - {len(jvm_reasons) - counted} x JVM token outside the three "
            "conftest signatures (read the run log before re-running anything)"
        )
    return "\n".join(lines)
