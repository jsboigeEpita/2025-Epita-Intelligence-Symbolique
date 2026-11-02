# -*- coding: utf-8 -*-
"""Deterministic Dung-annex ref placement: the ref rides the sentence it
proves (#3349).

## The gap this closes

The #1914 citation contract (``annex_ref_rule``, ``act2_narrative_plugin``)
tells the writer to cite an annex ref « sur le battement qui mobilise
l'évidence correspondante » — the Dung annex ref belongs on the sentence
about the attack graph. No post-generation check held that rule:
``appendix_refs_in`` builds the prompt, nothing verifies where a ref landed.

Paid pass R1133a (doc ``8fa89437_ext1``, main ``30ec9a3cb``), Act II: the
ref sat on the FIRST-ORDER/MODAL sentence (« Les tests de théories du
premier ordre et modale n'ont rien distingué (voir Annexe Dung[…]) ») — a
reader following it to check that claim lands in the attack-graph annex,
which holds no FOL or modal material.

## Why the rule is this narrow

The dispatch's coarse census (a ref sentence with no graph keyword) mostly
catches prose that talks about the graph in OTHER words — measured on the
local stored states: « une réorganisation du matériau extrait », « ne
retient ni la thèse… », « n'y garde pas d'assise » — all legitimate Dung
sentences a keyword list cannot see. Moving those would be the pendulum.
The defect class, read on every locally readable hit, is exactly the
conjunction:

- the sentence, ref stripped, NAMES another formal axis (premier ordre /
  FOL / modal / Tweety), and
- it names NO graph vocabulary.

Only that shape is moved — to the nearest PRECEDING sentence of the same
paragraph that names the graph (the minimal displacement), else the
nearest FOLLOWING one; a paragraph with no graph sentence cannot host the
ref, and it is dropped. The prose otherwise stays unchanged, byte for
byte.

## Honesty contract (#1019, #3249)

The check is deterministic and never calls an LLM. What changed is
recorded as a code literal with counts — act, moved, dropped — never a
quote of the prose; the motif is filed under the #2046 fabrication-note
keys, so it is archived in the appendix and never reaches the reader as a
repair note.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

#: The woven ref shape the prompt licenses: « … (voir Annexe Dung[…]) ».
_REF_SPAN = re.compile(r"\s*\((voir\s+)?(Annexe\s+Dung\[[^\]]*\])\s*\)")

#: Graph vocabulary — the dispatch census list, stemmed to its inflections
#: (``graph* / attaquer / fragiliser / accepter / rejeter / extension /
#: sémantique / cadre / Dung``) so a conjugated sentence still counts.
_GRAPH_WORDS = re.compile(
    r"\b(graph\w*|attaqu\w*|fragilis\w*|accept\w*|rejet\w*|extension\w*|"
    r"s[ée]mantique\w*|cadre\w*|dung)\b",
    re.IGNORECASE,
)

#: The other formal axes the act names — the plugin's own vocabulary
#: (``act2_narrative_plugin``: « logique du premier ordre », « logique
#: modale », « solveur Tweety »). ``fol`` the adjective is archaic and
#: never co-occurs here without the graph words that exempt the sentence.
_AXIS_WORDS = re.compile(
    r"\b(premier\s+ordre|first[-\s]order|fol|moda(?:l|le|les|ux)|tweety)\b",
    re.IGNORECASE,
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _names(bare: str, words: re.Pattern[str]) -> bool:
    return bool(words.search(bare))


def _misplaced(sentence: str) -> Optional[re.Match[str]]:
    """The ref match when the sentence carries a Dung ref it does not prove.

    The conjunction the recorded defect has and the false positives the
    coarse census caught do not: another formal axis named, no graph
    vocabulary, ref excluded from both tests. Returning the match (not a
    bool) lets the caller use it without a second search.
    """
    match = _REF_SPAN.search(sentence)
    if match is None:
        return None
    bare = _REF_SPAN.sub("", sentence)
    if _names(bare, _AXIS_WORDS) and not _names(bare, _GRAPH_WORDS):
        return match
    return None


def _attach(target: str, ref: str) -> str:
    """Insert « (voir <ref>) » before the target sentence's final period."""
    stripped = target.rstrip()
    if stripped.endswith((".", "!", "?")):
        return stripped[:-1] + f" (voir {ref})" + stripped[-1]
    return stripped + f" (voir {ref})"


def move_misplaced_dung_refs(text: str) -> Tuple[str, int, int]:
    """Move (or drop) Dung annex refs their sentence does not prove.

    Returns ``(text, moved, dropped)``. Untouched paragraphs are returned
    byte-identical — the positive control of the family.
    """
    moved = dropped = 0
    out_lines: List[str] = []
    for line in text.split("\n"):
        sentences = _SENTENCE_SPLIT.split(line)
        changed = False
        for i in range(len(sentences)):
            while (match := _misplaced(sentences[i])) is not None:
                ref = match.group(2)
                bare_sentence = _REF_SPAN.sub("", sentences[i], count=1)
                target_idx = None
                for j in range(i - 1, -1, -1):
                    if _names(sentences[j], _GRAPH_WORDS) and not _REF_SPAN.search(
                        sentences[j]
                    ):
                        target_idx = j
                        break
                if target_idx is None:
                    for j in range(i + 1, len(sentences)):
                        if _names(sentences[j], _GRAPH_WORDS) and not _REF_SPAN.search(
                            sentences[j]
                        ):
                            target_idx = j
                            break
                sentences[i] = bare_sentence
                if target_idx is None:
                    # A paragraph with no graph sentence cannot host the
                    # ref: it is dropped, the sentence itself stays.
                    dropped += 1
                else:
                    sentences[target_idx] = _attach(sentences[target_idx], ref)
                    moved += 1
                changed = True
        out_lines.append(" ".join(sentences) if changed else line)
    return "\n".join(out_lines), moved, dropped


def dung_ref_placement_motif(act_label: str, moved: int, dropped: int) -> str:
    """The motive of the ref placement — act, counts, never the prose (#3249).

    An auditor must be able to find that the prose was CHANGED here; the
    reader must not see a repair note. The motif is a code literal folded
    into the appendix with the other fabrication notes (#2046).
    """
    parts = []
    if moved:
        parts.append(
            f"{moved} référence(s) d'annexe Dung déplacée(s) sur la phrase "
            "du graphe qu'elle prouve"
        )
    if dropped:
        parts.append(
            f"{dropped} référence(s) d'annexe Dung retirée(s) — aucun "
            "battement graphe dans le paragraphe"
        )
    return f"{act_label} : " + " ; ".join(parts) + "."
