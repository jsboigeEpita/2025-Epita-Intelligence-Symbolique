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

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List

from .formal_derivation import is_real_formula

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
    # #3105 — the per-argument pass reads UNITS, not the document head.
    "fallacy_per_argument": "détection de sophismes — lecture par argument",
    # #3136 — the logic arms read a head for the vocabulary (pass 1) and
    # stratified UNITS for the formulas (pass 2): two readings, two sites.
    "fol_reasoning_units": "logique du premier ordre — lecture par unités",
    "propositional_logic_units": "logique propositionnelle — lecture par unités",
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
    # #3105 — a units-reading site (the per-argument pass) speaks in units
    # and span, not in a document head: "5 unités sur 10" says how much of
    # the population it read, ``span_lo``/``span_hi`` where those units sit.
    units: int = 0
    unit_total: int = 0
    span_lo: int = 0
    span_hi: int = 0


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


def _fallacy_counts(state: Any) -> "tuple[Dict[str, int], int, int]":
    """#3105 — how the state's retained fallacies split across the paths.

    Returns ``(per_path, untagged, shared)`` from each entry's
    ``detection_paths`` tag. An entry the merge never tagged (a legacy
    state, or a writer that dropped the tag) is counted as ``untagged``,
    never credited to a path — crediting the total to the descent is the
    #3105 defect itself.
    """
    per_path: Dict[str, int] = {}
    untagged = 0
    shared = 0
    fallacies = getattr(state, "identified_fallacies", None) or {}
    entries = fallacies.values() if isinstance(fallacies, dict) else fallacies
    for f in entries:
        paths = f.get("detection_paths") if isinstance(f, dict) else None
        if not isinstance(paths, list) or not paths:
            untagged += 1
            continue
        seen = {str(p) for p in paths}
        if len(seen) > 1:
            shared += 1
        for p in seen:
            per_path[p] = per_path.get(p, 0) + 1
    return per_path, untagged, shared


def _count_fr(n: int) -> str:
    """« 1 retenu » / « 3 retenus » / « 0 retenu »."""
    return f"{n} retenu" + ("s" if n > 1 else "")


def _fallacy_fed(site: str, state: Any) -> str:
    """#3105 — one fallacy site's OWN share, from the state's tags."""
    per_path, untagged, shared = _fallacy_counts(state)
    n = per_path.get(site, 0)
    if site == "fallacy_descent":
        base = (
            "les procédés confirmés de la détection de sophismes " f"({_count_fr(n)})"
        )
        other = "la lecture par argument"
    elif site == "fallacy_one_shot":
        base = f"le repli en un appel de la détection de sophismes ({_count_fr(n)})"
        other = "la lecture par argument"
    else:
        base = f"les procédés retenus de la lecture par argument ({_count_fr(n)})"
        other = "la descente"
    if shared:
        base += f" — dont {shared} partagé{'s' if shared > 1 else ''} avec {other}"
    if untagged and site == "fallacy_descent":
        # Legacy states carry no tag: say how many are unattributed rather
        # than let the descent absorb them silently (R1101 dump).
        base += f" — {untagged} sans origine enregistrée"
    return base


# #3149 — the field that carries a logic record's verdict, per axis. A value
# that is not a bool is the #2970 « not evaluated » shape: no verdict.
_VERDICT_KEY = {
    "propositional_analysis_results": "satisfiable",
    "fol_analysis_results": "consistent",
}


def _formula_source_counts(state: Any, attribute: str) -> "tuple[int, int]":
    """#3136 — how many of a logic leg's formulas name the units they came from.

    ``formula_sources`` is aligned with ``formulas`` (#3107/#3122): entry *i*
    names the unit id(s) the formula was translated from, an empty list when
    the formula came from the head's wide pass or from an upstream
    translation. Returns ``(sourced, total)`` — the count the units line
    credits, never the whole population.

    #3149 — the counting population is the DECIDED records over their REAL
    formulas. A ``satisfiable``/``consistent`` of ``None`` is an « not
    evaluated » record (#2970) carrying no verdict, and its one string is a
    writer placeholder, not a tested formula; counting both inflated the line
    to « 30 sur 32 ... 3 verdicts » where the state held 30 formulas and one
    verdict. The placeholder predicate is the shared one
    (:func:`formal_derivation.is_real_formula`), never a second copy.
    """
    verdict_key = _VERDICT_KEY[attribute]
    sourced = 0
    total = 0
    for result in getattr(state, attribute, None) or []:
        if not isinstance(result, dict):
            continue
        if not isinstance(result.get(verdict_key), bool):
            continue  # not evaluated: no verdict, no tested formula
        formulas = result.get("formulas") or []
        sources = result.get("formula_sources") or []
        for index, formula in enumerate(formulas):
            if not isinstance(formula, str) or not is_real_formula(formula):
                continue
            total += 1
            if index < len(sources) and sources[index]:
                sourced += 1
    return sourced, total


def _decided_verdicts(state: Any, attribute: str) -> int:
    """#3149 — records that carry a VERDICT (a bool), not a #2970 placeholder."""
    verdict_key = _VERDICT_KEY[attribute]
    return sum(
        1
        for result in getattr(state, attribute, None) or []
        if isinstance(result, dict) and isinstance(result.get(verdict_key), bool)
    )


def _head_formula_extras(state: Any, site: str) -> int:
    """#3136 — formulas the head's wide pass produced, when the arm recorded
    them on the head site (the PL wide-net pass reads the same head)."""
    table = getattr(state, "reading_window_status", None) or {}
    entry = table.get(site) if isinstance(table, dict) else None
    if not isinstance(entry, dict):
        return 0
    extras = entry.get("head_formulas")
    return extras if isinstance(extras, int) and not isinstance(extras, bool) else 0


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
    # #3136 — the head reads fix the VOCABULARY; the formulas come from the
    # units site below. Crediting the verdicts here is the #3105 defect on
    # the logic axis: the formulas cite units spread across the text, which
    # a 4000-char head cannot have produced.
    if site == "propositional_logic":
        base = (
            "l'inventaire des atomes propositionnels — le vocabulaire des "
            "formules, jamais leur contenu"
        )
        extras = _head_formula_extras(state, site)
        if extras:
            base += (
                f" — plus {extras} formule(s) de structure globale lue(s) "
                "sur cette fenêtre"
            )
        return base
    if site == "fol_reasoning":
        return (
            "la signature FOL — sorts, prédicats et constantes — le "
            "vocabulaire employé par les formules, jamais les formules"
        )
    if site in ("propositional_logic_units", "fol_reasoning_units"):
        fol = site == "fol_reasoning_units"
        attribute = "fol_analysis_results" if fol else "propositional_analysis_results"
        name = "la traduction FOL" if fol else "la traduction propositionnelle"
        n = _decided_verdicts(state, attribute)
        sourced, total = _formula_source_counts(state, attribute)
        if total:
            return (
                f"{name} ({sourced} formule(s) sur {total} issues des unités "
                f"lues) et ses {n} verdict(s) formel(s)"
            )
        return f"{name} et ses {n} verdict(s) formel(s)"
    if site == "fallacy_widenet":
        return "les candidats de la détection de sophismes (phase large filet)"
    if site in ("fallacy_descent", "fallacy_one_shot", "fallacy_per_argument"):
        return _fallacy_fed(site, state)
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
                    units=int(entry.get("units", 0) or 0),
                    unit_total=int(entry.get("unit_total", 0) or 0),
                    span_lo=int(entry.get("span_lo", 0) or 0),
                    span_hi=int(entry.get("span_hi", 0) or 0),
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
    elif line.units and line.unit_total and 0 < source_chars:
        # #3105 — a units-reading site: it read units, not a document head,
        # and says both how many and where they sit.
        if line.span_hi or line.span_lo:
            span = (
                f"étendue {line.span_lo / source_chars:.2f}–"
                f"{line.span_hi / source_chars:.2f} du texte"
            )
        else:
            span = "étendue non dite"
        base = (
            f"« {label} » : {line.units} unités sur {line.unit_total} lues " f"({span})"
        )
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


# #3134 — the reader-facing bounds passage. The R1105b render (Sonnet) wove
# the three fallacy lines into one "initial detection" carrying the descent's
# 500; Haiku had them right; Opus quoted none. A bound that depends on which
# model paraphrases the record is not a bound the pipeline guarantees — so the
# numbers the reader receives are the record's own lines, grafted AFTER the
# woven prose, and the prose restates none (``restated_bound_sentences``
# below removes any that does, #1605 enforcement shape: the record's sentence
# replaces the woven one, the event is logged, never a reader note).
READER_BOUNDS_HEADING = "Bornes de lecture du run (enregistrement #1737)"


def format_reader_bounds_passage(record: ReadingRecord) -> str:
    """The bounds passage the acts graft after their prose — record only.

    Empty when nothing was recorded: the rule's absent case (no line → no
    bound) extends to the passage itself.
    """
    if not record.lines:
        return ""
    lines = "\n".join(
        f"- {format_reading_line(ln, record.source_chars)}" for ln in record.lines
    )
    passage = f"**{READER_BOUNDS_HEADING}**\n{lines}"
    if record.basis:
        passage += f"\n- {record.basis}"
    return passage


#: A numeric reading-bound shape: "500 des 12000 caractères", "4000 caractères",
#: "10 unités sur 91". French only — the acts and the record speak French.
_BOUND_SHAPE = re.compile(
    r"\d+\s+(?:des\s+\d+\s+)?(?:caractères?|unités?\s+sur\s+\d+)",
    re.IGNORECASE,
)

#: A word naming a bounded READING (a site of the record). The shape alone
#: would also catch a document length (« un discours de 12000 caractères ») —
#: the measured object there is the document, not a reading.
_READING_WORD = re.compile(
    r"détection|lecture|extraction|traduction|logique|filet|descente|repli",
    re.IGNORECASE,
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def restated_bound_sentences(text: str) -> List[str]:
    """The woven sentences that restate a numeric reading bound (#3134).

    A sentence is restating a bound when it carries BOTH a bound shape
    (a character or unit count in the record's grammar) and a reading word.
    The caller removes them from the prose — the reader-facing bounds are
    the record's passage, where each number sits under its own site label.
    """
    caught: List[str] = []
    for sentence in _SENTENCE_SPLIT.split(text or ""):
        sentence = sentence.strip()
        if not sentence:
            continue
        if _BOUND_SHAPE.search(sentence) and _READING_WORD.search(sentence):
            caught.append(sentence)
    return caught


# The naming contract every grafting act carries, from this one constant.
# Its absent case forbids invention: no recorded line → no bound to quote,
# never a fabricated one. The reader receives woven bounds, never the table.
# #3094 — the rule offers no template phrase: the R1101 render copied the
# old example (« sur le début du document… ») verbatim into its sentence.
# The sentence now comes from the record's own lines, which name what each
# bound fed, and from the basis line, which says what the rest rests on.
# #3134 — and it comes from the pipeline, not from the model: no character
# or unit count is restated by the prose, the passage grafted after the
# text carries the record's lines as they are.
READING_BASIS_RULE = (
    "- LES BORNES DE LECTURE SE DISENT PAR LES LIGNES LECTURES DU RUN ci-dessus :\n"
    "  une ligne « lecture de k des N caractères » dit que le spécialiste a lu\n"
    "  k caractères, et dit CE QU'ELLE A ALIMENTÉ — la borne ne pèse que sur\n"
    "  ces résultats-là, jamais sur les autres. La ligne BASE DU RUN dit sur\n"
    "  quoi repose le reste du run (unités du texte entier, ou seule\n"
    "  l'ouverture). Le récit ne présente JAMAIS une lecture bornée comme\n"
    "  celle du document entier. Aucune ligne → aucune borne à citer : n'en\n"
    "  fabrique aucune.\n"
    "- NE REFORMULE AUCUN CHIFFRE DE BORNE DANS TA PROSE : aucun compte de\n"
    "  caractères ou d'unités ne sort de toi. Le passage « Bornes de lecture\n"
    "  du run », ajouté après ton texte, porte les lignes de l'enregistrement\n"
    "  telles quelles — chaque borne sous l'étiquette de son site. Ta prose\n"
    "  peut NOMMER ce que chaque lecture a alimenté ; les nombres viennent du\n"
    "  passage, jamais de toi."
)
