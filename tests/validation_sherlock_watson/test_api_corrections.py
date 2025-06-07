#!/usr/bin/env python3
"""
Script de test rapide pour valider les corrections d'incompatibilités API.
"""

import asyncio
import sys
import traceback
from datetime import datetime

# Test des imports critiques
try:
    from argumentation_analysis.core.cluedo_oracle_state import CluedoOracleState
    from argumentation_analysis.agents.core.oracle.permissions import OracleResponse, QueryType
    from argumentation_analysis.agents.core.oracle.cluedo_dataset import CluedoDataset, RevelationRecord
    print("✅ Imports critiques réussis")
except Exception as e:
    print(f"❌ Erreur d'import: {e}")
    sys.exit(1)

def test_oracle_response_api():
    """Test de l'API OracleResponse avec attribut success."""
    print("\n🔍 Test OracleResponse API...")
    
    # Test avec authorized=True
    response = OracleResponse(
        authorized=True,
        message="Test réussi",
        query_type=QueryType.CARD_INQUIRY
    )
    
    # Test de la propriété success
    assert response.success == True, f"Expected success=True, got {response.success}"
    assert response.authorized == True, f"Expected authorized=True, got {response.authorized}"
    
    # Test avec authorized=False
    response_fail = OracleResponse(
        authorized=False,
        message="Test échoué",
        error_code="TEST_ERROR"
    )
    
    assert response_fail.success == False, f"Expected success=False, got {response_fail.success}"
    assert response_fail.error_code == "TEST_ERROR", f"Expected error_code='TEST_ERROR', got {response_fail.error_code}"
    
    print("✅ OracleResponse API compatible")

def test_revelation_record_api():
    """Test de l'API RevelationRecord."""
    print("\n🔍 Test RevelationRecord API...")
    
    revelation = RevelationRecord(
        card_revealed="Colonel Moutarde",
        revelation_type="owned_card",
        message="Moriarty possède Colonel Moutarde",
        strategic_value=0.8
    )
    
    # Test des propriétés de compatibilité
    assert revelation.card == "Colonel Moutarde", f"Expected card='Colonel Moutarde', got {revelation.card}"
    assert revelation.reason == "Moriarty possède Colonel Moutarde", f"Expected reason match, got {revelation.reason}"
    assert revelation.card_revealed == "Colonel Moutarde", f"Expected card_revealed match"
    
    print("✅ RevelationRecord API compatible")

def test_cluedo_oracle_state_initialization():
    """Test de l'initialisation de CluedoOracleState."""
    print("\n🔍 Test CluedoOracleState initialization...")
    
    elements_jeu = {
        "suspects": ["Colonel Moutarde", "Professeur Violet", "Mademoiselle Rose"],
        "armes": ["Poignard", "Chandelier", "Revolver"],
        "lieux": ["Salon", "Cuisine", "Bureau"]
    }
    
    oracle_state = CluedoOracleState(
        nom_enquete_cluedo="Test Mystery",
        elements_jeu_cluedo=elements_jeu,
        description_cas="Test case",
        initial_context="Test context",
        oracle_strategy="balanced"
    )
    
    # Test des attributs requis par les tests
    assert hasattr(oracle_state, 'oracle_interactions'), "Attribut oracle_interactions manquant"
    assert hasattr(oracle_state, 'cards_revealed'), "Attribut cards_revealed manquant"
    assert hasattr(oracle_state, 'agent_turns'), "Attribut agent_turns manquant"
    assert hasattr(oracle_state, 'recent_revelations'), "Attribut recent_revelations manquant"
    
    # Test des valeurs initiales
    assert oracle_state.oracle_interactions == 0, f"Expected oracle_interactions=0, got {oracle_state.oracle_interactions}"
    assert oracle_state.cards_revealed == 0, f"Expected cards_revealed=0, got {oracle_state.cards_revealed}"
    assert oracle_state.agent_turns == {}, f"Expected agent_turns={{}}, got {oracle_state.agent_turns}"
    assert oracle_state.recent_revelations == [], f"Expected recent_revelations=[], got {oracle_state.recent_revelations}"
    
    print("✅ CluedoOracleState initialization compatible")

def test_cluedo_dataset_api():
    """Test de l'API CluedoDataset."""
    print("\n🔍 Test CluedoDataset API...")
    
    elements_jeu = {
        "suspects": ["Colonel Moutarde", "Professeur Violet"],
        "armes": ["Poignard", "Chandelier"],
        "lieux": ["Salon", "Cuisine"]
    }
    
    dataset = CluedoDataset(
        moriarty_cards=["Colonel Moutarde", "Poignard"],
        elements_jeu=elements_jeu
    )
    
    # Test de la propriété elements_jeu
    assert hasattr(dataset, 'elements_jeu'), "Propriété elements_jeu manquante"
    assert dataset.elements_jeu == elements_jeu, f"Expected elements_jeu match, got {dataset.elements_jeu}"
    
    # Test de la méthode is_game_solvable_by_elimination
    assert hasattr(dataset, 'is_game_solvable_by_elimination'), "Méthode is_game_solvable_by_elimination manquante"
    solvable = dataset.is_game_solvable_by_elimination()
    assert isinstance(solvable, bool), f"Expected bool, got {type(solvable)}"
    
    print("✅ CluedoDataset API compatible")

def test_record_agent_turn():
    """Test de la méthode record_agent_turn."""
    print("\n🔍 Test record_agent_turn...")
    
    elements_jeu = {
        "suspects": ["Colonel Moutarde"],
        "armes": ["Poignard"],
        "lieux": ["Salon"]
    }
    
    oracle_state = CluedoOracleState(
        nom_enquete_cluedo="Test",
        elements_jeu_cluedo=elements_jeu,
        description_cas="Test",
        initial_context="Test"
    )
    
    # Test d'enregistrement d'un tour
    oracle_state.record_agent_turn(
        agent_name="Sherlock",
        action_type="hypothesis",
        action_details={"hypothesis": "Test hypothesis"}
    )
    
    # Vérifications
    assert "Sherlock" in oracle_state.agent_turns, "Agent 'Sherlock' non trouvé dans agent_turns"
    assert oracle_state.agent_turns["Sherlock"]["total_turns"] == 1, "total_turns incorrect"
    assert len(oracle_state.agent_turns["Sherlock"]["recent_actions"]) == 1, "recent_actions incorrect"
    
    print("✅ record_agent_turn compatible")

def test_add_revelation():
    """Test de la méthode add_revelation."""
    print("\n🔍 Test add_revelation...")
    
    elements_jeu = {
        "suspects": ["Colonel Moutarde"],
        "armes": ["Poignard"],
        "lieux": ["Salon"]
    }
    
    oracle_state = CluedoOracleState(
        nom_enquete_cluedo="Test",
        elements_jeu_cluedo=elements_jeu,
        description_cas="Test",
        initial_context="Test"
    )
    
    # Test d'ajout de révélation
    revelation = RevelationRecord(
        card_revealed="Colonel Moutarde",
        revelation_type="owned_card",
        message="Test revelation"
    )
    
    oracle_state.add_revelation(revelation, "Moriarty")
    
    # Vérifications
    assert len(oracle_state.recent_revelations) == 1, "recent_revelations length incorrect"
    assert oracle_state.cards_revealed == 1, "cards_revealed counter incorrect"
    assert oracle_state.recent_revelations[0]["card_revealed"] == "Colonel Moutarde", "card_revealed incorrect"
    
    print("✅ add_revelation compatible")

async def test_validate_suggestion_async():
    """Test de la méthode async validate_suggestion_with_oracle."""
    print("\n🔍 Test validate_suggestion_with_oracle (async)...")
    
    elements_jeu = {
        "suspects": ["Colonel Moutarde"],
        "armes": ["Poignard"],
        "lieux": ["Salon"]
    }
    
    oracle_state = CluedoOracleState(
        nom_enquete_cluedo="Test",
        elements_jeu_cluedo=elements_jeu,
        description_cas="Test",
        initial_context="Test"
    )
    
    # Test avec nouvelle signature
    suggestion = {
        "suspect": "Colonel Moutarde",
        "arme": "Poignard",
        "lieu": "Salon"
    }
    
    try:
        result = await oracle_state.validate_suggestion_with_oracle(
            suggestion=suggestion,
            requesting_agent="Watson"
        )
        
        assert isinstance(result, OracleResponse), f"Expected OracleResponse, got {type(result)}"
        print("✅ validate_suggestion_with_oracle (async) compatible")
        
    except Exception as e:
        print(f"❌ Erreur async validate_suggestion: {e}")
        raise

async def run_all_tests():
    """Lance tous les tests de validation."""
    print("🚀 Démarrage des tests de validation API...")
    
    try:
        test_oracle_response_api()
        test_revelation_record_api()
        test_cluedo_oracle_state_initialization()
        test_cluedo_dataset_api()
        test_record_agent_turn()
        test_add_revelation()
        await test_validate_suggestion_async()
        
        print("\n🎉 TOUS LES TESTS DE COMPATIBILITÉ API RÉUSSIS !")
        print("✅ Les incompatibilités critiques ont été corrigées")
        
    except Exception as e:
        print(f"\n❌ ÉCHEC DES TESTS: {e}")
        print(f"📝 Traceback: {traceback.format_exc()}")
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)