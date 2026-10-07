"""#2960 — witnesses for the rename-apart helper and its wiring at the union sites.

The KB union sites (PL, FOL, modal) conjoined ``translations[*].formula``
and ignored the per-translation ``variables`` maps, so two unrelated
sentences translated independently could both pick ``p`` — a mechanical
UNSAT the report pinned on the first formulas of the record (measured on
the 06/10 authorized pass). These witnesses pin the fix:

- different meanings under one atom name -> renamed apart, no ``a``/``!a``
  pair survives on a shared name (the born-red shape: on main the helper
  does not exist and the raw conjoin stays contradictory);
- **positive control**: the SAME meaning under ``p`` and ``!p`` is a
  genuine contradiction and must stay shared — without this control a
  rename-everything fix would pass;
- the identifier boundary (``p`` inside ``p1`` does not move), the suffix
  collision guard, and the absent-recording rule;
- the three union sites actually route through the helper (a structural
  witness — the raw conjoin must not come back).
"""

from __future__ import annotations

import re
from pathlib import Path

from argumentation_analysis.orchestration.kb_atom_renaming import rename_atoms_apart

REPO = Path(__file__).resolve().parents[4]
INVOKE = REPO / "argumentation_analysis" / "orchestration" / "invoke_callables.py"


def _t(index: int, formula: str, variables: dict | None) -> dict:
    """A translation dict shaped like the nl_to_logic batch output."""
    out = {
        "original_text": f"unit {index}",
        "formula": formula,
        "logic_type": "propositional",
        "is_valid": True,
        "attempts": 1,
        "confidence": 0.9,
    }
    out["variables"] = variables if variables is not None else {}
    return out


class TestCollidingMeaningsAreRenamedApart:
    def test_two_meanings_under_one_atom_no_longer_contradict(self) -> None:
        """The measured 06/10 shape: ``!p`` (M1) vs ``p`` (M2).

        On main the union conjoined both formulas verbatim and the KB was
        UNSAT; after the fix each meaning gets its own atom, so no pair of
        formulas asserts ``a`` and ``!a`` on the same name.
        """
        translations = [
            _t(0, "!p", {"p": "M1 (accusation)"}),
            _t(1, "p", {"p": "M2 (enumeration)"}),
        ]
        renamed = rename_atoms_apart(translations)
        assert renamed == ["!p__t0", "p__t1"]
        # no shared atom carries both polarities across the batch
        atoms = {renamed[0].lstrip("!"), renamed[1].lstrip("!")}
        assert len(atoms) == 2

    def test_same_meaning_stays_shared(self) -> None:
        """Positive control: one meaning, two polarities, a genuine refutation.

        A rename-everything fix would destroy this contradiction and pass
        the test above for the wrong reason — this control reddens it.
        """
        translations = [
            _t(0, "!p", {"p": "M1"}),
            _t(1, "p", {"p": "M1"}),
        ]
        assert rename_atoms_apart(translations) == ["!p", "p"]

    def test_partial_overlap_renames_only_the_colliding_atom(self) -> None:
        translations = [
            _t(0, "!p & q", {"p": "M1", "q": "shared"}),
            _t(1, "p & q", {"p": "M2", "q": "shared"}),
        ]
        assert rename_atoms_apart(translations) == ["!p__t0 & q", "p__t1 & q"]

    def test_identifier_boundary_p1_is_not_p(self) -> None:
        """``p`` inside ``p1`` is a different atom and must not move (#2012)."""
        translations = [
            _t(0, "!p & p1", {"p": "M1", "p1": "other"}),
            _t(1, "p", {"p": "M2"}),
        ]
        renamed = rename_atoms_apart(translations)
        assert renamed[0] == "!p__t0 & p1"
        assert renamed[1] == "p__t1"


class TestRecordingRules:
    def test_absent_recording_is_an_absent_discriminant(self) -> None:
        """Unprovable sharing is a collision: renaming cannot create a false
        contradiction, only lose an unjustified share."""
        translations = [
            _t(0, "!p", {"p": "M1"}),
            _t(1, "p", {}),  # uses p in the formula, records nothing for it
        ]
        assert rename_atoms_apart(translations) == ["!p__t0", "p__t1"]

    def test_suffix_collision_extends_until_fresh(self) -> None:
        translations = [
            _t(0, "!p", {"p": "M1", "p__t1": "occupied"}),
            _t(1, "p", {"p": "M2"}),
        ]
        renamed = rename_atoms_apart(translations)
        # p__t1 already exists: translation 1's fresh name must extend.
        assert renamed[1].startswith("p__t1_")

    def test_single_translation_is_never_renamed(self) -> None:
        translations = [_t(0, "!p & p", {"p": "M1"})]
        assert rename_atoms_apart(translations) == ["!p & p"]

    def test_non_string_formula_yields_empty(self) -> None:
        translations = [_t(0, "", {"p": "M1"})]
        assert rename_atoms_apart(translations) == [""]


class TestUnionSitesRouteThroughTheHelper:
    def test_every_union_site_calls_the_helper(self) -> None:
        """Structural witness: the PL, FOL and modal union sites conjoin
        RENAMED formulas — the raw ``t["formula"]`` conjoin must not come
        back (one helper, called by every site, never a copy per site).
        """
        source = INVOKE.read_text(encoding="utf-8-sig")
        calls = re.findall(r"rename_atoms_apart\(", source)
        assert len(calls) == 3, (
            f"expected exactly 3 union-site calls (PL, FOL, modal), "
            f"found {len(calls)} — a site conjoining raw formulas again "
            "is the #2960 defect"
        )
