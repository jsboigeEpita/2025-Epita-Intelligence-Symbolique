"""#2476 — a class name followed by a derivational suffix is still a name.

The #2012 letter frontier closed on the first letter after the core, so a
derived form (the adjective or the movement a name forms) escaped every
detector built on ``letter_boundary``: ``LEAK_RE``, ``PERSON_RE``, the two
sweeps and the commit-message gate. Measured on ``main``: 0 of 80 English
capitalised carriers, where the old cassette audit caught 80.

No leader spelling is written here (the tests/ sweep would flag it): every
carrier is built at run time from ``PERSON_PATTERNS``. The suffixes below are
the requirement, spelled independently of the module's own list.
"""

import importlib.util
import re
from pathlib import Path

from argumentation_analysis.evaluation.leak_patterns import (
    LEAK_RE,
    PERSON_PATTERNS,
    PERSON_RE,
    letter_boundary,
)

REPO_ROOT = Path(__file__).resolve().parents[4]

SUFFIXES = ("ist", "ism", "ian", "ite", "iste", "isme", "ien", "ienne", "ists", "ismes")
OFF_LIST = ("et", "ed", "ing", "er", "ly", "ish")

CORES = [p for p in PERSON_PATTERNS if p.isalpha()]


def _swept(text: str) -> bool:
    """The sweeps' construction: one letter-bounded regex per pattern."""
    return any(
        re.search(letter_boundary(p), text, re.IGNORECASE) for p in PERSON_PATTERNS
    )


def _scanner():
    path = REPO_ROOT / "scripts" / "security" / "scan_indexed_surfaces.py"
    spec = importlib.util.spec_from_file_location("_scan_2476", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_core_is_caught_with_each_suffix():
    assert len(CORES) >= 20, "carrier population collapsed"
    scanner = _scanner()
    missed = []
    for i, core in enumerate(CORES):
        for suffix in SUFFIXES:
            for form in (f"{core}{suffix}", f"{core}{suffix}".lower()):
                carrier = f"the {form} regime, as they call it"
                caught = (
                    PERSON_RE.search(carrier),
                    LEAK_RE.search(carrier),
                    _swept(carrier),
                    scanner.scan_text(carrier) > 0,
                )
                if not all(caught):
                    missed.append((i, suffix, [bool(c) for c in caught]))
    assert missed == [], f"{len(missed)} derived carriers escape: {missed[:6]}"


def test_a_core_ending_in_e_takes_the_suffix_on_its_stem():
    stems = [c for c in CORES if c.endswith("e")]
    assert stems, "no core ends in e: the premise of this test moved"
    missed = [
        i
        for i, core in enumerate(stems)
        for suffix in SUFFIXES
        if not PERSON_RE.search(f"le courant {core[:-1]}{suffix} du parti")
    ]
    assert missed == [], f"stem forms escape for cores {sorted(set(missed))}"


def test_a_letter_run_off_the_list_still_stops_the_match():
    # The frontier's reason to exist (#2012): a case-insensitive core must not
    # fire inside a common word that merely begins with it.
    fired = [
        (i, run)
        for i, core in enumerate(CORES)
        for run in OFF_LIST
        if PERSON_RE.search(f"a {core.lower()}{run} sound")
        or _swept(f"a {core}{run} sound")
    ]
    assert fired == [], f"off-list runs matched: {fired[:6]}"


def test_the_log_anonymizer_redacts_derived_and_identifier_forms(tmp_path):
    # The one production redactor that framed names with its own ``\b``:
    # blind to ``name_only`` (#2012) and to the derived form (#2476).
    from scripts.utils.cleanup_sensitive_traces import (
        SensitiveDataCleaner,
        _build_sensitive_patterns,
    )

    core = next(c for c in CORES if c.isascii())
    log = tmp_path / "run.log"
    log.write_text(
        f"a {core}ist view\nkey {core.lower()}_only=1\nthe {core}ism of it\n",
        encoding="utf-8",
    )
    SensitiveDataCleaner(dry_run=False)._anonymize_file(
        log, _build_sensitive_patterns()
    )
    scrubbed = log.read_text(encoding="utf-8")
    assert scrubbed.count("[LEADER]") == 3, "a derived or identifier form survived"
    assert core.lower() not in scrubbed.lower()
