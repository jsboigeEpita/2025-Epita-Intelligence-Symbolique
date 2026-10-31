"""#3073 — the discursive arena as ONE record with its provenance, shared by Acts I and III.

The arena has two producers. ``state.source_metadata`` is the corpus side — the
run recorded it, so it is a documented fact; on the measured document the
metadata carries no arena key at all (its four keys all read ``unknown``).
``state.stakes_and_stakeholders["discursive_arena"]`` is the stakes extractor's
reading of the text — an LLM inference.

Acte I printed the inference under a block headed ``DONNÉES VERIFIÉES DANS LE
STATE`` (the writer then repeated "verified", as instructed), while Acte III —
reading ``source_metadata`` only — told the reader the source documents neither
the speaker nor the arena type. One fact, two containers, and the inferred one
mislabelled.

This module resolves the two producers into a single record and renders the one
line both acts quote, so they agree **by construction**: same value, same
provenance tag, from a single formatter. A documented arena beats an inferred
one; an arena recorded as ``unknown`` documents nothing; nothing anywhere →
said absent, never invented.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Provenance classes. The labels the prompts render come from these, so the two
# acts cannot drift into two contracts.
PROVENANCE_METADATA = "source_metadata"
PROVENANCE_INFERRED = "inferred_from_text"

# The metadata keys that document an arena. ``venue`` is the political
# vocabulary's own field — ``stakes_extractor`` reads Speaker/venue/topic/era,
# and the #2845 witness builds its arena from ``venue``; ``arena`` and
# ``discursive_arena`` are the generic spellings.
_ARENA_METADATA_KEYS = ("arena", "discursive_arena", "venue")

# Values that look like a field but document nothing: the measured document's
# ``source_metadata`` carries four keys, all reading ``unknown`` — none of them
# documents the arena, and a reader must not be told it does.
_NOT_DOCUMENTED = frozenset(
    {
        "",
        "unknown",
        "inconnu",
        "inconnue",
        "n/a",
        "na",
        "none",
        "null",
        "nan",
        "-",
        "—",
        "non renseigné",
        "non renseignée",
        "not documented",
        "undocumented",
    }
)

# Same cap as the acts' ``_META_CAP``: the record is quoted by both acts, so it
# is truncated once, here, and the two prompts cannot diverge on its extent.
ARENA_CAP = 160

_LABEL_METADATA = "métadonnée enregistrée"
_LABEL_INFERRED = (
    "INFÉRÉE du texte par l'extracteur d'enjeux — jamais une donnée vérifiée"
)


@dataclass
class ArenaRecord:
    """The arena with its provenance — the single container Acts I and III read.

    ``source_key`` names where the value came from (``source_metadata.venue``,
    ``discursive_arena``); empty on an absent record.
    """

    value: str = ""
    provenance: str = ""  # PROVENANCE_METADATA | PROVENANCE_INFERRED | ""
    source_key: str = ""


def _cap(text: str) -> str:
    return text if len(text) <= ARENA_CAP else text[: ARENA_CAP - 6].rstrip() + " […]"


def _documents(value: Any) -> bool:
    text = str(value or "").strip()
    return bool(text) and text.lower() not in _NOT_DOCUMENTED


def build_arena_record(state: Any) -> ArenaRecord:
    """Resolve the state's two arena producers into one record (no LLM).

    Metadata first: when the corpus documents the arena, that is the record —
    the producer's own note travels in ``source_key``. Otherwise the stakes
    extractor's reading is the record, labelled as the inference it is.
    """
    metadata = getattr(state, "source_metadata", {}) or {}
    if isinstance(metadata, dict):
        for key in _ARENA_METADATA_KEYS:
            value = str(metadata.get(key, "") or "").strip()
            if _documents(value):
                return ArenaRecord(
                    value=_cap(value),
                    provenance=PROVENANCE_METADATA,
                    source_key=f"source_metadata.{key}",
                )
    stakes = getattr(state, "stakes_and_stakeholders", {}) or {}
    if isinstance(stakes, dict):
        value = str(stakes.get("discursive_arena", "") or "").strip()
        if value:
            return ArenaRecord(
                value=_cap(value),
                provenance=PROVENANCE_INFERRED,
                source_key="discursive_arena",
            )
    return ArenaRecord()


def format_arena_line(record: ArenaRecord) -> str:
    """The ONE line both acts render — same value, same tag, by construction."""
    if not record.value:
        return (
            "Arène discursive : (non renseignée — ni en métadonnée, ni inférée "
            "du texte par l'extracteur d'enjeux)"
        )
    if record.provenance == PROVENANCE_METADATA:
        # #3311 — the writer reads the provenance CLASS (enregistrée vs
        # inférée), never the internal dotted path that carried it;
        # ``source_key`` stays on the record for tests and debugging.
        return f"Arène discursive : {record.value} " f"(provenance : {_LABEL_METADATA})"
    return f"Arène discursive : {record.value} " f"(provenance : {_LABEL_INFERRED})"
