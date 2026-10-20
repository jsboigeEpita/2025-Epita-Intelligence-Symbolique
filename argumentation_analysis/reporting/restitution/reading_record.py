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
from typing import Any, Dict, List

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
    # #2850 lot 7 — the fallacy workflow's document-path windows.
    "fallacy_widenet": "détection de sophismes — large filet",
    "fallacy_descent": "détection de sophismes — descente",
    "fallacy_one_shot": "détection de sophismes — repli en un appel",
}

# The French label a reader understands, per producer of the run's units —
# one table, the way sites have theirs (#3099 rework). A producer the table
# does not carry keeps its raw id rather than being dropped: an unnamed
# producer still counts, and the id stays traceable to its wiring point.
PRODUCER_LABELS_FR = {
    "llm_extract": "extraction LLM",
    "kb_heuristic": "découpage heuristique",
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
    # #3094 — what the read fed, counts from the state's own tables. The
    # R1101 render attached a head bound to judgments produced mid-document
    # by whole-unit specialists: a line that names its own results lets the
    # narrative tie the bound to them, and to nothing else.
    fed: str = ""


@dataclass
class ReadingRecord:
    """Every bounded reading the run recorded, plus the document's length.

    ``lines`` is empty when nothing recorded — the acts then graft no block
    and invent no bound (the rule says exactly that). ``basis`` is the run's
    whole-text basis (#3094): what the per-unit specialists worked on, so a
    prompt that carries bounded reads cannot let them stand for the run."""

    lines: List[ReadingLine] = field(default_factory=list)
    source_chars: int = 0
    basis: str = ""

    @property
    def truncated_lines(self) -> List[ReadingLine]:
        """The lines whose window actually bounds the document (k < N)."""
        return [
            ln
            for ln in self.lines
            if ln.status == "selected" and 0 < ln.window < self.source_chars
        ]


def _site_fed(site: str, state: Any) -> str:
    """#3094 — what one bounded read fed, counts from the run's state.

    The capability→results linkage is structural (this resolver); the counts
    are the run's own — never a hand-kept per-run list. Sites whose results
    the state does not count keep their capability name alone."""
    if site == "fact_extraction":
        prov = getattr(state, "argument_provenance", None)
        if isinstance(prov, dict) and prov:
            llm = sum(
                1
                for p in prov.values()
                if isinstance(p, dict) and str(p.get("producer", "")) == "llm_extract"
            )
            return f"l'extraction LLM ({llm} unités sur {len(prov)})"
        return "l'extraction LLM (population non enregistrée)"
    if site == "propositional_logic":
        n = len(getattr(state, "propositional_analysis_results", None) or [])
        return f"la traduction propositionnelle et ses {n} verdict(s) formel(s)"
    if site == "fol_reasoning":
        n = len(getattr(state, "fol_analysis_results", None) or [])
        return f"la traduction FOL et ses {n} verdict(s) formel(s)"
    if site == "fallacy_widenet":
        return "les candidats de la détection de sophismes (phase large filet)"
    if site == "fallacy_descent":
        n = len(getattr(state, "identified_fallacies", None) or {})
        return "les procédés confirmés de la détection de sophismes " f"({n} retenus)"
    if site == "fallacy_one_shot":
        return "le repli en un appel de la détection de sophismes"
    if site == "counter_argument":
        n = len(getattr(state, "counter_arguments", None) or [])
        return f"la contre-argumentation ({n} contre-argument(s))"
    if site == "governance":
        n = len(getattr(state, "governance_decisions", None) or [])
        return f"la délibération de gouvernance ({n} décision(s))"
    if site == "collaborative_debate":
        return "le débat collaboratif"
    return ""


def _whole_text_basis(state: Any, source_chars: int) -> str:
    """#3094 — the run's whole-text basis, from the provenance table.

    The R1101 render said the reading "ne porte que sur une portion limitée"
    and widened it to every conclusion — while 83 of 89 units were anchored
    across the whole text by another producer. A block that lists only
    bounded reads invites that generalization; this line says what the
    per-unit material actually is (units, producers, bands, span). No
    provenance at all → the basis IS the opening, said, never guessed."""
    prov = getattr(state, "argument_provenance", None)
    if not isinstance(prov, dict) or not prov:
        return (
            "BASE DU RUN : l'ouverture du document — aucune unité analysée "
            "au-delà des lectures bornées ci-dessus"
        )
    by_prod: Dict[str, int] = {}
    offsets: List[int] = []
    for p in prov.values():
        if not isinstance(p, dict):
            continue
        prod = str(p.get("producer", "inconnu"))
        by_prod[prod] = by_prod.get(prod, 0) + 1
        off = p.get("offset")
        if isinstance(off, int) and not isinstance(off, bool) and off >= 0:
            offsets.append(off)
    parts = " + ".join(
        f"{v} {PRODUCER_LABELS_FR.get(k, k)}" for k, v in sorted(by_prod.items())
    )
    head = f"BASE DU RUN : {len(prov)} unités ({parts})"
    if not offsets or source_chars <= 0:
        # Unanchored units make no span claim — « texte entier » would be a
        # label stronger than its own measurement (#3099 rework).
        return f"{head} (aucune unité ancrée : étendue non dite)"
    bands = len({min(off * 3 // source_chars, 2) for off in offsets})
    span_lo = min(offsets) / source_chars
    span_hi = max(offsets) / source_chars
    if bands >= 3:
        # The whole-text claim is earned by the measurement alone: 3/3 bands.
        return (
            f"{head} SUR LE TEXTE ENTIER, "
            f"{bands}/3 bandes, étendue {span_lo:.2f}–{span_hi:.2f}"
        )
    return f"{head}, {bands}/3 bandes, étendue {span_lo:.2f}–{span_hi:.2f}"


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
                    fed=_site_fed(str(site), state),
                )
            )
    record.basis = _whole_text_basis(state, record.source_chars)
    return record


def format_reading_line(line: ReadingLine, source_chars: int) -> str:
    """The ONE phrasing every act quotes for one site — counts only."""
    label = SITE_LABELS_FR.get(line.site, line.site)
    if line.status != "selected":
        phrase = _STATUS_PHRASES_FR.get(line.status, line.status)
        base = f"« {label} » : {phrase}"
    elif 0 < source_chars and line.window >= source_chars:
        base = (
            f"« {label} » : document lu en entier "
            f"({line.window} de {source_chars} caractères)"
        )
    elif line.offset:
        base = (
            f"« {label} » : lecture de {line.window} des {source_chars} "
            f"caractères (décalage {line.offset})"
        )
    else:
        base = f"« {label} » : lecture de {line.window} des {source_chars} caractères"
    if line.fed:
        base += f" — a alimenté : {line.fed}"
    return base


def format_reading_block(record: ReadingRecord) -> str:
    """The block the acts graft — empty string when nothing recorded."""
    if not record.lines:
        return ""
    lines = "\n".join(
        f"  {format_reading_line(ln, record.source_chars)}" for ln in record.lines
    )
    block = f"[LECTURES DU RUN — bornes réelles, enregistrement #1737]\n{lines}"
    if record.basis:
        block += f"\n  {record.basis}"
    return block


# The naming contract every grafting act carries, from this one constant.
# Its absent case forbids invention: no recorded line → no bound to quote,
# never a fabricated one. The reader receives woven bounds, never the table.
# #3094 — the rule offers no template phrase: the R1101 render copied the
# old example (« sur le début du document… ») verbatim into its sentence.
# The sentence now comes from the record's own lines, which name what each
# bound fed, and from the basis line, which says what the rest rests on.
READING_BASIS_RULE = (
    "- LES BORNES DE LECTURE SE DISENT PAR LES LIGNES LECTURES DU RUN ci-dessus :\n"
    "  une ligne « lecture de k des N caractères » dit que le spécialiste a lu\n"
    "  k caractères, et dit CE QU'ELLE A ALIMENTÉ — la borne ne pèse que sur\n"
    "  ces résultats-là, jamais sur les autres. La ligne BASE DU RUN dit sur\n"
    "  quoi repose le reste du run (unités du texte entier, ou seule\n"
    "  l'ouverture). Le récit ne présente JAMAIS une lecture bornée comme\n"
    "  celle du document entier. Aucune ligne → aucune borne à citer : n'en\n"
    "  fabrique aucune."
)
