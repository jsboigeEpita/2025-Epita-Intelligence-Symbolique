"""#2960 — rename atoms apart before conjoining nl_to_logic translations.

Each translation of a ``nl_to_logic`` batch carries its own ``variables``
map (atom -> meaning), so an atom name only means something *inside* its
translation. The KB union sites (PL, FOL, modal in ``invoke_callables.py``)
used to conjoin ``translations[*].formula`` and ignore those maps: two
unrelated sentences translated independently can both pick ``p``, and the
conjoined KB then carries ``p`` and ``!p`` under two different meanings —
a mechanical UNSAT the report pinned on the first formulas of the record
(measured on the 06/10 authorized pass: PL 39 formulas UNSAT, SAT without
the two colliding ones).

The fix is one helper, called by every union site (never a copy per site):
an atom whose meaning DIFFERS across translations is renamed apart (suffixed
with the translation's index — the batch carries no id field); an atom whose
meaning is identical stays shared, since a shared signature is the point of
a joint KB. The discriminant is the MEANING recorded in ``variables``, never
the name. An atom with no recorded meaning on either side cannot be proven
identical, so it is renamed apart too — renaming cannot create a false
contradiction, only lose a share the record could not justify.

The replacement is identifier-bounded (a letter boundary, not a word
boundary: ``p`` inside ``p1`` is a different atom and must not move), and a
suffixed name that would collide with an existing atom extends its suffix
until it does not.
"""

from __future__ import annotations

import re
from typing import Dict, List

Translation = Dict[str, object]


# Letter boundary on both sides of the atom: `_` is a word character, so
# `p` does not match inside `p1` or `premise` (#2012's boundary, applied to
# renaming — a `\\b` regex would leave `p_only` untouched where `p` moved).
def _atom_pattern(atom: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![A-Za-z0-9_]){re.escape(atom)}(?![A-Za-z0-9_])")


def rename_atoms_apart(translations: List[Translation]) -> List[str]:
    """The batch's formulas with colliding-meaning atoms renamed apart.

    Returns one formula string per translation, in batch order — the union
    sites keep their own filtering (logic_type, is_valid, ``;`` splitting
    for FOL), applied AFTER the renaming so every fragment of a translation
    carries the translation's renamed atoms consistently.

    An atom used by several translations keeps its name when every recorded
    meaning is identical; any difference — including a missing recording,
    which is an absent discriminant, not a meaning — renames it in EVERY
    translation that uses it, suffixed with that translation's index.
    """
    # Pass 1 — the batch's recorded atom universe.
    recorded: Dict[str, List[object]] = {}
    formulas: List[str] = []
    per_translation_vars: List[Dict[str, object]] = []
    for t in translations:
        variables = t.get("variables")
        variables = variables if isinstance(variables, dict) else {}
        per_translation_vars.append(variables)
        formula = t.get("formula")
        formulas.append(formula if isinstance(formula, str) else "")
        for atom, meaning in variables.items():
            if isinstance(atom, str):
                recorded.setdefault(atom, []).append(meaning)

    # Pass 2 — atom -> one meaning per translation that USES it, recorded or
    # not. A translation using the atom in its formula without recording it
    # contributes None: unprovable sharing is a collision (renaming cannot
    # create a false contradiction, only lose an unjustified share).
    users: Dict[str, List[object]] = {}
    for variables, formula in zip(per_translation_vars, formulas):
        for atom in recorded:
            if atom in variables:
                users.setdefault(atom, []).append(variables.get(atom))
            elif _atom_pattern(atom).search(formula):
                users.setdefault(atom, []).append(None)

    colliding = {
        atom
        for atom, meanings in users.items()
        if len(meanings) > 1 and any(m != meanings[0] for m in meanings[1:])
    }

    all_atoms = set(recorded)
    renamed: List[str] = []
    for index, t in enumerate(translations):
        formula = t.get("formula")
        if not isinstance(formula, str):
            renamed.append("")
            continue
        variables = t.get("variables")
        variables = variables if isinstance(variables, dict) else {}
        for atom in sorted(colliding):
            if atom not in variables and not _atom_pattern(atom).search(formula):
                continue  # this translation does not use the atom
            fresh = f"{atom}__t{index}"
            while fresh in all_atoms:
                fresh += "_"
            all_atoms.add(fresh)
            formula = _atom_pattern(atom).sub(fresh, formula)
        renamed.append(formula)
    return renamed
