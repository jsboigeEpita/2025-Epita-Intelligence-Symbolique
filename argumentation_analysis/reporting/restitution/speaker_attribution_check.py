"""#3559 — the claim-attribution check (Act III's #3343 family).

A claim whose passage the document marks with a speaker tag must not be
handed to another party. The Act III prompt now carries that marker
(``claim_speakers``), and this check reads the WOVEN prose: a sentence
that quotes a marked claim's distinctive words while speaking of a party
whose marker it does not carry is flagged for the bounded retry — never
silently rewritten (#3317's calibration: the fix is the writer's own
rewrite, not a behind-the-reader edit).

The reader side is deliberately narrow: only a QUOTED fragment (the unit's
own words in « … », "…", or « … »/curly quotes) binds a sentence to a unit
— a paraphrase stays the writer's licence. Only a marker with a name form
(``NOM:``) or a dot form (``NOM.``) resolves to a party name; the name is
matched case-insensitively on word boundaries. A sentence that names no
party of a different marked claim stands, as does any unmarked claim.
"""

from __future__ import annotations

import re
from typing import Dict, List, Mapping

#: One sentence, French or English typography, with its terminator kept.
_SENTENCE_RE = re.compile(r"[^.!?]*[.!?]+[\"'”’)\]]*\s*|[^.!?]+\Z", re.M)

#: A quoted fragment of at least four words (a slogan or a claim's own
#: words; shorter quotes bind too loosely to attribute).
_QUOTED_RE = re.compile(r"[«\"“]([^»\"”]{8,}?)[»\"”]")

_WORD_RE = re.compile(r"[^\W\d_]+(?:[-'][^\W\d_]+)*", re.U)


def tag_party_name(tag: str) -> str:
    """The party name a speaker tag resolves to, ``""`` when it carries none.

    ``NOM:`` and ``NOM.`` both resolve to ``NOM``; anything else (a tag the
    #3623 convention would not read, an empty string) resolves to nothing.
    """
    raw = (tag or "").strip()
    if not raw:
        return ""
    head = re.split(r"[:.]", raw, maxsplit=1)[0].strip()
    return head


def _content_words(text: str) -> List[str]:
    return [w.lower() for w in _WORD_RE.findall(text) if len(w) >= 4]


def _binds_unit(sentence: str, unit_text: str) -> bool:
    """True when the sentence quotes the unit's own distinctive words.

    The longest quoted fragment of four words or more is the binder: its
    distinctive words must appear, in the same relative order, among the
    unit's words (a contiguous-or-sparse quote of the passage).
    """
    unit_words = _content_words(unit_text)
    if len(unit_words) < 4:
        return False
    for frag in _QUOTED_RE.findall(sentence):
        words = _content_words(frag)
        if len(words) < 4:
            continue
        it = iter(unit_words)
        if all(any(w == u for u in it) for w in words):
            return True
    return False


def attribution_flagged_sentences(
    narrative: str,
    unit_texts: Mapping[str, str],
    claim_speakers: Mapping[str, str],
) -> List[str]:
    """The sentences that hand a marked claim's words to another party.

    ``claim_speakers`` maps a unit id to its speaker TAG (as the prompt
    carries it); units without a tag are unmarked and never flag. A
    sentence flags when it binds one marked unit by quoting it AND names
    the party of a DIFFERENT marked unit without naming the bound unit's
    own party.
    """
    parties: Dict[str, str] = {}
    for unit_id, tag in claim_speakers.items():
        name = tag_party_name(tag)
        if name:
            parties[unit_id] = name
    if len(set(parties.values())) < 2:
        return []
    flagged: List[str] = []
    for match in _SENTENCE_RE.finditer(narrative or ""):
        sentence = match.group(0).strip()
        if not sentence:
            continue
        bound = [
            u
            for u, name in parties.items()
            if u in unit_texts and _binds_unit(sentence, unit_texts[u])
        ]
        if not bound:
            continue
        low = sentence.lower()
        named = {
            u
            for u, name in parties.items()
            if re.search(rf"(?<![\w-]){re.escape(name.lower())}(?![\w-])", low)
        }
        for u in bound:
            others = named - {u}
            if others and u not in named:
                flagged.append(sentence)
                break
    return flagged


def attribution_note(count: int, act_label: str = "Acte III") -> str:
    """The log line the dress carries when the check fired."""
    if not count:
        return ""
    return (
        f"{act_label} — #3559 : {count} phrase(s) prêtant à un autre parti "
        "les mots d'une revendication marquée (relance bornée)."
    )
