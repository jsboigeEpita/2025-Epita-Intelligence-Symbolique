# -*- coding: utf-8 -*-
"""#2896 (d)+(f): no raw ``arg_N`` in the Act II sequence block, and the
sequence moves are spread over the text.

The paid run's Act II printed « Plus loin, ``arg_40`` tente de… » : the
sequence block uses ``m.arg_ref`` — an opaque machine id — as the ACTOR of
each narrated move, and the narrator echoes it verbatim. Opaque ids stay
legitimate in the structured data blocks (the Dung trace anchors, #1280);
the narrative thread refers to its actors by a stable non-id label.

(f): the 8 narrated moves come from the same ``select_for_budget`` —
replayed on the dump the picks left a 0.41 stretch holding 23 anchored
moves. The stretch bound applies to this selection too.
"""

import re

from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    Act2Evidence,
    build_act2_prompt,
)
from argumentation_analysis.reporting.restitution.text_sequence import (
    TextSequence,
    TraceMove,
)

_SOURCE = 30_000


def _moves_head_dense():
    """60 anchored moves spread THROUGH each third (the dump's shape: 61
    anchored moves spanning 0.00–0.97 — the 0.41 stretch HELD 23 moves the
    picks skipped; a population of head-only moves would make the gap
    irreducible and the witness would measure nothing)."""
    moves = []
    n = 0
    for band_start in (0, 10_000, 20_000):
        for j in range(20):
            n += 1
            moves.append(
                TraceMove(
                    move="assert" if j % 2 == 0 else "retract",
                    offset=band_start + j * 500,
                    length=40,
                    arg_ref=f"arg_{n}",
                )
            )
    return moves


def _evidence(moves):
    return Act2Evidence(
        text_sequence=TextSequence(moves=tuple(moves), order_differs=None),
        source_length=_SOURCE,
    )


def _sequence_block(prompt):
    m = re.search(r"SÉQUENCE DU TEXTE.*?(?=\n\n)", prompt, re.DOTALL)
    assert m is not None, "prompt carries no sequence block"
    return m.group(0)


def test_sequence_block_prints_no_raw_arg_id():
    """(d) witness: the sequence block refers to actors without the raw
    ``arg_N`` machine id (born red: today's block prints 'arg_1 — pose …')."""
    prompt = build_act2_prompt(_evidence(_moves_head_dense()))
    block = _sequence_block(prompt)
    assert not re.search(r"arg_\d+", block), (
        "the Act II sequence block prints a raw arg_N id — the narrator "
        f"echoes it into the prose: {block.splitlines()[1][:80]!r}"
    )


def test_narrated_moves_are_spread():
    """(f) witness: the 8 narrated moves leave no uncovered stretch over
    a third of the text (head-picks leave ~0.31 here; the spread brings
    the largest gap under 0.25)."""
    prompt = build_act2_prompt(_evidence(_moves_head_dense()))
    block = _sequence_block(prompt)
    offsets = sorted(int(m) for m in re.findall(r"offset (\d+)", block))
    assert len(offsets) == 8, f"expected 8 narrated moves, got {len(offsets)}"

    edges = [offsets[0] - 0]
    edges += [b - a for a, b in zip(offsets, offsets[1:])]
    edges.append(_SOURCE - offsets[-1])
    gap = max(edges) / _SOURCE
    assert gap <= 0.25, (
        f"narrated moves leave a {gap:.3f} uncovered stretch — the Act II "
        "thread still reads only each band's head"
    )
