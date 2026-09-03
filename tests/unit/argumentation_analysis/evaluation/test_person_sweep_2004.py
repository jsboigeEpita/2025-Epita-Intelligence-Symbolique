"""tests/ person-name sweep guard (#2004, follow-up of #1999).

Sweeps tests/**/*.py with the 19 leader patterns of the repo's leak detector
(shared vocabulary: argumentation_analysis/evaluation/leak_patterns.py — the
import-effect-free single source; scripts/run_fb34_opaqueness_check.py
consumes the same list at runtime).

Invariant: every tests/ file matching a leader pattern must be a DECLARED
canary. Reddens on any non-canary match — the #1999 fixtures and the #2004
FOL constants both reddened it before their substitution (né-rouge control
run on pre-fix origin/main). Failure output reports file paths and pattern
indexes only, never the matched context.

Exclusion ledger:
- #2009 removed the CLI-contract exclusion: the production corpus-selector
  flag got an opaque spelling with the old one kept as a deprecated alias,
  and the argparse test now pins the alias through the imported production
  constant, so the spelling lives only in production code (never swept here).
- #2009 also removed the serialized exclusion on test_opaque_id.py: the name
  there was a substitutable non-ASCII carrier, substituted by a synthetic one.
- #2012 stripped the word boundaries from the shared literals: the guard now
  applies the module-level ``letter_boundary`` (letter frontier), which catches
  the identifier form (``<core>_only``) the word boundary was blind to. The
  control lives in ``test_letter_boundary_catches_identifier_carrier``.
"""

import re
from pathlib import Path

from argumentation_analysis.evaluation.leak_patterns import (
    PERSON_PATTERNS,
    letter_boundary,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent

# Canaries whose job is to carry a real name (privacy tests / cassettes).
PRIVACY_CANARY_SUFFIXES = ("_privacy.py", "_cassette_privacy.py")

# Behavior-keyed canaries — production code under test branches on the name:
# extract-repair name-keyed filter, AnonymizeFilter [LEADER] substitution,
# generator corpus-selection branch, corpus grouping keys (verdicts #1999).
NAME_KEYED_CANARIES = {
    "tests/argumentation_analysis/utils/dev_tools/test_repair_utils.py",
    "tests/unit/argumentation_analysis/core/test_source_management_extended.py",
    "tests/unit/argumentation_analysis/utils/test_data_generation.py",
    "tests/unit/argumentation_analysis/utils/test_data_processing_utils.py",
}


def test_person_sweep_tests_tree():
    regexes = [re.compile(letter_boundary(p), re.IGNORECASE) for p in PERSON_PATTERNS]
    leaks = {}
    for path in sorted(REPO_ROOT.joinpath("tests").rglob("*.py")):
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel.endswith(PRIVACY_CANARY_SUFFIXES):
            continue
        if rel in NAME_KEYED_CANARIES:
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        hits = [i for i, rx in enumerate(regexes) if rx.search(content)]
        if hits:
            leaks[rel] = hits
    assert not leaks, (
        "tests/ files matching leader patterns outside declared canaries "
        f"(pattern indexes among the {len(PERSON_PATTERNS)} PERSON_PATTERNS): "
        + "; ".join(f"{rel} (patterns {idx})" for rel, idx in leaks.items())
        + " — each new site needs a written verdict (canary / substitutable) "
        "per #1999/#2004 before it may join an exclusion set"
    )


def test_letter_boundary_catches_identifier_carrier():
    """#2012 born-red: the identifier form the word boundary never saw.

    A leaked name smuggled into code takes the shape ``<core>_only``. The
    old literals framed every pattern with a word boundary; ``_`` is a word
    character, so it never fired. The letter frontier does. The core is
    derived at runtime: no leader spelling may live in this file, or the
    sweep this module guards would flag it.
    """
    core = next(p for p in PERSON_PATTERNS if p.isascii() and p.isalpha())
    token = f"{core.lower()}_only"

    word_boundary = re.compile(rf"\b{core}\b", re.IGNORECASE)
    assert word_boundary.search(token) is None, "born-red premise broken"

    bounded = [re.compile(letter_boundary(p), re.IGNORECASE) for p in PERSON_PATTERNS]
    assert any(rx.search(token) for rx in bounded), "letter frontier must catch it"
