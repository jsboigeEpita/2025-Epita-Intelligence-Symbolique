"""#3394 follow-up (R1142) — the penalty is said, the rank compares parts,
every definition addresses the arguer.

Three defects the coordinator's re-review put on the cycle-0 record:

1. 38 of 67 quality entries are ``original_score × (1 − penalty_factor)``
   while the ranking's base clause called every figure a plain sum — the
   render hid WHICH figure the penalty moved (ask 5's class, render side).
2. The ranking sorted on the raw sum while each entry printed its own
   ceiling: whichever unit happened to have more evaluated virtues came
   first, not the better-held one. Measured on this seat's 10 cycle-0
   state dumps, the sum order and the part order disagree on 9/10
   documents (table in the PR body). The sort now follows the reading
   ``add_quality_score``'s own contract documents: readers normalise by
   dividing by ``len(scores)``.
3. 5 of the 1 408 vendored ``desc_fr`` cells did not address the arguer in
   the second person — two had lost their leading « V » upstream, three
   were impersonal statements. The CSV stays a byte-faithful mirror of
   upstream (#1956 pin): the fixes live in the #2036 override table and
   apply at load.

Offline: no JVM, no network, no LLM.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

from argumentation_analysis.utils.taxonomy_local_overrides import (
    REGISTER_FIXES,
    purge_row,
)
from argumentation_analysis.utils.taxonomy_loader import taxonomy_definition


class TestEveryDefinitionAddressesTheArguer:
    """Point 3 — 5 of the 1 408 upstream desc_fr cells were not in the
    second person. The vendored CSV is a byte-faithful mirror of upstream
    (#1956 integrity pin): the fixes live in the code-level override table
    (#2036's vehicle) and apply at load. The census measures the LOADED
    register; the loader witness pins one fixed node end to end."""

    _CSV = Path(__file__).resolve().parents[5] / (
        "argumentation_analysis/data/argumentum_fallacies_taxonomy.csv"
    )
    _SECOND_PERSON = re.compile(r"\b(vous|votre|vos)\b", re.IGNORECASE)

    def _loaded_rows(self) -> list:
        # Parse integrity first: DictReader is lenient (an extra comma in
        # an unquoted cell shifts every column after it silently — the
        # pandas loaders raise where a lenient census kept reading green).
        # The strict reader pins the file shape before the census reads it.
        with self._CSV.open(encoding="utf-8-sig", newline="") as fh:
            reader = csv.reader(fh)
            header = next(reader)
            rows_raw = list(reader)
        bad_rows = [i for i, r in enumerate(rows_raw, start=2) if len(r) != len(header)]
        assert bad_rows == [], bad_rows
        rows = [dict(zip(header, r)) for r in rows_raw]
        return [purge_row(r) for r in rows]

    def test_every_loaded_desc_fr_cell_addresses_the_arguer(self):
        rows = self._loaded_rows()
        assert len(rows) == 1408
        offenders = [
            r["path"]
            for r in rows
            if (r.get("desc_fr") or "").strip()
            and not self._SECOND_PERSON.search(r["desc_fr"])
        ]
        assert offenders == [], offenders

    def test_every_register_fix_targets_an_offending_cell(self):
        # Dead-override guard, the #2036 discipline: a fix whose upstream
        # cell already addresses the arguer is pointless; a fix that does
        # not address the arguer is no fix. Both redden here.
        with self._CSV.open(encoding="utf-8-sig", newline="") as fh:
            raw = {
                r["PK"]: (r.get("desc_fr") or "").strip() for r in csv.DictReader(fh)
            }
        missing = {str(pk) for pk in REGISTER_FIXES} - set(raw)
        assert not missing, missing
        for pk, fixed in REGISTER_FIXES.items():
            assert not self._SECOND_PERSON.search(raw[str(pk)]), (pk, raw[str(pk)])
            assert self._SECOND_PERSON.search(fixed), (pk, fixed)

    def test_a_reworded_node_resolves_to_a_you_definition(self):
        # PK 501 (2.3.2.4.1.2) was « Cibler un individu… » — third person.
        d = taxonomy_definition("cible", "2.3.2.4.1.2")
        assert d and self._SECOND_PERSON.search(d), d
        # PK 1253 (6.3.3.1.3.2.2) had lost its leading « V » upstream.
        d2 = taxonomy_definition("comportementalisme", "6.3.3.1.3.2.2")
        assert d2 and d2.startswith("Vous "), d2
