# -*- coding: utf-8 -*-
"""
#2403 — tests du localisateur de passage (``quality/passage.py``, symbole neuf).

Module pur et déterministe : localisation de la citation source (exacte puis
normalisée casse/accents/ponctuation), fenêtre de phrases autour du hit,
plancher de longueur de citation (pas de passage fabriqué pour « donc »).
Les imports sont locaux aux tests : ce fichier teste une surface **nouvelle**,
il n'a pas de témoin pristine — le né-rouge #2403 vit dans
``test_quality_passage_2403.py``.
"""

from argumentation_analysis.agents.core.quality import passage


def test_exact_quote_locates_at_its_offsets():
    src = "Alpha beta gamma. Delta epsilon zeta."
    quote = "Delta epsilon"
    span = passage.locate_quote(src, quote)
    assert span == (18, 31)
    assert src[span[0] : span[1]] == quote


def test_normalized_drift_still_locates_and_maps_back():
    src = "Les économistes l'ont affirmé hier, sans réserve."
    quote = "les economistes l ont affirme hier"  # accents et tiret perdus
    span = passage.locate_quote(src, quote)
    assert span is not None
    extracted = src[span[0] : span[1]]
    # La carte retour pointe dans l'original : les mots accentués y sont.
    assert "économistes" in extracted
    assert "affirmé" in extracted


def test_case_and_punctuation_drift_locates():
    src = "Cependant, les Économistes contestent la méthode."
    quote = "cependant les economistes contestent"
    assert passage.locate_quote(src, quote) is not None


def test_short_quote_is_refused():
    # Plancher 8 caractères : sous lui, un hit sous-chaîne ne prouve rien.
    assert passage.locate_quote("mot donc chose.", "donc") is None
    assert passage.locate_quote("mot pourtant chose.", "pourtan") is None  # 7


def test_quote_short_after_normalization_is_refused():
    # 9 caractères bruts (plancher franchi) mais la forme normalisée ne
    # garde que « donc » : la preuve sous-chaîne ne prouve rien.
    assert passage.locate_quote("mot — donc — chose.", "« donc !»") is None


def test_empty_and_absent_return_none():
    src = "Un texte source assez long pour servir de corps."
    assert passage.locate_quote(src, "") is None
    assert passage.locate_quote(src, "   ") is None
    assert passage.locate_quote(src, "citation absente du texte") is None
    assert passage.locate_quote("", "citation quelconque") is None


def test_quote_longer_than_source_returns_none():
    assert passage.locate_quote("court", "une citation beaucoup plus longue") is None


def test_split_sentences_covers_the_whole_text():
    src = "Une phrase. Une seconde ! Une troisième ?"
    spans = passage.split_sentences(src)
    assert [src[s:e] for s, e in spans] == [
        "Une phrase.",
        "Une seconde !",
        "Une troisième ?",
    ]


def test_passage_covers_overlapping_sentence_plus_neighbors():
    src = "Première phrase. Deuxième phrase. Troisième phrase. Quatrième. Cinquième."
    # « Troisième » vit dans la 3e phrase (indices 0..4).
    span = passage.locate_quote(src, "Troisième phrase")
    assert span is not None
    window = passage.sentence_passage(src, span[0], span[1], neighbors=1)
    assert "Deuxième" in window and "Troisième" in window and "Quatrième" in window
    assert "Première" not in window and "Cinquième" not in window


def test_passage_budget_trims_neighbors_never_the_quote():
    long_tail = " ".join(f"Phrase de bourrage numéro {i}." for i in range(60))
    src = (
        "Une amorce hors fenêtre. "
        "La citation cible se trouve exactement ici. "
        f"{long_tail}"
    )
    span = passage.locate_quote(src, "La citation cible se trouve exactement ici")
    assert span is not None
    window = passage.sentence_passage(src, span[0], span[1], neighbors=5, max_chars=300)
    assert len(window) <= 300
    assert "cible" in window  # la citation n'est jamais amputée


def test_passage_on_span_without_sentence_structure():
    # Aucun séparateur de phrase : la fenêtre retombe sur le span brut.
    src = "texte sans ponctuation du tout contenant la citation cherchée dedans"
    span = passage.locate_quote(src, "la citation cherchée")
    assert span is not None
    assert "citation" in passage.sentence_passage(src, span[0], span[1])


def test_map_back_offsets_stay_inside_the_source():
    src = "Éléonore décida d'agir : « Agissons ! » dit-elle."
    for quote in ("eleonore decida d agir", "agissons dit elle"):
        span = passage.locate_quote(src, quote)
        assert span is not None, quote
        start, end = span
        assert 0 <= start < end <= len(src)
