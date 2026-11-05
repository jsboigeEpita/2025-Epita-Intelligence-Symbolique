"""#3442 (follow-up) — a pillar whose kind is unreadable is a CLAIM, never « autre ».

The coordinator's ask, verbatim: « `kind: "other"` → `claim` dans le sauvetage
des piliers (#3442), la PR de suivi que tu as annoncée. »

The mapping itself landed with #3442 (`first_reading.py`, the pillar loop of
``build_first_reading``): a pillar the model labelled ``other`` — or with a
word outside the closed vocabulary, or with no kind at all — is recorded as a
``claim``, because the kind is a hint, not a verdict, and refusing the
passage would lose what the thesis rests on. What #3442 did NOT leave behind
is a witness: nothing pinned the mapping, so a regression would silently
print the pillar under « autre » in the reading note.

This file is that witness. It also pins the SCOPE of the mapping: a local move
labelled ``other`` stays ``other`` (#3029's honest absence) — the repair must
not launder the closed vocabulary for the rest of the reading.

Synthetic: invented text, no LLM (the callable is a stub), no JVM, no corpus.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from argumentation_analysis.agents.core.reading.first_reading import (
    build_first_reading,
)

#: The document the stub "read". Every quote below is a substring of it, so
#: each move clears the citation rule and reaches the state.
_DOCUMENT = (
    "Le dispositif repose sur une clause de revue annuelle. "
    "Le rapport cite une etude de 2019. "
    "L'auteur concede que le cout augmente chaque annee."
)

_CLAUSE = "une clause de revue annuelle"
_ETUDE = "une etude de 2019"
_CONCESSION = "le cout augmente chaque annee"


def _pillar(reading: str, quote: str, kind: object = "<absent>") -> dict:
    pillar: dict = {"reading": reading, "quote": quote}
    if kind != "<absent>":
        pillar["kind"] = kind
    return pillar


async def _read(answer: dict):
    """One first reading over the stub answer, on the real parser path."""

    async def _stub(_prompt: str) -> str:
        return json.dumps(answer, ensure_ascii=False)

    state = SimpleNamespace(raw_text=_DOCUMENT)
    return await build_first_reading(state, llm_callable=_stub)


def _pillars(reading) -> list:
    return [m for m in reading.moves if m.slot == "pillar"]


@pytest.mark.parametrize(
    "kind, why",
    [
        ("other", "the model's own honest « other »"),
        ("raisonnement", "a word outside the closed vocabulary"),
        ("<absent>", "no kind at all"),
        (None, "a null kind"),
    ],
)
async def test_an_unreadable_pillar_kind_reads_as_claim(kind, why):
    reading = await _read(
        {"pillars": [_pillar("la clause de revue porte le dispositif", _CLAUSE, kind)]}
    )

    kept = _pillars(reading)
    assert len(kept) == 1, f"the pillar must survive ({why})"
    assert kept[0].kind == "claim", (
        f"{why}: a passage the thesis rests on is a claim — recording it as "
        "« other » would print it under « autre » in the reading note, and "
        "the passage is not a non-move"
    )


async def test_a_pillar_with_a_closed_vocabulary_kind_keeps_it():
    reading = await _read(
        {
            "pillars": [
                _pillar("l'auteur concede un cout croissant", _CONCESSION, "concession")
            ]
        }
    )

    kept = _pillars(reading)
    assert len(kept) == 1
    assert kept[0].kind == "concession", (
        "the mapping is a floor, not an overwrite: a kind the model DID name "
        "from the closed vocabulary is what the state records"
    )


async def test_a_local_move_labelled_other_stays_other():
    """Control — the repair is scoped to the pillar slot.

    A local move keeps #3029's honest absence: an unreadable kind is stated as
    ``other``, never promoted to a vocabulary word the model did not choose.
    Without this pin, "map other to claim" would drift into laundering every
    unreadable kind in the reading.
    """
    reading = await _read(
        {
            "moves": [
                {
                    "reading": "le rapport cite une étude",
                    "quote": _ETUDE,
                    "kind": "other",
                },
                {"reading": "le coût progresse", "quote": _CONCESSION, "kind": "zzz"},
            ]
        }
    )

    local = [m for m in reading.moves if not m.slot]
    assert [m.kind for m in local] == ["other", "other"], (
        "outside the pillar slot, an unreadable kind stays « other » — the "
        "mapping must not launder the closed vocabulary"
    )
