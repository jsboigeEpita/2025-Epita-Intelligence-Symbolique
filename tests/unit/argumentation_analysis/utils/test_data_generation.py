# -*- coding: utf-8 -*-
"""Tests pour les utilitaires de génération de données."""

import pytest
from argumentation_analysis.utils.data_generation import generate_sample_text

# Les textes attendus peuvent être longs, donc on peut vérifier des sous-chaînes clés.
LINCOLN_EXPECTED_SUBSTRING = "Nous sommes engagés dans une grande guerre civile"
DEBATE_SPEECH_EXPECTED_SUBSTRING = "Mesdames et messieurs, je me présente devant vous"
DEFAULT_EXPECTED_SUBSTRING = "L'argumentation est l'art de convaincre"

def test_generate_sample_text_lincoln_in_extract_name():
    """Teste le texte de Lincoln quand 'Lincoln' est dans extract_name."""
    text = generate_sample_text(extract_name="Discours de Lincoln", source_name="Quelconque")
    assert LINCOLN_EXPECTED_SUBSTRING in text

def test_generate_sample_text_lincoln_in_source_name():
    """Teste le texte de Lincoln quand 'Lincoln' est dans source_name."""
    text = generate_sample_text(extract_name="Un discours", source_name="Source: Abraham Lincoln")
    assert LINCOLN_EXPECTED_SUBSTRING in text

def test_generate_sample_text_debat_in_extract_name():
    """Teste le texte de débat/discours quand 'Débat' est dans extract_name."""
    text = generate_sample_text(extract_name="Grand Débat National", source_name="Quelconque")
    assert DEBATE_SPEECH_EXPECTED_SUBSTRING in text

def test_generate_sample_text_discours_in_extract_name():
    """Teste le texte de débat/discours quand 'Discours' est dans extract_name."""
    text = generate_sample_text(extract_name="Discours inaugural", source_name="Quelconque")
    assert DEBATE_SPEECH_EXPECTED_SUBSTRING in text

def test_generate_sample_text_hitler_in_source_name():
    """Teste le texte de débat/discours quand 'Hitler' est dans source_name."""
    text = generate_sample_text(extract_name="Un extrait", source_name="Discours d'Hitler")
    assert DEBATE_SPEECH_EXPECTED_SUBSTRING in text # La logique actuelle regroupe Hitler avec Débat/Discours

def test_generate_sample_text_hitler_in_extract_name_lower():
    """Teste le texte de débat/discours quand 'hitler' (minuscule) est dans extract_name."""
    text = generate_sample_text(extract_name="discours hitlerien", source_name="Archives")
    assert DEBATE_SPEECH_EXPECTED_SUBSTRING in text

def test_generate_sample_text_churchill_in_source_name():
    """Teste le texte de débat/discours quand 'Churchill' est dans source_name."""
    text = generate_sample_text(extract_name="Un extrait", source_name="Discours de Churchill")
    assert DEBATE_SPEECH_EXPECTED_SUBSTRING in text

def test_generate_sample_text_churchill_in_extract_name_lower():
    """Teste le texte de débat/discours quand 'churchill' (minuscule) est dans extract_name."""
    text = generate_sample_text(extract_name="paroles de churchill", source_name="Histoire")
    assert DEBATE_SPEECH_EXPECTED_SUBSTRING in text

def test_generate_sample_text_default_case():
    """Teste le cas par défaut quand aucun mot-clé n'est trouvé."""
    text = generate_sample_text(extract_name="Texte générique", source_name="Source quelconque")
    assert DEFAULT_EXPECTED_SUBSTRING in text

def test_generate_sample_text_empty_names():
    """Teste avec des noms vides, devrait retourner le texte par défaut."""
    text = generate_sample_text(extract_name="", source_name="")
    assert DEFAULT_EXPECTED_SUBSTRING in text