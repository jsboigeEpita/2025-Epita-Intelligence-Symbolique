"""Privacy leak indicators — shared detector vocabulary (#2004, follow-up of #1999).

Single import-effect-free source of truth for the leak-detection patterns.
The runtime verifier ``scripts/run_fb34_opaqueness_check.py`` consumes
``LEAK_RE`` for its synthesis-prose grep; the tests/ person-name sweep guard
consumes ``PERSON_PATTERNS`` and ``letter_boundary`` for its static scan.

The patterns are stored BARE — no word boundary baked into the literals.
The boundary lives at one place: ``letter_boundary()``, a letter frontier
(``(?<![A-Za-z])...(?![A-Za-z])``). A word boundary is blind to the
identifier form: ``_`` is a word character, so ``core_only`` never matched
the old literals — the exact shape a leaked name takes when smuggled into
code as an identifier (#2012).

This module MUST stay import-effect-free: no environment access, no
filesystem, no logging, no third-party imports. Keep it stdlib-only.

Privacy HARD: these ARE the real names — that is the point of a detector.
Only their hit counts may be written to committed artifacts, never matched
context. The patterns themselves already live in the indexed repo (they
were extracted verbatim from scripts/run_fb34_opaqueness_check.py).
"""

import re


def letter_boundary(core: str) -> str:
    """Wrap a bare core in the #2012 letter frontier.

    ``(?<![A-Za-z]){core}(?![A-Za-z])`` — fires on prose and on identifiers
    alike: the frontier is drawn on letters, not on word characters, so the
    underscore of ``core_only`` no longer shields a smuggled name.
    """
    return rf"(?<![A-Za-z]){core}(?![A-Za-z])"


# leaders / heads of state — the 19 person patterns the tests/ sweep uses
LEADER_PATTERNS = [
    r"Putin",
    r"Poutine",
    r"Stalin",
    r"Staline",
    r"Lenin",
    r"Lénine",
    r"Hitler",
    r"Mussolini",
    r"Macron",
    r"Sarkozy",
    r"Mitterrand",
    r"Le Pen",
    r"Khrushchev",
    r"Khrouchtchev",
    r"Trump",
    r"Biden",
    r"Mélenchon",
    r"Zelensky",
    r"Zelenskiy",
]

# states / regions
STATE_PATTERNS = [
    r"Ukraine",
    r"Ukrainien(?:ne)?s?",
    r"Russie",
    r"Russian",
    r"France",
    r"French",
    r"Allemagne",
    r"Germany",
    r"Crimée",
    r"Crimea",
    r"Donbass",
    r"Donetsk",
]

# parties / ideologies (proper-noun forms)
PARTY_PATTERNS = [
    r"Bolshevik",
    r"Bolchevik(?:s)?",
    r"Nazi(?:s)?",
    r"Communist(?:e)?(?:s)?",
    r"Soviétique(?:s)?",
    r"Soviet",
]

# specific events/dates that betray identity
EVENT_PATTERNS = [
    r"1917",
    r"Brest-Litovsk",
]

# Full detector list, order preserved from the original script (alternation
# order affects which first match finditer reports).
LEAK_PATTERNS = LEADER_PATTERNS + STATE_PATTERNS + PARTY_PATTERNS + EVENT_PATTERNS

# The 19 person patterns: the subset used to sweep tests/ for fixtures
# carrying real leader identities (#1999/#2004).
PERSON_PATTERNS = LEADER_PATTERNS

LEAK_RE = re.compile("|".join(letter_boundary(p) for p in LEAK_PATTERNS), re.IGNORECASE)
