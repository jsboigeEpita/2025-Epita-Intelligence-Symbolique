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
"""

import re
from pathlib import Path

from argumentation_analysis.evaluation.leak_patterns import PERSON_PATTERNS

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent

# Canaries whose job is to carry a real name (privacy tests / cassettes).
PRIVACY_CANARY_SUFFIXES = ("_privacy.py", "_cassette_privacy.py")

# Behavior-keyed canaries — production code under test branches on the name:
# extract-repair name-keyed filter, AnonymizeFilter [LEADER] substitution,
# generator corpus-selection branch, corpus grouping keys (verdicts #1999),
# and the CLI contract: --hitler-only is a real flag of
# argumentation_analysis/core/utils/cli_utils.py (verdict #2004).
NAME_KEYED_CANARIES = {
    "tests/argumentation_analysis/utils/dev_tools/test_repair_utils.py",
    "tests/unit/argumentation_analysis/core/test_source_management_extended.py",
    "tests/unit/argumentation_analysis/utils/test_data_generation.py",
    "tests/unit/argumentation_analysis/utils/test_data_processing_utils.py",
    "tests/unit/argumentation_analysis/utils/core_utils/test_cli_utils.py",
}

# Serialized on #1998 (its PR rewrites this file): re-verify once it lands;
# remove from this set only if the real name is gone by then.
SERIALIZED_CANARIES = {
    "tests/unit/argumentation_analysis/evaluation/test_opaque_id.py",
}

# This guard itself: documenting the canary verdicts requires spelling the
# production flag name (which embeds a leader pattern) in the comment above.
# Declared self-exclusion, not a silent one — the né-rouge control proves
# the sweep still catches real fixtures.
GUARD_SELF = {
    "tests/unit/argumentation_analysis/evaluation/test_person_sweep_2004.py",
}


def test_person_sweep_tests_tree():
    regexes = [re.compile(p, re.IGNORECASE) for p in PERSON_PATTERNS]
    leaks = {}
    for path in sorted(REPO_ROOT.joinpath("tests").rglob("*.py")):
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel.endswith(PRIVACY_CANARY_SUFFIXES):
            continue
        if (
            rel in NAME_KEYED_CANARIES
            or rel in SERIALIZED_CANARIES
            or rel in GUARD_SELF
        ):
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
