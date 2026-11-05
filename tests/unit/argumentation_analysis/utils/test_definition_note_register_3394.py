"""#3394 (R1142, reworked R1143) — the note states the register; upstream
cells are repaired only where truncated.

The R1142 head re-personed three upstream definitions (PK 501, 589, 1057)
to raise the « vous » count the writer receives. The coordinator's re-review
sent it back: an impersonal definition is correct in another register, and
the addressee the taxonomy speaks to is a fact for the ONE producer the
writer reads — ``taxonomy_definition_note`` — not an edit to upstream
content.

What stays from R1142: the two truncation repairs (PK 1253, 1265 — upstream
cells that lost their leading « V »), the same #2036 override discipline.

Offline: no JVM, no network, no LLM.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

from argumentation_analysis.core.fallacy_attribution import (
    taxonomy_definition_note,
)
from argumentation_analysis.utils.taxonomy_local_overrides import (
    REGISTER_FIXES,
    purge_row,
)
from argumentation_analysis.utils.taxonomy_loader import taxonomy_definition

_CSV = Path(__file__).resolve().parents[4] / (
    "argumentation_analysis/data/argumentum_fallacies_taxonomy.csv"
)
# The V-truncation class the census measures: a cell opening on « ous » is a
# « Vous » upstream cut off — anything subtler is not reliably measurable,
# and the census does not pretend to measure it.
_TRUNCATED = re.compile(r"^ous\b", re.IGNORECASE)
_SECOND_PERSON = re.compile(r"\b(vous|votre|vos)\b", re.IGNORECASE)
_ADDRESSEE = "la taxonomie s'adresse à qui commet le sophisme"


def _loaded_rows() -> list:
    # Parse integrity first: DictReader is lenient (an extra comma in
    # an unquoted cell shifts every column after it silently — the
    # pandas loaders raise where a lenient census kept reading green).
    with _CSV.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        rows_raw = list(reader)
    bad_rows = [i for i, r in enumerate(rows_raw, start=2) if len(r) != len(header)]
    assert bad_rows == [], bad_rows
    return [purge_row(dict(zip(header, r))) for r in rows_raw]


class TestNoLoadedCellIsTruncated:
    """The census measures the TRUNCATION class, not the register: on main
    (no load-time repair) the two « ous … » cells are visible offenders."""

    def test_every_loaded_desc_fr_cell_is_a_whole_sentence(self):
        rows = _loaded_rows()
        assert len(rows) == 1408
        offenders = [
            r["path"]
            for r in rows
            if _TRUNCATED.search((r.get("desc_fr") or "").strip())
        ]
        assert offenders == [], offenders

    def test_every_repair_targets_a_truncated_cell(self):
        # Dead-override guard, the #2036 discipline: a repair whose upstream
        # cell is whole is pointless; a repair that stays truncated is no
        # repair. Both redden here.
        with _CSV.open(encoding="utf-8-sig", newline="") as fh:
            raw = {
                r["PK"]: (r.get("desc_fr") or "").strip() for r in csv.DictReader(fh)
            }
        missing = {str(pk) for pk in REGISTER_FIXES} - set(raw)
        assert not missing, missing
        assert set(REGISTER_FIXES) == {1253, 1265}, sorted(REGISTER_FIXES)
        for pk, repaired in REGISTER_FIXES.items():
            assert _TRUNCATED.search(raw[str(pk)]), (pk, raw[str(pk)])
            assert not _TRUNCATED.search(repaired), (pk, repaired)

    def test_a_truncation_repair_resolves_end_to_end(self):
        # PK 1253 (Comportementalisme) had lost its leading « V » upstream.
        d = taxonomy_definition("comportementalisme", "6.3.3.1.3.2.2")
        assert d and d.startswith("Vous "), d


class TestTheNoteStatesTheRegister:
    """R1143 — the producer says who the taxonomy addresses; an impersonal
    definition keeps the bare form, an unresolvable label prints nothing."""

    def test_a_second_person_definition_names_its_addressee(self):
        note = taxonomy_definition_note(
            {"type": "comportementalisme", "taxonomy_path": "6.3.3.1.3.2.2"}
        )
        assert note.startswith(f"définition ({_ADDRESSEE}) : Vous "), note

    def test_an_impersonal_definition_keeps_the_bare_form(self):
        # PK 589 upstream (« Les bras croisés envoient… ») is third person —
        # correct in its own register, never rewritten, so its note carries
        # no addressee clause.
        note = taxonomy_definition_note(
            {"type": "Bras croisés", "taxonomy_path": "2.3.3.4.4.2"}
        )
        assert note == (
            "définition : Les bras croisés envoient un signal de fermeture "
            "ou de défense."
        ), note
        assert _ADDRESSEE not in note

    def test_an_unresolvable_label_still_prints_nothing(self):
        # Control from the R1142 suite: the lookup, not the register, gates
        # the note's existence.
        assert taxonomy_definition_note({"type": "sophisme inexistant de test"}) == ""

    def test_the_register_test_is_the_census_one(self):
        # The clause fires on the same \b(vous|votre|vos)\b the census used —
        # « Votre » and « vos » count, a substring like « vous-mêmes » does
        # not exist here but « coud-vous » would not fire on \b alone.
        assert _SECOND_PERSON.search("Votre discours vise à tromper.")
        assert _SECOND_PERSON.search("Un signal de vos pairs.")
        assert not _SECOND_PERSON.search("Les bras croisés envoient un signal.")
