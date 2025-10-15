# -*- coding: utf-8 -*-
"""Tests pour les utilitaires de traitement de texte."""

import pytest
from argumentation_analysis.utils.text_processing import split_text_into_arguments


def test_split_simple_sentences():
    """Teste la division de phrases simples séparées par des points."""
    text = "Ceci est le premier argument. Et voici le deuxième argument. Un troisième pour la route."
    expected = [
        "Ceci est le premier argument.",
        "Et voici le deuxième argument.",
        "Un troisième pour la route.",
    ]
    assert split_text_into_arguments(text, min_arg_length=5) == expected


def test_split_with_various_delimiters():
    """Teste la division avec différents types de délimiteurs (points, exclamations, nouvelles lignes)."""
    text = "Premier point! \nDeuxième point? Un troisième.\nEt un quatrième après un simple point."
    expected = [
        "Premier point!",
        "Deuxième point?",
        "Un troisième.",
        "Et un quatrième après un simple point.",
    ]
    # Augmenter min_arg_length pour éviter "Un troisième" seul si le split est trop fin avant le strip
    assert split_text_into_arguments(text, min_arg_length=5) == expected


def test_split_no_delimiters_long_text():
    """Teste un texte long sans délimiteurs, doit retourner le texte entier."""
    text = "Ceci est un long texte sans aucun délimiteur de phrase standard"
    expected = ["Ceci est un long texte sans aucun délimiteur de phrase standard"]
    assert split_text_into_arguments(text, min_arg_length=10) == expected


def test_split_no_delimiters_short_text():
    """Teste un texte court sans délimiteurs, ne doit rien retourner si trop court."""
    text = "Court."
    expected = []  # Car "Court." est < min_arg_length=10 par défaut
    assert split_text_into_arguments(text) == expected
    expected_long_enough = ["Texte assez long"]
    assert (
        split_text_into_arguments("Texte assez long", min_arg_length=5)
        == expected_long_enough
    )


def test_split_ignore_short_arguments():
    """Teste que les arguments trop courts sont ignorés."""
    text = "Argument long et valide. Court. Autre argument valide et suffisamment long."
    expected = [
        "Argument long et valide.",
        "Autre argument valide et suffisamment long.",
    ]
    assert split_text_into_arguments(text, min_arg_length=10) == expected


def test_split_empty_text():
    """Teste avec un texte vide."""
    text = ""
    expected = []
    assert split_text_into_arguments(text) == expected


def test_split_none_text():
    """Teste avec une entrée None."""
    text = None
    expected = []
    assert split_text_into_arguments(text) == expected


def test_split_delimiters_no_content():
    """Teste des délimiteurs sans contenu suffisant entre eux."""
    text = ". . . ! ? "
    expected = []
    assert split_text_into_arguments(text, min_arg_length=5) == expected


def test_split_text_with_multiple_spaces_around_delimiters():
    """Teste des espaces multiples autour des délimiteurs."""
    text = "Phrase un.    Phrase deux! \n\n Phrase trois?"
    expected = ["Phrase un.", "Phrase deux!", "Phrase trois?"]
    assert split_text_into_arguments(text, min_arg_length=5) == expected


def test_split_text_ends_without_delimiter_but_is_argument():
    """Teste un texte qui se termine sans délimiteur mais constitue un argument valide."""
    text = "Ceci est un argument qui ne finit pas par un point mais est assez long"
    expected = [
        "Ceci est un argument qui ne finit pas par un point mais est assez long"
    ]
    assert split_text_into_arguments(text, min_arg_length=10) == expected


def test_split_complex_case_with_newlines_and_short_parts():
    """Cas complexe avec nouvelles lignes et parties courtes."""
    text = "Voici la première idée principale.\nElle est importante. \n\nOk. \nUne autre idée suit. Et c'est tout."
    # "Ok." sera filtré par min_arg_length=10
    expected = [
        "Voici la première idée principale.",
        "Elle est importante.",
        "Une autre idée suit.",
        "Et c'est tout.",
    ]
    assert split_text_into_arguments(text, min_arg_length=10) == expected


def test_split_keeps_punctuation_at_end_of_argument():
    """Vérifie que la ponctuation finale est conservée."""
    text = "Argument un! Argument deux? Argument trois."
    expected = ["Argument un!", "Argument deux?", "Argument trois."]
    assert split_text_into_arguments(text, min_arg_length=5) == expected
