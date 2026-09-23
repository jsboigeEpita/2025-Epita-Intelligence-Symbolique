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

Privacy HARD: these ARE real names — of the CLASS vocabulary only (public
figures, states, parties: political-historical forms already present in
the indexed repo before this module existed). Only their hit counts may
be written to committed artifacts, never matched context.

Class vs instance (#2168): this module must never carry a DOCUMENT
IDENTIFIER — a ``source_name`` or any label mapping 1:1 to one encrypted
document of our corpus. "It's a detector" is not a license: a detector
enumerating corpus identifiers publishes the census the encryption
protects. Detect instances by deriving tokens at runtime from the
in-memory decrypted definitions, never by listing them here.

Surface partition (#2349) — written here ONCE, because this module is what
every instrument consumes. Two surfaces, two instruments, and neither
substitutes for the other:

* the FLUX — what a push makes permanent. ``scripts/security/scan_indexed_surfaces.py``
  scans commit messages (``--commits origin/main..HEAD``, also a CI gate) and
  any text body (``--text-file``) before it is posted. A commit message is
  forever: the repo is public and forked, so history rewriting does not remove
  it from the forks.
* the ARBRE — what the tree already carries, at rest, in tracked files. Two
  sweeps cover it, and their roots tile without overlap:
  ``tests/unit/argumentation_analysis/evaluation/test_person_sweep_2004.py``
  sweeps ``tests/``; ``test_production_person_sweep_2349.py`` sweeps every
  tracked ``.py`` OUTSIDE ``tests/``. Before #2349 the second root was covered
  by nobody: a name could sit in ``argumentation_analysis/``, ``scripts/`` or
  ``project_core/`` indefinitely, while both instruments reported clean.

Both sweeps exclude nominatively — a file, an issue owning its triage, a
reason — never a directory. A directory-wide exclusion is how a carpet forms.
"""

import re


def letter_boundary(core: str) -> str:
    """Wrap a bare core in the #2012 letter frontier.

    ``(?<![A-Za-z]){core}(?![A-Za-z])`` — fires on prose and on identifiers
    alike: the frontier is drawn on letters, not on word characters, so the
    underscore of ``core_only`` no longer shields a smuggled name.
    """
    return rf"(?<![A-Za-z]){core}(?![A-Za-z])"


# --- Class vocabulary: entries are never elided toward the corpus (#2202) ---
#
# These lists are CLASS vocabulary and their entries are added for class
# reasons. They are NEVER removed on the grounds that the corpus does not
# contain them. Eliding them toward the census is the operation that turns them
# INTO a census: the survivors would be exactly the entries the corpus holds,
# and no line of that diff would look like a leak. What makes these lists safe
# is not their content but their not having been pruned — which is why the
# margin below is measured and recorded rather than curated.
#
# Margin, measured 2026-09-13 by matching every pattern against the tokens
# derived at runtime from the encrypted corpus: LEADER_PATTERNS 17 of 19
# absent, STATE_PATTERNS 12 of 12 absent. This is #2187's mirror image: there,
# the moved token was an INSTITUTION whose presence in a detector was itself
# the signal; here a reader cannot tell which entries the corpus holds.
# RE-MEASURE BEFORE QUOTING — the figure moves with every corpus revision.
#
# 2026-09-23, option 4 (user arbitration Q-R1042-A, #2362 class A): 9
# additions — 5 heads of state and 4 spelling variants — ruled PUBLIC CLASS
# VOCABULARY by the user. Margin measured the same day: the additions are
# 9 of 9 absent from the runtime-derived corpus tokens (zero corpus margin);
# the merged list measures 26 of 28 absent.
#
# leaders / heads of state — the 28 person patterns the tests/ sweep uses
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
    r"Zelenskyy",
    r"Melenchon",
    r"Pétain",
    r"Petain",
    r"Bachelet",
    r"Milei",
    r"Bolsonaro",
    r"Orbán",
    r"Orban",
]

# states / regions — same invariant as above: never elided toward the census
# on the grounds of absence (#2202; margin and re-measure clause above).
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

# The person patterns: the subset used to sweep tests/ for fixtures
# carrying real leader identities (#1999/#2004).
PERSON_PATTERNS = LEADER_PATTERNS

# The person-only detector. The cassette privacy audit consumes this
# (#2362 class A, option 4): one vocabulary, one boundary (#2012), one
# casing rule — instead of a hand-copied list that could drift from the
# class vocabulary in silence.
PERSON_RE = re.compile(
    "|".join(letter_boundary(p) for p in PERSON_PATTERNS), re.IGNORECASE
)

LEAK_RE = re.compile("|".join(letter_boundary(p) for p in LEAK_PATTERNS), re.IGNORECASE)
