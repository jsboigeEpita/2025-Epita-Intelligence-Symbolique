"""Modal KB identifier normalization (#1326, builds on #1260/#1230).

Tweety's ``MlParser`` grammar is *stricter* than the propositional parser: a
predicate/sort declaration must match ``[a-zA-Z][a-zA-Z0-9]*`` — underscores and
other separators are rejected with::

    ParserException: Illegal characters in predicate definition 'joke_teleprompter';
                      declaration must conform to [a-z,A-Z]([a-z,A-Z,0-9])*

Several modal-KB producers emit underscored multi-word atoms (LLM-generated
identifiers such as ``joke_teleprompter``, the spectacular-path
``_construct_modal_kb_from_json``). Such a KB never parses, so consistency is
never decided and the modal axis degrades to honest ``None`` (the R519
firsthand-reproduced failure: 3/3 modal axes undecided).

This module maps every MlParser-illegal atom to a fresh legal identifier and is
applied at the parse point (``ModalHandler``, immediately *amont* de
``parseBeliefBase``) so EVERY caller is protected regardless of upstream
producer — defense-in-depth. The transform:

* PascalCase join on non-alphanumeric splits: ``joke_teleprompter`` →
  ``JokeTeleprompter`` (the semantic stem survives, only the separators drop).
* generic ``MpAtomN`` fallback when the stem is empty/illegal.
* applied **consistently** to declarations and bodies, and the collision set
  tracks *generated* candidates too — so two distinct source atoms that
  PascalCase to the same stem (``heavy_rain`` vs ``heavy__rain``) are
  disambiguated instead of collapsed. That soundness guard was absent from the
  original inline #1260 closure.
* the collision set also starts with every atom that is **already legal** in
  the text being normalised (#2471), so ``heavy_rain`` next to a real
  ``HeavyRain`` becomes ``HeavyRain1`` instead of merging into it. Without it,
  the consistent KB ``heavy_rain``, ``!HeavyRain`` reached the solver as
  ``HeavyRain``, ``!HeavyRain`` and was decided inconsistent (measured).

The FOL parser (``FolParser``) applies the same rule to predicate declarations
(measured on the real JVM, #2468: ``A_Fait`` is refused, ``AFait`` accepted), so
``FOLLogicAgent.extract_fol_metadata`` names FOL predicates with ``legalize``
too. ``legalize`` folds accents to ASCII before it splits (``Évalue`` →
``Evalue``); without the fold the accented letter was a separator and the name
lost it (``Value``).

Anti-pendule: this normalizes the **syntax** of the sort-name for Tweety only;
it does not neutralize semantic content or variance. No heuristic masks a
parse-fail — a genuinely malformed KB is still rejected and the handler returns
honest ``None`` (#1019 fail-loud). It is idempotent on already-legal atoms, so
the nl path, which builds its KB with ``build_modal_kb``, is unaffected by the
second pass in ``ModalHandler``. ``build_modal_kb`` is the one legaliser of the
modal paths: the inline #1260 closure of ``invoke_callables`` and the copy in
``scripts/run_fp16_modal_enum.py`` call it now (#2471).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Dict, Iterable, List, Tuple

# Reserved words of the modal grammar — must never be treated as atoms.
_KEYWORDS = frozenset(
    {
        "forall",
        "exists",
        "true",
        "false",
        "type",
        "prop",
        "and",
        "or",
        "not",
        "implies",
    }
)

# A modal atom token: any identifier-shaped run including underscores, so
# ``joke_teleprompter`` is captured as ONE token rather than split around the
# underscore. Accented letters belong to the token too (#2471): MlParser refuses
# them ("Illegal characters in predicate definition 'évalue'", measured), so an
# accented atom is captured whole and folded by ``legalize`` instead of being
# split around its accent, which left the accent in the KB.
_ACCENTED = "\u00c0-\u00d6\u00d8-\u00f6\u00f8-\u00ff"  # Latin-1 letters
_ATOM_RE = re.compile(rf"[A-Za-z{_ACCENTED}_][A-Za-z0-9{_ACCENTED}_]*")

# Illegal ``sort`` declaration lines (#1441). The Tweety FOL/ML grammar
# (firsthand-confirmed vs FolParser/MlParser BNF: ``tweety_fol_bnf.md``) has
# NO ``sort`` keyword — sorts are declared as ``NAME = {constants}`` and
# propositions as ``type(prop)``. Producers occasionally emit ``sort ((a || b
# || c))`` (a compound boolean where the parser expects a single sort
# identifier), which raises ``ParserException: Illegal characters / Missing '='
# in sort definition`` on EVERY modal KB and leaves the modal axis falling back
# to SPASS noisily (ATT-3 firsthand finding, 3/3 corpus). Stripping the line is
# the honest fix: the declaration is syntactically unrepresentable (there is no
# "union sort" in Tweety), and the propositions it names are already declared
# via ``type(prop)`` — so removing it changes nothing semantic, only silences a
# quasi-dead path's error trace. Anti-pendule: strip the illegal SYNTAX only,
# do not mask a genuine parse-fail (#1019 fail-loud) — a KB malformed beyond
# this still raises.
_ILLEGAL_SORT_LINE_RE = re.compile(r"^[ \t]*sort\b[^\n]*\n?", re.MULTILINE)


def strip_illegal_sort_declarations(content: str) -> Tuple[str, int]:
    """Remove illegal ``sort ...`` declaration lines a Tweety ML KB cannot parse.

    Returns ``(cleaned_content, removed_count)``. ``removed_count`` lets callers
    log the sanitization (visible, not silent — anti-théâtre #1019).
    """
    if "sort" not in content:  # fast path: most KBs declare via type(prop)
        return content, 0
    matches = _ILLEGAL_SORT_LINE_RE.findall(content)
    if not matches:
        return content, 0
    return _ILLEGAL_SORT_LINE_RE.sub("", content), len(matches)


# The MlParser declaration grammar (firsthand-confirmed via the ParserException
# message reproduced in #1326): first letter alphabetic, rest alphanumeric, NO
# underscores/separators.
_LEGAL_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9]*$")


def fold_to_ascii(text: str) -> str:
    """Drop the accents of ``text`` (``été`` → ``ete``) and any character
    with no ASCII base letter."""
    decomposed = unicodedata.normalize("NFKD", text)
    return decomposed.encode("ascii", "ignore").decode("ascii")


class ModalIdentifierNormalizer:
    """Sound, memoized mapping of modal atoms to MlParser-legal identifiers.

    ``reserved`` pre-seeds the collision set (e.g. atoms already legal in the
    KB) so a generated symbol never shadows a real atom;
    ``reserve_legal_atoms`` seeds it from the texts themselves (#2471).
    Generated candidates
    are also added to the collision set, so two distinct source atoms that
    PascalCase to the same stem are disambiguated rather than collapsed — the
    soundness guard missing from the original inline #1260 closure.
    """

    def __init__(self, reserved: Iterable[str] = ()) -> None:
        self._reserved: set[str] = set(reserved)
        self._forward: Dict[str, str] = {}

    def reserve_legal_atoms(self, *texts: str) -> None:
        """Add every atom already legal in ``texts`` to the collision set.

        Call it with every text that shares this normaliser (a KB and its
        query) before normalising any of them: a renamed atom must never take
        the name of a legal atom that only appears in a text normalised later.
        """
        for text in texts:
            for tok in _ATOM_RE.findall(text):
                if tok not in _KEYWORDS and _LEGAL_RE.match(tok):
                    self._reserved.add(tok)

    def legalize(self, atom: str) -> str:
        """Return an MlParser-legal identifier for ``atom`` (memoized)."""
        if atom in _KEYWORDS or _LEGAL_RE.match(atom):
            return atom
        cached = self._forward.get(atom)
        if cached is not None:
            return cached
        parts = [p for p in re.split(r"[^A-Za-z0-9]+", fold_to_ascii(atom)) if p]
        candidate = "".join(p[:1].upper() + p[1:] for p in parts) or "MpAtom"
        if not _LEGAL_RE.match(candidate) or candidate in self._reserved:
            # Rare: degenerate stem or collision — disambiguate, but keep the
            # readable stem as the base (not a bare MpAtomN).
            base = candidate if _LEGAL_RE.match(candidate) else "MpAtom"
            suffix = 1
            while f"{base}{suffix}" in self._reserved:
                suffix += 1
            candidate = f"{base}{suffix}"
        self._reserved.add(candidate)
        self._forward[atom] = candidate
        return candidate

    def normalize_belief_set(self, content: str) -> Tuple[str, Dict[str, str]]:
        """Normalize every atom in a modal belief-set string.

        Returns ``(normalized_content, reverse_map)`` where ``reverse_map`` is
        ``{normalized: original}`` for readability/traceability. Atoms already
        legal are absent from the map (they pass through verbatim), and they
        are reserved before anything is renamed (#2471).

        Also strips illegal ``sort ...`` declaration lines (#1441): the ML
        grammar has no ``sort`` keyword, so such a line is never parseable.
        The strip count is surfaced via the ``reverse_map`` under a synthetic
        ``__stripped_sort_lines__`` key so callers can log it (visible, not
        silent — anti-théâtre #1019).
        """
        content, removed = strip_illegal_sort_declarations(content)
        self.reserve_legal_atoms(content)
        normalized = _ATOM_RE.sub(lambda m: self.legalize(m.group(0)), content)
        reverse = {v: k for k, v in self._forward.items()}
        if removed:
            reverse["__stripped_sort_lines__"] = str(removed)
        return normalized, reverse


def build_modal_kb(formulas: Iterable[str]) -> Tuple[List[str], List[str]]:
    """Declare and legalise the atoms of undeclared modal formulas.

    The nl path's KB builder (#1224; FP-11 #1214 for the declarations). Returns
    ``(declarations, formulas)``: one ``type(atom)`` per atom in first-seen
    order, and the formulas with every atom made MlParser-legal. One normaliser
    renames every formula, and its collision set starts with every atom already
    legal in any of them, so a renamed atom merges neither into a real atom nor
    into another renamed one (#2471).
    """
    texts = [str(f) for f in formulas]
    normalizer = ModalIdentifierNormalizer()
    normalizer.reserve_legal_atoms(*texts)
    renamed = [
        _ATOM_RE.sub(lambda m: normalizer.legalize(m.group(0)), text) for text in texts
    ]
    seen: Dict[str, None] = {}
    for text in renamed:
        for tok in _ATOM_RE.findall(text):
            if tok not in _KEYWORDS:
                seen.setdefault(tok, None)
    return [f"type({atom})" for atom in seen], renamed
