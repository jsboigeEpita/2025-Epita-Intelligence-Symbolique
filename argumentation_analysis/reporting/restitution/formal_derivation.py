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

import re
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

# #2882 — the one default-mode admission rule, shared by the formal axes'
# folded subsections and the Dung canonical line. The issue's R1 as issued
# (« canonique Dung : 1 token, ≤ 40 car. » — the inline predicate
# ``" " not in a and len(a) <= 40``) cannot be adopted bare: confronted with
# the strings it admits (90 real campaign dumps, local inspection), 454 of
# its 519 unique admissions are underscore-joined SENTENCE TRANSCRIPTIONS —
# the FOL/PL atom naming swaps spaces for underscores, so a whole corpus
# proposition is one punctuation-free token (« <mot>_<mot>_<mot> », 3-6
# word-runs, ≤ 40 chars). The Dung side never hits this (its atoms keep
# their spaces: 0/717 real atoms pass R1), which is why the same predicate
# looked safe there. The guard: a string that is a word SEQUENCE (≥ 3 runs
# of ≥ 3 letters) carrying no logic symbol is a transcription whatever its
# separator — machine atoms carry symbols (``p(a)``, ``¬(p∧q)``, ``a->b``)
# or stay under three word-runs (``pred_alpha``).
_CANONICAL_ATOM_CHAR_CAP = 40
_TRANSCRIBED_WORD_RUNS = 3
_LOGIC_SYMBOL_RE = re.compile(r"[∧∨¬→←↔⇒⇐∀∃≡⊕⊤⊥()!&|<>=]")
_WORD_RUN_RE = re.compile(r"[A-Za-zÀ-ÿ]{3,}")


def is_machine_shaped(text: str) -> bool:
    """#2882 — a tested-content string the folded annex may cite by default.

    One definition for both surfaces (the three formal-axis subsections and
    the Dung machinery's canonical line): the R1 bound (one token, ≤ 40
    chars) completed by the transcribed-sentence guard measured above. A
    spaced string never passes (R1's bound — the next-more-permissive rules
    R2-R4 measured +688 to +1955 admissions beyond R1, of which 322-404
    prose-shaped); an underscore-joined sentence never passes either.
    """
    stripped = text.strip()
    if " " in stripped or len(stripped) > _CANONICAL_ATOM_CHAR_CAP:
        return False
    if _LOGIC_SYMBOL_RE.search(stripped):
        return True
    return len(_WORD_RUN_RE.findall(stripped)) < _TRANSCRIBED_WORD_RUNS


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


# A unit literal is an optional negation followed by ONE atom term: a PL/modal
# identifier (``p``) or a FOL ground atom (``mortal(socrates)`` — flat terms
# only, no nested parens: a nested term does not localize and stays honest).
_UNIT_LITERAL = re.compile(
    r"^\s*(!?)([A-Za-z_][A-Za-z0-9_]*(?:\([A-Za-z0-9_,\s]*\))?)\s*$"
)


def _locate_conflict_pair(
    formulas: List[str],
) -> Optional[Tuple[str, str]]:
    """The complementary unit-literal pair of a whole-KB refutation, if any.

    #2960: a refuted record is a whole-KB consistency check — its verdict
    belongs to the formulas IN CONFLICT, not to whichever formula happens to
    come first in list order. The offline localization this pipeline can do
    without a solver is the unit-clause pair (``a`` asserted by one formula,
    ``!a`` by another). A conflict spread over compound formulas is NOT
    localized: the caller renders the honest absence instead of pinning the
    refutation on the record's first formulas.
    """
    seen: Dict[str, Tuple[str, int]] = {}
    for index, formula in enumerate(formulas):
        match = _UNIT_LITERAL.match(formula)
        if not match:
            continue
        polarity, atom = match.groups()
        if atom in seen:
            other_polarity, other_index = seen[atom]
            if other_polarity != polarity:
                return formulas[other_index], formulas[index]
        else:
            seen[atom] = (polarity, index)
    return None


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
    verified ones (a sample of what passed).

    #2960: for a refuted record the content is the CONFLICT — the
    complementary unit-literal pair when the conflict localizes offline —
    never the record's first formulas in list order: a KB-level refutation
    pinned on whatever comes first names an inference the solver never
    singled out. When the conflict does not localize (compound formulas,
    spread conflict), there is no localizable tested content: ``None``,
    and the decisive role must not fire against a specific inference.
    """
    selected = _records_with_verdict(records, verdict_reader, verdict=not refuted)
    real, placeholders = scan_tested_content(selected, verdict_reader)
    if refuted:
        conflict = _locate_conflict_pair(real)
        if conflict is None:
            return None
        atoms = [_readable_atom(f) for f in conflict]
    else:
        atoms = [_readable_atom(f) for f in real[:max_atoms]]
    if not atoms:
        return None
    quoted = ", ".join(f"« {a} »" for a in atoms)
    extra = len(real) + placeholders - len(atoms)
    suffix = (
        f" (+{accord(extra, 'autre formule', 'autres formules')})" if extra > 0 else ""
    )
    return quoted + suffix
