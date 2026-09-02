"""Privacy leak indicators — shared detector vocabulary (#2004, follow-up of #1999).

Single import-effect-free source of truth for the leak-detection patterns.
The runtime verifier ``scripts/run_fb34_opaqueness_check.py`` consumes
``LEAK_PATTERNS``/``LEAK_RE`` for its synthesis-prose grep; the tests/
person-name sweep guard consumes ``PERSON_PATTERNS`` for its static scan.

This module MUST stay import-effect-free: no environment access, no
filesystem, no logging, no third-party imports. Keep it stdlib-only.

Privacy HARD: these ARE the real names — that is the point of a detector.
Only their hit counts may be written to committed artifacts, never matched
context. The patterns themselves already live in the indexed repo (they
were extracted verbatim from scripts/run_fb34_opaqueness_check.py).
"""

import re

# leaders / heads of state — the 19 person patterns the tests/ sweep uses
LEADER_PATTERNS = [
    r"\bPutin\b",
    r"\bPoutine\b",
    r"\bStalin\b",
    r"\bStaline\b",
    r"\bLenin\b",
    r"\bLénine\b",
    r"\bHitler\b",
    r"\bMussolini\b",
    r"\bMacron\b",
    r"\bSarkozy\b",
    r"\bMitterrand\b",
    r"\bLe Pen\b",
    r"\bKhrushchev\b",
    r"\bKhrouchtchev\b",
    r"\bTrump\b",
    r"\bBiden\b",
    r"\bMélenchon\b",
    r"\bZelensky\b",
    r"\bZelenskiy\b",
]

# states / regions
STATE_PATTERNS = [
    r"\bUkraine\b",
    r"\bUkrainien(?:ne)?s?\b",
    r"\bRussie\b",
    r"\bRussian\b",
    r"\bFrance\b",
    r"\bFrench\b",
    r"\bAllemagne\b",
    r"\bGermany\b",
    r"\bCrimée\b",
    r"\bCrimea\b",
    r"\bDonbass\b",
    r"\bDonetsk\b",
]

# parties / ideologies (proper-noun forms)
PARTY_PATTERNS = [
    r"\bBolshevik\b",
    r"\bBolchevik(?:s)?\b",
    r"\bNazi(?:s)?\b",
    r"\bCommunist(?:e)?(?:s)?\b",
    r"\bSoviétique(?:s)?\b",
    r"\bSoviet\b",
]

# specific events/dates that betray identity
EVENT_PATTERNS = [
    r"\b1917\b",
    r"\bBrest-Litovsk\b",
]

# Full detector list, order preserved from the original script (alternation
# order affects which first match finditer reports).
LEAK_PATTERNS = LEADER_PATTERNS + STATE_PATTERNS + PARTY_PATTERNS + EVENT_PATTERNS

# The 19 person patterns: the subset used to sweep tests/ for fixtures
# carrying real leader identities (#1999/#2004).
PERSON_PATTERNS = LEADER_PATTERNS

LEAK_RE = re.compile("|".join(LEAK_PATTERNS), re.IGNORECASE)
