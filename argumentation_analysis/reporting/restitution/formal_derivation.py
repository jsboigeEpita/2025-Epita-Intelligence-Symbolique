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
    decided = _records_with_verdict(records, verdict_reader, verdict=not refuted)
    atoms: List[str] = []
    n_formulas = 0
    for r in decided:
        formulas = r.get("formulas")
        if not isinstance(formulas, list):
            continue
        for f in formulas:
            if not isinstance(f, str):
                continue
            n_formulas += 1
            if _is_real_formula(f) and len(atoms) < max_atoms:
                atoms.append(_readable_atom(f))
    if not atoms:
        return None
    quoted = ", ".join(f"« {a} »" for a in atoms)
    extra = n_formulas - len(atoms)
    suffix = (
        f" (+{accord(extra, 'autre formule', 'autres formules')})" if extra > 0 else ""
    )
    return quoted + suffix
