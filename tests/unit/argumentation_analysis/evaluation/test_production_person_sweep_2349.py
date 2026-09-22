"""#2349 — the class vocabulary is swept over the PRODUCTION tree, not just tests/.

The gap this closes: two instruments existed and neither covered
``argumentation_analysis/``, ``scripts/`` or ``project_core/``.
``scripts/security/scan_indexed_surfaces.py`` scans the FLUX (commit messages,
text bodies); ``test_person_sweep_2004.py`` sweeps the ``tests/`` root of the
ARBRE. A name could therefore sit in production code indefinitely while both
instruments reported clean. The surface partition is written once in
``argumentation_analysis/evaluation/leak_patterns.py`` (the module both
instruments consume) — read it there, not here.

This module sweeps every tracked ``.py`` OUTSIDE ``tests/``: the two roots tile
the tree without overlap. It excludes **nominatively** — a path, the issue that
owns its triage, a written reason — never a directory. A directory-wide
exclusion is how a carpet forms.

Exclusion sets are the #1842 ``PENDING_TRIAGE`` idiom:

* ``DECLARED`` — a legitimate carrier, justified in a line of prose.
* ``PENDING_TRIAGE`` — a measured violation, owned by #2362. The set shrinks as
  that issue lands and never grows to absorb new silence: a new bearer reddens,
  and so does an entry that no longer carries a pattern (stale entry, its
  repair landed without removing the line).

Privacy HARD (rule 7, #2168): failure output reports paths and PATTERN INDEXES
only, never matched context — and no leader spelling may live in this file, or
the sweep this module adds would flag it.
"""

import re
import subprocess
from pathlib import Path

from argumentation_analysis.evaluation.leak_patterns import (
    PERSON_PATTERNS,
    letter_boundary,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent

# --- Declared carriers: legitimate, each justified in one line -------------
DECLARED = {
    "argumentation_analysis/evaluation/leak_patterns.py": (
        "the single source of the class vocabulary itself; its docstring "
        "forbids eliding entries toward the corpus, because the survivors "
        "would BE the census"
    ),
    "scripts/cassettes/privacy.py": (
        "SOURCE_NAME_HINTS — a declared canary detector, dated 2026-08-06 "
        "(#1603 R758) and self-documented as intentionally narrow"
    ),
    "argumentation_analysis/core/utils/cli_utils.py": (
        "DEPRECATED_ORATOR_ALIAS — a declared deprecated CLI spelling, i.e. a "
        "contract, not a detector (tension noted on #2362, not re-litigated)"
    ),
}

# --- Measured violations, owned by #2362 ----------------------------------
# class B1 (redactor by enumeration) and class C (incidental carrier) landed:
# the redactors derive their person alternation from PERSON_PATTERNS (#2348
# pattern) and the incidental carriers went opaque — their entries left the
# ledger as their repairs landed. What remains is class B2.
# class B2: behaviour keyed on ONE instance (branch / flag / label)
PENDING_TRIAGE = {
    "argumentation_analysis/utils/dev_tools/repair_utils.py": "#2362 B2",
    "argumentation_analysis/utils/dev_tools/verification_utils.py": "#2362 B2",
    "argumentation_analysis/utils/run_verify_extracts.py": "#2362 B2",
    "argumentation_analysis/scripts/run_verify_extracts_llm.py": "#2362 B2",
    "argumentation_analysis/utils/run_verify_extracts_with_llm.py": "#2362 B2",
    "argumentation_analysis/utils/data_generation.py": "#2362 B2",
    "argumentation_analysis/utils/data_processing_utils.py": "#2362 B2",
    "argumentation_analysis/pipelines/reporting_pipeline.py": "#2362 B2",
    "scripts/orchestration/run_extract_repair.py": "#2362 B2",
    "scripts/orchestration/run_verify_extracts.py": "#2362 B2",
    "scripts/reporting/generate_rhetorical_analysis_summaries.py": "#2362 B2",
    "scripts/reporting/generate_comprehensive_report.py": "#2362 B2",
}

# The only path #2348 changed, used by the historical control below.
_NET_2348_PATH = "argumentation_analysis/core/source_management.py"
_BEFORE_2348 = "888086575"
_AFTER_2348 = "076b5a34"


def _regexes():
    return [re.compile(letter_boundary(p), re.IGNORECASE) for p in PERSON_PATTERNS]


def _bearers_in_text(text: str, regexes) -> list:
    return [i for i, rx in enumerate(regexes) if rx.search(text)]


def _production_tree() -> list:
    """Tracked ``.py`` outside ``tests/`` — the ARBRE root this module owns.

    ``git ls-files`` (tracked only): the subject is the codebase at rest, and
    an untracked file is not yet a leak surface. A failure here is loud, never
    a skip — an instrument that cannot enumerate its surface has measured
    nothing, and a silent skip would read as clean.
    """
    proc = subprocess.run(
        ["git", "ls-files", "*.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, (
        "the sweep cannot enumerate the tracked tree, so it has measured "
        f"nothing: git ls-files exited {proc.returncode} ({proc.stderr.strip()})"
    )
    paths = [p for p in proc.stdout.split() if not p.startswith("tests/")]
    assert paths, "git ls-files returned no production .py — the surface is empty"
    return paths


def _scan():
    regexes = _regexes()
    bearers = {}
    scanned = 0
    for rel in _production_tree():
        path = REPO_ROOT / rel
        if not path.exists():
            continue
        scanned += 1
        hits = _bearers_in_text(
            path.read_text(encoding="utf-8", errors="replace"), regexes
        )
        if hits:
            bearers[rel] = hits
    return scanned, bearers


def test_no_unregistered_bearer_outside_tests():
    """Born-red on today's tree: 21 bearers, of which 18 are unowned violations."""
    scanned, bearers = _scan()
    assert scanned > 1000, f"only {scanned} production files read — surface too small"

    unregistered = {
        rel: idx
        for rel, idx in bearers.items()
        if rel not in DECLARED and rel not in PENDING_TRIAGE
    }
    assert not unregistered, (
        "production .py matching leader patterns with no written verdict "
        f"(pattern indexes among the {len(PERSON_PATTERNS)} PERSON_PATTERNS): "
        + "; ".join(
            f"{rel} (patterns {idx})" for rel, idx in sorted(unregistered.items())
        )
        + " — each new site needs a written verdict (declared carrier / "
        "measured violation + owning issue) before it may join an exclusion "
        "set, and the class vocabulary itself is never pruned to make one go "
        "away (#2168, #2349)"
    )


def test_ledger_entries_still_carry_a_pattern():
    """Inverse control: the ledger shrinks, it does not survive its own repair.

    An entry listed as a violation but no longer matching means the repair
    landed without removing the line — a stale entry that would silently
    absorb the next occurrence of the same path.
    """
    regexes = _regexes()
    stale = []
    for rel in sorted(set(DECLARED) | set(PENDING_TRIAGE)):
        path = REPO_ROOT / rel
        if not path.exists():
            stale.append(f"{rel} (missing)")
            continue
        if not _bearers_in_text(
            path.read_text(encoding="utf-8", errors="replace"), regexes
        ):
            stale.append(f"{rel} (no longer matches)")
    assert not stale, (
        "ledger entries that no longer carry a pattern: "
        + "; ".join(stale)
        + " — remove them as their repair lands; the ledger shrinks and never "
        "grows to absorb new silence (#1842, #2349)"
    )


def test_enumeration_shape_is_caught():
    """The instrument must prove it can render non-zero (anti-theater #1019).

    A zero only measures if the instrument is known to render non-zero. The
    carrier is derived at runtime from ``PERSON_PATTERNS`` — no leader spelling
    is written here — in the shape #2362 B1 measured: a hardcoded alternation
    used as a redactor.
    """
    cores = [p for p in PERSON_PATTERNS if p.isascii() and p.isalpha()][:2]
    assert len(cores) == 2, "need two runtime-derived cores for the synthetic carrier"
    carrier = (
        "SENSITIVE = [" + ", ".join(f'"{c}"' for c in cores) + "]\n"
        "def scrub(msg):\n"
        "    for c in SENSITIVE:\n"
        '        msg = msg.replace(c, "[LEADER]")\n'
        "    return msg\n"
    )

    hits = _bearers_in_text(carrier, _regexes())

    assert len(hits) >= 2, (
        "the sweep failed to flag a synthetic enumerated redactor built from "
        f"the class vocabulary — it read {len(hits)} pattern(s); a clean report "
        "from an instrument that cannot render non-zero proves nothing"
    )


def test_historical_control_the_2348_census_was_visible():
    """The deciding measurement, replayed: red before #2348, green after.

    #2348 replaced an enumerated census in ``source_management.py`` with
    class-based redaction. That file is the discriminating case because it is
    the ONLY path #2348 changed: at ``888086575`` (before) it carried 6
    patterns; at ``076b5a34`` (after) it carries none. A sweep that cannot see
    that difference is not an instrument, it is a report.

    History is required. Under a shallow checkout the control cannot run, and
    it says so loudly — a silent skip would be indistinguishable from a pass.
    """
    regexes = _regexes()
    measured = {}
    for rev in (_BEFORE_2348, _AFTER_2348):
        proc = subprocess.run(
            ["git", "show", f"{rev}:{_NET_2348_PATH}"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise AssertionError(
                f"git show {rev}:{_NET_2348_PATH} failed (rc={proc.returncode}) — "
                "the historical control NEEDS history; a shallow clone makes "
                "this control unmeasurable, and it must not pass silently "
                f"({proc.stderr.strip().splitlines()[:1]})"
            )
        measured[rev] = _bearers_in_text(proc.stdout, regexes)

    assert measured[_BEFORE_2348], (
        "the enumerated census before #2348 was NOT detected — the sweep is "
        "blind to the exact shape it was widened to catch"
    )
    assert not measured[_AFTER_2348], (
        "the class-based redaction after #2348 still reports a pattern "
        f"({measured[_AFTER_2348]}) — either #2348 regressed or the sweep "
        "over-reports"
    )
