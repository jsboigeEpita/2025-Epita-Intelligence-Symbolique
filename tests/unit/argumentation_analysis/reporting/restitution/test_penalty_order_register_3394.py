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

from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    quality_ranking_line,
)
from argumentation_analysis.reporting.restitution.figure_scales import (
    penalised_sum_on_its_maximum,
)
from argumentation_analysis.utils.taxonomy_local_overrides import (
    REGISTER_FIXES,
    purge_row,
)
from argumentation_analysis.utils.taxonomy_loader import taxonomy_definition


def _quality(*entries: tuple) -> dict:
    """Production shape: ``overall`` never travels without its ``scores``
    map (``add_quality_score`` writes the pair). ``n`` is the count of
    evaluated virtues — the sum's own ceiling (#1942). A 5th element
    ``(before,)`` adds the #289 record ``applied`` + ``original_score``."""
    out = {}
    for entry in entries:
        arg_id, overall, n = entry[0], entry[1], entry[2]
        record = {
            "overall": overall,
            "scores": {f"vertu_{i}": 1.0 for i in range(n)},
        }
        if len(entry) > 3:
            record["fallacy_penalty"] = {
                "applied": True,
                "penalty_factor": 0.15,
                "original_score": entry[3],
            }
        out[arg_id] = record
    return out


class TestAPenalisedScoreSaysIt:
    """Point 1 — the record says the penalty; the render repeated the sum."""

    def test_a_penalised_entry_prints_after_and_before(self):
        quality = _quality(("arg_1", 4.25, 6, 5.0), ("arg_2", 3.0, 6))
        line = quality_ranking_line(quality, 9)
        assert "arg_1 (4,25 sur 6 après pénalité (5,00 avant))" in line, line
        assert "arg_2 (3,00 sur 6)" in line, line

    def test_the_base_clause_says_the_penalty_convention_only_when_one_applied(self):
        penalised = quality_ranking_line(
            _quality(("arg_1", 4.25, 6, 5.0), ("arg_2", 3.0, 6)), 9
        )
        assert "après la pénalité de sophisme" in penalised, penalised
        clean = quality_ranking_line(_quality(("arg_1", 5.0, 6)), 9)
        assert "pénalité" not in clean, clean

    def test_the_winner_clause_says_the_penalty(self):
        quality = _quality(("arg_1", 4.25, 6, 5.0), ("arg_2", 3.0, 6))
        line = quality_ranking_line(quality, 9, "arg_2")
        assert "est 2ᵉ de ce classement (3,00 sur 6)" in line, line
        assert "est en tête" in line and "4,25 sur 6 après pénalité" in line, line

    def test_the_head_group_scale_is_silent_when_ceilings_differ(self):
        # Part-tied head (1,50 each) on different ceilings: one member's
        # ceiling must not label the other's — the listing carries each, the
        # shared-head clause carries no parenthetical. The head clause only
        # exists on the winner branch, so the vote winner sits below the tie.
        quality = _quality(("arg_a", 3.0, 2), ("arg_b", 6.0, 4), ("arg_w", 2.0, 2))
        line = quality_ranking_line(quality, 9, "arg_w")
        assert "arg_a (3,00 sur 2)" in line and "arg_b (6,00 sur 4)" in line, line
        assert "partagent la tête" in line, line
        assert "partagent la tête (" not in line, line

    def test_a_penalty_without_a_readable_before_still_says_after(self):
        assert (
            penalised_sum_on_its_maximum(4.25, None, 6) == "4,25 sur 6 après pénalité"
        )
        # unreadable shapes (string, NaN) keep the marker, lose the parenthetical
        assert penalised_sum_on_its_maximum(4.25, "x", 6) == "4,25 sur 6 après pénalité"


class TestTheRankComparesParts:
    """Point 2 — measured on the cycle-0 dumps: the sum order and the part
    order disagree on 9/10 documents. The sort follows the part."""

    def test_a_smaller_sum_on_a_smaller_ceiling_ranks_first(self):
        # 4-on-2 (part 2,00) outranks 5-on-6 (part 0,83): the sum order
        # crowned the six-virtue unit by ceiling accident.
        line = quality_ranking_line(_quality(("arg_1", 5.0, 6), ("arg_2", 4.0, 2)), 9)
        assert line.index("arg_2") < line.index("arg_1"), line

    def test_uniform_ceilings_keep_the_sum_order(self):
        # Control — same ceiling everywhere: part order == sum order, the
        # #3159/#3347/#3356 contract shapes are untouched.
        line = quality_ranking_line(
            _quality(("a", 5.0, 6), ("b", 4.0, 6), ("c", 3.0, 6)), 9
        )
        assert line.index("a") < line.index("b") < line.index("c"), line

    def test_the_base_clause_names_the_part_reading(self):
        line = quality_ranking_line(_quality(("arg_1", 5.0, 6)), 9)
        assert "le rang se lit sur la part du plafond atteinte" in line, line

    def test_an_entry_without_scores_rides_after_the_measured(self):
        quality = _quality(("arg_1", 5.0, 6), ("arg_2", 4.0, 2))
        quality["arg_bare"] = {"overall": 4.5}
        line = quality_ranking_line(quality, 9)
        assert line.index("arg_2") < line.index("arg_1") < line.index("arg_bare"), line
        assert "arg_bare (" not in line, line

    def test_a_bare_entry_never_ties_a_measured_one(self):
        # The part sort's first cut compared ``None == None`` — on #3337's
        # all-bare fixture every entry "tied" whatever its sum, and a bare
        # 4.0 rode the co-holders of a bare 5.0 head. The tie key carries
        # the group: bare ties bare on the sum, measured ties measured on
        # the part, and the two groups never tie.
        quality = _quality(("arg_a", 3.0, 3), ("arg_b", 3.0, 3))
        quality["arg_bare"] = {"overall": 3.0}
        line = quality_ranking_line(quality, 9, "arg_a")
        assert "partage la tête" in line and "avec arg_b." in line, line
        assert "arg_bare" not in line.split("partage la tête")[1], line


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
