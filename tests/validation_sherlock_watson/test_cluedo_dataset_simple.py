#!/usr/bin/env python3
"""
Test simple pour vérifier que CluedoDataset fonctionne après les corrections d'intégrité.
"""

import pytest
from datetime import datetime
from argumentation_analysis.agents.core.oracle.cluedo_dataset import (
    CluedoDataset, CluedoSuggestion, RevelationRecord, ValidationResult
)
from argumentation_analysis.agents.core.oracle.permissions import QueryType, RevealPolicy

def test_cluedo_dataset_basic():
    """Test basique de CluedoDataset après corrections d'intégrité."""
    # Cartes détenues par Moriarty
    moriarty_cards = ["Professeur Violet", "Chandelier"]
    
    # Création du dataset
    dataset = CluedoDataset(moriarty_cards)
    assert dataset is not None
    
    # Vérification des cartes de Moriarty
    cards = dataset.get_moriarty_cards()
    assert len(cards) == 2
    assert "Professeur Violet" in cards
    assert "Chandelier" in cards
    
    print("[OK] Test de base CluedoDataset reussi")

def test_cluedo_suggestion_creation():
    """Test de création de suggestion Cluedo."""
    suggestion = CluedoSuggestion(
        suspect="Colonel Moutarde",
        arme="Poignard", 
        lieu="Salon",
        suggested_by="TestAgent"
    )
    
    assert suggestion.suspect == "Colonel Moutarde"
    assert suggestion.arme == "Poignard"
    assert suggestion.lieu == "Salon"
    assert suggestion.suggested_by == "TestAgent"
    
    print("[OK] Test creation CluedoSuggestion reussi")

def test_revelation_record_creation():
    """Test de création d'enregistrement de révélation."""
    revelation = RevelationRecord(
        card_revealed="Professeur Violet",
        revelation_type="owned_card",
        message="Test révélation",
        revealed_to="TestAgent",
        timestamp=datetime.now(),
        query_type=QueryType.CARD_INQUIRY
    )
    
    assert revelation.card == "Professeur Violet"
    assert revelation.revealed_to == "TestAgent"
    assert revelation.reason == "Test révélation"
    assert revelation.query_type == QueryType.CARD_INQUIRY
    
    print("[OK] Test creation RevelationRecord reussi")

def test_forbidden_methods_integrity():
    """Test que les méthodes interdites lèvent bien des erreurs d'intégrité."""
    moriarty_cards = ["Professeur Violet", "Chandelier"]
    dataset = CluedoDataset(moriarty_cards)
    
    # Test que get_autres_joueurs_cards() est interdite
    with pytest.raises(PermissionError) as exc_info:
        dataset.get_autres_joueurs_cards()
    
    assert "VIOLATION RÈGLES CLUEDO" in str(exc_info.value)
    print("[OK] Test méthodes interdites réussi")

def test_validation_result_creation():
    """Test de création de résultat de validation."""
    result = ValidationResult(
        is_valid=True,
        reason="Test validation",
        revealed_cards=["Professeur Violet"]
    )
    
    assert result.is_valid is True
    assert result.reason == "Test validation" 
    assert "Professeur Violet" in result.revealed_cards
    
    print("[OK] Test création ValidationResult réussi")

if __name__ == "__main__":
    test_cluedo_dataset_basic()
    test_cluedo_suggestion_creation()
    test_revelation_record_creation()
    test_forbidden_methods_integrity()
    test_validation_result_creation()
    print("\n[SUCCESS] Tous les tests simples sont passés ! L'intégrité est préservée.")