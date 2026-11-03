"""Personas that read the situation before the analysis (#3377, Epic #3374).

Two producers live here, each on its own capability, each read downstream by a
production phase:

- :mod:`~argumentation_analysis.agents.core.context.historian` — the historical
  situation: date, place, actors, and what was at stake then
  (capability ``historical_context``);
- :mod:`~argumentation_analysis.agents.core.context.strategist` — the game being
  played: players, options, preference profile, and the manipulability the
  governance engine actually COMPUTES (capability ``strategic_read``).

Both write MODEL KNOWLEDGE: what the model brings to the document, never what
the document says. The measured gap (#2841 M1) is exactly this one — the
pipeline forbids itself what the model knows, the same-model zero-shot does not,
and on an undated document the render says "the date is only a deduction from
the content" while the zero-shot dates it in its title line.

The labelling discipline is the whole point, so it is stamped by the producer
and never read from the model's reply: `stamp_basis` walks the items and writes
``basis`` itself. A model that forgets the label — or claims another one —
cannot pass its guess off as the text's own content.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable

#: The only basis a persona item may carry. Downstream readers compare against
#: this constant, never against a literal, so a rename cannot leave a consumer
#: silently accepting an unlabelled claim.
MODEL_KNOWLEDGE_BASIS = "model_knowledge"

#: French label the restitution renders. The report is French; the state stays
#: language-neutral so an English renderer can map it differently.
MODEL_KNOWLEDGE_LABEL_FR = "savoir du modèle"

#: Basis written by a producer that read the document itself. Kept distinct so
#: a reader can tell "the text says it" from "the model knows it" without
#: parsing prose.
TEXT_BASIS = "text"


def stamp_basis(items: Iterable[Dict[str, Any]], basis: str = MODEL_KNOWLEDGE_BASIS):
    """Stamp ``basis`` on every item produced by a persona.

    Returns a new list of new dicts: the caller's objects are never mutated, so
    a caller cannot hand back a half-labelled item by reusing one.

    The stamp is unconditional by design. A producer that let the model choose
    its own basis would turn the one guarantee this module exists for into a
    convention — and the first model that answers ``"text"`` would launder a
    deduction into a quotation.
    """
    stamped: list = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        copy = dict(item)
        copy["basis"] = basis
        stamped.append(copy)
    return stamped


__all__ = [
    "MODEL_KNOWLEDGE_BASIS",
    "MODEL_KNOWLEDGE_LABEL_FR",
    "TEXT_BASIS",
    "stamp_basis",
]
