"""#2850 lot 6 — the run's bounded readings as ONE record, read by Acts II and III.

The trace has spoken the reading windows since lot 4 (``Lecture : k des N``)
and the #1737 table (``state.reading_window_status``) records every selection
the state-carrying sites make — but no restitution act ever read either: a
reader of the acts could not learn that the specialists read a bounded head
of the document (#2850's "Acts silent" family). This module resolves the
recorded selections into a single record and renders the lines the acts
quote — counts only, never source text — carrying the #1737 tri-state
statuses, because a status nobody reads is the #1019 shape.

Mirror of ``speaker_record`` (#3082): one builder from the state (no LLM),
one formatter, one rule constant — the acts that graft the block agree by
construction, and the stateless surfaces that cannot reach the state keep
their payload-side basis (their reader is their result, not the acts).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List

# The French label a reader understands, per recorded site. A site the table
# carries but this map does not (a new wiring point) renders under its raw
# name rather than being dropped — an unnamed reading still speaks.
SITE_LABELS_FR = {
    "fact_extraction": "extraction des unités",
    "propositional_logic": "logique propositionnelle",
    "fol_reasoning": "logique du premier ordre",
    "governance": "délibération de gouvernance",
    "counter_argument": "contre-argumentation",
    "collaborative_debate": "débat collaboratif",
}

# The non-selected statuses #1737 defines, in the reader's words.
_STATUS_PHRASES_FR = {
    "no_punctuated_span_found": (
        "aucun segment ponctué de la taille de la fenêtre n'a été trouvé — "
        "la lecture a renoncé plutôt que de couper au milieu d'une phrase"
    ),
    "empty_input": "aucun texte à lire",
    "short_input": "texte plus court que la fenêtre — lu en entier",
}


@dataclass
class ReadingLine:
    """One site's recorded selection — counts only."""

    site: str = ""
    status: str = ""
    offset: int = 0
    window: int = 0


@dataclass
class ReadingRecord:
    """Every bounded reading the run recorded, plus the document's length.

    ``lines`` is empty when nothing recorded — the acts then graft no block
    and invent no bound (the rule says exactly that)."""

    lines: List[ReadingLine] = field(default_factory=list)
    source_chars: int = 0

    @property
    def truncated_lines(self) -> List[ReadingLine]:
        """The lines whose window actually bounds the document (k < N)."""
        return [
            ln
            for ln in self.lines
            if ln.status == "selected" and 0 < ln.window < self.source_chars
        ]


def build_reading_record(state: Any) -> ReadingRecord:
    """Resolve the state's recorded selections into one record (no LLM)."""
    record = ReadingRecord(source_chars=len(getattr(state, "raw_text", "") or ""))
    table = getattr(state, "reading_window_status", {}) or {}
    if isinstance(table, dict):
        for site, entry in sorted(table.items()):
            if not isinstance(entry, dict):
                continue
            record.lines.append(
                ReadingLine(
                    site=str(site),
                    status=str(entry.get("status", "") or ""),
                    offset=int(entry.get("offset", 0) or 0),
                    window=int(entry.get("window", 0) or 0),
                )
            )
    return record


def format_reading_line(line: ReadingLine, source_chars: int) -> str:
    """The ONE phrasing every act quotes for one site — counts only."""
    label = SITE_LABELS_FR.get(line.site, line.site)
    if line.status != "selected":
        phrase = _STATUS_PHRASES_FR.get(line.status, line.status)
        return f"« {label} » : {phrase}"
    if 0 < source_chars and line.window >= source_chars:
        return (
            f"« {label} » : document lu en entier "
            f"({line.window} de {source_chars} caractères)"
        )
    if line.offset:
        return (
            f"« {label} » : lecture de {line.window} des {source_chars} "
            f"caractères (décalage {line.offset})"
        )
    return f"« {label} » : lecture de {line.window} des {source_chars} caractères"


def format_reading_block(record: ReadingRecord) -> str:
    """The block the acts graft — empty string when nothing recorded."""
    if not record.lines:
        return ""
    lines = "\n".join(
        f"  {format_reading_line(ln, record.source_chars)}" for ln in record.lines
    )
    return f"[LECTURES DU RUN — bornes réelles, enregistrement #1737]\n{lines}"


# The naming contract every grafting act carries, from this one constant.
# Its absent case forbids invention: no recorded line → no bound to quote,
# never a fabricated one. The reader receives woven bounds, never the table.
READING_BASIS_RULE = (
    "- LES BORNES DE LECTURE SE DISENT PAR LES LIGNES LECTURES DU RUN ci-dessus :\n"
    "  une ligne « lecture de k des N caractères » dit que le spécialiste a lu\n"
    "  k caractères — le récit ne présente JAMAIS cette lecture comme celle du\n"
    "  document entier, et tient la borne au français courant quand elle pèse\n"
    "  sur un jugement (« sur le début du document… »). Aucune ligne → aucune\n"
    "  borne à citer : n'en fabrique aucune."
)
