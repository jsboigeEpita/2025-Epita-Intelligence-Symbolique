# -*- coding: utf-8 -*-
"""Tests pour les utilitaires de génération de données.

#2362 : le style est un identifiant de configuration opaque — aucun contenu
de nom ne sélectionne de branche.
"""

import pytest
from argumentation_analysis.utils.data_generation import generate_sample_text

# Les textes attendus peuvent être longs, donc on vérifie des sous-chaînes clés.
CIVIL_ADDRESS_EXPECTED_SUBSTRING = "Nous sommes engagés dans une grande guerre civile"
FORMAL_ORATORY_EXPECTED_SUBSTRING = "Mesdames et messieurs, je me présente devant vous"
DEFAULT_EXPECTED_SUBSTRING = "L'argumentation est l'art de convaincre"


def test_generate_sample_text_civil_address_style():
    """Le style « civil_address » produit le discours d'adresse civile."""
    text = generate_sample_text(
        extract_name="extract_0101", source_name="corpus_001", style="civil_address"
    )
    assert CIVIL_ADDRESS_EXPECTED_SUBSTRING in text


def test_generate_sample_text_formal_oratory_style():
    """Le style « formal_oratory » produit le discours oratoire formel."""
    text = generate_sample_text(
        extract_name="extract_0101", source_name="corpus_001", style="formal_oratory"
    )
    assert FORMAL_ORATORY_EXPECTED_SUBSTRING in text


def test_generate_sample_text_generic_default():
    """Sans style, le texte générique est retourné."""
    text = generate_sample_text(extract_name="extract_0101", source_name="corpus_001")
    assert DEFAULT_EXPECTED_SUBSTRING in text


def test_generate_sample_text_unknown_style_falls_back_to_generic():
    """Un style non répertorié retombe sur le texte générique."""
    text = generate_sample_text(
        extract_name="extract_0101", source_name="corpus_001", style="inconnu"
    )
    assert DEFAULT_EXPECTED_SUBSTRING in text


def test_generate_sample_text_empty_names_generic_default():
    """Des noms vides retournent le texte générique."""
    text = generate_sample_text(extract_name="", source_name="")
    assert DEFAULT_EXPECTED_SUBSTRING in text


def test_generate_sample_text_is_name_blind():
    """Témoin d'aveuglement (#2362) : les noms qui sélectionnaient une branche
    par mot-clé retournent désormais le texte générique par défaut."""
    for extract_name, source_name in [
        ("Discours de Lincoln", "Quelconque"),
        ("Un discours", "Source: Abraham Lincoln"),
        ("Grand Débat National", "Quelconque"),
        ("Discours inaugural", "Quelconque"),
        ("Un extrait", "Discours d'Hitler"),
        ("discours hitlerien", "Archives"),
        ("Un extrait", "Discours de Churchill"),
        ("paroles de churchill", "Histoire"),
    ]:
        text = generate_sample_text(extract_name, source_name)
        assert DEFAULT_EXPECTED_SUBSTRING in text, (extract_name, source_name)
