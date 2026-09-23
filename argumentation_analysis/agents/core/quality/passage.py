# -*- coding: utf-8 -*-
"""Localisation du passage source d'une unité extraite (#2403).

La phase qualité jugeait la paraphrase de l'extracteur (``arg["text"]``) :
la présence des 7 vertus structurelles était décidée par la verbosité de
cette session d'extraction, pas par le document. Ce module localise la
citation source (``source_quote``) dans le texte d'origine et en extrait le
passage — la claim **plus** le passage où elle se situe, le niveau
``LOCAL_CONTEXT`` que #1907 définit.

Pur et déterministe : aucun LLM, aucune dépendance lourde. Les fonctions
rendent ``None`` quand la citation ne se localise pas — l'unité reste alors
``CLAIM``, comptée par la phase (jamais devinée).
"""

import re
import unicodedata
from typing import List, Optional, Tuple

_MAX_PASSAGE_CHARS = 1500
_DEFAULT_NEIGHBORS = 1

# Limite basse : une citation plus courte que ça se localise par sous-chaîne
# n'importe où (mots vides), et la « preuve » ne prouve rien.
_MIN_QUOTE_CHARS = 8

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?…])\s+")


def _normalize_with_map(text: str) -> Tuple[str, List[int]]:
    """Forme normalisée + carte retour vers les offsets originaux.

    La normalisation est celle des dérives mesurées des citations LLM :
    casse, accents, ponctuation et espacement. Chaque caractère conservé
    porte l'offset du caractère d'origine qui l'a produit.
    """
    chars: List[str] = []
    offsets: List[int] = []
    prev_space = True
    for i, ch in enumerate(text):
        if ch.isspace():
            if not prev_space:
                chars.append(" ")
                offsets.append(i)
                prev_space = True
            continue
        decomposed = unicodedata.normalize("NFKD", ch)
        ascii_ch = next(
            (c for c in decomposed if not unicodedata.combining(c) and c.isalnum()),
            None,
        )
        if ascii_ch is None:
            if not prev_space:
                chars.append(" ")
                offsets.append(i)
                prev_space = True
            continue
        chars.append(ascii_ch.lower())
        offsets.append(i)
        prev_space = False
    return "".join(chars), offsets


def locate_quote(source_text: str, quote: str) -> Optional[Tuple[int, int]]:
    """Offsets ``(début, fin)`` de la citation dans le texte source, ou ``None``.

    Essai exact d'abord (une citation byte-exacte est la preuve la plus
    forte), puis recherche sur forme normalisée (casse/accents/ponctuation/
    espacement). Une citation vide ou trop courte n'est pas localisable :
    renvoyer un hit pour « le mot « donc » » fabrique un passage, exactement
    le genre de zéro inventé que #1907 interdit.
    """
    if not source_text or not quote or len(quote.strip()) < _MIN_QUOTE_CHARS:
        return None
    exact = source_text.find(quote)
    if exact != -1:
        return exact, exact + len(quote)

    norm_source, src_map = _normalize_with_map(source_text)
    norm_quote, _ = _normalize_with_map(quote)
    # Même plancher sur la forme normalisée : « donc » habillé de
    # guillemets et de ponctuation (9 caractères bruts) ne devient pas
    # une preuve pour autant.
    if len(norm_quote.strip()) < _MIN_QUOTE_CHARS:
        return None
    hit = norm_source.find(norm_quote)
    if hit == -1:
        return None
    # Carte retour : le premier offset conservé ≥ hit, le dernier ≤ hit+fin.
    start = src_map[hit]
    last = hit + len(norm_quote) - 1
    if last >= len(src_map):
        last = len(src_map) - 1
    end = src_map[last]
    if end < start:
        return None
    return start, end + 1


def split_sentences(text: str) -> List[Tuple[int, int]]:
    """Offsets des phrases du texte (séparation regex, sans modèle)."""
    sentences: List[Tuple[int, int]] = []
    start = 0
    for match in _SENTENCE_SPLIT.finditer(text):
        sentences.append((start, match.start()))
        start = match.end()
    if start < len(text):
        sentences.append((start, len(text)))
    return [(s, e) for s, e in sentences if text[s:e].strip()]


def sentence_passage(
    source_text: str,
    start: int,
    end: int,
    neighbors: int = _DEFAULT_NEIGHBORS,
    max_chars: int = _MAX_PASSAGE_CHARS,
) -> str:
    """Le passage où la citation se situe : phrases chevauchantes ± voisines.

    « Quelques phrases » au sens de #1907. Le budget ``max_chars`` borne
    l'entrée de l'évaluateur ; si la fenêtre déborde, on rogne côté voisins
    (la citation elle-même n'est jamais amputée).
    """
    sentences = split_sentences(source_text)
    if not sentences:
        return source_text[start:end]

    overlapping: List[int] = [
        k for k, (s, e) in enumerate(sentences) if s < end and e > start
    ]
    if not overlapping:
        return source_text[start:end]
    first = max(0, overlapping[0] - neighbors)
    last = min(len(sentences) - 1, overlapping[-1] + neighbors)

    while (
        last > overlapping[-1] and sentences[last][1] - sentences[first][0] > max_chars
    ):
        last -= 1
    while (
        first < overlapping[0] and sentences[last][1] - sentences[first][0] > max_chars
    ):
        first += 1
    return source_text[sentences[first][0] : sentences[last][1]].strip()
