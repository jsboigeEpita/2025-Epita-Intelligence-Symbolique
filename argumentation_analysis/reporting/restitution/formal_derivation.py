# -*- coding: utf-8 -*-
"""Extract the tested-inference content carried by formal-axis state records.

#1914 (constat 1, tranche Acte II) : « Solver badges without derivations ».
The state records of the three logic axes DO carry the concrete tested
content — ``formulas`` (the actual clauses), ``model``, ``axiom_count`` for
PL, ``inferences`` for FOL — but the restitution collapsed them to counts
(« N inférences PL inconsistantes sur M vérifiées »). This module extracts a
bounded, reader-orientable rendering of WHAT WAS TESTED so both Acte II
surfaces (the ``TENUE FORMELLE`` anchors and the #1914 role statements) can
hand the conductor the derivation material instead of a bare badge.

Anti-fabrication contract (the #1941 discipline applied to Acte II):

* the fragment is built ONLY from formula strings actually present in the
  record — nothing is invented, reformulated or translated here (the
  conducted LLM translates in its own words; we hand it material);
* placeholder strings the writers emit when they carried no real formula
  (``CL(0 conditionals): …``, ``DL: Knowledge base is consistent.``,
  pasted titles/URLs) are NOT derivations — an axis whose decided records
  carry only placeholders yields ``None`` and the surfaces render the
  honest absence (« contenu testé non disponible »), never a dressed-up
  counter;
* content-derived atoms (underscored identifiers transcribed from the
  corpus) are local processing material — on GitHub-indexed surfaces the
  caller must scrub them (privacy HARD, same rule as render excerpts).
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from .fr_accord import accord

# Writers emit these lead-ins when the record carries NO real formula —
# a status message, not tested content. Measured on real dumps
# (CL/QBF/DL placeholders, pasted transcript titles with URLs).
_PLACEHOLDER_PREFIXES: Tuple[str, ...] = (
    "CL(",
    "DL:",
    "QBF:",
    "KB ",
    "Knowledge base",
)

_MAX_ATOMS = 3
_ATOM_CHAR_CAP = 56
_TOTAL_FORMULA_CAP = 12

# #1914 criterion 6 — the folded appendix carries one subsection per formal
# axis under this stable ref, the twin of ``dung_reader.appendix_ref`` for the
# derivation material (« Annexe Dung[label] » ⇄ « Annexe FOL[dérivations] »).
# Produced here, next to the axis vocabulary, so a citer imports one spelling.
_AXIS_REF_FAMILIES: Tuple[str, ...] = ("FOL", "PL", "modale")


def formal_axis_ref(family: str) -> str:
    """The stable opaque appendix ref of a formal axis (#1914 criterion 6)."""
    return f"Annexe {family}[dérivations]"


def _is_real_formula(text: str) -> bool:
    """A formula string qualifies as tested content unless it is a
    writer placeholder (status message, pasted title, URL)."""
    stripped = text.strip()
    if not stripped:
        return False
    if any(stripped.startswith(p) for p in _PLACEHOLDER_PREFIXES):
        return False
    if "http://" in stripped or "https://" in stripped:
        return False
    return True


def _readable_atom(formula: str) -> str:
    """Underscored identifiers → spaced words, bounded length.

    The atoms are transcribed identifiers (``device_is_broken``) or short
    clauses — already semi-readable once underscores become spaces. The
    conducted LLM translates them into prose; this only makes them
    hand-over-able."""
    spaced = formula.strip().replace("_", " ")
    if len(spaced) > _ATOM_CHAR_CAP:
        spaced = spaced[: _ATOM_CHAR_CAP - 1].rstrip() + "…"
    return spaced


def _records_with_verdict(
    records: Any,
    verdict_reader: Callable[[Dict[str, Any]], Optional[bool]],
    verdict: bool,
) -> List[Dict[str, Any]]:
    if not isinstance(records, list):
        return []
    return [r for r in records if isinstance(r, dict) and verdict_reader(r) is verdict]


def scan_tested_content(
    records: Any,
    verdict_reader: Callable[[Dict[str, Any]], Optional[bool]],
) -> Tuple[List[str], int]:
    """The formula strings a DECIDED record set carries, verbatim.

    Returns ``(real, placeholders)``: the strings that qualify as tested
    content (in record order, duplicates kept — the caller caps and de-dupes),
    and how many were rejected by :func:`_is_real_formula`. One reader of the
    ``formulas`` shape, shared by the readable rendering below and by the
    folded appendix (#1914 criterion 6) — a second loop over the same shape
    would be a second way to misread it. Undecided records (``None``) are
    dropped, never collapsed into a verdict (#1019).
    """
    real: List[str] = []
    placeholders = 0
    for record in records if isinstance(records, list) else []:
        if not isinstance(record, dict):
            continue
        if verdict_reader(record) is None:
            continue
        formulas = record.get("formulas")
        if not isinstance(formulas, list):
            continue
        for formula in formulas:
            if not isinstance(formula, str):
                continue
            if _is_real_formula(formula):
                real.append(formula)
            else:
                placeholders += 1
    return real, placeholders


def extract_tested_content(
    records: Any,
    verdict_reader: Callable[[Dict[str, Any]], Optional[bool]],
    refuted: bool,
    max_atoms: int = _MAX_ATOMS,
) -> Optional[str]:
    """Bounded rendering of what the axis actually tested.

    Returns ``None`` when the selected records carry no real formula
    (placeholder-only or empty) — the caller renders the honest absence,
    never a fabricated derivation. ``refuted=True`` selects the REFUTED
    records (the decisive derivation: what failed); ``refuted=False`` the
    verified ones (a sample of what passed)."""
    selected = _records_with_verdict(records, verdict_reader, verdict=not refuted)
    real, placeholders = scan_tested_content(selected, verdict_reader)
    atoms = [_readable_atom(f) for f in real[:max_atoms]]
    if not atoms:
        return None
    quoted = ", ".join(f"« {a} »" for a in atoms)
    extra = len(real) + placeholders - len(atoms)
    suffix = (
        f" (+{accord(extra, 'autre formule', 'autres formules')})" if extra > 0 else ""
    )
    return quoted + suffix
