"""A whole-scope superlative needs a measured ranking to stand on (#3297).

## The gap this closes

#3159 gave Act II the measured quality ranking **with its base** and the
instruction « C'est le SEUL classement mesuré — aucun superlatif portant sur
« tout le discours » n'a de base ici » (``quality_ranking_line``). The
instruction was necessary and not sufficient: nothing read Act II after the
weaving, so the writer could break the rule and the pipeline could not tell.

R1125a (one paid pass) shipped « Ce résultat est décisif : cet appui reste le
plus fragile du dispositif. » — a superlative over the whole argument set,
with **no fragility ranking in the state**, and two paragraphs later the same
report gave another unit more convergent fragility. The report contradicted
itself.

The shape of the defect is #3134's: a rule the writer can comply with or
not, and no instrument to tell. This module is that instrument.

## The dictionary, measured before it was chosen

The pattern is the coordinator's census dictionary (comment 6523194792 on
#3297, 21 paid passes, 55 superlatives, 7 whole-scope, 4 unbacked):
``\\b(le|la|les) (plus|mieux|moins) <word>`` plus a whole-scope tail.

Measured locally on the stored states' own act strings (115 state files, 229
``act2_narrative`` / ``act3_conclusion`` strings — gitignored, never
published): **317 superlative heads, 46 whole-scope hits, 38 unbacked**. Two
measurement traps, each paid for in a wrong number on the way here:

* the head consumes **three** tokens. A four-token head swallows the tail
  itself (``du dispositif`` becomes the 4th word) and the whole-scope count
  collapses;
* the tail must be **attached** to the head — nothing but the noun may sit
  between them. A clause boundary between head and tail means the tail
  belongs to the next sentence (8 of the 46 local hits were exactly that:
  « C'est le point le plus fragile. Le dispositif repose sur lui »), and a
  window without the boundary rule counts sentences the writer never wrote.

An earlier census of mine counted 91 hits by cutting the rendered markdown
instead of the act strings — the cut ran Acte III into the per-argument
appendix, so it measured prose the check never reads. The 46 above is the
number on the strings the check actually receives.

## What is licensed, and what is not

A whole-scope superlative is **licensed** when the sentence itself carries
the ranking it rests on:

1. a **measured scope** — « de l'ensemble évalué » (the #3159 form): the
   claim names the population it ranks, not the whole report;
2. the **measured ranking** — the sentence quotes the ranking line's base
   (« 8 unités évaluées sur 90 »), so the reader sees how thin the base is,
   or names a ranked unit together with a ranking word (« classement »,
   « P1 », « en tête »… — the reader contract's own hierarchy vocabulary);
3. for Act III, the **P1-first hierarchy** — the sentence names a unit the
   salience assessment ranks first (``licensed_ids``). Criterion 4 of the
   reader contract REQUIRES a ranking marker in Act III, so this licence is
   not a courtesy: banning « le plus » there would redden the contract.

A **quantifier** is not a ranking and is excluded by construction: « la plus
grande **partie** du discours » states a share, not a rank. The noun right
after the head decides. A superlative inside a « … » quotation is the
speaker's words, not the report's claim — excluded too.

Anti-pendulum: nothing here bans « le plus ». The check only ever reports on
a superlative whose scope is the whole report and whose ranking is missing.

## Honesty contract (#1019)

The check only ever reports; it never needs an LLM and never rewrites the
prose. With no body, it returns PASS silently. The motive the caller records
in the act's ``degraded`` map is a **code literal with counts, never a quote
of the prose**: ``restitution_acts_degraded`` is tolerated by the sanitizer
as a closed producer vocabulary (#3249 census), and a motif that quoted the
act would carry corpus text into that container — the sentence itself goes
to the trace log, which is where the neighbouring repairs already log their
excerpts.
"""

from __future__ import annotations

import re
from typing import Iterable, List, Optional, Sequence, Tuple

from .readability_gate import GateVerdict

#: The superlative head: « le plus <adj> », « la moins <adj> », « les mieux <adj> ».
#: Three tokens — a fourth swallows the tail (see the module docstring).
_SUPERLATIVE = re.compile(r"\b(le|la|les)\s+(plus|mieux|moins)\s+(\w+)", re.IGNORECASE)

#: The noun right after the head, read WITHOUT consuming it.
_NOUN_AFTER = re.compile(r"\s+(\w+)")

#: Whole-scope tails — the superlative's scope is the whole report.
_WHOLE_SCOPE_TAILS = (
    re.compile(r"du\s+dispositif", re.IGNORECASE),
    re.compile(r"du\s+discours", re.IGNORECASE),
    re.compile(r"du\s+texte", re.IGNORECASE),
    re.compile(r"de\s+tout\b", re.IGNORECASE),
    re.compile(r"de\s+l['’]ensemble\b", re.IGNORECASE),
)

#: A clause boundary — when one sits between the head and the tail, the tail
#: belongs to the next sentence and the hit is a false positive (measured:
#: 8 of the 46 local whole-scope hits).
_CLAUSE_BOUNDARY = re.compile(r"[.,;:!?\n]")

#: A « … » quotation span — the speaker's words, not the report's claim.
_QUOTED_SPAN = re.compile(r"«[^»]{0,400}»")

#: A MEASURED scope licenses the superlative: « de l'ensemble évalué » (#3159).
_MEASURED_SCOPE = re.compile(
    r"de\s+l['’]ensemble\s+(?:évalu|mesur|retenu|sélectionn|examin|considér|"
    r"evalu|evalue|mesure|selectionn|examine|considere)",
    re.IGNORECASE,
)

#: A QUANTIFIER is not a ranking: « la plus grande PARTIE », « le plus grand
#: NOMBRE ». Excluded by construction — the noun right after the head decides.
_QUANTIFIER_NOUNS = frozenset(
    {
        "partie",
        "fraction",
        "majorité",
        "majorite",
        "moitié",
        "moitie",
        "nombre",
        "proportion",
        "part",
        "portion",
        "lot",
        "ensemble",
        "fois",
        "cas",
    }
)

#: The measured ranking's own base — « 8 unités évaluées sur 90 ».
_RANKING_BASE = re.compile(r"\d+\s+unités\s+évaluées\s+sur\s+\d+", re.IGNORECASE)

#: The ranked unit ids, as the ranking line names them.
_RANKED_ID = re.compile(r"\barg_\d+\b")

#: The words that tie a unit id to the ranking it comes from — the reader
#: contract's own hierarchy vocabulary (``act_reader_contract_check``),
#: deliberately WITHOUT « le plus », which is the thing under judgement.
_RANKING_WORD = re.compile(
    r"\bclassement\b|\bP[123]\b|en\s+t[êe]te|dans\s+cet\s+ordre|hi[ée]rarchi",
    re.IGNORECASE,
)

#: How far the tail may sit from the head, in characters — the noun phrase
#: and its qualifiers, nothing more.
_TAIL_WINDOW = 60


def _unit_in(unit_id: str, sentence: str) -> bool:
    """Word-boundary membership — ``arg_1`` is not inside ``arg_15``."""
    return re.search(r"\b" + re.escape(unit_id) + r"\b", sentence) is not None


def _ranking_anchors(ranking_line: str) -> Tuple[Sequence[str], Sequence[str]]:
    """What a sentence must carry to rest on the measured ranking.

    The base figure (« 8 unités évaluées sur 90 ») and the ranked unit ids.
    Empty when there is no ranking line — the caller passes the line the act
    actually showed the writer, never a recomputed guess.
    """
    if not ranking_line:
        return (), ()
    return (
        _RANKING_BASE.findall(ranking_line),
        tuple(dict.fromkeys(_RANKED_ID.findall(ranking_line))),
    )


def _carries_ranking(sentence: str, bases: Sequence[str], ids: Sequence[str]) -> bool:
    """True when the sentence quotes the ranking it would rest on."""
    for base in bases:
        if base and base in sentence:
            return True
    if ids and _RANKING_WORD.search(sentence):
        return any(_unit_in(unit_id, sentence) for unit_id in ids)
    return False


def _names_licensed_unit(sentence: str, licensed_ids: Optional[Iterable[str]]) -> bool:
    """True when the sentence names a unit the run ranked first (Act III P1)."""
    if not licensed_ids:
        return False
    return any(unit_id and _unit_in(unit_id, sentence) for unit_id in licensed_ids)


def _is_quoted(body: str, index: int) -> bool:
    """True when ``index`` sits inside a « … » span."""
    return any(m.start() < index < m.end() for m in _QUOTED_SPAN.finditer(body))


def _sentence_of(body: str, index: int) -> str:
    """The sentence carrying ``index`` — for the licence tests and the report."""
    start = 0
    for stop in range(index, -1, -1):
        if body[stop] in ".!?;\n":
            start = stop + 1
            break
    end = len(body)
    for stop in range(index, len(body)):
        if body[stop] in ".!?;\n":
            end = stop + 1
            break
    return body[start:end]


def whole_scope_superlative_sentences(
    body: str,
    ranking_line: str = "",
    licensed_ids: Optional[Iterable[str]] = None,
) -> List[str]:
    """Whole-scope superlatives with no measured ranking behind them.

    Returned as exact slices of ``body``. Empty when there is none — the
    check is silent on everything else, including every superlative whose
    scope is not the whole report.
    """
    if not body:
        return []
    bases, ids = _ranking_anchors(ranking_line)
    hits: List[str] = []
    for match in _SUPERLATIVE.finditer(body):
        if _is_quoted(body, match.start()):
            continue  # the speaker's words, not the report's claim
        noun_match = _NOUN_AFTER.match(body, match.end())
        noun = noun_match.group(1).lower() if noun_match else ""
        if noun in _QUANTIFIER_NOUNS:
            # A share, not a rank — excluded by construction.
            continue
        window = body[match.end() : match.end() + _TAIL_WINDOW]
        tail_match = None
        for tail in _WHOLE_SCOPE_TAILS:
            found = tail.search(window)
            if found and (tail_match is None or found.start() < tail_match.start()):
                tail_match = found
        if tail_match is None:
            continue
        gap = body[match.end() : match.end() + tail_match.start()]
        if _CLAUSE_BOUNDARY.search(gap):
            continue  # the tail belongs to the next sentence, not to the head
        sentence = _sentence_of(body, match.start())
        if _MEASURED_SCOPE.search(sentence):
            continue
        if _carries_ranking(sentence, bases, ids):
            continue
        if _names_licensed_unit(sentence, licensed_ids):
            continue
        hits.append(sentence.strip())
    return hits


def check_whole_scope_superlative(
    body: str,
    ranking_line: str = "",
    licensed_ids: Optional[Iterable[str]] = None,
) -> GateVerdict:
    """Post-generation guarantee: a whole-scope superlative with no ranking.

    FAIL when the prose claims a rank over the whole report that no
    measurement backs. Silent PASS otherwise — including when the act has no
    ranking at all and the prose makes no such claim.

    The reasons carry the COUNT and the issue, never the sentence — the same
    rule `whole_scope_superlative_note` follows below: a verdict that quotes
    the act carries a corpus sentence onto a diagnostic surface the sanitizer
    does not police (#3249). The sentences themselves stay available to
    whoever wants them through `whole_scope_superlative_sentences`; the
    verdict does not have to be the place they leave the report (#3297).
    """
    flagged = whole_scope_superlative_sentences(
        body, ranking_line=ranking_line, licensed_ids=licensed_ids
    )
    if not flagged:
        return GateVerdict(band="PASS", reasons=[])
    plural = "s" if len(flagged) > 1 else ""
    reasons = [
        f"{len(flagged)} superlatif{plural} de portée globale sans classement "
        "mesuré pour l'adosser (#3297)"
    ]
    return GateVerdict(band="FAIL", reasons=reasons)


def whole_scope_superlative_note(
    body: str,
    ranking_line: str = "",
    licensed_ids: Optional[Iterable[str]] = None,
    act_label: str = "Acte II",
) -> str:
    """The motive recorded in the act's ``degraded`` map — empty when clean.

    The render is NOT rewritten: the reader sees the claim, and the report
    carries the reason the claim is unbacked. The motive is a code literal
    with a count, NEVER a quote of the prose — ``restitution_acts_degraded``
    is a closed producer vocabulary as far as the sanitizer is concerned
    (#3249), and quoting the act would carry corpus text into it. The
    sentence itself belongs on the trace log.
    """
    flagged = whole_scope_superlative_sentences(
        body, ranking_line=ranking_line, licensed_ids=licensed_ids
    )
    if not flagged:
        return ""
    plural = "s" if len(flagged) > 1 else ""
    return (
        f"{act_label} porte {len(flagged)} superlatif{plural} de portée globale "
        "sans classement mesuré pour l'adosser — la base du classement n'est "
        "pas dans l'acte (#3297)"
    )
