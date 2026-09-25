"""One vocabulary for a stored belief set's ``logic_type`` (#2643).

Writers spell the type several ways: the state wrappers store ``"Propositional"``
and ``"FOL"``, the pipeline's state writers store ``"propositional"`` and
``"fol"``, the web service stores the request's value. Readers rebuild a
``BeliefSet`` from the stored dict. Every writer and reader resolves a spelling
through this table, so a stored belief set rebuilds whichever writer stored it.
"""

from typing import Optional

# Accepted spelling (lower-case) -> ``BeliefSet.logic_type``.
LOGIC_TYPE_ALIASES = {
    "propositional": "propositional",
    "pl": "propositional",
    "first_order": "first_order",
    "fol": "first_order",
    "modal": "modal",
}

# ``BeliefSet.logic_type`` -> the label the state wrappers store.
STATE_LABELS = {
    "propositional": "Propositional",
    "first_order": "FOL",
    "modal": "Modal",
}


def canonical_logic_type(name: object) -> Optional[str]:
    """The ``BeliefSet.logic_type`` a spelling names, or ``None`` if unknown."""
    if not isinstance(name, str):
        return None
    return LOGIC_TYPE_ALIASES.get(name.strip().lower())
