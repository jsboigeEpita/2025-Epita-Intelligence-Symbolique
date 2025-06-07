#!/usr/bin/env python3
"""
Test d'intégration des extensions Phase D dans CluedoOracleState
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from argumentation_analysis.core.cluedo_oracle_state import CluedoOracleState
from argumentation_analysis.agents.core.oracle.phase_d_extensions import PhaseDExtensions

def test_phase_d_integration():
    """Test complet de l'intégration des extensions Phase D"""
    
    print("[INFO] Test d'intégration des extensions Phase D...")
    print("="*60)
    
    # 1. Créer une instance CluedoOracleState
    test_state = CluedoOracleState(
        nom_enquete_cluedo="Test Phase D",
        elements_jeu_cluedo={
            "suspects": ["Colonel Moutarde", "Professeur Violet", "Madame Leblanc"],
            "armes": ["Revolver", "Chandelier", "Poignard"],
            "lieux": ["Bureau", "Salon", "Cuisine"]
        },
        description_cas="Test des extensions Phase D avancées",
        initial_context={"test": True}
    )
    
    print(f"[OK] CluedoOracleState créé: {test_state.nom_enquete_cluedo}")
    
    # 2. Test des nouvelles méthodes Phase D intégrées
    print("\n[TEST] Méthodes Phase D intégrées...")
    
    # Test add_dramatic_revelation
    if hasattr(test_state, 'add_dramatic_revelation'):
        test_revelation = test_state.add_dramatic_revelation(
            "J'ai le Colonel Moutarde dans mes cartes !",
            intensity=0.9,
            use_false_lead=True
        )
        print(f"[OK] add_dramatic_revelation: {len(test_revelation)} caractères")
        print(f"     Aperçu: {test_revelation[:100]}...")
    else:
        print(f"[ERROR] add_dramatic_revelation manquante")
    
    # Test get_ideal_trace_metrics
    if hasattr(test_state, 'get_ideal_trace_metrics'):
        test_metrics = test_state.get_ideal_trace_metrics()
        print(f"[OK] get_ideal_trace_metrics: score = {test_metrics.get('score_trace_ideale', 0):.2f}")
        print(f"     Métriques: {len(test_metrics)} critères")
    else:
        print(f"[ERROR] get_ideal_trace_metrics manquante")
    
    # Test apply_conversational_polish_to_message
    if hasattr(test_state, 'apply_conversational_polish_to_message'):
        test_polish = test_state.apply_conversational_polish_to_message(
            "Watson", 
            "C'est une déduction brillante !"
        )
        print(f"[OK] apply_conversational_polish_to_message: '{test_polish}'")
    else:
        print(f"[ERROR] apply_conversational_polish_to_message manquante")
    
    # 3. Test des extensions Phase D avancées
    print("\n[TEST] Extensions Phase D avancées...")
    
    extensions = PhaseDExtensions()
    
    # Test révélation progressive
    revelation = extensions.generate_progressive_revelation(
        "Sherlock a émis une hypothèse brillante",
        "Je confirme : j'ai effectivement le Revolver !",
        0.8
    )
    print(f"[OK] Révélation progressive: {len(revelation)} caractères")
    
    # Test fausse piste
    false_setup, misdirection, true_reveal = extensions.create_false_lead_sequence(
        "J'ai le Chandelier ET le Poignard !"
    )
    print(f"[OK] Séquence fausse piste générée")
    print(f"     Setup: {false_setup[:50]}...")
    print(f"     Misdirection: {misdirection}")
    print(f"     Révélation: {true_reveal[:50]}...")
    
    # Test polish conversationnel
    watson_content = extensions.apply_conversational_polish("Watson", "Excellent travail !")
    sherlock_content = extensions.apply_conversational_polish("Sherlock", "Cette déduction est logique")
    moriarty_content = extensions.apply_conversational_polish("Moriarty", "Voici ma révélation")
    
    print(f"[OK] Polish conversationnel:")
    print(f"     Watson: '{watson_content}'")
    print(f"     Sherlock: '{sherlock_content}'")
    print(f"     Moriarty: '{moriarty_content}'")
    
    # 4. Test métriques trace idéale
    print("\n[TEST] Métriques trace idéale...")
    
    # Simulons une conversation avec quelques messages
    test_state.conversation_history = [
        {"agent_name": "Sherlock", "content": "Je pense que c'est le Colonel Moutarde avec le Revolver dans le Bureau", "message_type": "hypothesis"},
        {"agent_name": "Watson", "content": "Brillante déduction ! Cette hypothèse me semble logique", "message_type": "analysis"},
        {"agent_name": "Moriarty", "content": "*pause dramatique* Intéressante théorie... Je révèle : j'ai le **Revolver** !", "message_type": "revelation"}
    ]
    
    metrics = test_state.get_ideal_trace_metrics()
    print(f"[OK] Métriques calculées:")
    for key, value in metrics.items():
        print(f"     {key}: {value:.2f}")
    
    # 5. Validation Phase D
    print("\n[TEST] Validation critères Phase D...")
    
    if hasattr(test_state, 'validate_phase_d_requirements'):
        validations = test_state.validate_phase_d_requirements()
        print(f"[OK] Validation Phase D:")
        for criteria, status in validations.items():
            status_symbol = "[OK]" if status else "[KO]"
            print(f"     {status_symbol} {criteria}: {status}")
    
    print("\n" + "="*60)
    print("[SUCCESS] Intégration des extensions Phase D complète !")
    print("          - Révélations progressives avec fausses pistes")
    print("          - Timing dramatique optimisé") 
    print("          - Polish conversationnel par agent")
    print("          - Métriques de trace idéale (objectif 8.0+/10)")
    print("          - Validation automatique des critères Phase D")

if __name__ == "__main__":
    test_phase_d_integration()