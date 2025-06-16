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
    assert miner_custom_config.min_claim_length == 5
    assert miner_custom_config.claim_keywords == ["point clé:", "important:"]

def test_extract_claims_non_string_input(miner_default: MockClaimMiner, caplog):
    """Teste l'extraction avec une entrée non textuelle."""
    with caplog.at_level(logging.WARNING):
        result = miner_default.extract_claims(123) # type: ignore
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
    """Teste un texte court sans mots-clés, inférieur à min_length."""
    assert miner_default.extract_claims("Court.") == []

def test_extract_claims_global_claim_success(miner_default: MockClaimMiner):
    """Teste le cas d'une revendication globale (pas de mots-clés, pas de phrases assertives distinctes)."""
    text = "Ceci est une affirmation unique sans rien de spécial." # > 8 chars
    result = miner_default.extract_claims(text)
    assert len(result) == 1
    claim = result[0]
    assert claim["type"] == "Revendication Globale (Mock)"
    assert claim["claim_text"] == text

def test_extract_claims_global_claim_too_short(miner_custom_config: MockClaimMiner):
    """Teste qu'une revendication globale trop courte n'est pas retournée."""
    # min_claim_length est 5 pour miner_custom_config
    assert miner_custom_config.extract_claims("Test") == [] # len 4 < 5

    text_just_long_enough = "Assez" # len 5
    result = miner_custom_config.extract_claims(text_just_long_enough)
    assert len(result) == 1
    assert result[0]["type"] == "Revendication Globale (Mock)"

def test_extract_claims_by_keyword_success(miner_default: MockClaimMiner):
    """Teste la détection réussie par mot-clé."""
    text = "Il est clair que le projet avancera rapidement."
    result = miner_default.extract_claims(text)
    assert len(result) == 1
    claim = result[0]
    assert claim["type"] == "Revendication par Mot-Clé (Mock)"
    assert claim["claim_text"] == "le projet avancera rapidement."
    assert claim["keyword_used"] == "il est clair que"

def test_extract_claims_by_keyword_text_too_short_after_keyword(miner_default: MockClaimMiner, miner_custom_config: MockClaimMiner):
    """Teste mot-clé mais texte suivant trop court."""
    text = "Finalement, il faut noter A." # "A." (len 2) < min_claim_length 8
    result = miner_default.extract_claims(text)
    # Ne devrait rien trouver car le texte après le mot-clé est trop court
    # et le fallback global ne s'applique pas car un mot-clé a été trouvé.
    assert result == []

    # Avec config custom (min_length 5)
    text_custom = "Point clé: B." # "B." (len 2) < min_claim_length 5
    result_custom = miner_custom_config.extract_claims(text_custom)
    assert result_custom == []

def test_extract_claims_multiple_keywords(miner_default: MockClaimMiner):
    """Teste la détection de plusieurs revendications par mots-clés."""
    text = "Nous affirmons que c'est vrai. De plus, il faut noter que c'est important."
    result = miner_default.extract_claims(text)
    assert len(result) == 2
    types = {c["type"] for c in result}
    assert "Revendication par Mot-Clé (Mock)" in types

def test_extract_claims_assertive_sentence_if_no_keywords(miner_default: MockClaimMiner):
    """Teste la logique de fallback sur Revendication Globale."""
    text = "Ceci est une phrase assertive. Elle est assez longue. Une autre plus courte."
    result = miner_default.extract_claims(text)
    # Avec la nouvelle logique, si aucun mot-clé n'est trouvé, tout le texte est une Revendication Globale.
    assert len(result) == 1
    assert result[0]["type"] == "Revendication Globale (Mock)"
    assert result[0]["claim_text"] == text

def test_extract_claims_assertive_sentence_filtered_by_length(miner_custom_config: MockClaimMiner):
    """Teste que les phrases assertives sont filtrées par longueur."""
    # min_claim_length = 5
    text = "Ok. Valide ici. Non."
    result = miner_custom_config.extract_claims(text)
    # Le texte entier est pris comme revendication globale car il est > 5
    assert len(result) == 1
    assert result[0]["type"] == "Revendication Globale (Mock)"
    assert result[0]["claim_text"] == text