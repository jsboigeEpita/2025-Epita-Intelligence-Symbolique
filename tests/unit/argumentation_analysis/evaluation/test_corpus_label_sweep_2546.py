"""#2546: no tracked file carries a corpus label.

CLAUDE.md privacy rule 7: a label that maps 1:1 to one encrypted document
stays out of every tracked file. ``test_production_person_sweep_2349.py``
sweeps by CLASS (public vocabulary). This module sweeps by INSTANCE: it
decrypts the dataset definitions in memory, takes every source and extract
label, and looks for each one in every tracked text file. The labels exist
only in this process; nothing here writes or prints them.

#2546 measured three carriers this way on ``main`` ``41ebd4aee``: a
diagnostic branch in ``ui/verification_utils.py`` keyed on one extract's
title, the benchmark skill's index-to-name table, and a student subject that
uses a public institution's name as an example. The first two are repaired;
the third is DECLARED below.

Failure output names paths and counts, never a label.
"""

import os
import subprocess
from pathlib import Path

import pytest

# It decrypts the dataset with the real ambient passphrase: the keyless
# pass of #2411 leaves it out (#2565).
pytestmark = pytest.mark.requires_dataset_passphrase

REPO_ROOT = Path(__file__).resolve().parents[4]
DATASET = REPO_ROOT / "argumentation_analysis" / "data" / "extract_sources.json.gz.enc"

# Shorter labels collide with ordinary words.
MIN_LABEL_LEN = 8


class _Labels(frozenset):
    """The decrypted labels. Its repr is a count, so neither an assertion
    rewrite nor ``--showlocals`` can print a label into a public CI log."""

    def __repr__(self):
        return f"<{len(self)} corpus labels>"


# A legitimate carrier, justified in one line. The set never grows to absorb a
# new carrier, and an entry that stops carrying a label reddens (stale entry).
DECLARED = {
    "docs/projets/sujets/DEMOCRATECH_UNIFIED_ANALYSIS.md": (
        "a public institution's name used as an application example in a "
        "student subject; nothing pairs it with the corpus (#2546 item 3)"
    ),
}


@pytest.fixture(scope="module")
def labels():
    passphrase = os.environ.get("TEXT_CONFIG_PASSPHRASE")
    if not passphrase:
        if os.environ.get("CI"):
            pytest.fail(
                "the CI test step provides TEXT_CONFIG_PASSPHRASE; without it "
                "this sweep cannot decrypt the labels it looks for"
            )
        pytest.skip("needs TEXT_CONFIG_PASSPHRASE to decrypt the labels in memory")

    from argumentation_analysis.core.io_manager import load_extract_definitions
    from argumentation_analysis.core.utils.crypto_utils import derive_encryption_key

    key = derive_encryption_key(passphrase)
    definitions = load_extract_definitions(
        DATASET, b64_derived_key=key.decode("utf-8"), raise_on_decrypt_error=True
    )
    found = set()
    for source in definitions:
        found.add(source.get("source_name") or "")
        for extract in source.get("extracts", []):
            found.add(extract.get("extract_name") or "")
    found = _Labels(label for label in found if len(label) > MIN_LABEL_LEN)
    count = len(found)
    # Non-vacuity: #2546 counted 58 labels (20 source, 38 extract).
    assert count >= 50, "too few labels decrypted to sweep with"
    return found


@pytest.fixture(scope="module")
def carriers(labels):
    tracked = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    # Search bytes, not decoded text: a file that does not decode as UTF-8
    # (a cp1252 script, a PDF) is swept too instead of skipped in silence.
    needles = []
    for label in labels:
        forms = {label.encode("utf-8")}
        try:
            forms.add(label.encode("cp1252"))
        except UnicodeEncodeError:
            pass
        needles.append(forms)
    hits = {}
    for path in tracked:
        if not (REPO_ROOT / path).is_file():
            continue  # a submodule entry: its files are not ours to sweep
        data = (REPO_ROOT / path).read_bytes()
        count = sum(1 for forms in needles if any(f in data for f in forms))
        if count:
            hits[path] = count
    return hits


def test_no_tracked_file_carries_a_corpus_label(carriers):
    undeclared = {path: n for path, n in carriers.items() if path not in DECLARED}

    assert undeclared == {}, "path -> number of corpus labels it carries"


def test_every_declared_carrier_still_carries_one(carriers):
    stale = sorted(path for path in DECLARED if path not in carriers)

    assert stale == [], "no longer a carrier: remove the DECLARED entry"
