# -*- coding: utf-8 -*-
"""Per-act unit label tables for writer-facing prompts (#3296).

The census (issue comment 6525864773) measured 15 writer-input blocks that
hand the conductor a bare ``arg_N``; the readability gate (#2980) counts
every printed id as jargon, and the renders echoed them (5 of 41 documents,
R1125a). PR #3303 removed the directives that ORDERED the id; this module
is the second half of the repair (R1126 arbitration): the designation moves
to a per-act Greek-letter table whose legend carries the referent — the
#2896/#2965 precedent (the narrative thread's letters + legend),
generalised from one block to the whole act.

Design, from the measured shapes (c. 6531974201):

- **Substitution at the assembly seam.** The ids reach the prompt through
  *statements* built at evidence time (``conclusion_salience`` writes
  ``f"{arg_id} tient : …"``; ``global_projection`` writes ``f"{arg_id} : N
  méthodes convergent"``) as much as through ``(ancres : …)`` lists — fixing
  the blocks one by one would leave the statements. One substitution over
  the assembled prompt covers every source, present and future.
- **Only ``arg_\\d+`` is labelled.** ``cites`` is a MIXED vocabulary —
  ``arg_1`` but also ``FOL``, ``solveur Tweety``, ``qualite``,
  ``cadre_structure`` — and the method names are readable referents of
  their own: converting them to letters would LOSE a referent, not repair
  one.
- **Letters in order of first appearance**, shared by every block of the
  act, so a join that used to ride the id (weak point ↔ claim excerpt) now
  rides the letter. Past the Greek alphabet (24) a whole act may cite more
  arguments than the thread ever did — the letters double (αα, ββ…) rather
  than fail.
- **The legend carries the referent, never the id** — the capped unit text
  when the state has one, a named absence when it does not (the same
  honesty rule as the thread legend, #2965).

The ids stay inside the evidence layer untouched: checks, rejections and
structured consumers keep reading ``arg_N`` — only the WRITER's view is
relabeled.
"""

import re
from typing import Dict, List, Mapping

from .cited_units import truncate_at_boundary

#: The machine id as it appears in evidence strings. The letter-lookalike
#: prefix boundary matters: ``larg_1`` (a French elision) must not match.
RAW_UNIT_ID_RE = re.compile(r"\barg_(\d+)\b")

#: #2896's thread alphabet, kept — the legend reads the same letters the
#: narrative thread used before the table generalised them.
_LETTERS = "αβγδεζηθικλμνξοπρστυφχψω"

#: The legend referent cap: enough to recognise the passage, not enough to
#: smuggle a second copy of the corpus into the prompt budget.
LEGEND_REFERENT_CAP = 200

LEGEND_HEADING = "LÉGENDE DES DÉSIGNATIONS"

_LEGEND_INTRO = (
    "chaque lettre grecque désigne UN argument du corpus — l'identifiant "
    "machine arg_N n'apparaît plus dans ce prompt ; lis chaque lettre par "
    "cette légende :"
)

_LEGEND_MISSING = (
    "(texte non joint dans ce prompt — désigne-le par sa lettre, ne lui "
    "prête pas de texte)"
)


def _letter_for(index: int) -> str:
    """The index-th label: α..ω, then doubled (αα, ββ…) — a whole act can
    cite more arguments than the Greek alphabet holds; the thread never did."""
    cycle, offset = divmod(index, len(_LETTERS))
    return _LETTERS[offset] * (cycle + 1)


def collect_unit_ids(text: str) -> List[str]:
    """The distinct unit ids in ``text``, in order of first appearance —
    the deterministic letter-assignment order."""
    seen: Dict[str, None] = {}
    for match in RAW_UNIT_ID_RE.finditer(text):
        seen.setdefault(match.group(0), None)
    return list(seen)


def label_writer_prompt(
    prompt: str,
    unit_texts: Mapping[str, str],
    *,
    insert_before: str = "CONSIGNE DE RÉDACTION",
) -> str:
    """Relabel every ``arg_N`` in ``prompt`` with its per-act letter and
    insert the legend before ``insert_before``.

    A prompt with no unit id comes back unchanged — the acts legitimately
    carry none (Acte I never did, census) — so the caller's non-vacuity
    lives in its own assertions, not here.
    """
    ids = collect_unit_ids(prompt)
    if not ids:
        return prompt
    table = {unit_id: _letter_for(i) for i, unit_id in enumerate(ids)}
    labelled = RAW_UNIT_ID_RE.sub(lambda m: table[m.group(0)], prompt)

    lines = [f"{LEGEND_HEADING} — {_LEGEND_INTRO}"]
    for unit_id, letter in table.items():
        text = unit_texts.get(unit_id)
        referent = (
            truncate_at_boundary(str(text), LEGEND_REFERENT_CAP)
            if text
            else _LEGEND_MISSING
        )
        lines.append(f"  • {letter} : {referent}")
    legend = "\n".join(lines) + "\n\n"

    if insert_before and insert_before in labelled:
        return labelled.replace(insert_before, legend + insert_before, 1)
    return labelled.rstrip("\n") + "\n\n" + legend
