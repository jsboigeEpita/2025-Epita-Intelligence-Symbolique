# -*- coding: utf-8 -*-
"""Tests pour le MockClaimMiner."""

import pytest
import logging
from argumentation_analysis.mocks.claim_mining import MockClaimMiner

@pytest.fixture
def miner_default() -> MockClaimMiner:
    """Instance de MockClaimMiner avec config par défaut."""
    return MockClaimMiner()

@pytest.fixture
def miner_custom_config() -> MockClaimMiner:
    """Instance avec une configuration personnalisée."""
    config = {
        "min_claim_length": 5,
        "claim_keywords": ["point clé:", "important:"]
    }
    return MockClaimMiner(config=config)

def test_initialization_default(miner_default: MockClaimMiner):
    """Teste l'initialisation avec la configuration par défaut."""
    assert miner_default.get_config() == {}
    assert miner_default.min_claim_length == 8
    assert "il est clair que" in miner_default.claim_keywords

def test_initialization_custom_config(miner_custom_config: MockClaimMiner):
    """Teste l'initialisation avec une configuration personnalisée."""
    expected_config = {
        "min_claim_length": 5,
        "claim_keywords": ["point clé:", "important:"]
    }
    assert miner_custom_config.get_config() == expected_config
    assert miner_custom_config.min_claim_length == 5
    assert miner_custom_config.claim_keywords == ["point clé:", "important:"]

def test_extract_claims_non_string_input(miner_default: MockClaimMiner, caplog):
    """Teste l'extraction avec une entrée non textuelle."""
    with caplog.at_level(logging.WARNING):
        result = miner_default.extract_claims(False) # type: ignore
    assert result == []
    assert "MockClaimMiner.extract_claims a reçu une entrée non textuelle." in caplog.text
    
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        result_none = miner_default.extract_claims(None) # type: ignore
    assert result_none == []
    assert "MockClaimMiner.extract_claims a reçu une entrée non textuelle." in caplog.text

def test_extract_claims_empty_string(miner_default: MockClaimMiner):
    """Teste avec une chaîne vide."""
    assert miner_default.extract_claims("") == []

def test_extract_claims_short_text_no_keywords(miner_default: MockClaimMiner):
    """Teste un texte court sans mots-clés, inférieur à min_length pour global."""
    # min_claim_length est 8 par défaut
    assert miner_default.extract_claims("Court.") == [] 

def test_extract_claims_global_claim_success(miner_default: MockClaimMiner):
    """Teste le cas d'une revendication globale (pas de mots-clés, pas de phrases assertives distinctes)."""
    text = "Ceci est une affirmation unique sans rien de spécial." # > 8 chars
    result = miner_default.extract_claims(text)
    assert len(result) == 1
    claim = result[0]
    assert claim["type"] == "Revendication Globale (Mock)"
    assert claim["claim_text"] == text
    assert claim["confidence"] == 0.50
    assert claim["source_indices"] == (0, len(text))

def test_extract_claims_global_claim_too_short(miner_custom_config: MockClaimMiner):
    """Teste qu'une revendication globale trop courte n'est pas retournée."""
    # min_claim_length est 5 pour miner_custom_config
    assert miner_custom_config.extract_claims("Test") == [] # len 4 < 5
    
    text_just_long_enough = "Assez" # len 5
    result = miner_custom_config.extract_claims(text_just_long_enough)
    assert len(result) == 1
    assert result[0]["type"] == "Revendication Globale (Mock)"

def test_extract_claims_by_keyword_success(miner_default: MockClaimMiner):
    """Teste la détection par mot-clé."""
    text = "D'abord, il est clair que le ciel est bleu. Ensuite, un autre point."
    result = miner_default.extract_claims(text)
    assert len(result) == 1
    claim = result[0]
    assert claim["type"] == "Revendication par Mot-Clé (Mock)"
    assert claim["claim_text"] == "le ciel est bleu." # S'arrête au point
    assert claim["keyword_used"] == "il est clair que"
    assert claim["confidence"] == 0.75
    keyword_start = text.find("il est clair que")
    keyword_end = keyword_start + len("il est clair que")
    # Les indices de la source incluent le mot-clé et le texte de la revendication
    assert claim["source_indices"] == (keyword_start, text.find(".", keyword_end) + 1)

def test_extract_claims_by_keyword_no_period(miner_default: MockClaimMiner):
    """Teste mot-clé sans point final, prend une portion."""
    text = "Aussi, nous affirmons que la terre est ronde et c'est tout"
    result = miner_default.extract_claims(text)
    assert len(result) == 1
    claim = result[0]
    assert claim["type"] == "Revendication par Mot-Clé (Mock)"
    assert claim["claim_text"] == "que la terre est ronde et c'est tout" # Prend jusqu'à 100 chars ou fin
    assert claim["keyword_used"] == "nous affirmons"

def test_extract_claims_by_keyword_text_too_short_after_keyword(miner_default: MockClaimMiner):
    """Teste mot-clé mais texte suivant trop court."""
    text = "Finalement, il faut noter A." # "A." (len 2) < min_claim_length 8
    result = miner_default.extract_claims(text)
    # Devrait tomber sur Revendication Globale si le texte entier est assez long
    assert len(result) == 1
    assert result[0]["type"] == "Revendication Globale (Mock)"

    # Avec config custom (min_length 5)
    text_custom = "Point clé: B." # "B." (len 2) < min_claim_length 5
    result_custom = miner_custom_config.extract_claims(text_custom)
    assert len(result_custom) == 1
    assert result_custom[0]["type"] == "Revendication Globale (Mock)"

    text_custom_valid = "Important: Valide." # "Valide." (len 7) >= min_claim_length 5
    result_custom_valid = miner_custom_config.extract_claims(text_custom_valid)
    assert len(result_custom_valid) == 1
    assert result_custom_valid[0]["type"] == "Revendication par Mot-Clé (Mock)"
    assert result_custom_valid[0]["claim_text"] == "Valide."
    assert result_custom_valid[0]["keyword_used"] == "Important:"


def test_extract_claims_assertive_sentence_if_no_keywords(miner_default: MockClaimMiner):
    """Teste phrase assertive si aucun mot-clé n'est trouvé."""
    text = "Ceci est une phrase assertive. Elle est assez longue. Une autre plus courte."
    # min_claim_length = 8
    # "Ceci est une phrase assertive." (OK)
    # "Elle est assez longue." (OK)
    # "Une autre plus courte." (len 22, OK)
    result = miner_default.extract_claims(text)
    assert len(result) == 3 # Le mock actuel prend toutes les phrases si pas de keyword
    claim_texts = {r["claim_text"] for r in result}
    assert "Ceci est une phrase assertive" in claim_texts # Le mock split sur '.', donc le point n'est pas inclus
    assert "Elle est assez longue" in claim_texts
    assert "Une autre plus courte" in claim_texts
    for claim in result:
        assert claim["type"] == "Revendication Assertive (Mock)"
        assert claim["confidence"] == 0.60

def test_extract_claims_assertive_sentence_filtered_by_length(miner_custom_config: MockClaimMiner):
    """Teste que les phrases assertives sont filtrées par longueur."""
    # min_claim_length = 5
    text = "Ok. Valide ici. Non."
    # "Ok" (len 2) < 5
    # "Valide ici" (len 10) > 5
    # "Non" (len 3) < 5
    result = miner_custom_config.extract_claims(text)
    assert len(result) == 1
    assert result[0]["type"] == "Revendication Assertive (Mock)"
    assert result[0]["claim_text"] == "Valide ici"

def test_extract_claims_keywords_have_priority_over_assertive(miner_default: MockClaimMiner):
    """Teste que les mots-clés ont la priorité sur les phrases assertives."""
    text = "Il est clair que c'est un point. Une autre phrase assertive ici."
    result = miner_default.extract_claims(text)
    assert len(result) == 1 # Seulement celle par mot-clé
    assert result[0]["type"] == "Revendication par Mot-Clé (Mock)"
    assert result[0]["claim_text"] == "c'est un point."
    assert result[0]["keyword_used"] == "il est clair que"

def test_extract_claims_multiple_keywords(miner_default: MockClaimMiner):
    """Teste la détection de plusieurs mots-clés."""
    text = (
        "Il est clair que le premier argument est solide. "
        "De plus, nous affirmons que le second est pertinent."
    )
    result = miner_default.extract_claims(text)
    assert len(result) == 2
    keywords_found = {r["keyword_used"] for r in result}
    assert "il est clair que" in keywords_found
    assert "nous affirmons" in keywords_found
    
    claim_texts = {r["claim_text"] for r in result}
    assert "le premier argument est solide." in claim_texts
    assert "que le second est pertinent." in claim_texts